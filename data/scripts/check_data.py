"""Invariant checks on the RT tables; exits non-zero if any invariant fails.

  .venv/Scripts/python.exe data/scripts/check_data.py --athletes data/derived/rt_athletes.csv
      --races data/derived/races.csv --waveform data/derived/rt_waveform.csv

Guards the claims the README makes about the data: key format and uniqueness,
athlete rows <-> race rows consistency, status vocabulary, RT range, holds only
where validated, and false starts implying a restart where the Seiko attempt is known.
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

RID = (r"^(WCH|OG|WIC)\d{4}-(100m|100mH|110mH|200m|60m|60mH)-(M|W)-"
       r"(PR|R1|RP|R2|SF|F)-H\d+$")
STATUS = {"OK", "FS", "DQ", "DQ-post", "DNF", "DNS", "NR"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--athletes", required=True)
    ap.add_argument("--races", required=True)
    ap.add_argument("--waveform", required=True)
    a = ap.parse_args(argv)
    ath = pd.read_csv(a.athletes)
    races = pd.read_csv(a.races)
    wf = pd.read_csv(a.waveform)
    fails = []

    def check(ok, msg):
        if not ok:
            fails.append(msg)

    check(ath["race_id"].str.match(RID).all(), "rt_athletes: malformed race_id")
    check(races["race_id"].str.match(RID).all(), "races: malformed race_id")
    check(races["race_id"].is_unique, "races: duplicate race_id")
    keyed = ath.dropna(subset=["lane"])
    check(not keyed.duplicated(["race_id", "lane"]).any(), "rt_athletes: duplicate race_id+lane")
    check(set(ath["race_id"]) == set(races["race_id"]), "race_id sets differ between tables")
    n = ath.groupby("race_id").size()
    check((races.set_index("race_id")["n_athletes"] == n.reindex(races["race_id"]).values).all(),
          "races.n_athletes != athlete rows")
    check(ath["status"].isin(STATUS).all(), f"unknown status {set(ath['status']) - STATUS}")
    rt = ath["rt_s"].dropna()
    check(rt.between(-1, 1).all(), "rt_s outside [-1, 1] s")
    check(not (ath["rt_s"].lt(0.100) & ~ath["status"].eq("FS")).any(),
          "RT < 0.100 s on a row not labelled FS")
    check(not (races["wf_ready_time_s"].notna() & ~races["wf_ok"].fillna(False).astype(bool)).any(),
          "races: hold filled where waveform not validated")
    check(wf.loc[wf["wf_ok"], "wf_ready_time_s"].between(0.5, 6.0).all(), "validated hold out of range")
    fs_known = races[(races["n_fs"] > 0) & races["wf_attempt"].notna()]
    check((fs_known["wf_attempt"] >= 2).all(), "false start but Seiko attempt 1")
    check(ath.loc[ath["status"].eq("FS"), "fs_evidence"].fillna("").ne("").all(),
          "FS row without fs_evidence")
    for f in fails:
        print("FAIL", f)
    print(f"{len(fails)} invariant(s) failed" if fails else "all invariants hold")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
