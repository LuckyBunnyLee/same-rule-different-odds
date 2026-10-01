"""Linear mixed model with crossed random intercepts, fitted by exact (RE)ML.

    y = X b + sum_k Z_k u_k + e,   u_k ~ N(0, s2 * g_k I),   e ~ N(0, s2 I)

The profiled (RE)ML likelihood is evaluated with the Woodbury identity, so every step
works with the q x q matrix M = Z'Z + G^-1 (q = total number of random-effect levels):
    |V| = s2^n |G| |M|,   V^-1 = (I - Z M^-1 Z') / s2.
statsmodels' MixedLM handles crossed factors (race x athlete) only through one giant group
and is very slow for n ~ 5,000; this engine is exact and fast for q up to a few thousand.
Validated against statsmodels on a single-factor model in tests/test_lmm.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy import linalg, optimize, stats


@dataclass
class LMMResult:
    names: list
    beta: np.ndarray
    cov_beta: np.ndarray
    sigma2: float
    var_comp: dict            # name -> variance (same units as y^2)
    loglik: float
    method: str
    n: int
    p: int
    k: int                    # number of variance parameters incl. residual
    blups: dict = field(default_factory=dict)
    converged: bool = True
    levels: dict = field(default_factory=dict)

    @property
    def se(self):
        return np.sqrt(np.diag(self.cov_beta))

    @property
    def aic(self):
        return -2 * self.loglik + 2 * (self.p + self.k)

    def coef_table(self, level=0.95):
        z = stats.norm.ppf(0.5 + level / 2)
        se = self.se
        return pd.DataFrame({"coef": self.beta, "se": se, "lo": self.beta - z * se,
                             "hi": self.beta + z * se,
                             "p": 2 * stats.norm.sf(np.abs(self.beta / se))}, index=self.names)

    def coef(self, name):
        i = self.names.index(name)
        z = stats.norm.ppf(0.975)
        return float(self.beta[i]), float(self.beta[i] - z * self.se[i]), float(self.beta[i] + z * self.se[i])

    def contrast(self, L):
        """Estimate and 95% CI of L @ beta (L: vector over names)."""
        L = np.asarray(L, float)
        est = float(L @ self.beta)
        se = float(np.sqrt(L @ self.cov_beta @ L))
        z = stats.norm.ppf(0.975)
        return est, est - z * se, est + z * se, se

    def icc(self, comp: str, denom: list | None = None):
        denom = denom if denom is not None else list(self.var_comp)
        tot = sum(self.var_comp[c] for c in denom) + self.sigma2
        return self.var_comp[comp] / tot


def indicator(codes) -> tuple[sp.csr_matrix, list]:
    cat = pd.Categorical(codes)
    n, q = len(cat), len(cat.categories)
    ok = cat.codes >= 0
    Z = sp.csr_matrix((np.ones(ok.sum()), (np.nonzero(ok)[0], cat.codes[ok])), shape=(n, q))
    return Z, list(cat.categories)


def fit_lmm(y, X, names, re: dict, method: str = "REML", start=None) -> LMMResult:
    """Fit y ~ X with independent random intercepts for each entry of ``re`` (name -> codes).

    The factor with the most levels is eliminated analytically: its block of Z'Z is diagonal,
    so M = [[D, B], [B', C]] is solved through the Schur complement S = C - B' D^-1 B.
    """
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, p = X.shape
    keys = list(re.keys())
    Zs, levels = {}, {}
    for k in keys:
        Zs[k], levels[k] = indicator(re[k])
    qs = {k: Zs[k].shape[1] for k in keys}
    k1 = max(keys, key=lambda k: qs[k])                  # eliminated (diagonal) factor
    rest = [k for k in keys if k != k1]
    Z1 = Zs[k1]
    cnt1 = np.asarray(Z1.sum(axis=0)).ravel()
    a1X, a1y = np.asarray(Z1.T @ X), np.asarray(Z1.T @ y).ravel()
    if rest:
        Zr = sp.hstack([Zs[k] for k in rest]).tocsr()
        B = (Z1.T @ Zr).tocsr()                           # q1 x q2, sparse (athlete x race incidence)
        C0 = (Zr.T @ Zr).toarray()                        # q2 x q2
        a2X, a2y = np.asarray(Zr.T @ X), np.asarray(Zr.T @ y).ravel()
        blocks2 = np.repeat(np.arange(len(rest)), [qs[k] for k in rest])
    XtX, Xty, yty = X.T @ X, X.T @ y, float(y @ y)
    reml = method.upper() == "REML"
    dfree = n - p if reml else n
    order = [k1] + rest

    def solve_M(g, a1, a2, fac):
        """M^-1 [a1; a2] given the factorisation from ``factor``."""
        dinv, c = fac
        if not rest:
            return dinv[:, None] * a1 if a1.ndim == 2 else dinv * a1, None
        t = a2 - B.T @ (dinv[:, None] * a1 if a1.ndim == 2 else dinv * a1)
        u2 = linalg.cho_solve(c, t, check_finite=False)
        u1 = (dinv[:, None] if a1.ndim == 2 else dinv) * (a1 - B @ u2)
        return u1, u2

    def factor(logg):
        g = np.exp(logg)
        d = cnt1 + 1.0 / g[0]
        dinv = 1.0 / d
        logdet = np.log(d).sum()
        c = None
        if rest:
            S = C0 + np.diag(1.0 / g[1:][blocks2]) - (B.T @ sp.diags(dinv) @ B).toarray()
            try:
                c = linalg.cho_factor(S, lower=True, check_finite=False)
            except linalg.LinAlgError:
                return None
            logdet += 2 * np.log(np.diag(c[0])).sum()
        # log|G| = sum_k q_k log g_k
        logG = qs[k1] * logg[0] + sum(qs[k] * logg[i + 1] for i, k in enumerate(rest))
        return (dinv, c), logdet + logG

    def core(logg):
        f = factor(logg)
        if f is None:
            return None
        fac, logdetV0 = f
        uX1, uX2 = solve_M(None, a1X, a2X if rest else None, fac)
        uy1, uy2 = solve_M(None, a1y, a2y if rest else None, fac)
        XVX = XtX - a1X.T @ uX1 - (a2X.T @ uX2 if rest else 0)
        XVy = Xty - a1X.T @ uy1 - (a2X.T @ uy2 if rest else 0)
        yVy = yty - a1y @ uy1 - (a2y @ uy2 if rest else 0)
        try:
            beta = linalg.solve(XVX, XVy, assume_a="pos")
        except linalg.LinAlgError:
            return None
        s2 = (yVy - XVy @ beta) / dfree
        if not np.isfinite(s2) or s2 <= 0:
            return None
        if reml:
            ll = -0.5 * (dfree * np.log(s2) + logdetV0 + np.linalg.slogdet(XVX)[1] + dfree * (1 + np.log(2 * np.pi)))
        else:
            ll = -0.5 * (n * np.log(s2) + logdetV0 + n * (1 + np.log(2 * np.pi)))
        return ll, beta, s2, XVX, fac

    def nll(logg_ordered):
        r = core(np.clip(logg_ordered, -12, 8))
        return 1e15 if r is None else -r[0]

    if start is None:
        x0 = np.log(np.full(len(order), 0.3))
    else:
        x0 = np.log(np.maximum(np.array([start[keys.index(k)] for k in order], float), 1e-4))
    best = None
    for s0 in (x0, x0 - 2.0, x0 + 1.0):
        r = optimize.minimize(nll, s0, method="L-BFGS-B", bounds=[(-12, 8)] * len(order),
                              options={"maxiter": 500})
        if best is None or r.fun < best.fun:
            best = r
    r = optimize.minimize(nll, best.x, method="Nelder-Mead",
                          options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 300})
    if r.fun < best.fun:
        best = r
    logg = np.clip(best.x, -12, 8)
    ll, beta, s2, XVX, fac = core(logg)
    cov = s2 * np.linalg.inv(XVX)
    g = np.exp(logg)
    var_comp = {k: float(s2 * g[order.index(k)]) for k in keys}
    # numerical Hessian of -loglik in log-variance-ratio space (for delta-method CIs)
    K = len(order)
    h = 1e-3
    H = np.zeros((K, K))
    f0 = nll(logg)
    for i in range(K):
        for j in range(i, K):
            ei, ej = np.eye(K)[i] * h, np.eye(K)[j] * h
            if i == j:
                H[i, i] = (nll(logg + ei) - 2 * f0 + nll(logg - ei)) / h ** 2
            else:
                H[i, j] = H[j, i] = (nll(logg + ei + ej) - nll(logg + ei - ej) -
                                     nll(logg - ei + ej) + nll(logg - ei - ej)) / (4 * h * h)
    try:
        cov_logg = np.linalg.inv(H)
        if not np.all(np.isfinite(cov_logg)) or np.any(np.diag(cov_logg) <= 0):
            cov_logg = None
    except np.linalg.LinAlgError:
        cov_logg = None
    # BLUPs: u = M^-1 Z'(y - X beta)
    res = y - X @ beta
    u1, u2 = solve_M(None, np.asarray(Z1.T @ res).ravel(),
                     np.asarray(Zr.T @ res).ravel() if rest else None, fac)
    blups = {k1: pd.Series(u1, index=levels[k1])}
    i0 = 0
    for k in rest:
        blups[k] = pd.Series(u2[i0:i0 + qs[k]], index=levels[k])
        i0 += qs[k]
    res_obj = LMMResult(list(names), beta, cov, float(s2), var_comp, float(ll), method.upper(), n, p,
                        len(keys) + 1, blups, bool(best.success), levels)
    res_obj.logg = {k: float(logg[order.index(k)]) for k in keys}
    res_obj.cov_logg = cov_logg
    res_obj.order = order
    return res_obj


def ratio_ci(res: LMMResult, num_keys: list, den_keys: list, level=0.95, include_resid=True):
    """Point estimate and delta-method CI (logit scale) for a variance share such as an ICC:
        sum_{num} var_k / (sum_{den} var_k + [sigma2]).
    Uses the Hessian in log variance-ratio space; sigma2 cancels out of the ratio."""
    order = res.order
    lg = np.array([res.logg[k] for k in order])

    def share(l):
        g = dict(zip(order, np.exp(l)))
        num_ = sum(g[k] for k in num_keys)
        den_ = sum(g[k] for k in den_keys) + (1.0 if include_resid else 0.0)
        return num_ / den_

    est = share(lg)
    if res.cov_logg is None or not (0 < est < 1):
        return est, float("nan"), float("nan")
    eps = 1e-5
    grad = np.array([(np.log(share(lg + e) / (1 - share(lg + e))) -
                      np.log(share(lg - e) / (1 - share(lg - e)))) / (2 * eps)
                     for e in np.eye(len(order)) * eps])
    se = float(np.sqrt(grad @ res.cov_logg @ grad))
    z = stats.norm.ppf(0.5 + level / 2)
    lo_, hi_ = np.log(est / (1 - est)) - z * se, np.log(est / (1 - est)) + z * se
    return float(est), float(1 / (1 + np.exp(-lo_))), float(1 / (1 + np.exp(-hi_)))


def sd_ci(res: LMMResult, key: str, level=0.95):
    """SD of a random effect with a delta-method CI on the log scale (sigma2 treated as fixed)."""
    sd = float(np.sqrt(res.var_comp[key]))
    if res.cov_logg is None:
        return sd, float("nan"), float("nan")
    i = res.order.index(key)
    se_log_sd = 0.5 * float(np.sqrt(res.cov_logg[i, i]))
    z = stats.norm.ppf(0.5 + level / 2)
    return sd, float(sd * np.exp(-z * se_log_sd)), float(sd * np.exp(z * se_log_sd))


def fit_formula(formula_rhs: str, data: pd.DataFrame, y: str, re: list, method="REML", **kw):
    """Convenience wrapper: patsy RHS formula + list of random-intercept columns."""
    import patsy
    # positional index: bootstrap samples repeat rows (duplicate labels), and label-based
    # alignment with patsy's kept rows would otherwise duplicate them again
    data = data.reset_index(drop=True)
    keep = data[y].notna()
    for c in re:
        keep &= data[c].notna()
    data = data.loc[keep]
    X = patsy.dmatrix(formula_rhs, data, return_type="dataframe")   # drops rows with NA covariates
    data = data.loc[X.index]                                          # ... so align y and groups to it
    res = fit_lmm(data[y].to_numpy(float), X.to_numpy(float), list(X.columns),
                  {c: data[c].astype(str).to_numpy() for c in re}, method=method, **kw)
    res.design_info = X.design_info
    res.n_dropped = int((~keep).sum() + (keep.sum() - len(X)))
    return res


def lrt(full: LMMResult, reduced: LMMResult):
    """Likelihood-ratio test between nested ML fits (fixed-effect comparison)."""
    if full.method != "ML" or reduced.method != "ML":
        raise ValueError("LRT for fixed effects requires ML fits")
    stat = 2 * (full.loglik - reduced.loglik)
    df = (full.p + full.k) - (reduced.p + reduced.k)
    return float(stat), int(df), float(stats.chi2.sf(max(stat, 0), df))
