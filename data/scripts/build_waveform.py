"""Step 5b: parse waveform OCR + pixel geometry -> rt_waveform.csv / rt_waveform_lanes.csv.

Inputs: the OCR cache written by ocr_waveforms.py, the cached waveform JPGs, and
the WA results pages (via build_rt.load_all) for race_id mapping and validation.

Two independent readings of the Seiko 'Ready Time' are produced per race:
* ``wf_ready_time_s``    - the printed header value ('Ready Time : 1.810 sec'), OCR;
* ``wf_ready_time_px_s`` - the x-position of the magenta 'set' marker line,
  converted with a pixel->time mapping fitted on the red per-lane RT marker lines
  against the official RTs (the plot is linear, -2.0 s .. +1.0 s over 1800 px).
Per-lane RT text (OCR) and red-line positions are also checked against the
official WA RTs. ``wf_ok`` is True only when all checks pass (see README).

Usage:
  data/scripts/build_waveform.py --table races --out data/derived/rt_waveform.csv
  data/scripts/build_waveform.py --table lanes --out data/derived/rt_waveform_lanes.csv
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from build_rt import add_subset_args, load_all, subset
from fetch_docs import local_path
from ocr_waveforms import OCR_DIR, STRIP, magenta_mask
from wa_http import read_meta

PANEL_TOP0 = 146.0      # y of the first lane panel's top edge (px)
PANEL_PITCH = 266.0     # vertical pitch of the nine lane panels (px)
N_PANELS = 9
PLOT_Y = (150, 2525)    # rows spanned by the lane panels
DEFAULT_X0, DEFAULT_S = 1200.0, 600.0   # axis labels: -2.0 s at x=0, +1.0 s at x=1800

HEAT_RE = re.compile(r"Heat\s*:?\s*(\d{1,3})")
ATT_RE = re.compile(r"Attempt\s*:?\s*(\d{1,3})")
READY_RE = re.compile(r"Ready\s*Time\s*:?\s*(\d+\.\d{3})")
RACE_RE = re.compile(r"Race\s*:?\s*\((\d+)\)\s*(.+)")
STAMP_RE = re.compile(r"(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{1,2}:\d{2})")
LANE_RE = re.compile(r"Lane\s*(\d)")
RT_RE = re.compile(r"(-?\d\.\d{3})\s*s?e?c?")
# bib/name/country line, matched per OCR row ("2873 Akani SIMBINE (RSA)"; OCR may drop the space)
BIB_RE = re.compile(r"^\s*(\d{3,5})\s*([^\d|].*?)\s*\(\s*([A-Z]{3})\s*\)?\s*$")


def join_boxes(bxs: list[dict], ytol: float = 12.0) -> str:
    """Join OCR boxes into reading order (rows by y, then x)."""
    bxs = sorted(bxs, key=lambda b: ((b["y0"] + b["y1"]) / 2, b["x0"]))
    rows, cur, cy = [], [], None
    for b in bxs:
        yc = (b["y0"] + b["y1"]) / 2
        if cy is None or abs(yc - cy) <= ytol:
            cur.append(b)
            cy = yc if cy is None else cy
        else:
            rows.append(cur)
            cur, cy = [b], yc
    if cur:
        rows.append(cur)
    return " | ".join(" ".join(b["text"] for b in sorted(r, key=lambda b: b["x0"])) for r in rows)


def line_centres(counts: np.ndarray, min_count: float) -> list[float]:
    cols = np.flatnonzero(counts >= min_count)
    if cols.size == 0:
        return []
    groups = np.split(cols, np.flatnonzero(np.diff(cols) > 1) + 1)
    return [float(g.mean()) for g in groups]


def red_mask(im: np.ndarray) -> np.ndarray:
    r, g, b = (im[..., i].astype(np.int16) for i in range(3))
    return (r > 150) & (g < 120) & (b < 120) & (r - g > 90)


def trace_top(im: np.ndarray, k: int) -> np.ndarray:
    """Uppermost blue force-trace pixel (row within the panel) for every column."""
    top = int(PANEL_TOP0 + (k - 1) * PANEL_PITCH)
    pan = im[top + 2: top + 252].astype(np.int16)
    r, g, b = pan[..., 0], pan[..., 1], pan[..., 2]
    m = (b - r > 40) & (b - g > 40) & (r < 90) & (g < 90)
    ys = np.full(pan.shape[1], np.nan)
    has = m.any(axis=0)
    ys[has] = np.argmax(m[:, has], axis=0)
    return ys


def force_onset_x(ys: np.ndarray, red_x: float | None):
    """First column (>= +0.05 s) where the trace rises >= max(3 px, 5% of its peak)
    above the pre-gun baseline (median over -0.30..-0.02 s), for 3 columns running.
    Uses the nominal axis (x = 1200 + 600 t); a descriptive check of where the
    red detection line sits on the displayed force rise, not a force estimate."""
    if red_x is None:
        return None, None
    x = np.arange(ys.size)
    t = (x - DEFAULT_X0) / DEFAULT_S
    red_t = (red_x - DEFAULT_X0) / DEFAULT_S
    base = (t > -0.30) & (t < -0.02) & ~np.isnan(ys)
    if base.sum() < 50:
        return None, None
    yb = np.median(ys[base])
    noise = np.median(np.abs(ys[base] - yb))
    win = (t >= 0.05) & (t <= red_t + 0.15)
    rise = yb - ys
    if not np.any(win & ~np.isnan(ys)):
        return None, None
    peak = float(np.nanmax(np.where(win, rise, np.nan)))
    thr = max(3.0, 3 * noise + 1, 0.05 * peak)
    for i in np.flatnonzero(win & (rise >= thr)):
        seg = rise[i:i + 3]
        if seg.size == 3 and np.all(seg >= thr):
            return float(i), peak
    return None, peak


def pixel_geometry(img_path: Path) -> dict:
    im = np.asarray(Image.open(img_path).convert("RGB"))
    y0, y1 = PLOT_Y
    mag = magenta_mask(im[y0:y1]).sum(axis=0)
    mag_x = line_centres(mag, 0.5 * (y1 - y0))
    red = red_mask(im)
    lanes, onsets = {}, {}
    for k in range(1, N_PANELS + 1):
        top = int(PANEL_TOP0 + (k - 1) * PANEL_PITCH)
        cnt = red[top + 5: top + 255].sum(axis=0)
        xs = line_centres(cnt, 150)
        lanes[k] = xs
        onsets[k] = force_onset_x(trace_top(im, k), xs[0] if len(xs) == 1 else None)
    return dict(mag_x=mag_x, red_x=lanes, onset=onsets, shape=im.shape)


def parse_header(hdr: list[dict]) -> dict:
    text = join_boxes(hdr)
    def grab(rx):
        m = rx.search(text)
        return m.group(1) if m else None
    rm = RACE_RE.search(text)
    title = sorted(hdr, key=lambda b: (b["y0"], b["x0"]))[0]["text"] if hdr else ""
    key_scores = [b["score"] for b in hdr if re.search(r"Heat|Attempt|Ready", b["text"])]
    return dict(wf_title=title, wf_race_label=(rm.group(2).split("|")[0].strip() if rm else None),
                wf_stamp=grab(STAMP_RE), wf_heat_ocr=grab(HEAT_RE), wf_attempt=grab(ATT_RE),
                wf_ready_time_s=grab(READY_RE),
                wf_header_min_score=min(key_scores) if key_scores else None,
                wf_header_text=text)


def parse_lanes(lane_boxes: list[dict]) -> dict:
    per = {k: [] for k in range(1, N_PANELS + 1)}
    for b in lane_boxes:
        yc = (b["y0"] + b["y1"]) / 2 + STRIP[0]
        k = int((yc - PANEL_TOP0 + 6) // PANEL_PITCH) + 1
        if 1 <= k <= N_PANELS:
            per[k].append(b)
    out = {}
    for k, bxs in per.items():
        text = join_boxes(bxs)
        lm = LANE_RE.search(text)
        body = text[lm.end():] if lm else text
        rtm = RT_RE.search(body)
        bm = next((m for m in (BIB_RE.match(row) for row in body.split(" | ")) if m), None)
        out[k] = dict(lane_label=int(lm.group(1)) if lm else None,
                      wf_rt_s=float(rtm.group(1)) if rtm else None,
                      wf_dashes=bool(re.search(r"-{3,}", body)) and not rtm,
                      wf_quickest="Quickest" in body,
                      wf_bib=bm.group(1) if bm else None,
                      wf_name=bm.group(2).strip() if bm else None,
                      wf_country=bm.group(3) if bm else None,
                      ocr_text=text,
                      min_score=min((b["score"] for b in bxs), default=None))
    return out


def norm(s) -> str:
    return re.sub(r"[^A-Z]", "", str(s or "").upper())


def collect(ocr_dir: Path, comps=None, events=None):
    ath, all_races = load_all(comps, events)
    races = all_races[all_races["waveform_url"].fillna("").str.startswith("http")].copy()
    linked = set(races["race_id"])
    rows, lanes = [], []
    for _, r in races.iterrows():
        img = local_path(r["waveform_url"], "waveform")
        ocr_path = Path(ocr_dir) / img.parent.name / (img.stem + ".json")
        base = dict(race_id=r["race_id"], comp=r["comp"], year=r["year"], event=r["event"],
                    sex=r["sex"], round=r["round"], heat=r["heat"],
                    waveform_url=r["waveform_url"],
                    retrieved_at=(read_meta(img) or {}).get("retrieved_at", ""))
        if not img.exists() or not ocr_path.exists():
            rows.append({**base, "wf_notes": "image or OCR missing"})
            continue
        ocr = json.loads(ocr_path.read_text(encoding="utf-8"))
        hdr = parse_header(ocr["header"])
        geo = pixel_geometry(img)
        lp = parse_lanes(ocr["lanes"])
        # WA occasionally links a heat's image under another heat of the same round
        # (WCH2023 110mH-M SF: the 'heat 1' link shows heat 2). Re-key the image to
        # the heat printed in its header when that race exists and has no image of
        # its own; the lane-RT check below then validates the re-keyed race.
        target = r["race_id"]
        h = hdr.get("wf_heat_ocr")
        if h and h.isdigit() and int(h) != int(r["heat"]):
            alt = r["race_id"].rsplit("-H", 1)[0] + f"-H{int(h)}"
            if alt in set(all_races["race_id"]) and alt not in linked:
                target = alt
        base.update(race_id=target, heat=int(target.rsplit("-H", 1)[1]),
                    wf_linked_from=r["race_id"] if target != r["race_id"] else "")
        rows.append({**base, **hdr, "mag_x": geo["mag_x"]})
        a = ath[ath["race_id"] == target]
        for k in range(1, N_PANELS + 1):
            aj = a[a["lane"] == k]
            j = aj.iloc[0] if len(aj) else None
            reds = geo["red_x"][k]
            lanes.append(dict(race_id=target, lane=k, **{kk: v for kk, v in lp[k].items()},
                              red_x=reds[0] if len(reds) == 1 else None, n_red_lines=len(reds),
                              onset_x=geo["onset"][k][0], trace_peak_px=geo["onset"][k][1],
                              json_athlete=j["athlete"] if j is not None else None,
                              json_bib=str(j["bib"]) if j is not None else None,
                              json_rt_s=j["rt_s"] if j is not None else None,
                              json_status=j["status"] if j is not None else None))
    return pd.DataFrame(rows), pd.DataFrame(lanes)


def calibrate(lanes: pd.DataFrame):
    """Fit x = X0 + S * t on red RT lines whose OCR text equals the official RT."""
    ok = lanes.dropna(subset=["red_x", "json_rt_s", "wf_rt_s"])
    ok = ok[(ok["wf_rt_s"] - ok["json_rt_s"]).abs() < 0.0005]
    if len(ok) < 10:
        return DEFAULT_X0, DEFAULT_S, np.nan, len(ok)
    S, X0 = np.polyfit(ok["json_rt_s"].to_numpy(), ok["red_x"].to_numpy(), 1)
    resid = ok["red_x"] - (X0 + S * ok["json_rt_s"])
    return float(X0), float(S), float(resid.std(ddof=2)), len(ok)


def build(ocr_dir: Path, comps=None, events=None):
    races, lanes = collect(ocr_dir, comps, events)
    X0, S, sd_px, n_cal = calibrate(lanes)
    lanes["wf_rt_px_s"] = ((lanes["red_x"] - X0) / S).round(4)
    lanes["onset_5pct_s"] = ((lanes["onset_x"] - X0) / S).round(4)
    lanes["red_minus_onset_ms"] = ((lanes["red_x"] - lanes["onset_x"]) / S * 1000).round(1)
    lanes["rt_match"] = np.where(lanes["json_rt_s"].notna() & lanes["wf_rt_s"].notna(),
                                 (lanes["wf_rt_s"] - lanes["json_rt_s"]).abs() < 0.0005, np.nan)
    lanes["name_match"] = np.where(lanes["json_athlete"].notna() & lanes["wf_name"].notna(),
                                   [norm(a) == norm(b) or norm(a).endswith(norm(b)) or norm(b).endswith(norm(a))
                                    for a, b in zip(lanes["json_athlete"], lanes["wf_name"])], np.nan)
    races["wf_ready_time_s"] = pd.to_numeric(races.get("wf_ready_time_s"), errors="coerce")
    races["wf_attempt"] = pd.to_numeric(races.get("wf_attempt"), errors="coerce").astype("Int64")
    races["wf_heat_ocr"] = pd.to_numeric(races.get("wf_heat_ocr"), errors="coerce").astype("Int64")

    def px_fp(xs):
        if not isinstance(xs, list) or len(xs) != 1:
            return np.nan
        return round((X0 - xs[0]) / S, 4)
    races["wf_ready_time_px_s"] = races["mag_x"].apply(px_fp)
    races["wf_n_magenta_lines"] = races["mag_x"].apply(lambda v: len(v) if isinstance(v, list) else 0)
    races["wf_ready_diff_ms"] = ((races["wf_ready_time_s"] - races["wf_ready_time_px_s"]) * 1000).round(1)
    g = lanes.groupby("race_id")
    agg = pd.DataFrame({
        "wf_lanes_rt_compared": g["rt_match"].apply(lambda s: int(s.notna().sum())),
        "wf_lanes_rt_match": g["rt_match"].apply(lambda s: int((s == True).sum())),  # noqa: E712
        "wf_lanes_name_compared": g["name_match"].apply(lambda s: int(s.notna().sum())),
        "wf_lanes_name_match": g["name_match"].apply(lambda s: int((s == True).sum())),  # noqa: E712
        "wf_quickest_lane": g.apply(lambda d: ",".join(str(x) for x in d.loc[d["wf_quickest"] == True, "lane"])),  # noqa: E712
        "wf_lanes_with_rt": g["wf_rt_s"].apply(lambda s: int(s.notna().sum())),
    }).reset_index()
    races = races.merge(agg, on="race_id", how="left")
    heat_ok = races["wf_heat_ocr"].astype("float") == races["heat"].astype("float")
    # 0.000 s (no 'set' signal registered) and e.g. 0.103 s are system artefacts
    # 9.999 is a saturated/sentinel value; WIC2025 holds run long (see README)
    fp_ok = races["wf_ready_time_s"].between(0.5, 6.0)
    crossed = races["wf_ready_diff_ms"].abs() <= 4.0
    # the plot starts at -2.0 s, so a longer hold has no marker line to check against
    off_chart = (races["wf_n_magenta_lines"] == 0) & (races["wf_ready_time_s"] > 1.99)
    px_ok = crossed | off_chart
    lanes_ok = races["wf_lanes_rt_match"] == races["wf_lanes_rt_compared"]
    races["wf_crosschecked"] = crossed
    races["wf_ok"] = heat_ok & fp_ok & px_ok & lanes_ok & races["wf_attempt"].notna()
    notes = []
    for i, r in races.iterrows():
        n = [r["wf_notes"]] if isinstance(r.get("wf_notes"), str) else []
        if isinstance(r.get("wf_linked_from"), str) and r["wf_linked_from"]:
            n.append(f"image is linked under {r['wf_linked_from']} on the WA site but its "
                     f"header says heat {r['wf_heat_ocr']}; re-keyed")
        if not heat_ok[i]:
            n.append(f"OCR heat {r['wf_heat_ocr']} != {r['heat']}")
        if not fp_ok[i]:
            n.append("ready time missing/out of range")
        if off_chart[i]:
            n.append("hold > 2.0 s: 'set' marker outside the plot window, OCR value not cross-checked")
        elif not px_ok[i]:
            n.append(f"OCR vs marker-line ready time differ by {r['wf_ready_diff_ms']} ms"
                     if pd.notna(r["wf_ready_diff_ms"]) else "magenta marker line not found uniquely")
        if fp_ok[i] and r["wf_ready_time_s"] < 1.0:
            n.append("unusually short hold (< 1.0 s)")
        if fp_ok[i] and r["wf_ready_time_s"] > 3.0:
            n.append("unusually long hold (> 3.0 s)")
        if r["comp"] == "WIC" and int(r["year"]) == 2025:
            n.append("WIC2025 holds are systematically long (median ~3.2 s): the 'ready' "
                     "trigger may differ at this meet; do not pool without checking")
        if not lanes_ok[i]:
            n.append(f"lane RT OCR matched {r['wf_lanes_rt_match']}/{r['wf_lanes_rt_compared']}")
        notes.append("; ".join(n))
    races["wf_notes"] = notes
    races["wf_px_calibration"] = f"x = {X0:.2f} + {S:.2f}*t (n={n_cal} red lines, resid SD {sd_px:.2f} px)"
    races = races.drop(columns=["mag_x"])
    front = ["race_id", "comp", "year", "event", "sex", "round", "heat", "wf_attempt",
             "wf_ready_time_s", "wf_ready_time_px_s", "wf_ready_diff_ms", "wf_ok", "wf_crosschecked",
             "wf_notes",
             "wf_heat_ocr", "wf_lanes_rt_match", "wf_lanes_rt_compared", "wf_lanes_name_match",
             "wf_lanes_name_compared", "wf_lanes_with_rt", "wf_quickest_lane",
             "wf_header_min_score", "wf_title", "wf_race_label", "wf_stamp",
             "wf_n_magenta_lines", "wf_px_calibration", "wf_linked_from", "waveform_url", "retrieved_at",
             "wf_header_text"]
    races = races[[c for c in front if c in races.columns]]
    lanes = lanes[["race_id", "lane", "lane_label", "wf_rt_s", "wf_rt_px_s", "json_rt_s",
                   "rt_match", "wf_dashes", "wf_quickest", "wf_bib", "json_bib", "wf_name",
                   "wf_country", "json_athlete", "name_match", "json_status", "n_red_lines",
                   "red_x", "onset_5pct_s", "red_minus_onset_ms", "trace_peak_px",
                   "min_score", "ocr_text"]]
    return races.sort_values("race_id"), lanes.sort_values(["race_id", "lane"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["races", "lanes"], required=True)
    ap.add_argument("--ocr-dir", default=str(OCR_DIR))
    ap.add_argument("--out", required=True)
    add_subset_args(ap)
    a = ap.parse_args(argv)
    races, lanes = build(Path(a.ocr_dir), **subset(a))
    df = races if a.table == "races" else lanes
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False, encoding="utf-8", lineterminator="\n")
    if a.table == "races":
        print(f"{a.out}: {len(races)} races, wf_ok={int(races['wf_ok'].sum())}, "
              f"ready time read={int(races['wf_ready_time_s'].notna().sum())}")
        print(races["wf_px_calibration"].iloc[0])
    else:
        print(f"{a.out}: {len(lanes)} lane rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
