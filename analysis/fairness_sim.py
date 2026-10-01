"""Deliverable 3 - SIMULATION: how the starter's hold changes the chance that a legitimate,
gun-triggered start is scored below 0.100 s (and so disqualified).

Everything here is a model-based simulation. Real inputs: championship RT distributions fitted
in descriptive.json (World Athletics results + Fiore et al. data) and published effect sizes.
Nothing below is an observed foreperiod effect.

Model
  A legitimate start's RT = R + D(FP) + c_meet, where
    R        ~ reference RT distribution at an average meet, first round, 100 m (fitted per sex
               with left truncation at 0.100 s; ex-Gaussian primary, shifted lognormal and
               shifted Wald as tail-shape sensitivity; race-cluster bootstrap draws carry
               parameter uncertainty),
    D(FP)    = RT shift caused by the hold FP (scenarios below),
    c_meet   = the meet's timing-calibration offset (observed championship deviations).
  P(legit FS | FP) = F_R(0.100 - D(FP) - c_meet).

Scenarios for D(FP) (FP in s; reference hold 1.780 s)
  none            D = 0
  haugen_slower   linear, +r * SD_RT / SD_FP per s    (|r| = 0.16, sign of Haugen et al. 2013)
  haugen_faster   linear, -r * SD_RT / SD_FP per s    (same size, variable-foreperiod direction)
  hazard          D = -k [h~(FP) - h~(1.780)], h~ = subjective hazard of the starter's hold
                  distribution (Janssen & Shadlen 2005 blur, Weber fraction phi); k set so the
                  implied athlete-level corr(FP, RT) = -0.16 under the championship distribution
  otsuka_lab      linear, -(156-117) ms / (2.096-1.465) s  (lab contrast; an upper bound)

Hold distribution (championships): Normal(1.780, 0.158) s truncated to [1.2, 2.8]
(Otsuka et al. 2017, 83 races, verified by the literature review). Starter policies compared under
the hazard scenario share the same mean hold.

Usage: .venv\\Scripts\\python.exe analysis\\fairness_sim.py --descriptive analysis/outputs/descriptive.json
                                                   --out analysis/outputs/fairness.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import hazard as hz
import rtdist
from common import FS_THRESHOLD, add_common_args, num, resolve_out, write_result

FP_MEAN, FP_SD, FP_LO, FP_HI = 1.780, 0.158, 1.2, 2.8
HAUGEN_R = 0.16
OTSUKA_SLOPE = -(0.156 - 0.117) / (2.096 - 1.465)        # s of RT per s of hold
FP_GRID = np.round(np.arange(1.30, 2.401, 0.01), 3)
# Long grid for hazard computations: the time-proportional blur spreads mass far beyond the
# holds themselves, and a short grid creates a spurious hazard spike at its right edge.
G = np.round(np.linspace(0.0, 10.0, 2001), 4)
Z10, Z90 = stats.norm.ppf(0.10), stats.norm.ppf(0.90)
FP_P10, FP_P90 = FP_MEAN + Z10 * FP_SD, FP_MEAN + Z90 * FP_SD
ATHLETE_Q = {"median athlete": 0.50, "10th percentile (fast)": 0.10, "1st percentile (fastest)": 0.01}

ASSUMPTIONS = [
    "Legitimate = gun-triggered; anticipations are not modelled. The fitted RT distributions come from valid "
    "championship starts (0.100-0.300 s) and are extrapolated below 0.100 s by a parametric family.",
    "The hold shifts the whole RT distribution (location only); it does not change its spread or shape.",
    "Haugen et al. (2013) |r| = 0.16 is an athlete-level correlation; converted to a slope with our within-"
    "championship RT SD and the championship hold SD of 0.158 s (Otsuka et al. 2017).",
    "Hazard scenario: RT is linear in the subjective hazard of the starter's hold distribution (Weber blur phi); "
    "athletes know the distribution; k is fixed across starter policies.",
    "Meet offsets are the championship deviations estimated in descriptive.json and act as pure location shifts.",
    "Athlete heterogeneity: normal athlete effects (SD from the crossed model); within-athlete ex-Gaussian fitted "
    "to conditional residuals; race-to-race variation added as a normal component.",
    "Parameter uncertainty = race-cluster bootstrap of the reference fit only; scenario inputs (r, slopes, phi, "
    "hold distribution) are fixed design values varied as sensitivities, not estimated.",
]


def load_desc(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("mock") and "mock" not in str(path):
        raise RuntimeError("descriptive input is MOCK")
    return d


def ref_policy_pdf(sd=FP_SD, mean=FP_MEAN):
    return hz.truncnorm_pdf(G, mean, sd, FP_LO, FP_HI)


def policies():
    g = G
    return {
        "championship (Normal 1.78, SD 0.158)": ref_policy_pdf(),
        "predictable (Normal 1.78, SD 0.08)": ref_policy_pdf(sd=0.08),
        "variable (Normal 1.78, SD 0.30)": ref_policy_pdf(sd=0.30),
        "uniform 1.30-2.26": hz.uniform_pdf(g, 1.30, 2.26),
        "non-ageing (1.30 + exponential, mean 1.78)": hz.shifted_exponential_pdf(g, 1.30, 1.78),
    }


def hazard_k(phi, sd_rt_s, r=HAUGEN_R):
    """k (s of RT per unit subjective hazard) giving corr(FP, RT) = -r under the championship policy."""
    g = G
    pdf = ref_policy_pdf()
    h = hz.hazard_curve(pdf=pdf, grid=G, phi=phi)
    w = pdf / np.trapezoid(pdf, g)
    ef, eh = np.trapezoid(w * g, g), np.trapezoid(w * h, g)
    cov = np.trapezoid(w * (g - ef) * (h - eh), g)
    sd_fp = np.sqrt(np.trapezoid(w * (g - ef) ** 2, g))
    return r * sd_fp * sd_rt_s / cov, h


def delta(scenario, fp, sd_rt_s, phi=0.25, policy_pdf=None, k=None, h_ref_at_mean=None):
    fp = np.asarray(fp, float)
    slope_h = HAUGEN_R * sd_rt_s / FP_SD
    if scenario == "none":
        return np.zeros_like(fp)
    if scenario == "haugen_slower":
        return slope_h * (fp - FP_MEAN)
    if scenario == "haugen_faster":
        return -slope_h * (fp - FP_MEAN)
    if scenario == "otsuka_lab":
        return OTSUKA_SLOPE * (fp - FP_MEAN)
    if scenario == "hazard":
        if k is None:
            k, h_ref = hazard_k(phi, sd_rt_s)
            h_ref_at_mean = np.interp(FP_MEAN, G, h_ref)
        pdf = ref_policy_pdf() if policy_pdf is None else policy_pdf
        h = hz.hazard_curve(pdf=pdf, grid=G, phi=phi)
        return -k * (np.interp(fp, G, h) - h_ref_at_mean)
    raise ValueError(scenario)


SCENARIOS = ["none", "haugen_slower", "haugen_faster", "hazard", "otsuka_lab"]


def p_fs(family, params, shift):
    """P(RT < 0.100) when the reference distribution is shifted by ``shift`` seconds."""
    return rtdist.cdf(family, params, FS_THRESHOLD - np.asarray(shift, float))


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--descriptive", required=True)
    ap.add_argument("--phi", type=float, default=0.25)
    ap.add_argument("--fp-models", default=None, help="fp_models.json: Seiko Ready Times and slope CI (data-calibrated block)")
    ap.add_argument("--calibration", default=None, help="calibration.json: Ready Time -> foreperiod calibration factor")
    args = ap.parse_args()
    out = resolve_out(args, "fairness")
    desc = load_desc(args.descriptive)
    nd = desc["numbers"]
    ref = desc["extra"]["reference_fits"]
    within = desc["extra"]["within_athlete"]
    vc = desc["extra"]["variance_components_ms2"]
    sd_rt_s = nd["sd_rt_within_compyear"]["value"] / 1000.0
    sexes = sorted({k.split("_")[0] for k in ref})
    families = ["exgauss", "slognorm", "swald"]
    meets = pd.DataFrame(desc["tables"].get("meet_effects", []))

    numbers, tables, extra = {}, {}, {"assumptions": ASSUMPTIONS}
    k_h, h_ref_curve = hazard_k(args.phi, sd_rt_s)
    h_ref_mean = float(np.interp(FP_MEAN, G, h_ref_curve))
    extra["hazard_k_s_per_unit"] = k_h
    extra["hold_distribution"] = {"mean": FP_MEAN, "sd": FP_SD, "p10": FP_P10, "p90": FP_P90}
    slope_h_ms = HAUGEN_R * sd_rt_s / FP_SD * 1000 / 10
    numbers["haugen_slope_ms_per_100ms"] = num(round(slope_h_ms, 3), unit="ms per 100 ms",
                                               desc="slope implied by |r|=0.16 with our within-championship RT SD and hold SD 0.158 s")
    numbers["otsuka_slope_ms_per_100ms"] = num(round(OTSUKA_SLOPE * 100, 3), unit="ms per 100 ms",
                                               desc="lab contrast of Otsuka et al. 2017 (156 vs 117 ms at 1.465 vs 2.096 s)")
    dh = delta("hazard", [FP_P10, FP_P90], sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
    numbers["hazard_shift_p10_to_p90_ms"] = num(round(float((dh[1] - dh[0]) * 1000), 3), unit="ms",
                                                desc=f"hazard scenario: RT change from the 10th to the 90th percentile hold (phi={args.phi})")

    # ---- 1. population-average curves and summaries ------------------------------------------------
    curve_rows, summ_rows = [], []
    w_fp = stats.norm.pdf(FP_GRID, FP_MEAN, FP_SD)
    w_fp /= w_fp.sum()
    for sex in sexes:
        for fam in families:
            key = f"{sex}_{fam}"
            if key not in ref:
                continue
            p0 = ref[key]["params"]
            draws = ref[key]["boot_params"]
            for sc in SCENARIOS:
                d_grid = delta(sc, FP_GRID, sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
                d_q = delta(sc, [FP_P10, FP_MEAN, FP_P90], sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
                pc = p_fs(fam, p0, d_grid)
                pq = p_fs(fam, p0, d_q)
                bq = np.array([p_fs(fam, dp, d_q) for dp in draws]) if draws else np.empty((0, 3))
                bavg = np.array([np.sum(w_fp * p_fs(fam, dp, d_grid)) for dp in draws]) if draws else np.empty(0)
                if fam == "exgauss" and draws:
                    bc = np.array([p_fs(fam, dp, d_grid) for dp in draws])
                    lo_c, hi_c = np.percentile(bc, [2.5, 97.5], axis=0)
                else:
                    lo_c = hi_c = np.full_like(pc, np.nan)
                for i, fpv in enumerate(FP_GRID):
                    curve_rows.append({"sex": sex, "family": fam, "scenario": sc, "fp": fpv,
                                       "shift_ms": d_grid[i] * 1000, "p": pc[i], "lo": lo_c[i], "hi": hi_c[i]})
                ratio = pq[2] / pq[0] if pq[0] > 0 else np.nan
                row = {"sex": sex, "family": fam, "scenario": sc,
                       "p_p10": pq[0], "p_median": pq[1], "p_p90": pq[2], "ratio_p90_p10": ratio,
                       "per_1000_avg": 1000 * np.sum(w_fp * pc)}
                if len(bq):
                    with np.errstate(divide="ignore", invalid="ignore"):
                        br = bq[:, 2] / bq[:, 0]
                    br[~np.isfinite(br)] = np.nan
                    row.update({"p_p10_lo": np.percentile(bq[:, 0], 2.5), "p_p10_hi": np.percentile(bq[:, 0], 97.5),
                                "p_p90_lo": np.percentile(bq[:, 2], 2.5), "p_p90_hi": np.percentile(bq[:, 2], 97.5),
                                "ratio_lo": np.nanpercentile(br, 2.5), "ratio_hi": np.nanpercentile(br, 97.5),
                                "per_1000_lo": 1000 * np.percentile(bavg, 2.5),
                                "per_1000_hi": 1000 * np.percentile(bavg, 97.5)})
                summ_rows.append(row)
    curves = pd.DataFrame(curve_rows)
    summ = pd.DataFrame(summ_rows)
    tables["curves"] = curves
    tables["summary"] = summ
    for _, r in summ.iterrows():
        tag = f"{r['scenario']}_{r['family']}_{r['sex']}"
        ci = lambda a, b: (float(f"{r[a]:.4g}"), float(f"{r[b]:.4g}")) if (a in r and pd.notna(r.get(a))) else None
        numbers[f"ratio_p90_p10_{tag}"] = num(float(f"{r['ratio_p90_p10']:.4g}"), ci=ci("ratio_lo", "ratio_hi"),
                                              desc=f"P(legit FS) at the 90th vs 10th percentile hold, {r['scenario']}, "
                                                   f"{r['family']}, sex={r['sex']} (SIMULATION)")
        numbers[f"per1000_{tag}"] = num(float(f"{r['per_1000_avg']:.4g}"), ci=ci("per_1000_lo", "per_1000_hi"),
                                        desc=f"legitimate starts scored <0.100 s per 1,000 starts, averaged over "
                                             f"championship holds, {r['scenario']}, {r['family']}, sex={r['sex']} (SIMULATION)")
        numbers[f"p_p10_{tag}"] = num(float(f"{r['p_p10']:.4g}"), ci=ci("p_p10_lo", "p_p10_hi"),
                                      desc=f"P(legit FS) at the 10th percentile hold ({FP_P10:.3f} s), {tag} (SIMULATION)")
        numbers[f"p_p90_{tag}"] = num(float(f"{r['p_p90']:.4g}"), ci=ci("p_p90_lo", "p_p90_hi"),
                                      desc=f"P(legit FS) at the 90th percentile hold ({FP_P90:.3f} s), {tag} (SIMULATION)")

    # ---- 2. athlete heterogeneity (ex-Gaussian hierarchy) ------------------------------------------
    ath_rows = []
    sd_ath = np.sqrt(vc["athlete"]) / 1000
    sd_race = np.sqrt(vc["race"]) / 1000
    for sex in sexes:
        if f"{sex}_exgauss" not in ref or sex not in within:
            continue
        pr = ref[f"{sex}_exgauss"]["params"]
        m_ref = pr["mu"] + pr["tau"]
        pw = within[sex]["params_s"]
        sig = float(np.sqrt(pw["sigma"] ** 2 + sd_race ** 2))
        # consistency: implied population average vs direct reference fit
        pop = {"mu": m_ref - pw["tau"], "sigma": float(np.sqrt(sig ** 2 + sd_ath ** 2)), "tau": pw["tau"]}
        extra.setdefault("hierarchy_check", {})[sex] = {
            "p_direct_ref_fit": float(p_fs("exgauss", pr, 0.0)),
            "p_implied_by_hierarchy": float(p_fs("exgauss", pop, 0.0))}
        for lab, q in ATHLETE_Q.items():
            a = stats.norm.ppf(q) * sd_ath
            pa = {"mu": m_ref + a - pw["tau"], "sigma": sig, "tau": pw["tau"]}
            for sc in SCENARIOS:
                d_q = delta(sc, [FP_P10, FP_MEAN, FP_P90], sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
                pq = p_fs("exgauss", pa, d_q)
                ath_rows.append({"sex": sex, "athlete": lab, "q": q, "athlete_mean_ms": (m_ref + a) * 1000,
                                 "scenario": sc, "p_p10": pq[0], "p_median": pq[1], "p_p90": pq[2],
                                 "ratio_p90_p10": pq[2] / pq[0] if pq[0] > 0 else np.nan})
    ath = pd.DataFrame(ath_rows)
    tables["athletes"] = ath
    extra["hierarchy_note"] = ("sensitivity only: normal athlete effects imply a population tail larger than the "
                               "direct reference fit (see hierarchy_check), so these athlete-level numbers are not used "
                               "for headline claims; the empirical split-half fast group below is used instead")

    # ---- 2b. empirical fast athletes (split-half selection, held-out starts) --------------------------
    fg = desc["extra"].get("fast_group") or {}
    fast_rows = []
    if fg.get("params"):
        pf, draws = fg["params"], fg.get("boot_params", [])
        for sc in SCENARIOS:
            d_q = delta(sc, [FP_P10, FP_MEAN, FP_P90], sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
            d_grid = delta(sc, FP_GRID, sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
            pq = p_fs("exgauss", pf, d_q)
            bq = np.array([p_fs("exgauss", dp, d_q) for dp in draws]) if draws else np.empty((0, 3))
            bavg = np.array([np.sum(w_fp * p_fs("exgauss", dp, d_grid)) for dp in draws]) if draws else np.empty(0)
            row = {"scenario": sc, "p_p10": pq[0], "p_median": pq[1], "p_p90": pq[2],
                   "ratio_p90_p10": pq[2] / pq[0] if pq[0] > 0 else np.nan,
                   "per_1000_avg": 1000 * np.sum(w_fp * p_fs("exgauss", pf, d_grid))}
            if len(bq):
                with np.errstate(divide="ignore", invalid="ignore"):
                    br = bq[:, 2] / bq[:, 0]
                row.update({"p_median_lo": np.percentile(bq[:, 1], 2.5), "p_median_hi": np.percentile(bq[:, 1], 97.5),
                            "ratio_lo": np.nanpercentile(br, 2.5), "ratio_hi": np.nanpercentile(br, 97.5),
                            "per_1000_lo": 1000 * np.percentile(bavg, 2.5), "per_1000_hi": 1000 * np.percentile(bavg, 97.5)})
            fast_rows.append(row)
        fdf = pd.DataFrame(fast_rows)
        tables["fast_group"] = fdf
        for _, r in fdf.iterrows():
            ci = lambda a, b: (float(f"{r[a]:.4g}"), float(f"{r[b]:.4g}")) if (a in r and pd.notna(r.get(a))) else None
            numbers[f"fast_per1000_{r['scenario']}"] = num(
                float(f"{r['per_1000_avg']:.4g}"), ci=ci("per_1000_lo", "per_1000_hi"),
                desc=f"fastest-quartile athletes (held-out starts): legitimate starts scored <0.100 s per 1,000, "
                     f"averaged over championship holds, {r['scenario']} (SIMULATION; men/R1/flat sprint/average championship)")
            numbers[f"fast_ratio_{r['scenario']}"] = num(
                float(f"{r['ratio_p90_p10']:.4g}"), ci=ci("ratio_lo", "ratio_hi"),
                desc=f"fastest-quartile athletes: P(legit FS) at the 90th vs 10th percentile hold, {r['scenario']} (SIMULATION)")

    # ---- 3. starter policies under the hazard scenario ------------------------------------------------
    pol_rows = []
    for name, pdf in policies().items():
        cdfp = np.cumsum(pdf) / np.sum(pdf)
        w = pdf / pdf.sum()
        p90_hold = float(np.interp(0.90, cdfp, G))
        d_all = delta("hazard", G, sd_rt_s, args.phi, policy_pdf=pdf, k=k_h, h_ref_at_mean=h_ref_mean)
        for sex in sexes:
            pr = ref.get(f"{sex}_exgauss", {}).get("params")
            if pr is None:
                continue
            pp = p_fs("exgauss", pr, d_all)
            pol_rows.append({"policy": name, "sex": sex, "p90_hold_s": p90_hold,
                             "mean_shift_ms": float(np.sum(w * d_all) * 1000),
                             "per_1000_avg": float(1000 * np.sum(w * pp)),
                             "p_at_p90_hold": float(np.interp(p90_hold, G, pp)),
                             "sd_shift_ms": float(np.sqrt(np.sum(w * (d_all - np.sum(w * d_all)) ** 2)) * 1000)})
    pol = pd.DataFrame(pol_rows)
    tables["policies"] = pol
    for _, r in pol[pol["sex"] == "M"].iterrows():
        slug = r["policy"].split(" (")[0].replace(" ", "_").replace("-", "_").replace(".", "")
        numbers[f"policy_per1000_{slug}_M"] = num(float(f"{r['per_1000_avg']:.4g}"),
                                                  desc=f"hazard scenario, men: legit FS per 1,000 starts under starter policy '{r['policy']}' (SIMULATION)",
                                                  sd_shift_ms=float(f"{r['sd_shift_ms']:.4g}"))

    # ---- 4. meets vs holds ----------------------------------------------------------------------------------
    meet_rows = []
    if not meets.empty:
        for sex in sexes:
            for fam in families:
                pr = ref.get(f"{sex}_{fam}", {}).get("params")
                if pr is None:
                    continue
                for _, m in meets.iterrows():
                    meet_rows.append({"sex": sex, "family": fam, "comp_year": m["comp_year"],
                                      "offset_ms": m["deviation_ms"],
                                      "p_median_hold": float(p_fs(fam, pr, m["deviation_ms"] / 1000))})
        mt = pd.DataFrame(meet_rows)
        tables["meets"] = mt
        for sex in sexes:
            s = mt[(mt["sex"] == sex) & (mt["family"] == "exgauss")]
            if s.empty:
                continue
            hi_m, lo_m = s.loc[s["p_median_hold"].idxmax()], s.loc[s["p_median_hold"].idxmin()]
            ratio = hi_m["p_median_hold"] / lo_m["p_median_hold"] if lo_m["p_median_hold"] > 0 else np.inf
            numbers[f"meet_p_max_{sex}"] = num(float(f"{hi_m['p_median_hold']:.4g}"), meet=hi_m["comp_year"],
                                               desc=f"P(legit FS) at the median hold at the fastest-scoring meet offset, ex-Gaussian, sex={sex} (SIMULATION)")
            numbers[f"meet_p_min_{sex}"] = num(float(f"{lo_m['p_median_hold']:.4g}"), meet=lo_m["comp_year"],
                                               desc=f"P(legit FS) at the median hold at the slowest-scoring meet offset, ex-Gaussian, sex={sex} (SIMULATION)")
            numbers[f"meet_ratio_{sex}"] = num(float(f"{ratio:.4g}") if np.isfinite(ratio) else None,
                                               desc=f"ratio of P(legit FS) between the fastest- and slowest-scoring meet offsets, sex={sex} (SIMULATION)")

    # ---- 5. foreperiod-aware threshold -------------------------------------------------------------------
    thr_rows = []
    for sc in SCENARIOS:
        d_q = delta(sc, [FP_P10, FP_P90], sd_rt_s, args.phi, k=k_h, h_ref_at_mean=h_ref_mean)
        thr_rows.append({"scenario": sc, "threshold_p10_ms": (FS_THRESHOLD + d_q[0]) * 1000,
                         "threshold_p90_ms": (FS_THRESHOLD + d_q[1]) * 1000})
        numbers[f"threshold_shift_{sc}_ms"] = num(round(float((d_q[1] - d_q[0]) * 1000), 3), unit="ms",
                                                  desc=f"change in a false-positive-matched threshold from the 10th to the 90th percentile hold, {sc}")
    tables["threshold"] = pd.DataFrame(thr_rows)

    # ---- 6. phi sensitivity for the hazard scenario ----------------------------------------------------------
    phi_rows = []
    for phi in (0.15, 0.25, 0.35):
        k_p, h_p = hazard_k(phi, sd_rt_s)
        hm = float(np.interp(FP_MEAN, G, h_p))
        d_q = delta("hazard", [FP_P10, FP_P90], sd_rt_s, phi, k=k_p, h_ref_at_mean=hm)
        for sex in sexes:
            pr = ref.get(f"{sex}_exgauss", {}).get("params")
            if pr is None:
                continue
            pq = p_fs("exgauss", pr, d_q)
            phi_rows.append({"phi": phi, "sex": sex, "k": k_p, "shift_p10_ms": d_q[0] * 1000,
                             "shift_p90_ms": d_q[1] * 1000, "ratio_p90_p10": pq[1] / pq[0]})
    tables["phi_sensitivity"] = pd.DataFrame(phi_rows)

    # ---- 7. data-calibrated block: measured holds (official Seiko) and the measured slope CI ------------
    inputs = [Path(args.descriptive)]
    if args.fp_models:
        fpm = json.loads(Path(args.fp_models).read_text(encoding="utf-8"))
        inputs.append(Path(args.fp_models))
        holds = np.array([row["foreperiod_s"] for row in fpm["tables"]["race_level"]], float)
        h10, h50, h90 = np.percentile(holds, [10, 50, 90])
        sl = fpm["numbers"]["slope_ms_per_100ms"]
        slopes = {"measured_point": sl["value"], "measured_ci_low": sl["ci95"][0], "measured_ci_high": sl["ci95"][1]}
        extra["measured_holds"] = {"n_races": int(len(holds)), "p10": h10, "median": h50, "p90": h90}
        cal_rows = []
        for sex in sexes:
            for fam in families:
                pr = ref.get(f"{sex}_{fam}", {}).get("params")
                draws = ref.get(f"{sex}_{fam}", {}).get("boot_params", [])
                if pr is None:
                    continue
                for lab, b in slopes.items():
                    dq = np.array([h10 - h50, 0.0, h90 - h50]) * 10 * b / 1000.0       # s
                    pq = p_fs(fam, pr, dq)
                    row = {"sex": sex, "family": fam, "slope_label": lab, "slope_ms_per_100ms": b,
                           "p_p10": pq[0], "p_median": pq[1], "p_p90": pq[2], "ratio_p90_p10": pq[2] / pq[0]}
                    if draws:
                        br = np.array([p_fs(fam, dp, dq) for dp in draws])
                        rr_ = br[:, 2] / br[:, 0]
                        row.update({"ratio_lo": np.nanpercentile(rr_, 2.5), "ratio_hi": np.nanpercentile(rr_, 97.5)})
                    cal_rows.append(row)
        cal = pd.DataFrame(cal_rows)
        tables["data_calibrated"] = cal
        # sensitivity: the fitted piecewise shape (slopes below / above the championship median hold)
        nb, na = fpm["numbers"].get("slope_below_median_ms_per_100ms"), fpm["numbers"].get("slope_above_median_ms_per_100ms")
        if nb and na:
            pw_rows = []
            for sex in sexes:
                pr = ref.get(f"{sex}_exgauss", {}).get("params")
                if pr is None:
                    continue
                for lab, bb, ba in (("point", nb["value"], na["value"]),
                                    ("steepest (CI ends)", nb["ci95"][0], na["ci95"][1])):
                    dq = np.array([(h10 - h50) * 10 * bb, 0.0, (h90 - h50) * 10 * ba]) / 1000.0
                    pq = p_fs("exgauss", pr, dq)
                    pw_rows.append({"sex": sex, "shape": lab, "slope_below": bb, "slope_above": ba,
                                    "p_p10": pq[0], "p_median": pq[1], "p_p90": pq[2],
                                    "ratio_p10_median": pq[0] / pq[1], "ratio_p90_median": pq[2] / pq[1]})
            pw = pd.DataFrame(pw_rows)
            tables["piecewise_sensitivity"] = pw
            r0 = pw[(pw["sex"] == sexes[0]) & (pw["shape"] == "point")].iloc[0]
            numbers["pw_ratio_p10_median"] = num(float(f"{r0['ratio_p10_median']:.4g}"),
                                                 desc=f"piecewise measured shape: P(legit FS) at the 10th percentile vs median hold, "
                                                      f"ex-Gaussian, sex={sexes[0]} (SIMULATION, sensitivity)")
            numbers["pw_ratio_p90_median"] = num(float(f"{r0['ratio_p90_median']:.4g}"),
                                                 desc=f"piecewise measured shape: P(legit FS) at the 90th percentile vs median hold, "
                                                      f"ex-Gaussian, sex={sexes[0]} (SIMULATION, sensitivity)")
        hg = np.round(np.linspace(float(np.percentile(holds, 1)), float(np.percentile(holds, 99)), 80), 4)
        cc = []
        for sex in sexes:
            pr = ref.get(f"{sex}_exgauss", {}).get("params")
            if pr is None:
                continue
            for lab, b in slopes.items():
                pp = p_fs("exgauss", pr, (hg - h50) * 10 * b / 1000.0)
                cc += [{"sex": sex, "slope_label": lab, "hold_s": hv, "p": pv} for hv, pv in zip(hg, pp)]
            hs_ready = fpm["numbers"]["haugen_slope_same_scale"]["value"] / 1000.0 * 10   # s per s of Ready Time
            for sc, sign in (("haugen_slower", 1), ("haugen_faster", -1)):
                pp = p_fs("exgauss", pr, sign * hs_ready * (hg - h50))
                cc += [{"sex": sex, "slope_label": sc, "hold_s": hv, "p": pv} for hv, pv in zip(hg, pp)]
        tables["cal_curves"] = pd.DataFrame(cc)
        tables["measured_holds"] = pd.DataFrame({"hold_s": np.sort(holds)})
        for _, r in cal[cal["family"] == "exgauss"].iterrows():
            numbers[f"cal_ratio_{r['slope_label']}_{r['sex']}"] = num(
                float(f"{r['ratio_p90_p10']:.4g}"),
                desc=f"P(legit FS) at the 90th vs 10th percentile Seiko Ready Time ({h90:.3f} vs {h10:.3f} s) with the "
                     f"measured slope at its {r['slope_label']} ({r['slope_ms_per_100ms']:.3g} ms/100 ms), "
                     f"ex-Gaussian, sex={r['sex']} (SIMULATION on measured inputs)")
        # largest plausible hold-driven change in either direction, men, ex-Gaussian
        sub = cal[(cal["family"] == "exgauss") & (cal["sex"] == sexes[0])]
        worst = float(max(sub["ratio_p90_p10"].max(), 1.0 / sub["ratio_p90_p10"].min()))
        numbers["cal_max_fold_change"] = num(float(f"{worst:.4g}"),
                                             desc=f"largest fold change in P(legit FS) between the 10th and 90th percentile "
                                                  f"Seiko Ready Time allowed by the slope's 95% CI, ex-Gaussian, sex={sexes[0]} (SIMULATION)")
        if args.calibration:
            cal_j = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
            inputs.append(Path(args.calibration))
            bcal = cal_j["numbers"]["calib_slope_b"]
            pr0 = ref[f"{sexes[0]}_exgauss"]["params"]
            for tag, bval in (("corrected", bcal["value"]), ("corrected_b_low", bcal["ci95"][0])):
                if not bval or bval <= 0:
                    continue
                folds = []
                for lab_, bslope in slopes.items():
                    # across the 10th-90th percentile of the (unobserved) foreperiod, the RT shift is the Ready-Time
                    # shift divided by sqrt(b) under classical error (slope / b, spread x sqrt(b))
                    dq = np.array([h10 - h50, 0.0, h90 - h50]) * 10 * bslope / 1000.0 / np.sqrt(bval)
                    pq = p_fs("exgauss", pr0, dq)
                    folds.append(pq[2] / pq[0])
                worst_c = float(max(max(folds), 1.0 / min(folds)))
                numbers[f"cal_max_fold_change_{tag}"] = num(
                    float(f"{worst_c:.4g}"), b=float(f"{bval:.4g}"),
                    desc=f"largest fold change in P(legit FS) across the 10th-90th percentile foreperiod after correcting "
                         f"the Ready-Time slope CI for proxy error (calibration factor b = {bval:.3g}), ex-Gaussian, "
                         f"sex={sexes[0]} (SIMULATION)")
        if "meets" in tables:
            mt = tables["meets"]
            s_ = mt[(mt["sex"] == sexes[0]) & (mt["family"] == "exgauss")]
            q25, q75 = np.percentile(s_["offset_ms"], [25, 75])
            pr = ref[f"{sexes[0]}_exgauss"]["params"]
            iqr_fold = float(p_fs("exgauss", pr, q25 / 1000) / p_fs("exgauss", pr, q75 / 1000))
            numbers["meet_iqr_fold_change"] = num(float(f"{iqr_fold:.4g}"),
                                                  desc=f"fold change in P(legit FS) between the 25th and 75th percentile "
                                                       f"championship offsets ({q25:.1f} vs {q75:.1f} ms), ex-Gaussian, "
                                                       f"sex={sexes[0]} (SIMULATION)")

    p = write_result(out, "fairness", numbers, inputs, args.mock, tables=tables,
                     extra=extra, seed=args.seed)
    show = summ[summ["family"] == "exgauss"][["sex", "scenario", "p_p10", "p_median", "p_p90", "ratio_p90_p10",
                                             "ratio_lo", "ratio_hi", "per_1000_avg"]]
    print(show.to_string(index=False))
    if "fast_group" in tables:
        print(tables["fast_group"].to_string(index=False))
    print(pol.to_string(index=False))
    if meet_rows:
        print(tables["meets"][tables["meets"]["family"] == "exgauss"].to_string(index=False))
    print(tables["threshold"].to_string(index=False))
    print(tables["phi_sensitivity"].to_string(index=False))
    print(json.dumps(extra.get("hierarchy_check"), indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
