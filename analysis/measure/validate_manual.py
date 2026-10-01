"""Agreement between the automated pipeline and blind manual readings of annotation sheets (real broadcasts).

Usage:
  python analysis/measure/validate_manual.py --manual analysis/measure/manual_annotations.csv \
      --auto analysis/measure/results/starts_measured.csv --split dev \
      --out analysis/measure/results/auto_vs_manual_dev.json

--split selects which annotation rows to score: 'dev' = sheets used while developing the detector (in-sample),
'heldout' = sheets annotated after the detector was frozen. The split of each sheet is in the manual file
(column `split`, default 'dev' when absent). Only starts marked clean=1 are scored for the "Set" timings.
"""
import argparse
import json

import numpy as np
import pandas as pd


def st(e):
    e = np.asarray(e, float)
    e = e[np.isfinite(e)]
    if len(e) == 0:
        return {"n": 0}
    return {"n": int(len(e)), "bias_ms": round(float(e.mean()), 2), "mae_ms": round(float(np.abs(e).mean()), 2),
            "median_ms": round(float(np.median(e)), 2), "sd_ms": round(float(e.std(ddof=1)), 2) if len(e) > 1 else None,
            "max_abs_ms": round(float(np.abs(e).max()), 2),
            "within_10ms": round(float((np.abs(e) <= 10).mean()), 4), "within_20ms": round(float((np.abs(e) <= 20).mean()), 4),
            "within_40ms": round(float((np.abs(e) <= 40).mean()), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", required=True)
    ap.add_argument("--auto", required=True)
    ap.add_argument("--split", required=True, choices=["dev", "heldout", "all"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = pd.read_csv(a.manual)
    if "split" not in m.columns:
        m["split"] = "dev"
    m["split"] = m["split"].fillna("dev")
    if a.split != "all":
        m = m[m.split == a.split]
    m = m[m.attempt_status != "not_a_start"]
    au = pd.read_csv(a.auto)
    d = au.merge(m[["race_id", "attempt", "t_set_on", "t_voicing_end", "t_gun", "clean"]], on=["race_id", "attempt"],
                 suffixes=("", "_man"))
    d["e_gun_ms"] = (d.t_gun - d.t_gun_man) * 1000
    d["e_on_ms"] = (d.t_set_on - d.t_set_on_man) * 1000
    d["e_off_ms"] = (d.t_set_off - d.t_voicing_end) * 1000
    d["e_fp_on_ms"] = ((d.t_gun - d.t_set_on) - (d.t_gun_man - d.t_set_on_man)) * 1000
    c = d[d.clean == 1]
    res = {"split": a.split, "description": "automated minus manual (ms), real broadcast audio",
           "n_starts_matched": int(len(d)), "n_clean": int(len(c)),
           "gun_onset": st(d.e_gun_ms), "set_onset_clean": st(c.e_on_ms), "fp_onset_clean": st(c.e_fp_on_ms),
           "set_offset_vs_voicing_end_clean": st(c.e_off_ms),
           "failures": [{"race_id": r.race_id, "attempt": int(r.attempt), "fail": r.fail}
                        for _, r in au.iterrows() if isinstance(r.get("fail"), str) and r.fail],
           "rows": [{"race_id": r.race_id, "attempt": int(r.attempt), "clean": int(r.clean),
                     "e_gun_ms": round(float(r.e_gun_ms), 2) if np.isfinite(r.e_gun_ms) else None,
                     "e_on_ms": round(float(r.e_on_ms), 2) if np.isfinite(r.e_on_ms) else None,
                     "e_off_ms": round(float(r.e_off_ms), 2) if np.isfinite(r.e_off_ms) else None,
                     "qc_flag": r.qc_flag} for _, r in d.sort_values(["race_id", "attempt"]).iterrows()]}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
