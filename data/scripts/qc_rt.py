"""Quality checks and coverage for the RT tables.

--report flags    -> one row per flagged item (rt_qc_flags.csv)
--report coverage -> races / starts / RTs / validated Seiko holds per comp x event x sex
                     (rt_coverage.csv); --markdown also prints it as a Markdown table.

Checks (level, check):
  race    lanes_gt_9 / lanes_lt_5   athletes on the start list outside 5..9
  race    dup_lane                  two athletes with the same lane in one race
  race    lane_out_of_range         lane not in 1..9
  race    fs_without_extra_attempt  a false start but the Seiko waveform says attempt 1
  race    extra_attempt_without_fs  waveform attempt >= 2 but nobody DQ'd for a false start
  athlete rt_outside_0.08_0.40      RT outside the plausibility band (FS rows included)
  athlete rt_lt_0.100_not_fs        RT < 0.100 s without a false-start label
  athlete missing_rt                started (not DNS) but no RT
  athlete dup_athlete_in_race       same WA athlete id twice in one race
  athlete source_disagreement       notes record a site/PDF disagreement

Usage:
  data/scripts/qc_rt.py --report flags --athletes data/derived/rt_athletes.csv
      --races data/derived/races.csv --out data/derived/rt_qc_flags.csv
  data/scripts/qc_rt.py --report coverage --athletes data/derived/rt_athletes.csv
      --races data/derived/races.csv --out data/derived/rt_coverage.csv [--markdown]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

EV_ORDER = {"100m": 0, "100mH": 1, "110mH": 2, "200m": 3, "60m": 4, "60mH": 5}


def flags(ath: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
    out = []

    def add(level, check, rid, lane=None, athlete=None, value=None, detail=""):
        out.append(dict(level=level, check=check, race_id=rid, lane=lane, athlete=athlete,
                        value=value, detail=detail))

    for _, r in races.iterrows():
        if r["n_athletes"] > 9:
            add("race", "lanes_gt_9", r["race_id"], value=r["n_athletes"])
        if r["n_athletes"] < 5:
            add("race", "lanes_lt_5", r["race_id"], value=r["n_athletes"])
        att = r.get("wf_attempt")
        if pd.notna(att):
            if r["n_fs"] > 0 and att < 2:
                add("race", "fs_without_extra_attempt", r["race_id"], value=int(att),
                    detail=str(r.get("dq_detail", "")))
            if r["n_fs"] == 0 and att >= 2:
                yc = r.get("card_detail")
                add("race", "extra_attempt_without_fs", r["race_id"], value=int(att),
                    detail=(f"aborted start(s), no false-start DQ; card(s): {yc}"
                            if isinstance(yc, str) and yc else
                            "aborted start(s) with no false-start DQ or card (recall / unfair start)"))
    lanes = ath.dropna(subset=["lane"])
    for (rid, ln), g in lanes.groupby(["race_id", "lane"]):
        if len(g) > 1:
            add("race", "dup_lane", rid, lane=int(ln), detail="; ".join(g["athlete"]))
    for _, a in lanes[~lanes["lane"].between(1, 9)].iterrows():
        add("race", "lane_out_of_range", a["race_id"], lane=a["lane"], athlete=a["athlete"])
    for _, a in ath.iterrows():
        rt, st = a["rt_s"], a["status"]
        if pd.notna(rt) and not (0.08 <= rt <= 0.40):
            add("athlete", "rt_outside_0.08_0.40", a["race_id"], a["lane"], a["athlete"], rt, st)
        if pd.notna(rt) and rt < 0.100 and st != "FS":
            add("athlete", "rt_lt_0.100_not_fs", a["race_id"], a["lane"], a["athlete"], rt, st)
        if pd.isna(rt) and st not in ("DNS", "NR"):
            add("athlete", "missing_rt", a["race_id"], a["lane"], a["athlete"], None,
                f"status {st}; {a.get('fs_evidence') or ''}".strip("; "))
        note = str(a.get("notes") or "")
        if any(k in note for k in ("replaced by official PDF", "PDF name at this lane",
                                   "DQ on WA site but ranked", "competitorId differs")):
            add("athlete", "source_disagreement", a["race_id"], a["lane"], a["athlete"], None, note)
    for (rid, aid), g in ath.dropna(subset=["athlete_id"]).groupby(["race_id", "athlete_id"]):
        if len(g) > 1:
            add("athlete", "dup_athlete_in_race", rid, athlete=g["athlete"].iloc[0], value=len(g))
    df = pd.DataFrame(out, columns=["level", "check", "race_id", "lane", "athlete", "value", "detail"])
    df["lane"] = pd.array(df["lane"], dtype="Int64")
    return df.sort_values(["level", "check", "race_id", "lane"], kind="stable")


def coverage(ath: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
    races = races.copy()
    races["fp"] = races["wf_ready_time_s"].notna() if "wf_ready_time_s" in races else False
    rg = races.groupby(["comp", "year", "event", "sex"]).agg(
        races=("race_id", "size"), rounds=("round", lambda s: "/".join(
            sorted(s.unique(), key=["PR", "R1", "RP", "R2", "SF", "F"].index))),
        races_with_seiko_hold=("fp", "sum"), false_starts=("n_fs", "sum"))
    ag = ath.groupby(["comp", "year", "event", "sex"]).agg(
        starts=("race_id", "size"), starts_with_rt=("rt_s", lambda s: int(s.notna().sum())))
    fp_races = set(races.loc[races["fp"], "race_id"])
    ok = ath[ath["race_id"].isin(fp_races) & ath["rt_s"].notna() & ath["status"].ne("FS")]
    rt_fp = ok.groupby(["comp", "year", "event", "sex"]).size().rename("rts_with_seiko_hold")
    cov = rg.join(ag).join(rt_fp).fillna({"rts_with_seiko_hold": 0}).reset_index()
    cov["rts_with_seiko_hold"] = cov["rts_with_seiko_hold"].astype(int)
    cov["_e"] = cov["event"].map(EV_ORDER)
    cov = cov.sort_values(["comp", "year", "_e", "sex"], ascending=[False, False, True, True])
    cov = cov.drop(columns="_e")
    total = cov.drop(columns=["comp", "year", "event", "sex", "rounds"]).sum()
    tot = pd.DataFrame([{"comp": "ALL", "year": "", "event": "", "sex": "", "rounds": "",
                         **total.to_dict()}])
    return pd.concat([cov, tot], ignore_index=True)


def to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", choices=["flags", "coverage"], required=True)
    ap.add_argument("--athletes", required=True)
    ap.add_argument("--races", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args(argv)
    ath = pd.read_csv(a.athletes)
    races = pd.read_csv(a.races)
    df = flags(ath, races) if a.report == "flags" else coverage(ath, races)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False, encoding="utf-8", lineterminator="\n")
    if a.report == "flags":
        print(df.groupby(["level", "check"]).size().to_string())
    elif a.markdown:
        print(to_markdown(df))
    print(f"wrote {a.out} ({len(df)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
