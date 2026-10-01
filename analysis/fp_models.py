"""Deliverable 2 - reaction time as a function of the starter's foreperiod (hold).

Foreperiods: official Seiko start-waveform 'Ready Time' (validated rows of rt_waveform.csv,
WCH2022/2023/2025) and/or broadcast-audio measurements (foreperiods.csv). RTs: valid starts
(0.100-0.300 s, not FS, not DNS) from rt_athletes.csv in those races.

All models: crossed random intercepts for race and athlete, fixed effects for championship
(absorbs timing-system calibration, which differs by up to ~40 ms between meets), sex, round
and event type.
  M0  no foreperiod
  M1  linear foreperiod                      -> slope (ms per 100 ms), r-equivalent
  M2  natural cubic spline (df 3)            -> LRT vs M1 (non-linearity) and vs M0
  M3  objective hazard of the championship's empirical hold distribution (KDE)
  M4  subjective hazard (Weber blur phi=0.25) of the same distribution
  M5  relative hold: z-score within championship
  M6  subjective hazard of the session's (date x half-day) distribution, falls back to the
      championship distribution for sessions with < 5 races
  plus foreperiod x sex, foreperiod x championship interactions, a restart sensitivity,
  race-cluster bootstrap CI for the slope, and shares of RT < 0.100 / < 0.120 s by hold bin.
Model comparison uses ML fits (AIC; LRT for nested pairs); coefficients are reported from ML fits.

Usage: .venv\\Scripts\\python.exe analysis\\fp_models.py --out analysis/outputs/fp_models.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse

import numpy as np
import pandas as pd
import patsy
from scipy import stats

import hazard as hz
from common import (add_common_args, attach_races, load_fp_sources, load_races, load_rt, num,
                    resolve_out, valid_rt_mask, wilson_ci, write_result)
from lmm import fit_formula, lrt, ratio_ci

FX = "C(comp_year) + C(sex, Treatment('M')) + C(round, Treatment('R1')) + C(event_type, Treatment('flat'))"
BINS = [0.0, 1.40, 1.55, 1.70, 1.85, 9.0]
BIN_LABELS = ["<1.40", "1.40-1.55", "1.55-1.70", "1.70-1.85", ">=1.85"]


def session_of(df: pd.DataFrame) -> pd.Series:
    """comp_year + date + half-day (start hour < 15 -> AM) when the schedule is known."""
    base = df["comp_year"].astype(str)
    if "race_date" in df and df["race_date"].notna().any():
        half = np.where(pd.to_numeric(df.get("race_sched_start_local", pd.Series("", index=df.index))
                                      .astype(str).str.slice(0, 2), errors="coerce") < 15, "AM", "PM")
        return base + "-" + df["race_date"].astype(str) + "-" + pd.Series(half, index=df.index)
    return base


def _spline_argmin(fit, data, grid):
    """Hold (on ``grid``) where a fitted spline model predicts the fastest RT."""
    idx = [i for i, n in enumerate(fit.names) if n.startswith("cr(")]
    base = data.iloc[[0] * len(grid)].copy()
    base["foreperiod_s"] = grid
    Xg = patsy.dmatrix(fit.design_info, base, return_type="dataframe").to_numpy()[:, idx]
    return float(grid[int(np.argmin(Xg @ fit.beta[idx]))])


def race_level(d: pd.DataFrame) -> pd.DataFrame:
    return d.groupby("race_id", sort=True).agg(
        foreperiod_s=("foreperiod_s", "first"), comp_year=("comp_year", "first"),
        session=("session", "first"), restart=("restart", "first"), n=("rt_ms", "size"),
        mean_rt=("rt_ms", "mean")).reset_index()


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--fp-source", default="seiko", choices=["auto", "seiko", "audio"],
                    help="seiko = official waveform holds only (primary); audio = broadcast measurements; auto = both")
    ap.add_argument("--boot", type=int, default=500, help="race-cluster bootstrap replicates for the slope")
    ap.add_argument("--phi", type=float, default=0.26, help="Weber blur for hazard/CDF (Janssen & Shadlen 2005)")
    ap.add_argument("--phi-pdf", type=float, default=0.21, help="Weber blur for the reciprocal PDF (Grabenhorst 2019)")
    ap.add_argument("--catch", type=float, default=0.05, help="abort (catch-trial) probability for the abort hazard")
    ap.add_argument("--perm", type=int, default=5000, help="permutations for the fast-RT share test")
    ap.add_argument("--exclude-fp-comps", default="",
                    help="comma-separated championships whose holds are excluded (e.g. WIC2025)")
    args = ap.parse_args()
    out = resolve_out(args, "fp_models")
    LAB = "Seiko Ready Time" if args.fp_source == "seiko" else "foreperiod"

    fp, fused = load_fp_sources(args.mock, args.fp_source)
    if fp.empty:
        raise SystemExit("no foreperiod data yet")
    excluded = {}
    for cy in [c for c in (args.exclude_fp_comps or "").split(",") if c]:
        sel = fp["race_id"].str.startswith(cy + "-")
        if sel.any():
            excluded[cy] = {"n_races": int(sel.sum()), "median_hold_s": float(fp.loc[sel, "foreperiod_s"].median())}
        fp = fp[~sel].copy()
    rt, rused = load_rt(args.mock, "athletes")
    races, raced = load_races(args.mock)
    rt = attach_races(rt, races)
    rt["valid"] = valid_rt_mask(rt)
    d = rt[rt["valid"]].merge(fp, on="race_id", how="inner")
    d["rt_ms"] = d["rt_s"] * 1000
    d["session"] = session_of(d)
    ak = d["athlete_key"].astype(object)
    d["athlete_id2"] = np.where(ak.isna(), "anon_" + d.index.astype(str), ak.astype(str))
    fp_mean_ref = 1.78
    d["fp_c100"] = (d["foreperiod_s"] - fp_mean_ref) * 10.0          # units of 100 ms
    r = race_level(d)

    numbers, tables, extra = {}, {}, {"fp_sources": sorted(d["fp_source"].unique()),
                                      "centre_s": fp_mean_ref, "excluded_hold_comps": excluded}
    for cy, info in excluded.items():
        numbers[f"excluded_median_hold_{cy}"] = num(round(info["median_hold_s"], 4), unit="s",
                                                   desc=f"median Seiko 'Ready Time' at {cy}, excluded from the Ready Time "
                                                        f"analyses (suspected different definition)", n_races=info["n_races"])
    numbers["n_races"] = num(int(r.shape[0]), desc=f"races with a validated {LAB} and >=1 valid RT")
    numbers["n_rts"] = num(int(len(d)), desc="valid RTs in those races")
    numbers["n_restart_races"] = num(int(r["restart"].sum()), desc="races whose recorded start followed an aborted attempt")
    numbers["fp_median_s"] = num(round(float(r["foreperiod_s"].median()), 4), unit="s", desc=f"median {LAB} across races")
    numbers["fp_mean_s"] = num(round(float(r["foreperiod_s"].mean()), 4), unit="s", desc=f"mean {LAB} across races")
    numbers["fp_sd_s"] = num(round(float(r["foreperiod_s"].std(ddof=1)), 4), unit="s", desc=f"SD of {LAB} across races")
    numbers["fp_min_s"] = num(round(float(r["foreperiod_s"].min()), 4), unit="s", desc=f"shortest {LAB}")
    numbers["fp_max_s"] = num(round(float(r["foreperiod_s"].max()), 4), unit="s", desc=f"longest {LAB}")
    for cy, g in r.groupby("comp_year"):
        numbers[f"fp_median_{cy}"] = num(round(float(g["foreperiod_s"].median()), 4), unit="s",
                                         desc=f"median {LAB}, {cy}", n=int(len(g)),
                                         sd=float(f"{g['foreperiod_s'].std(ddof=1):.4g}"))
    tables["race_level"] = r
    # championship difference in holds (one-way ANOVA on race-level holds)
    groups = [g["foreperiod_s"].to_numpy() for _, g in r.groupby("comp_year")]
    if len(groups) >= 2:
        f_, p_ = stats.f_oneway(*groups)
        numbers["fp_anova_comp_F"] = num(round(float(f_), 4), desc=f"one-way ANOVA of {LAB} across championships",
                                         p=float(f"{p_:.3g}"))

    # ---- predictors (race level). The athletes' expectation is the championship's empirical hold
    #      distribution (KDE) unless stated; each shape follows lit/review.md section 5.11. ----------
    rl = r.copy()
    rl["h_obj_comp"] = hz.group_hazard(rl, "foreperiod_s", "comp_year", phi=0.0, s_floor=0.02)
    rl["h_subj_comp"] = hz.group_hazard(rl, "foreperiod_s", "comp_year", phi=args.phi)
    rl["h_subj_session"] = hz.group_hazard(rl, "foreperiod_s", "session", phi=args.phi,
                                           fallback_samples=None, min_n=5)
    # sessions with < 5 races use the championship distribution instead of the pooled one
    small = rl.groupby("session")["race_id"].transform("size") < 5
    rl.loc[small, "h_subj_session"] = rl.loc[small, "h_subj_comp"]
    rl["h_abort_comp"] = hz.group_curve_at(rl, "foreperiod_s", "comp_year", hz.abort_hazard_curve, catch=args.catch)
    rl["recip_pdf_comp"] = hz.group_curve_at(rl, "foreperiod_s", "comp_year", hz.recip_pdf_curve, phi=args.phi_pdf)
    rl["fmtp_cdf_comp"] = hz.group_curve_at(rl, "foreperiod_s", "comp_year", hz.blurred_cdf_curve, phi=args.phi)
    rl["fp_z_comp"] = rl.groupby("comp_year")["foreperiod_s"].transform(lambda s: (s - s.mean()) / s.std(ddof=1))
    rl["fp_med_comp"] = rl.groupby("comp_year")["foreperiod_s"].transform("median")
    rl["below100"] = np.minimum(rl["foreperiod_s"] - rl["fp_med_comp"], 0.0) * 10
    rl["above100"] = np.maximum(rl["foreperiod_s"] - rl["fp_med_comp"], 0.0) * 10
    pred_cols = ["h_obj_comp", "h_subj_comp", "h_subj_session", "h_abort_comp", "recip_pdf_comp", "fmtp_cdf_comp"]
    d = d.merge(rl[["race_id", "fp_z_comp", "below100", "above100"] + pred_cols], on="race_id")
    for c in pred_cols:
        d[c + "_z"] = (d[c] - rl[c].mean()) / rl[c].std(ddof=1)
    extra["predictor_settings"] = {"phi_hazard": args.phi, "phi_pdf": args.phi_pdf, "catch": args.catch,
                                   "distribution": "championship empirical holds (KDE, Silverman)"}
    tables["race_predictors"] = rl[["race_id", "comp_year", "foreperiod_s"] + pred_cols]

    # ---- models (ML) --------------------------------------------------------------------------------
    re_ = ["race_id", "athlete_id2"]
    specs = {
        "M0 no Ready Time term": FX,
        "M1 Ready Time (linear)": FX + " + fp_c100",
        "M2 Ready Time (spline df3)": FX + " + cr(foreperiod_s, df=3, constraints='center')",
        "M3 objective hazard": FX + " + h_obj_comp_z",
        "M4 subjective hazard": FX + " + h_subj_comp_z",
        "M5 relative Ready Time (z in champ.)": FX + " + fp_z_comp",
        "M6 subjective hazard (session)": FX + " + h_subj_session_z",
        "M7 abort-adjusted hazard": FX + " + h_abort_comp_z",
        "M8 reciprocal PDF (Grabenhorst)": FX + " + recip_pdf_comp_z",
        "M9 fMTP-style (blurred CDF)": FX + " + fmtp_cdf_comp_z",
        "M10 piecewise at champ. median": FX + " + below100 + above100",
    }
    fits = {k: fit_formula(v, d, "rt_ms", re_, method="ML") for k, v in specs.items()}
    m0, m1, m2 = fits["M0 no Ready Time term"], fits["M1 Ready Time (linear)"], fits["M2 Ready Time (spline df3)"]
    comp_rows = []
    for name, f in fits.items():
        comp_rows.append({"model": name, "k_fixed": f.p, "loglik": f.loglik, "aic": f.aic,
                          "delta_aic_vs_M0": f.aic - m0.aic})
    comp = pd.DataFrame(comp_rows)
    tables["model_comparison"] = comp
    for _, rr in comp.iterrows():
        numbers["daic_" + rr["model"].split(" ")[0]] = num(round(float(rr["delta_aic_vs_M0"]), 3),
                                                            desc=f"AIC({rr['model']}) - AIC(M0), ML fits (negative = better)")
    best = comp.sort_values("aic").iloc[0]
    numbers["best_model"] = num(str(best["model"]), desc="lowest-AIC model among M0-M10",
                                delta_to_M0=float(f"{best['delta_aic_vs_M0']:.4g}"))
    est, lo, hi = m1.coef("fp_c100")
    numbers["slope_ms_per_100ms"] = num(round(est, 3), ci=(round(lo, 3), round(hi, 3)), unit="ms per 100 ms",
                                        desc=f"RT change per 100 ms longer {LAB} (M1, ML, Wald CI; championship fixed effects)",
                                        p=float(f"{2 * stats.norm.sf(abs(est / m1.se[m1.names.index('fp_c100')])):.3g}"))
    s_lr, df_lr, p_lr = lrt(m1, m0)
    numbers["lrt_linear_vs_none"] = num(round(s_lr, 4), desc="LRT M1 vs M0", df=df_lr, p=float(f"{p_lr:.3g}"))
    s2, df2, p2 = lrt(m2, m1)
    numbers["lrt_spline_vs_linear"] = num(round(s2, 4), desc="LRT spline (df 3) vs linear: evidence of non-linearity",
                                          df=df2, p=float(f"{p2:.3g}"))
    s3, df3, p3 = lrt(m2, m0)
    numbers["lrt_spline_vs_none"] = num(round(s3, 4), desc=f"LRT spline vs no {LAB} term", df=df3, p=float(f"{p3:.3g}"))
    # r-equivalent: slope x SD_FP / SD_RT(within championship)
    m0r = fit_formula(FX, d, "rt_ms", re_, method="REML")
    sd_w = float(np.sqrt(m0r.var_comp["race_id"] + m0r.var_comp["athlete_id2"] + m0r.sigma2))
    # the slope is identified from within-championship hold variation, so the r-equivalent uses the
    # pooled within-championship SD of holds (the pooled overall SD is reported as a sensitivity)
    gsd = r.groupby("comp_year")["foreperiod_s"].agg(["var", "size"])
    sd_fp_within = float(np.sqrt(((gsd["size"] - 1) * gsd["var"]).sum() / (gsd["size"] - 1).sum()))
    sd_fp100 = sd_fp_within * 10
    numbers["fp_sd_within_comp_s"] = num(round(sd_fp_within, 4), unit="s", desc=f"pooled within-championship SD of {LAB}")
    numbers["r_equivalent"] = num(round(est * sd_fp100 / sd_w, 4), ci=(round(lo * sd_fp100 / sd_w, 4), round(hi * sd_fp100 / sd_w, 4)),
                                  desc=f"slope x within-championship SD({LAB}) / SD(RT within championship); on the {LAB} scale")
    sd_all100 = float(r["foreperiod_s"].std(ddof=1) * 10)
    numbers["r_equivalent_pooled_sd"] = num(round(est * sd_all100 / sd_w, 4),
                                            ci=(round(lo * sd_all100 / sd_w, 4), round(hi * sd_all100 / sd_w, 4)),
                                            desc=f"r-equivalent using the overall SD of {LAB} (sensitivity)")
    numbers["sd_rt_within_ms"] = num(round(sd_w, 3), unit="ms", desc=f"SD of RT within championship in the {LAB} sample (M0)")
    icc, ilo, ihi = ratio_ci(m0r, ["race_id"], ["race_id", "athlete_id2"])
    numbers["icc_race"] = num(round(icc, 4), ci=(round(ilo, 4), round(ihi, 4)),
                              desc=f"race ICC within championship in the {LAB} sample (M0, REML)")
    numbers["haugen_slope_same_scale"] = num(round(0.16 * sd_w / sd_fp100, 3), unit="ms per 100 ms",
                                             desc=f"slope that |r| = 0.16 would imply on the {LAB} scale with this sample's within-championship SDs")
    numbers["ci_excludes_haugen"] = num(bool(hi < 0.16 * sd_w / sd_fp100 and lo > -0.16 * sd_w / sd_fp100),
                                        desc=f"95% CI of the {LAB} slope excludes a Haugen-sized slope (|r| = 0.16 on the {LAB} scale) in both directions")
    se1 = float(m1.se[m1.names.index("fp_c100")])
    numbers["mde80_slope_ms_per_100ms"] = num(round(2.8016 * se1, 3), unit="ms per 100 ms",
                                              desc=f"minimum detectable {LAB} slope, 80% power, two-sided 0.05 (2.80 x SE)")
    numbers["mde80_r"] = num(round(2.8016 * se1 * sd_fp100 / sd_w, 4),
                             desc="minimum detectable |r|-equivalent, 80% power")
    # predicted sign of each predictor's coefficient on RT (lit/review.md section 5.11): more hazard or
    # more accumulated preparation -> faster (-); a larger reciprocal PDF (less expected moment) -> slower (+)
    predicted = {"fp_z_comp": 0, "h_obj_comp_z": -1, "h_subj_comp_z": -1, "h_subj_session_z": -1,
                 "h_abort_comp_z": -1, "recip_pdf_comp_z": 1, "fmtp_cdf_comp_z": -1}
    eff_rows = []
    for nm, sgn in predicted.items():
        mname = [k for k, f in fits.items() if nm in f.names][0]
        e_, l_, h_ = fits[mname].coef(nm)
        se_ = float(fits[mname].se[fits[mname].names.index(nm)])
        verdict = ("no prediction" if sgn == 0 else
                   "predicted sign, CI excludes 0" if (l_ > 0 and sgn > 0) or (h_ < 0 and sgn < 0) else
                   "opposite sign, CI excludes 0" if (l_ > 0 and sgn < 0) or (h_ < 0 and sgn > 0) else
                   ("predicted sign, CI includes 0" if np.sign(e_) == sgn else "opposite sign, CI includes 0"))
        eff_rows.append({"model": mname, "term": nm, "ms_per_sd": e_, "lo": l_, "hi": h_, "mde80": 2.8016 * se_,
                         "delta_aic_vs_M0": fits[mname].aic - m0.aic, "predicted_sign": sgn, "verdict": verdict})
        numbers[f"coef_{nm}"] = num(round(e_, 3), ci=(round(l_, 3), round(h_, 3)), unit="ms per SD",
                                    desc=f"RT change per SD of {nm} ({mname})", mde80=float(f"{2.8016 * se_:.3g}"),
                                    predicted_sign=sgn, verdict=verdict)
    tables["predictor_effects"] = pd.DataFrame(eff_rows)
    mp = fits["M10 piecewise at champ. median"]
    for nm, lab in (("below100", "below"), ("above100", "above")):
        e_, l_, h_ = mp.coef(nm)
        numbers[f"slope_{lab}_median_ms_per_100ms"] = num(
            round(e_, 3), ci=(round(l_, 3), round(h_, 3)), unit="ms per 100 ms",
            desc=f"slope {lab} each championship's median {LAB} (piecewise model M10); lit predictions above the "
                 "mode: reciprocal PDF +, hazard -, fMTP ~0")

    # ---- sequential effect: the same athlete's previous start at the championship (fMTP/MTP) --------
    from common import ROUND_ORDER
    allv = rt[rt["valid"] & rt["athlete_key"].notna()].copy()
    allv["round_idx"] = allv["round"].map({r_: i for i, r_ in enumerate(ROUND_ORDER)})
    allv = allv.sort_values(["athlete_key", "comp_year", "round_idx"])
    allv["prev_race"] = allv.groupby(["athlete_key", "comp_year"])["race_id"].shift(1)
    hold_of = fp.set_index("race_id")["foreperiod_s"]
    allv["prev_hold"] = allv["prev_race"].map(hold_of)
    d = d.merge(allv[["race_id", "athlete_key", "prev_hold"]], on=["race_id", "athlete_key"], how="left")
    sq = d[d["prev_hold"].notna()].copy()
    msq = None
    if sq["race_id"].nunique() >= 20:
        sq["prev_longer100"] = np.maximum(sq["prev_hold"] - sq["foreperiod_s"], 0.0) * 10
        sq["prev_shorter100"] = np.maximum(sq["foreperiod_s"] - sq["prev_hold"], 0.0) * 10
        # later rounds only (a first start has no previous hold), so use default reference levels
        fx_seq = "C(comp_year) + C(sex) + C(round) + C(event_type)"
        try:
            msq = fit_formula(fx_seq + " + fp_c100 + prev_longer100 + prev_shorter100", sq, "rt_ms", re_, method="ML")
        except Exception as e:  # recorded, not hidden
            extra["sequential_error"] = type(e).__name__
    if msq is not None:
        for nm in ("prev_longer100", "prev_shorter100"):
            e_, l_, h_ = msq.coef(nm)
            numbers[f"seq_{nm}_ms_per_100ms"] = num(
                round(e_, 3), ci=(round(l_, 3), round(h_, 3)), unit="ms per 100 ms",
                desc=f"sequential effect: RT change per 100 ms that the athlete's previous {LAB} at the championship was "
                     f"{'longer' if 'longer' in nm else 'shorter'} than the current one (MTP predicts + for longer)",
                n_starts=int(len(sq)), n_athletes=int(sq["athlete_key"].nunique()))

    # residualised race means for plotting: race mean of (RT - fixed effects of M0 except intercept)
    X0 = patsy.dmatrix(m0.design_info, d, return_type="dataframe").to_numpy()
    fx0 = X0[:, 1:] @ m0.beta[1:]
    d["rt_resid_ms"] = d["rt_ms"] - fx0 - m0.beta[0]
    rres = d.groupby("race_id").agg(fp=("foreperiod_s", "first"), comp_year=("comp_year", "first"),
                                    resid_ms=("rt_resid_ms", "mean"), n=("rt_ms", "size")).reset_index()
    tables["race_resid"] = rres

    # spline partial effect curve (relative to 1.78 s)
    grid = np.round(np.linspace(float(r["foreperiod_s"].quantile(0.02)), float(r["foreperiod_s"].quantile(0.98)), 60), 4)
    names = m2.names
    sp_idx = [i for i, n in enumerate(names) if n.startswith("cr(")]
    base = d.iloc[[0] * len(grid)].copy()
    base["foreperiod_s"] = grid
    Xg = patsy.dmatrix(m2.design_info, base, return_type="dataframe").to_numpy()[:, sp_idx]
    ref_row = base.iloc[[0]].copy()
    ref_row["foreperiod_s"] = fp_mean_ref
    Xr = patsy.dmatrix(m2.design_info, ref_row, return_type="dataframe").to_numpy()[:, sp_idx]
    L = Xg - Xr
    b = m2.beta[sp_idx]
    V = m2.cov_beta[np.ix_(sp_idx, sp_idx)]
    eff = L @ b
    se = np.sqrt(np.einsum("ij,jk,ik->i", L, V, L))
    lin = (grid - fp_mean_ref) * 10 * est
    tables["spline_curve"] = pd.DataFrame({"fp": grid, "effect_ms": eff, "lo": eff - 1.96 * se,
                                           "hi": eff + 1.96 * se, "linear_ms": lin})

    # ---- interactions and sensitivities -----------------------------------------------------------------
    mi = fit_formula(FX + " + fp_c100 * C(sex, Treatment('M'))", d, "rt_ms", re_, method="ML")
    nm_i = [n for n in mi.names if n.startswith("fp_c100:")]
    if nm_i:
        e_, l_, h_ = mi.coef(nm_i[0])
        s_, df_, p_ = lrt(mi, m1)
        numbers["fp_x_sex_ms_per_100ms"] = num(round(e_, 3), ci=(round(l_, 3), round(h_, 3)), unit="ms per 100 ms",
                                               desc=f"difference in {LAB} slope, women minus men", p=float(f"{p_:.3g}"))
    mc = fit_formula(FX + " + fp_c100:C(comp_year)", d, "rt_ms", re_, method="ML")
    s_, df_, p_ = lrt(mc, m1)
    numbers["lrt_fp_x_comp"] = num(round(s_, 4), desc="LRT: championship-specific slopes vs common slope", df=df_,
                                   p=float(f"{p_:.3g}"))
    per_comp = []
    for n_ in mc.names:
        if n_.startswith("fp_c100:C(comp_year)"):
            e_, l_, h_ = mc.coef(n_)
            per_comp.append({"comp_year": n_.split("[")[-1].rstrip("]"), "slope": e_, "lo": l_, "hi": h_})
    tables["slope_by_comp"] = pd.DataFrame(per_comp)
    d_nr = d[~d["restart"]]
    if d_nr["race_id"].nunique() < d["race_id"].nunique():
        m1n = fit_formula(FX + " + fp_c100", d_nr, "rt_ms", re_, method="ML")
        e_, l_, h_ = m1n.coef("fp_c100")
        numbers["slope_no_restarts"] = num(round(e_, 3), ci=(round(l_, 3), round(h_, 3)), unit="ms per 100 ms",
                                           desc=f"{LAB} slope excluding races that followed an aborted start",
                                           n_races=int(d_nr["race_id"].nunique()))
    # race-cluster bootstrap of the linear slope (resample races within championship)
    rng = np.random.default_rng(args.seed)
    by_comp = {c: sorted(g["race_id"].unique()) for c, g in d.groupby("comp_year")}
    idx_by_race = {k: v.to_numpy() for k, v in d.groupby("race_id").groups.items()}
    bs, bmin = [], []
    fastest_hold = _spline_argmin(m2, d, grid)
    for _ in range(args.boot):
        pick = []
        for c, rids in by_comp.items():
            for j in rng.integers(0, len(rids), len(rids)):
                pick.append(idx_by_race[rids[j]])
        ii = np.concatenate(pick)
        db = d.loc[ii].copy()
        # bootstrap duplicates of a race must stay distinct clusters
        db["race_id"] = db["race_id"] + "_" + np.repeat(np.arange(len(pick)), [len(p_) for p_ in pick]).astype(str)
        try:
            fb = fit_formula(FX + " + fp_c100", db, "rt_ms", re_, method="ML")
            bs.append(fb.coef("fp_c100")[0])
            fs_ = fit_formula(FX + " + cr(foreperiod_s, df=3, constraints='center')", db, "rt_ms", re_, method="ML")
            bmin.append(_spline_argmin(fs_, db, grid))
        except Exception:
            continue
    if bmin:
        numbers["spline_fastest_hold_s"] = num(round(float(fastest_hold), 3),
                                               ci=(round(float(np.percentile(bmin, 2.5)), 3), round(float(np.percentile(bmin, 97.5)), 3)),
                                               unit="s", desc=f"{LAB} at which the spline predicts the fastest RT "
                                                              "(race-cluster bootstrap CI); compare with the median hold",
                                               median_hold=float(f"{r['foreperiod_s'].median():.4g}"))
    if bs:
        numbers["slope_boot_ci"] = num(round(est, 3), ci=(round(float(np.percentile(bs, 2.5)), 3),
                                                          round(float(np.percentile(bs, 97.5)), 3)),
                                       unit="ms per 100 ms", desc=f"linear {LAB} slope with race-cluster bootstrap 95% CI",
                                       n_boot=len(bs))

    # ---- within-championship terciles and a permutation test for the fast-RT share -------------------
    dt = d.copy()
    dt["tercile"] = dt.groupby("comp_year")["foreperiod_s"].transform(
        lambda s_: pd.qcut(s_.rank(method="first"), 3, labels=["short", "mid", "long"]).astype(str))
    dt["lt120"] = dt["rt_s"] < 0.120
    terc = dt.groupby(["comp_year", "tercile"], sort=True).agg(
        races=("race_id", "nunique"), n=("rt_s", "size"), k_lt120=("lt120", "sum"), share_lt120=("lt120", "mean"),
        mean_rt_ms=("rt_ms", "mean"), sd_rt_ms=("rt_ms", "std"), mean_fp_s=("foreperiod_s", "mean")).reset_index()
    tables["by_comp_tercile"] = terc
    rr_ = dt.groupby("race_id").agg(comp=("comp_year", "first"), fp=("foreperiod_s", "first"),
                                    k=("lt120", "sum"), n=("lt120", "size")).reset_index()

    def _stat(frame):
        tot = 0.0
        for _, g in frame.groupby("comp"):
            tot += float(((g["fp"] - g["fp"].mean()) * (g["k"] / g["n"] - g["k"].sum() / g["n"].sum()) * g["n"]).sum())
        return tot

    obs = _stat(rr_)
    rng_p = np.random.default_rng(args.seed + 3)
    comps_idx = {c: np.flatnonzero(rr_["comp"].to_numpy() == c) for c in sorted(rr_["comp"].unique())}
    fpv = rr_["fp"].to_numpy().copy()
    null = np.empty(args.perm)
    for b in range(args.perm):
        perm_fp = fpv.copy()
        for c, ix in comps_idx.items():
            perm_fp[ix] = fpv[rng_p.permutation(ix)]
        null[b] = _stat(rr_.assign(fp=perm_fp))
    p_perm = float((np.sum(np.abs(null) >= abs(obs)) + 1) / (args.perm + 1))
    per_comp_k = rr_.groupby("comp")["k"].sum().to_dict()
    numbers["perm_p_lt120_vs_hold"] = num(float(f"{p_perm:.3g}"),
                                          desc=f"within-championship permutation test ({LAB} shuffled among races of the same "
                                               "championship): association of race share of RT<0.120 s with hold (two-sided, "
                                               "exploratory)", sign=int(np.sign(obs)), n_perm=args.perm,
                                          fast_rts_by_comp={str(k_): int(v_) for k_, v_ in per_comp_k.items()})

    # ---- shares of fast RTs by hold bin -------------------------------------------------------------
    allst = rt[rt["rt_s"].notna() & ~rt["is_dns"].astype(bool)].merge(fp[["race_id", "foreperiod_s"]], on="race_id")
    allst["bin"] = pd.cut(allst["foreperiod_s"], BINS, labels=BIN_LABELS, right=False)
    dv = d.copy()
    dv["bin"] = pd.cut(dv["foreperiod_s"], BINS, labels=BIN_LABELS, right=False)
    rows = []
    for lab in BIN_LABELS:
        g = dv[dv["bin"] == lab]
        ga = allst[allst["bin"] == lab]
        k120, n = int((g["rt_s"] < 0.120).sum()), int(len(g))
        k100, na = int((ga["rt_s"] < 0.100).sum()), int(len(ga))
        l120, h120 = wilson_ci(k120, n)
        l100, h100 = wilson_ci(k100, na)
        rows.append({"bin": lab, "races": int(g["race_id"].nunique()), "valid_rts": n,
                     "share_lt120": k120 / n if n else np.nan, "lt120_lo": l120, "lt120_hi": h120, "k_lt120": k120,
                     "recorded_starts": na, "share_lt100": k100 / na if na else np.nan,
                     "lt100_lo": l100, "lt100_hi": h100, "k_lt100": k100})
    tables["share_by_bin"] = pd.DataFrame(rows)
    # GEE logistic, P(RT<0.120) ~ hold, clustered by race (exchangeable)
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        dv["lt120"] = (dv["rt_s"] < 0.120).astype(int)
        gee = smf.gee("lt120 ~ fp_c100 + C(comp_year) + C(sex)", "race_id", dv,
                      family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        b_, se_ = float(gee.params["fp_c100"]), float(gee.bse["fp_c100"])
        numbers["or_lt120_per_100ms"] = num(round(float(np.exp(b_)), 4),
                                            ci=(round(float(np.exp(b_ - 1.96 * se_)), 4), round(float(np.exp(b_ + 1.96 * se_)), 4)),
                                            desc=f"odds ratio of a valid RT < 0.120 s per 100 ms longer {LAB} (GEE, race clusters)",
                                            p=float(f"{float(gee.pvalues['fp_c100']):.3g}"))
    except Exception as e:  # pragma: no cover
        extra["gee_error"] = type(e).__name__

    extra["model_coefs_M1"] = m1.coef_table().reset_index().rename(columns={"index": "term"}).to_dict("records")
    p = write_result(out, "fp_models", numbers, fused + rused + raced, args.mock, tables=tables, extra=extra,
                     seed=args.seed)
    print(comp.to_string(index=False))
    for k, v in numbers.items():
        print(f"{k:34s} {v.get('value')!s:>10} {v.get('ci95', '')} {v.get('p', '')}")
    print(tables["share_by_bin"].to_string(index=False))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
