"""Checks for analysis/rtdist.py: closed-form densities equal scipy.stats; fits recover truth.

Usage:  .venv\\Scripts\\python.exe analysis\\tests\\test_rtdist.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rtdist  # noqa: E402

PARAMS = {"exgauss": {"mu": 0.135, "sigma": 0.012, "tau": 0.016},
          "slognorm": {"shift": 0.08, "m": np.log(0.065), "s": 0.25},
          "swald": {"shift": 0.08, "a": 0.35, "b": 0.2}}


def test_closed_forms():
    x = np.linspace(0.06, 0.35, 300)
    for fam, p in PARAMS.items():
        d = rtdist.make_dist(fam, p)
        lp_ref, cdf_ref = d.logpdf(x), d.cdf(x)
        ok = np.isfinite(lp_ref)
        assert np.allclose(rtdist.logpdf(fam, p, x)[ok], lp_ref[ok], atol=1e-8), fam
        assert np.allclose(rtdist.cdf(fam, p, x), cdf_ref, atol=1e-10), fam
    print("[ok] closed-form logpdf/cdf match scipy.stats for all families")


def test_recovery():
    rng = np.random.default_rng(5)
    for fam, p in PARAMS.items():
        x = rtdist.make_dist(fam, p).rvs(3000, random_state=rng)
        t = time.time()
        f = rtdist.fit_family(x, fam, 0.100, 0.300)
        el = time.time() - t
        m_true = rtdist.cdf(fam, p, 0.100)
        print(f"[info] {fam}: fit {el * 1000:.0f} ms; P(<0.1) true {m_true:.2e} fit {rtdist.mass_below(f):.2e}")
        assert abs(np.log(rtdist.mass_below(f) + 1e-12) - np.log(m_true + 1e-12)) < 1.5
    print("[ok] truncated fits recover the tail mass within a factor e^1.5")


if __name__ == "__main__":
    test_closed_forms()
    test_recovery()
