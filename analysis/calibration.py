"""Seiko Ready Time as an error-prone proxy for the foreperiod: regression calibration.

The measurement pipeline found that the Seiko 'Ready Time' is not set-onset -> gun: broadcast-audio
foreperiods (set onset -> gun) exceed it by about half a second, with championship-specific offsets
and residual scatter. A noisy proxy attenuates the RT slope toward zero, so the Ready-Time null
needs an errors-in-variables check.

  1. Pairs: manual broadcast annotations (clean, valid attempts; analysis/measure/manual_annotations.csv)
     joined to the Seiko Ready Time of the same race and attempt (data/derived/rt_waveform.csv).
  2. Calibration: X (audio foreperiod) = a_championship + b * W (Ready Time) + e, OLS with championship
     fixed effects (the RT models also use championship fixed effects). Stratified bootstrap over pairs.
  3. Correction (regression calibration): slope per 100 ms of foreperiod = slope per 100 ms of Ready
     Time / b; r-equivalent on the foreperiod scale = r(Ready) / sqrt(b) (classical-error case).
     Monte Carlo: slope ~ Normal(estimate, Wald SE) from fp_models.json x bootstrap draws of b.
  4. Direct fit where audio foreperiods exist: RT ~ audio foreperiod + championship/sex/round/event
     fixed effects + race and athlete random intercepts (small n; reported separately).

Usage: .venv\\Scripts\\python.exe analysis\\calibration.py --fp-models analysis/outputs/fp_models.json
           --out analysis/outputs/calibration.json
"""
from __future__ import annotations

import _env  # noqa: F401

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import (ROOT, add_common_args, attach_races, data_path, load_races, load_rt, num, resolve_out,
                    valid_rt_mask, write_result)
from lmm import fit_formula

MANUAL = ROOT / "analysis" / "measure" / "manual_annotations.csv"
FX = "C(comp_year) + C(sex) + C(round) + C(event_type)"


def pairs_table(mock: bool):
    man = pd.read_csv(MANUAL)
    man = man[(man["clean"].astype(str) == "1") & (man["attempt_status"] == "valid")].copy()
    man["fp_onset_s"] = man["t_gun"] - man["t_set_on"]
    man["fp_voice_end_s"] = man["t_gun"] - man["t_voicing_end"]
    wf = pd.read_csv(data_path("rt_waveform.csv", mock), encoding="utf-8-sig")
    wf = wf[wf["wf_ok"].astype(str).str.lower().isin(["true", "1"])]
    p = man.merge(wf[["race_id", "wf_attempt", "wf_ready_time_s"]], on="race_id")
    p = p[p["attempt"] == p["wf_attempt"]].copy()
    p["comp_year"] = p["race_id"].str.split("-").str[0]
    return p.dropna(subset=["fp_onset_s", "wf_ready_time_s"]).reset_index(drop=True)


def calib_slope(x, w, comp):
    """Within-championship OLS slope of x on w (championship fixed effects)."""
    df = pd.DataFrame({"x": x, "w": w, "c": comp})
    xc = df["x"] - df.groupby("c")["x"].transform("mean")
    wc = df["w"] - df.groupby("c")["w"].transform("mean")
    sww = float((wc ** 2).sum())
    if sww <= 0:
        return np.nan, np.nan
    b = float((wc * xc).sum() / sww)
    resid = xc - b * wc
    dof = len(df) - df["c"].nunique() - 1
    se = float(np.sqrt((resid ** 2).sum() / max(dof, 1) / sww))
    return b, se


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--fp-models", required=True)
    ap.add_argument("--boot", type=int, default=5000)
    ap.add_argument("--mc", type=int, default=20000)
    args = ap.parse_args()
    out = resolve_out(args, "calibration")
    rng = np.random.default_rng(args.seed)
    fpm = json.loads(Path(args.fp_models).read_text(encoding="utf-8"))
    nf = fpm["numbers"]
    numbers, tables, extra = {}, {}, {}

    p = pairs_table(args.mock)
    tables["pairs"] = p[["race_id", "comp_year", "attempt", "fp_onset_s", "fp_voice_end_s", "wf_ready_time_s"]]
    d = p["fp_onset_s"] - p["wf_ready_time_s"]
    numbers["n_pairs"] = num(int(len(p)), desc="races with a clean manual broadcast foreperiod and a Seiko Ready Time "
                                                "for the same attempt")
    numbers["offset_mean_s"] = num(round(float(d.mean()), 4), unit="s", desc="mean (audio set-onset foreperiod - Ready Time)")
    dw = d - d.groupby(p["comp_year"]).transform("mean")
    dof_w = len(p) - p["comp_year"].nunique()
    numbers["offset_sd_within_comp_s"] = num(round(float(np.sqrt((dw ** 2).sum() / max(dof_w, 1))), 4), unit="s",
                                             desc="within-championship SD of (audio foreperiod - Ready Time)")
    for cy, g in p.groupby("comp_year"):
        numbers[f"offset_mean_{cy}_s"] = num(round(float((g['fp_onset_s'] - g['wf_ready_time_s']).mean()), 4), unit="s",
                                             desc=f"mean (audio foreperiod - Ready Time), {cy}", n=int(len(g)))
    numbers["corr_ready_audio"] = num(round(float(np.corrcoef(p["fp_onset_s"], p["wf_ready_time_s"])[0, 1]), 4),
                                      desc="Pearson r between Ready Time and audio foreperiod (pooled over championships)")

    # ---- calibration slope b (within championship) ------------------------------------------------
    b, se_b = calib_slope(p["fp_onset_s"], p["wf_ready_time_s"], p["comp_year"])
    groups = {c: np.flatnonzero(p["comp_year"].to_numpy() == c) for c in sorted(p["comp_year"].unique())}
    bb = []
    for _ in range(args.boot):
        ii = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups.values()])
        bi, _ = calib_slope(p["fp_onset_s"].to_numpy()[ii], p["wf_ready_time_s"].to_numpy()[ii],
                            p["comp_year"].to_numpy()[ii])
        if np.isfinite(bi):
            bb.append(bi)
    bb = np.array(bb)
    numbers["calib_slope_b"] = num(round(b, 4), ci=(round(float(np.percentile(bb, 2.5)), 4), round(float(np.percentile(bb, 97.5)), 4)),
                                   desc="within-championship slope of audio foreperiod on Ready Time (regression "
                                        "calibration factor; 1 = no attenuation); stratified bootstrap CI",
                                   se_ols=float(f"{se_b:.4g}"), n_boot=int(len(bb)),
                                   share_boot_below_0_2=float(f"{(bb < 0.2).mean():.4g}"))
    b_v, se_v = calib_slope(p["fp_voice_end_s"], p["wf_ready_time_s"], p["comp_year"])
    numbers["calib_slope_b_voice_end"] = num(round(b_v, 4), desc="calibration slope using the end of voicing of 'Set' "
                                                                  "instead of its onset (sensitivity)",
                                             se_ols=float(f"{se_v:.4g}"))

    # ---- corrected slope and r-equivalent -------------------------------------------------------------
    sl = nf["slope_ms_per_100ms"]
    se_sl = (sl["ci95"][1] - sl["ci95"][0]) / (2 * 1.959964)
    rq = nf["r_equivalent"]
    se_r = (rq["ci95"][1] - rq["ci95"][0]) / (2 * 1.959964)
    bs = rng.choice(bb, size=args.mc, replace=True)
    ok = bs > 0.05
    slope_draw = rng.normal(sl["value"], se_sl, args.mc)
    r_draw = rng.normal(rq["value"], se_r, args.mc)
    corr_slope = slope_draw[ok] / bs[ok]
    corr_r = r_draw[ok] / np.sqrt(bs[ok])
    lo_s, hi_s = np.percentile(corr_slope, [2.5, 97.5])
    lo_r, hi_r = np.percentile(corr_r, [2.5, 97.5])
    numbers["slope_corrected_ms_per_100ms"] = num(round(sl["value"] / b, 3), ci=(round(float(lo_s), 3), round(float(hi_s), 3)),
                                                  unit="ms per 100 ms of foreperiod",
                                                  desc="Ready-Time slope divided by the calibration factor b (Monte Carlo "
                                                       "over the slope's sampling error and bootstrap b)",
                                                  share_draws_used=float(f"{ok.mean():.4g}"))
    numbers["r_corrected"] = num(round(rq["value"] / np.sqrt(b), 4), ci=(round(float(lo_r), 4), round(float(hi_r), 4)),
                                 desc="r-equivalent on the foreperiod scale (r(Ready) / sqrt(b), classical error)")
    numbers["corrected_excludes_haugen"] = num(bool(hi_r < 0.16 and lo_r > -0.16),
                                               desc="corrected r interval excludes |r| = 0.16 in both directions")
    # worst case: b at its lower 2.5% bound
    b_lo = float(np.percentile(bb, 2.5))
    if b_lo > 0:
        numbers["r_ci_high_at_b_low"] = num(round(float(rq["ci95"][1] / np.sqrt(b_lo)), 4),
                                            desc="upper 95% bound of the r-equivalent if b sits at its lower 2.5% bound (conservative)")
        numbers["r_ci_low_at_b_low"] = num(round(float(rq["ci95"][0] / np.sqrt(b_lo)), 4),
                                           desc="lower 95% bound of the r-equivalent if b sits at its lower 2.5% bound (conservative)")
    extra["b_boot_quantiles"] = {q: float(np.percentile(bb, q)) for q in (1, 2.5, 5, 25, 50, 75, 95, 97.5, 99)}

    # ---- direct fit on audio foreperiods ----------------------------------------------------------------
    rt, rused = load_rt(args.mock, "athletes")
    races, raced = load_races(args.mock)
    rt = attach_races(rt, races)
    v = rt[valid_rt_mask(rt)].merge(p[["race_id", "fp_onset_s"]], on="race_id")
    if v["race_id"].nunique() >= 8:
        v = v.copy()
        v["rt_ms"] = v["rt_s"] * 1000
        v["athlete_id2"] = v["athlete_key"].astype(str)
        v["afp_c100"] = (v["fp_onset_s"] - v["fp_onset_s"].mean()) * 10
        try:
            f = fit_formula(FX + " + afp_c100", v, "rt_ms", ["race_id", "athlete_id2"], method="ML")
            e_, l_, h_ = f.coef("afp_c100")
            numbers["direct_audio_slope_ms_per_100ms"] = num(round(e_, 3), ci=(round(l_, 3), round(h_, 3)),
                                                             unit="ms per 100 ms of foreperiod",
                                                             desc="RT on broadcast-audio foreperiod directly (small sample)",
                                                             n_races=int(v["race_id"].nunique()), n_rts=int(len(v)))
        except Exception as e:  # recorded
            extra["direct_fit_error"] = type(e).__name__
    inputs = [MANUAL, data_path("rt_waveform.csv", args.mock), Path(args.fp_models)] + rused + raced
    res = write_result(out, "calibration", numbers, inputs, args.mock, tables=tables, extra=extra, seed=args.seed)
    for k, val in numbers.items():
        print(f"{k:34s} {val.get('value')!s:>10} {val.get('ci95', '')}")
    print(f"wrote {res}")


if __name__ == "__main__":
    main()
