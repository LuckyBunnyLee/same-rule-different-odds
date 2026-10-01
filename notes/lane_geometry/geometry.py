"""EXPLORATORY (already-seen data): can one point sound source explain the WCH2025 home-straight lane gradients at both
start lines (100 m / 100 mH line at x = 0; 110 mH line 10 m behind, x = -10)? Scratch analysis, not a registered test."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import least_squares
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "analysis"))
import recent_probe as P

LANE_W = 1.22
v, rt, races, _ = P.load_valid()
P.fit_global(v)
w = v[v["named"] & v["lane"].notna() & (v["comp_year"] == "WCH2025") & (v["loc"] == "straight")].copy()
w["lane"] = w["lane"].astype(int)
w["date"] = w["date"].astype(str)
days14 = {"2025-09-13", "2025-09-14", "2025-09-15", "2025-09-16"}
print("dates:", w.groupby("date")["event"].agg(lambda s: sorted(set(s))).to_dict())
w = w[w["date"].isin(days14)]
w["x_line"] = np.where(w["event"] == "110mH", -10.0, 0.0)
T = float(w["temperature_c"].dropna().mean()) if w["temperature_c"].notna().any() else 27.0
c = 331.3 + 0.606 * T
print(f"n starts = {len(w)}, races = {w.race_id.nunique()}, by event: {w.event.value_counts().to_dict()}; T = {T:.1f} C, c = {c:.1f} m/s")

w["yc"] = w["adj"] - w.groupby("race_id")["adj"].transform("mean")
y_lane = (w["lane"].to_numpy() - 0.5) * LANE_W
xl = w["x_line"].to_numpy(); race = w["race_id"].to_numpy(); yc = w["yc"].to_numpy()
codes, inv = np.unique(race, return_inverse=True)

def pred(theta, alpha_free=True):
    xs, ys = theta[0], theta[1]
    a = theta[2] if alpha_free else 1.0
    tau = 1000.0 * np.hypot(xl - xs, y_lane - ys) / c
    tau_c = tau - (np.bincount(inv, tau) / np.bincount(inv))[inv]          # centre within race, like the data
    return a * tau_c

def fit(alpha_free, starts):
    best = None
    for x0 in starts:
        r = least_squares(lambda th: pred(th, alpha_free) - yc, x0, bounds=([-60, -40, 0.0][:len(x0)], [60, -0.01, 3.0][:len(x0)]))
        if best is None or r.cost < best.cost:
            best = r
    return best

grid = [[xs, ys, 1.0] for xs in (-20, -8, -4, 0, 4, 8, 20) for ys in (-1, -4, -10, -25)]
fa = fit(True, grid)
f1 = fit(False, [g[:2] for g in grid])
# per-line free linear slopes (2 params) for comparison
def slopes_sse():
    X = np.zeros((len(w), 2))
    Lc = w["lane"] - w.groupby("race_id")["lane"].transform("mean")
    X[:, 0] = np.where(xl == 0, Lc, 0); X[:, 1] = np.where(xl != 0, Lc, 0)
    b, *_ = np.linalg.lstsq(X, yc, rcond=None)
    return b, float(np.sum((X @ b - yc) ** 2))
b_lin, sse_lin = slopes_sse()
sse0 = float(np.sum(yc ** 2))
print(f"SSE: no lane effect {sse0:.0f}; per-line linear slopes {sse_lin:.0f} (A {b_lin[0]:.2f}, B {b_lin[1]:.2f} ms/lane)")
print(f"point source, alpha free: x_s = {fa.x[0]:.1f} m, y_s = {fa.x[1]:.1f} m, alpha = {fa.x[2]:.2f}; SSE {2*fa.cost:.0f}")
print(f"point source, alpha = 1 (pure airborne delay): x_s = {f1.x[0]:.1f} m, y_s = {f1.x[1]:.1f} m; SSE {2*f1.cost:.0f}")

# implied per-line slopes of the fitted source, and observed lane means
for name, th, af in (("alpha free", fa.x, True), ("alpha=1", f1.x, False)):
    p = pred(th, af)
    for L, lab in ((0.0, "A 100m/100mH"), (-10.0, "B 110mH")):
        m = xl == L
        Lc = (w["lane"] - w.groupby("race_id")["lane"].transform("mean")).to_numpy()[m]
        print(f"  {name:10s} line {lab:12s}: implied slope {np.sum(Lc*p[m])/np.sum(Lc*Lc):.2f} ms/lane")
obs = w.groupby(["x_line", "lane"])["yc"].agg(["mean", "size"]).round(1)
print(obs.unstack(0).to_string())

# race-cluster bootstrap of the alpha-free source position
rng = np.random.default_rng(20261001); B = 300; boots = []
groups = [np.where(inv == k)[0] for k in range(len(codes))]
for _ in range(B):
    idx = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
    xl_b, yl_b, yc_b = xl[idx], y_lane[idx], yc[idx]
    _, inv_b = np.unique(np.concatenate([[f"{k}_{j}"] * len(groups[k]) for j, k in enumerate(rng.integers(0, 1, 0))]) if False else race[idx], return_inverse=True)
    def pb(th):
        tau = 1000.0 * np.hypot(xl_b - th[0], yl_b - th[1]) / c
        return th[2] * (tau - (np.bincount(inv_b, tau) / np.bincount(inv_b))[inv_b])
    r = least_squares(lambda th: pb(th) - yc_b, fa.x, bounds=([-60, -40, 0.0], [60, -0.01, 3.0]))
    boots.append(r.x)
boots = np.array(boots)
q = lambda a: [round(float(np.percentile(a, 2.5)), 1), round(float(np.percentile(a, 97.5)), 1)]
print(f"bootstrap 95%: x_s {q(boots[:,0])}, y_s {q(boots[:,1])}, alpha {q(boots[:,2])}")
