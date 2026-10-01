"""Compare broadcast-audio foreperiods with the official Seiko 'Ready Time' printed on WA start waveforms.

Usage:
  python analysis/measure/validate_seiko.py --manual analysis/measure/manual_annotations.csv \
      --auto analysis/measure/results/starts_measured.csv --waveform data/derived/rt_waveform.csv \
      --out analysis/measure/results/seiko_validation.json

For each valid (final) start attempt with a Seiko Ready Time (wf_ok and matching attempt number):
  d_on   = (gun - set onset)      - ReadyTime
  d_vend = (gun - end of voicing) - ReadyTime
  d_wend = (gun - end of word incl. released /t/) - ReadyTime
Statistics: n, mean (bias), SD, MAE, max |d|, share within +-20/+-40 ms, per-championship means, Pearson r
(Fisher-z 95% CI) and OLS fit of ReadyTime on the broadcast foreperiod. Manual annotations are primary; the
automated pipeline is reported on the same starts. Real broadcast audio only (no simulation).
"""
import argparse
import json
import math

import numpy as np
import pandas as pd


def stats(d):
    d = np.asarray(d, dtype=float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n == 0:
        return {"n": 0}
    return {"n": int(n), "bias_s": round(float(d.mean()), 4), "sd_s": round(float(d.std(ddof=1)), 4) if n > 1 else None,
            "mae_s": round(float(np.abs(d).mean()), 4), "max_abs_s": round(float(np.abs(d).max()), 4),
            "min_s": round(float(d.min()), 4), "max_s": round(float(d.max()), 4),
            "within_20ms": round(float((np.abs(d) <= 0.020).mean()), 4),
            "within_40ms": round(float((np.abs(d) <= 0.040).mean()), 4)}


def corr(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 4:
        return {"n": int(n)}
    r = float(np.corrcoef(x, y)[0, 1])
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    slope, intercept = np.polyfit(x, y, 1)
    return {"n": int(n), "r": round(r, 4), "r_ci95": [round(math.tanh(z - 1.96 * se), 4), round(math.tanh(z + 1.96 * se), 4)],
            "ols_ready_on_fp_slope": round(float(slope), 4), "ols_ready_on_fp_intercept_s": round(float(intercept), 4)}


def by_comp(df, col):
    out = {}
    for comp, g in df.groupby("compyear"):
        s = stats(g[col])
        out[comp] = {k: s.get(k) for k in ("n", "bias_s", "sd_s", "min_s", "max_s")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual", required=True)
    ap.add_argument("--auto", required=True)
    ap.add_argument("--waveform", required=True)
    ap.add_argument("--foreperiods", required=True, help="final dataset (all reviewed starts)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    man = pd.read_csv(a.manual)
    auto = pd.read_csv(a.auto)
    wf = pd.read_csv(a.waveform)[["race_id", "wf_attempt", "wf_ready_time_s", "wf_ok"]]
    man = man[man.attempt_status == "valid"].copy()
    df = man.merge(wf, on="race_id", how="left")
    df["compyear"] = df.race_id.str.split("-").str[0]
    excluded = []
    keep = []
    for _, r in df.iterrows():
        why = None
        if pd.isna(r.wf_ready_time_s) or not bool(r.wf_ok):
            why = "no validated Seiko Ready Time"
        elif int(r.wf_attempt) != int(r.attempt):
            why = f"attempt mismatch (audio attempt {int(r.attempt)} vs waveform attempt {int(r.wf_attempt)})"
        elif int(r.clean) != 1 or pd.isna(r.t_set_on):
            why = "Set command not identifiable in broadcast audio: " + str(r.notes)
        if why:
            excluded.append({"race_id": r.race_id, "attempt": int(r.attempt), "reason": why})
        else:
            keep.append(r)
    k = pd.DataFrame(keep)
    k["fp_on"] = k.t_gun - k.t_set_on
    k["fp_vend"] = k.t_gun - k.t_voicing_end
    k["fp_wend"] = k.t_gun - k.t_word_end
    for c in ("on", "vend", "wend"):
        k[f"d_{c}"] = k[f"fp_{c}"] - k.wf_ready_time_s
    # automated pipeline on the same starts
    au = auto[auto.attempt_status == "valid"][["race_id", "attempt", "fp_on_s", "fp_off_s", "qc_flag"]]
    k = k.merge(au, on=["race_id", "attempt"], how="left")
    k["d_auto_on"] = k.fp_on_s - k.wf_ready_time_s
    k["d_auto_off"] = k.fp_off_s - k.wf_ready_time_s
    # within-championship residual SD (after removing each championship's mean offset)
    k["d_on_demeaned"] = k.d_on - k.groupby("compyear").d_on.transform("mean")
    k["d_vend_demeaned"] = k.d_vend - k.groupby("compyear").d_vend.transform("mean")
    # automated-only comparison over all measured valid starts with a validated Ready Time (larger n; starts the
    # manual reader judged unidentifiable are excluded; split by QC status)
    allauto = auto[(auto.attempt_status == "valid") & auto.fp_on_s.notna()].merge(wf, on="race_id", how="inner")
    allauto = allauto[(allauto.wf_ok.astype(bool)) & (allauto.wf_attempt == allauto.attempt)]
    unident = set(zip(man.race_id[man.clean == 0], man.attempt[man.clean == 0]))
    fpall = pd.read_csv(a.foreperiods)
    unident |= set(zip(fpall.race_id[fpall.foreperiod_s.isna()], fpall.attempt[fpall.foreperiod_s.isna()]))
    allauto = allauto[[(r, a) not in unident for r, a in zip(allauto.race_id, allauto.attempt)]].copy()
    allauto["compyear"] = allauto.race_id.str.split("-").str[0]
    allauto["d"] = allauto.fp_on_s - allauto.wf_ready_time_s
    allauto["d_off"] = allauto.fp_off_s - allauto.wf_ready_time_s
    qc_ok = allauto[allauto.qc_flag == "ok"]
    automated_all = {"n": int(len(allauto)), "onset_minus_ready": stats(allauto.d),
                     "onset_minus_ready_by_championship": by_comp(allauto, "d"),
                     "offset_minus_ready": stats(allauto.d_off),
                     "corr_ready_vs_fp_onset": corr(allauto.fp_on_s, allauto.wf_ready_time_s),
                     "qc_ok_onset_minus_ready": stats(qc_ok.d),
                     "qc_ok_corr_ready_vs_fp_onset": corr(qc_ok.fp_on_s, qc_ok.wf_ready_time_s),
                     "within_championship_sd_s": round(float((allauto.d - allauto.groupby("compyear").d.transform("mean")).std(ddof=1)), 4)}
    # final dataset (data/derived/foreperiods.csv: automated values after blind/visual review) vs Ready Time
    fpd = pd.read_csv(a.foreperiods)
    fpd = fpd[(fpd.attempt_status == "valid") & fpd.foreperiod_s.notna()].merge(wf, on="race_id", how="inner")
    fpd = fpd[fpd.wf_ok.astype(bool) & (fpd.wf_attempt == fpd.attempt)].copy()
    fpd["compyear"] = fpd.race_id.str.split("-").str[0]
    fpd["d"] = fpd.foreperiod_s - fpd.wf_ready_time_s
    fpd["resid"] = fpd.d - fpd.groupby("compyear").d.transform("mean")
    final = {"n": int(len(fpd)), "onset_minus_ready": stats(fpd.d),
             "onset_minus_ready_by_championship": by_comp(fpd, "d"),
             "corr_ready_vs_fp_onset": corr(fpd.foreperiod_s, fpd.wf_ready_time_s),
             "within_championship_sd_s": round(float(fpd.resid.std(ddof=1)), 4),
             "within_championship_mad_s": round(float(np.median(np.abs(fpd.resid))), 4),
             "within_championship_share_resid_le_100ms": round(float((fpd.resid.abs() <= 0.1).mean()), 4)}
    res = {
        "final_dataset_valid": final,
        "automated_all_measured_valid": automated_all,
        "description": "Broadcast-audio foreperiods vs official Seiko Ready Time (real broadcast audio; manual "
                       "annotation primary, automated pipeline secondary). d = broadcast foreperiod - Ready Time.",
        "n_valid_starts_annotated": int(len(df)),
        "n_compared": int(len(k)),
        "manual": {"onset_minus_ready": stats(k.d_on), "voicing_end_minus_ready": stats(k.d_vend),
                   "word_end_minus_ready": stats(k.d_wend),
                   "onset_minus_ready_by_championship": by_comp(k, "d_on"),
                   "voicing_end_minus_ready_by_championship": by_comp(k, "d_vend"),
                   "onset_minus_ready_within_championship_sd_s": round(float(k.d_on_demeaned.std(ddof=1)), 4),
                   "voicing_end_minus_ready_within_championship_sd_s": round(float(k.d_vend_demeaned.std(ddof=1)), 4),
                   "corr_ready_vs_fp_onset": corr(k.fp_on, k.wf_ready_time_s),
                   "corr_ready_vs_fp_voicing_end": corr(k.fp_vend, k.wf_ready_time_s)},
        "automated": {"onset_minus_ready": stats(k.d_auto_on), "offset_minus_ready": stats(k.d_auto_off),
                      "corr_ready_vs_fp_onset": corr(k.fp_on_s, k.wf_ready_time_s)},
        "excluded": excluded,
        "rows": [{c: (round(float(r[c]), 4) if isinstance(r[c], (float, np.floating)) and np.isfinite(r[c]) else
                      (None if isinstance(r[c], (float, np.floating)) else r[c]))
                  for c in ("race_id", "attempt", "compyear", "wf_ready_time_s", "fp_on", "fp_vend", "fp_wend", "d_on",
                            "d_vend", "d_wend", "fp_on_s", "fp_off_s", "d_auto_on", "qc_flag")}
                 for _, r in k.sort_values("race_id").iterrows()],
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, sort_keys=False)
        f.write("\n")


if __name__ == "__main__":
    main()
