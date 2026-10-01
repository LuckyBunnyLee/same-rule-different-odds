"""Tests for analysis/trend.py (guard every claim a test can hold).

Unit tests (synthetic data, no repo outputs needed):
  1. r_of_beta: Pearson r from the stored centred sums equals direct computation, within-centred and pooled
  2. beta_for_rw gives the target population within-championship correlation
  3. r_crit: the naive test at r_crit has p = alpha exactly
  4. S4 simulator: within-analysis sums do not depend on the championship offsets (same seed, offsets on/off);
     the within r is centred on 0 at beta = 0 and on ~r_w at beta(r_w)
  5. S4 simulator vs S3's sim_haugen (same design and parameters, independent streams): the pooled r of one cell
     has the same distribution (P(r >= 0.16) and SD)
  6. per-cell probability rule: simulated share at >= 200 hits, normal approximation below
  7. inversion: linear interpolation, first grid point, never reached
  8. H6 helpers: F-ratio CI, dispersion-trend slope, permutation p, bootstrap SDs, near-threshold counting
  9. the pre-registered verdict rules (truth tables)
Claim guards on analysis/outputs/trend.json (skipped if absent), each proven to fire on a corrupted copy:
  G1 S4 primary verdict, its alternative readings and the per-design verdicts recomputed from stored numbers
  G2 likelihood ratios = stored pooled / within; LR and inversion verdicts; r_star recomputed from the stored curve
  G3 H6 verdict and sensitivity classifications recomputed from the stored CIs
  G4 every stored S4 probability lies in [0, 1]; monotonicity flags hold
  G5 inputs match their sources: r_w settings = calibration.json; S4 SDs = systematic.json S3 inputs; fastest /
     slowest offsets = descriptive.json; near-threshold count = descriptive.json; top rate = fairness.json
  G6 the S4 pooled cell reproduces S3's registered cell5 probability within Monte Carlo error

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_trend.py   (or pytest)
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
import systematic as S  # noqa: E402
import trend as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"
PAR = {"sd_b": 0.2313, "sd_w": 0.1972, "sd_champ": 9.276, "sd_race": 5.116, "sd_ath": 15.574, "sd_res": 14.969}


# ---------------------------------------------------------------------------------------------------
# unit tests
# ---------------------------------------------------------------------------------------------------

def test_r_of_beta_exact():
    rng = np.random.default_rng(1)
    g = np.repeat(np.arange(5), 80)
    x = rng.normal(0, 0.2, 5)[g] + rng.normal(0, 0.2, len(g))
    z = rng.normal(0, 9, 5)[g] + rng.normal(0, 20, len(g))
    xc = x - pd.Series(x).groupby(g).transform("mean").to_numpy()
    zc = z - pd.Series(z).groupby(g).transform("mean").to_numpy()
    ssw = np.array([xc @ xc, xc @ zc, zc @ zc])
    xp, zp = x - x.mean(), z - z.mean()
    ssp = np.array([xp @ xp, xp @ zp, zp @ zp])
    for beta in (-40.0, 0.0, 7.5, 80.0):
        assert abs(T.r_of_beta(ssw, beta) - np.corrcoef(xc, zc + beta * xc)[0, 1]) < 1e-12
        assert abs(T.r_of_beta(ssp, beta) - np.corrcoef(x, z + beta * x)[0, 1]) < 1e-12
    print("[ok] r_of_beta equals direct Pearson r (within-centred and pooled)")


def test_beta_for_rw():
    rng = np.random.default_rng(2)
    sd_noise = np.sqrt(PAR["sd_race"] ** 2 + PAR["sd_ath"] ** 2 + PAR["sd_res"] ** 2)
    n_heat, m = 40000, 7
    h = rng.normal(0, PAR["sd_w"], n_heat)
    u = rng.normal(0, PAR["sd_race"], n_heat)
    x = np.repeat(h, m)
    z = np.repeat(u, m) + rng.normal(0, PAR["sd_ath"], len(x)) + rng.normal(0, PAR["sd_res"], len(x))
    for rw in (0.04, 0.114, 0.3):
        b = T.beta_for_rw(rw, sd_noise, PAR["sd_w"])
        r = np.corrcoef(x, b * x + z)[0, 1]
        assert abs(r - rw) < 0.01, (rw, r)
    print("[ok] beta_for_rw reproduces the target within-championship correlation")


def test_r_crit():
    for n in (272, 415, 588):
        for a in (0.001, 0.05):
            rc = T.r_crit(a, n)
            assert abs(S.naive_p(rc, n) - a) < 1e-10, (n, a)
    print("[ok] r_crit: naive p at r_crit equals alpha")


def test_s4_within_ignores_championship_offsets():
    dsg = T.s4_design(4, 9)
    a = T.simulate_s4(dsg, PAR, 300, np.random.default_rng(3), chunk=100)
    b = T.simulate_s4(dsg, {**PAR, "sd_champ": 40.0}, 300, np.random.default_rng(3), chunk=100)
    assert np.allclose(a["within"], b["within"]) and not np.allclose(a["pooled"], b["pooled"])
    sd_noise = np.sqrt(PAR["sd_race"] ** 2 + PAR["sd_ath"] ** 2 + PAR["sd_res"] ** 2)
    big = T.simulate_s4(T.s4_design(6, 13), PAR, 2000, np.random.default_rng(4))
    r0 = T.r_of_beta(big["within"], 0.0)
    r1 = T.r_of_beta(big["within"], T.beta_for_rw(0.2, sd_noise, PAR["sd_w"]))
    se = r0.std() / np.sqrt(r0.size)
    assert abs(r0.mean()) < 5 * se, r0.mean()
    assert 0.18 < r1.mean() < 0.2, r1.mean()        # finite-heat centring attenuates slightly below 0.2
    print(f"[ok] S4 within sums unaffected by championship offsets; within r at beta 0: {r0.mean():+.4f}, "
          f"at r_w 0.2: {r1.mean():.4f}")


def test_s4_matches_s3():
    dsg = {**T.s4_design(*T.CELL5)}
    par3 = {"hold_mean_s": T.HOLD_MEAN, "sd_hold_between_s": PAR["sd_b"], "sd_hold_within_s": PAR["sd_w"],
            "sd_champ_ms": PAR["sd_champ"], "sd_race_ms": PAR["sd_race"], "sd_athlete_ms": PAR["sd_ath"],
            "sd_residual_ms": PAR["sd_res"]}
    n = 6000
    r3 = S.sim_haugen(dsg, par3, n, np.random.default_rng(5))
    sim = T.simulate_s4(dsg, PAR, n, np.random.default_rng(6))
    r4 = T.r_of_beta(sim["pooled"], 0.0)[:, T.CELLS.index(("M", 0))]
    p3, p4 = (r3 >= 0.16).mean(), (r4 >= 0.16).mean()
    se = np.sqrt(p3 * (1 - p3) / n + p4 * (1 - p4) / n)
    assert abs(p3 - p4) < 4 * se, (p3, p4)
    assert abs(r4.std() / r3.std() - 1) < 0.06, (r3.std(), r4.std())
    # the two sexes of one era share championships: their pooled r correlate; different eras do not
    rp = T.r_of_beta(sim["pooled"], 0.0)
    c_same = np.corrcoef(rp[:, 0], rp[:, 1])[0, 1]
    c_diff = np.corrcoef(rp[:, 0], rp[:, 2])[0, 1]
    assert c_same > 0.3 and abs(c_diff) < 0.05, (c_same, c_diff)
    print(f"[ok] S4 pooled cell = S3 sim_haugen: P(r >= 0.16) {p4:.4f} vs {p3:.4f}, SD {r4.std():.4f} vs "
          f"{r3.std():.4f}; same-era sexes correlate {c_same:.2f}, eras {c_diff:+.3f}")


def test_cell_probability_rule():
    rng = np.random.default_rng(7)
    r = rng.normal(0.0, 0.05, 20000)
    p, m = T.cell_prob_upper(r, 0.08)
    assert m == "share" and abs(p - (r >= 0.08).mean()) < 1e-15
    p, m = T.cell_prob_upper(r, 0.19)                  # ~1 hit in 20,000 -> normal approximation
    assert m == "normal" and abs(p - stats.norm.sf((0.19 - r.mean()) / r.std(ddof=1))) < 1e-15
    assert (r >= 0.19).sum() < T.MIN_HITS
    p, m = T.cell_prob_ns(r, 0.098)
    assert m == "share" and abs(p - (np.abs(r) < 0.098).mean()) < 1e-15
    print("[ok] per-cell probability: simulated share at >= 200 hits, normal approximation below")


def test_invert():
    g = np.array([0.0, 0.1, 0.2])
    assert abs(T.invert(g, [0.01, 0.03, 0.07]) - 0.15) < 1e-12
    assert T.invert(g, [0.06, 0.07, 0.08]) == 0.0
    assert T.invert(g, [0.01, 0.02, 0.03]) is None
    print("[ok] inversion: interpolation, first grid point, never reached")


def test_h6_helpers():
    lo, hi = T.f_ratio_ci(2.0, 5, 1.0, 6)
    R = 4.0
    assert abs(lo - np.sqrt(R / stats.f.ppf(0.975, 4, 5))) < 1e-12 and abs(hi - np.sqrt(R / stats.f.ppf(0.025, 4, 5))) < 1e-12
    rng = np.random.default_rng(8)
    yr = np.arange(1999, 2026, dtype=float)
    # widening dispersion around a mean trend: the slope of |residual| is positive on average (vectorised over
    # 2,000 realisations); constant dispersion gives slopes centred on 0
    Z = rng.normal(0, 1, (2000, len(yr)))
    s_wide = T.absdev_slope(np.broadcast_to(yr, Z.shape), Z * (1 + 0.5 * (yr - yr[0])) + 0.3 * (yr - yr[0])) * 10
    s_flat = T.absdev_slope(np.broadcast_to(yr, Z.shape), 5 * Z) * 10
    assert s_wide.mean() > 10 * s_wide.std() / np.sqrt(len(s_wide)) and (s_wide > 0).mean() > 0.95, s_wide.mean()
    assert abs(s_flat.mean()) < 4 * s_flat.std() / np.sqrt(len(s_flat)), s_flat.mean()
    strong = rng.normal(0, 1, len(yr)) * (0.2 + (yr - yr[0]))
    tb = T.trend_block(yr, strong, T.absdev_slope, 2000, 2000, np.random.default_rng(9))
    assert tb["slope"] > 0 and tb["perm_p"] < 0.05 and tb["lo"] > 0, tb
    tb0 = T.trend_block(yr, 5 * rng.normal(0, 1, len(yr)), T.absdev_slope, 500, 2000, np.random.default_rng(11))
    assert 0 < tb0["perm_p"] <= 1 and tb0["lo"] < tb0["slope"] < tb0["hi"]
    # a pure linear mean trend has zero dispersion trend (residuals are all 0)
    assert abs(T.absdev_slope(yr, 2.0 * yr)) < 1e-9
    sds = T.boot_sds(np.array([1.0, 5.0, -3.0, 2.0, 0.0]), np.full(5, 0.5), 3000, np.random.default_rng(10))
    assert sds.shape == (3000,) and sds.min() >= 0 and np.median(sds) < np.std([1.0, 5.0, -3.0, 2.0, 0.0], ddof=1) + 1
    st = pd.DataFrame({"comp_year": ["A"] * 6 + ["B"] * 3,
                       "rt_s": [0.095, 0.0999, 0.100, 0.089, np.nan, 0.150, 0.091, 0.140, 0.120],
                       "is_fs": [True, True, False, True, True, False, True, False, False]})
    c = T.near_threshold_counts(st).set_index("comp_year")
    assert c.loc["A"].tolist() == [6, 4, 3, 2] and c.loc["B"].tolist() == [3, 1, 1, 1]
    print("[ok] H6 helpers: F CI, dispersion trend + permutation p, bootstrap SDs, near-threshold counting")


def test_verdict_rules():
    assert T.s4_verdict(0.009, 0.05) == "WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE"
    assert T.s4_verdict(0.01, 0.9) == "WITHIN-CHAMPIONSHIP ANALYSIS NOT EXCLUDED"
    assert T.s4_verdict(0.009, 0.049).startswith("INCONCLUSIVE")
    assert T.lr_verdict(10.0) == "FAVOURS POOLED" and T.lr_verdict(0.1) == "FAVOURS WITHIN"
    assert T.lr_verdict(9.99) == T.lr_verdict(0.11) == "INCONCLUSIVE"
    assert T.inversion_verdict(None, 0.114) == T.inversion_verdict(0.115, 0.114) == "WITHIN READING NEEDS r_w ABOVE OUR CI"
    assert T.inversion_verdict(0.114, 0.114) == "WITHIN READING COMPATIBLE WITH OUR CI"
    assert T.classify_ratio(1.01, 3) == "WORSENING" and T.classify_ratio(0.2, 0.99) == "IMPROVING"
    assert T.classify_ratio(0.5, 2) == T.classify_ratio(1.0, 2) == "PERSISTING, NOT WORSENING"
    print("[ok] pre-registered verdict rules")


# ---------------------------------------------------------------------------------------------------
# claim guards on the stored result
# ---------------------------------------------------------------------------------------------------

IMPL = "WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE"


def check_s4_verdicts(tj: dict) -> list:
    n, bad = tj["numbers"], []
    v = n["s4_verdict"]
    pw, pp = n["s4_p_within_upper"]["value"], n["s4_p_pooled_upper"]["value"]
    if v["p_within_upper"] != pw or v["p_pooled_upper"] != pp:
        bad.append("s4_verdict fields disagree with s4_p_*_upper")
    if v["value"] != T.s4_verdict(pw, pp):
        bad.append(f"S4 verdict {v['value']} but the stored probabilities imply {T.s4_verdict(pw, pp)}")
    if v["verdict_if_pooled_at_estimate"] != T.s4_verdict(pw, n["s4_p_pooled_estimate"]["value"]):
        bad.append("alternative reading (pooled at estimate) disagrees")
    if v["verdict_if_pooled_at_zero"] != T.s4_verdict(pw, n["s4_p_pooled_zero"]["value"]):
        bad.append("alternative reading (pooled at zero) disagrees")
    d = pd.DataFrame(tj["tables"]["s4_designs"])
    d = d[(d["setting"] == "upper") & d["in_average"]]
    per = {r["design"]: T.s4_verdict(T.sig(r["p3_within"]), T.sig(r["p3_pooled"])) for _, r in d.iterrows()}
    if per != v["per_design"]:
        bad.append("per-design verdicts disagree with the design table")
    if abs(np.mean([x == IMPL for x in per.values()]) - v["share_of_designs_implausible"]) > 1e-9:
        bad.append("share of designs meeting the rule disagrees")
    for nm in ("zero", "estimate", "upper", "haugen"):
        want_w = T.sig(d_avg(tj, "p3_within", nm))
        want_p = T.sig(d_avg(tj, "p3_pooled", nm))
        if n[f"s4_p_within_{nm}"]["value"] != want_w or n[f"s4_p_pooled_{nm}"]["value"] != want_p:
            bad.append(f"design-averaged probabilities at {nm} disagree with the design table")
    return bad


def d_avg(tj, col, setting):
    d = pd.DataFrame(tj["tables"]["s4_designs"])
    d = d[(d["setting"] == setting) & d["in_average"]]
    return float(d[col].mean())


def check_s4_lr_inversion(tj: dict) -> list:
    n, bad = tj["numbers"], []
    for nm in ("zero", "estimate", "upper", "haugen"):
        pw, pp, lr = n[f"s4_p_within_{nm}"]["value"], n[f"s4_p_pooled_{nm}"]["value"], n[f"s4_lr_{nm}"]["value"]
        if pw > 0 and abs(lr - pp / pw) > 1e-3 * (pp / pw):
            bad.append(f"s4_lr_{nm} {lr} != stored pooled / within {pp / pw}")
    if n["s4_verdict_lr"]["value"] != T.lr_verdict(n["s4_lr_estimate"]["value"]):
        bad.append("LR verdict disagrees with the stored LR at our estimate")
    rs, rup = n["s4_r_star"]["value"], n["s4_rw_upper"]["value"]
    if n["s4_verdict_inversion"]["value"] != T.inversion_verdict(rs, rup):
        bad.append("inversion verdict disagrees with the stored r_star / r_up")
    c = pd.DataFrame(tj["tables"]["s4_curve_average"])
    r2 = T.invert(c["r_w"], c["p3_within_avg"])
    if (r2 is None) != (rs is None) or (r2 is not None and abs(round(r2, 4) - rs) > 2e-4):
        bad.append(f"r_star {rs} does not match the stored curve ({r2})")
    return bad


def check_h6(tj: dict) -> list:
    n, bad = tj["numbers"], []
    lo, hi = n["h6_sd_ratio_recent_pre2010"]["ci95"]
    if n["h6_verdict"]["value"] != T.classify_ratio(lo, hi):
        bad.append(f"H6 verdict {n['h6_verdict']['value']} but the stored CI implies {T.classify_ratio(lo, hi)}")
    for k in ("h6_sd_ratio_recent_2010s", "h6_sens_wic_sd_ratio_recent_pre2010", "h6_sens_wch_sd_ratio_recent_pre2010"):
        if n[k]["classification"] != T.classify_ratio(*n[k]["ci95"]):
            bad.append(f"{k} classification disagrees with its CI")
    sds = {p: n[f"h6_sd_ms_{p}"]["value"] for p in T.PERIODS}
    if abs(round(sds["2020_2025"] / sds["pre2010"], 3) - n["h6_sd_ratio_recent_pre2010"]["value"]) > 2e-3:
        bad.append("primary SD ratio disagrees with the stored period SDs")
    return bad


def check_probabilities(tj: dict) -> list:
    bad = []
    for k, e in tj["numbers"].items():
        if k.startswith(("s4_p_", "s4_full_p_", "s4_lenient_p_", "s4_litsd_p_")) or k == "s4_cell5_pooled_cell_m9703_p":
            if not (0.0 <= float(e["value"]) <= 1.0):
                bad.append(f"{k}: probability outside [0, 1]: {e['value']}")
    mono = tj["extra"]["s4_monotone_in_rw"]
    if not (mono["within_design_avg"] and mono["pooled_design_avg"]):
        bad.append(f"design-averaged probabilities not monotone in r_w: {mono}")
    return bad


def check_inputs(tj: dict, cal: dict, desc: dict, fair: dict, sysj: dict | None) -> list:
    n, bad = tj["numbers"], []
    if n["s4_rw_estimate"]["value"] != cal["numbers"]["r_corrected"]["value"]:
        bad.append("s4_rw_estimate != calibration.r_corrected")
    if n["s4_rw_upper"]["value"] != cal["numbers"]["r_ci_high_at_b_low"]["value"]:
        bad.append("s4_rw_upper != calibration.r_ci_high_at_b_low")
    p = tj["extra"]["s4_parameters"]
    if sysj is not None and "S3" in sysj.get("extra", {}).get("simulation_parameters", {}):
        s3 = sysj["extra"]["simulation_parameters"]["S3"]
        for a, b in (("sd_b", "sd_hold_between_s"), ("sd_w", "sd_hold_within_s"), ("sd_champ", "sd_champ_ms"),
                     ("sd_race", "sd_race_ms"), ("sd_ath", "sd_athlete_ms"), ("sd_res", "sd_residual_ms")):
            if abs(p[a] - s3[b]) > 1e-5 * max(1.0, abs(s3[b])):
                bad.append(f"S4 input {a} {p[a]} != S3 {b} {s3[b]}")
    me = pd.DataFrame(desc["tables"]["meet_effects"])
    od = me[~me["comp_year"].str.startswith("WIC")]
    f_, s_ = od.loc[od["deviation_ms"].idxmin()], od.loc[od["deviation_ms"].idxmax()]
    if n["h6_offset_fastest_ms"]["champ"] != f_["comp_year"] or abs(n["h6_offset_fastest_ms"]["value"] - f_["deviation_ms"]) > 0.01:
        bad.append("fastest offset disagrees with descriptive.json meet_effects")
    if n["h6_offset_slowest_ms"]["champ"] != s_["comp_year"] or abs(n["h6_offset_slowest_ms"]["value"] - s_["deviation_ms"]) > 0.01:
        bad.append("slowest offset disagrees with descriptive.json meet_effects")
    ft = desc["numbers"]["fs_near_threshold_090_100"]
    if n["h6_fs_near_total"]["value"] != ft["value"] or n["h6_fs_near_total"]["by_champ"] != ft["by_meet"]:
        bad.append("near-threshold false starts disagree with descriptive.json")
    top = n["h6_fs_near_top_champ_count"]
    all_one = len(n["h6_fs_near_total"]["by_champ"]) == 1
    if (top["value"] == top["total"]) != all_one or top["total"] != n["h6_fs_near_total"]["value"]:
        bad.append("'all near-threshold false starts at one championship' flag disagrees with the counts")
    fm = fair["numbers"]["meet_p_max_M"]
    if n["h6_rate_per1000_max"]["champ"] != fm["meet"] or abs(n["h6_rate_per1000_max"]["value"] - 1000 * fm["value"]) > 1e-3 * 1000 * fm["value"]:
        bad.append("top modelled rate disagrees with fairness.json meet_p_max_M")
    return bad


def check_s3_agreement(tj: dict, sysj: dict | None) -> list:
    if sysj is None or "h1s3_cell5_p_ge016_sig" not in sysj["numbers"]:
        return []
    a = tj["numbers"]["s4_cell5_pooled_cell_m9703_p"]
    b = sysj["numbers"]["h1s3_cell5_p_ge016_sig"]["value"]
    n_a, n_b = a["n_sims"], sysj["numbers"]["h1s3_cell5_r_mean"]["n_sims"]
    se = np.sqrt(b * (1 - b) / n_a + b * (1 - b) / n_b)
    return [] if abs(a["value"] - b) <= 4 * se else [f"S4 pooled cell {a['value']} vs S3 {b} (4 SE = {4 * se:.4f})"]


def run_guards() -> bool:
    p = OUT / "trend.json"
    if not p.exists():
        print("[skip] analysis/outputs/trend.json not built")
        return True
    tj = json.loads(p.read_text(encoding="utf-8"))
    cal = json.loads((OUT / "calibration.json").read_text(encoding="utf-8"))
    desc = json.loads((OUT / "descriptive.json").read_text(encoding="utf-8"))
    fair = json.loads((OUT / "fairness.json").read_text(encoding="utf-8"))
    sp = OUT / "systematic.json"
    sysj = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None

    def all_checks(t):
        return (check_s4_verdicts(t) + check_s4_lr_inversion(t) + check_h6(t) + check_probabilities(t)
                + check_inputs(t, cal, desc, fair, sysj) + check_s3_agreement(t, sysj))

    failures = all_checks(tj)
    corruptions = []

    def corrupt(fn):
        c = copy.deepcopy(tj)
        fn(c)
        corruptions.append(bool(all_checks(c)))

    flip = {IMPL: "WITHIN-CHAMPIONSHIP ANALYSIS NOT EXCLUDED"}
    corrupt(lambda c: c["numbers"]["s4_verdict"].update(value=flip.get(c["numbers"]["s4_verdict"]["value"], IMPL)))
    corrupt(lambda c: c["numbers"]["s4_p_within_upper"].update(value=0.5))
    corrupt(lambda c: c["numbers"]["s4_p_pooled_upper"].update(value=0.001))
    corrupt(lambda c: c["numbers"]["s4_lr_estimate"].update(value=c["numbers"]["s4_lr_estimate"]["value"] * 2))
    corrupt(lambda c: c["numbers"]["s4_verdict_lr"].update(value="FAVOURS WITHIN"))
    corrupt(lambda c: c["numbers"]["s4_r_star"].update(value=0.05))
    corrupt(lambda c: c["numbers"]["s4_verdict_inversion"].update(value="WITHIN READING COMPATIBLE WITH OUR CI"
                                                                   if c["numbers"]["s4_verdict_inversion"]["value"].startswith("WITHIN READING NEEDS")
                                                                   else "WITHIN READING NEEDS r_w ABOVE OUR CI"))
    corrupt(lambda c: c["numbers"]["h6_verdict"].update(value="WORSENING"
                                                        if c["numbers"]["h6_verdict"]["value"] != "WORSENING" else "IMPROVING"))
    corrupt(lambda c: c["numbers"]["h6_sd_ratio_recent_pre2010"].update(ci95=[1.2, 3.0]))
    corrupt(lambda c: c["numbers"]["s4_litsd_p_pooled_upper"].update(value=1.2))
    corrupt(lambda c: c["numbers"]["s4_rw_upper"].update(value=0.2))
    corrupt(lambda c: c["numbers"]["h6_fs_near_total"].update(value=c["numbers"]["h6_fs_near_total"]["value"] + 1))
    corrupt(lambda c: c["numbers"]["h6_offset_fastest_ms"].update(champ="WCH1999"))
    corrupt(lambda c: c["extra"]["s4_parameters"].update(sd_w=0.16))
    corrupt(lambda c: c["numbers"]["s4_cell5_pooled_cell_m9703_p"].update(value=0.2))
    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(corruptions)}/{len(corruptions)}")
    ok = not failures and all(corruptions)
    if ok:
        print("[ok] trend.json: verdicts, likelihood ratios, r_star, H6 classification and input provenance agree "
              "with the stored numbers and their sources")
    return ok


def test_guards():
    assert run_guards()


if __name__ == "__main__":
    for fn in (test_r_of_beta_exact, test_beta_for_rw, test_r_crit, test_s4_within_ignores_championship_offsets,
               test_s4_matches_s3, test_cell_probability_rule, test_invert, test_h6_helpers, test_verdict_rules):
        fn()
    if not run_guards():
        sys.exit(1)
