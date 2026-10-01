# Planning calc only (NOT a paper result): sensitivity of P(RT<0.100) to location/scale shifts,
# using the published men's GG-GAMLSS fit of Fiore, Schifano & Yan (2025), Table 2 (incl. 2022).
import numpy as np
from scipy import stats, integrate
b0, g0, nu, tv, th = -1.910, -2.200, -1.178, 0.058, 0.320
def p_below(y, mu, sigma, nu=nu):
    theta = 1.0/(sigma**2 * nu**2)
    z = (y/mu)**nu
    if nu < 0:
        return stats.gamma.sf(theta*z, a=theta)
    return stats.gamma.cdf(theta*z, a=theta)
mu0, s0 = np.exp(b0), np.exp(g0)
print(f"median-ish mu={mu0*1000:.1f} ms, sigma={s0:.4f}")
print("conditional P(<0.100) at h=v=0:", p_below(0.100, mu0, s0))
# marginal over heat effect on log sigma and venue effect on log mu (Gauss-Hermite)
xh, wh = np.polynomial.hermite_e.hermegauss(80)
def marginal(y, dlogmu=0.0, dlogsig=0.0, th=th, tv=tv):
    tot = 0.0
    for a, wa in zip(xh, wh):
        for b, wb in zip(xh, wh):
            tot += wa*wb*p_below(y, np.exp(b0+dlogmu+tv*a), np.exp(g0+dlogsig+th*b))
    return tot/(np.sqrt(2*np.pi)**2)
m = marginal(0.100)
print(f"marginal P(<0.100) = {m:.2e} (1 in {1/m:.0f}); Fiore reports 2.76e-3 (1 in 362)")
for d_ms in [-10,-5,-3,3,5,10]:
    dl = np.log((mu0*1000+d_ms)/(mu0*1000))
    mm = marginal(0.100, dlogmu=dl)
    print(f"shift location by {d_ms:+d} ms -> marginal P={mm:.2e}, ratio={mm/m:.2f}")
for ds in [-0.2,-0.1,0.1,0.2]:
    mm = marginal(0.100, dlogsig=ds)
    print(f"shift log-sigma by {ds:+.1f} -> marginal P={mm:.2e}, ratio={mm/m:.2f}")
# share of tail from high-dispersion heats: P conditional on heat effect quantiles
for q in [0.1,0.5,0.9,0.975]:
    hq = stats.norm.ppf(q)*th
    c = sum(wb*p_below(0.100, np.exp(b0+tv*b), np.exp(g0+hq)) for b,wb in zip(xh,wh))/np.sqrt(2*np.pi)
    print(f"heat-effect quantile {q}: P(<0.100)={c:.2e}")
