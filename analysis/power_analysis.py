"""Deliverable 1 - simulation-based power analysis for the RT-foreperiod association.

Question: how many races (about 8 athletes nested in each race) are needed to detect an
athlete-level RT-foreperiod correlation of the size reported by Haugen, Shalfawi & Tonnessen
(2013), |r| ~= 0.16, and what slope (ms of RT per 100 ms of foreperiod) does that imply?

Data-generating model (standardised so Var(RT) = 1 within a competition):
    x_j ~ N(0, 1)                         foreperiod of race j (race-level predictor)
    y_ij = r * x_j + u_j + e_ij           RT of athlete i in race j
    u_j ~ N(0, icc * (1 - r^2))           residual race effect (timing system, conditions...)
    e_ij ~ N(0, (1 - icc) * (1 - r^2))    athlete-level noise (or ex-Gaussian, sensitivity)
    x~_j = x_j + N(0, lam^2)              measured foreperiod, lam = sd_measurement / sd_FP
so the marginal athlete-level corr(x, y) equals r, and icc is the share of the non-FP
variance that is shared within a race.

Primary test: OLS of race-mean RT on measured foreperiod (t-test, N-2 df, two-sided 0.05).
For a race-level predictor with equal cluster sizes this is the GLS / mixed-model estimator;
decision agreement with statsmodels MixedLM (random race intercept) is checked on a subset.
Common random numbers are used across N, r and ICC so the curves are smooth and monotone.

Usage:  .venv\\Scripts\\python.exe analysis\\power_analysis.py [--sims 10000] [--mock]
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import add_common_args, num, rel, resolve_out, write_result

R_GRID = [0.10, 0.16, 0.20, 0.30]
ICC_GRID = [0.00, 0.05, 0.10, 0.20]
N_GRID = [10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300, 400]


# ------------------------------------------------------------------------------------
# simulation core (common random numbers)
# ------------------------------------------------------------------------------------

class Draws:
    """Standard-normal building blocks for `sims` datasets of up to `n_max` races."""

    def __init__(self, sims, n_max, m, rng, resid="normal", sizes=None):
        self.sims, self.n_max, self.m = sims, n_max, m
        self.x = rng.standard_normal((sims, n_max))
        self.zu = rng.standard_normal((sims, n_max))
        self.zme = rng.standard_normal((sims, n_max))
        m_max = m if sizes is None else int(max(sizes))
        if sizes is None:
            self.size = np.full((sims, n_max), m, float)
        else:
            self.size = rng.choice(np.asarray(sizes), size=(sims, n_max)).astype(float)
        ebar = np.zeros((sims, n_max))
        # accumulate athlete noise race-means in chunks to limit memory
        for k in range(m_max):
            if resid == "normal":
                ek = rng.standard_normal((sims, n_max))
            else:  # ex-Gaussian, tau/sigma = 1, standardised to unit variance
                ek = (rng.standard_normal((sims, n_max)) + rng.exponential(1.0, (sims, n_max)) - 1.0) / np.sqrt(2)
            ebar += np.where(k < self.size, ek, 0.0)
        self.ebar = ebar / self.size

    def reject(self, r, icc, n, lam=0.0, alpha=0.05):
        var_u = icc * (1 - r ** 2)
        var_e = (1 - icc) * (1 - r ** 2)
        x = self.x[:, :n]
        ybar = r * x + np.sqrt(var_u) * self.zu[:, :n] + np.sqrt(var_e) * self.ebar[:, :n]
        x_obs = x + lam * self.zme[:, :n] if lam > 0 else x
        return _ols_t_reject(x_obs, ybar, alpha)

    def power(self, r, icc, n, lam=0.0, alpha=0.05):
        return float(self.reject(r, icc, n, lam, alpha).mean())


def _ols_t_reject(x, y, alpha):
    n = x.shape[1]
    xc = x - x.mean(1, keepdims=True)
    yc = y - y.mean(1, keepdims=True)
    sxx = (xc ** 2).sum(1)
    b = (xc * yc).sum(1) / sxx
    resid = yc - b[:, None] * xc
    s2 = (resid ** 2).sum(1) / (n - 2)
    t = b / np.sqrt(s2 / sxx)
    return 2 * stats.t.sf(np.abs(t), n - 2) < alpha


def naive_type1(icc, n, m, sims, rng, alpha=0.05):
    """Athlete-level OLS that ignores nesting, under r = 0."""
    x = rng.standard_normal((sims, n))
    y = (np.sqrt(icc) * rng.standard_normal((sims, n))[..., None] +
         np.sqrt(1 - icc) * rng.standard_normal((sims, n, m)))
    xs = np.repeat(x[..., None], m, axis=-1).reshape(sims, -1)
    rej_naive = _ols_t_reject(xs, y.reshape(sims, -1), alpha).mean()
    rej_means = _ols_t_reject(x, y.mean(-1), alpha).mean()
    return float(rej_naive), float(rej_means)


def analytic_power(r, icc, m, n, alpha=0.05, lam=0.0):
    rc = _race_level_r(r, icc, m, lam)
    return float(stats.norm.cdf(np.arctanh(rc) * np.sqrt(n - 3) - stats.norm.ppf(1 - alpha / 2)))


def analytic_n(r, icc, m, power=0.80, alpha=0.05, lam=0.0):
    """Fisher-z approximation on race means (cross-check of the simulation)."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return (z / np.arctanh(_race_level_r(r, icc, m, lam))) ** 2 + 3


def _race_level_r(r, icc, m, lam=0.0):
    var_u = icc * (1 - r ** 2)
    var_e = (1 - icc) * (1 - r ** 2)
    return r / np.sqrt(r ** 2 + var_u + var_e / m) / np.sqrt(1 + lam ** 2)


def n_for_power(D: Draws, r, icc, target, lam=0.0):
    """Smallest N with simulated power >= target (every integer N scanned, CRN)."""
    for n in range(5, D.n_max + 1):
        if D.power(r, icc, n, lam) >= target:
            return n
    return float("nan")


def mde_r(D: Draws, n, icc, target=0.80):
    rs = np.round(np.arange(0.02, 0.80, 0.0025), 4)
    lo, hi = 0, len(rs) - 1                   # power is monotone in r under CRN: bisection
    if D.power(rs[hi], icc, n) < target:
        return float("nan")
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if D.power(rs[mid], icc, n) >= target:
            hi = mid
        else:
            lo = mid
    return float(rs[hi])


def mixedlm_validation(r, icc, n_races, m, sims, rng):
    """Compare race-mean OLS and statsmodels MixedLM decisions on identical datasets."""
    import statsmodels.formula.api as smf
    agree = rej_means = rej_mlm = fails = 0
    var_u, var_e = icc * (1 - r ** 2), (1 - icc) * (1 - r ** 2)
    for _ in range(sims):
        x = rng.standard_normal(n_races)
        y = r * x[:, None] + np.sqrt(var_u) * rng.standard_normal(n_races)[:, None] + \
            np.sqrt(var_e) * rng.standard_normal((n_races, m))
        d = pd.DataFrame({"y": y.ravel(), "x": np.repeat(x, m), "g": np.repeat(np.arange(n_races), m)})
        rm = bool(_ols_t_reject(x[None, :], y.mean(1)[None, :], 0.05)[0])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                rl = bool(smf.mixedlm("y ~ x", d, groups="g").fit(reml=True).pvalues["x"] < 0.05)
            except Exception:
                fails += 1
                continue
        agree += int(rm == rl)
        rej_means += int(rm)
        rej_mlm += int(rl)
    k = sims - fails
    return {"sims": k, "agreement": agree / k, "power_race_means": rej_means / k, "power_mixedlm": rej_mlm / k}


def empirical_inputs(path):
    """Optional data-driven inputs from a real descriptive.json (explicit --descriptive)."""
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("mock"):
        raise RuntimeError("descriptive input is a MOCK result")
    nums = d.get("numbers", {})
    got = {"source": rel(p)}
    if "icc_race_within_compyear" in nums:
        got["icc"] = nums["icc_race_within_compyear"]["value"]
        got["icc_ci"] = nums["icc_race_within_compyear"].get("ci95")
    if "sd_rt_within_compyear" in nums:
        got["sd_rt"] = nums["sd_rt_within_compyear"]["value"] / 1000.0  # ms -> s
    return got


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--descriptive", default=None, help="real descriptive.json for observed ICC/SD")
    ap.add_argument("--sims", type=int, default=10000)
    ap.add_argument("--m", type=int, default=8, help="athletes per race")
    ap.add_argument("--r", type=float, default=0.16)
    ap.add_argument("--validate-sims", type=int, default=200)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    out = resolve_out(args, "power")
    emp = {} if args.mock else empirical_inputs(args.descriptive)
    icc_list = list(ICC_GRID)
    if emp.get("icc") is not None:
        icc_list.append(round(float(emp["icc"]), 3))

    D = Draws(args.sims, max(N_GRID), args.m, rng)

    # ---- power curves -------------------------------------------------------------
    rows = []
    for r in R_GRID:
        for icc in icc_list:
            for n in N_GRID:
                pw = D.power(r, icc, n)
                rows.append({"r": r, "icc": icc, "n_races": n, "n_rts": n * args.m, "power": pw,
                             "mc_se": np.sqrt(pw * (1 - pw) / args.sims),
                             "power_analytic": analytic_power(r, icc, args.m, n)})
    curves = pd.DataFrame(rows)
    fine = pd.DataFrame([{"icc": icc, "n_races": n, "power": D.power(args.r, icc, n)}
                         for icc in icc_list for n in range(8, 401, 2)])

    # ---- N for 80% / 90% power at |r| = 0.16 ---------------------------------------------
    nreq = []
    for icc in icc_list:
        for target in (0.80, 0.90):
            ns = n_for_power(D, args.r, icc, target)
            nreq.append({"r": args.r, "icc": icc, "power": target, "n_races_sim": ns,
                         "n_races_analytic": float(np.ceil(analytic_n(args.r, icc, args.m, target))),
                         "n_rts_sim": ns * args.m})
    nreq_df = pd.DataFrame(nreq)

    # ---- sensitivities (ICC 0.10) --------------------------------------------------------------
    sens = [{"scenario": "baseline (normal residuals, 8 per race, exact FP)",
             "n_races_80": n_for_power(D, args.r, 0.10, 0.8)}]
    for sd_me in (0.03, 0.06):
        sens.append({"scenario": f"FP measurement error SD {sd_me} s (SD_FP 0.158 s)",
                     "n_races_80": n_for_power(D, args.r, 0.10, 0.8, lam=sd_me / 0.158)})
    D_eg = Draws(args.sims // 2, 200, args.m, rng, resid="exgauss")
    sens.append({"scenario": "ex-Gaussian residuals (tau/sigma = 1)",
                 "n_races_80": n_for_power(D_eg, args.r, 0.10, 0.8)})
    D_sz = Draws(args.sims // 2, 200, args.m, rng, sizes=[6, 7, 7, 8, 8, 8, 8, 8, 8, 9])
    sens.append({"scenario": "cluster sizes 6-9 (mean 7.7)", "n_races_80": n_for_power(D_sz, args.r, 0.10, 0.8)})
    del D_eg, D_sz
    for s in sens:
        s["icc"] = 0.10
    sens_df = pd.DataFrame(sens)

    # ---- type I error when nesting is ignored ----------------------------------------------
    t1 = []
    for icc in (0.0, 0.05, 0.10, 0.20):
        a, b = naive_type1(icc, 50, args.m, args.sims, rng)
        t1.append({"icc": icc, "n_races": 50, "type1_naive_athlete_ols": a, "type1_race_means": b})
    t1_df = pd.DataFrame(t1)


    # ---- minimum detectable |r| --------------------------------------------------------------
    mde = [{"n_races": n, "icc": icc, "mde_r_80": mde_r(D, n, icc)}
           for n in (20, 30, 50, 75, 100, 150, 200, 300, 400) for icc in (0.0, 0.10, 0.20)]
    mde_df = pd.DataFrame(mde)

    # ---- MixedLM agreement ----------------------------------------------------------------------
    val = {}
    if args.validate_sims > 0:
        for n in (40, 70):
            val[f"N{n}_icc0.10"] = mixedlm_validation(args.r, 0.10, n, args.m, args.validate_sims, rng)

    # ---- slope implied by r ----------------------------------------------------------------------
    sd_rt_grid = [0.018, 0.022, 0.026]
    if emp.get("sd_rt"):
        sd_rt_grid = sorted(set(sd_rt_grid + [round(float(emp["sd_rt"]), 4)]))
    slope_df = pd.DataFrame([{"r": args.r, "sd_rt_s": s, "sd_fp_s": f,
                              "slope_ms_per_100ms": args.r * s / f * 100.0}
                             for s in sd_rt_grid for f in (0.158, 0.20, 0.25)])

    # ---- JSON ---------------------------------------------------------------------------------
    numbers = {}
    for row in nreq:
        tag = f"{row['icc']:.3f}" if row["icc"] not in ICC_GRID else f"{row['icc']:.2f}"
        numbers[f"n_races_{int(row['power'] * 100)}_icc{tag}"] = num(
            row["n_races_sim"], unit="races",
            desc=f"races for {int(row['power'] * 100)}% power, |r|={args.r}, residual race ICC={row['icc']}",
            analytic=row["n_races_analytic"])
    for _, rr in slope_df.iterrows():
        numbers[f"slope_sdrt{rr.sd_rt_s}_sdfp{rr.sd_fp_s}"] = num(
            round(rr.slope_ms_per_100ms, 2), unit="ms per 100 ms FP",
            desc=f"slope implied by |r|={args.r} with SD_RT={rr.sd_rt_s} s, SD_FP={rr.sd_fp_s} s")
    for row in t1:
        numbers[f"type1_naive_icc{row['icc']:.2f}"] = num(round(row["type1_naive_athlete_ols"], 3),
            desc=f"type I error of athlete-level OLS ignoring nesting (50 races, ICC={row['icc']})")
        numbers[f"type1_racemeans_icc{row['icc']:.2f}"] = num(round(row["type1_race_means"], 3),
            desc=f"type I error of race-mean regression (50 races, ICC={row['icc']})")
    for i, s in enumerate(sens):
        numbers[f"sens{i}_n80"] = num(s["n_races_80"], unit="races",
                                      desc=f"races for 80% power at ICC 0.10: {s['scenario']}")
    for row in mde:
        numbers[f"mde_r80_N{row['n_races']}_icc{row['icc']:.2f}"] = num(
            round(row["mde_r_80"], 3), desc=f"minimum detectable |r| (80% power), {row['n_races']} races, ICC={row['icc']}")
    for k, v in val.items():
        numbers[f"mixedlm_agreement_{k}"] = num(round(v["agreement"], 3),
            desc=f"decision agreement, race-mean OLS vs statsmodels MixedLM ({v['sims']} datasets)",
            power_race_means=v["power_race_means"], power_mixedlm=v["power_mixedlm"])
    extra = {"m": args.m, "sims": args.sims, "alpha": 0.05, "r": args.r, "icc_grid": icc_list,
             "empirical_inputs": emp,
             "sd_fp_note": "SD_FP 0.158 s = Otsuka et al. 2017 championship holds (lit/novelty.md [V])"}
    tables = {"curves": curves, "curves_fine": fine, "n_required": nreq_df, "sensitivity": sens_df,
              "type1": t1_df, "mde": mde_df, "implied_slope": slope_df,
              "mixedlm_validation": [dict(k=k, **v) for k, v in val.items()]}
    inputs = [Path(emp["source"])] if emp.get("source") else []
    p = write_result(out, "power", numbers, inputs, args.mock, tables=tables, extra=extra, seed=args.seed)
    print(nreq_df.to_string(index=False))
    print(sens_df.to_string(index=False))
    print(t1_df.to_string(index=False))
    print(mde_df.pivot(index="n_races", columns="icc", values="mde_r_80").to_string())
    print(slope_df.to_string(index=False))
    print(json.dumps(val, indent=1))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
