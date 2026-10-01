"""Reaction-time distribution families with truncated maximum-likelihood fitting.

Observed legal RTs are left-truncated at the 0.100 s false-start threshold (faster
responses are disqualified) and we also right-truncate at ``hi`` (default 0.300 s) to drop
hesitations and misreads. The likelihood of each observation is f(x) / (F(hi) - F(lo)); lo
and hi may differ per observation (needed when RTs are re-centred by meet or by model). The
mass a fitted family puts below 0.100 s is an *extrapolation*; that is why three families
are fitted and compared.

Families (all in seconds):
  exgauss   Gaussian(mu, sigma) + Exponential(tau)   == scipy.stats.exponnorm(K=tau/sigma, loc=mu, scale=sigma)
  slognorm  shift + LogNormal(m, s)                   == scipy.stats.lognorm(s, loc=shift, scale=exp(m))
  swald     shift + inverse Gaussian                  == scipy.stats.invgauss(a, loc=shift, scale=b)

Likelihoods use closed-form log-densities / CDFs (scipy.special) for speed; they are checked
against scipy.stats in tests/test_rtdist.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import optimize, special, stats

_LOG2PI = np.log(2 * np.pi)


@dataclass
class Fit:
    family: str
    params: dict
    loglik: float
    n: int
    lo: float
    hi: float
    k: int = 3
    extra: dict = field(default_factory=dict)

    @property
    def aic(self):
        return 2 * self.k - 2 * self.loglik

    def dist(self, shift: float = 0.0, sigma: float | None = None):
        return make_dist(self.family, self.params, shift=shift, sigma=sigma)

    def cdf(self, x, shift: float = 0.0, sigma: float | None = None):
        return cdf(self.family, self.params, np.asarray(x, float) - shift, sigma=sigma)

    def mean(self):
        return float(self.dist().mean())

    def as_dict(self):
        return {"family": self.family, "params": self.params, "loglik": self.loglik, "aic": self.aic,
                "n": self.n, "lo": self.lo, "hi": self.hi, **self.extra}


def make_dist(family: str, p: dict, shift: float = 0.0, sigma: float | None = None):
    """Frozen scipy distribution (``shift`` moves it; ``sigma`` replaces the ex-Gaussian SD)."""
    if family == "exgauss":
        s = p["sigma"] if sigma is None else sigma
        return stats.exponnorm(K=p["tau"] / s, loc=p["mu"] + shift, scale=s)
    if family == "slognorm":
        return stats.lognorm(p["s"], loc=p["shift"] + shift, scale=np.exp(p["m"]))
    if family == "swald":
        return stats.invgauss(p["a"], loc=p["shift"] + shift, scale=p["b"])
    raise ValueError(family)


# ---- closed-form log-density and CDF ------------------------------------------------------

def logpdf(family: str, p: dict, x):
    x = np.asarray(x, float)
    if family == "exgauss":
        mu, s, t = p["mu"], p["sigma"], p["tau"]
        return -np.log(t) + (mu - x) / t + s * s / (2 * t * t) + special.log_ndtr((x - mu) / s - s / t)
    if family == "slognorm":
        y = x - p["shift"]
        with np.errstate(divide="ignore", invalid="ignore"):
            ly = np.log(np.where(y > 0, y, np.nan))
            out = -ly - np.log(p["s"]) - 0.5 * _LOG2PI - (ly - p["m"]) ** 2 / (2 * p["s"] ** 2)
        return np.where(y > 0, out, -np.inf)
    if family == "swald":
        a, b = p["a"], p["b"]
        y = (x - p["shift"]) / b
        with np.errstate(divide="ignore", invalid="ignore"):
            yy = np.where(y > 0, y, np.nan)
            out = -0.5 * _LOG2PI - 1.5 * np.log(yy) - (yy - a) ** 2 / (2 * yy * a * a) - np.log(b)
        return np.where(y > 0, out, -np.inf)
    raise ValueError(family)


def cdf(family: str, p: dict, x, sigma: float | None = None):
    x = np.asarray(x, float)
    if family == "exgauss":
        mu, t = p["mu"], p["tau"]
        s = p["sigma"] if sigma is None else sigma
        z = (x - mu) / s
        second = np.exp((mu - x) / t + s * s / (2 * t * t) + special.log_ndtr(z - s / t))
        return np.clip(special.ndtr(z) - second, 0.0, 1.0)
    if family == "slognorm":
        y = x - p["shift"]
        with np.errstate(divide="ignore", invalid="ignore"):
            c = special.ndtr((np.log(np.where(y > 0, y, np.nan)) - p["m"]) / p["s"])
        return np.where(y > 0, c, 0.0)
    if family == "swald":
        a, b = p["a"], p["b"]
        y = (x - p["shift"]) / b
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            yy = np.where(y > 0, y, np.nan)
            r = np.sqrt(1.0 / yy)
            c = special.ndtr(r * (yy / a - 1)) + np.exp(2.0 / a + special.log_ndtr(-r * (yy / a + 1)))
        return np.where(y > 0, np.clip(c, 0.0, 1.0), 0.0)
    raise ValueError(family)


# ---- parameter transforms --------------------------------------------------------------------

def _unpack(family, th, xmin):
    if family == "exgauss":
        return {"mu": th[0], "sigma": np.exp(th[1]), "tau": np.exp(th[2])}
    if family == "slognorm":
        return {"shift": xmin - 1e-4 - np.exp(th[0]), "m": th[1], "s": np.exp(th[2])}
    if family == "swald":
        return {"shift": xmin - 1e-4 - np.exp(th[0]), "a": np.exp(th[1]), "b": np.exp(th[2])}
    raise ValueError(family)


def _pack(family, p, xmin):
    if family == "exgauss":
        return np.array([p["mu"], np.log(p["sigma"]), np.log(p["tau"])])
    gap = max(xmin - 1e-4 - p["shift"], 1e-6)
    if family == "slognorm":
        return np.array([np.log(gap), p["m"], np.log(p["s"])])
    return np.array([np.log(gap), np.log(p["a"]), np.log(p["b"])])


def _starts(family, x):
    xmin, med, sd = x.min(), np.median(x), x.std()
    if family == "exgauss":
        return [np.array([med - 0.4 * sd, np.log(0.7 * sd), np.log(0.5 * sd)]),
                np.array([med - 0.8 * sd, np.log(0.5 * sd), np.log(0.9 * sd)])]
    out = []
    for gap in (0.2 * sd + 1e-3, 1.0 * sd, 3.0 * sd):
        c = xmin - gap
        y = x - c
        if family == "slognorm":
            ly = np.log(y)
            out.append(np.array([np.log(max(gap - 1e-4, 1e-6)), ly.mean(), np.log(ly.std())]))
        else:
            lam = y.mean() ** 3 / y.var()            # IG(mean, shape) -> scipy a = mean/lam, scale = lam
            out.append(np.array([np.log(max(gap - 1e-4, 1e-6)), np.log(y.mean() / lam), np.log(lam)]))
    return out


def _nll(family, th, x, lo, hi, xmin):
    p = _unpack(family, th, xmin)
    lp = logpdf(family, p, x)
    z = cdf(family, p, hi) - cdf(family, p, lo)
    if not np.all(np.isfinite(lp)):
        return 1e12
    z = np.asarray(z, float)
    if np.any(~np.isfinite(z)) or np.any(z <= 1e-300):
        return 1e12
    lz = np.log(z)
    return -(lp.sum() - (lz.sum() if lz.ndim else len(x) * lz))


def fit_family(x, family: str, lo=0.100, hi=0.300, start: dict | None = None) -> Fit:
    """Truncated MLE. ``lo``/``hi`` are scalars or per-observation arrays (same length as x).
    ``start`` (a params dict, e.g. the full-sample fit) warm-starts bootstrap refits."""
    x = np.asarray(x, float)
    lo_a = np.broadcast_to(np.asarray(lo, float), x.shape)
    hi_a = np.broadcast_to(np.asarray(hi, float), x.shape)
    keep = (x >= lo_a) & (x <= hi_a) & np.isfinite(x)
    per_obs = np.ndim(lo) > 0 or np.ndim(hi) > 0
    x = x[keep]
    lo_v = lo_a[keep] if per_obs else float(lo)
    hi_v = hi_a[keep] if per_obs else float(hi)
    xmin = float(x.min())
    starts = [_pack(family, start, xmin)] if start is not None else _starts(family, x)
    best = None
    for th0 in starts:
        f = lambda th: _nll(family, th, x, lo_v, hi_v, xmin)
        r = optimize.minimize(f, th0, method="L-BFGS-B", options={"maxiter": 1000})
        if not np.isfinite(r.fun) or r.fun >= 1e11:
            r = optimize.minimize(f, th0, method="Nelder-Mead",
                                  options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    # polish
    f = lambda th: _nll(family, th, x, lo_v, hi_v, xmin)
    r = optimize.minimize(f, best.x, method="Nelder-Mead",
                          options={"xatol": 1e-9, "fatol": 1e-11, "maxiter": 600, "initial_simplex": None})
    if r.fun < best.fun:
        best = r
    p = {k: float(v) for k, v in _unpack(family, best.x, xmin).items()}
    lo_r = float(np.min(lo_v)) if per_obs else float(lo_v)
    hi_r = float(np.max(hi_v)) if per_obs else float(hi_v)
    return Fit(family, p, float(-best.fun), int(len(x)), lo_r, hi_r,
               extra={"converged": bool(best.success), "per_obs_truncation": bool(per_obs)})


def fit_all(x, lo=0.100, hi=0.300, families=("exgauss", "slognorm", "swald")) -> dict[str, Fit]:
    return {f: fit_family(x, f, lo, hi) for f in families}


def truncated_ks(fit: Fit, x) -> tuple[float, float]:
    """KS statistic against the fitted *truncated* CDF (scalar bounds only; the p-value is
    optimistic because parameters were estimated from the same data)."""
    x = np.asarray(x, float)
    x = x[(x >= fit.lo) & (x <= fit.hi)]
    flo, fhi = cdf(fit.family, fit.params, fit.lo), cdf(fit.family, fit.params, fit.hi)
    r = stats.kstest(x, lambda v: (cdf(fit.family, fit.params, v) - flo) / (fhi - flo))
    return float(r.statistic), float(r.pvalue)


def mass_below(fit: Fit, t: float = 0.100, shift: float = 0.0, sigma: float | None = None) -> float:
    """Untruncated probability that a response from the fitted family is faster than t."""
    return float(cdf(fit.family, fit.params, t - shift, sigma=sigma))


def quantile(family: str, p: dict, q: float, shift: float = 0.0, sigma: float | None = None):
    return float(make_dist(family, p, shift=shift, sigma=sigma).ppf(q))
