# Planning/illustration only (NOT data): theoretical RT-predictor shapes for a Gaussian starter
# hold distribution N(1.78, 0.158) s (Otsuka et al. 2017 broadcast estimate). Verifies numbers
# quoted in lit/review.md section 5.11 (originally computed by the cognitive-science search pass).
import numpy as np
from scipy import stats
mu, sd = 1.78, 0.158
t = np.linspace(0.8, 3.2, 24001)
f = stats.norm.pdf(t, mu, sd); F = stats.norm.cdf(t, mu, sd)
probe = np.array([1.465, 1.622, 1.780, 1.938, 2.096])
def at(x, y): return np.interp(probe, x, y)
h = f / (1 - F)
print("objective hazard at probes:", np.round(at(t, h), 2))
for c in [0.01, 0.02, 0.05, 0.10]:
    hc = (1 - c) * f / (1 - (1 - c) * F)
    m = (t > 1.3) & (t < 2.8)
    print(f"abort c={c}: hazard peak at {t[m][np.argmax(hc[m])]:.3f} s")
def blur(y, phi):
    # Janssen & Shadlen-style blur: y~(t) = int y(tau) N(tau; t, phi*t) dtau
    out = np.empty_like(t)
    dt = t[1] - t[0]
    for i, ti in enumerate(t[::10]):
        k = stats.norm.pdf(t, ti, phi * ti)
        out[i*10:(i+1)*10] = np.sum(y * k) * dt
    return out
for phi in [0.10, 0.21, 0.26, 0.30]:
    fb = blur(f, phi)
    Fb = np.cumsum(fb) * (t[1] - t[0])
    hb = fb / np.clip(1 - Fb, 1e-9, None)
    m = (t > 1.2) & (t < 2.4)
    tmin = t[m][np.argmax(fb[m])]
    recip = 1 / at(t, fb) * at(t, fb).max()  # normalised reciprocal PDF at probes
    print(f"phi={phi}: blurred-PDF peak {tmin:.3f} s; blurred hazard at probes {np.round(at(t, hb), 2)}; "
          f"normalised 1/PDF at probes {np.round(recip, 2)}")
