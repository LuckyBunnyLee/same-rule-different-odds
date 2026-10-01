"""Systematic (athlete-independent) variation in official reaction times: the pre-registered analyses
of analysis/prereg_systematic.md (committed before any of them was computed).

H1  False-positive mechanism for the hold effect (232-race Seiko Ready Time sample of fp_models.py)
    (a) within-championship mixed model (reproduces fp_models M1; asserted)
    (b) the same model without championship effects (race + athlete random intercepts kept)
    (c) naive athlete-level Pearson r over all starts, pooled over championships (Haugen-style):
        uncentred (primary), championship-centred (control), audio-calibrated foreperiod scale (secondary)
    (d) championship mean Ready Time vs championship RT offset (descriptive; 4 / 5 / 3 championships)
    S1  SIMULATION, observed structure: fitted championship offsets, race/athlete/residual SDs, observed
        Ready Times; true within-championship slope 0 and = the (a) estimate; naive pooled r
    S2  SIMULATION, exchangeable championships: championship RT offsets and mean Ready Times redrawn
        independently in every dataset
    S3  SIMULATION, Haugen et al. 2013 design (only when --haugen-design is given; see the prereg addendum)
H2  Sensitivity of 'human limit' estimates to championship structure (all valid RTs of descriptive.py)
    P(RT < 0.100) and the 1e-3 barrier (0.001 quantile), per sex and family (ex-Gaussian, shifted lognormal,
    shifted Wald; left-truncated fits from rtdist.py): (a) pooled, (b) athlete-adjusted championship offsets
    removed, (c) per championship; race-cluster bootstrap CIs; pooled-vs-adjusted shift, per-championship
    spread (with a DerSimonian-Laird noise guard) and family-to-family spread; pre-registered verdicts.
Confounder audit (prereg addendum 3; post-hoc diagnostics addendum 5):
H3  rule-era contrasts (pre-2003 / 2003-2009 / 2010+) under championship sampling: Haugen-matched subsets, a
    random-championship model and a same-rule null; verdicts on sign and on the published +30 / -4 ms effects
H4  athlete-adjusted sex gap by championship (sex x championship interaction, LRT, DerSimonian-Laird)
H5  venue dependence inside Fiore et al. 2025's published GG model (quadrature; per-venue effects read from
    their vector figure); reproduction check against their tables
O2  optional: RT vs 100 m time, pooled vs championship-centred vs within race

Usage: .venv\\Scripts\\python.exe analysis\\systematic.py --seed 20260928 --descriptive analysis/outputs/descriptive.json
           --fp-models analysis/outputs/fp_models.json --calibration analysis/outputs/calibration.json
           --out analysis/outputs/systematic.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
from scipy import stats

import rtdist
from common import (ROUND_ORDER, add_common_args, attach_races, data_path, dedupe_sources, load_fp_sources,
                    load_races, load_rt, num, resolve_out, valid_rt_mask, write_result)
from fp_models import FX as FX_WITHIN
from lmm import fit_formula

# ---- design constants (prereg_systematic.md; not measurements) --------------------------------------
HAUGEN_R = 0.16                  # Haugen et al. 2013, athlete-level r (positive = slower after longer holds)
P_NONTRIVIAL = 0.05              # "non-trivial probability" in the H1 rule
MATERIAL_MS = 10.0               # H2 materiality bar
THRESH_FIORE_S, THRESH_BROSNAN_S = 0.094, 0.119   # published threshold proposals (their gap = reference scale)
BARRIER_Q = 1e-3                 # tail probability that defines the barrier (Fiore et al. 2025)
FP_CENTRE = 1.78                 # centring of Ready Time in fp_models.py (fp_c100)
FAMILIES = ("exgauss", "slognorm", "swald")
PRIMARY_FAMILY, PRIMARY_SEX = "exgauss", "M"
EXCLUDE_HOLD_COMPS = ("WIC2025",)                  # as in the registered fp_models.py command
FX_NOCHAMP = "C(sex, Treatment('M')) + C(round, Treatment('R1')) + C(event_type, Treatment('flat'))"
Z975 = 1.959963984540054


# =====================================================================================================
# statistics helpers (unit-tested in analysis/tests/test_systematic.py)
# =====================================================================================================

def pearson(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    xc, yc = x - x.mean(), y - y.mean()
    return float((xc @ yc) / np.sqrt((xc @ xc) * (yc @ yc)))


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    """Naive Fisher-z 95% CI (observations treated as independent)."""
    z, se = np.arctanh(r), 1.0 / np.sqrt(n - 3)
    return float(np.tanh(z - Z975 * se)), float(np.tanh(z + Z975 * se))


def naive_p(r: float, n: int) -> float:
    """Two-sided p of the naive t-test of a Pearson r (observations treated as independent)."""
    t = r * np.sqrt((n - 2) / (1 - r * r))
    return float(2 * stats.t.sf(abs(t), n - 2))


def race_sums(x, y, race_codes, n_races) -> np.ndarray:
    """Per-race sufficient statistics of a pooled Pearson r: rows n, Sx, Sy, Sxx, Syy, Sxy (6 x R)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    return np.stack([np.bincount(race_codes, minlength=n_races).astype(float),
                     np.bincount(race_codes, x, n_races), np.bincount(race_codes, y, n_races),
                     np.bincount(race_codes, x * x, n_races), np.bincount(race_codes, y * y, n_races),
                     np.bincount(race_codes, x * y, n_races)])


def r_from_totals(T) -> np.ndarray:
    """Pearson r from totals (..., 6) = n, Sx, Sy, Sxx, Syy, Sxy."""
    T = np.asarray(T, float)
    n, sx, sy, sxx, syy, sxy = (T[..., i] for i in range(6))
    return (n * sxy - sx * sy) / np.sqrt((n * sxx - sx ** 2) * (n * syy - sy ** 2))


def r_centred_from_totals(Tc) -> np.ndarray:
    """Pearson r after centring x and y within groups, from per-group totals (..., G, 6)."""
    Tc = np.asarray(Tc, float)
    n, sx, sy, sxx, syy, sxy = (Tc[..., i] for i in range(6))
    cxy = (sxy - sx * sy / n).sum(-1)
    cxx = (sxx - sx ** 2 / n).sum(-1)
    cyy = (syy - sy ** 2 / n).sum(-1)
    return cxy / np.sqrt(cxx * cyy)


def strat_multiplicities(race_group, n_boot: int, rng) -> np.ndarray:
    """(B, R) resampling counts: races drawn with replacement within their group (championship)."""
    race_group = np.asarray(race_group)
    K = np.zeros((n_boot, len(race_group)))
    rows = np.arange(n_boot)[:, None]
    for g in np.unique(race_group):
        ids = np.flatnonzero(race_group == g)
        draw = rng.integers(0, len(ids), size=(n_boot, len(ids)))
        np.add.at(K, (rows, ids[draw]), 1.0)
    return K


def rowwise_r(X, Y) -> np.ndarray:
    """Pearson r of each row of Y with X (X shared 1-D, or one row per row of Y)."""
    Yc = Y - Y.mean(1, keepdims=True)
    if np.ndim(X) == 1:
        Xc = X - X.mean()
        return (Yc @ Xc) / np.sqrt((Yc ** 2).sum(1) * (Xc @ Xc))
    Xc = X - X.mean(1, keepdims=True)
    return (Xc * Yc).sum(1) / np.sqrt((Xc ** 2).sum(1) * (Yc ** 2).sum(1))


def centre_rows(M, onehot, counts) -> np.ndarray:
    """Subtract each group's mean within every row of M (onehot: N x G, counts: G)."""
    return M - ((M @ onehot) / counts) @ onehot.T


def summarize_r(r, thr: float = HAUGEN_R) -> dict:
    r = np.asarray(r, float)
    q = np.percentile(r, [2.5, 50, 97.5])
    p_ge, p_abs = float((r >= thr).mean()), float((np.abs(r) >= thr).mean())
    return {"mean": float(r.mean()), "sd": float(r.std(ddof=1)), "q025": float(q[0]), "q50": float(q[1]),
            "q975": float(q[2]), "p_ge": p_ge, "p_absge": p_abs,
            "mc_se_p_ge": float(np.sqrt(p_ge * (1 - p_ge) / len(r))), "n_sims": int(len(r))}


def reml_between_within_sd(values, groups) -> tuple[float, float]:
    """One-way random-effects REML: SD between group means (net of within-group noise) and SD within."""
    df = pd.DataFrame({"y": np.asarray(values, float), "g": np.asarray(groups).astype(str)})
    f = fit_formula("1", df, "y", ["g"], method="REML")
    return float(np.sqrt(f.var_comp["g"])), float(np.sqrt(f.sigma2))


def barrier_ms(family: str, params: dict, q: float = BARRIER_Q) -> float:
    """The RT (ms) below which a legitimate start from the fitted untruncated distribution has probability q."""
    return 1000.0 * rtdist.quantile(family, params, q)


def dersimonian_laird(est, se) -> dict:
    """Random-effects between-study SD (DerSimonian-Laird), Cochran's Q and its p-value."""
    est, se = np.asarray(est, float), np.asarray(se, float)
    w = 1.0 / se ** 2
    k = len(est)
    mu = float((w * est).sum() / w.sum())
    Q = float((w * (est - mu) ** 2).sum())
    c = float(w.sum() - (w ** 2).sum() / w.sum())
    tau2 = max(0.0, (Q - (k - 1)) / c)
    return {"tau": float(np.sqrt(tau2)), "Q": Q, "p": float(stats.chi2.sf(Q, k - 1)), "k": k, "mu_fixed": mu}


def h1_verdict(W: bool, crit: dict) -> tuple[str, str]:
    """Pre-registered H1 rule. crit: R1, R2, Q1, Q2, Q3 -> bool or None (not run)."""
    fired = [k for k, v in crit.items() if v]
    if W and fired:
        grade = "observed structure" if any(crit.get(k) for k in ("R1", "R2", "Q1")) else "simulation only"
        return "SUPPORTS the mechanism", grade
    return "NOT REPRODUCED", ""


def h2_verdict(c1: bool, c2: bool) -> str:
    return "CONSEQUENTIAL" if (c1 or c2) else "NOT CONSEQUENTIAL"


# =====================================================================================================
# H1
# =====================================================================================================

def h1_sample(mock: bool):
    """The fp_models.py analysis sample (Seiko holds, WIC2025 excluded) plus the unexcluded version."""
    fp_all, fused = load_fp_sources(mock, "seiko")
    fp = fp_all.copy()
    for cy in EXCLUDE_HOLD_COMPS:
        fp = fp[~fp["race_id"].str.startswith(cy + "-")].copy()
    rt, rused = load_rt(mock, "athletes")
    races, raced = load_races(mock)
    rt = attach_races(rt, races)
    rt["valid"] = valid_rt_mask(rt)
    d = rt[rt["valid"]].merge(fp, on="race_id", how="inner")
    d["rt_ms"] = d["rt_s"] * 1000
    ak = d["athlete_key"].astype(object)
    d["athlete_id2"] = np.where(ak.isna(), "anon_" + d.index.astype(str), ak.astype(str))
    d["fp_c100"] = (d["foreperiod_s"] - FP_CENTRE) * 10.0
    d_all = rt[rt["valid"]].merge(fp_all, on="race_id", how="inner")
    return d, d_all, fused + rused + raced


def design_arrays(d: pd.DataFrame) -> dict:
    comps = sorted(d["comp_year"].unique())
    race_codes, race_levels = pd.factorize(d["race_id"], sort=True)
    ath_codes, _ = pd.factorize(d["athlete_id2"], sort=True)
    champ_idx = d["comp_year"].map({c: i for i, c in enumerate(comps)}).to_numpy()
    race_champ = pd.Series(champ_idx).groupby(race_codes).first().to_numpy()
    onehot = np.eye(len(comps))[champ_idx]
    return {"comps": comps, "race_idx": race_codes, "n_race": len(race_levels), "ath_idx": ath_codes,
            "n_ath": int(ath_codes.max()) + 1, "champ_idx": champ_idx, "race_champ": race_champ,
            "onehot": onehot, "counts": onehot.sum(0), "W": d["foreperiod_s"].to_numpy(float),
            "N": len(d)}


def naive_block(x, y, D: dict, n_boot: int, rng, label: str) -> dict:
    """(c) statistics for one hold scale x: r (uncentred / championship-centred), naive Fisher CI and p,
    race-cluster bootstrap CI with races resampled within championship."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    S = race_sums(x, y, D["race_idx"], D["n_race"])                       # 6 x R
    K = strat_multiplicities(D["race_champ"], n_boot, rng)                 # B x R
    r_u = pearson(x, y)
    boot_u = r_from_totals(K @ S.T)
    Tc_full = np.stack([S[:, D["race_champ"] == c].sum(1) for c in range(len(D["comps"]))])   # C x 6
    r_c = float(r_centred_from_totals(Tc_full[None])[0])
    Tc_boot = np.stack([K[:, D["race_champ"] == c] @ S[:, D["race_champ"] == c].T
                        for c in range(len(D["comps"]))], axis=1)          # B x C x 6
    boot_c = r_centred_from_totals(Tc_boot)
    n = len(x)
    out = {}
    for tag, r_, bt in (("pooled", r_u, boot_u), ("centred", r_c, boot_c)):
        lo, hi = np.percentile(bt, [2.5, 97.5])
        out[tag] = {"r": r_, "boot_lo": float(lo), "boot_hi": float(hi), "naive_ci": fisher_ci(r_, n),
                    "naive_p": naive_p(r_, n), "n": n, "n_races": int(D["n_race"]), "label": label}
    return out


def sim_observed(D, eta, vc, sims, rng, delta=None, sd_cal=0.0, chunk=500) -> dict:
    """S1: simulate RT = eta + race + athlete + residual on the observed design; return naive r arrays."""
    W, ri, ai, ci = D["W"], D["race_idx"], D["ath_idx"], D["champ_idx"]
    sd_r, sd_a, sd_e = (float(np.sqrt(vc[k])) for k in ("race", "athlete", "residual"))
    Wc = W - ((W @ D["onehot"]) / D["counts"]) @ D["onehot"].T
    out = {"ready": [], "centred": [], "fp": []}
    for s0 in range(0, sims, chunk):
        S = min(chunk, sims - s0)
        u = rng.standard_normal((S, D["n_race"])) * sd_r
        a = rng.standard_normal((S, D["n_ath"])) * sd_a
        e = rng.standard_normal((S, D["N"])) * sd_e
        Y = eta[None, :] + u[:, ri] + a[:, ai] + e
        out["ready"].append(rowwise_r(W, Y))
        out["centred"].append(rowwise_r(Wc, centre_rows(Y, D["onehot"], D["counts"])))
        if delta is not None:
            ecal = rng.standard_normal((S, D["n_race"])) * sd_cal
            X = W[None, :] + delta[ci][None, :] + ecal[:, ri]
            out["fp"].append(rowwise_r(X, Y))
    return {k: np.concatenate(v) for k, v in out.items() if v}


def sim_exchangeable(D, eta_nc, slope, vc, sd_champ, sd_w_between, sims, rng, chunk=500) -> np.ndarray:
    """S2: championship RT offsets ~ N(0, sd_champ) and championship mean Ready Times ~ N(mean, sd_w_between)
    drawn independently in every dataset; within-championship Ready Time deviations and the rest of the
    observed design kept. eta_nc = fixed part without championship effects and without the slope term."""
    W, ri, ai, ci = D["W"], D["race_idx"], D["ath_idx"], D["champ_idx"]
    race_W = pd.Series(W).groupby(ri).first()
    cmean = race_W.groupby(D["race_champ"]).mean().to_numpy()             # race-level championship means
    mu = float(race_W.mean())
    Wdev = W - cmean[ci]
    sd_r, sd_a, sd_e = (float(np.sqrt(vc[k])) for k in ("race", "athlete", "residual"))
    C = len(D["comps"])
    out = []
    for s0 in range(0, sims, chunk):
        S = min(chunk, sims - s0)
        gam = rng.standard_normal((S, C)) * sd_champ
        m = rng.standard_normal((S, C)) * sd_w_between
        u = rng.standard_normal((S, D["n_race"])) * sd_r
        a = rng.standard_normal((S, D["n_ath"])) * sd_a
        e = rng.standard_normal((S, D["N"])) * sd_e
        Ws = Wdev[None, :] + mu + m[:, ci]
        Y = eta_nc[None, :] + gam[:, ci] + slope * (Ws - FP_CENTRE) * 10.0 + u[:, ri] + a[:, ai] + e
        out.append(rowwise_r(Ws, Y))
    return np.concatenate(out)


def haugen_layout(design: dict):
    """Start-level layout of one Haugen-style cell: heat and championship of every start, and athlete ids
    (athletes nested within championship, about starts_per_athlete starts each, never twice in a heat)."""
    K, H = int(design["n_champs"]), int(design["heats_per_champ"])
    m = float(design["starts_per_heat"])
    spa = max(1.0, float(design.get("starts_per_athlete", 1.0)))
    per_champ = int(np.floor(H * m + 0.5))                     # e.g. 11 heats x 7.5 -> 83 starts
    base, extra_ = divmod(per_champ, H)
    sizes = np.array([base + 1] * extra_ + [base] * (H - extra_))
    heat_champ = np.repeat(np.arange(K), H)
    start_heat = np.repeat(np.arange(K * H), np.tile(sizes, K))
    start_champ = heat_champ[start_heat]
    ath = np.empty(len(start_heat), int)
    nxt = 0
    for c in range(K):
        idx = np.flatnonzero(start_champ == c)
        na = max(int(np.ceil(len(idx) / spa)), int(sizes.max()))
        ath[idx] = nxt + (np.arange(len(idx)) % na)
        nxt += na
    return heat_champ, start_heat, start_champ, ath, nxt


def _truncnorm_rows(mean, sd, shape, lo, hi, rng, max_iter=500):
    """Normal draws redrawn until inside [lo, hi] (mean broadcasts to shape)."""
    x = mean + rng.standard_normal(shape) * sd
    for _ in range(max_iter):
        bad = (x < lo) | (x > hi)
        if not bad.any():
            break
        x = np.where(bad, mean + rng.standard_normal(shape) * sd, x)
    return np.clip(x, lo, hi)


def sim_haugen(design: dict, par: dict, sims: int, rng, chunk=200) -> np.ndarray:
    """S3: one Haugen-style sex x rule-period cell with zero true hold effect; returns the naive pooled r of
    every simulated study. design: n_champs, heats_per_champ, starts_per_heat (may be fractional),
    starts_per_athlete, hold_lo_s, hold_hi_s, truncate ('champ_mean' | 'heat' | 'none').
    par: hold_mean_s, sd_hold_between_s, sd_hold_within_s (s) and sd_champ_ms, sd_race_ms, sd_athlete_ms,
    sd_residual_ms (ms). Championship mean holds and championship RT offsets are independent."""
    heat_champ, start_heat, start_champ, ath, n_ath = haugen_layout(design)
    K, n_heat, N = int(design["n_champs"]), len(heat_champ), len(start_heat)
    lo, hi = float(design["hold_lo_s"]), float(design["hold_hi_s"])
    mode = str(design.get("truncate", "none"))
    out = []
    for s0 in range(0, sims, chunk):
        S = min(chunk, sims - s0)
        if mode == "champ_mean":
            cm = _truncnorm_rows(par["hold_mean_s"], par["sd_hold_between_s"], (S, K), lo, hi, rng)
        else:
            cm = par["hold_mean_s"] + rng.standard_normal((S, K)) * par["sd_hold_between_s"]
        if mode == "heat":
            hold = _truncnorm_rows(cm[:, heat_champ], par["sd_hold_within_s"], (S, n_heat), lo, hi, rng)
        else:
            hold = cm[:, heat_champ] + rng.standard_normal((S, n_heat)) * par["sd_hold_within_s"]
        g = rng.standard_normal((S, K)) * par["sd_champ_ms"]
        u = rng.standard_normal((S, n_heat)) * par["sd_race_ms"]
        a = rng.standard_normal((S, n_ath)) * par["sd_athlete_ms"]
        e = rng.standard_normal((S, N)) * par["sd_residual_ms"]
        Y = g[:, start_champ] + u[:, start_heat] + a[:, ath] + e
        out.append(rowwise_r(hold[:, start_heat], Y))
    return np.concatenate(out)


def run_h1(args, numbers, tables, extra):
    d, d_all, inputs = h1_sample(args.mock)
    fpm = json.loads(Path(args.fp_models).read_text(encoding="utf-8"))["numbers"]
    cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))["numbers"]
    desc = json.loads(Path(args.descriptive).read_text(encoding="utf-8"))
    inputs += [Path(args.fp_models), Path(args.calibration), Path(args.descriptive)]
    D = design_arrays(d)
    if not args.mock:
        if D["n_race"] != fpm["n_races"]["value"] or D["N"] != fpm["n_rts"]["value"]:
            raise SystemExit(f"H1 sample mismatch: {D['n_race']} races / {D['N']} RTs vs fp_models "
                             f"{fpm['n_races']['value']} / {fpm['n_rts']['value']}")
    comps = D["comps"]
    numbers["h1_n_races"] = num(D["n_race"], desc="H1 sample: races with a validated Seiko Ready Time and >=1 valid RT "
                                                  "(fp_models sample, WIC2025 excluded)")
    numbers["h1_n_rts"] = num(D["N"], desc="H1 sample: valid RTs")
    numbers["h1_n_champs"] = num(len(comps), desc="H1 sample: championships", champs=comps)
    re_ = ["race_id", "athlete_id2"]
    race_lvl = d.groupby("race_id", sort=True).agg(W=("foreperiod_s", "first"), comp=("comp_year", "first"))

    # ---- (a) within-championship model -------------------------------------------------------------
    m1 = fit_formula(FX_WITHIN + " + fp_c100", d, "rt_ms", re_, method="ML")
    m0 = fit_formula(FX_WITHIN, d, "rt_ms", re_, method="ML")
    m0r = fit_formula(FX_WITHIN, d, "rt_ms", re_, method="REML")
    est, lo, hi = m1.coef("fp_c100")
    if not args.mock and abs(est - fpm["slope_ms_per_100ms"]["value"]) > 1e-3:
        raise SystemExit(f"(a) does not reproduce fp_models: {est} vs {fpm['slope_ms_per_100ms']['value']}")
    sd_w = float(np.sqrt(m0r.var_comp["race_id"] + m0r.var_comp["athlete_id2"] + m0r.sigma2))
    gsd = race_lvl.groupby("comp")["W"].agg(["var", "size"])
    sd_fp_within = float(np.sqrt(((gsd["size"] - 1) * gsd["var"]).sum() / (gsd["size"] - 1).sum()))
    k_a = sd_fp_within * 10 / sd_w
    haugen_a = HAUGEN_R / k_a
    p_a = float(2 * stats.norm.sf(abs(est / m1.se[m1.names.index("fp_c100")])))
    numbers["h1a_slope_ms_per_100ms"] = num(round(est, 3), ci=(round(lo, 3), round(hi, 3)), unit="ms per 100 ms",
                                            desc="(a) within-championship Ready Time slope (championship, sex, round, event "
                                                 "fixed effects; race + athlete random intercepts; ML, Wald CI); "
                                                 "reproduces fp_models.slope_ms_per_100ms", p=float(f"{p_a:.3g}"))
    numbers["h1a_r_equivalent"] = num(round(est * k_a, 4), ci=(round(lo * k_a, 4), round(hi * k_a, 4)),
                                      desc="(a) r-equivalent: slope x pooled within-championship SD(Ready Time) / "
                                           "within-championship SD(RT)")
    numbers["h1a_haugen_slope_ms_per_100ms"] = num(round(haugen_a, 3), unit="ms per 100 ms",
                                                   desc="(a) slope that r = 0.16 implies on the (a) scale")
    # verdict flags are computed from the stored (rounded) values so a re-check can reproduce them exactly
    lo_s, hi_s = numbers["h1a_slope_ms_per_100ms"]["ci95"]
    h_s = numbers["h1a_haugen_slope_ms_per_100ms"]["value"]
    W_ok = bool(hi_s < h_s and lo_s > -h_s)
    numbers["h1a_ci_excludes_haugen"] = num(W_ok, desc="criterion W: the (a) slope CI excludes the Haugen-sized slope "
                                                       "in both directions")

    # ---- (b) without championship effects ------------------------------------------------------------
    m1b = fit_formula(FX_NOCHAMP + " + fp_c100", d, "rt_ms", re_, method="ML")
    m0br = fit_formula(FX_NOCHAMP, d, "rt_ms", re_, method="REML")
    eb, lb, hb = m1b.coef("fp_c100")
    sd_b = float(np.sqrt(m0br.var_comp["race_id"] + m0br.var_comp["athlete_id2"] + m0br.sigma2))
    sd_fp_all = float(race_lvl["W"].std(ddof=1))
    k_b = sd_fp_all * 10 / sd_b
    p_b = float(2 * stats.norm.sf(abs(eb / m1b.se[m1b.names.index("fp_c100")])))
    numbers["h1b_slope_ms_per_100ms"] = num(round(eb, 3), ci=(round(lb, 3), round(hb, 3)), unit="ms per 100 ms",
                                            desc="(b) Ready Time slope WITHOUT championship effects (sex, round, event fixed "
                                                 "effects; race + athlete random intercepts; ML, Wald CI)",
                                            p=float(f"{p_b:.3g}"))
    numbers["h1b_r_equivalent"] = num(round(eb * k_b, 4), ci=(round(lb * k_b, 4), round(hb * k_b, 4)),
                                      desc="(b) r-equivalent: slope x overall SD(race-level Ready Time) / SD(RT) of the "
                                           "same model without Ready Time (race + athlete + residual, REML)")
    numbers["h1b_haugen_slope_ms_per_100ms"] = num(round(HAUGEN_R / k_b, 3), unit="ms per 100 ms",
                                                   desc="(b) slope that r = 0.16 implies on the (b) scale")
    R1 = bool(numbers["h1b_r_equivalent"]["ci95"][1] >= HAUGEN_R)
    numbers["h1b_reaches_haugen"] = num(R1, desc="criterion R1: the (b) r-equivalent 95% CI upper bound is >= 0.16")
    numbers["h1b_sd_race_ms"] = num(round(float(np.sqrt(m0br.var_comp["race_id"])), 3), unit="ms",
                                    desc="(b) race SD without championship effects (REML; absorbs championship offsets)",
                                    sd_race_with_champ_fe_ms=float(f"{np.sqrt(m0r.var_comp['race_id']):.4g}"))

    # ---- (c) naive pooled athlete-level r --------------------------------------------------------------
    rng_c = np.random.default_rng(args.seed + 101)
    y = d["rt_s"].to_numpy(float)
    W = D["W"]
    delta = np.array([cal.get(f"offset_mean_{c}_s", cal["offset_mean_s"])["value"] for c in comps], float)
    delta_src = {c: ("own pairs" if f"offset_mean_{c}_s" in cal else "pooled offset (no pairs)") for c in comps}
    nb_ready = naive_block(W, y, D, args.boot_r, rng_c, "Ready Time")
    nb_fp = naive_block(W + delta[D["champ_idx"]], y, D, args.boot_r, rng_c, "calibrated foreperiod")

    def put_r(key, res, desc):
        numbers[key] = num(round(res["r"], 4), ci=(round(res["boot_lo"], 4), round(res["boot_hi"], 4)), desc=desc,
                           naive_ci95=[round(res["naive_ci"][0], 4), round(res["naive_ci"][1], 4)],
                           naive_p=float(f"{res['naive_p']:.3g}"), n_starts=res["n"], n_races=res["n_races"])

    put_r("h1c_r_pooled", nb_ready["pooled"],
          "(c1) naive Pearson r of Ready Time and RT over all starts, pooled over championships (Haugen-style); "
          "95% CI = race-cluster bootstrap within championship (naive Fisher CI and p in naive_ci95 / naive_p)")
    put_r("h1c_r_centred", nb_ready["centred"],
          "(c2) the same r after centring Ready Time and RT within championship (mechanism control)")
    put_r("h1c_r_pooled_fp", nb_fp["pooled"],
          "(c-fp, secondary) naive pooled r on the audio-calibrated foreperiod scale (Ready Time + championship "
          "calibration offset; WIC2024 uses the pooled offset)")
    R2 = bool(numbers["h1c_r_pooled"]["ci95"][1] >= HAUGEN_R)
    numbers["h1c_reaches_haugen"] = num(R2, desc="criterion R2: the (c1) race-cluster 95% CI upper bound is >= 0.16")
    numbers["h1c_centred_below_haugen"] = num(bool(numbers["h1c_r_centred"]["ci95"][1] < HAUGEN_R),
                                              desc="mechanism check: the championship-centred r (c2) 95% CI stays below 0.16")
    sub_rows = []
    for lab, sel in (("M", d["sex"] == "M"), ("W", d["sex"] == "W"), ("100m", d["event"] == "100m")):
        ds = d[sel.to_numpy()].reset_index(drop=True)
        Ds = design_arrays(ds)
        res = naive_block(Ds["W"], ds["rt_s"].to_numpy(float), Ds, args.boot_r, rng_c, lab)
        put_r(f"h1c_r_pooled_{lab}", res["pooled"],
              f"(c1, secondary) naive pooled r of Ready Time and RT, subset {lab} ({Ds['N']} starts, "
              f"{len(Ds['comps'])} championships)")
        sub_rows.append({"subset": lab, "n": Ds["N"], "champs": len(Ds["comps"]), **{k: res["pooled"][k] for k in
                                                                                    ("r", "boot_lo", "boot_hi", "naive_p")},
                         "r_centred": res["centred"]["r"]})
    tables["h1_naive_subsets"] = pd.DataFrame(sub_rows)
    extra["calibration_offsets_used_s"] = {c: {"delta_s": float(dv), "source": delta_src[c]} for c, dv in zip(comps, delta)}

    # ---- (d) championship means vs offsets (descriptive) ----------------------------------------------
    me = pd.DataFrame(desc["tables"]["meet_effects"]).set_index("comp_year")["deviation_ms"]
    fe_a = {c: 0.0 for c in comps}
    for nm, b in zip(m1.names, m1.beta):
        if nm.startswith("C(comp_year)[T."):
            fe_a[nm.split("[T.")[1].rstrip("]")] = float(b)
    fe_mean = np.mean(list(fe_a.values()))
    rl_all = d_all.groupby("race_id", sort=True).agg(W=("foreperiod_s", "first"), comp=("comp_year", "first"))
    rows = []
    for c, g in rl_all.groupby("comp"):
        rows.append({"comp_year": c, "in_h1_sample": c in comps, "n_races": int(len(g)),
                     "mean_ready_s": float(g["W"].mean()), "median_ready_s": float(g["W"].median()),
                     "offset_ms_descriptive": float(me.get(c, np.nan)),
                     "offset_ms_model_a": float(fe_a[c] - fe_mean) if c in fe_a else np.nan,
                     "calib_offset_s": float(cal[f"offset_mean_{c}_s"]["value"]) if f"offset_mean_{c}_s" in cal else np.nan})
    dt = pd.DataFrame(rows)
    dt["mean_fp_s"] = dt["mean_ready_s"] + dt["calib_offset_s"]
    tables["h1d_champ_table"] = dt
    s4 = dt[dt["in_h1_sample"]]
    s3 = dt[dt["calib_offset_s"].notna()]
    for tag, s, xcol, desc_ in (("4", s4, "mean_ready_s", "the 4 championships of the H1 sample"),
                                ("5", dt, "mean_ready_s", "5 championships incl. WIC2025 (anomalous Ready Times, flagged)"),
                                ("fp_3", s3, "mean_fp_s", "3 championships with audio pairs, calibrated foreperiod scale")):
        numbers[f"h1d_pearson_{tag}"] = num(round(pearson(s[xcol], s["offset_ms_descriptive"]), 4),
                                            desc=f"(d) descriptive: Pearson r across championships of mean Ready Time and the "
                                                 f"athlete-adjusted RT offset, {desc_}; no inference", n_champs=int(len(s)))
        numbers[f"h1d_spearman_{tag}"] = num(round(float(stats.spearmanr(s[xcol], s["offset_ms_descriptive"])[0]), 4),
                                             desc=f"(d) descriptive: Spearman rho across championships, {desc_}",
                                             n_champs=int(len(s)))

    # ---- S1: observed structure (SIMULATION) --------------------------------------------------------------
    X0 = patsy.dmatrix(m0.design_info, d, return_type="dataframe").to_numpy()
    X1 = patsy.dmatrix(m1.design_info, d, return_type="dataframe").to_numpy()
    eta0, eta1 = X0 @ m0.beta, X1 @ m1.beta
    champ0 = [i for i, nm in enumerate(m0.names) if nm.startswith("C(comp_year)")]
    champ1 = [i for i, nm in enumerate(m1.names) if nm.startswith("C(comp_year)")]
    eta0_nc = eta0 - X0[:, champ0] @ m0.beta[champ0]
    eta1_nc = eta1 - X1[:, champ1] @ m1.beta[champ1] - est * d["fp_c100"].to_numpy(float)
    vc0 = {"race": m0.var_comp["race_id"], "athlete": m0.var_comp["athlete_id2"], "residual": m0.sigma2}
    vc1 = {"race": m1.var_comp["race_id"], "athlete": m1.var_comp["athlete_id2"], "residual": m1.sigma2}
    sd_cal = float(cal["offset_sd_within_comp_s"]["value"])
    rng_s1 = np.random.default_rng(args.seed + 131)
    sims = {"S1_beta0": sim_observed(D, eta0, vc0, args.sims, rng_s1, delta=delta, sd_cal=sd_cal),
            "S1_betahat": sim_observed(D, eta1, vc1, args.sims, rng_s1, delta=delta, sd_cal=sd_cal),
            "S1_control": sim_observed(D, eta0_nc, vc0, args.sims, rng_s1)}
    # ---- S2: exchangeable championships (SIMULATION) --------------------------------------------------------
    sd_champ = float(desc["numbers"]["sd_championship_ms"]["value"])
    sd_wb, sd_ww = reml_between_within_sd(race_lvl["W"], race_lvl["comp"])
    rng_s2 = np.random.default_rng(args.seed + 151)
    s2 = {"S2_beta0": sim_exchangeable(D, eta0_nc, 0.0, vc0, sd_champ, sd_wb, args.sims, rng_s2),
          "S2_betahat": sim_exchangeable(D, eta1_nc, est, vc1, sd_champ, sd_wb, args.sims, rng_s2)}
    extra["simulation_parameters"] = {
        "S1": {"vc_ms2_beta0": vc0, "vc_ms2_betahat": vc1, "slope_betahat_ms_per_100ms": est,
               "calibration_delta_s": dict(zip(comps, delta.tolist())), "sd_cal_s": sd_cal,
               "championship_fe_beta0_ms": {m0.names[i]: float(m0.beta[i]) for i in champ0}},
        "S2": {"sd_champ_ms": sd_champ, "sd_ready_between_s": sd_wb, "sd_ready_within_s": sd_ww}}
    numbers["h1s2_sd_champ_ms"] = num(round(sd_champ, 3), unit="ms", desc="S2 input: championship RT-offset SD "
                                                                         "(descriptive.sd_championship_ms, 18 championships)")
    numbers["h1s2_sd_ready_between_s"] = num(round(sd_wb, 4), unit="s",
                                             desc="S2 input: REML between-championship SD of race-level Ready Time (H1 sample)",
                                             sd_within_s=float(f"{sd_ww:.4g}"))
    sim_rows, hist_rows = [], []
    bins = np.round(np.arange(-0.40, 0.8001, 0.01), 2)
    blocks = [("h1s1_ready_beta0", sims["S1_beta0"]["ready"], "S1 observed structure, true slope 0, Ready Time scale"),
              ("h1s1_ready_betahat", sims["S1_betahat"]["ready"], "S1 observed structure, true slope = (a) estimate, Ready Time scale"),
              ("h1s1_fp_beta0", sims["S1_beta0"]["fp"], "S1, true slope 0, foreperiod scale (Ready Time + championship "
                                                          "calibration offset + within-championship calibration scatter)"),
              ("h1s1_fp_betahat", sims["S1_betahat"]["fp"], "S1, true slope = (a) estimate, foreperiod scale"),
              ("h1s1_centred_beta0", sims["S1_beta0"]["centred"], "S1, true slope 0, championship-centred r (control)"),
              ("h1s1_centred_betahat", sims["S1_betahat"]["centred"], "S1, true slope = (a) estimate, championship-centred r"),
              ("h1s1_control", sims["S1_control"]["ready"], "S1 control: true slope 0 and no championship offsets"),
              ("h1s2_beta0", s2["S2_beta0"], "S2 exchangeable championships, true slope 0, Ready Time scale"),
              ("h1s2_betahat", s2["S2_betahat"], "S2 exchangeable championships, true slope = (a) estimate")]
    summ = {}
    for key, arr, lab in blocks:
        s = summarize_r(arr)
        summ[key] = s
        sim_rows.append({"key": key, "label": lab, **s})
        cnt, _ = np.histogram(arr, bins=bins)
        hist_rows += [{"key": key, "lo": float(bins[i]), "hi": float(bins[i + 1]), "count": int(cnt[i])}
                      for i in range(len(cnt))]
        numbers[f"{key}_r_mean"] = num(round(s["mean"], 4), desc=f"SIMULATION: mean naive pooled r, {lab}",
                                       sd=float(f"{s['sd']:.4g}"), q025=float(f"{s['q025']:.4g}"),
                                       q50=float(f"{s['q50']:.4g}"), q975=float(f"{s['q975']:.4g}"), n_sims=s["n_sims"])
        numbers[f"{key}_p_ge016"] = num(float(f"{s['p_ge']:.4g}"), desc=f"SIMULATION: P(naive r >= 0.16), {lab}",
                                        mc_se=float(f"{s['mc_se_p_ge']:.3g}"), n_sims=s["n_sims"])
        numbers[f"{key}_p_absge016"] = num(float(f"{s['p_absge']:.4g}"), desc=f"SIMULATION: P(|naive r| >= 0.16), {lab}",
                                           n_sims=s["n_sims"])
    tables["h1_sim_summary"] = pd.DataFrame(sim_rows)
    tables["h1_sim_hist"] = pd.DataFrame(hist_rows)
    Q1 = bool(numbers["h1s1_ready_beta0_p_ge016"]["value"] >= P_NONTRIVIAL)
    Q2 = bool(numbers["h1s2_beta0_p_ge016"]["value"] >= P_NONTRIVIAL)

    # ---- S3: Haugen et al. 2013 design (SIMULATION; only with --haugen-design) ---------------------------
    Q3 = None
    if args.haugen_design:
        hpath = Path(args.haugen_design)
        inputs.append(hpath)
        hd = pd.read_csv(hpath, encoding="utf-8-sig")
        fpa_path = data_path("foreperiods.csv", args.mock)
        inputs.append(fpa_path)
        fpa = pd.read_csv(fpa_path, encoding="utf-8-sig")
        fpa = fpa[(fpa["attempt_status"] == "valid") & fpa["foreperiod_s"].notna()].copy()
        fpa = fpa.sort_values(["race_id", "attempt"]).drop_duplicates("race_id", keep="last")
        fpa["comp"] = fpa["race_id"].str.split("-").str[0]
        sdb_fp, sdw_fp = reml_between_within_sd(fpa["foreperiod_s"], fpa["comp"])
        nd = desc["numbers"]
        par = {"hold_mean_s": float(fpa["foreperiod_s"].mean()), "sd_hold_between_s": sdb_fp,
               "sd_hold_within_s": sdw_fp, "sd_champ_ms": nd["sd_championship_ms"]["value"],
               "sd_race_ms": nd["sd_race_ms"]["value"], "sd_athlete_ms": nd["sd_athlete_ms"]["value"],
               "sd_residual_ms": nd["sd_residual_ms"]["value"]}
        extra["simulation_parameters"]["S3"] = {**par, "n_audio_races": int(len(fpa)),
                                                "n_audio_champs": int(fpa["comp"].nunique())}
        numbers["h1s3_sd_hold_between_s"] = num(round(sdb_fp, 4), unit="s",
                                                desc="S3 input: REML between-championship SD of audio (set onset -> gun) "
                                                     "foreperiods, valid attempts (foreperiods.csv)",
                                                sd_within_s=float(f"{sdw_fp:.4g}"), n_races=int(len(fpa)),
                                                n_champs=int(fpa["comp"].nunique()))
        rng_s3 = np.random.default_rng(args.seed + 171)
        q3_list, rows3 = [], []
        for _, row in hd.iterrows():
            dsg = row.to_dict()
            tag = str(dsg["subgroup"])
            primary = str(dsg.get("primary", "no")).strip().lower() in ("yes", "true", "1")
            # blank hold SDs -> the pre-registered REML estimates from our audio foreperiods
            p_row = {**par, "hold_mean_s": float(dsg["hold_mean_s"]),
                     "sd_hold_between_s": sdb_fp if pd.isna(dsg.get("sd_hold_between_s")) else float(dsg["sd_hold_between_s"]),
                     "sd_hold_within_s": sdw_fp if pd.isna(dsg.get("sd_hold_within_s")) else float(dsg["sd_hold_within_s"])}
            arr = sim_haugen(dsg, p_row, args.sims, rng_s3)
            n_starts = len(haugen_layout(dsg)[1])
            t_ = arr * np.sqrt((n_starts - 2) / (1 - arr ** 2))
            p_naive = 2 * stats.t.sf(np.abs(t_), n_starts - 2)
            s = summarize_r(arr)
            p_sig = float((p_naive < 0.001).mean())
            p_ge_sig = float(((arr >= HAUGEN_R) & (p_naive < 0.001)).mean())
            rows3.append({"subgroup": tag, "primary": primary, "n_starts": n_starts,
                          "sd_hold_between_used_s": p_row["sd_hold_between_s"],
                          "sd_hold_within_used_s": p_row["sd_hold_within_s"],
                          **{k: dsg[k] for k in hd.columns if k not in ("subgroup", "primary", "source")},
                          **s, "p_naive_lt_0001": p_sig, "p_ge016_and_naive_lt_0001": p_ge_sig})
            cnt, _ = np.histogram(arr, bins=bins)
            hist_rows += [{"key": f"h1s3_{tag}", "lo": float(bins[i]), "hi": float(bins[i + 1]), "count": int(cnt[i])}
                          for i in range(len(cnt))]
            lab = f"Haugen 2013 design '{tag}' ({int(dsg['n_champs'])} championships, {n_starts} starts), true effect 0"
            numbers[f"h1s3_{tag}_r_mean"] = num(round(s["mean"], 4), desc=f"SIMULATION: mean naive pooled r, {lab}",
                                                sd=float(f"{s['sd']:.4g}"), q025=float(f"{s['q025']:.4g}"),
                                                q975=float(f"{s['q975']:.4g}"), n_sims=s["n_sims"], primary=primary)
            numbers[f"h1s3_{tag}_p_absge016"] = num(float(f"{s['p_absge']:.4g}"),
                                                    desc=f"SIMULATION: P(|naive r| >= 0.16), {lab}",
                                                    mc_se=float(f"{np.sqrt(s['p_absge'] * (1 - s['p_absge']) / s['n_sims']):.3g}"),
                                                    primary=primary)
            numbers[f"h1s3_{tag}_p_ge016"] = num(float(f"{s['p_ge']:.4g}"), desc=f"SIMULATION: P(naive r >= 0.16), {lab}",
                                                 primary=primary)
            numbers[f"h1s3_{tag}_p_ge016_sig"] = num(float(f"{p_ge_sig:.4g}"),
                                                     desc=f"SIMULATION (secondary): P(naive r >= 0.16 and naive p < 0.001), {lab}",
                                                     p_naive_lt_0001=float(f"{p_sig:.4g}"), primary=primary)
            if primary:
                q3_list.append(numbers[f"h1s3_{tag}_p_absge016"]["value"] >= P_NONTRIVIAL)
        tables["h1_s3_summary"] = pd.DataFrame(rows3)
        tables["h1_sim_hist"] = pd.DataFrame(hist_rows)
        Q3 = bool(any(q3_list)) if q3_list else None

    crit = {"R1": R1, "R2": R2, "Q1": Q1, "Q2": Q2, "Q3": Q3}
    verdict, grade = h1_verdict(W_ok, crit)
    numbers["h1_verdict"] = num(verdict, desc="pre-registered H1 verdict (prereg_systematic.md): SUPPORTS if W and any of "
                                              "R1, R2, Q1, Q2, Q3; otherwise NOT REPRODUCED",
                                grade=grade, W=W_ok, **{k: v for k, v in crit.items()},
                                s3_run=Q3 is not None)
    return inputs


# =====================================================================================================
# H2
# =====================================================================================================

def h2_sample(mock: bool):
    """The descriptive.py sample of valid RTs (rt_athletes + rt_fiore, de-duplicated)."""
    rt, used = load_rt(mock)
    races, rused = load_races(mock)
    rt = attach_races(dedupe_sources(rt), races)
    rt["valid"] = valid_rt_mask(rt)
    v = rt[rt["valid"]].copy()
    v["rt_ms"] = v["rt_s"] * 1000.0
    ak = v["athlete_key"].astype(object)
    miss = ak.isna() | (ak.astype(str) == "None")
    v["athlete_id2"] = np.where(miss, "anon_" + v.index.astype(str), ak.astype(str))
    rounds_present = [r for r in ROUND_ORDER if r in set(v["round"])]
    v["round"] = pd.Categorical(v["round"], categories=rounds_present + sorted(set(v["round"]) - set(rounds_present)))
    return v, used + rused


def championship_offsets(v: pd.DataFrame):
    """Athlete-adjusted championship deviations (ms) of descriptive.py's ML meet model, with the
    ingredients to redraw them from their joint sampling distribution, and each start's round + event-type
    fixed-effect shift (ms, relative to first round / flat sprint) for the post-hoc composition sensitivity."""
    mf = fit_formula(FX_NOCHAMP + " + C(comp_year, Sum)", v, "rt_ms", ["race_id", "athlete_id2"], method="ML")
    levels = sorted(v["comp_year"].unique())
    idx = [i for i, n in enumerate(mf.names) if n.startswith("C(comp_year, Sum)")]
    L = np.zeros((len(levels), len(mf.names)))
    for j in range(len(levels)):
        if j < len(idx):
            L[j, idx[j]] = 1.0
        else:
            L[j, idx] = -1.0
    off = L @ mf.beta
    se = np.sqrt(np.diag(L @ mf.cov_beta @ L.T))
    chol = np.linalg.cholesky(mf.cov_beta[np.ix_(idx, idx)])
    Xmf = patsy.dmatrix(mf.design_info, v, return_type="dataframe").to_numpy()
    re_cols = [i for i, n in enumerate(mf.names) if n.startswith(("C(round", "C(event_type"))]
    comp_shift_ms = Xmf[:, re_cols] @ mf.beta[re_cols]
    return levels, off, se, L[:, idx], chol, comp_shift_ms


def _fit(x, fam, lo, hi, start=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with np.errstate(all="ignore"):
            return rtdist.fit_family(x, fam, lo, hi, start=start)


def run_h2(args, numbers, tables, extra):
    v, inputs = h2_sample(args.mock)
    desc = json.loads(Path(args.descriptive).read_text(encoding="utf-8"))
    nd = desc["numbers"]
    if not args.mock and len(v) != nd["n_valid"]["value"]:
        raise SystemExit(f"H2 sample mismatch: {len(v)} vs descriptive.n_valid {nd['n_valid']['value']}")
    numbers["h2_n_valid"] = num(int(len(v)), desc="H2 sample: valid RTs (descriptive.py sample)")
    levels, off, off_se, Lc, chol, comp_shift_ms = championship_offsets(v)
    v = v.assign(comp_shift_ms=comp_shift_ms)
    if not args.mock:
        me = pd.DataFrame(desc["tables"]["meet_effects"]).set_index("comp_year")["deviation_ms"]
        bad = [c for c, o in zip(levels, off) if abs(o - me[c]) > 1e-3 * max(1.0, abs(me[c]))]
        if bad:
            raise SystemExit(f"championship offsets do not reproduce descriptive.json meet_effects: {bad}")
    rng = np.random.default_rng(args.seed + 211)
    rng_c = np.random.default_rng(args.seed + 223)
    cmap = {c: i for i, c in enumerate(levels)}
    pa_rows, champ_rows, off_rows = [], [], []
    point, boot = {}, {}
    for sex in ("M", "W"):
        vs = v[v["sex"] == sex]
        x = vs["rt_s"].to_numpy(float)
        cidx = vs["comp_year"].map(cmap).to_numpy()
        w = np.bincount(cidx, minlength=len(levels)) / len(x)
        off_s = off - w @ off
        for c, o, oc in zip(levels, off, off_s):
            off_rows.append({"sex": sex, "comp_year": c, "offset_ms": o, "offset_centred_ms": oc})
        race_codes, _ = pd.factorize(vs["race_id"], sort=True)
        rows_by_race = pd.Series(np.arange(len(x))).groupby(race_codes).apply(lambda s: s.to_numpy()).to_dict()
        race_champ = pd.Series(cidx).groupby(race_codes).first()
        races_by_c = {ci: race_champ.index[race_champ.to_numpy() == ci].to_numpy() for ci in range(len(levels))}

        def adjusted(xx, cc, offc):
            sh = offc[cc] / 1000.0
            return xx - sh, 0.100 - sh, 0.300 - sh

        fa, fb = {}, {}
        xa, loa, hia = adjusted(x, cidx, off_s)
        for fam in FAMILIES:
            fa[fam] = _fit(x, fam, 0.100, 0.300)
            fb[fam] = _fit(xa, fam, loa, hia)
            if not args.mock:
                ref = nd[f"tail_mass_pooled_{fam}_{sex}"]["value"]
                if float(f"{rtdist.mass_below(fa[fam], 0.100):.4g}") != ref:
                    raise SystemExit(f"pooled fit does not reproduce descriptive tail_mass_pooled_{fam}_{sex}")
            point[(sex, fam)] = {"pooled_p": rtdist.mass_below(fa[fam], 0.100), "pooled_b": barrier_ms(fam, fa[fam].params),
                                 "adj_p": rtdist.mass_below(fb[fam], 0.100), "adj_b": barrier_ms(fam, fb[fam].params),
                                 "pooled_params": fa[fam].params, "adj_params": fb[fam].params}
        # paired race-cluster bootstrap (races within championship), offsets redrawn from their sampling distribution
        bt = {fam: [] for fam in FAMILIES}
        for _ in range(args.boot_h2):
            pick = np.concatenate([rows_by_race[r] for ci in range(len(levels)) if len(races_by_c[ci])
                                   for r in races_by_c[ci][rng.integers(0, len(races_by_c[ci]), len(races_by_c[ci]))]])
            off_b = off + Lc @ (chol @ rng.standard_normal(chol.shape[0]))
            off_bs = off_b - w @ off_b
            xb, cb = x[pick], cidx[pick]
            xab, lob, hib = adjusted(xb, cb, off_bs)
            for fam in FAMILIES:
                f1 = _fit(xb, fam, 0.100, 0.300, start=fa[fam].params)
                f2 = _fit(xab, fam, lob, hib, start=fb[fam].params)
                bt[fam].append((rtdist.mass_below(f1, 0.100), barrier_ms(fam, f1.params),
                                rtdist.mass_below(f2, 0.100), barrier_ms(fam, f2.params)))
        for fam in FAMILIES:
            b = np.array(bt[fam])
            boot[(sex, fam)] = b
            pt = point[(sex, fam)]
            ci = lambda j: np.percentile(b[:, j], [2.5, 97.5])
            shift_b = b[:, 1] - b[:, 3]
            pa_rows.append({"sex": sex, "family": fam, "n": int(len(x)),
                            "pooled_p": pt["pooled_p"], "pooled_p_lo": ci(0)[0], "pooled_p_hi": ci(0)[1],
                            "pooled_barrier_ms": pt["pooled_b"], "pooled_barrier_lo": ci(1)[0], "pooled_barrier_hi": ci(1)[1],
                            "adj_p": pt["adj_p"], "adj_p_lo": ci(2)[0], "adj_p_hi": ci(2)[1],
                            "adj_barrier_ms": pt["adj_b"], "adj_barrier_lo": ci(3)[0], "adj_barrier_hi": ci(3)[1],
                            "shift_ms": pt["pooled_b"] - pt["adj_b"],
                            **{f"pooled_{k}": val for k, val in pt["pooled_params"].items()},
                            **{f"adj_{k}": val for k, val in pt["adj_params"].items()},
                            "shift_lo": float(np.percentile(shift_b, 2.5)), "shift_hi": float(np.percentile(shift_b, 97.5)),
                            "n_boot": int(len(b))})
        # ---- (c) per championship ----------------------------------------------------------------------
        for ci_, c in enumerate(levels):
            sel = cidx == ci_
            nr = int(len(races_by_c[ci_]))
            row = {"sex": sex, "comp_year": c, "n": int(sel.sum()), "races": nr,
                   "eligible": bool(sel.sum() >= args.min_n and nr >= args.min_races)}
            if row["eligible"]:
                xc = x[sel]
                for fam in FAMILIES:
                    fc = _fit(xc, fam, 0.100, 0.300)
                    row[f"p_{fam}"] = rtdist.mass_below(fc, 0.100)
                    row[f"barrier_ms_{fam}"] = barrier_ms(fam, fc.params)
                    if fam == PRIMARY_FAMILY:
                        fc0 = fc
                bb = []
                for _ in range(args.boot_champ):
                    rr = races_by_c[ci_][rng_c.integers(0, nr, nr)]
                    fcb = _fit(x[np.concatenate([rows_by_race[r] for r in rr])], PRIMARY_FAMILY, 0.100, 0.300,
                               start=fc0.params)
                    bb.append((rtdist.mass_below(fcb, 0.100), barrier_ms(PRIMARY_FAMILY, fcb.params)))
                bb = np.array(bb)
                row.update({"p_exgauss_lo": np.percentile(bb[:, 0], 2.5), "p_exgauss_hi": np.percentile(bb[:, 0], 97.5),
                            "barrier_exgauss_lo": np.percentile(bb[:, 1], 2.5),
                            "barrier_exgauss_hi": np.percentile(bb[:, 1], 97.5),
                            "barrier_exgauss_se": float(np.std(bb[:, 1], ddof=1)),
                            "family_spread_ms": max(row[f"barrier_ms_{f}"] for f in FAMILIES)
                            - min(row[f"barrier_ms_{f}"] for f in FAMILIES)})
                # POST-HOC sensitivity (prereg addendum 1): round + event-type composition removed (reference
                # first round / flat sprint), per-observation truncation; point estimate, ex-Gaussian
                sh = vs["comp_shift_ms"].to_numpy(float)[sel] / 1000.0
                fce = _fit(xc - sh, PRIMARY_FAMILY, 0.100 - sh, 0.300 - sh)
                row["barrier_ms_exgauss_compadj"] = barrier_ms(PRIMARY_FAMILY, fce.params)
            champ_rows.append(row)
    pa = pd.DataFrame(pa_rows)
    ch = pd.DataFrame(champ_rows)
    tables["h2_pooled_adjusted"] = pa
    tables["h2_per_championship"] = ch
    tables["h2_offsets"] = pd.DataFrame(off_rows)
    gap_ms = (THRESH_BROSNAN_S - THRESH_FIORE_S) * 1000.0

    # ---- numbers ------------------------------------------------------------------------------------------
    for _, r in pa.iterrows():
        t = f"{r['family']}_{r['sex']}"
        numbers[f"h2_pooled_p_lt100_{t}"] = num(float(f"{r['pooled_p']:.4g}"),
                                                ci=(float(f"{r['pooled_p_lo']:.4g}"), float(f"{r['pooled_p_hi']:.4g}")),
                                                desc=f"H2(a) pooled over championships: fitted P(RT<0.100) for a gun-triggered "
                                                     f"start, {r['family']}, sex={r['sex']} (left-truncated fit; race-cluster "
                                                     f"bootstrap CI) - an extrapolation")
        numbers[f"h2_pooled_barrier_ms_{t}"] = num(round(r["pooled_barrier_ms"], 2),
                                                   ci=(round(r["pooled_barrier_lo"], 2), round(r["pooled_barrier_hi"], 2)),
                                                   unit="ms", desc=f"H2(a) pooled: 1e-3 barrier (RT with P = 0.001 below it), "
                                                                   f"{r['family']}, sex={r['sex']}")
        numbers[f"h2_adjusted_p_lt100_{t}"] = num(float(f"{r['adj_p']:.4g}"),
                                                  ci=(float(f"{r['adj_p_lo']:.4g}"), float(f"{r['adj_p_hi']:.4g}")),
                                                  desc=f"H2(b) athlete-adjusted championship offsets removed (average "
                                                       f"championship): fitted P(RT<0.100), {r['family']}, sex={r['sex']} "
                                                       f"(per-observation truncation; bootstrap redraws races and offsets)")
        numbers[f"h2_adjusted_barrier_ms_{t}"] = num(round(r["adj_barrier_ms"], 2),
                                                     ci=(round(r["adj_barrier_lo"], 2), round(r["adj_barrier_hi"], 2)),
                                                     unit="ms", desc=f"H2(b) championship-adjusted 1e-3 barrier, "
                                                                     f"{r['family']}, sex={r['sex']}")
        numbers[f"h2_shift_ms_{t}"] = num(round(r["shift_ms"], 2), ci=(round(r["shift_lo"], 2), round(r["shift_hi"], 2)),
                                          unit="ms", desc=f"H2 pooled-vs-adjusted shift: pooled minus championship-adjusted "
                                                          f"barrier, {r['family']}, sex={r['sex']} (paired bootstrap CI)",
                                          share_of_gap=float(f"{abs(r['shift_ms']) / gap_ms:.3g}"))
        if r["family"] == "exgauss":
            for comp_, lab_ in (("sigma", "Gaussian SD sigma"), ("tau", "exponential mean tau")):
                numbers[f"h2_exgauss_{comp_}_ms_{r['sex']}"] = num(
                    round(1000 * r[f"pooled_{comp_}"], 3), unit="ms",
                    desc=f"H2 ex-Gaussian {lab_}, pooled fit (value) and championship-adjusted fit (adjusted), sex={r['sex']}",
                    adjusted=float(f"{1000 * r[f'adj_{comp_}']:.6g}"))
    tau_info = {}
    for sex in ("M", "W"):
        e = ch[(ch["sex"] == sex) & ch["eligible"]]
        numbers[f"h2_n_champs_eligible_{sex}"] = num(int(len(e)), desc=f"H2(c) championships with >= {args.min_n} valid RTs "
                                                                       f"in >= {args.min_races} races, sex={sex}",
                                                     champs=e["comp_year"].tolist())
        for fam in FAMILIES:
            col = f"barrier_ms_{fam}"
            lo_r, hi_r = e.loc[e[col].idxmin()], e.loc[e[col].idxmax()]
            rng_ms = float(hi_r[col] - lo_r[col])
            numbers[f"h2_champ_barrier_range_ms_{fam}_{sex}"] = num(
                round(rng_ms, 2), unit="ms",
                desc=f"H2(c) per-championship spread (max - min) of the 1e-3 barrier, {fam}, sex={sex}",
                min_ms=float(f"{lo_r[col]:.4g}"), min_champ=lo_r["comp_year"], max_ms=float(f"{hi_r[col]:.4g}"),
                max_champ=hi_r["comp_year"], n_champs=int(len(e)), share_of_gap=float(f"{rng_ms / gap_ms:.3g}"))
        col = "barrier_ms_exgauss_compadj"
        lo_r, hi_r = e.loc[e[col].idxmin()], e.loc[e[col].idxmax()]
        numbers[f"h2_champ_barrier_range_ms_exgauss_{sex}_compadj"] = num(
            round(float(hi_r[col] - lo_r[col]), 2), unit="ms",
            desc=f"POST-HOC sensitivity (prereg addendum 1): per-championship spread of the ex-Gaussian barrier after "
                 f"removing round and event-type composition (first round / flat sprint reference), sex={sex}; "
                 f"not part of the decision rule",
            min_champ=lo_r["comp_year"], max_champ=hi_r["comp_year"], n_champs=int(len(e)))
        dl = dersimonian_laird(e[f"barrier_ms_{PRIMARY_FAMILY}"], e["barrier_exgauss_se"])
        tau_info[sex] = dl
        numbers[f"h2_champ_barrier_tau_ms_{sex}"] = num(round(dl["tau"], 3), unit="ms",
                                                        desc=f"H2(c) noise guard: between-championship SD of the ex-Gaussian "
                                                             f"barrier net of bootstrap sampling error (DerSimonian-Laird), sex={sex}",
                                                        Q=float(f"{dl['Q']:.4g}"), Q_p=float(f"{dl['p']:.3g}"), k=dl["k"])
        numbers[f"h2_champ_barrier_pi_width_ms_{sex}"] = num(round(2 * Z975 * dl["tau"], 2), unit="ms",
                                                             desc=f"H2(c) width of the 95% prediction interval of a "
                                                                  f"championship's ex-Gaussian barrier (2 x 1.96 x tau), sex={sex}")
        sub = pa[pa["sex"] == sex].set_index("family")
        numbers[f"h2_family_spread_pooled_ms_{sex}"] = num(round(float(sub["pooled_barrier_ms"].max() - sub["pooled_barrier_ms"].min()), 2),
                                                           unit="ms", desc=f"H2 family-to-family spread (max - min over the "
                                                                           f"three families) of the pooled barrier, sex={sex}")
        numbers[f"h2_family_spread_adjusted_ms_{sex}"] = num(round(float(sub["adj_barrier_ms"].max() - sub["adj_barrier_ms"].min()), 2),
                                                             unit="ms", desc=f"H2 family-to-family spread of the "
                                                                             f"championship-adjusted barrier, sex={sex}")
        numbers[f"h2_family_spread_champ_median_ms_{sex}"] = num(round(float(e["family_spread_ms"].median()), 2), unit="ms",
                                                                 desc=f"H2 median over eligible championships of the "
                                                                      f"family-to-family barrier spread, sex={sex}")
        numbers[f"h2_family_p_ratio_pooled_{sex}"] = num(float(f"{sub['pooled_p'].max() / sub['pooled_p'].min():.4g}"),
                                                         desc=f"H2 max / min over families of the pooled P(RT<0.100), sex={sex}")
    # ---- verdict (primary cell men / ex-Gaussian) -------------------------------------------------------
    crit = {}
    for sex in ("M", "W"):
        for fam in FAMILIES:
            rng_v = numbers[f"h2_champ_barrier_range_ms_{fam}_{sex}"]["value"]
            shift_v = numbers[f"h2_shift_ms_{fam}_{sex}"]["value"]
            guard = (numbers[f"h2_champ_barrier_pi_width_ms_{sex}"]["value"] >= MATERIAL_MS) if fam == PRIMARY_FAMILY else None
            c1 = bool(rng_v >= MATERIAL_MS and (guard if guard is not None else True))
            c2 = bool(abs(shift_v) >= MATERIAL_MS)
            crit[(sex, fam)] = {"C1": c1, "C2": c2, "C1_range_only": bool(rng_v >= MATERIAL_MS), "guard": guard,
                                "shift_ci_lo_clears": bool(numbers[f"h2_shift_ms_{fam}_{sex}"]["ci95"][0] >= MATERIAL_MS)}
    pc = crit[(PRIMARY_SEX, PRIMARY_FAMILY)]
    verdict = h2_verdict(pc["C1"], pc["C2"])
    agree = {f"{s}_{f}": h2_verdict(c["C1"], c["C2"]) for (s, f), c in crit.items() if (s, f) != (PRIMARY_SEX, PRIMARY_FAMILY)}
    fam_flag = any(numbers[f"h2_family_spread_{a}_ms_{s}"]["value"] >= MATERIAL_MS
                   for a in ("pooled", "adjusted") for s in ("M", "W"))
    numbers["h2_verdict"] = num(verdict, desc="pre-registered H2 verdict (prereg_systematic.md), primary cell men / "
                                              "ex-Gaussian: CONSEQUENTIAL if C1 (per-championship spread >= 10 ms and noise "
                                              "guard) or C2 (|pooled - adjusted| >= 10 ms)",
                                C1=pc["C1"], C2=pc["C2"], C1_range_only=pc["C1_range_only"], C1_guard=pc["guard"],
                                C2_ci_lower_clears=pc["shift_ci_lo_clears"], other_cells=agree,
                                family_spread_ge_10ms=fam_flag)
    extra["h2_criteria"] = {f"{s}_{f}": c for (s, f), c in crit.items()}
    return inputs


# =====================================================================================================
# Confounder audit (prereg addendum 3): H3 rule eras, H4 sex x championship, H5 Fiore et al.'s venue, O2
# =====================================================================================================

ERA_POOLS = {"pre2003": ("WCH1999", "WCH2001"),
             "2003_2009": ("WCH2003", "WCH2005", "WCH2007", "WCH2009"),
             "zt": ("WCH2011", "WCH2013", "WCH2015", "WCH2017", "WCH2019", "WCH2022", "WCH2023", "WCH2025",
                    "OG2020", "OG2024")}
WIC_ZT = ("WIC2024", "WIC2025")
HAUGEN_K = {"pre2003": 5, "2003_2009": 5, "zt": 2}      # Haugen et al. 2013 (lit/systematic_forensics.md 1.7)
HAN_K = (11, 8)                                        # Han et al. 2025: senior championships 2010+ vs 2000-2009
PUB_HAUGEN_MS, PUB_HAN_MS = 30.0, -4.0                 # published era effects: +0.03 s (Haugen), -0.004 s (Han)
P_FLIP = 0.10
CONTRASTS = {"c1": ("2003_2009", "pre2003"), "c2": ("zt", "2003_2009"), "c3": ("zt", "pre2003"),
             "c4": ("zt", "pre2010")}
PARAM_DESIGNS = {"c1": ("haugen", 5, 5), "c2": ("haugen", 2, 5), "c3": ("haugen", 2, 5), "c4": ("han",) + HAN_K}
FIORE_TAILS = (1e-2, 1e-3, 1e-4)
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(80)
GH_W = GH_W / np.sqrt(2 * np.pi)


def era_sets(zt_pool) -> dict:
    pools = {"pre2003": list(ERA_POOLS["pre2003"]), "2003_2009": list(ERA_POOLS["2003_2009"]), "zt": list(zt_pool)}
    pools["pre2010"] = pools["pre2003"] + pools["2003_2009"]
    return pools


def haugen_subsets(vals: dict, pools: dict, k: dict):
    """Every design with k championships per era (capped at availability): contrast -> array of values."""
    from itertools import combinations
    ks = {e: min(k[e], len(pools[e])) for e in ("pre2003", "2003_2009", "zt")}
    out, picks = {c: [] for c in CONTRASTS}, []
    for a in combinations(pools["pre2003"], ks["pre2003"]):
        for b in combinations(pools["2003_2009"], ks["2003_2009"]):
            for z in combinations(pools["zt"], ks["zt"]):
                m = {"pre2003": np.mean([vals[x] for x in a]), "2003_2009": np.mean([vals[x] for x in b]),
                     "zt": np.mean([vals[x] for x in z]), "pre2010": np.mean([vals[x] for x in a + b])}
                for c, (A, B) in CONTRASTS.items():
                    out[c].append(m[A] - m[B])
                picks.append("+".join(z))
    return {c: np.array(v_) for c, v_ in out.items()}, ks, picks


def same_rule_null(vals: dict, pool, k1: int, k2: int) -> np.ndarray:
    """'Era contrasts' with no rule change: mean of k1 minus mean of k2 disjoint championships of one era."""
    from itertools import combinations
    out = []
    for g1 in combinations(pool, k1):
        m1 = np.mean([vals[c] for c in g1])
        rest = [c for c in pool if c not in g1]
        out += [m1 - np.mean([vals[c] for c in g2]) for g2 in combinations(rest, k2)]
    return np.array(out)


def within_era_tau(vals: dict, se: dict, pools: dict) -> tuple[float, float]:
    """Between-championship SD within era, pooled over eras, net of estimation error (floored at 0); and raw SD."""
    ss, dof, se2 = 0.0, 0, []
    for e in ("pre2003", "2003_2009", "zt"):
        x = np.array([vals[c] for c in pools[e]])
        ss += float(((x - x.mean()) ** 2).sum())
        dof += len(x) - 1
        se2 += [se[c] ** 2 for c in pools[e]]
    return float(np.sqrt(max(0.0, ss / dof - float(np.mean(se2))))), float(np.sqrt(ss / dof))


def run_h3(args, numbers, tables, extra):
    v, inputs = h2_sample(args.mock)
    levels, off, off_se, Lc, chol, _ = championship_offsets(v)
    cov = Lc @ (chol @ chol.T) @ Lc.T
    adj, adj_se = dict(zip(levels, off)), dict(zip(levels, off_se))
    g = v.groupby("comp_year")["rt_ms"]
    raw, raw_se = g.mean().to_dict(), (g.std(ddof=1) / np.sqrt(g.size())).to_dict()
    era_of = {c: e for e in ("pre2003", "2003_2009", "zt") for c in ERA_POOLS[e]}
    tables["h3_offsets"] = pd.DataFrame([{"comp_year": c, "era": era_of.get(c, "zt (indoor)" if c in WIC_ZT else ""),
                                          "offset_adj_ms": adj[c], "se_adj_ms": adj_se[c], "mean_raw_ms": raw[c],
                                          "se_raw_ms": raw_se[c]} for c in levels])
    res_all, summary = {}, []
    for tag, vals, se_d, cov_m, zt in (("adj", adj, adj_se, cov, ERA_POOLS["zt"]),
                                       ("raw", raw, raw_se, None, ERA_POOLS["zt"]),
                                       ("wic", adj, adj_se, cov, ERA_POOLS["zt"] + WIC_ZT)):
        pools = era_sets(zt)
        tau, sd_pooled = within_era_tau(vals, se_d, pools)
        sub, ks, picks = haugen_subsets(vals, pools, HAUGEN_K)
        null = same_rule_null(vals, pools["zt"], HAUGEN_K["zt"], HAUGEN_K["pre2003"])
        q025, q975 = np.percentile(null, [2.5, 97.5])
        res = {"tau": tau, "sd_pooled": sd_pooled, "ks": ks, "null_q": (float(q025), float(q975)),
               "null_halfwidth": float((q975 - q025) / 2), "null_max_abs": float(np.abs(null).max()),
               "null_share_ge_haugen": float((np.abs(null) >= abs(PUB_HAUGEN_MS)).mean()),
               "null_share_ge_han": float((np.abs(null) >= abs(PUB_HAN_MS)).mean()), "null_n": int(len(null)),
               "han_halfwidth": float(Z975 * tau * np.sqrt(1 / HAN_K[0] + 1 / HAN_K[1])), "contrasts": {}}
        for c, (A, B) in CONTRASTS.items():
            w = np.array([(1 / len(pools[A]) if l in pools[A] else 0.0) - (1 / len(pools[B]) if l in pools[B] else 0.0)
                          for l in levels])
            val = np.array([vals[l] for l in levels])
            d_all = float(w @ val)
            se_all = float(np.sqrt(w @ cov_m @ w)) if cov_m is not None else \
                float(np.sqrt(sum((w[i] * se_d[l]) ** 2 for i, l in enumerate(levels))))
            s = sub[c]
            design, k1, k2 = PARAM_DESIGNS[c]
            sd_k = float(np.sqrt(tau ** 2 * (1 / k1 + 1 / k2) + se_all ** 2))
            res["contrasts"][c] = {"all": d_all, "se": se_all, "n_A": len(pools[A]), "n_B": len(pools[B]),
                                   "sub_min": float(s.min()), "sub_median": float(np.median(s)), "sub_max": float(s.max()),
                                   "sub_p_opposite": float((np.sign(s) != np.sign(d_all)).mean()),
                                   "sub_share_positive": float((s > 0).mean()), "sub_n": int(len(s)),
                                   "param_design": design, "param_k": (k1, k2), "param_sd": sd_k,
                                   "param_p_opposite": float(stats.norm.cdf(-abs(d_all) / sd_k))}
            summary.append({"offsets": tag, "contrast": c, "A": A, "B": B, **{k_: v_ for k_, v_ in res["contrasts"][c].items()
                                                                            if not isinstance(v_, tuple)}})
        res_all[tag] = res
        if tag == "adj":
            tables["h3_designs_adj"] = pd.DataFrame({"zt_pair": picks, **{c: sub[c] for c in CONTRASTS}})
    tables["h3_summary"] = pd.DataFrame(summary)
    r = res_all["adj"]
    numbers["h3_tau_ms"] = num(round(r["tau"], 3), unit="ms",
                               desc="H3: between-championship SD of athlete-adjusted offsets within rule era, pooled over "
                                    "eras, net of estimation error (outdoor pools)",
                               sd_pooled_ms=float(f"{r['sd_pooled']:.4g}"),
                               n_champs={e: len(era_sets(ERA_POOLS['zt'])[e]) for e in ("pre2003", "2003_2009", "zt")})
    labels = {"c1": "2003-2009 minus pre-2003", "c2": "2010+ (zero tolerance) minus 2003-2009",
              "c3": "2010+ minus pre-2003 (Haugen's 15-year span)", "c4": "2010+ minus all pre-2010 (Han's contrast)"}
    for c, cc in r["contrasts"].items():
        numbers[f"h3_{c}_all_ms"] = num(round(cc["all"], 3), ci=(round(cc["all"] - Z975 * cc["se"], 3),
                                                                  round(cc["all"] + Z975 * cc["se"], 3)), unit="ms",
                                        desc=f"H3 era contrast {labels[c]}, all available outdoor championships, "
                                             f"athlete-adjusted offsets (CI conditional on these championships)",
                                        n_A=cc["n_A"], n_B=cc["n_B"])
        numbers[f"h3_{c}_subsets_p_opposite"] = num(
            float(f"{cc['sub_p_opposite']:.4g}"),
            desc=f"H3 (A): share of Haugen-matched designs (k = 5, 5, 2 per era, capped at availability) whose "
                 f"{labels[c]} has the opposite sign to the all-championship estimate",
            min_ms=float(f"{cc['sub_min']:.4g}"), median_ms=float(f"{cc['sub_median']:.4g}"),
            max_ms=float(f"{cc['sub_max']:.4g}"), share_positive=float(f"{cc['sub_share_positive']:.4g}"),
            n_designs=cc["sub_n"], k_used=dict(r["ks"]))
        numbers[f"h3_{c}_{cc['param_design']}_p_opposite"] = num(
            float(f"{cc['param_p_opposite']:.4g}"),
            desc=f"H3 (B): P(opposite sign) for {labels[c]} when the eras are represented by {cc['param_k'][0]} and "
                 f"{cc['param_k'][1]} randomly drawn championships ({cc['param_design']} design; random-championship model)",
            sd_ms=float(f"{cc['param_sd']:.4g}"), k1=cc["param_k"][0], k2=cc["param_k"][1],
            lo95_ms=float(f"{cc['all'] - Z975 * cc['param_sd']:.4g}"), hi95_ms=float(f"{cc['all'] + Z975 * cc['param_sd']:.4g}"))
    numbers["h3_samerule_halfwidth_ms"] = num(round(r["null_halfwidth"], 3), unit="ms",
                                              desc="H3 (C) same-rule null: half-width of the central 95% range of 'era "
                                                   "contrasts' between disjoint groups of 2 and 5 zero-tolerance championships",
                                              q025_ms=float(f"{r['null_q'][0]:.4g}"), q975_ms=float(f"{r['null_q'][1]:.4g}"),
                                              max_abs_ms=float(f"{r['null_max_abs']:.4g}"),
                                              share_ge_haugen=float(f"{r['null_share_ge_haugen']:.4g}"),
                                              share_ge_han=float(f"{r['null_share_ge_han']:.4g}"), n_designs=r["null_n"])
    numbers["h3_han_samerule_halfwidth_ms"] = num(round(r["han_halfwidth"], 3), unit="ms",
                                                  desc="H3 (C) same-rule null for Han et al.'s sizes (11 vs 8 championships): "
                                                       "1.96 x tau x sqrt(1/11 + 1/8)")
    for yr, key in (("WCH2011", "h3_named_wch2011_ms"), ("WCH2022", "h3_named_wch2022_ms")):
        numbers[key] = num(round(adj[yr] - (adj["WCH1999"] + adj["WCH2001"]) / 2, 3), unit="ms",
                           desc=f"H3 named contrast: {yr} minus mean(WCH1999, WCH2001), athlete-adjusted offsets "
                                f"(one zero-tolerance championship standing for its era)",
                           raw_ms=float(f"{raw[yr] - (raw['WCH1999'] + raw['WCH2001']) / 2:.4g}"))
    for tag in ("raw", "wic"):
        rt_ = res_all[tag]
        c2 = rt_["contrasts"]["c2"]
        lab = {"raw": "raw championship means (unadjusted)", "wic": "athlete-adjusted offsets, WIC2024/2025 added to 2010+"}[tag]
        numbers[f"h3_{tag}_c2_all_ms"] = num(round(c2["all"], 3), unit="ms",
                                             desc=f"H3 sensitivity ({lab}): 2010+ minus 2003-2009, all championships")
        numbers[f"h3_{tag}_c2_subsets_p_opposite"] = num(float(f"{c2['sub_p_opposite']:.4g}"),
                                                         desc=f"H3 sensitivity ({lab}): share of Haugen-matched designs "
                                                              f"with the opposite sign (2010+ minus 2003-2009)",
                                                         min_ms=float(f"{c2['sub_min']:.4g}"),
                                                         max_ms=float(f"{c2['sub_max']:.4g}"), n_designs=c2["sub_n"])
        numbers[f"h3_{tag}_c2_haugen_p_opposite"] = num(float(f"{c2['param_p_opposite']:.4g}"),
                                                        desc=f"H3 sensitivity ({lab}): random-championship P(opposite "
                                                             f"sign), 2 vs 5 championships")
        numbers[f"h3_{tag}_tau_ms"] = num(round(rt_["tau"], 3), unit="ms", desc=f"H3 sensitivity ({lab}): within-era "
                                                                                 f"between-championship SD net of error")
        numbers[f"h3_{tag}_samerule_halfwidth_ms"] = num(round(rt_["null_halfwidth"], 3), unit="ms",
                                                         desc=f"H3 sensitivity ({lab}): same-rule 95% half-width, 2 vs 5")
    # ---- verdicts from the stored values ---------------------------------------------------------------
    p_sub = numbers["h3_c2_subsets_p_opposite"]["value"]
    p_par = numbers["h3_c2_haugen_p_opposite"]["value"]
    flip = bool(p_sub >= P_FLIP or p_par >= P_FLIP)
    numbers["h3_verdict_sign"] = num("SAMPLING CAN FLIP THE SIGN" if flip else "SIGN STABLE UNDER SAMPLING",
                                     desc="pre-registered H3 sign verdict (addendum 3): flips if, for 2010+ minus "
                                          "2003-2009, the share of opposite-sign Haugen-matched designs or the "
                                          "random-championship P(opposite sign) is >= 0.10",
                                     p_subsets=p_sub, p_random=p_par)
    hw, hw_han = numbers["h3_samerule_halfwidth_ms"]["value"], numbers["h3_han_samerule_halfwidth_ms"]["value"]
    numbers["h3_verdict_haugen"] = num("WITHIN SAME-RULE NOISE" if abs(PUB_HAUGEN_MS) <= hw else "EXCEEDS SAME-RULE NOISE",
                                       desc="pre-registered H3 verdict for Haugen et al.'s +30 ms era effect vs the "
                                            "same-rule 95% half-width (2 vs 5 championships)",
                                       effect_ms=PUB_HAUGEN_MS, halfwidth_ms=hw)
    numbers["h3_verdict_han"] = num("WITHIN SAME-RULE NOISE" if abs(PUB_HAN_MS) <= hw_han else "EXCEEDS SAME-RULE NOISE",
                                    desc="pre-registered H3 verdict for Han et al.'s -4 ms zero-tolerance effect vs the "
                                         "same-rule 95% half-width (11 vs 8 championships)",
                                    effect_ms=PUB_HAN_MS, halfwidth_ms=hw_han)
    return inputs


def sex_gap_by_championship(v: pd.DataFrame, fx_base: str):
    """Athlete-adjusted sex gap (women minus men, ms) per championship from a sex x championship interaction
    model; LRT against the additive model; average gap = the sex main effect (sum-coded championships)."""
    from lmm import lrt
    re_ = ["race_id", "athlete_id2"]
    base = fx_base + " + C(comp_year, Sum)"
    m_add = fit_formula(base, v, "rt_ms", re_, method="ML")
    m_int = fit_formula(base + " + C(comp_year, Sum):C(sex, Treatment('M'))", v, "rt_ms", re_, method="ML")
    stat, df_, p = lrt(m_int, m_add)
    names = m_int.names
    i_sex = names.index("C(sex, Treatment('M'))[T.W]")
    int_idx = {n.split("[S.")[1].split("]")[0]: i for i, n in enumerate(names)
               if n.startswith("C(comp_year, Sum)[S.") and ":C(sex" in n}
    rows = []
    for lev in sorted(v["comp_year"].unique()):
        L = np.zeros(len(names))
        L[i_sex] = 1.0
        if lev in int_idx:
            L[int_idx[lev]] = 1.0
        else:
            L[list(int_idx.values())] = -1.0
        est, lo, hi, se = m_int.contrast(L)
        rows.append({"comp_year": lev, "gap_ms": est, "lo": lo, "hi": hi, "se": se,
                     "n_M": int(((v["comp_year"] == lev) & (v["sex"] == "M")).sum()),
                     "n_W": int(((v["comp_year"] == lev) & (v["sex"] == "W")).sum())})
    return pd.DataFrame(rows), (stat, df_, p), m_int.coef(names[i_sex])


def run_h4(args, numbers, tables, extra):
    v, inputs = h2_sample(args.mock)
    vf = v[v["event_type"] == "flat"].copy()
    vf["round"] = pd.Categorical(vf["round"].astype(str),
                                 categories=[r_ for r_ in ROUND_ORDER if r_ in set(vf["round"].astype(str))])
    vm = v[v["year"] >= 2015].copy()                     # POST-HOC (addendum 5): athlete-identified championships
    vm["round"] = pd.Categorical(vm["round"].astype(str),
                                 categories=[r_ for r_ in ROUND_ORDER if r_ in set(vm["round"].astype(str))])
    for tag, data, fx in (("", v, FX_NOCHAMP), ("flat_", vf, "C(sex, Treatment('M')) + C(round, Treatment('R1'))"),
                          ("modern_", vm, FX_NOCHAMP)):
        gaps, (stat, df_, p), (mg, mlo, mhi) = sex_gap_by_championship(data, fx)
        dl = dersimonian_laird(gaps["gap_ms"], gaps["se"])
        pi = (mg - Z975 * dl["tau"], mg + Z975 * dl["tau"])
        tables[f"h4_{tag}gaps"] = gaps
        lab = {"": "all events", "flat_": "flat sprints only (100 m, 60 m)",
               "modern_": "POST-HOC: championships from 2015 on (athlete-identified; addendum 5)"}[tag]
        numbers[f"h4_{tag}lrt_chi2"] = num(round(stat, 3), desc=f"H4 LRT: sex x championship interaction vs additive "
                                                               f"model (ML), {lab}", df=df_, p=float(f"{p:.3g}"))
        numbers[f"h4_{tag}gap_mean_ms"] = num(round(mg, 3), ci=(round(mlo, 3), round(mhi, 3)), unit="ms",
                                              desc=f"H4 average athlete-adjusted sex gap (women minus men) over "
                                                   f"championships (sex main effect, sum-coded), {lab}")
        lo_r, hi_r = gaps.loc[gaps["gap_ms"].idxmin()], gaps.loc[gaps["gap_ms"].idxmax()]
        numbers[f"h4_{tag}gap_range_ms"] = num(round(float(hi_r["gap_ms"] - lo_r["gap_ms"]), 3), unit="ms",
                                               desc=f"H4 spread (max - min) of the per-championship sex gap, {lab}",
                                               min_ms=float(f"{lo_r['gap_ms']:.4g}"), min_champ=lo_r["comp_year"],
                                               max_ms=float(f"{hi_r['gap_ms']:.4g}"), max_champ=hi_r["comp_year"],
                                               n_champs=int(len(gaps)))
        numbers[f"h4_{tag}gap_tau_ms"] = num(round(dl["tau"], 3), unit="ms",
                                             desc=f"H4 between-championship SD of the sex gap net of sampling error "
                                                  f"(DerSimonian-Laird), {lab}", Q=float(f"{dl['Q']:.4g}"),
                                             Q_p=float(f"{dl['p']:.3g}"), k=dl["k"])
        numbers[f"h4_{tag}gap_pi_ms"] = num(round(mg, 3), unit="ms", ci=(round(pi[0], 3), round(pi[1], 3)),
                                            desc=f"H4 95% prediction interval (in ci95) of a championship's sex gap: "
                                                 f"average +/- 1.96 tau, {lab}", interval_type="prediction")
        numbers[f"h4_{tag}n_negative"] = num(int((gaps["gap_ms"] < 0).sum()),
                                             desc=f"H4 championships whose point estimate has women faster than men, {lab}",
                                             n_ci_below_0=int((gaps["hi"] < 0).sum()), n_ci_above_0=int((gaps["lo"] > 0).sum()),
                                             n_champs=int(len(gaps)),
                                             negative_champs=gaps.loc[gaps["gap_ms"] < 0, "comp_year"].tolist())
    p = numbers["h4_lrt_chi2"]["p"]
    lo_pi, hi_pi = numbers["h4_gap_pi_ms"]["ci95"]
    verdict = ("NO EVIDENCE OF VARIATION" if p >= 0.05 else
               "CHAMPIONSHIP-DEPENDENT (sign not stable)" if lo_pi <= 0 <= hi_pi else "VARIES IN SIZE, NOT SIGN")
    numbers["h4_verdict"] = num(verdict, desc="pre-registered H4 verdict (addendum 3), all events: LRT p < 0.05 and the "
                                              "prediction interval includes 0 -> championship-dependent (sign not stable)",
                                lrt_p=p, pi95=[lo_pi, hi_pi])
    return inputs


def gg_cdf(y, mu, sigma, nu):
    """CDF of the GAMLSS generalized gamma GG(mu, sigma, nu) (Fiore et al. 2025, eq. for f_Y): z = (y/mu)^nu,
    theta = 1/(sigma^2 nu^2); theta z ~ Gamma(theta)."""
    from scipy import special
    theta = 1.0 / (np.asarray(sigma, float) ** 2 * nu ** 2)
    z = (y / np.asarray(mu, float)) ** nu
    return special.gammaincc(theta, theta * z) if nu < 0 else special.gammainc(theta, theta * z)


def fiore_p(y: float, p: dict, v: float | None = None) -> float:
    """P(RT < y) in Fiore et al.'s model: marginal over venue and heat effects (v None) or at venue effect v
    (marginal over the heat effect only). Gauss-Hermite quadrature replaces their 10^7 draws."""
    sig = np.exp(p["gamma0"] + p["tau_h"] * GH_X)
    if v is None:
        mu = np.exp(p["beta0"] + p["tau_v"] * GH_X)
        return float(GH_W @ gg_cdf(y, mu[:, None], sig[None, :], p["nu"]) @ GH_W)
    return float(gg_cdf(y, np.exp(p["beta0"] + v), sig, p["nu"]) @ GH_W)


def fiore_barrier_ms(q: float, p: dict, v: float | None = None) -> float:
    from scipy import optimize
    return 1000.0 * optimize.brentq(lambda y: fiore_p(y, p, v) - q, 0.01, 0.3, xtol=1e-12)


def parse_venue_pdf(path) -> dict:
    """Per-year venue effects from Fiore et al.'s vector figure (ggplot2 PDF): circle centres per panel, y axis
    calibrated by a least-squares line through the labelled tick marks, x matched to the year of the nearest
    vertical grid line. Returns {'top': {year: effect}, 'bottom': {...}, 'calibration': {...}}."""
    import re
    import zlib
    b = Path(path).read_bytes()
    m = re.search(rb"stream\r?\n", b)
    t = zlib.decompress(b[m.end():b.find(b"endstream", m.end())].rstrip(b"\r\n")).decode("latin-1")
    f = r"(-?\d+\.\d+)"
    circles = [(float(a), float(c), float(e), float(g_)) for a, _, c, e, g_ in
               re.findall(rf"{f} {f} m\s+\S+ \S+ \S+ \S+ \S+ {f} c\s+\S+ \S+ \S+ \S+ {f} \S+ c\s+\S+ \S+ \S+ \S+ \S+ {f} c", t)]
    # centre x = mean of leftmost (m) and rightmost (2nd curve end) x; centre y = mean of top and bottom y
    cents = [((x0 + x1) / 2, (ytop + ybot) / 2) for x0, ytop, x1, ybot in circles]
    labels = [(float(y_), float(val)) for y_, val in re.findall(rf"9\.00 0\.00 0\.00 9\.00 \S+ {f} Tm \((-?\d\.\d\d)\) Tj", t)]
    ticks = sorted({float(y_) for y_ in re.findall(rf"40\.51 {f} m\s+43\.25 \S+ l", t)})
    years = [(float(x_), int(yr)) for x_, yr in re.findall(rf"9\.00 0\.00 0\.00 9\.00 {f} \S+ Tm \((\d{{4}})\) Tj", t)]
    vgrid = sorted({float(x_) for x_, y0, x2, y1 in re.findall(rf"{f} {f} m\s+{f} {f} l", t)
                    if x_ == x2 and abs(float(y1) - float(y0)) > 150})
    out = {"calibration": {}}
    for panel, keep in (("top", lambda y_: y_ > 234.0), ("bottom", lambda y_: y_ < 234.0)):
        tk = [y_ for y_ in ticks if keep(y_)]
        lb = sorted([(y_, val) for y_, val in labels if keep(y_)])
        # each label sits a constant distance below its tick mark: pair them in order
        yy, vv = np.array(tk[:len(lb)]), np.array([val for _, val in lb])
        slope, icpt = np.polyfit(yy, vv, 1)
        resid = float(np.abs(vv - (icpt + slope * yy)).max())
        yrs = sorted({yr for x_, yr in years})
        out["calibration"][panel] = {"per_point": float(slope), "intercept": float(icpt), "max_tick_residual": resid}
        eff = {}
        for cx, cy in cents:
            if keep(cy):
                j = int(np.argmin([abs(cx - gx) for gx in vgrid]))
                eff[yrs[j]] = float(icpt + slope * cy)
        out[panel] = dict(sorted(eff.items()))
    return out


def run_h5(args, numbers, tables, extra):
    pp = pd.read_csv(args.fiore_params, encoding="utf-8-sig")
    inputs = [Path(args.fiore_params)]
    rows, repro_ok = [], True
    for _, r in pp.iterrows():
        p = {k: float(r[k]) for k in ("beta0", "gamma0", "nu", "tau_v", "tau_h")}
        s = str(r["set"])
        pm = {y: fiore_p(y, p) for y in (0.080, 0.090, 0.100)}
        bm = {q: fiore_barrier_ms(q, p) for q in FIORE_TAILS}
        b_med = fiore_barrier_ms(1e-3, p, 0.0)
        bq = {q: fiore_barrier_ms(1e-3, p, p["tau_v"] * stats.norm.ppf(q)) for q in (0.025, 0.25, 0.75, 0.975)}
        rel = abs(pm[0.100] - r["pub_p_lt100"]) / r["pub_p_lt100"]
        diffs = {q: bm[q] - 1000 * r[f"pub_barrier_{t}_s"] for q, t in zip(FIORE_TAILS, ("1e2", "1e3", "1e4"))}
        ok = bool(rel <= 0.05 and all(abs(d_) <= 1.0 for d_ in diffs.values()))
        repro_ok &= ok
        rows.append({"set": s, "p_lt080": pm[0.080], "p_lt090": pm[0.090], "p_lt100": pm[0.100],
                     "pub_p_lt080": r["pub_p_lt080"], "pub_p_lt090": r["pub_p_lt090"], "pub_p_lt100": r["pub_p_lt100"],
                     **{f"barrier_{t}_ms": bm[q] for q, t in zip(FIORE_TAILS, ("1e2", "1e3", "1e4"))},
                     **{f"pub_barrier_{t}_ms": 1000 * r[f"pub_barrier_{t}_s"] for t in ("1e2", "1e3", "1e4")},
                     "median_venue_barrier_1e3_ms": b_med, "median_venue_p_lt100": fiore_p(0.100, p, 0.0),
                     **{f"venue_q{int(q * 1000):03d}_barrier_ms": bq[q] for q in bq}, "reproduced": ok})
        numbers[f"h5_{s}_p_lt100"] = num(float(f"{pm[0.100]:.4g}"),
                                         desc=f"H5 Fiore et al. 2025 model ({s}; published parameters): marginal P(RT<0.100) "
                                              f"over venue and heat (quadrature)", published=float(r["pub_p_lt100"]),
                                         rel_diff=float(f"{rel:.3g}"), p_lt080=float(f"{pm[0.080]:.4g}"),
                                         p_lt090=float(f"{pm[0.090]:.4g}"))
        numbers[f"h5_{s}_barrier_1e3_ms"] = num(round(bm[1e-3], 3), unit="ms",
                                                desc=f"H5 Fiore et al. model ({s}): 1e-3 barrier of the marginal distribution",
                                                published_ms=float(1000 * r["pub_barrier_1e3_s"]),
                                                barrier_1e2_ms=float(f"{bm[1e-2]:.5g}"), barrier_1e4_ms=float(f"{bm[1e-4]:.5g}"),
                                                max_abs_diff_ms=float(f"{max(abs(d_) for d_ in diffs.values()):.3g}"))
        numbers[f"h5_{s}_median_venue_barrier_1e3_ms"] = num(round(b_med, 3), unit="ms",
                                                             desc=f"H5 Fiore et al. model ({s}): 1e-3 barrier at the median "
                                                                  f"venue (venue effect 0; heat integrated)")
        numbers[f"h5_{s}_marginal_minus_median_ms"] = num(round(bm[1e-3] - b_med, 3), unit="ms",
                                                          desc=f"H5 ({s}): marginal minus median-venue 1e-3 barrier "
                                                               f"(what averaging over venues does)")
        from scipy import optimize
        b0_implied = optimize.brentq(lambda b0: fiore_p(0.100, {**p, "beta0": b0}) - float(r["pub_p_lt100"]),
                                     -2.3, -1.5, xtol=1e-10)
        numbers[f"h5_{s}_implied_beta0"] = num(round(b0_implied, 4),
                                               desc=f"H5 POST-HOC diagnostic (addendum 5): intercept beta0 that reproduces "
                                                    f"the published P(RT<0.100) of set {s} with its other printed parameters",
                                               printed_beta0=p["beta0"])
        numbers[f"h5_{s}_venue_range95_ms"] = num(round(bq[0.975] - bq[0.025], 3), unit="ms",
                                                  desc=f"H5 ({s}): 1e-3 barrier at the 97.5th minus the 2.5th percentile "
                                                       f"venue of N(0, tau_v^2) - how far venue moves the barrier inside "
                                                       f"Fiore et al.'s own model",
                                                  q025_barrier_ms=float(f"{bq[0.025]:.5g}"), q975_barrier_ms=float(f"{bq[0.975]:.5g}"),
                                                  iqr_range_ms=float(f"{bq[0.75] - bq[0.25]:.4g}"))
    tables["h5_fiore"] = pd.DataFrame(rows)
    # secondary: the 13 WCH venues' own effects, read from the vector figure (top panel = model incl. 2022)
    if args.fiore_venue_pdf:
        inputs.append(Path(args.fiore_venue_pdf))
        ve = parse_venue_pdf(args.fiore_venue_pdf)
        p0 = {k: float(pp.loc[pp["set"] == "men_incl2022", k].iloc[0]) for k in ("beta0", "gamma0", "nu", "tau_v", "tau_h")}
        yrow = [{"year": yr, "venue_effect": e, "barrier_1e3_ms": fiore_barrier_ms(1e-3, p0, e),
                 "p_lt100": fiore_p(0.100, p0, e), "effect_excl2022": ve["bottom"].get(yr, np.nan)}
                for yr, e in ve["top"].items()]
        yt = pd.DataFrame(yrow)
        tables["h5_venue_years"] = yt
        extra["h5_pdf_calibration"] = ve["calibration"]
        lo_r, hi_r = yt.loc[yt["barrier_1e3_ms"].idxmin()], yt.loc[yt["barrier_1e3_ms"].idxmax()]
        numbers["h5_years_barrier_range_ms"] = num(
            round(float(hi_r["barrier_1e3_ms"] - lo_r["barrier_1e3_ms"]), 3), unit="ms",
            desc="H5 secondary: range of the 1e-3 barrier across the 13 WCH venues (1999-2023) using each venue's own "
                 "effect read from Fiore et al.'s vector figure (removed from the published paper), men incl. 2022",
            min_year=int(lo_r["year"]), min_ms=float(f"{lo_r['barrier_1e3_ms']:.5g}"), max_year=int(hi_r["year"]),
            max_ms=float(f"{hi_r['barrier_1e3_ms']:.5g}"), n_years=int(len(yt)),
            max_tick_residual=float(f"{max(c_['max_tick_residual'] for c_ in ve['calibration'].values()):.3g}"))
        shared = [yr for yr in ve["top"] if yr in ve["bottom"]]
        shift = float(np.mean([ve["top"][yr] for yr in shared]) - np.mean([ve["bottom"][yr] for yr in shared]))
        numbers["h5_pdf_excl2022_intercept_shift"] = num(
            round(shift, 4), desc="H5 POST-HOC diagnostic (addendum 5): mean venue effect over the 12 shared years in the "
                                  "figure's top panel (model incl. 2022) minus the bottom panel (model excl. 2022) - the "
                                  "intercept change that removing 2022 implies", n_years=len(shared))
        e22 = ve["top"].get(2022)
        if e22 is not None:
            numbers["h5_year2022_barrier_1e3_ms"] = num(round(fiore_barrier_ms(1e-3, p0, e22), 3), unit="ms",
                                                         desc="H5 secondary: 1e-3 barrier at the 2022 venue (its effect read "
                                                              "from the figure), men incl. 2022",
                                                         venue_effect=float(f"{e22:.5g}"),
                                                         p_lt100=float(f"{fiore_p(0.100, p0, e22):.4g}"))
    numbers["h5_verdict_reproduced"] = num("REPRODUCED" if repro_ok else "NOT REPRODUCED",
                                           desc="pre-registered H5 reproduction verdict (addendum 3): every published "
                                                "marginal P(RT<0.100) within 5% and every published barrier within 1 ms",
                                           sets={row["set"]: bool(row["reproduced"]) for row in rows})
    x = numbers["h5_men_incl2022_venue_range95_ms"]["value"]
    numbers["h5_verdict_venue"] = num("VENUE MATERIAL WITHIN FIORE ET AL.'S MODEL" if x >= MATERIAL_MS else "NOT MATERIAL",
                                      desc="pre-registered H5 venue verdict: 1e-3 barrier range between the 2.5th and "
                                           "97.5th percentile venues (men incl. 2022) >= 10 ms", range_ms=x)
    return inputs


def run_o2(args, numbers, tables, extra):
    """Optional O2: Pearson r of RT and 100 m time, pooled vs championship-centred vs race-centred."""
    rt, used = load_rt(args.mock, "athletes")
    races, raced = load_races(args.mock)
    rt = attach_races(rt, races)
    rt["valid"] = valid_rt_mask(rt)
    d = rt[rt["valid"] & (rt["event"] == "100m") & rt["comp"].isin(["WCH", "OG"])].copy()
    d["time_s"] = pd.to_numeric(d["result"], errors="coerce")
    d = d[d["time_s"].notna()].reset_index(drop=True)
    rng = np.random.default_rng(args.seed + 301)
    rows = []
    for sex in ("M", "W"):
        ds = d[d["sex"] == sex].reset_index(drop=True)
        race_codes, _ = pd.factorize(ds["race_id"], sort=True)
        comps = sorted(ds["comp_year"].unique())
        cidx = ds["comp_year"].map({c: i for i, c in enumerate(comps)}).to_numpy()
        race_champ = pd.Series(cidx).groupby(race_codes).first().to_numpy()
        R = int(race_codes.max()) + 1
        S_ = race_sums(ds["rt_s"].to_numpy(float), ds["time_s"].to_numpy(float), race_codes, R)
        cr = np.stack([S_[5] - S_[1] * S_[2] / S_[0], S_[3] - S_[1] ** 2 / S_[0], S_[4] - S_[2] ** 2 / S_[0]])
        K = np.vstack([np.ones((1, R)), strat_multiplicities(race_champ, args.boot_r, rng)])
        pooled = r_from_totals(K @ S_.T)
        champ = r_centred_from_totals(np.stack([K[:, race_champ == c] @ S_[:, race_champ == c].T
                                                for c in range(len(comps))], axis=1))
        race = (K @ cr[0]) / np.sqrt((K @ cr[1]) * (K @ cr[2]))
        diff = pooled - champ
        ci = lambda a: (float(np.percentile(a[1:], 2.5)), float(np.percentile(a[1:], 97.5)))
        rows.append({"sex": sex, "n": int(len(ds)), "races": R, "champs": len(comps), "r_pooled": pooled[0],
                     "r_champ": champ[0], "r_race": race[0], "diff": diff[0]})
        for key, arr, lab in (("pooled", pooled, "pooled over championships"),
                              ("champ", champ, "after centring RT and time within championship"),
                              ("race", race, "within race (both centred within race)")):
            lo_, hi_ = ci(arr)
            numbers[f"o2_r_{key}_{sex}"] = num(round(float(arr[0]), 4), ci=(round(lo_, 4), round(hi_, 4)),
                                               desc=f"O2 (optional): Pearson r of RT and 100 m time, {lab}, sex={sex} "
                                                    f"(race-cluster bootstrap within championship)",
                                               n_starts=int(len(ds)), n_races=R, n_champs=len(comps))
        lo_, hi_ = ci(diff)
        numbers[f"o2_diff_{sex}"] = num(round(float(diff[0]), 4), ci=(round(lo_, 4), round(hi_, 4)),
                                        desc=f"O2: pooled minus championship-centred r (paired bootstrap), sex={sex}")
    tables["o2_summary"] = pd.DataFrame(rows)
    verdicts = {}
    for sex in ("M", "W"):
        dv = numbers[f"o2_diff_{sex}"]
        verdicts[sex] = ("CHAMPIONSHIP-CONFOUNDED" if abs(dv["value"]) >= 0.10 and (dv["ci95"][0] > 0 or dv["ci95"][1] < 0)
                         else "NOT CONFOUNDED BY CHAMPIONSHIP")
    numbers["o2_verdict"] = num("CHAMPIONSHIP-CONFOUNDED" if "CHAMPIONSHIP-CONFOUNDED" in verdicts.values()
                                else "NOT CONFOUNDED BY CHAMPIONSHIP",
                                desc="pre-registered O2 verdict (addendum 3): |pooled - championship-centred r| >= 0.10 "
                                     "with a paired CI excluding 0, per sex", **verdicts)
    return used + raced


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--descriptive", required=True)
    ap.add_argument("--fp-models", required=True)
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--boot-r", type=int, default=2000, help="race-cluster bootstrap replicates for the naive r")
    ap.add_argument("--sims", type=int, default=10000, help="simulated datasets per setting (S1, S2, S3)")
    ap.add_argument("--boot-h2", type=int, default=200, help="paired bootstrap replicates for H2 (a)/(b)")
    ap.add_argument("--boot-champ", type=int, default=100, help="bootstrap replicates per championship for H2 (c)")
    ap.add_argument("--min-n", type=int, default=100, help="H2 (c): minimum valid RTs per championship x sex")
    ap.add_argument("--min-races", type=int, default=10, help="H2 (c): minimum races per championship x sex")
    ap.add_argument("--haugen-design", default=None, help="CSV with the Haugen 2013 design (S3; prereg addendum)")
    ap.add_argument("--fiore-params", default=None, help="Fiore et al. 2025 published GG parameters (H5; addendum 3)")
    ap.add_argument("--fiore-venue-pdf", default=None, help="Fiore et al.'s vector venue-effects figure (H5 secondary)")
    ap.add_argument("--skip-h2", action="store_true", help="development only: H1 alone (never registered)")
    ap.add_argument("--only-audit", action="store_true", help="development only: H3-H5/O2 alone (never registered)")
    args = ap.parse_args()
    out = resolve_out(args, "systematic")
    numbers, tables, extra = {}, {}, {"prereg": "analysis/prereg_systematic.md",
                                      "design_constants": {"haugen_r": HAUGEN_R, "p_nontrivial": P_NONTRIVIAL,
                                                           "material_ms": MATERIAL_MS, "barrier_q": BARRIER_Q,
                                                           "threshold_proposals_s": [THRESH_FIORE_S, THRESH_BROSNAN_S]}}
    inputs = [] if args.only_audit else run_h1(args, numbers, tables, extra)
    if not (args.skip_h2 or args.only_audit):
        inputs += run_h2(args, numbers, tables, extra)
    if not args.skip_h2:                       # confounder audit (addendum 3); H1/H2 streams are untouched
        extra["audit_constants"] = {"published_era_effects_ms": {"haugen": PUB_HAUGEN_MS, "han": PUB_HAN_MS},
                                    "haugen_k": HAUGEN_K, "han_k": list(HAN_K), "p_flip": P_FLIP,
                                    "era_pools": {k: list(v_) for k, v_ in ERA_POOLS.items()}, "wic_zt": list(WIC_ZT)}
        inputs += run_h3(args, numbers, tables, extra)
        inputs += run_h4(args, numbers, tables, extra)
        if args.fiore_params:
            inputs += run_h5(args, numbers, tables, extra)
        inputs += run_o2(args, numbers, tables, extra)
    seen, uniq = set(), []
    for p in inputs:
        k = str(Path(p).resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(Path(p))
    p = write_result(out, "systematic", numbers, uniq, args.mock, tables=tables, extra=extra, seed=args.seed)
    for k, val in numbers.items():
        print(f"{k:44s} {val.get('value')!s:>22} {val.get('ci95', '')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
