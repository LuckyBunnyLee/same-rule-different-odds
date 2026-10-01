"""EXPLORATORY: absolute delay check. Same athletes' adjusted RT at each WCH2025 straight line minus their 200 m RT,
against the mean airborne travel time predicted by the fitted source (x_s = 4.2 m ahead of the 100 m line, inner edge)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "analysis"))
import recent_probe as P
v, *_ = P.load_valid(); P.fit_global(v)
w = v[v["named"] & (v["comp_year"] == "WCH2025")].copy()
w["date"] = w["date"].astype(str)
w["line"] = np.select([w["event"].isin(["100m", "100mH"]), w["event"] == "110mH", w["event"] == "200m"], ["A", "B", "200m"], "other")
c = 331.3 + 0.606 * 28.5
for line, xline in (("A", 0.0), ("B", -10.0)):
    d = w[w["line"] == line]
    # same athletes with a 200 m run at WCH2025
    both = set(d["athlete_id2"]) & set(w.loc[w["line"] == "200m", "athlete_id2"])
    a = d[d["athlete_id2"].isin(both)].groupby("athlete_id2")["rd"].mean()
    b = w[(w["line"] == "200m") & w["athlete_id2"].isin(both)].groupby("athlete_id2")["rd"].mean()
    diff = (a - b).dropna()
    rng = np.random.default_rng(1); bs = [diff.sample(len(diff), replace=True, random_state=int(rng.integers(1e9))).mean() for _ in range(2000)]
    lanes = d["lane"].dropna().astype(int)
    tau = 1000 * np.hypot(xline - 4.2, (lanes - 0.5) * 1.22 - 0.0) / c
    print(f"line {line}: same-athlete minus 200 m = {diff.mean():.1f} ms [{np.percentile(bs,2.5):.1f}, {np.percentile(bs,97.5):.1f}] (n = {len(diff)}); "
          f"fixed-source predicted mean airborne delay = {tau.mean():.1f} ms")
    if line == "B":
        tau_mv = 1000 * np.hypot(4.2, (lanes - 0.5) * 1.22) / c     # starter re-positioned 4.2 m ahead of the 110 mH line
        print(f"         if the source moved with the start line: predicted {tau_mv.mean():.1f} ms, slope ~ same as line A")
