"""Regression tests for the false-start classifier in analysis/common.normalize_rt (fixed 2026-09-30).

Bug: the label regex 'false.?start' matched inside the note "(not a false start)", so 33 hurdle and lane DQs were
counted as false starts and their legal RTs left the valid set; and the Fiore et al. file's RT 0.000 missing-value
placeholders (DNS rows, and DQ rows whose negative RT was dropped) counted as false starts "with an RT".

1. Synthetic rows (rt_athletes-like and rt_fiore-like) are classified as the fix intends.
2. On the current data version: no "not a false start" row is a false start, no RT is 0.000, and the counts equal the
   guard-band analysis's independent recount: 37 false starts, 27 with a
   measured RT, 6,408 valid starts. Skipped if the data files change (the counts are pinned to their hashes).

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_common_fs.py   (or pytest)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (DERIVED, attach_races, dedupe_sources, load_races, load_rt, normalize_rt,  # noqa: E402
                    valid_rt_mask)

PINNED = {"rt_athletes.csv": "af44975b3e1a", "rt_fiore.csv": "dff5cb184d1b"}   # data versions the counts refer to


def test_synthetic_athletes():
    d = pd.DataFrame({
        "race_id": ["WCH2015-110mH-M-R1-H1"] * 5,
        "athlete": list("ABCDE"), "rt_s": [0.160, 0.085, np.nan, 0.140, 0.189],
        "status": ["DQ", "FS", "DQ", "OK", "DQ"],
        "notes": ["official PDF: DQ 168.7(b) (not a false start)", "official PDF: TR16.8", "official PDF: DQ TR16.8",
                  "", "official PDF: DQ 163.3(a) (NOT A FALSE START)"]})
    o = normalize_rt(d, "rt_athletes")
    assert list(o["is_fs"]) == [False, True, True, False, False], list(o["is_fs"])
    v = valid_rt_mask(o)
    assert list(v) == [True, False, False, True, True], list(v)       # non-start DQs keep their legal RT
    print("[ok] '(not a false start)' DQs keep their legal RT; TR16.8 rows stay false starts")


def test_synthetic_fiore():
    d = pd.DataFrame({"Year": [1999] * 5, "Event": ["100 Dash"] * 5, "Gender": ["M"] * 5, "Stage": ["S"] * 5,
                      "Batch": [1] * 5, "TotalTime": ["DNS", "DQ", "10.21", "10.05", "D"],
                      "ReactionTime": [0.0, 0.0, 0.095, 0.150, 0.0]})
    o = normalize_rt(d, "rt_fiore")
    assert o["rt_s"].isna().tolist() == [True, True, False, False, True]          # 0.000 is missing, not measured
    assert list(o["is_dns"]) == [True, False, False, False, False]
    assert list(o["is_fs"]) == [False, True, True, False, False], list(o["is_fs"])
    started = o["rt_s"].notna() | o["is_fs"]
    assert list(started) == [False, True, True, True, False]
    print("[ok] Fiore RT 0.000: DNS -> not a start, DQ -> false start without a measured RT")


def test_real_data_counts():
    for f, h in PINNED.items():
        if hashlib.sha256((DERIVED / f).read_bytes()).hexdigest()[:12] != h:
            print(f"[skip] {f} changed; the pinned counts refer to {h}")
            return
    rt, _ = load_rt(False)
    races, _ = load_races(False)
    rt = attach_races(dedupe_sources(rt), races)
    raw = pd.read_csv(DERIVED / "rt_athletes.csv", low_memory=False)
    n_note = int(raw["notes"].fillna("").str.contains("not a false start", case=False).sum())
    assert n_note == 33
    started = rt[rt["rt_s"].notna() | rt["is_fs"]]
    fs = started[started["is_fs"].astype(bool)]
    assert not (rt["rt_s"] == 0).any()
    assert len(fs) == 37 and int(fs["rt_s"].notna().sum()) == 27, (len(fs), int(fs["rt_s"].notna().sum()))
    assert int(valid_rt_mask(rt).sum()) == 6408
    near = fs[fs["rt_s"].between(0.090, 0.0999)]
    assert len(near) == 4 and set(near["comp_year"]) == {"WCH2022"}
    print("[ok] real data: 37 false starts (27 with a measured RT), 6,408 valid starts, 4 near-threshold at WCH2022")


if __name__ == "__main__":
    test_synthetic_athletes()
    test_synthetic_fiore()
    test_real_data_counts()
