"""Hazard-rate (temporal-expectation) utilities for foreperiod distributions.

Two predictors are provided for a race with foreperiod t drawn from a starter's
foreperiod distribution g:

* objective hazard   h(t)  = g(t) / (1 - G(t))
* subjective hazard  h~(t) = g~(t) / (1 - G~(t)), where g~ is g blurred by a Gaussian whose
  SD grows in proportion to elapsed time (scalar timing), following Janssen & Shadlen (2005,
  Nat Neurosci 8:234) and the hazard account of the variable-foreperiod effect (Niemi &
  Naatanen 1981, Psychol Bull 89:133). phi is the Weber fraction of interval timing.

For empirical samples (measured foreperiods of one competition or session) g is a Gaussian
KDE (Silverman bandwidth). A survivor floor keeps the objective hazard finite in the far
right tail, where it is undefined for a finite sample.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

GRID = np.round(np.linspace(0.0, 8.0, 4001), 4)  # seconds, 2 ms resolution; long enough that the
# time-proportional blur does not pile mass against the right edge (spurious hazard spike)


def _normalize(grid, pdf):
    pdf = np.clip(np.asarray(pdf, float), 0, None)
    area = np.trapezoid(pdf, grid)
    return pdf / area if area > 0 else pdf


def _cdf(grid, pdf):
    c = np.concatenate([[0.0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(grid))])
    return np.clip(c / c[-1] if c[-1] > 0 else c, 0, 1)


def kde_pdf(samples, grid=GRID, bw="silverman"):
    samples = np.asarray(samples, float)
    samples = samples[np.isfinite(samples)]
    if samples.size < 2 or np.std(samples) == 0:
        # degenerate: narrow Gaussian at the value
        mu = samples.mean() if samples.size else 1.8
        return _normalize(grid, stats.norm.pdf(grid, mu, 0.05))
    k = stats.gaussian_kde(samples, bw_method=bw)
    return _normalize(grid, k(grid))


def blur_time_proportional(grid, pdf, phi: float):
    """Blur a pdf with a Gaussian kernel whose SD is phi * t (Janssen & Shadlen 2005)."""
    if phi <= 0:
        return _normalize(grid, pdf)
    pdf = _normalize(grid, pdf)
    w = pdf * np.gradient(grid)
    keep = w > 1e-12 * w.max()                     # integrate only over the pdf's support
    s = grid[keep][None, :]                        # true foreperiods (cols)
    t = np.maximum(grid, 1e-3)[:, None]            # evaluation times (rows)
    sd = phi * t
    kern = np.exp(-0.5 * ((s - t) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
    blurred = kern @ w[keep]
    return _normalize(grid, blurred)


def hazard_from_pdf(grid, pdf, s_floor: float = 0.01):
    pdf = _normalize(grid, pdf)
    surv = 1.0 - _cdf(grid, pdf)
    return pdf / np.maximum(surv, s_floor)


def hazard_curve(samples=None, pdf=None, grid=GRID, phi: float = 0.0, s_floor: float = 0.01):
    """Hazard on ``grid`` from either FP samples (KDE) or an explicit pdf; phi>0 -> subjective."""
    if pdf is None:
        pdf = kde_pdf(samples, grid)
    pdf = blur_time_proportional(grid, pdf, phi) if phi > 0 else _normalize(grid, pdf)
    return hazard_from_pdf(grid, pdf, s_floor)


def hazard_at(t, samples=None, pdf=None, grid=GRID, phi: float = 0.0, s_floor: float = 0.01):
    h = hazard_curve(samples, pdf, grid, phi, s_floor)
    return np.interp(np.asarray(t, float), grid, h)


def group_hazard(df, fp_col: str, group_col: str, phi: float = 0.0, loo: bool = False,
                 s_floor: float = 0.01, min_n: int = 5, fallback_samples=None):
    """Hazard of each row's foreperiod under its group's empirical FP distribution.

    One row per race is expected. Groups with fewer than ``min_n`` races fall back to the
    pooled distribution (``fallback_samples`` or all rows). ``loo`` excludes the race itself.
    """
    import pandas as pd
    pooled = np.asarray(fallback_samples if fallback_samples is not None else df[fp_col], float)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for _, g in df.groupby(group_col):
        fps = g[fp_col].to_numpy(float)
        if len(fps) < min_n:
            out.loc[g.index] = hazard_at(fps, samples=pooled, phi=phi, s_floor=s_floor)
            continue
        if not loo:
            out.loc[g.index] = hazard_at(fps, samples=fps, phi=phi, s_floor=s_floor)
        else:
            for i, idx in enumerate(g.index):
                others = np.delete(fps, i)
                out.loc[idx] = hazard_at(fps[i], samples=others, phi=phi, s_floor=s_floor)
    return out


# ---- parametric starter policies used by the fairness simulation -------------------

def truncnorm_pdf(grid, mean, sd, lo, hi):
    a, b = (lo - mean) / sd, (hi - mean) / sd
    return _normalize(grid, stats.truncnorm.pdf(grid, a, b, loc=mean, scale=sd))


def uniform_pdf(grid, lo, hi):
    return _normalize(grid, ((grid >= lo) & (grid <= hi)).astype(float))


def shifted_exponential_pdf(grid, lo, mean, hi=None):
    """Non-ageing policy: flat objective hazard 1/(mean-lo) after ``lo`` (optionally truncated)."""
    lam = 1.0 / (mean - lo)
    pdf = np.where(grid >= lo, lam * np.exp(-lam * (grid - lo)), 0.0)
    if hi is not None:
        pdf = np.where(grid <= hi, pdf, 0.0)
    return _normalize(grid, pdf)


def two_point_pdf(grid, a, b, width=0.005):
    """Two equiprobable foreperiods (lab design), as narrow Gaussians."""
    return _normalize(grid, stats.norm.pdf(grid, a, width) + stats.norm.pdf(grid, b, width))


def pdf_sample(grid, pdf, n, rng):
    c = _cdf(grid, _normalize(grid, pdf))
    u = rng.random(n)
    return np.interp(u, c, grid)


# ---- further temporal-expectation predictors (lit/review.md section 5.11) -----------------------

def abort_hazard_curve(samples=None, pdf=None, grid=GRID, catch: float = 0.05):
    """Objective hazard when a share ``catch`` of set commands end without a gun (aborted
    starts act as catch trials): h_c(t) = (1-c) f(t) / (1 - (1-c) F(t)); finite at the right tail."""
    if pdf is None:
        pdf = kde_pdf(samples, grid)
    pdf = _normalize(grid, pdf)
    cdf = _cdf(grid, pdf)
    return (1 - catch) * pdf / (1 - (1 - catch) * cdf)


def recip_pdf_curve(samples=None, pdf=None, grid=GRID, phi: float = 0.21, floor: float = 1e-3):
    """Reciprocal of the Weber-blurred PDF (Grabenhorst et al. 2019): larger = less expected."""
    if pdf is None:
        pdf = kde_pdf(samples, grid)
    b = blur_time_proportional(grid, pdf, phi) if phi > 0 else _normalize(grid, pdf)
    return 1.0 / np.maximum(b, floor * b.max())


def blurred_cdf_curve(samples=None, pdf=None, grid=GRID, phi: float = 0.26):
    """Weber-blurred CDF: a reduced-form stand-in for trace-based (fMTP-like) preparation that
    rises until the typical hold and then plateaus. Not the full fMTP model."""
    if pdf is None:
        pdf = kde_pdf(samples, grid)
    b = blur_time_proportional(grid, pdf, phi) if phi > 0 else _normalize(grid, pdf)
    return _cdf(grid, b)


def group_curve_at(df, fp_col: str, group_col: str, curve_fn, min_n: int = 5, **kw):
    """Evaluate ``curve_fn(samples=..., **kw)`` (a curve on GRID) at each row's foreperiod, using
    the row's group sample; groups smaller than ``min_n`` use the pooled sample."""
    import pandas as pd
    pooled = df[fp_col].to_numpy(float)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for _, g in df.groupby(group_col):
        fps = g[fp_col].to_numpy(float)
        curve = curve_fn(samples=fps if len(fps) >= min_n else pooled, **kw)
        out.loc[g.index] = np.interp(fps, GRID, curve)
    return out
