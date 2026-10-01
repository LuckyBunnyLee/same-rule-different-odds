"""Where does the Seiko RT detection mark sit on the displayed force trace, per championship?

Input: data/derived/rt_waveform_lanes.csv (data pipeline's OCR / pixel reading of the start waveform
images): red_minus_onset_ms = position of the red RT-detection line minus the 5%-of-peak onset of the
displayed force rise; onset_5pct_s = that onset relative to the gun. If the detection threshold had
changed between championships, the detection line would sit at a different point of the rise.

Output: per-championship median / IQR / share at the modal offset, force-onset medians, and
Kruskal-Wallis tests across championships.

Usage: .venv\\Scripts\\python.exe analysis\\detector_check.py --out analysis/outputs/detector.json
"""
from __future__ import annotations

import _env  # noqa: F401

import argparse

import numpy as np
import pandas as pd
from scipy import stats

from common import add_common_args, data_path, num, resolve_out, write_result


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    args = ap.parse_args()
    out = resolve_out(args, "detector")
    p = data_path("rt_waveform_lanes.csv", args.mock)
    d = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    d = d[d["red_minus_onset_ms"].notna() & d["onset_5pct_s"].notna()].copy()
    d["comp_year"] = d["race_id"].str.split("-").str[0]
    mode = float(d["red_minus_onset_ms"].round(1).mode().iloc[0])
    numbers, rows = {}, []
    for cy, g in d.groupby("comp_year", sort=True):
        x = g["red_minus_onset_ms"].to_numpy(float)
        on = g["onset_5pct_s"].to_numpy(float) * 1000
        row = {"comp_year": cy, "n_lanes": int(len(g)), "median_ms": float(np.median(x)),
               "q25_ms": float(np.percentile(x, 25)), "q75_ms": float(np.percentile(x, 75)),
               "share_at_mode": float(np.mean(np.abs(x - mode) <= 0.5)),
               "force_onset_median_ms": float(np.median(on))}
        rows.append(row)
        numbers[f"detector_offset_median_{cy}_ms"] = num(
            round(row["median_ms"], 2), unit="ms", n_lanes=row["n_lanes"],
            iqr=[round(row["q25_ms"], 2), round(row["q75_ms"], 2)],
            share_at_mode=float(f"{row['share_at_mode']:.4g}"),
            desc=f"median position of the Seiko RT-detection line relative to the 5%-of-peak onset of the displayed "
                 f"force rise, {cy}")
        numbers[f"force_onset_median_{cy}_ms"] = num(
            round(row["force_onset_median_ms"], 1), unit="ms",
            desc=f"median 5%-of-peak force onset after the gun on the displayed trace, {cy}")
    tab = pd.DataFrame(rows)
    groups = [g["red_minus_onset_ms"].to_numpy(float) for _, g in d.groupby("comp_year", sort=True)]
    groups_on = [g["onset_5pct_s"].to_numpy(float) for _, g in d.groupby("comp_year", sort=True)]
    numbers["detector_mode_ms"] = num(mode, unit="ms", desc="modal detection-line offset over all lanes")
    numbers["detector_share_at_mode_all"] = num(float(f"{np.mean(np.abs(d['red_minus_onset_ms'] - mode) <= 0.5):.4g}"),
                                                desc="share of all lanes whose detection line sits within 0.5 ms of the modal offset",
                                                n_lanes=int(len(d)))
    if len(groups) >= 2:
        h, pv = stats.kruskal(*groups)
        numbers["detector_offset_kw_p"] = num(float(f"{pv:.3g}"), desc="Kruskal-Wallis test: detection-line offset "
                                                                        "differs between championships", H=float(f"{h:.4g}"))
        h2, pv2 = stats.kruskal(*groups_on)
        numbers["force_onset_kw_p"] = num(float(f"{pv2:.3g}"), desc="Kruskal-Wallis test: force onset after the gun "
                                                                     "differs between championships", H=float(f"{h2:.4g}"))
    numbers["detector_median_range_ms"] = num(round(float(tab["median_ms"].max() - tab["median_ms"].min()), 2), unit="ms",
                                              desc="range of the per-championship median detection-line offsets")
    numbers["force_onset_median_range_ms"] = num(round(float(tab["force_onset_median_ms"].max() -
                                                             tab["force_onset_median_ms"].min()), 1), unit="ms",
                                                 desc="range of the per-championship median force onsets after the gun")
    res = write_result(out, "detector", numbers, [p], args.mock, tables={"by_comp": tab}, seed=args.seed)
    print(tab.to_string(index=False))
    for k, v in numbers.items():
        print(f"{k:40s} {v['value']}")
    print(f"wrote {res}")


if __name__ == "__main__":
    main()
