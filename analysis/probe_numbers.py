"""EXPLORATORY probe numbers for analysis/numbers.json (keys 'probe.*').

Reads analysis/outputs/recent_probe.json (written by analysis/recent_probe.py; NOT pre-registered) and re-publishes
the quantities the abstract may quote. Every description starts with 'EXPLORATORY (not pre-registered)'. Abstract use
was authorised by the author on 2026-09-30, provided the quantities are labelled exploratory.

Nothing is estimated here. Values are copied from the probe output, sign-flipped where stated, or summarised (min,
max, counts).

Provenance: recent_probe.json records its inputs as {path: sha256 prefix}, a format make_numbers.py does not follow.
So this result lists those data files directly as its inputs, after checking that their current sha256 prefixes
equal the recorded ones; a stale probe output stops the run. The probe JSON's own hash is kept in 'extra'.

Usage: .venv\\Scripts\\python.exe analysis\\probe_numbers.py --probe analysis/outputs/recent_probe.json
           --out analysis/outputs/probe.json
"""
from __future__ import annotations

import _env  # noqa: F401

import argparse
import hashlib
import json
from pathlib import Path

from common import ROOT, num, rel, write_result

TAG = "EXPLORATORY (not pre-registered): "
SCRATCH = "analysis/probe/"


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "missing"


def probe_inputs(pj: dict) -> dict:
    """All inputs recent_probe.json recorded: repo data files plus the optional scratch tables."""
    rec = dict(pj["inputs"])
    for block in ("q3b_extra_events", "q5_audio"):
        rec.update({SCRATCH + k: v for k, v in (pj.get(block, {}).get("inputs") or {}).items()})
    return rec


def build(pj: dict) -> dict:
    n = {}
    q1, q2, q3 = pj["q1_shape"], pj["q2_lanes"], pj["q3_rounds"]
    q3b, ex, q4 = pj["q3b_location_day"], pj["q3b_extra_events"], pj["q4_same_athletes"]
    # 1. same athletes: home-straight start minus 200 m start (probe stores 200 m minus straight)
    wa = q4["within_athlete_200m_minus_straight_ms"]
    w25 = wa["WCH2025"]
    other = {k: round(-v["mean"], 2) for k, v in wa.items() if k != "WCH2025"}
    lo_c, hi_c = min(other, key=other.get), max(other, key=other.get)
    n["wch2025_straight_minus_200m_same_athlete_ms"] = num(
        round(-w25["mean"], 2), ci=(round(-w25["ci"][1], 2), round(-w25["ci"][0], 2)), unit="ms",
        desc=TAG + "the same athletes' RT on the home-straight start minus their RT on the 200 m start at WCH2025 "
                   "(sign-flipped from the probe's 200 m minus straight; positive = straight start slower)",
        n_athletes=w25["n"])
    for key, c in (("straight_minus_200m_same_athlete_other_min_ms", lo_c),
                   ("straight_minus_200m_same_athlete_other_max_ms", hi_c)):
        n[key] = num(other[c], ci=(round(-wa[c]["ci"][1], 2), round(-wa[c]["ci"][0], 2)), unit="ms",
                     desc=TAG + f"{'smallest' if c == lo_c else 'largest'} same-athlete straight-minus-200 m difference "
                                f"among the other {len(other)} championships with such athletes",
                     champ=c, n_athletes=wa[c]["n"], n_other_champs=len(other))
    # 2. lane gradient on the home-straight start at WCH2025, and the days those starts were run
    s = q2["rt_slopes"]["WCH2025|straight"]
    days = ex["WCH2025_sprint_dates"]["straight"]
    rest = {k: v["slope_ms_per_lane"] for k, v in q2["rt_slopes"].items() if k != "WCH2025|straight"}
    nxt = max(rest, key=rest.get)
    n["wch2025_straight_lane_gradient_ms_per_lane"] = num(
        s["slope_ms_per_lane"], ci=tuple(s["ci"]), unit="ms per lane",
        desc=TAG + "RT gradient across lanes on the home-straight start at WCH2025 (outer lanes slower), within race",
        n_starts=s["n"], first_day=days[0], last_day=days[-1], first_day_of_month=int(days[0][-2:]),
        last_day_of_month=int(days[-1][-2:]), n_days=len(days), next_largest=rest[nxt], next_largest_cell=nxt)
    oi = q2["WCH2025_straight"]
    n["wch2025_outer_minus_inner_lanes_ms"] = num(
        oi["outer7_9_minus_inner1_5_ms"], ci=tuple(oi["ci"]), unit="ms",
        desc=TAG + "WCH2025 home-straight start: lanes 7-9 minus lanes 1-5, athlete-adjusted RT",
        n_outer=oi["n_outer"], n_inner=oi["n_inner"])
    # 3. WCH2022 fast at every start type, round and day
    c = q1["changes"]["WCH2022->WCH2023|all|adj"]
    n["wch2022_to_2023_median_minus_p5_shift_ms"] = num(
        c["dq50_minus_dq5"], ci=tuple(c["dq50_minus_dq5_ci"]), unit="ms",
        desc=TAG + "WCH2022 to WCH2023: change of the athlete-adjusted median RT minus change of its 5th percentile "
                   "(0 = the whole distribution shifted uniformly)",
        p5_change_ms=c["dq"][0], median_change_ms=c["dq"][2], p95_change_ms=c["dq"][4])
    rounds = {rd: q3["change_by_round"][f"{rd}|WCH2023-WCH2022"] for rd in ("R1", "SF", "F")}
    n["wch2022_faster_rounds"] = num(
        int(sum(v[1] > 0 for v in rounds.values())),
        desc=TAG + "rounds (first round, semi-final, final) in which WCH2023 minus WCH2022 is positive with a CI "
                   "excluding 0, i.e. WCH2022 faster",
        n_rounds=len(rounds), **{f"{rd}_change_ms": v[0] for rd, v in rounds.items()})
    starts = {loc: q1["changes"][f"WCH2022->WCH2023|{loc}|adj"] for loc in ("straight", "200m")}
    n["wch2022_faster_start_types"] = num(
        int(sum(v["dq_ci"][2][0] > 0 for v in starts.values())),
        desc=TAG + "start types (home straight, 200 m) whose athlete-adjusted median RT rose from WCH2022 to WCH2023 "
                   "with a CI excluding 0, i.e. WCH2022 faster",
        n_start_types=len(starts), **{f"{loc}_median_change_ms": v["dq"][2] for loc, v in starts.items()})
    d22, d23 = q3b["day_timeline_adj"]["WCH2022"], q3b["day_timeline_adj"]["WCH2023"]
    min23 = min(v["adj_mean"] for v in d23.values())
    n["wch2022_days_faster_than_every_2023_day"] = num(
        int(sum(v["adj_mean"] < min23 for v in d22.values())),
        desc=TAG + "WCH2022 competition days whose athlete-adjusted mean RT is below that of every WCH2023 day",
        n_days=len(d22), max_2022_day_ms=max(v["adj_mean"] for v in d22.values()), min_2023_day_ms=min23)
    # 4. the same athletes across championships
    for pair, key in (("WCH2022->WCH2023", "same_athletes_2022_to_2023_change_ms"),
                      ("WCH2023->WCH2025", "same_athletes_2023_to_2025_change_ms")):
        pc = q4["panel_change_ms"][pair]
        n[key] = num(pc["mean"], ci=tuple(pc["ci"]), unit="ms",
                     desc=TAG + f"mean change in RT of the same athletes from {pair.replace('->', ' to ')} (athletes with "
                                f"valid starts at all three recent World Championships)",
                     n_athletes=q4["n_panel"], median_ms=pc["median"], share_slower=pc["share_slower"])
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pj_path = Path(a.probe)
    pj = json.loads(pj_path.read_text(encoding="utf-8"))
    rec = probe_inputs(pj)
    stale = [f"{p}: recorded {s_}, now {sha12(ROOT / p)}" for p, s_ in rec.items() if sha12(ROOT / p) != s_]
    if stale:
        raise SystemExit("recent_probe.json is stale relative to its inputs; rerun analysis/recent_probe.py:\n  "
                         + "\n  ".join(stale))
    numbers = build(pj)
    extra = {"status": TAG.rstrip(": "), "probe_status": pj.get("status"),
             "abstract_use": "authorised by the author on 2026-09-30, labelled EXPLORATORY",
             "probe_json": {"path": rel(pj_path), "sha256_12": sha12(pj_path)}}
    p = write_result(a.out, "probe", numbers, [ROOT / k for k in rec], False, extra=extra, seed=pj.get("seed"))
    for k, v in numbers.items():
        print(f"{k:48s} {v.get('value')!s:>10} {v.get('ci95', '')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
