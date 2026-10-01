"""Summarise the SYNTHETIC benchmark (simulated clips) and derive the uncertainty calibration.

Usage:
  python analysis/measure/summarize_benchmark.py --trials analysis/measure/results/benchmark_synthetic_trials.csv \
      --out analysis/measure/results/benchmark_synthetic_summary.json
  python analysis/measure/summarize_benchmark.py --trials analysis/measure/results/benchmark_synthetic_trials.csv \
      --calibration-only --out analysis/measure/calibration_synthetic.json

Gross error: no measurement, |gun error| > 50 ms, or |set-onset error| > 250 ms (a wrong event was chosen).
Accuracy statistics (bias, MAE, shares within +-20/+-40 ms) are reported over all trials (gross errors count as
misses in the 'within' shares) and over non-gross trials. 'Realistic' backgrounds = real set-to-gun hold audio
(hold) and stationary pink noise; 'stress' = race-period crowd noise and pre-race commentary.
Calibration: 68th percentile of |set-onset error| (and |offset error| vs the -20 dB word end) among non-gross
trials in bins of the detector-measured set SNR, used by fpmeasure.uncertainty().
"""
import argparse
import json

import numpy as np
import pandas as pd

EDGES = [-99, 12, 20, 30, 999]


def acc(d, col):
    e = d[col]
    ok = ~d.gross
    eo = e[ok]
    n = len(d)
    return {"n": int(n), "detected": round(float(d.detected.mean()), 4) if n else None,
            "gross": round(float(d.gross.mean()), 4) if n else None,
            "bias_ms": round(float(eo.mean()), 2) if len(eo) else None,
            "mae_ms": round(float(eo.abs().mean()), 2) if len(eo) else None,
            "median_abs_ms": round(float(eo.abs().median()), 2) if len(eo) else None,
            "within_20ms": round(float(((e.abs() <= 20) & ok).mean()), 4) if n else None,
            "within_40ms": round(float(((e.abs() <= 40) & ok).mean()), 4) if n else None,
            "within_20ms_nongross": round(float((eo.abs() <= 20).mean()), 4) if len(eo) else None,
            "within_40ms_nongross": round(float((eo.abs() <= 40).mean()), 4) if len(eo) else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", required=True)
    ap.add_argument("--calibration-only", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = pd.read_csv(a.trials)
    d["e_gun_ms"] = (d.det_gun - d.true_gun) * 1000
    d["e_on_ms"] = (d.det_set_on - d.true_set_on) * 1000
    d["e_off20_ms"] = (d.det_set_off - d.true_set_off20) * 1000
    d["e_fp_ms"] = (d.det_fp_on - d.true_fp_on) * 1000
    d["e_fpoff_ms"] = ((d.det_gun - d.det_set_off) - (d.true_gun - d.true_set_off20)) * 1000
    d["gross"] = (d.detected != 1) | d.det_fp_on.isna() | (d.e_gun_ms.abs() > 50) | (d.e_on_ms.abs() > 250)
    d["qc_ok"] = d.qc_flag.fillna("") == "ok"
    ng = d[~d.gross]
    cal = {"snr_edges": EDGES, "set_on": [], "set_off": [], "n_per_bin": [], "gun": None,
           "source": "SYNTHETIC benchmark calibration (simulated clips): 68th pct |error| by measured set SNR"}
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        b = ng[(ng.det_set_snr >= lo) & (ng.det_set_snr < hi)]
        q_on = float(np.percentile(b.e_on_ms.abs(), 68)) / 1000 if len(b) >= 5 else 0.06
        q_off = float(np.percentile(b.e_off20_ms.dropna().abs(), 68)) / 1000 if b.e_off20_ms.notna().sum() >= 5 else 0.08
        cal["set_on"].append(round(max(q_on, 0.005), 4))
        cal["set_off"].append(round(max(q_off, 0.01), 4))
        cal["n_per_bin"].append(int(len(b)))
    cal["gun"] = round(max(float(np.percentile(ng.e_gun_ms.abs(), 68)) / 1000, 0.001), 4)
    if a.calibration_only:
        json.dump(cal, open(a.out, "w"), indent=1)
        open(a.out, "a").write("\n")
        return
    realistic = d[d.noise_type.isin(["hold", "pink"])]
    stress = d[d.noise_type.isin(["race", "commentary"])]
    table = []
    for (nt, snr), g in d.groupby(["noise_type", "snr_db"], sort=True):
        r = acc(g, "e_fp_ms")
        table.append({"condition": f"{nt}, SNR {snr:+.0f} dB", "noise_type": nt, "snr_db": snr, **r})
    res = {
        "description": "SYNTHETIC benchmark (simulated start clips; real broadcast backgrounds or pink noise; SAPI TTS "
                       "'Set'; synthetic gun, reverb, crowd surge; Opus/AAC round trip). Errors = detected - truth.",
        "n_trials": int(len(d)),
        "overall": {"fp_onset": acc(d, "e_fp_ms"), "set_onset": acc(d, "e_on_ms"), "gun": acc(d, "e_gun_ms")},
        "realistic_backgrounds": {"fp_onset": acc(realistic, "e_fp_ms"), "set_onset": acc(realistic, "e_on_ms"),
                                  "gun": acc(realistic, "e_gun_ms"), "fp_offset_vs_minus20dB_end": acc(realistic, "e_fpoff_ms")},
        "stress_backgrounds": {"fp_onset": acc(stress, "e_fp_ms"), "gun": acc(stress, "e_gun_ms")},
        "realistic_snr_ge_10": {"fp_onset": acc(realistic[realistic.snr_db >= 10], "e_fp_ms")},
        "qc": {"share_qc_ok": round(float(d.qc_ok.mean()), 4),
               "gross_rate_if_qc_ok": round(float(d[d.qc_ok].gross.mean()), 4) if d.qc_ok.any() else None,
               "gross_rate_if_flagged": round(float(d[~d.qc_ok].gross.mean()), 4) if (~d.qc_ok).any() else None,
               "fp_onset_if_qc_ok": acc(d[d.qc_ok], "e_fp_ms")},
        "table": table,
        "calibration": cal,
    }
    ro = res["realistic_backgrounds"]["fp_onset"]
    r10 = res["realistic_snr_ge_10"]["fp_onset"]
    res["headline"] = {"n_trials": res["n_trials"],
                       "realistic_n": ro["n"], "realistic_gross": ro["gross"], "realistic_fp_bias_ms": ro["bias_ms"],
                       "realistic_fp_mae_ms": ro["mae_ms"], "realistic_within_20ms": ro["within_20ms"],
                       "realistic_within_40ms": ro["within_40ms"],
                       "realistic_snr_ge_10_n": r10["n"], "realistic_snr_ge_10_gross": r10["gross"],
                       "realistic_snr_ge_10_fp_bias_ms": r10["bias_ms"], "realistic_snr_ge_10_fp_mae_ms": r10["mae_ms"],
                       "realistic_snr_ge_10_within_20ms": r10["within_20ms"], "realistic_snr_ge_10_within_40ms": r10["within_40ms"],
                       "stress_gross": res["stress_backgrounds"]["fp_onset"]["gross"],
                       "gun_mae_ms_nongross": res["overall"]["gun"]["mae_ms"],
                       "qc_ok_share": res["qc"]["share_qc_ok"], "gross_rate_if_qc_ok": res["qc"]["gross_rate_if_qc_ok"]}
    json.dump(res, open(a.out, "w"), indent=1)
    open(a.out, "a").write("\n")


if __name__ == "__main__":
    main()
