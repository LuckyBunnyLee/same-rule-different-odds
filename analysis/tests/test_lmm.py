"""Checks for the crossed-random-effects REML engine (analysis/lmm.py).

1. Single random factor: estimates must match statsmodels MixedLM (REML).
2. Crossed race + athlete + competition factors on MOCK data: recovery of the known truth.

Usage:  .venv\\Scripts\\python.exe analysis\\tests\\test_lmm.py
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import MOCK_DATA, load_rt, valid_rt_mask  # noqa: E402
from lmm import fit_formula  # noqa: E402


def test_vs_statsmodels():
    import statsmodels.formula.api as smf
    rng = np.random.default_rng(3)
    n_g, m = 120, 8
    g = np.repeat(np.arange(n_g), m)
    x = rng.standard_normal(n_g * m)
    z = rng.integers(0, 3, n_g * m)
    y = 1.0 + 0.3 * x + 0.2 * (z == 1) + rng.normal(0, 0.5, n_g)[g] + rng.normal(0, 1.0, n_g * m)
    d = pd.DataFrame({"y": y, "x": x, "z": z, "g": g})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sm = smf.mixedlm("y ~ x + C(z)", d, groups="g").fit(reml=True)
    mine = fit_formula("x + C(z)", d, "y", ["g"], method="REML")
    b_sm = sm.fe_params.to_numpy()
    se_sm = sm.bse_fe.to_numpy()
    assert np.allclose(mine.beta, b_sm, atol=1e-4), (mine.beta, b_sm)
    assert np.allclose(mine.se, se_sm, rtol=2e-3), (mine.se, se_sm)
    assert abs(mine.sigma2 - sm.scale) / sm.scale < 1e-3
    assert abs(mine.var_comp["g"] - float(sm.cov_re.iloc[0, 0])) / float(sm.cov_re.iloc[0, 0]) < 5e-3
    print(f"[ok] matches statsmodels: beta_x {mine.beta[mine.names.index('x')]:.5f} vs "
          f"{sm.fe_params['x']:.5f}; var_g {mine.var_comp['g']:.4f} vs {float(sm.cov_re.iloc[0, 0]):.4f}")


def test_mock_recovery():
    truth = json.loads((MOCK_DATA / "MOCK_truth.json").read_text())
    rt, _ = load_rt(True, "athletes")
    d = rt[valid_rt_mask(rt)].copy()
    d["rt_ms"] = d["rt_s"] * 1000
    t = time.time()
    f = fit_formula("C(sex) + C(round, Treatment('R1')) + C(event)", d, "rt_ms",
                    ["comp_year", "race_id", "athlete_key"], method="REML")
    el = time.time() - t
    sd = {k: np.sqrt(v) for k, v in f.var_comp.items()}
    print(f"[info] crossed fit n={f.n}, q={sum(len(v) for v in f.levels.values())}, {el:.1f}s")
    print("       SDs (ms):", {k: round(v, 2) for k, v in sd.items()}, "resid", round(np.sqrt(f.sigma2), 2))
    print("       truth  : comp", truth["sd_comp_s"] * 1000, "race", truth["sd_race_s"] * 1000,
          "(+FP effect)", "athlete", truth["sd_athlete_s"] * 1000,
          "resid ~", round(np.hypot(truth["resid_sigma_s"], truth["resid_tau_s"]) * 1000, 2))
    w = f.coef("C(sex)[T.W]")
    print(f"       sex W-M: {w[0]:.2f} ms (95% CI {w[1]:.2f}, {w[2]:.2f}); truth {truth['sex_W_s'] * 1000}")
    assert w[1] < truth["sex_W_s"] * 1000 < w[2] + 1.0
    assert 6 < sd["athlete_key"] < 14, sd
    print("[ok] mock recovery within tolerance")


def test_duplicate_index_and_na():
    """Bootstrap samples carry duplicate index labels and covariates can be missing: the fit must
    use exactly the rows with complete data, once each."""
    rng = np.random.default_rng(9)
    n_g, m = 60, 6
    d = pd.DataFrame({"g": np.repeat(np.arange(n_g), m), "x": rng.standard_normal(n_g * m),
                      "z": rng.integers(0, 3, n_g * m).astype(float)})
    d["y"] = 0.5 * d["x"] + rng.normal(0, 0.5, n_g)[d["g"]] + rng.standard_normal(len(d))
    d.loc[d.index[:7], "z"] = np.nan                      # 7 rows with a missing covariate
    dup = pd.concat([d, d.iloc[:30]])                     # 30 duplicated index labels
    f = fit_formula("x + C(z)", dup, "y", ["g"], method="REML")
    assert f.n == len(dup) - 7 - 7, (f.n, len(dup))       # the first 30 rows include the 7 NA rows twice
    print(f"[ok] duplicate labels + NA: n used = {f.n} of {len(dup)} rows")


if __name__ == "__main__":
    test_vs_statsmodels()
    test_duplicate_index_and_na()
    test_mock_recovery()
