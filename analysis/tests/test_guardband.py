"""Tests for analysis/guardband.py (guard every claim a test can hold).

Unit tests (synthetic data, no repo outputs needed):
  1. acceptance limits of P0-P3 (deviation from 0.100 s), including the common-u_res variant of P3
  2. flag_prob = F_R(L - o) for every family; under P0 it is fairness_sim.p_fs(o) exactly
  3. counting on the 0.001 s grid: limit edges, float noise, negative RTs, 'no longer flagged' / 'newly flagged'
  4. summaries over championships (max, median, folds) and safe ratios with zeros
  5. the pre-registered decision rule (truth table and boundaries)
  6. the corrected false-start classification (notes 'not a false start'; Fiore 0.000 placeholders)
  7. numerical accuracy of the ex-Gaussian left tail used by the fairness model (vs quadrature of the density)
Claim guards on analysis/outputs/guardband.json (skipped if absent), each proven to fire on a corrupted copy:
  G1 verdict, criteria flags, alternative readings and sensitivity verdicts recomputed from stored numbers
  G2 g = k x u for every variant; limits and effective (0.001 s grid) limits recomputed
  G3 P0 reproduces fairness.json (table meets, meet_p_max_M, meet_iqr_fold_change)
  G4 P1 <= P0 at every championship with the same top championship; P2 plug-in = reference rate = descriptive
     tail_mass_ref_exgauss_M; cuts = stored max ratios
  G5 counts reproduce descriptive.json and add up (descriptive set - noted - placeholders = primary set)
  G6 (c) shares = stored counts / denominators; (b) by-championship counts sum to totals; the near-threshold false
     starts of descriptive.json are among those P1 no longer flags
  G7 the false_starts table: primary-set rows, and P1 'no longer flagged' recomputed from each RT and the limit
  G8 the trade-off curve is monotone, starts at P0, and its summaries match the curve
  G9 rerunning the registered command reproduces guardband.json byte for byte

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_guardband.py   (or pytest)
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import integrate, stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import guardband as G  # noqa: E402
import rtdist  # noqa: E402
from fairness_sim import p_fs  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"
CMD = ("analysis/guardband.py --seed 20260928 --descriptive analysis/outputs/descriptive.json --fairness "
       "analysis/outputs/fairness.json --offset-draws 25 --out {out}")
PAR = {"exgauss": {"mu": 0.14134, "sigma": 0.0137249, "tau": 0.0141533},
       "slognorm": {"shift": 0.06, "m": -2.5, "s": 0.25},
       "swald": {"shift": 0.06, "a": 0.4, "b": 0.2}}


# ---------------------------------------------------------------------------------------------------
# unit tests
# ---------------------------------------------------------------------------------------------------

def test_limits():
    o, se = np.array([-18.5, 0.0, 15.5]), np.array([1.0, 2.0, 1.5])
    assert np.array_equal(G.limit_dev_ms("P0", o, se), np.zeros(3))
    assert np.allclose(G.limit_dev_ms("P1", o, se, g_ms=15.26), -15.26)
    assert np.allclose(G.limit_dev_ms("P2", o, se), o)
    assert np.allclose(G.limit_dev_ms("P3", o, se, k=1.645), o - 1.645 * se)
    assert np.allclose(G.limit_dev_ms("P3", o, se, k=2.0, u_res_ms=3.0), o - 6.0)
    try:
        G.limit_dev_ms("P9", o, se)
        raise AssertionError("unknown policy accepted")
    except ValueError:
        pass
    print("[ok] acceptance limits P0-P3")


def test_flag_prob():
    o = np.array([-18.5, -3.0, 0.0, 9.0])
    for fam, par in PAR.items():
        for d in (np.zeros(4), np.full(4, -15.26), o, o - 2.0):
            got = G.flag_prob(fam, par, d, o)
            want = rtdist.cdf(fam, par, (100.0 + d - o) / 1000.0)
            assert np.allclose(got, want, rtol=1e-10, atol=1e-300), fam
    # P0 equals the fairness model's own call exactly (same shift argument)
    assert np.array_equal(G.flag_prob("exgauss", PAR["exgauss"], np.zeros(4), o),
                          np.asarray(p_fs("exgauss", PAR["exgauss"], o / 1000.0)))
    # P2 plug-in: the offset cancels exactly, so every championship gets F_R(0.100)
    r2 = G.flag_prob("exgauss", PAR["exgauss"], o, o)
    assert np.all(r2 == r2[0]) and abs(r2[0] - rtdist.cdf("exgauss", PAR["exgauss"], 0.100)) < 1e-15
    print("[ok] flag_prob = F_R(L - o); P0 = fairness_sim.p_fs; P2 plug-in equal everywhere")


def test_grid_counting():
    rt = np.array([0.099, 0.100, 0.085, 0.084, -0.2, 0.0, 0.147, 0.0999999999])
    assert G.is_flagged(rt, 0.0).tolist() == [True, False, True, True, True, True, False, False]
    lim = -15.259                                                  # 0.084741 s
    assert G.is_flagged(rt, lim).tolist() == [False, False, False, True, True, True, False, False]
    assert G.unflagged(rt, lim).tolist() == [True, False, True, False, False, False, False, False]
    # float noise around an integer-ms limit: 0.095 stays unflagged at a limit of 0.095 + 1e-12 s
    assert not G.is_flagged(np.array([0.095]), -5.0 + 1e-9)[0] and G.is_flagged(np.array([0.094]), -5.0)[0]
    # raising the limit (P2 at a slow championship) newly flags legal RTs below it, never above
    legal = np.array([0.100, 0.104, 0.105, 0.120])
    assert G.newly_flagged(legal, 4.8).tolist() == [True, True, False, False]
    assert not G.newly_flagged(legal, -3.0).any() and not G.unflagged(legal, 4.8).any()
    print("[ok] 0.001 s grid counting: limit edges, float noise, negative RTs, newly flagged")


def test_summaries():
    r = np.array([[1.0, 2.0, 3.0, 4.0, 100.0], [0.0, 0.0, 0.0, 1.0, 5.0]])
    s = G.summarise(r)
    assert s["max"].tolist() == [100.0, 5.0] and s["argmax"].tolist() == [4, 4]
    assert s["median"].tolist() == [3.0, 0.0]
    assert abs(s["fold_max_median"][0] - 100.0 / 3.0) < 1e-12 and math.isinf(s["fold_max_median"][1])
    assert abs(s["fold_iqr"][0] - 2.0) < 1e-12 and math.isinf(s["fold_iqr"][1])
    assert G.ratio(4.0, 2.0) == 2.0 and math.isinf(G.ratio(1.0, 0.0))
    assert G.pct_ci([1.0, 2.0, np.inf, np.inf])[1] is None
    print("[ok] summaries and ratios (zeros -> infinite, stored as null)")


def test_verdict_rule():
    assert G.verdict(22.5, 0.0625) == G.LABEL_OK
    assert G.verdict(10.0, 0.10) == G.LABEL_OK                      # both bars inclusive
    assert G.verdict(22.5, 0.148) == G.LABEL_I
    assert G.verdict(9.99, 0.05) == G.LABEL_II
    assert G.verdict(5.8, 0.148) == G.LABEL_NONE
    print("[ok] pre-registered decision rule")


def test_classify_records():
    rt = pd.DataFrame({
        "race_id": ["A-1", "A-1", "A-2", "B-1", "B-1", "B-2", "B-3"],
        "athlete": ["11", "12", "13", np.nan, np.nan, np.nan, "14"],
        "source": ["rt_athletes"] * 3 + ["rt_fiore"] * 3 + ["rt_athletes"],
        "rt_s": [0.099, 0.145, np.nan, 0.0, 0.0, -0.1, 0.147],
        "is_fs": [True, True, True, True, True, True, True],
        "result": ["DQ", "DQ", "DQ", "DNS", "DQ", "DQ", "DQ"],
        "status": ["FS", "DQ", "DQ", "", "", "", "FS"]})
    raw = pd.DataFrame({"race_id": ["A-1", "A-1", "A-2", "B-3"], "athlete_id": [11, 12, 13, 14],
                        "notes": ["false start (official PDF: DQ TR16.8)", "official PDF: DQ TR22.6 (not a false start)",
                                  "official PDF: DQ 163.3(a) (not a false start)", "false start (official PDF: TR16.8)"]})
    m = G.classify_records(rt, raw)
    assert m["mis_note"].tolist() == [False, True, True, False, False, False, False]
    assert m["ph"].tolist() == [False, False, False, True, True, False, False]
    assert m["ph_dns"].tolist() == [False, False, False, True, False, False, False]
    assert m["fs_corr"].tolist() == [True, False, False, False, True, True, True]
    assert m["fs_meas"].tolist() == [True, False, False, False, False, True, True]
    assert m["fs_note"].tolist() == [True, False, False, True, True, True, True]
    assert m["n_raw_not_fs_notes"] == 2
    print("[ok] corrected false-start classification")


def test_exgauss_left_tail_accuracy():
    p = PAR["exgauss"]
    d = stats.exponnorm(K=p["tau"] / p["sigma"], loc=p["mu"], scale=p["sigma"])
    for x in (0.060, 0.070, 0.080, 0.085, 0.090, 0.100, 0.1185):
        q, _ = integrate.quad(d.pdf, p["mu"] - 40 * p["sigma"], x, epsabs=0.0, epsrel=1e-11, limit=200)
        c = float(rtdist.cdf("exgauss", p, x))
        assert abs(c - q) <= 1e-6 * q, (x, c, q)
    print("[ok] ex-Gaussian left tail: closed form = quadrature within 1e-6 (relative) down to 0.060 s")


# ---------------------------------------------------------------------------------------------------
# claim guards on the stored result
# ---------------------------------------------------------------------------------------------------

def check_verdict(gj: dict) -> list:
    n, bad = gj["numbers"], []
    v = n["verdict"]
    cut, share = n["a_p1_cut_max"]["value"], n["c_share_band"]["value"]
    if v["value"] != G.verdict(cut, share):
        bad.append(f"verdict {v['value']} but the stored cut {cut} and share {share} imply {G.verdict(cut, share)}")
    if v["cut_max"] != cut or v["share_changed"] != share or v["g_ms"] != n["g_ms"]["value"]:
        bad.append("verdict fields disagree with the stored numbers")
    if v["crit_cut_ge_10"] != (cut >= G.CUT_BAR) or v["crit_share_le_010"] != (share <= G.SHARE_BAR):
        bad.append("verdict criterion flags disagree")
    lo = n["a_p1_cut_max"]["ci95"][0]
    if v["cut_ci_low_ge_10"] != (lo is not None and lo >= G.CUT_BAR):
        bad.append("cut CI flag disagrees")
    if v["reading_note_fix_only"] != G.verdict(cut, n["c_share_band_note"]["value"]):
        bad.append("note-fix-only reading disagrees")
    if v["reading_descriptive_definition"] != G.verdict(cut, n["c_share_band_desc"]["value"]):
        bad.append("descriptive-definition reading disagrees")
    sv = v["sensitivity_verdicts"]
    for s in ("p1_k1", "p1_k2", "p1_u_ci_low", "p1_u_ci_high", "p1_u_mom", "p1_u_raw", "p1_u_comb"):
        want = G.verdict(n[f"a_{s}_cut_max"]["value"], n[f"c_{s[3:]}_share_band"]["value"])
        if sv.get(s) != want:
            bad.append(f"sensitivity verdict {s} disagrees")
    for sex, fam in G.SENS_CELLS:
        if sv.get(f"{sex}_{fam}") != G.verdict(n[f"s_{sex}_{fam}_p1_cut_max"]["value"], share):
            bad.append(f"sensitivity verdict {sex}_{fam} disagrees")
    return bad


def check_g(gj: dict) -> list:
    n, bad = gj["numbers"], []
    u = n["u_ms"]["value"]
    lo, hi = n["u_ms"]["ci95"]
    want = {"g_ms": (1.645, u), "g_ms_k1": (1.0, u), "g_ms_k2": (2.0, u), "g_ms_u_ci_low": (1.645, lo),
            "g_ms_u_ci_high": (1.645, hi), "g_ms_u_mom": (1.645, n["u_mom_ms"]["value"]),
            "g_ms_u_raw": (1.645, n["u_raw_ms"]["value"]), "g_ms_u_comb": (1.645, n["u_comb_ms"]["value"])}
    for key, (k, uu) in want.items():
        e = n[key]
        if abs(e["value"] - k * uu) > 2e-3 * k * uu or e["k"] != k or abs(e["u_ms"] - uu) > 1e-3 * uu:
            bad.append(f"{key} {e['value']} != {k} x {uu}")
        if abs(e["limit_s"] - (0.100 - k * uu / 1000.0)) > 1e-5:          # stored u has 4 significant digits
            bad.append(f"{key} limit disagrees")
        if abs(e["limit_effective_s"] - math.ceil(round(e["limit_s"] * 1000, 6)) / 1000.0) > 1e-9:
            bad.append(f"{key} effective limit disagrees")
    if n["c_share_band"]["band_s"][0] != n["g_ms"]["limit_s"]:
        bad.append("(c) band does not start at the P1 limit")
    return bad


def check_p0(gj: dict, fair: dict) -> list:
    n, bad = gj["numbers"], []
    ch = pd.DataFrame(gj["tables"]["championships"]).set_index("comp_year")
    fm = pd.DataFrame(fair["tables"]["meets"])
    fm = fm[(fm["sex"] == "M") & (fm["family"] == "exgauss")].set_index("comp_year")["p_median_hold"] * 1000.0
    if set(fm.index) != set(ch.index):
        bad.append("championship sets differ from fairness.json")
    else:
        rel = ((ch["rate_p0"] - fm.loc[ch.index]).abs() / fm.loc[ch.index]).max()
        if rel > 1e-4:
            bad.append(f"P0 rates differ from fairness.json meets (max relative {rel:.2g})")
    fx = fair["numbers"]["meet_p_max_M"]
    if n["a_p0_max_per1000"]["champ"] != fx["meet"] or abs(n["a_p0_max_per1000"]["value"] - 1000 * fx["value"]) > 1e-3 * 1000 * fx["value"]:
        bad.append("P0 max disagrees with fairness.json meet_p_max_M")
    if abs(n["a_p0_fold_iqr_offsetq"]["value"] - fair["numbers"]["meet_iqr_fold_change"]["value"]) > 1e-3 * fair["numbers"]["meet_iqr_fold_change"]["value"]:
        bad.append("offset-percentile middle-half fold disagrees with fairness.json")
    return bad


def check_policies(gj: dict, desc: dict) -> list:
    n, bad = gj["numbers"], []
    ch = pd.DataFrame(gj["tables"]["championships"])
    if not (ch["rate_p1"] <= ch["rate_p0"]).all() or not (ch["rate_p1_k2"] <= ch["rate_p1"]).all():
        bad.append("a guard band raised a championship's modelled rate")
    if ch.loc[ch["rate_p1"].idxmax(), "comp_year"] != ch.loc[ch["rate_p0"].idxmax(), "comp_year"]:
        bad.append("P1 top championship differs from P0's (a uniform shift keeps the order)")
    if n["a_p1_max_per1000"]["champ"] != n["a_p0_max_per1000"]["champ"]:
        bad.append("stored P1 top championship differs from P0's")
    ref = n["a_ref_rate_per1000"]["value"]
    tm = 1000.0 * desc["numbers"]["tail_mass_ref_exgauss_M"]["value"]
    if abs(ref - tm) > 1e-3 * tm:
        bad.append("reference rate disagrees with descriptive tail_mass_ref_exgauss_M")
    if (ch["rate_p2"] - ref).abs().max() > 1e-3 * ref or n["a_p2_max_per1000"]["value"] != ref:
        bad.append("P2 plug-in rates are not the reference rate everywhere")
    for s in ("p1", "p1_k1", "p1_k2", "p2", "p3"):
        want = n["a_p0_max_per1000"]["value"] / n[f"a_{s}_max_per1000"]["value"]
        if abs(n[f"a_{s}_cut_max"]["value"] - want) > 2e-3 * want:
            bad.append(f"a_{s}_cut_max disagrees with the stored maxima")
    for s in ("p0", "p1"):
        lo, hi = n[f"a_{s}_max_per1000"]["ci95"]
        if not (lo <= n[f"a_{s}_max_per1000"]["value"] <= hi):
            bad.append(f"a_{s}_max point outside its CI")
    return bad


def check_counts(gj: dict, desc: dict) -> list:
    n, bad = gj["numbers"], []
    nd = desc["numbers"]
    if n["b_n_fs_desc_with_rt"]["value"] != nd["fs_recorded_with_rt"]["value"]:
        bad.append("descriptive-set count disagrees with descriptive.json fs_recorded_with_rt")
    if n["b_n_fs_desc_total"]["value"] != nd["fs_per_1000_starts"]["n_fs"]:
        bad.append("descriptive total disagrees with descriptive.json n_fs")
    if n["b_n_fs_desc_with_rt"]["value"] - n["b_n_misclassified_not_fs_note"]["with_rt"] != n["b_n_fs_note_with_rt"]["value"]:
        bad.append("descriptive set - noted rows != note-fix set")
    if n["b_n_fs_note_with_rt"]["value"] - n["b_n_fiore_rt0_placeholders"]["value"] != n["b_n_fs_with_rt"]["value"]:
        bad.append("note-fix set - placeholders != primary set")
    if n["b_n_fs_desc_total"]["value"] - n["b_n_misclassified_not_fs_note"]["value"] - n["b_n_fiore_rt0_placeholders"]["dns"] != n["b_n_fs_total"]["value"]:
        bad.append("corrected total does not add up")
    if n["b_n_fs_total"]["value"] - n["b_n_fs_with_rt"]["value"] != n["b_n_fs_no_rt"]["value"]:
        bad.append("false starts without an RT do not add up")
    return bad


def check_shares(gj: dict, desc: dict) -> list:
    n, bad = gj["numbers"], []
    nm = n["b_n_fs_with_rt"]["value"]
    for key in [k for k in n if k.endswith("_share_band") or k.startswith("c_share_band_")]:
        e = n[key]
        if e["value"] is None or abs(e["value"] - e["count"] / e["n_fs_with_rt"]) > 1e-3 * max(e["value"], 1e-9):
            bad.append(f"{key} != count / n")
    c = n["c_share_band"]
    if c["count"] != n["b_p1_n_unflagged"]["value"] or c["n_fs_with_rt"] != nm:
        bad.append("(c) count or denominator disagrees with (b)")
    if n["c_share_band_note"]["n_fs_with_rt"] != n["b_n_fs_note_with_rt"]["value"] or \
            n["c_share_band_desc"]["n_fs_with_rt"] != n["b_n_fs_desc_with_rt"]["value"]:
        bad.append("(c) sensitivity denominators disagree")
    for k, e in n.items():
        if k.startswith(("b_p", "b2_p")) and sum(e["by_champ"].values()) != e["value"]:
            bad.append(f"{k}: by-championship counts do not sum to the total")
    near = desc["numbers"]["fs_near_threshold_090_100"]
    u = n["b_p1_n_unflagged"]
    if n["g_ms"]["limit_s"] < 0.090 and (u["value"] < near["value"] or any(u["by_champ"].get(c, 0) < x for c, x in near["by_meet"].items())):
        bad.append("descriptive's near-threshold false starts are not all among those P1 no longer flags")
    if n["c_n_fs_ge_limit"]["value"] != c["count"] + n["b_n_fs_rt_ge_100"]["value"]:
        bad.append("false starts >= limit != band count + those >= 0.100")
    return bad


def check_fs_table(gj: dict) -> list:
    n, bad = gj["numbers"], []
    t = pd.DataFrame(gj["tables"]["false_starts"])
    prim = t[t["in_primary_set"]]
    if len(prim) != n["b_n_fs_with_rt"]["value"] or len(t) != n["b_n_fs_desc_with_rt"]["value"]:
        bad.append("false_starts table sizes disagree with the stored counts")
    if int(prim["unflagged_p1"].sum()) != n["b_p1_n_unflagged"]["value"]:
        bad.append("table P1 'no longer flagged' total disagrees")
    lim_ms = 1000.0 * n["g_ms"]["limit_s"]
    r = np.round(t["rt_s"].to_numpy(float) * 1000.0)
    want = (r < 100.0) & (r >= lim_ms - 1e-6)
    if not np.array_equal(want, t["unflagged_p1"].to_numpy(bool)):
        bad.append("table P1 'no longer flagged' flags disagree with RT and limit")
    if (prim["noted_not_a_false_start"] | prim["fiore_rt0_placeholder"]).any():
        bad.append("primary set contains a noted non-false start or a 0.000 placeholder")
    return bad


def check_curve(gj: dict) -> list:
    n, bad = gj["numbers"], []
    c = pd.DataFrame(gj["tables"]["tradeoff_p1"]).sort_values("g_ms")
    if (np.diff(c["max_per1000"]) > 0).any() or (np.diff(c["share_unflagged"]) < 0).any():
        bad.append("trade-off curve is not monotone")
    if abs(c["max_per1000"].iloc[0] - n["a_p0_max_per1000"]["value"]) > 1e-3 * n["a_p0_max_per1000"]["value"]:
        bad.append("curve at g = 0 is not P0")
    ok_cut = c[c["cut_max"] >= G.CUT_BAR]
    ok_sh = c[c["share_unflagged"] <= G.SHARE_BAR]
    if n["curve_g_min_cut10_ms"]["value"] != float(ok_cut["g_ms"].iloc[0]):
        bad.append("smallest g with a 10-fold cut disagrees with the curve")
    if n["curve_g_max_share010_ms"]["value"] != float(ok_sh["g_ms"].iloc[-1]):
        bad.append("largest g with <= 10% changed disagrees with the curve")
    both = bool(((c["cut_max"] >= G.CUT_BAR) & (c["share_unflagged"] <= G.SHARE_BAR)).any())
    if n["curve_any_g_meets_both"]["value"] != both:
        bad.append("'any g meets both' disagrees with the curve")
    return bad


def run_guards() -> bool:
    p = OUT / "guardband.json"
    if not p.exists():
        print("[skip] analysis/outputs/guardband.json not built")
        return True
    gj = json.loads(p.read_text(encoding="utf-8"))
    desc = json.loads((OUT / "descriptive.json").read_text(encoding="utf-8"))
    fair = json.loads((OUT / "fairness.json").read_text(encoding="utf-8"))

    def all_checks(t):
        return (check_verdict(t) + check_g(t) + check_p0(t, fair) + check_policies(t, desc) + check_counts(t, desc)
                + check_shares(t, desc) + check_fs_table(t) + check_curve(t))

    failures = all_checks(gj)
    corruptions = []

    def corrupt(fn):
        c = copy.deepcopy(gj)
        fn(c)
        corruptions.append(bool(all_checks(c)))

    other = {G.LABEL_I: G.LABEL_OK}
    corrupt(lambda c: c["numbers"]["verdict"].update(value=other.get(c["numbers"]["verdict"]["value"], G.LABEL_I)))
    corrupt(lambda c: c["numbers"]["c_share_band"].update(value=0.05))
    corrupt(lambda c: c["numbers"]["a_p1_cut_max"].update(value=8.0))
    corrupt(lambda c: c["numbers"]["verdict"]["sensitivity_verdicts"].update(p1_k1=G.LABEL_OK))
    corrupt(lambda c: c["numbers"]["g_ms"].update(value=12.0))
    corrupt(lambda c: c["numbers"]["g_ms_u_comb"].update(limit_effective_s=0.090))
    corrupt(lambda c: c["tables"]["championships"][0].update(rate_p0=c["tables"]["championships"][0]["rate_p0"] * 1.01))
    corrupt(lambda c: c["tables"]["championships"][3].update(rate_p1=c["tables"]["championships"][3]["rate_p0"] * 2))
    corrupt(lambda c: c["numbers"]["a_p2_max_per1000"].update(value=0.5))
    corrupt(lambda c: c["numbers"]["b_n_fs_desc_with_rt"].update(value=63))
    corrupt(lambda c: c["numbers"]["b_n_fs_with_rt"].update(value=64))
    corrupt(lambda c: c["numbers"]["b_p1_n_unflagged"]["by_champ"].update(WCH2022=3))
    corrupt(lambda c: next(r for r in c["tables"]["false_starts"] if not r["unflagged_p1"]).update(unflagged_p1=True))
    corrupt(lambda c: c["tables"]["tradeoff_p1"][10].update(max_per1000=1e6))
    corrupt(lambda c: c["numbers"]["curve_any_g_meets_both"].update(value=True))
    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(corruptions)}/{len(corruptions)}")
    ok = not failures and all(corruptions)
    if ok:
        print("[ok] guardband.json: verdict, g, P0 reproduction, policy ordering, counts, shares, false-start table "
              "and trade-off curve agree with the stored numbers and their sources")
    return ok


def check_rerun() -> bool:
    """G9: the registered command reproduces guardband.json byte for byte."""
    p = OUT / "guardband.json"
    if not p.exists():
        print("[skip] rerun check: guardband.json not built")
        return True
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "guardband.json"
        py = ROOT / ".venv" / "Scripts" / "python.exe"
        cmd = [str(py if py.exists() else sys.executable)] + CMD.format(out=out).split()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            print("FAIL rerun:", r.stderr[-2000:])
            return False
        a, b = hashlib.sha256(p.read_bytes()).hexdigest(), hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"[{'ok' if a == b else 'FAIL'}] rerun byte-identical: {a[:12]} vs {b[:12]}")
    return a == b


def test_guards():
    assert run_guards()


def test_rerun_byte_identical():
    assert check_rerun()


if __name__ == "__main__":
    for fn in (test_limits, test_flag_prob, test_grid_counting, test_summaries, test_verdict_rule,
               test_classify_records, test_exgauss_left_tail_accuracy):
        fn()
    ok = run_guards()
    ok = check_rerun() and ok
    if not ok:
        sys.exit(1)
