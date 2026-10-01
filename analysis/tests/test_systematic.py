"""Tests for analysis/systematic.py (guard every claim a test can hold).

Unit tests (synthetic data, no repo outputs needed):
  1. pooled / championship-centred Pearson r from per-race sums equal direct computation
  2. stratified race resampling keeps every championship's race count
  3. naive Fisher CI and p match scipy; row-wise r and within-group centring are exact
  4. the S1 simulator encodes the mechanism: zero offsets -> naive r ~ 0; offsets aligned with championship
     mean holds -> naive r clearly > 0 while the championship-centred r stays ~ 0
  5. the S2 simulator is centred on zero and symmetric under exchangeable championships
  6. the Haugen-design simulator is centred on zero; its spread grows with the championship SDs
  7. barrier inversion: F(barrier) = 1e-3 for every family
  8. DerSimonian-Laird recovers a known between-study SD and returns 0 for identical estimates
  9. REML between/within SDs recover known values
 10. the pre-registered verdict rules (truth tables)
Claim guards on analysis/outputs/systematic.json (skipped if absent), each proven to fire on a corrupted copy:
  G1 H1 verdict, grade and criteria recomputed from the stored numbers
  G2 (a) reproduces fp_models.slope_ms_per_100ms (estimate and CI)
  G3 H2 verdict and criteria recomputed from the stored numbers
  G4 every stored probability lies in [0, 1]

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_systematic.py   (or pytest)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rtdist  # noqa: E402
import systematic as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"


# ---------------------------------------------------------------------------------------------------
# synthetic design
# ---------------------------------------------------------------------------------------------------

def toy_design(n_champ=4, races=40, per_race=8, seed=0, hold_means=(1.45, 1.55, 1.65, 1.75)):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(n_champ):
        for r in range(races):
            w = hold_means[c] + rng.normal(0, 0.2)
            for k in range(per_race):
                rows.append({"race_id": f"C{c}-R{r}", "comp_year": f"C{c}", "foreperiod_s": w,
                             "athlete_id2": f"C{c}-A{(r * per_race + k) % 60}"})
    d = pd.DataFrame(rows)
    return d, S.design_arrays(d)


def test_sums_and_centring():
    d, D = toy_design()
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, D["N"]) + 0.3 * D["W"] + D["champ_idx"] * 0.5
    x = D["W"]
    assert abs(S.pearson(x, y) - np.corrcoef(x, y)[0, 1]) < 1e-12
    sums = S.race_sums(x, y, D["race_idx"], D["n_race"])
    assert abs(S.r_from_totals(sums.sum(1)) - np.corrcoef(x, y)[0, 1]) < 1e-12
    xc = x - pd.Series(x).groupby(D["champ_idx"]).transform("mean").to_numpy()
    yc = y - pd.Series(y).groupby(D["champ_idx"]).transform("mean").to_numpy()
    Tc = np.stack([sums[:, D["race_champ"] == c].sum(1) for c in range(len(D["comps"]))])
    assert abs(S.r_centred_from_totals(Tc[None])[0] - np.corrcoef(xc, yc)[0, 1]) < 1e-12
    print("[ok] pooled and championship-centred r from race sums equal direct computation")


def test_strat_multiplicities():
    groups = np.repeat([0, 1, 2], [5, 7, 3])
    K = S.strat_multiplicities(groups, 400, np.random.default_rng(2))
    for g, size in ((0, 5), (1, 7), (2, 3)):
        assert np.all(K[:, groups == g].sum(1) == size)
    assert K.min() >= 0 and np.isclose(K.mean(), 1.0, atol=0.05)
    print("[ok] stratified resampling keeps each championship's race count")


def test_naive_stats_rowwise():
    rng = np.random.default_rng(3)
    x, y = rng.normal(size=300), rng.normal(size=300)
    y = y + 0.2 * x
    r = S.pearson(x, y)
    assert abs(S.naive_p(r, 300) - stats.pearsonr(x, y)[1]) < 1e-10
    lo, hi = S.fisher_ci(r, 300)
    assert lo < r < hi and abs(np.arctanh(hi) - np.arctanh(r) - (np.arctanh(r) - np.arctanh(lo))) < 1e-12
    Y = rng.normal(size=(5, 300)) + x
    assert np.allclose(S.rowwise_r(x, Y), [np.corrcoef(x, Y[i])[0, 1] for i in range(5)])
    X2 = rng.normal(size=(5, 300))
    assert np.allclose(S.rowwise_r(X2, Y), [np.corrcoef(X2[i], Y[i])[0, 1] for i in range(5)])
    g = np.repeat(np.arange(3), 100)
    oh = np.eye(3)[g]
    C = S.centre_rows(Y, oh, oh.sum(0))
    assert np.allclose((C @ oh) / oh.sum(0), 0.0)
    print("[ok] naive Fisher CI / p match scipy; row-wise r and centring exact")


def test_sim_observed_mechanism():
    d, D = toy_design()
    vc = {"race": 25.0, "athlete": 240.0, "residual": 225.0}
    rng = np.random.default_rng(4)
    null = S.sim_observed(D, np.zeros(D["N"]), vc, 2000, rng)
    se = null["ready"].std() / np.sqrt(len(null["ready"]))
    assert abs(null["ready"].mean()) < 4 * se + 0.005, null["ready"].mean()
    # championship offsets that increase with the championship mean hold: the mechanism
    eta = np.array([-15.0, -5.0, 5.0, 15.0])[D["champ_idx"]]
    mech = S.sim_observed(D, eta, vc, 2000, rng)
    assert mech["ready"].mean() > 0.10, mech["ready"].mean()
    assert abs(mech["centred"].mean()) < 0.01, mech["centred"].mean()
    # a true within-championship slope raises the centred r too
    slope = S.sim_observed(D, 20.0 * (D["W"] - 1.6), vc, 2000, rng)
    assert slope["centred"].mean() > 0.05
    print(f"[ok] S1 simulator: null r {null['ready'].mean():+.3f}, aligned offsets r {mech['ready'].mean():+.3f} "
          f"(centred {mech['centred'].mean():+.3f})")


def test_sim_exchangeable_null():
    d, D = toy_design()
    vc = {"race": 25.0, "athlete": 240.0, "residual": 225.0}
    r = S.sim_exchangeable(D, np.zeros(D["N"]), 0.0, vc, 9.0, 0.12, 4000, np.random.default_rng(5))
    assert abs(r.mean()) < 0.01, r.mean()
    assert abs((r >= 0.16).mean() - (r <= -0.16).mean()) < 0.02
    print(f"[ok] S2 simulator centred on zero (mean {r.mean():+.4f}, SD {r.std():.3f}) and symmetric")


def test_haugen_layout():
    design = {"n_champs": 5, "heats_per_champ": 11, "starts_per_heat": 7.5, "starts_per_athlete": 3}
    heat_champ, start_heat, start_champ, ath, n_ath = S.haugen_layout(design)
    assert len(heat_champ) == 55 and len(start_heat) == 5 * 83            # 11 x 7.5 -> 83 starts per championship
    sizes = np.bincount(start_heat)
    assert set(sizes) == {7, 8}
    pairs = pd.DataFrame({"h": start_heat, "a": ath})
    assert not pairs.duplicated().any()                                    # nobody starts twice in one heat
    assert (pd.Series(start_champ).groupby(ath).nunique() == 1).all()      # athletes nested in championship
    assert abs(len(ath) / n_ath - 3) < 0.2
    print("[ok] Haugen layout: 83 starts per championship, heats of 7-8, athletes nested, ~3 starts each")


def test_sim_haugen():
    design = {"n_champs": 4, "heats_per_champ": 10, "starts_per_heat": 8, "starts_per_athlete": 1.5,
              "hold_lo_s": 1.3, "hold_hi_s": 2.2, "truncate": "champ_mean"}
    par = {"hold_mean_s": 1.75, "sd_hold_between_s": 0.15, "sd_hold_within_s": 0.15, "sd_champ_ms": 9.0,
           "sd_race_ms": 5.0, "sd_athlete_ms": 15.0, "sd_residual_ms": 15.0}
    rng = np.random.default_rng(6)
    r = S.sim_haugen(design, par, 3000, rng)
    assert abs(r.mean()) < 0.01, r.mean()
    r0 = S.sim_haugen(design, {**par, "sd_champ_ms": 0.0, "sd_hold_between_s": 0.0}, 3000, rng)
    assert r0.std() < r.std(), (r0.std(), r.std())
    rh = S.sim_haugen({**design, "truncate": "heat"}, par, 1000, rng)
    assert abs(rh.mean()) < 0.015
    x = S._truncnorm_rows(1.75, 0.5, (200, 50), 1.3, 2.2, rng)
    assert x.min() >= 1.3 and x.max() <= 2.2
    print(f"[ok] Haugen-design simulator centred on zero; SD {r.std():.3f} with vs {r0.std():.3f} without "
          f"championship structure; truncation respected")


def test_barrier_inversion():
    params = {"exgauss": {"mu": 0.135, "sigma": 0.012, "tau": 0.016},
              "slognorm": {"shift": 0.08, "m": np.log(0.065), "s": 0.25},
              "swald": {"shift": 0.08, "a": 0.35, "b": 0.2}}
    for fam, p in params.items():
        b = S.barrier_ms(fam, p) / 1000.0
        assert abs(rtdist.cdf(fam, p, b) - S.BARRIER_Q) < 1e-7, fam
    print("[ok] F(barrier) = 1e-3 for every family")


def test_dersimonian_laird():
    rng = np.random.default_rng(7)
    k, tau, se = 400, 5.0, 2.0
    est = 100 + rng.normal(0, tau, k) + rng.normal(0, se, k)
    dl = S.dersimonian_laird(est, np.full(k, se))
    assert abs(dl["tau"] - tau) / tau < 0.15, dl
    same = S.dersimonian_laird(np.full(10, 3.0), np.full(10, 1.0))
    assert same["tau"] == 0.0 and same["p"] > 0.99
    print(f"[ok] DerSimonian-Laird tau {dl['tau']:.2f} (true {tau}); identical estimates -> 0")


def test_reml_between_within():
    rng = np.random.default_rng(8)
    g = np.repeat(np.arange(30), 40)
    y = rng.normal(0, 0.2, 30)[g] + rng.normal(0, 0.3, len(g))
    b, w = S.reml_between_within_sd(y, g)
    assert abs(b - 0.2) < 0.07 and abs(w - 0.3) < 0.02, (b, w)
    print(f"[ok] REML between {b:.3f} (0.2), within {w:.3f} (0.3)")


def test_gg_cdf_and_fiore_quadrature():
    rng = np.random.default_rng(9)
    mu, sigma = 0.148, 0.11
    # nu = 1: GG is Gamma(shape 1/sigma^2, scale mu sigma^2)
    th = 1 / sigma ** 2
    ys = np.array([0.10, 0.13, 0.16])
    assert np.allclose(S.gg_cdf(ys, mu, sigma, 1.0), stats.gamma.cdf(ys, a=th, scale=mu / th), atol=1e-12)
    # nu < 0 (Fiore et al.'s men): Y = mu * Z^(1/nu), Z ~ Gamma(theta, rate theta)
    nu = -1.178
    th = 1 / (sigma ** 2 * nu ** 2)
    y = mu * rng.gamma(th, 1 / th, 400000) ** (1 / nu)
    for q in (0.11, 0.14, 0.17):
        assert abs(S.gg_cdf(q, mu, sigma, nu) - (y < q).mean()) < 0.004, q
    # quadrature marginal over venue and heat = their simfit Monte Carlo
    p = {"beta0": -1.910, "gamma0": -2.200, "nu": -1.178, "tau_v": 0.058, "tau_h": 0.320}
    m = np.exp(p["beta0"] + rng.normal(0, p["tau_v"], 1000000))
    s = np.exp(p["gamma0"] + rng.normal(0, p["tau_h"], 1000000))
    th = 1 / (s ** 2 * p["nu"] ** 2)
    ysim = m * rng.gamma(th, 1 / th) ** (1 / p["nu"])
    mc = (ysim < 0.100).mean()
    assert abs(S.fiore_p(0.100, p) - mc) / mc < 0.08, (S.fiore_p(0.100, p), mc)
    b = S.fiore_barrier_ms(1e-3, p) / 1000
    assert abs(S.fiore_p(b, p) - 1e-3) < 1e-9
    print(f"[ok] GG CDF (nu = 1 exact; nu < 0 vs simulation); quadrature P(<0.100) {S.fiore_p(0.100, p):.3e} vs "
          f"simulation {mc:.3e}; barrier inversion exact")


def test_venue_pdf_parser():
    pdf = ROOT / "analysis" / "external" / "fiore2025" / "ComparisonOfVenueEffects.pdf"
    if not pdf.exists():
        print("[skip] Fiore venue figure not stored")
        return
    ve = S.parse_venue_pdf(pdf)
    assert list(ve["top"]) == [1999, 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017, 2019, 2022, 2023]
    assert 2022 not in ve["bottom"] and len(ve["bottom"]) == 12              # 2022 was plotted off-scale there
    assert abs(ve["top"][2022] + 0.131) < 0.002 and abs(ve["top"][2011] - 0.097) < 0.002   # independent digitisation
    assert all(c["max_tick_residual"] < 1e-9 for c in ve["calibration"].values())
    print(f"[ok] venue figure: 13 + 12 points, 2022 {ve['top'][2022]:+.4f}, 2011 {ve['top'][2011]:+.4f}, exact axis")


def test_fiore_params_match_source():
    """Every transcribed parameter and published value appears verbatim in the manuscript extract."""
    src = ROOT / "analysis" / "external" / "fiore2025" / "source_extract.txt"
    if not src.exists():
        print("[skip] Fiore manuscript extract not present (run scripts/fetch_third_party.py)")
        return
    ext = src.read_text(encoding="utf-8")
    pp = pd.read_csv(ROOT / "analysis" / "fiore2025_params.csv")
    rowkey = {"men_incl2022": "Including 2022 &", "men_excl2022": "Excluding 2022 &", "women": "Women's &"}
    for _, r in pp.iterrows():
        lines = [l for l in ext.splitlines() if rowkey[r["set"]] in l]
        blob = " ".join(lines)
        for k in ("beta0", "gamma0", "nu", "tau_v", "tau_h"):
            assert f"{abs(r[k]):.3f}" in blob, (r["set"], k)
        for k in ("pub_barrier_1e2_s", "pub_barrier_1e3_s", "pub_barrier_1e4_s"):
            assert f"${r[k]:.3f}$" in blob, (r["set"], k)
        for k in ("pub_p_lt090", "pub_p_lt100"):
            mant, ex = f"{r[k]:.2e}".split("e")
            assert f"{mant}\\cdot10^{{{int(ex)}}}" in blob, (r["set"], k, mant, ex)
    print("[ok] fiore2025_params.csv matches the manuscript source extract line by line")


def test_h3_enumeration():
    pools = S.era_sets(S.ERA_POOLS["zt"])
    vals = {c: float(i) for i, c in enumerate(pools["pre2003"] + pools["2003_2009"] + pools["zt"])}
    sub, ks, picks = S.haugen_subsets(vals, pools, S.HAUGEN_K)
    assert ks == {"pre2003": 2, "2003_2009": 4, "zt": 2} and len(sub["c2"]) == 45 == len(set(picks))
    zt_mean_pairs = np.array([np.mean([vals[x] for x in p.split("+")]) for p in picks])
    assert np.allclose(sub["c2"], zt_mean_pairs - np.mean([vals[c] for c in pools["2003_2009"]]))
    null = S.same_rule_null(vals, pools["zt"], 2, 5)
    assert len(null) == 45 * 56
    se = {c: 0.0 for c in vals}
    tau, sd = S.within_era_tau(vals, se, pools)
    assert abs(tau - sd) < 1e-12 and tau > 0
    print("[ok] H3 enumeration: 45 Haugen-matched designs, 2,520 same-rule splits, tau estimator")


def test_sex_gap_recovery():
    rng = np.random.default_rng(11)
    gaps = {"A": 0.0, "B": 6.0, "C": 12.0, "D": -6.0}
    rows = []
    for c, gp in gaps.items():
        for r in range(30):
            for sex in ("M", "W"):
                u = rng.normal(0, 4)
                for k in range(8):
                    rows.append({"comp_year": c, "race_id": f"{c}{r}{sex}", "sex": sex, "athlete_id2": f"{c}{sex}{r}{k}",
                                 "rt_ms": 150 + (gp if sex == "W" else 0) + u + rng.normal(0, 15)})
    d = pd.DataFrame(rows)
    tab, (stat, df_, p), mean_gap = S.sex_gap_by_championship(d, "C(sex, Treatment('M'))")
    est = dict(zip(tab["comp_year"], tab["gap_ms"]))
    assert df_ == 3 and p < 0.01
    assert all(abs(est[c] - g_) < 4.0 for c, g_ in gaps.items()), est
    assert abs(mean_gap[0] - np.mean(list(gaps.values()))) < 2.5
    print(f"[ok] sex x championship gaps recovered ({', '.join(f'{c} {est[c]:+.1f}' for c in gaps)}); LRT p {p:.1e}")


def test_verdict_rules():
    none = {"R1": False, "R2": False, "Q1": False, "Q2": False, "Q3": None}
    assert S.h1_verdict(True, none) == ("NOT REPRODUCED", "")
    assert S.h1_verdict(False, {**none, "R2": True}) == ("NOT REPRODUCED", "")
    assert S.h1_verdict(True, {**none, "R2": True}) == ("SUPPORTS the mechanism", "observed structure")
    assert S.h1_verdict(True, {**none, "Q1": True}) == ("SUPPORTS the mechanism", "observed structure")
    assert S.h1_verdict(True, {**none, "Q2": True}) == ("SUPPORTS the mechanism", "simulation only")
    assert S.h1_verdict(True, {**none, "Q3": True}) == ("SUPPORTS the mechanism", "simulation only")
    assert S.h2_verdict(False, False) == "NOT CONSEQUENTIAL"
    assert S.h2_verdict(True, False) == S.h2_verdict(False, True) == "CONSEQUENTIAL"
    print("[ok] pre-registered verdict rules")


# ---------------------------------------------------------------------------------------------------
# claim guards on the stored result
# ---------------------------------------------------------------------------------------------------

def check_h1(sysj: dict) -> list:
    n = sysj["numbers"]
    bad = []
    lo, hi = n["h1a_slope_ms_per_100ms"]["ci95"]
    h = n["h1a_haugen_slope_ms_per_100ms"]["value"]
    W = bool(hi < h and lo > -h)
    if W != n["h1a_ci_excludes_haugen"]["value"]:
        bad.append("h1a_ci_excludes_haugen disagrees with the stored CI and Haugen-sized slope")
    crit = {"R1": n["h1b_r_equivalent"]["ci95"][1] >= S.HAUGEN_R,
            "R2": n["h1c_r_pooled"]["ci95"][1] >= S.HAUGEN_R,
            "Q1": n["h1s1_ready_beta0_p_ge016"]["value"] >= S.P_NONTRIVIAL,
            "Q2": n["h1s2_beta0_p_ge016"]["value"] >= S.P_NONTRIVIAL, "Q3": None}
    prim = [k for k in n if k.startswith("h1s3_") and k.endswith("_p_absge016") and n[k].get("primary")]
    if prim:
        crit["Q3"] = any(n[k]["value"] >= S.P_NONTRIVIAL for k in prim)
    if crit["R1"] != n["h1b_reaches_haugen"]["value"] or crit["R2"] != n["h1c_reaches_haugen"]["value"]:
        bad.append("R1/R2 flags disagree with the stored intervals")
    if (n["h1c_r_centred"]["ci95"][1] < S.HAUGEN_R) != n["h1c_centred_below_haugen"]["value"]:
        bad.append("h1c_centred_below_haugen disagrees with the stored interval")
    verdict, grade = S.h1_verdict(W, crit)
    v = n["h1_verdict"]
    if v["value"] != verdict or v.get("grade") != grade:
        bad.append(f"H1 verdict {v['value']}/{v.get('grade')} but the stored numbers imply {verdict}/{grade}")
    for k in ("R1", "R2", "Q1", "Q2", "Q3"):
        if v.get(k) != crit[k]:
            bad.append(f"H1 criterion {k} stored {v.get(k)} vs recomputed {crit[k]}")
    return bad


def check_reproduces_fp(sysj: dict, fpj: dict) -> list:
    a, f = sysj["numbers"]["h1a_slope_ms_per_100ms"], fpj["numbers"]["slope_ms_per_100ms"]
    return [] if (a["value"] == f["value"] and a["ci95"] == f["ci95"]) else \
        [f"(a) {a['value']} {a['ci95']} does not reproduce fp_models {f['value']} {f['ci95']}"]


def check_h2(sysj: dict) -> list:
    n = sysj["numbers"]
    s, f = S.PRIMARY_SEX, S.PRIMARY_FAMILY
    rng_ = n[f"h2_champ_barrier_range_ms_{f}_{s}"]["value"]
    pi = n[f"h2_champ_barrier_pi_width_ms_{s}"]["value"]
    shift = n[f"h2_shift_ms_{f}_{s}"]["value"]
    c1 = bool(rng_ >= S.MATERIAL_MS and pi >= S.MATERIAL_MS)
    c2 = bool(abs(shift) >= S.MATERIAL_MS)
    v = n["h2_verdict"]
    bad = []
    if v["value"] != S.h2_verdict(c1, c2):
        bad.append(f"H2 verdict {v['value']} but the stored numbers imply {S.h2_verdict(c1, c2)}")
    if v.get("C1") != c1 or v.get("C2") != c2:
        bad.append(f"H2 criteria stored C1={v.get('C1')} C2={v.get('C2')} vs recomputed {c1} {c2}")
    return bad


def check_probabilities(sysj: dict) -> list:
    bad = []
    for k, e in sysj["numbers"].items():
        if "_p_lt100_" in k or k.endswith(("_p_ge016", "_p_absge016", "_p_ge016_sig")):
            vals = [e["value"]] + list(e.get("ci95") or [])
            if any(not (0.0 <= float(x) <= 1.0) for x in vals):
                bad.append(f"{k}: probability outside [0, 1]: {vals}")
    return bad


def check_audit(sysj: dict) -> list:
    """H3/H4/H5/O2 verdicts recomputed from the stored numbers (addendum 3 rules)."""
    n, bad = sysj["numbers"], []
    if "h3_verdict_sign" not in n:
        return bad
    flip = n["h3_c2_subsets_p_opposite"]["value"] >= S.P_FLIP or n["h3_c2_haugen_p_opposite"]["value"] >= S.P_FLIP
    if n["h3_verdict_sign"]["value"] != ("SAMPLING CAN FLIP THE SIGN" if flip else "SIGN STABLE UNDER SAMPLING"):
        bad.append("H3 sign verdict disagrees with the stored shares")
    for key, eff, hw in (("h3_verdict_haugen", S.PUB_HAUGEN_MS, n["h3_samerule_halfwidth_ms"]["value"]),
                         ("h3_verdict_han", S.PUB_HAN_MS, n["h3_han_samerule_halfwidth_ms"]["value"])):
        want = "WITHIN SAME-RULE NOISE" if abs(eff) <= hw else "EXCEEDS SAME-RULE NOISE"
        if n[key]["value"] != want:
            bad.append(f"{key} {n[key]['value']} but the stored half-width implies {want}")
    p = n["h4_lrt_chi2"]["p"]
    lo, hi = n["h4_gap_pi_ms"]["ci95"]
    want = ("NO EVIDENCE OF VARIATION" if p >= 0.05 else
            "CHAMPIONSHIP-DEPENDENT (sign not stable)" if lo <= 0 <= hi else "VARIES IN SIZE, NOT SIGN")
    if n["h4_verdict"]["value"] != want:
        bad.append(f"H4 verdict {n['h4_verdict']['value']} but the stored LRT/PI imply {want}")
    if "h5_verdict_reproduced" in n:
        t = pd.DataFrame(sysj["tables"]["h5_fiore"])
        ok = all(abs(r["p_lt100"] - r["pub_p_lt100"]) / r["pub_p_lt100"] <= 0.05 and
                 all(abs(r[f"barrier_{x}_ms"] - r[f"pub_barrier_{x}_ms"]) <= 1.0 for x in ("1e2", "1e3", "1e4"))
                 for _, r in t.iterrows())
        if n["h5_verdict_reproduced"]["value"] != ("REPRODUCED" if ok else "NOT REPRODUCED"):
            bad.append("H5 reproduction verdict disagrees with the stored table")
        x = n["h5_men_incl2022_venue_range95_ms"]["value"]
        want = "VENUE MATERIAL WITHIN FIORE ET AL.'S MODEL" if x >= S.MATERIAL_MS else "NOT MATERIAL"
        if n["h5_verdict_venue"]["value"] != want:
            bad.append("H5 venue verdict disagrees with the stored range")
    if "o2_verdict" in n:
        conf = [abs(n[f"o2_diff_{s}"]["value"]) >= 0.10 and (n[f"o2_diff_{s}"]["ci95"][0] > 0 or n[f"o2_diff_{s}"]["ci95"][1] < 0)
                for s in ("M", "W")]
        want = "CHAMPIONSHIP-CONFOUNDED" if any(conf) else "NOT CONFOUNDED BY CHAMPIONSHIP"
        if n["o2_verdict"]["value"] != want:
            bad.append("O2 verdict disagrees with the stored differences")
    return bad


def run_guards() -> bool:
    p = OUT / "systematic.json"
    if not p.exists():
        print("[skip] analysis/outputs/systematic.json not built")
        return True
    sysj = json.loads(p.read_text(encoding="utf-8"))
    fpj = json.loads((OUT / "fp_models.json").read_text(encoding="utf-8"))
    failures = (check_h1(sysj) + check_reproduces_fp(sysj, fpj) + check_h2(sysj) + check_probabilities(sysj)
                + check_audit(sysj))
    fired = []
    if "h3_verdict_sign" in sysj["numbers"]:
        for key, alt in (("h3_verdict_sign", "SIGN STABLE UNDER SAMPLING"), ("h3_verdict_haugen", "WITHIN SAME-RULE NOISE"),
                         ("h4_verdict", "NO EVIDENCE OF VARIATION"), ("h5_verdict_reproduced", "REPRODUCED"),
                         ("h5_verdict_venue", "NOT MATERIAL"), ("o2_verdict", "CHAMPIONSHIP-CONFOUNDED")):
            if key not in sysj["numbers"]:
                continue
            c = copy.deepcopy(sysj)
            cur = c["numbers"][key]["value"]
            c["numbers"][key]["value"] = alt if cur != alt else cur + " (tampered)"
            fired.append(bool(check_audit(c)))
    c = copy.deepcopy(sysj)
    c["numbers"]["h1_verdict"]["value"] = ("NOT REPRODUCED" if c["numbers"]["h1_verdict"]["value"].startswith("SUPPORTS")
                                           else "SUPPORTS the mechanism")
    fired.append(bool(check_h1(c)))
    c = copy.deepcopy(sysj)
    c["numbers"]["h1a_slope_ms_per_100ms"]["value"] += 0.5
    fired.append(bool(check_reproduces_fp(c, fpj)))
    c = copy.deepcopy(sysj)
    c["numbers"]["h2_verdict"]["value"] = ("NOT CONSEQUENTIAL" if c["numbers"]["h2_verdict"]["value"] == "CONSEQUENTIAL"
                                           else "CONSEQUENTIAL")
    fired.append(bool(check_h2(c)))
    c = copy.deepcopy(sysj)
    c["numbers"]["h1s1_ready_beta0_p_ge016"]["value"] = 1.5
    fired.append(bool(check_probabilities(c)))
    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(fired)}/{len(fired)}")
    ok = not failures and all(fired)
    if ok:
        print("[ok] systematic.json: verdicts, criteria and the (a) reproduction agree with the stored numbers")
    return ok


def test_guards():
    assert run_guards()


if __name__ == "__main__":
    for fn in (test_sums_and_centring, test_strat_multiplicities, test_naive_stats_rowwise, test_sim_observed_mechanism,
               test_sim_exchangeable_null, test_haugen_layout, test_sim_haugen, test_barrier_inversion, test_dersimonian_laird,
               test_reml_between_within, test_gg_cdf_and_fiore_quadrature, test_venue_pdf_parser,
               test_fiore_params_match_source, test_h3_enumeration, test_sex_gap_recovery, test_verdict_rules):
        fn()
    if not run_guards():
        sys.exit(1)
