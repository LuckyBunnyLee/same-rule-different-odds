"""H1-S4 and H6: the pre-registered analyses of analysis/prereg_addendum_trend.md (which adopts
analysis/prereg_systematic.md addendum 4), committed before any of them was computed.

H1-S4  SIMULATION. How probable is Haugen et al.'s (2013) reported correlation pattern (men 1997-2003 r = 0.16,
       women 1997-2003 r = 0.17, men 2003-2009 r = 0.16, all P < 0.001; women 2003-2009 not significant) if their r
       had been computed WITHIN championships, and how probable if computed on POOLED starts (the S3 design of
       systematic.py)? Evaluated at true within-championship effects r_w = 0, our estimate, our conservative upper
       bound (and 0.16 for context), with the likelihood ratio, the inversion r_star (smallest r_w that makes the
       pattern plausible under a within analysis) and the design uncertainty propagated over a 9-design grid.
H6     Is championship-level variation getting worse? (a) SD of the athlete-adjusted championship offsets by period
       (pre-2010, 2010-2019, 2020-2025) with bootstrap CIs, SD ratios and a dispersion trend; (b) the modelled rate of
       legitimate sub-0.100 s starts per championship (fairness model); (c) near-threshold recorded false starts
       with denominators.

Usage: .venv\\Scripts\\python.exe analysis\\trend.py --seed 20260928 --descriptive analysis/outputs/descriptive.json
           --calibration analysis/outputs/calibration.json --fairness analysis/outputs/fairness.json
           --sims 20000 --boot 5000 --perm 10000 --out analysis/outputs/trend.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import (add_common_args, attach_races, data_path, dedupe_sources, load_races, load_rt, num,
                    resolve_out, wilson_ci, write_result)
from fairness_sim import p_fs                                   # the fairness model (read-only reuse)
from systematic import _truncnorm_rows, haugen_layout, reml_between_within_sd   # S3 machinery (read-only reuse)

# ---- design constants (prereg_addendum_trend.md; not measurements) ----------------------------------------------
# Haugen et al. 2013 reported cells: (sex, era index, reported r); era 0 = "1997-2003", era 1 = "2003-2009"
HAUGEN_CELLS = (("M", 0, 0.16), ("W", 0, 0.17), ("M", 1, 0.16))
LENIENT_R = {("M", 0): 0.155, ("W", 0): 0.165, ("M", 1): 0.155}     # lowest values that round to the reported r
NS_CELL = ("W", 1)                                                    # women 2003-2009: not significant
CELLS = (("M", 0), ("W", 0), ("M", 1), ("W", 1))                      # storage order of the simulated cells
ALPHA_SIG, ALPHA_NS = 0.001, 0.05
P_WITHIN_BAR, P_POOLED_BAR = 0.01, 0.05                               # pre-specified rule
LR_HI, LR_LO = 10.0, 0.1                                              # addendum 4 likelihood rule
P_INVERT = 0.05                                                       # inversion: P(P3 | WITHIN) >= 0.05
R_HAUGEN = 0.16                                                       # context setting (not in any rule)
MIN_HITS = 200                                                        # per-cell share vs normal approximation
GRID_K, GRID_H = (4, 5, 6), (9, 11, 13)                               # championships per era x heats per champ
CELL5 = (5, 11)
STARTS_PER_HEAT, STARTS_PER_ATHLETE = 7.5, 3
HOLD_MEAN, HOLD_LO, HOLD_HI = 1.75, 1.3, 2.2                          # S3 (haugen_design.csv, cell5)
LITSD = (0.25, 0.16)                                                  # S3 cell5_litsd hold SDs (between, within)
RW_GRID = np.round(np.arange(0.0, 0.30001, 0.005), 3)

PERIODS = {"pre2010": ("WCH1999", "WCH2001", "WCH2003", "WCH2005", "WCH2007", "WCH2009"),
           "2010_2019": ("WCH2011", "WCH2013", "WCH2015", "WCH2017", "WCH2019"),
           "2020_2025": ("OG2020", "WCH2022", "WCH2023", "WCH2025", "OG2024")}
PERIOD_LABEL = {"pre2010": "pre-2010", "2010_2019": "2010-2019", "2020_2025": "2020-2025"}
WIC = ("WIC2024", "WIC2025")
YEAR_HELD = {"OG2020": 2021}                                          # Tokyo 2020 was held in 2021
NEAR_LO, NEAR_HI = 0.090, 0.0999                                      # descriptive.py: rt_s.between(0.090, 0.0999)


def sig(x, n=4):
    """Round to n significant digits (stored values; verdicts are computed from these)."""
    x = float(x)
    return x if (x == 0 or not np.isfinite(x)) else float(f"{x:.{n}g}")


# =====================================================================================================
# H1-S4 helpers (unit-tested in analysis/tests/test_trend.py)
# =====================================================================================================

def r_crit(alpha: float, n: int) -> float:
    """Smallest |r| whose naive two-sided t-test (n - 2 df) gives p < alpha (boundary value)."""
    t = stats.t.isf(alpha / 2, n - 2)
    return float(t / np.sqrt(n - 2 + t * t))


def beta_for_rw(r_w: float, sd_noise: float, sd_w: float) -> float:
    """Hold slope (ms per s) giving a population within-championship correlation r_w between the heat hold
    (within-championship SD sd_w, s) and RT (non-hold within-championship SD sd_noise, ms)."""
    return float(r_w * sd_noise / (sd_w * np.sqrt(1.0 - r_w * r_w)))


def r_of_beta(ss, beta):
    """Pearson r of hold x and y = z + beta x from the centred sums (..., 3) = Sxx, Sxz, Szz."""
    ss = np.asarray(ss, float)
    sxx, sxz, szz = ss[..., 0], ss[..., 1], ss[..., 2]
    sxy = sxz + beta * sxx
    syy = szz + 2.0 * beta * sxz + beta * beta * sxx
    return sxy / np.sqrt(sxx * syy)


def s4_design(K: int, H: int) -> dict:
    return {"n_champs": int(K), "heats_per_champ": int(H), "starts_per_heat": STARTS_PER_HEAT,
            "starts_per_athlete": STARTS_PER_ATHLETE, "hold_lo_s": HOLD_LO, "hold_hi_s": HOLD_HI,
            "truncate": "champ_mean"}


def simulate_s4(design: dict, par: dict, sims: int, rng, chunk: int = 1000) -> dict:
    """Simulate `sims` Haugen-style studies (2 eras x 2 sexes; championships shared by the sexes within an era).
    Returns the centred sums (Sxx, Sxz, Szz) of hold x with the non-hold part of RT z for every study and cell,
    for the WITHIN analysis (centred within championship) and the POOLED analysis (centred over the cell):
    arrays (sims, 4 cells, 3) in CELLS order, plus n (starts per cell).
    par: sd_b, sd_w (s); sd_champ, sd_race, sd_ath, sd_res (ms)."""
    heat_champ, start_heat, start_champ, ath, n_ath = haugen_layout(design)
    K, n_heat, N = int(design["n_champs"]), len(heat_champ), len(start_heat)
    per = N // K
    if not (np.all(np.bincount(start_champ) == per) and np.all(np.diff(start_champ) >= 0)):
        raise RuntimeError("layout is not in equal contiguous championship blocks")
    within = np.empty((sims, 4, 3))
    pooled = np.empty((sims, 4, 3))
    for s0 in range(0, sims, chunk):
        S = min(chunk, sims - s0)
        for era in (0, 1):
            cm = _truncnorm_rows(HOLD_MEAN, par["sd_b"], (S, K), HOLD_LO, HOLD_HI, rng)   # shared by the sexes
            g = rng.standard_normal((S, K)) * par["sd_champ"]                             # shared by the sexes
            for si in (0, 1):
                cell = 2 * era + si
                h = cm[:, heat_champ] + rng.standard_normal((S, n_heat)) * par["sd_w"]
                u = rng.standard_normal((S, n_heat)) * par["sd_race"]
                a = rng.standard_normal((S, n_ath)) * par["sd_ath"]
                e = rng.standard_normal((S, N)) * par["sd_res"]
                x = h[:, start_heat]
                z = u[:, start_heat] + a[:, ath] + e
                xc = x.reshape(S, K, per)
                xc = xc - xc.mean(2, keepdims=True)
                zc = z.reshape(S, K, per)
                zc = zc - zc.mean(2, keepdims=True)
                within[s0:s0 + S, cell] = np.stack([(xc * xc).sum((1, 2)), (xc * zc).sum((1, 2)),
                                                    (zc * zc).sum((1, 2))], axis=1)
                y0 = z + g[:, start_champ]
                xp = x - x.mean(1, keepdims=True)
                yp = y0 - y0.mean(1, keepdims=True)
                pooled[s0:s0 + S, cell] = np.stack([(xp * xp).sum(1), (xp * yp).sum(1), (yp * yp).sum(1)], axis=1)
    return {"within": within, "pooled": pooled, "n": int(N)}


def cell_prob_upper(r, thr: float) -> tuple[float, str]:
    """P(r >= thr) for one within-analysis cell: simulated share if >= MIN_HITS studies reach it, else the normal
    approximation with the simulated mean and SD."""
    r = np.asarray(r, float)
    hits = int((r >= thr).sum())
    if hits >= MIN_HITS:
        return hits / len(r), "share"
    return float(stats.norm.sf((thr - r.mean()) / r.std(ddof=1))), "normal"


def cell_prob_ns(r, rc: float) -> tuple[float, str]:
    """P(|r| < rc) (naive p >= alpha) for one within-analysis cell, same share / normal rule."""
    r = np.asarray(r, float)
    hits = int((np.abs(r) < rc).sum())
    if hits >= MIN_HITS:
        return hits / len(r), "share"
    m, s = r.mean(), r.std(ddof=1)
    return float(stats.norm.cdf((rc - m) / s) - stats.norm.cdf((-rc - m) / s)), "normal"


def product_rel_se(ps, methods, n_sims: int) -> float:
    """Delta-method relative Monte Carlo SE of a product of independent binomial shares (normal-approximated
    factors are treated as exact: their error is approximation error, reported by the method flags)."""
    v = sum((1 - p) / (p * n_sims) for p, m in zip(ps, methods) if m == "share" and p > 0)
    return float(np.sqrt(v))


def s4_evaluate(sim: dict, beta: float, lenient: bool = False) -> dict:
    """P3 / P4 under WITHIN and POOLED at one true hold slope beta, from the stored sufficient statistics."""
    n = sim["n"]
    rw = r_of_beta(sim["within"], beta)          # (S, 4)
    rp = r_of_beta(sim["pooled"], beta)
    S = rw.shape[0]
    rc_sig, rc_ns = r_crit(ALPHA_SIG, n), r_crit(ALPHA_NS, n)
    out = {"n": n, "r_crit_001": rc_sig, "r_crit_05": rc_ns}
    ps, meths, mask = [], [], np.ones(S, bool)
    for sex, era, r_rep in HAUGEN_CELLS:
        ci = CELLS.index((sex, era))
        thr = max(LENIENT_R[(sex, era)] if lenient else r_rep, rc_sig)
        p, m = cell_prob_upper(rw[:, ci], thr)
        ps.append(p)
        meths.append(m)
        tag = f"{sex}{era}"
        out[f"within_cell_{tag}"], out[f"within_cell_{tag}_method"] = p, m
        out[f"within_cell_{tag}_mean_r"], out[f"within_cell_{tag}_sd_r"] = float(rw[:, ci].mean()), float(rw[:, ci].std(ddof=1))
        out[f"pooled_cell_{tag}"] = float((rp[:, ci] >= thr).mean())
        out[f"pooled_cell_{tag}_mean_r"] = float(rp[:, ci].mean())
        mask &= rp[:, ci] >= thr
    ci_ns = CELLS.index(NS_CELL)
    p_ns, m_ns = cell_prob_ns(rw[:, ci_ns], rc_ns)
    out["within_cell_W1_ns"], out["within_cell_W1_ns_method"] = p_ns, m_ns
    out["p3_within"] = float(np.prod(ps))
    out["p3_within_rel_se"] = product_rel_se(ps, meths, S)
    out["p3_within_all_share"] = all(m == "share" for m in meths)
    out["p3_pooled"] = float(mask.mean())
    out["p3_pooled_se"] = float(np.sqrt(out["p3_pooled"] * (1 - out["p3_pooled"]) / S))
    mask4 = mask & (np.abs(rp[:, ci_ns]) < rc_ns)
    out["p4_within"] = out["p3_within"] * p_ns
    out["p4_pooled"] = float(mask4.mean())
    return out


def invert(grid, p, target: float = P_INVERT):
    """Smallest grid value with p >= target, linearly interpolated from the previous grid point; None if never."""
    grid, p = np.asarray(grid, float), np.asarray(p, float)
    hit = np.flatnonzero(p >= target)
    if not len(hit):
        return None
    i = int(hit[0])
    if i == 0:
        return float(grid[0])
    return float(grid[i - 1] + (target - p[i - 1]) / (p[i] - p[i - 1]) * (grid[i] - grid[i - 1]))


def s4_verdict(p_within_up: float, p_pooled_up: float) -> str:
    """Pre-specified rule (prereg_addendum_trend.md)."""
    if p_within_up >= P_WITHIN_BAR:
        return "WITHIN-CHAMPIONSHIP ANALYSIS NOT EXCLUDED"
    if p_pooled_up >= P_POOLED_BAR:
        return "WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE"
    return "INCONCLUSIVE (pattern improbable under both analyses)"


def lr_verdict(lr: float) -> str:
    """Addendum 4 likelihood rule, at our estimate."""
    if lr >= LR_HI:
        return "FAVOURS POOLED"
    if lr <= LR_LO:
        return "FAVOURS WITHIN"
    return "INCONCLUSIVE"


def inversion_verdict(r_star, r_up: float) -> str:
    """Addendum 4 inversion rule."""
    return ("WITHIN READING NEEDS r_w ABOVE OUR CI" if (r_star is None or r_star > r_up)
            else "WITHIN READING COMPATIBLE WITH OUR CI")


# =====================================================================================================
# H6 helpers (unit-tested in analysis/tests/test_trend.py)
# =====================================================================================================

def boot_sds(est: np.ndarray, se: np.ndarray, B: int, rng) -> np.ndarray:
    """Bootstrap SDs (ddof 1): championships resampled with replacement, each drawn offset redrawn from
    N(estimate, se^2)."""
    k = len(est)
    idx = rng.integers(0, k, size=(B, k))
    vals = est[idx] + se[idx] * rng.standard_normal((B, k))
    return vals.std(axis=1, ddof=1)


def f_ratio_ci(sd_num: float, k_num: int, sd_den: float, k_den: int) -> tuple[float, float]:
    """95% CI of SD_num / SD_den from the F distribution of the variance ratio (normal theory)."""
    R = (sd_num / sd_den) ** 2
    d1, d2 = k_num - 1, k_den - 1
    return float(np.sqrt(R / stats.f.ppf(0.975, d1, d2))), float(np.sqrt(R / stats.f.ppf(0.025, d1, d2)))


def classify_ratio(lo: float, hi: float) -> str:
    """H6 rule on the 95% CI of an SD ratio (recent / earlier)."""
    if lo > 1.0:
        return "WORSENING"
    if hi < 1.0:
        return "IMPROVING"
    return "PERSISTING, NOT WORSENING"


def slope(x, y):
    """OLS slope of y on x along the last axis."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xm, ym = x.mean(-1, keepdims=True), y.mean(-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return ((x - xm) * (y - ym)).sum(-1) / ((x - xm) ** 2).sum(-1)


def absdev_slope(x, y):
    """Slope of |y - OLS line of y on x| on x (dispersion trend around a linear mean trend)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    b = slope(x, y)
    a = y.mean(-1) - b * x.mean(-1)
    res = y - (np.asarray(a)[..., None] + np.asarray(b)[..., None] * x)
    return slope(x, np.abs(res))


def trend_block(year, off, fn, B: int, n_perm: int, rng) -> dict:
    """Slope per decade of fn(year, offsets); pairs-bootstrap percentile CI; two-sided permutation p."""
    year, off = np.asarray(year, float), np.asarray(off, float)
    k = len(year)
    obs = float(fn(year, off)) * 10.0
    idx = rng.integers(0, k, size=(B, k))
    bt = fn(year[idx], off[idx]) * 10.0
    ok = np.isfinite(bt)
    lo, hi = np.percentile(bt[ok], [2.5, 97.5])
    perm = np.argsort(rng.random((n_perm, k)), axis=1)
    pm = fn(year[perm], np.broadcast_to(off, (n_perm, k))) * 10.0
    p = (1 + int((np.abs(pm) >= abs(obs) - 1e-12).sum())) / (n_perm + 1)
    return {"slope": obs, "lo": float(lo), "hi": float(hi), "perm_p": float(p), "n_boot_used": int(ok.sum())}


def near_threshold_counts(started: pd.DataFrame) -> pd.DataFrame:
    """Per championship: starts, false starts, false starts with an RT, false starts with RT in [0.090, 0.100)."""
    s = started.assign(fs=started["is_fs"].astype(bool))
    s["fs_rt"] = s["fs"] & s["rt_s"].notna()
    s["near"] = s["fs_rt"] & s["rt_s"].between(NEAR_LO, NEAR_HI)
    g = s.groupby("comp_year", sort=True)
    return pd.DataFrame({"starts": g.size(), "fs": g["fs"].sum(), "fs_with_rt": g["fs_rt"].sum(),
                         "fs_near": g["near"].sum()}).astype(int).reset_index()


# =====================================================================================================
# H1-S4
# =====================================================================================================

def run_s4(args, numbers, tables, extra, desc, cal):
    inputs = []
    fpa_path = data_path("foreperiods.csv", False)
    inputs.append(fpa_path)
    fpa = pd.read_csv(fpa_path, encoding="utf-8-sig")
    fpa = fpa[(fpa["attempt_status"] == "valid") & fpa["foreperiod_s"].notna()].copy()
    fpa = fpa.sort_values(["race_id", "attempt"]).drop_duplicates("race_id", keep="last")
    fpa["comp"] = fpa["race_id"].str.split("-").str[0]
    sd_b, sd_w = reml_between_within_sd(fpa["foreperiod_s"], fpa["comp"])      # S3's REML hold SDs
    nd = desc["numbers"]
    par = {"sd_b": sd_b, "sd_w": sd_w, "sd_champ": float(nd["sd_championship_ms"]["value"]),
           "sd_race": float(nd["sd_race_ms"]["value"]), "sd_ath": float(nd["sd_athlete_ms"]["value"]),
           "sd_res": float(nd["sd_residual_ms"]["value"])}
    sd_noise = float(np.sqrt(par["sd_race"] ** 2 + par["sd_ath"] ** 2 + par["sd_res"] ** 2))
    r_est = float(cal["r_corrected"]["value"])
    r_up = float(cal["r_ci_high_at_b_low"]["value"])
    settings = {"zero": 0.0, "estimate": r_est, "upper": r_up, "haugen": R_HAUGEN}
    extra["s4_parameters"] = {**par, "sd_noise_ms": sd_noise, "hold_mean_s": HOLD_MEAN, "hold_trunc_s": [HOLD_LO, HOLD_HI],
                              "n_audio_races": int(len(fpa)), "n_audio_champs": int(fpa["comp"].nunique()),
                              "r_w_settings": settings}
    numbers["s4_sd_hold_between_s"] = num(round(sd_b, 4), unit="s",
                                          desc="S4 input (as S3): REML between-championship SD of audio foreperiods",
                                          sd_within_s=float(f"{sd_w:.4g}"), n_races=int(len(fpa)),
                                          n_champs=int(fpa["comp"].nunique()))
    numbers["s4_rw_estimate"] = num(r_est, desc="S4 input: true within-championship r at our estimate "
                                                "(calibration.r_corrected)")
    numbers["s4_rw_upper"] = num(r_up, desc="S4 input: true within-championship r at our conservative upper bound "
                                            "(calibration.r_ci_high_at_b_low)")

    rng = np.random.default_rng(args.seed + 401)
    designs = [(f"K{K}_H{H}", s4_design(K, H), par) for K in GRID_K for H in GRID_H]
    designs.append(("cell5_litsd", s4_design(*CELL5), {**par, "sd_b": LITSD[0], "sd_w": LITSD[1]}))
    rows, curve_rows = [], []
    res = {}           # tag -> {"settings": {name: eval}, "grid": [eval per RW_GRID]}
    for tag, dsg, p_ in designs:
        sim = simulate_s4(dsg, p_, args.sims, rng)
        noise_sd_w = p_["sd_w"]
        ev_set = {nm: s4_evaluate(sim, beta_for_rw(rw, sd_noise, noise_sd_w)) for nm, rw in settings.items()}
        ev_len = {nm: s4_evaluate(sim, beta_for_rw(rw, sd_noise, noise_sd_w), lenient=True)
                  for nm, rw in settings.items()}
        ev_grid = [s4_evaluate(sim, beta_for_rw(rw, sd_noise, noise_sd_w)) for rw in RW_GRID]
        res[tag] = {"settings": ev_set, "lenient": ev_len, "grid": ev_grid, "design": dsg}
        for nm, ev in ev_set.items():
            rows.append({"design": tag, "K": dsg["n_champs"], "H": dsg["heats_per_champ"], "setting": nm,
                         "r_w": settings[nm], "in_average": tag != "cell5_litsd",
                         "sd_hold_between_s": p_["sd_b"], "sd_hold_within_s": p_["sd_w"],
                         **{k: v for k, v in ev.items()},
                         "p3_within_lenient": ev_len[nm]["p3_within"], "p3_pooled_lenient": ev_len[nm]["p3_pooled"]})
        for rw, ev in zip(RW_GRID, ev_grid):
            curve_rows.append({"design": tag, "r_w": float(rw), "p3_within": ev["p3_within"],
                               "p3_pooled": ev["p3_pooled"], "p4_within": ev["p4_within"], "p4_pooled": ev["p4_pooled"]})
    tables["s4_designs"] = pd.DataFrame(rows)
    tables["s4_curve"] = pd.DataFrame(curve_rows)

    grid_tags = [f"K{K}_H{H}" for K in GRID_K for H in GRID_H]
    c5 = f"K{CELL5[0]}_H{CELL5[1]}"

    def avg(key, setting, which="settings"):
        return float(np.mean([res[t][which][setting][key] for t in grid_tags]))

    def rng_over(key, setting):
        v = [res[t]["settings"][setting][key] for t in grid_tags]
        return float(min(v)), float(max(v))

    def avg_se(setting):
        """Monte Carlo SEs of the design averages (designs simulated independently): pooled binomial; within by the
        delta method over simulated-share factors (normal-approximated factors carry approximation error instead)."""
        ev = [res[t]["settings"][setting] for t in grid_tags]
        se_p = float(np.sqrt(sum(e["p3_pooled_se"] ** 2 for e in ev))) / len(ev)
        se_w = float(np.sqrt(sum((e["p3_within"] * e["p3_within_rel_se"]) ** 2 for e in ev))) / len(ev)
        return se_w, se_p

    # design-averaged curves and inversion
    avg_curve_w = np.array([np.mean([res[t]["grid"][i]["p3_within"] for t in grid_tags]) for i in range(len(RW_GRID))])
    avg_curve_p = np.array([np.mean([res[t]["grid"][i]["p3_pooled"] for t in grid_tags]) for i in range(len(RW_GRID))])
    c5_curve_w = np.array([res[c5]["grid"][i]["p3_within"] for i in range(len(RW_GRID))])
    mono_w = bool(np.all(np.diff(avg_curve_w) >= 0))
    mono_p = bool(np.all(np.diff(avg_curve_p) >= 0))
    tables["s4_curve_average"] = pd.DataFrame({"r_w": RW_GRID, "p3_within_avg": avg_curve_w, "p3_pooled_avg": avg_curve_p,
                                               "p3_within_cell5": c5_curve_w})
    r_star = invert(RW_GRID, avg_curve_w)
    r_star_c5 = invert(RW_GRID, c5_curve_w)
    extra["s4_monotone_in_rw"] = {"within_design_avg": mono_w, "pooled_design_avg": mono_p}

    # ---- numbers (rounded first; verdicts use the stored values) -------------------------------------------------
    lab = {"zero": "r_w = 0", "estimate": "r_w = our estimate", "upper": "r_w = our conservative upper bound",
           "haugen": "r_w = 0.16 (Haugen-sized; context only)"}
    for nm in settings:
        pw, pp = sig(avg("p3_within", nm)), sig(avg("p3_pooled", nm))
        lo_w, hi_w = rng_over("p3_within", nm)
        lo_p, hi_p = rng_over("p3_pooled", nm)
        c5w, c5p = res[c5]["settings"][nm]["p3_within"], res[c5]["settings"][nm]["p3_pooled"]
        se_w, se_p = avg_se(nm)
        n_normal = sum(res[t]["settings"][nm][f"within_cell_{s}{e}_method"] == "normal"
                       for t in grid_tags for s, e, _ in HAUGEN_CELLS)
        c5_share = res[c5]["settings"][nm]["p3_within_all_share"]
        numbers[f"s4_p_within_{nm}"] = num(
            pw, desc=f"SIMULATION: P(Haugen's three significant cells | WITHIN-championship analysis, {lab[nm]}), "
                     f"design-averaged over the 9-design grid (product of independent per-cell probabilities; "
                     f"mc_se only when every factor is a simulated share, None when normal-approximated factors "
                     f"carry approximation error instead)",
            r_w=settings[nm], mc_se=sig(se_w, 3) if n_normal == 0 else None,
            n_cells_normal_approx=int(n_normal), n_cells=3 * len(grid_tags),
            cell5=sig(c5w), min_over_designs=sig(lo_w), max_over_designs=sig(hi_w),
            cell5_rel_mc_se=sig(res[c5]["settings"][nm]["p3_within_rel_se"], 3) if c5_share else None,
            cell5_all_cells_simulated_share=c5_share)
        numbers[f"s4_p_pooled_{nm}"] = num(
            pp, desc=f"SIMULATION: P(Haugen's three significant cells | POOLED analysis (S3 design), {lab[nm]}), "
                     f"design-averaged over the 9-design grid (joint simulated share)",
            r_w=settings[nm], mc_se=sig(se_p, 3), cell5=sig(c5p), min_over_designs=sig(lo_p), max_over_designs=sig(hi_p),
            cell5_mc_se=sig(res[c5]["settings"][nm]["p3_pooled_se"], 3), n_sims=args.sims)
        lr = pp / pw if pw > 0 else None
        c5lr = c5p / c5w if c5w > 0 else None
        lrs = [res[t]["settings"][nm]["p3_pooled"] / res[t]["settings"][nm]["p3_within"] for t in grid_tags
               if res[t]["settings"][nm]["p3_within"] > 0]
        numbers[f"s4_lr_{nm}"] = num(sig(lr) if lr is not None else None,
                                     desc=f"SIMULATION: likelihood ratio P(pattern | POOLED) / P(pattern | WITHIN), "
                                          f"{lab[nm]}, design-averaged probabilities",
                                     r_w=settings[nm], cell5=sig(c5lr) if c5lr is not None else None,
                                     min_over_designs=sig(min(lrs)) if lrs else None,
                                     max_over_designs=sig(max(lrs)) if lrs else None)
        # full pattern P4 and lenient thresholds
        numbers[f"s4_full_p_within_{nm}"] = num(sig(avg("p4_within", nm)),
                                                desc=f"SIMULATION (secondary): P(full pattern incl. women 2003-2009 not "
                                                     f"significant | WITHIN, {lab[nm]}), design-averaged", r_w=settings[nm])
        numbers[f"s4_full_p_pooled_{nm}"] = num(sig(avg("p4_pooled", nm)),
                                                desc=f"SIMULATION (secondary): P(full pattern | POOLED, {lab[nm]}), "
                                                     f"design-averaged", r_w=settings[nm])
        fw, fp = numbers[f"s4_full_p_within_{nm}"]["value"], numbers[f"s4_full_p_pooled_{nm}"]["value"]
        numbers[f"s4_full_lr_{nm}"] = num(sig(fp / fw) if fw > 0 else None,
                                          desc=f"SIMULATION (secondary): likelihood ratio for the full pattern, {lab[nm]}",
                                          r_w=settings[nm])
        lw = sig(float(np.mean([res[t]["lenient"][nm]["p3_within"] for t in grid_tags])))
        lp = sig(float(np.mean([res[t]["lenient"][nm]["p3_pooled"] for t in grid_tags])))
        numbers[f"s4_lenient_p_within_{nm}"] = num(lw, desc=f"SIMULATION (sensitivity): P3 | WITHIN with rounding-lenient "
                                                            f"thresholds 0.155/0.165/0.155, {lab[nm]}, design-averaged",
                                                   r_w=settings[nm])
        numbers[f"s4_lenient_p_pooled_{nm}"] = num(lp, desc=f"SIMULATION (sensitivity): P3 | POOLED with rounding-lenient "
                                                            f"thresholds, {lab[nm]}, design-averaged", r_w=settings[nm])
        ls = res["cell5_litsd"]["settings"][nm]
        numbers[f"s4_litsd_p_within_{nm}"] = num(sig(ls["p3_within"]),
                                                 desc=f"SIMULATION (sensitivity): P3 | WITHIN, cell5 layout with S3's "
                                                      f"cell5_litsd hold SDs (0.25 / 0.16 s), {lab[nm]}", r_w=settings[nm])
        numbers[f"s4_litsd_p_pooled_{nm}"] = num(sig(ls["p3_pooled"]),
                                                 desc=f"SIMULATION (sensitivity): P3 | POOLED, cell5 layout with S3's "
                                                      f"cell5_litsd hold SDs, {lab[nm]}", r_w=settings[nm])

    # the S3 check: pooled, r_w = 0, one cell (men 1997-2003) at cell5 = S3 cell5's P(r >= 0.16)
    ev0 = res[c5]["settings"]["zero"]
    sim_c5_p_ge016 = ev0["pooled_cell_M0"]      # threshold here is max(0.16, r_crit) - see s4_evaluate
    numbers["s4_cell5_pooled_cell_m9703_p"] = num(
        sig(sim_c5_p_ge016), desc="SIMULATION check: P(pooled r >= max(0.16, r for p < 0.001)) in one cell "
                                  "(men 1997-2003), cell5 design, r_w = 0 (compare S3 h1s3_cell5_p_ge016_sig)",
        n_sims=args.sims, r_crit_001=sig(ev0["r_crit_001"], 5))

    # inversion
    numbers["s4_r_star"] = num(round(r_star, 4) if r_star is not None else None,
                               desc="SIMULATION: smallest true within-championship r at which a WITHIN analysis gives "
                                    "Haugen's three significant cells with probability >= 0.05 (design-averaged; grid "
                                    "0-0.30 by 0.005, linear interpolation); None = above 0.30",
                               cell5=round(r_star_c5, 4) if r_star_c5 is not None else None,
                               r_est=r_est, r_est_ci95=list(cal["r_corrected"]["ci95"]), r_up=r_up)

    # ---- verdicts ------------------------------------------------------------------------------------------------
    pw_up, pp_up = numbers["s4_p_within_upper"]["value"], numbers["s4_p_pooled_upper"]["value"]
    verdict = s4_verdict(pw_up, pp_up)
    alt_est = s4_verdict(pw_up, numbers["s4_p_pooled_estimate"]["value"])
    alt_zero = s4_verdict(pw_up, numbers["s4_p_pooled_zero"]["value"])
    per_design = {t: s4_verdict(sig(res[t]["settings"]["upper"]["p3_within"]), sig(res[t]["settings"]["upper"]["p3_pooled"]))
                  for t in grid_tags}
    share_meet = float(np.mean([v == "WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE" for v in per_design.values()]))
    numbers["s4_verdict"] = num(verdict, desc="pre-registered S4 verdict (coordinator's rule, prereg_addendum_trend.md): "
                                              "IMPLAUSIBLE if P(P3 | WITHIN, r_up) < 0.01 and P(P3 | POOLED, r_up) >= 0.05 "
                                              "(design-averaged); NOT EXCLUDED if P(P3 | WITHIN, r_up) >= 0.01; else INCONCLUSIVE",
                                p_within_upper=pw_up, p_pooled_upper=pp_up,
                                verdict_if_pooled_at_estimate=alt_est, verdict_if_pooled_at_zero=alt_zero,
                                cell5_verdict=per_design[c5], share_of_designs_implausible=sig(share_meet),
                                per_design=per_design)
    lr_est = numbers["s4_lr_estimate"]["value"]
    numbers["s4_verdict_lr"] = num(lr_verdict(lr_est) if lr_est is not None else "INCONCLUSIVE",
                                   desc="addendum 4 likelihood rule: FAVOURS POOLED if LR at our estimate >= 10, FAVOURS "
                                        "WITHIN if <= 0.1, otherwise INCONCLUSIVE",
                                   lr_estimate=lr_est, lr_upper=numbers["s4_lr_upper"]["value"])
    rs = numbers["s4_r_star"]["value"]
    numbers["s4_verdict_inversion"] = num(inversion_verdict(rs, r_up),
                                          desc="addendum 4 inversion rule: NEEDS r_w ABOVE OUR CI if r_star > our "
                                               "conservative upper bound, otherwise COMPATIBLE",
                                          r_star=rs, r_up=r_up)
    extra["s4_design_grid"] = {t: {"K": res[t]["design"]["n_champs"], "H": res[t]["design"]["heats_per_champ"],
                                   "starts_per_cell": res[t]["settings"]["zero"]["n"],
                                   "r_crit_001": res[t]["settings"]["zero"]["r_crit_001"]} for t in grid_tags}
    extra["s4_caveats"] = [
        "Before 2010 a false start did not disqualify outright (pre-2003: DQ on an athlete's own second false start; "
        "2003-2009: first false start in a race charged to the field), so anticipation, and with it the within-"
        "championship hold effect in 1997-2009, may genuinely differ from ours (2022-2025, zero tolerance); r_star "
        "states how large it would have had to be.",
        "Haugen et al.'s design is a reconstruction (lit/systematic_forensics.md section 1.2; full text closed).",
        "Championship mean holds and offsets are drawn independently; an alignment like ours would favour POOLED further.",
        "Both sexes get the same design; far-tail WITHIN probabilities rest on a normal approximation (method flags).",
    ]
    return inputs


# =====================================================================================================
# H6
# =====================================================================================================

def run_h6(args, numbers, tables, extra, desc, fair):
    inputs = []
    me = pd.DataFrame(desc["tables"]["meet_effects"])[["comp_year", "deviation_ms", "se", "lo", "hi", "n"]].copy()
    me["year"] = me["comp_year"].str[-4:].astype(int)
    me["year_held"] = [YEAR_HELD.get(c, y) for c, y in zip(me["comp_year"], me["year"])]
    per_of = {c: p for p, cs in PERIODS.items() for c in cs}
    me["period"] = me["comp_year"].map(per_of).fillna("indoor")
    missing = [c for cs in PERIODS.values() for c in cs if c not in set(me["comp_year"])]
    if missing:
        raise SystemExit(f"championships missing from descriptive.json meet_effects: {missing}")
    off = me.set_index("comp_year")["deviation_ms"]
    se = me.set_index("comp_year")["se"]

    # ---- (a) dispersion by period ------------------------------------------------------------------------------
    def period_block(pdef: dict, rng) -> dict:
        out = {}
        for p, cs in pdef.items():
            e, s_ = off[list(cs)].to_numpy(float), se[list(cs)].to_numpy(float)
            sd = float(e.std(ddof=1))
            out[p] = {"k": len(cs), "sd": sd, "boot": boot_sds(e, s_, args.boot, rng),
                      "sd_net": float(np.sqrt(max(0.0, e.var(ddof=1) - float(np.mean(s_ ** 2))))),
                      "mean": float(e.mean()), "champs": list(cs)}
        return out

    def ratio(blk, a, b) -> dict:
        r = blk[a]["sd"] / blk[b]["sd"]
        bt = blk[a]["boot"] / blk[b]["boot"]
        lo, hi = np.percentile(bt, [2.5, 97.5])
        flo, fhi = f_ratio_ci(blk[a]["sd"], blk[a]["k"], blk[b]["sd"], blk[b]["k"])
        return {"ratio": r, "lo": float(lo), "hi": float(hi), "f_lo": flo, "f_hi": fhi}

    blk = period_block(PERIODS, np.random.default_rng(args.seed + 451))
    r_main = ratio(blk, "2020_2025", "pre2010")
    r_sec = ratio(blk, "2020_2025", "2010_2019")
    sens_wic = {**PERIODS, "2020_2025": PERIODS["2020_2025"] + WIC}
    blk_wic = period_block(sens_wic, np.random.default_rng(args.seed + 452))
    sens_wch = {p: tuple(c for c in cs if c.startswith("WCH")) for p, cs in PERIODS.items()}
    blk_wch = period_block(sens_wch, np.random.default_rng(args.seed + 453))
    r_wic, r_wch = ratio(blk_wic, "2020_2025", "pre2010"), ratio(blk_wch, "2020_2025", "pre2010")

    per_rows = []
    for p, b in blk.items():
        lo, hi = np.percentile(b["boot"], [2.5, 97.5])
        sub = me[me["period"] == p]
        f_, s_ = sub.loc[sub["deviation_ms"].idxmin()], sub.loc[sub["deviation_ms"].idxmax()]
        numbers[f"h6_sd_ms_{p}"] = num(round(b["sd"], 3), ci=(round(float(lo), 3), round(float(hi), 3)), unit="ms",
                                       desc=f"H6(a) SD of athlete-adjusted championship offsets, {PERIOD_LABEL[p]} "
                                            f"(bootstrap CI: championships resampled within period, offsets redrawn)",
                                       k=b["k"], champs=b["champs"], sd_net_ms=round(b["sd_net"], 3),
                                       fastest=f_["comp_year"], fastest_ms=round(float(f_["deviation_ms"]), 2),
                                       slowest=s_["comp_year"], slowest_ms=round(float(s_["deviation_ms"]), 2))
        per_rows.append({"period": p, "k": b["k"], "sd_ms": b["sd"], "sd_lo": float(lo), "sd_hi": float(hi),
                         "sd_net_ms": b["sd_net"], "mean_ms": b["mean"], "fastest": f_["comp_year"],
                         "fastest_ms": float(f_["deviation_ms"]), "slowest": s_["comp_year"],
                         "slowest_ms": float(s_["deviation_ms"])})
    for key, rr, lab_ in (("h6_sd_ratio_recent_pre2010", r_main, "SD(2020-2025) / SD(pre-2010) (primary)"),
                          ("h6_sd_ratio_recent_2010s", r_sec, "SD(2020-2025) / SD(2010-2019) (secondary)"),
                          ("h6_sens_wic_sd_ratio_recent_pre2010", r_wic,
                           "sensitivity: SD(2020-2025 incl. WIC2024/2025) / SD(pre-2010)"),
                          ("h6_sens_wch_sd_ratio_recent_pre2010", r_wch,
                           "sensitivity (Seiko only, OG dropped): SD(WCH 2022-2025) / SD(WCH pre-2010)")):
        numbers[key] = num(round(rr["ratio"], 3), ci=(round(rr["lo"], 3), round(rr["hi"], 3)),
                           desc=f"H6(a) {lab_}; bootstrap percentile CI (f_ci95 = F-distribution CI, normal theory)",
                           f_ci95=[round(rr["f_lo"], 3), round(rr["f_hi"], 3)])
    for key in ("h6_sd_ratio_recent_2010s", "h6_sens_wic_sd_ratio_recent_pre2010", "h6_sens_wch_sd_ratio_recent_pre2010"):
        lo_, hi_ = numbers[key]["ci95"]
        numbers[key]["classification"] = classify_ratio(lo_, hi_)
    lo_m, hi_m = numbers["h6_sd_ratio_recent_pre2010"]["ci95"]
    numbers["h6_verdict"] = num(classify_ratio(lo_m, hi_m),
                                desc="pre-registered H6 verdict: WORSENING if the bootstrap 95% CI of SD(2020-2025) / "
                                     "SD(pre-2010) lies above 1, IMPROVING if below 1, otherwise PERSISTING, NOT "
                                     "WORSENING ('not worsening' = no credible increase, not evidence of stability)",
                                ratio=numbers["h6_sd_ratio_recent_pre2010"]["value"], ci95=[lo_m, hi_m],
                                f_ci95=numbers["h6_sd_ratio_recent_pre2010"]["f_ci95"],
                                secondary=numbers["h6_sd_ratio_recent_2010s"]["classification"],
                                sens_wic=numbers["h6_sens_wic_sd_ratio_recent_pre2010"]["classification"],
                                sens_wch=numbers["h6_sens_wch_sd_ratio_recent_pre2010"]["classification"])
    extra["h6_sensitivity_sds"] = {"wic": {p: {"k": b["k"], "sd": b["sd"]} for p, b in blk_wic.items()},
                                   "wch_only": {p: {"k": b["k"], "sd": b["sd"]} for p, b in blk_wch.items()}}

    # ---- (a) trend over the 16 outdoor championships --------------------------------------------------------------
    od = me[me["period"] != "indoor"].sort_values(["year_held", "comp_year"])
    yr, ov = od["year_held"].to_numpy(float), od["deviation_ms"].to_numpy(float)
    tr = trend_block(yr, ov, absdev_slope, args.boot, args.perm, np.random.default_rng(args.seed + 461))
    ta = trend_block(yr, ov, lambda x, y: slope(x, np.abs(y)), args.boot, args.perm, np.random.default_rng(args.seed + 462))
    numbers["h6_trend_absdev_ms_per_decade"] = num(
        round(tr["slope"], 3), ci=(round(tr["lo"], 3), round(tr["hi"], 3)), unit="ms per decade",
        desc="H6(a) dispersion trend (primary): slope of |offset - linear time trend| on year, 16 outdoor championships "
             "1999-2025; pairs-bootstrap CI; two-sided permutation p", perm_p=sig(tr["perm_p"], 3),
        n_champs=int(len(od)), n_boot_used=tr["n_boot_used"])
    numbers["h6_trend_absoffset_ms_per_decade"] = num(
        round(ta["slope"], 3), ci=(round(ta["lo"], 3), round(ta["hi"], 3)), unit="ms per decade",
        desc="H6(a) sensitivity: slope of |offset| (deviation from the 18-championship mean) on year, 16 outdoor "
             "championships; pairs-bootstrap CI; two-sided permutation p", perm_p=sig(ta["perm_p"], 3),
        n_champs=int(len(od)), n_boot_used=ta["n_boot_used"])
    f16, s16 = od.loc[od["deviation_ms"].idxmin()], od.loc[od["deviation_ms"].idxmax()]
    f18, s18 = me.loc[me["deviation_ms"].idxmin()], me.loc[me["deviation_ms"].idxmax()]
    numbers["h6_offset_fastest_ms"] = num(round(float(f16["deviation_ms"]), 2), unit="ms",
                                          desc="H6 fastest-scoring (most negative) athlete-adjusted offset, 16 outdoor "
                                               "championships", champ=f16["comp_year"], year_held=int(f16["year_held"]),
                                          period=f16["period"], all18_champ=f18["comp_year"])
    numbers["h6_offset_slowest_ms"] = num(round(float(s16["deviation_ms"]), 2), unit="ms",
                                          desc="H6 slowest-scoring (most positive) athlete-adjusted offset, 16 outdoor "
                                               "championships", champ=s16["comp_year"], year_held=int(s16["year_held"]),
                                          period=s16["period"], all18_champ=s18["comp_year"])
    tables["h6_periods"] = pd.DataFrame(per_rows)

    # ---- (b) modelled rate of legitimate sub-0.100 s starts (fairness model, men, ex-Gaussian) ---------------------
    ref = desc["extra"]["reference_fits"]["M_exgauss"]
    rate = 1000.0 * np.asarray(p_fs("exgauss", ref["params"], me["deviation_ms"].to_numpy(float) / 1000.0), float)
    fm = pd.DataFrame(fair["tables"]["meets"])
    fm = fm[(fm["sex"] == "M") & (fm["family"] == "exgauss")].set_index("comp_year")["p_median_hold"] * 1000.0
    bad = [c for c, r_ in zip(me["comp_year"], rate) if abs(r_ - fm[c]) > 1e-4 * max(abs(fm[c]), 1e-12)]
    if bad:
        raise SystemExit(f"(b) does not reproduce fairness.json meets: {bad}")
    rng_b = np.random.default_rng(args.seed + 481)
    e_all, s_all = me["deviation_ms"].to_numpy(float), me["se"].to_numpy(float)
    draws = np.array([1000.0 * np.asarray(p_fs("exgauss", bp, (e_all + s_all * rng_b.standard_normal(len(e_all))) / 1000.0))
                      for bp in ref["boot_params"]])                       # (n_ref_boot, 18)
    me["rate_per1000"] = rate
    me["rate_lo"], me["rate_hi"] = np.percentile(draws, 2.5, axis=0), np.percentile(draws, 97.5, axis=0)
    col = {c: i for i, c in enumerate(me["comp_year"])}
    hi_r, lo_r = me.loc[me["rate_per1000"].idxmax()], me.loc[me["rate_per1000"].idxmin()]
    numbers["h6_rate_per1000_max"] = num(sig(hi_r["rate_per1000"]), ci=(sig(hi_r["rate_lo"]), sig(hi_r["rate_hi"])),
                                         desc="H6(b) SIMULATION (fairness model): highest modelled rate of legitimate "
                                              "(gun-triggered) starts scored < 0.100 s per 1,000, men's reference "
                                              "ex-Gaussian shifted by the championship offset (descriptive CI: bootstrap "
                                              "reference fits x offset redraws)", champ=hi_r["comp_year"])
    numbers["h6_rate_per1000_min"] = num(sig(lo_r["rate_per1000"]), ci=(sig(lo_r["rate_lo"]), sig(lo_r["rate_hi"])),
                                         desc="H6(b) SIMULATION (fairness model): lowest modelled rate of legitimate "
                                              "starts scored < 0.100 s per 1,000 (men)", champ=lo_r["comp_year"])
    for p, cs in PERIODS.items():
        ix = [col[c] for c in cs]
        pr = rate[ix]
        med_d = np.median(draws[:, ix], axis=1)
        max_d = draws[:, ix].max(axis=1)
        imax, imin = int(np.argmax(pr)), int(np.argmin(pr))
        numbers[f"h6_rate_per1000_median_{p}"] = num(
            sig(float(np.median(pr))), ci=(sig(np.percentile(med_d, 2.5)), sig(np.percentile(med_d, 97.5))),
            desc=f"H6(b) SIMULATION: median over {PERIOD_LABEL[p]} championships of the modelled legitimate sub-0.100 s "
                 f"rate per 1,000 (men); descriptive CI", k=len(cs),
            max=sig(float(pr[imax])), max_champ=cs[imax],
            max_ci95=[sig(np.percentile(max_d, 2.5)), sig(np.percentile(max_d, 97.5))],
            min=sig(float(pr[imin])), min_champ=cs[imin])
        numbers[f"h6_rate_span_fold_{p}"] = num(sig(float(pr[imax] / pr[imin])),
                                                desc=f"H6(b) SIMULATION: max / min modelled legitimate sub-0.100 s rate "
                                                     f"across {PERIOD_LABEL[p]} championships (men)",
                                                max_champ=cs[imax], min_champ=cs[imin])

    # ---- (c) near-threshold recorded false starts (factual) --------------------------------------------------------
    rt, used = load_rt(False)
    races, rused = load_races(False)
    inputs += used + rused
    rt = attach_races(dedupe_sources(rt), races)
    started = rt[rt["rt_s"].notna() | rt["is_fs"]].copy()
    cnt = near_threshold_counts(started)
    nd = desc["numbers"]
    fs_tab = pd.DataFrame(desc["tables"]["false_starts"])
    fs_tab = fs_tab[fs_tab["by"] == "comp_year"].set_index("level")
    c_idx = cnt.set_index("comp_year")
    problems = []
    if int(cnt["fs_near"].sum()) != int(nd["fs_near_threshold_090_100"]["value"]):
        problems.append("near-threshold total")
    by_meet = {c: int(v) for c, v in c_idx["fs_near"].items() if v > 0}
    if by_meet != {str(k): int(v) for k, v in nd["fs_near_threshold_090_100"]["by_meet"].items()}:
        problems.append("near-threshold by championship")
    if int(cnt["fs_with_rt"].sum()) != int(nd["fs_recorded_with_rt"]["value"]):
        problems.append("false starts with RT")
    for c, r_ in fs_tab.iterrows():
        if c not in c_idx.index or int(c_idx.loc[c, "starts"]) != int(r_["starts"]) or int(c_idx.loc[c, "fs"]) != int(r_["fs"]):
            problems.append(f"starts/fs {c}")
    if problems:
        raise SystemExit(f"(c) recount does not reproduce descriptive.json: {problems}")
    me = me.merge(cnt, on="comp_year", how="left")
    tables["h6_championships"] = me[["comp_year", "period", "year", "year_held", "deviation_ms", "se", "lo", "hi",
                                     "rate_per1000", "rate_lo", "rate_hi", "starts", "fs", "fs_with_rt", "fs_near"]]
    top = me.loc[me["fs_near"].idxmax()]
    total_near = int(me["fs_near"].sum())
    numbers["h6_fs_near_total"] = num(total_near, desc="H6(c) recorded false starts with RT in [0.090, 0.100) s, all "
                                                       "18 championships (factual; recounted = descriptive)",
                                      n_fs_with_rt=int(me["fs_with_rt"].sum()), n_fs=int(me["fs"].sum()),
                                      n_starts=int(me["starts"].sum()),
                                      by_champ={c: int(v) for c, v in zip(me["comp_year"], me["fs_near"]) if v > 0})
    numbers["h6_fs_near_top_champ_count"] = num(int(top["fs_near"]),
                                                desc="H6(c) near-threshold false starts at the championship with the most "
                                                     "(value = total means all occurred there)",
                                                champ=top["comp_year"], total=total_near, starts=int(top["starts"]),
                                                fs=int(top["fs"]), fs_with_rt=int(top["fs_with_rt"]),
                                                rate_per1000_modelled=sig(top["rate_per1000"]))
    for p, cs in list(PERIODS.items()) + [("indoor", WIC)]:
        sub = me[me["comp_year"].isin(cs)]
        k_, n_ = int(sub["fs_near"].sum()), int(sub["starts"].sum())
        lo_, hi_ = wilson_ci(k_, n_)
        numbers[f"h6_fs_near_{p}"] = num(k_, desc=f"H6(c) near-threshold recorded false starts [0.090, 0.100) s, "
                                                  f"{PERIOD_LABEL.get(p, 'World Indoors (WIC2024, WIC2025)')} "
                                                  f"(factual; Wilson CI of the rate per 1,000 starts in per_1000_ci95)",
                                         starts=n_, fs=int(sub["fs"].sum()), fs_with_rt=int(sub["fs_with_rt"].sum()),
                                         per_1000=sig(1000.0 * k_ / n_), per_1000_ci95=[sig(1000 * lo_), sig(1000 * hi_)],
                                         champs=list(cs))
    extra["h6_caveats"] = [
        "False-start recording differs by source: from 2015 official PDF labels (TR16.8) plus RT; 1999-2013 rows come "
        "from Fiore et al.'s file, where a false start is visible only as an RT below 0.100 s. Near-threshold counts "
        "therefore compare across championships of one source only.",
        "(b) is a model output (reference distribution extrapolated below 0.100 s, offsets as pure location shifts); "
        "the CIs carry reference-fit and offset uncertainty only.",
        "Offsets are redrawn independently per championship in the H6(a) bootstrap (joint covariance not stored).",
        "Periods hold 5-6 championships each, so SD ratios have wide intervals: 'not worsening' means no credible "
        "increase, not evidence of stability.",
    ]
    return inputs


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--descriptive", required=True)
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--fairness", required=True)
    ap.add_argument("--sims", type=int, default=20000, help="simulated Haugen studies per design (S4)")
    ap.add_argument("--boot", type=int, default=5000, help="bootstrap replicates (H6)")
    ap.add_argument("--perm", type=int, default=10000, help="permutations for the H6 trend test")
    args = ap.parse_args()
    if args.mock:
        raise SystemExit("trend.py has no mock mode (it reads only registered real outputs)")
    out = resolve_out(args, "trend")
    desc = json.loads(Path(args.descriptive).read_text(encoding="utf-8"))
    cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    fair = json.loads(Path(args.fairness).read_text(encoding="utf-8"))
    for nm, d in (("descriptive", desc), ("calibration", cal), ("fairness", fair)):
        if d.get("mock"):
            raise SystemExit(f"{nm} input is MOCK")
    numbers, tables = {}, {}
    extra = {"prereg": ["analysis/prereg_addendum_trend.md", "analysis/prereg_systematic.md (addendum 4)"],
             "design_constants": {"haugen_cells": [list(c) for c in HAUGEN_CELLS], "lenient_r": {f"{k[0]}{k[1]}": v for k, v in LENIENT_R.items()},
                                  "alpha_sig": ALPHA_SIG, "alpha_ns": ALPHA_NS, "p_within_bar": P_WITHIN_BAR,
                                  "p_pooled_bar": P_POOLED_BAR, "lr_bars": [LR_LO, LR_HI], "p_invert": P_INVERT,
                                  "min_hits": MIN_HITS, "grid_K": list(GRID_K), "grid_H": list(GRID_H),
                                  "starts_per_heat": STARTS_PER_HEAT, "starts_per_athlete": STARTS_PER_ATHLETE,
                                  "hold_mean_s": HOLD_MEAN, "hold_trunc_s": [HOLD_LO, HOLD_HI], "litsd_s": list(LITSD),
                                  "periods": {k: list(v) for k, v in PERIODS.items()}, "year_held": YEAR_HELD,
                                  "near_threshold_s": [NEAR_LO, NEAR_HI]}}
    inputs = [Path(args.descriptive), Path(args.calibration), Path(args.fairness)]
    inputs += run_s4(args, numbers, tables, extra, desc, cal["numbers"])
    inputs += run_h6(args, numbers, tables, extra, desc, fair)
    seen, uniq = set(), []
    for p in inputs:
        k = str(Path(p).resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(Path(p))
    p = write_result(out, "trend", numbers, uniq, False, tables=tables, extra=extra, seed=args.seed)
    for k, val in numbers.items():
        print(f"{k:44s} {val.get('value')!s:>40} {val.get('ci95', '')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
