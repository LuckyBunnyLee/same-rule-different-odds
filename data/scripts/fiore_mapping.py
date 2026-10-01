"""Our derived columns of rt_fiore.csv, without the columns copied from Fiore et al.'s rxntime.csv.

rt_fiore.csv = the seven source columns of github.com/ofiore/Thesis Data/rxntime.csv (Year, Stage, TotalTime,
ReactionTime, Gender, Batch, Event; not redistributed here, since that repository has no licence) plus columns
computed by data/scripts/build_fiore.py. This script writes only the computed columns, keyed by fiore_row (1-based
data row of rxntime.csv), so the mapping we used can be inspected without the third-party file:

  fiore_row                      row key into rxntime.csv
  comp, year, event, sex,        recodes of Year / Event / Gender / Stage to our keys
  round_guess
  race_id                        our race key, from matching (result, RT) pairs against World Athletics results
  athlete, lane                  the matched athlete and lane (from data/derived/rt_athletes.csv)
  match_pairs, batch_n,          batch-to-race matching diagnostics
  runner_up_pairs, map_note,
  row_note
  source_url                     the pinned source file

Usage: python data/scripts/fiore_mapping.py --fiore-derived data/derived/rt_fiore.csv
           --out data/derived/rt_fiore_mapping.csv
"""
from __future__ import annotations

import argparse

import pandas as pd

SOURCE_COLS = ["Year", "Stage", "TotalTime", "ReactionTime", "Gender", "Batch", "Event"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fiore-derived", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    df = pd.read_csv(a.fiore_derived, dtype=str, keep_default_na=False)
    missing = [c for c in SOURCE_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"not an rt_fiore.csv: missing {missing}")
    df.drop(columns=SOURCE_COLS).to_csv(a.out, index=False, lineterminator="\n")
    print(f"wrote {a.out} ({len(df)} rows, {df.shape[1] - len(SOURCE_COLS)} columns)")


if __name__ == "__main__":
    main()
