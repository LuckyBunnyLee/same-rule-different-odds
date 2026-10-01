"""Step 2: parse cached WA results pages -> data/derived/rt_athletes.csv + races.csv.

Source of truth is the Next.js __NEXT_DATA__ JSON embedded in each cached page
(pageProps.eventPhasesByDiscipline): one ``unit`` per race (heat) with a
``startlist`` (lane = ``start``) and ``results`` (mark, wind, reactionTime,
rank, qualification). Optional enrichments are merged when present:

* --pdf (rt_pdf_results.csv, from parse_pdfs.py): official results-PDF rows
  -> DQ rule codes (TR16.8 = false start), actual start times, weather.
* --waveform (rt_waveform.csv, from ocr_waveforms.py): Seiko start-waveform
  header -> start attempt number and 'Ready Time'.

Each invocation writes exactly one table (--table) to --out, so the producer
commands in producers.json can be verified byte-for-byte:

  data/scripts/build_rt.py --table athletes --pdf data/derived/rt_pdf_results.csv
      --waveform data/derived/rt_waveform.csv --out data/derived/rt_athletes.csv
  data/scripts/build_rt.py --table races --pdf data/derived/rt_pdf_results.csv
      --waveform data/derived/rt_waveform.csv --out data/derived/races.csv

(run with .venv/Scripts/python.exe from the ssac/ folder; see data/README.md)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from config import (ALL_EVENTS, COMPETITIONS, ROUND_ORDER, WA_DOCS, comp_key,
                    race_id, round_code)
from wa_http import DERIVED, RAW, ROOT, extract_next_data, read_cached_text, read_meta

PAGES = RAW / "wa" / "pages"
DISC_TO_EVENT = {(d, s): (e, sx) for e, sx, s, d in ALL_EVENTS}

ATHLETE_COLS = ["race_id", "comp", "year", "event", "sex", "round", "heat", "lane",
                "athlete", "country", "rt_s", "result", "place", "wind", "status",
                "notes", "source_url", "retrieved_at",
                # extra columns (not in the original spec, kept at the end)
                "athlete_id", "bib", "qual", "record", "rt_raw", "wa_phase", "wa_unit_id"]


def doc_url(doc: dict) -> str:
    path = doc["filePath"].replace("\\", "/").strip("/")
    return f"{WA_DOCS}/{path}/{doc['fileName']}"


def status_from_mark(mark: str) -> str:
    m = (mark or "").strip().upper()
    if not m:
        return "NR"            # no result given
    if m[0].isdigit():
        return "OK"
    for code in ("DQ", "DNS", "DNF"):
        if m.startswith(code):
            return code
    return m


def to_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(str(x).replace("+", ""))
    except ValueError:
        return None


def parse_page(path: Path, comp: dict):
    html = read_cached_text(path)
    data = extract_next_data(html)
    meta = read_meta(path) or {}
    pp = data["props"]["pageProps"]
    ph = pp["eventPhasesByDiscipline"]
    q = data.get("query", {})
    disc_slug = ph["discipline"]["nameUrlSlug"]
    sex_slug = ph["sexNameUrlSlug"]
    event, sex = DISC_TO_EVENT[(disc_slug, sex_slug)]
    rnd = round_code(ph["phaseName"])
    source_url = meta.get("final_url") or meta.get("url")
    retrieved_at = meta.get("retrieved_at", "")

    phase_docs = {d["typeName"]: doc_url(d) for d in ph["documents"] if d["unitId"] == 0}
    unit_docs: dict[int, dict] = {}
    for d in ph["documents"]:
        if d["unitId"]:
            unit_docs.setdefault(d["unitId"], {})[d["typeName"]] = doc_url(d)

    athletes, races = [], []
    for u in ph["units"]:
        code = (u.get("unitCode") or "").strip()
        heat = int(code) if code.isdigit() else 1
        rid = race_id(comp["comp"], comp["year"], event, sex, rnd, heat)
        sl = {s["competitorId"]: s for s in (u.get("startlist") or [])}
        # WA sometimes uses a different competitorId in results than in the
        # startlist for the same athlete (duplicate profiles): fall back to bib,
        # then to the exact name.
        sl_bib = {str(s.get("bib")): cid for cid, s in sl.items() if s.get("bib")}
        sl_name = {s["competitorName"].strip().upper(): cid for cid, s in sl.items()}
        res = u.get("results") or []
        seen = set()
        rows = []
        for r in res:
            cid = r["competitorId"]
            notes = []
            if cid not in sl:
                alt = sl_bib.get(str(r.get("bib"))) or sl_name.get(r["competitorName"].strip().upper())
                if alt is not None:
                    notes.append("startlist matched by bib/name (WA competitorId differs)")
                    cid = alt
            seen.add(cid)
            s = sl.get(cid, {})
            rt_raw = (r.get("reactionTime") or "").strip()
            if not s:
                notes.append("not on WA startlist (lane unknown)")
            rt_val = to_float(rt_raw)
            if rt_val == 0.0:          # printed '0.000' = not recorded (site and PDF)
                rt_val = None
                notes.append("RT printed as 0.000 (not recorded); treated as missing")
            rows.append(dict(
                lane=s.get("start"), athlete=r["competitorName"],
                country=r.get("competitorCountryCode"), rt_s=rt_val,
                rt_raw=rt_raw, result=r.get("resultMark"), place=r.get("resultRank"),
                wind=to_float(r.get("resultWind")), status=status_from_mark(r.get("resultMark")),
                notes=notes, athlete_id=r.get("competitorId_WA"), bib=r.get("bib"),
                qual=r.get("qualified"), record=r.get("record")))
        for cid, s in sl.items():
            if cid in seen:
                continue
            rows.append(dict(
                lane=s.get("start"), athlete=s["competitorName"],
                country=s.get("competitorCountryCode"), rt_s=None, rt_raw="", result="",
                place=None, wind=None, status="NR",
                notes=["on WA startlist but absent from results"],
                athlete_id=s.get("competitorId_WA"), bib=s.get("bib"), qual=None, record=None))
        winds = [x["wind"] for x in rows if x["wind"] is not None]
        race_wind = winds[0] if winds else None
        for x in rows:
            x.update(race_id=rid, comp=comp["comp"], year=comp["year"], event=event, sex=sex,
                     round=rnd, heat=heat, source_url=source_url, retrieved_at=retrieved_at,
                     wa_phase=ph["phaseName"], wa_unit_id=u["unitId"])
            athletes.append(x)

        udt = (u.get("unitDateTime") or ph.get("phaseDateAndTime") or "")
        # WA stores local wall-clock time with a spurious 'Z' (checked vs PDFs).
        date_local, time_local = (udt[:10], udt[11:16]) if len(udt) >= 16 else ("", "")
        docs = unit_docs.get(u["unitId"], {})
        races.append(dict(
            race_id=rid, comp=comp["comp"], year=comp["year"], event=event, sex=sex,
            round=rnd, heat=heat, date=date_local, sched_start_local=time_local,
            tz=comp["tz"], n_athletes=len(rows),
            n_started=sum(1 for x in rows if x["status"] not in ("DNS", "NR")),
            n_rt=sum(1 for x in rows if x["rt_s"] is not None),
            wind=race_wind,
            n_dq=sum(1 for x in rows if x["status"] == "DQ"),
            n_dns=sum(1 for x in rows if x["status"] == "DNS"),
            n_dnf=sum(1 for x in rows if x["status"] == "DNF"),
            timing=comp["timing"], wa_phase=ph["phaseName"], wa_unit_id=u["unitId"],
            wa_unit_rule=u.get("unitRuleDetail"),
            waveform_url=docs.get("Waveform", ""),
            officiating_video_url=docs.get("Officiating Video Clip", ""),
            photofinish_url=docs.get("Photofinish", ""),
            results_pdf_url=phase_docs.get("Official Results", ""),
            unit_results_pdf_url=docs.get("Official Unit Results", ""),
            source_url=source_url, retrieved_at=retrieved_at))
    return athletes, races


def load_all(comps: list[str] | None = None, events: list[str] | None = None):
    """Parse every cached results page, optionally restricted to comps / events.

    ``comps`` like ['WCH2023', 'OG2024']; ``events`` like ['100m', '110mH'].
    Producer commands pass both explicitly so the analysed subset is recorded.
    """
    athletes, races = [], []
    known = {comp_key(c): c for c in COMPETITIONS}
    for comp_dir in sorted(PAGES.iterdir()):
        if comp_dir.name not in known or (comps and comp_dir.name not in comps):
            continue
        for path in sorted(comp_dir.glob("*.html.gz")):
            a, r = parse_page(path, known[comp_dir.name])
            if events and r and r[0]["event"] not in events:
                continue
            athletes += a
            races += r
    return pd.DataFrame(athletes), pd.DataFrame(races)


def add_subset_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--comps", required=True,
                    help="comma list of competitions, e.g. WCH2019,WCH2022,OG2024")
    ap.add_argument("--events", required=True, help="comma list of events, e.g. 100m,100mH,110mH")


def subset(a) -> dict:
    return dict(comps=a.comps.split(","), events=a.events.split(","))


def merge_pdf(ath: pd.DataFrame, races: pd.DataFrame, p: Path | None):
    """Use official results-PDF rows to label false starts and actual start times."""
    if p is None:
        return ath, races
    pdf = pd.read_csv(p, dtype={"bib": "string"})
    ath = ath.copy()
    # athlete-level merge on race_id + lane (Doha 2019 PDFs have no bib column)
    pdf_ath = pdf.rename(columns={"pdf_lane": "lane"})[
        ["race_id", "lane", "bib", "pdf_card", "pdf_name", "pdf_result", "pdf_rule", "pdf_fs",
         "pdf_rt", "pdf_fn", "pdf_heat_note"]].rename(columns={"bib": "pdf_bib"})
    ath["lane"] = pd.array(ath["lane"], dtype="Int64")
    pdf_ath["lane"] = pd.array(pdf_ath["lane"], dtype="Int64")
    pdf_ath.loc[pdf_ath["pdf_rt"] == 0.0, "pdf_rt"] = float("nan")   # '0.000' = not recorded
    m = ath.merge(pdf_ath, on=["race_id", "lane"], how="left")
    m["in_pdf"] = m["pdf_result"].notna()
    m["dq_rule"] = m["pdf_rule"].fillna("")
    m["pdf_fn"] = m["pdf_fn"].fillna("")
    fs = m["pdf_fs"].fillna(False).astype(bool)
    m.loc[fs & m["status"].eq("DQ"), "status"] = "FS"
    m.loc[fs, "fs_evidence"] = "official PDF: " + m.loc[fs, "dq_rule"]
    for i in m.index[fs]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [
            f"false start (official PDF: DQ {m.at[i, 'dq_rule']}"
            + (f", Fn {m.at[i, 'pdf_fn']}" if m.at[i, "pdf_fn"] else "")
            + (f", note '{m.at[i, 'pdf_heat_note']}'" if m.at[i, "dq_rule"] == "TR*" else "")
            + "); RT belongs to the aborted start, not the final valid start"]
    # where the two official sources disagree on RT, the organiser's PDF wins
    # (Doha 2019 site values for negative RTs are truncated, e.g. -0.030 vs -0.036)
    diff = m["pdf_rt"].notna() & m["rt_s"].notna() & ((m["pdf_rt"] - m["rt_s"]).abs() > 0.0005)
    for i in m.index[diff]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [
            f"site RT {m.at[i, 'rt_raw']} replaced by official PDF RT {m.at[i, 'pdf_rt']:.3f}"]
        m.at[i, "rt_s"] = m.at[i, "pdf_rt"]
    # start cards printed before the name (Y = yellow card / warning, L = lane mark)
    m["start_card"] = m["pdf_card"].fillna("")
    def card_note(row):
        if not row["start_card"] or not isinstance(row["pdf_heat_note"], str):
            return ""
        segs = [x for x in row["pdf_heat_note"].split(" | ") if f"BIB {row['pdf_bib']}" in x]
        return segs[0] if segs else ""
    m["card_note"] = m.apply(card_note, axis=1)
    for i in m.index[m["start_card"].ne("")]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [
            f"start card {m.at[i, 'start_card']}: {m.at[i, 'card_note'] or 'see PDF'}"]
    m = m.drop(columns=["pdf_fs", "pdf_heat_note", "pdf_card", "pdf_bib"])
    other = m["dq_rule"].ne("") & ~fs
    for i in m.index[other]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [
            f"official PDF: {m.at[i, 'pdf_result']} {m.at[i, 'dq_rule']} (not a false start)"]
    # post-competition changes: DQ on the website but a ranked time in the PDF
    later = m["status"].eq("DQ") & m["pdf_result"].fillna("").str.match(r"^\d")
    for i in m.index[later]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [
            f"DQ on WA site but ranked {m.at[i, 'pdf_result']} in the official PDF "
            "(post-race DQ/annulment; the start itself was legal)"]
        m.at[i, "status"] = "DQ-post"
    # cross-checks between the two official sources
    rt_mismatch = m["pdf_rt"].notna() & m["rt_s"].notna() & ((m["pdf_rt"] - m["rt_s"]).abs() > 0.0005)
    for i in m.index[rt_mismatch]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [f"PDF RT {m.at[i, 'pdf_rt']:.3f} differs from site"]
    rt_only_pdf = m["pdf_rt"].notna() & m["rt_s"].isna()
    for i in m.index[rt_only_pdf]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [f"RT {m.at[i, 'pdf_rt']:.3f} only in PDF"]
    name_mismatch = m["in_pdf"] & (m["pdf_name"].fillna("").str.upper().str.replace(r"\W", "", regex=True)
                                   != m["athlete"].fillna("").str.upper().str.replace(r"\W", "", regex=True))
    for i in m.index[name_mismatch]:
        m.at[i, "notes"] = list(m.at[i, "notes"]) + [f"PDF name at this lane: {m.at[i, 'pdf_name']}"]
    m = m.drop(columns=["pdf_result", "pdf_rule", "pdf_rt", "pdf_name"])

    heat_info = (pdf.dropna(subset=["race_id"]).groupby("race_id")
                 .agg(actual_start_local=("pdf_start_time", "first"),
                      pdf_wind=("pdf_wind", "first"),
                      temperature_c=("pdf_temp_c", "first"),
                      humidity_pct=("pdf_humidity", "first"),
                      pdf_notes=("pdf_heat_note", lambda s: " | ".join(sorted({x for x in s.dropna() if x})))))
    races = races.merge(heat_info, on="race_id", how="left")
    return m, races


def merge_waveform(races: pd.DataFrame, p: Path | None):
    if p is None:
        return races
    wf = pd.read_csv(p)
    # only validated readings are carried into races.csv (details: rt_waveform.csv)
    wf["wf_ready_time_s"] = wf["wf_ready_time_s"].where(wf["wf_ok"])
    wf["wf_attempt"] = wf["wf_attempt"].where(wf["wf_heat_ocr"] == wf["heat"])
    cols = ["race_id", "wf_attempt", "wf_ready_time_s", "wf_ok", "wf_crosschecked", "wf_notes"]
    cols = [c for c in cols if c in wf.columns]
    out = races.merge(wf[cols].drop_duplicates("race_id"), on="race_id", how="left")
    out["wf_attempt"] = pd.array(out["wf_attempt"], dtype="Int64")
    return out


def finalize(ath: pd.DataFrame, races: pd.DataFrame):
    ath = ath.copy()
    for col in ("fs_evidence", "dq_rule", "pdf_fn", "start_card", "card_note"):
        if col not in ath.columns:
            ath[col] = ""
        ath[col] = ath[col].fillna("")
    if "in_pdf" not in ath.columns:
        ath["in_pdf"] = False
    # Without an official PDF (Olympics), a DQ with RT < 0.100 s is labelled a
    # false start by inference (the 0.100 s rule); fs_evidence records this.
    inferred = ath["status"].eq("DQ") & ath["rt_s"].lt(0.100) & ath["fs_evidence"].eq("")
    ath.loc[inferred, "status"] = "FS"
    ath.loc[inferred, "fs_evidence"] = "inferred: DQ with RT < 0.100 s (no official PDF)"
    for i in ath.index[inferred]:
        ath.at[i, "notes"] = list(ath.at[i, "notes"]) + [
            "false start inferred from DQ + RT<0.100 (no PDF); RT belongs to the aborted start"]
    ath["notes"] = ath["notes"].apply(lambda v: "; ".join(v) if isinstance(v, list) else (v or ""))
    for col in ("lane", "place", "athlete_id", "heat", "year"):
        ath[col] = pd.array(ath[col], dtype="Int64")
    ath["_ro"] = ath["round"].map(ROUND_ORDER)
    ath = ath.sort_values(["comp", "year", "event", "sex", "_ro", "heat", "lane"]).drop(columns="_ro")
    ath = ath[ATHLETE_COLS + [c for c in ath.columns if c not in ATHLETE_COLS]]

    fs_counts = ath[ath["status"].eq("FS")].groupby("race_id").size().rename("n_fs")
    fs_inf = (ath[ath["status"].eq("FS") & ath["fs_evidence"].str.startswith("inferred")]
              .groupby("race_id").size().rename("n_fs_inferred"))
    races = races.merge(fs_counts, on="race_id", how="left").merge(fs_inf, on="race_id", how="left")
    races["n_fs"] = races["n_fs"].fillna(0).astype(int)
    races["n_fs_inferred"] = races["n_fs_inferred"].fillna(0).astype(int)
    fn = (ath[ath["pdf_fn"].ne("")].assign(d=lambda d: d["athlete"] + ":" + d["pdf_fn"])
          .groupby("race_id")["d"].apply(lambda s: "; ".join(s)).rename("pdf_fn_marks"))
    races = races.merge(fn, on="race_id", how="left")
    yc = ath[ath["start_card"].eq("Y")]
    races = races.merge(yc.groupby("race_id").size().rename("n_yellow"), on="race_id", how="left")
    races["n_yellow"] = races["n_yellow"].fillna(0).astype(int)
    cards = (ath[ath["start_card"].ne("")]
             .assign(d=lambda d: d["start_card"] + " " + d["athlete"] + " (lane "
                     + d["lane"].astype("string").fillna("?") + "): " + d["card_note"])
             .groupby("race_id")["d"].apply(lambda s: "; ".join(s)).rename("card_detail"))
    races = races.merge(cards, on="race_id", how="left")
    dq_desc = (ath[ath["status"].isin(["DQ", "FS", "DQ-post"])]
               .assign(d=lambda d: d["athlete"] + " (" + d["country"].fillna("") + ", lane "
                       + d["lane"].astype("string").fillna("?") + ", " + d["status"]
                       + ", RT " + d["rt_raw"].replace("", "n/a") + ")")
               .groupby("race_id")["d"].apply(lambda s: "; ".join(s)).rename("dq_detail"))
    races = races.merge(dq_desc, on="race_id", how="left")
    races["_ro"] = races["round"].map(ROUND_ORDER)
    races = races.sort_values(["comp", "year", "event", "sex", "_ro", "heat"]).drop(columns="_ro")
    front = ["race_id", "comp", "year", "event", "sex", "round", "heat", "date",
             "sched_start_local", "actual_start_local", "tz", "n_athletes", "n_started",
             "n_rt", "wind", "n_fs", "n_dq", "n_dns", "n_dnf", "dq_detail", "n_yellow",
             "card_detail"]
    front = [c for c in front if c in races.columns]
    races = races[front + [c for c in races.columns if c not in front]]
    return ath, races


def build(pdf: Path | None, waveform: Path | None, comps=None, events=None):
    ath, races = load_all(comps, events)
    ath, races = merge_pdf(ath, races, pdf)
    races = merge_waveform(races, waveform)
    return finalize(ath, races)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["athletes", "races"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pdf", default=None, help="rt_pdf_results.csv to merge (optional)")
    ap.add_argument("--waveform", default=None, help="rt_waveform.csv to merge (optional)")
    add_subset_args(ap)
    a = ap.parse_args(argv)
    ath, races = build(Path(a.pdf) if a.pdf else None,
                       Path(a.waveform) if a.waveform else None, **subset(a))
    df = ath if a.table == "athletes" else races
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False, encoding="utf-8", lineterminator="\n")
    if a.table == "athletes":
        print(f"{a.out}: {len(ath)} athlete-starts, {ath['rt_s'].notna().sum()} with RT")
    else:
        print(f"{a.out}: {len(races)} races")
    return 0


if __name__ == "__main__":
    sys.exit(main())
