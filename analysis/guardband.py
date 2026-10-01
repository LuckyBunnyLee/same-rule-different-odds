"""Guard band for the 0.100 s false-start rule: the pre-registered analysis of analysis/prereg_guardband.md
(committed before anything here was computed).

SIMULATION (metric a) + RECORDS (metrics b, c). Anti-doping applies a decision limit DL = T + g, g = k x u_c,Max,
k = 1.645 (one-sided 95%), with u_c,Max built from between-laboratory reproducibility (WADA TD2022DL; JCGM 106:2012
"guarded rejection"). The athletics analogue uses the between-championship variation of official RT.

Policies (a start is flagged if RT < L_c, the acceptance limit at championship c)
  P0  current                       L_c = 0.100 s
  P1  guard band                    L_c = 0.100 - g, g = k x u; u = descriptive.sd_championship_ms (REML SD of the
                                    athlete-adjusted championship offsets); k = 1.645 primary, 1 and 2 sensitivities
  P2  per-championship calibration  L_c = 0.100 + o-hat_c (the championship's estimated offset)
  P3  P2 + residual guard band      L_c = 0.100 + o-hat_c - k x se_c (se_c = SE of o-hat_c)

Metrics
  (a)  modelled rate of legitimate (gun-triggered) starts flagged, per 1,000, at each of the 18 championships: the
       fairness model (fairness_sim.p_fs; reference RT distribution shifted by the championship offset). Plug-in
       point; 95% CI over the 200 reference bootstrap fits x 25 redraws of the true offsets N(o-hat_c, se_c^2).
       Max, median, max/median fold, middle-half fold (75th / 25th percentile of the rates), cut vs P0.
  (b)  recorded false starts each policy would no longer flag, by championship; (b2) valid starts P2 / P3 would newly
       flag (slow-scoring championships).
  (c)  share of recorded false starts with an RT whose RT lies in [0.100 - g, 0.100) (cost proxy), with the count of
       recorded false starts with RT >= 0.100 - g at all.
  Verdict (fixed in the prereg): "PROTECTIVE AT LOW HISTORICAL COST" if max_P0 / max_P1 >= 10 and the (c) share
  <= 0.10 (men, ex-Gaussian, k = 1.645); otherwise the trade-off label says which criterion failed.

Recorded false starts (prereg deviation 1, appended to analysis/prereg_guardband.md). The recount reproduces
descriptive.json's is_fs exactly, but that classification counts (i) non-start DQs whose raw notes say "(not a false
start)" (the regex 'false.?start' in common.normalize_rt matches the phrase) and (ii) Fiore-file rows whose RT 0.000 is
a missing-value placeholder (DNS or DQ). (b) and (c) therefore use the corrected set "recorded false starts with a
measured RT"; the literal descriptive set and a note-fix-only set are reported as sensitivities.

Usage: .venv\\Scripts\\python.exe analysis\\guardband.py --seed 20260928 --descriptive analysis/outputs/descriptive.json
           --fairness analysis/outputs/fairness.json --offset-draws 25 --out analysis/outputs/guardband.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import (FS_THRESHOLD, add_common_args, attach_races, dedupe_sources, load_races, load_rt, num,
                    resolve_out, valid_rt_mask, wilson_ci, write_result)
from fairness_sim import p_fs                                   # the fairness model (read-only reuse)

# ---- design constants (analysis/prereg_guardband.md; not measurements) -------------------------------------------
T_MS = 1000.0 * FS_THRESHOLD                                    # 0.100 s
K_PRIMARY = 1.645                                               # WADA: one-sided 95% coverage
K_SENS = (1.0, 2.0)
CUT_BAR, SHARE_BAR = 10.0, 0.10                                 # decision rule
G_GRID_MS = np.round(np.arange(0.0, 30.0001, 0.5), 1)           # descriptive P1 trade-off curve
FAMILIES = ("exgauss", "slognorm", "swald")
PRIMARY_CELL = ("M", "exgauss")
SENS_CELLS = (("W", "exgauss"), ("M", "slognorm"), ("M", "swald"))
SENS_POLICIES = ("p0", "p1", "p2", "p3")
EPS_MS = 1e-9
NEAR_LO, NEAR_HI = 0.090, 0.0999                                # descriptive.py's near-threshold band (recount check)
YEAR_OFFICIAL, YEAR_ZERO_TOL = 2015, 2010                       # (c) breakdowns

LABEL_OK = "PROTECTIVE AT LOW HISTORICAL COST"
LABEL_I = "TRADE-OFF: PROTECTIVE BUT CHANGES MORE THAN 10% OF RECORDED FALSE STARTS"
LABEL_II = "TRADE-OFF: LOW HISTORICAL COST BUT CUTS THE MAXIMUM LESS THAN 10-FOLD"
LABEL_NONE = "TRADE-OFF: NEITHER CRITERION MET"

POLICY_DESC = {
    "p0": "P0 current rule (flag if RT < 0.100 s)",
    "p1": "P1 guard band, g = 1.645 x u (u = between-championship SD, REML)",
    "p1_k1": "P1 guard band, g = 1 x u",
    "p1_k2": "P1 guard band, g = 2 x u",
    "p1_u_ci_low": "P1 guard band, g = 1.645 x lower CI end of u",
    "p1_u_ci_high": "P1 guard band, g = 1.645 x upper CI end of u",
    "p1_u_mom": "P1 guard band, g = 1.645 x u_mom (moment SD of the 18 offsets net of their SEs)",
    "p1_u_raw": "P1 guard band, g = 1.645 x u_raw (SD of the 18 estimated offsets, not net)",
    "p1_u_comb": "P1 guard band, g = 1.645 x sqrt(u^2 + race SD^2)",
    "p2": "P2 per-championship calibration (limit shifted by the estimated offset)",
    "p3": "P3 = P2 + residual guard band 1.645 x se_c",
    "p3_k1": "P3 = P2 + residual guard band 1 x se_c",
    "p3_k2": "P3 = P2 + residual guard band 2 x se_c",
    "p3_umax": "P3 = P2 + common residual guard band 1.645 x max_c se_c (u_c,Max analogue)",
}
MAIN_TABLE_POLICIES = ("p0", "p1", "p1_k1", "p1_k2", "p2", "p3")
SET_DESC = {
    "meas": "recorded false starts with a measured RT (corrected: rows whose notes say 'not a false start' and the Fiore "
            "file's 0.000 RT placeholders removed) - primary (prereg deviation 1)",
    "note": "recorded false starts with an RT, corrected for the rows noted 'not a false start' only (Fiore 0.000 "
            "placeholders kept) - sensitivity",
    "desc": "recorded false starts with an RT as descriptive.py counts them (includes non-start DQs noted 'not a false "
            "start' and Fiore 0.000 RT placeholders) - the prereg's literal reading, an artefact",
}

ASSUMPTIONS = [
    "SIMULATION: every rate in (a) is a model output. Legitimate = gun-triggered; the reference RT distribution is fitted "
    "to valid championship starts (0.100-0.300 s, left-truncated) and extrapolated below 0.100 s; the family changes "
    "absolute rates several-fold (sensitivity cells).",
    "Championship offsets are the athlete-adjusted estimates of descriptive.json and act as pure location shifts of "
    "official RT (the fairness model's assumption). Their source is not identified; if part of an offset were genuine "
    "athlete behaviour, P2 would penalise or reward real behaviour.",
    "True anticipations are not observable. (b) and (c) count historically flagged starts: an upper bound on the "
    "anticipations a guard band would let through among them (some may have been legitimate); athletes' behavioural "
    "response to a new limit is not modelled.",
    "False-start data before 2015 come from Fiore et al.'s file, where a false start is visible only as an RT below "
    "0.100 s; from 2015 official labels (TR16.8) plus RT. Before 2010 a first false start did not disqualify "
    "(pre-2003: the athlete's own second; 2003-2009: charged to the field), so 'flagged' is not 'disqualified' then.",
    "P2 and P3 use the RT-based offset estimates and their SEs as a stand-in for an audit; a real audit would have its "
    "own uncertainty.",
    "CIs of (a) carry reference-fit and offset-estimation uncertainty only; g is a declared constant (uncertainty in u "
    "enters through the u sensitivities).",
    "The WADA decision limit is an analogy, not a transferred rule.",
]


def sig(x, n=4):
    """Round to n significant digits (stored values; the verdict is computed from these)."""
    x = float(x)
    return x if (x == 0 or not np.isfinite(x)) else float(f"{x:.{n}g}")


# =====================================================================================================
# helpers (unit-tested in analysis/tests/test_guardband.py)
# =====================================================================================================

def limit_dev_ms(policy: str, ohat_ms, se_ms, g_ms: float = 0.0, k: float = K_PRIMARY, u_res_ms=None) -> np.ndarray:
    """Acceptance limit of each championship as a deviation from 0.100 s, in ms (L_c = 0.100 s + d_c)."""
    ohat, se = np.asarray(ohat_ms, float), np.asarray(se_ms, float)
    if policy == "P0":
        return np.zeros_like(ohat)
    if policy == "P1":
        return np.full_like(ohat, -float(g_ms))
    if policy == "P2":
        return ohat.copy()
    if policy == "P3":
        res = se if u_res_ms is None else np.full_like(se, float(u_res_ms))
        return ohat - float(k) * res
    raise ValueError(policy)


def flag_prob(family: str, params: dict, d_ms, true_off_ms) -> np.ndarray:
    """P(a legitimate start is flagged) = F_R(L - o) = fairness_sim.p_fs with shift o - d (seconds)."""
    shift_s = (np.asarray(true_off_ms, float) - np.asarray(d_ms, float)) / 1000.0
    return np.asarray(p_fs(family, params, shift_s), float)


def is_flagged(rt_s, d_ms) -> np.ndarray:
    """Flag if RT < 0.100 s + d, comparing the RT on its 0.001 s grid."""
    r = np.round(np.asarray(rt_s, float) * 1000.0)
    return r < T_MS + np.asarray(d_ms, float) - EPS_MS


def summarise(rates) -> dict:
    """Summaries over championships (last axis): max, argmax, median, max/median, 75th/25th percentile."""
    r = np.asarray(rates, float)
    mx, med = r.max(-1), np.median(r, -1)
    q25, q75 = np.percentile(r, [25, 75], axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        f_mm = np.where(med > 0, mx / np.where(med > 0, med, 1.0), np.inf)
        f_iqr = np.where(q25 > 0, q75 / np.where(q25 > 0, q25, 1.0), np.inf)
    return {"max": mx, "argmax": r.argmax(-1), "median": med, "q25": q25, "q75": q75,
            "fold_max_median": f_mm, "fold_iqr": f_iqr}


def ratio(a, b) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / np.where(b > 0, b, 1.0), np.inf)


def pct_ci(x) -> list | None:
    """95% percentile interval; infinite draws are kept as +inf (stored as null)."""
    x = np.asarray(x, float)
    x = np.where(np.isfinite(x), x, 1e300)
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [sig(lo) if lo < 1e299 else None, sig(hi) if hi < 1e299 else None]


def verdict(cut_max: float, share: float) -> str:
    """The pre-registered decision rule."""
    c1, c2 = cut_max >= CUT_BAR, share <= SHARE_BAR
    if c1 and c2:
        return LABEL_OK
    if c1:
        return LABEL_I
    if c2:
        return LABEL_II
    return LABEL_NONE


def unflagged(rt_s, d_ms) -> np.ndarray:
    """Recorded false starts flagged by the current RT rule (RT < 0.100) but not under limit d."""
    return is_flagged(rt_s, 0.0) & ~is_flagged(rt_s, d_ms)


def newly_flagged(rt_s, d_ms) -> np.ndarray:
    """Starts not flagged by the current RT rule but flagged under limit d (only possible when d > 0)."""
    return ~is_flagged(rt_s, 0.0) & is_flagged(rt_s, d_ms)


# =====================================================================================================

NOT_FS_NOTE = "not a false start"


def athlete_key(s: pd.Series) -> pd.Series:
    """The athlete identifier exactly as common.normalize_rt builds it (str, stripped, upper case)."""
    return s.map(lambda z: str(z).strip().upper(), na_action="ignore")


def classify_records(rt: pd.DataFrame, raw_athletes: pd.DataFrame) -> dict:
    """Masks over the normalised RT table.

    fs_desc   descriptive.py's is_fs (RT < 0.100 or a false-start regex match on the status/notes text)
    mis_note  rows whose raw notes say 'not a false start' (non-start DQs: hurdle and lane rules); the regex
              'false.?start' in common.normalize_rt matches that phrase, so descriptive.py counts them as false starts
    ph        RT exactly 0.000 in the Fiore file: a placeholder for a missing RT (the rows are DNS or DQ)
    ph_dns    placeholders whose Fiore result is DNS (not a start)
    fs_corr   recorded false starts, corrected: fs_desc minus mis_note minus ph_dns
    fs_meas   corrected false starts with a measured RT (placeholders excluded): the (b)/(c) primary set
    fs_note   fs_desc minus mis_note, with an RT (placeholders kept): the 'note fix only' sensitivity
    """
    keys = set(zip(raw_athletes.loc[raw_athletes["notes"].fillna("").astype(str).str.contains(
        NOT_FS_NOTE, case=False, regex=False), "race_id"].astype(str),
        athlete_key(raw_athletes.loc[raw_athletes["notes"].fillna("").astype(str).str.contains(
            NOT_FS_NOTE, case=False, regex=False), "athlete_id"])))
    k = pd.Series(list(zip(rt["race_id"].astype(str), rt["athlete"].astype(object))), index=rt.index)
    mis = (rt["source"] == "rt_athletes") & k.isin(keys)
    fs_desc = rt["is_fs"].fillna(False).astype(bool)
    has_rt = rt["rt_s"].notna()
    ph = (rt["source"] == "rt_fiore") & (rt["rt_s"] == 0.0)
    ph_dns = ph & rt["result"].astype(str).str.strip().str.upper().eq("DNS")
    fs_corr = fs_desc & ~mis & ~ph_dns
    return {"fs_desc": fs_desc, "mis_note": mis, "ph": ph, "ph_dns": ph_dns, "fs_corr": fs_corr,
            "fs_meas": fs_corr & has_rt & ~ph, "fs_note": fs_desc & ~mis & has_rt, "fs_desc_rt": fs_desc & has_rt,
            "n_raw_not_fs_notes": len(keys)}


def load_records(desc: dict):
    """Starts, recorded false starts and valid starts as descriptive.py defines them (the recount must reproduce
    descriptive.json, else stop), plus the corrected classification of classify_records."""
    rt, used = load_rt(False)
    races, rused = load_races(False)
    rt = attach_races(dedupe_sources(rt), races)
    rt["valid"] = valid_rt_mask(rt)
    started = rt[rt["rt_s"].notna() | rt["is_fs"]].copy()
    fs = started[started["is_fs"].astype(bool)].copy()
    fs_rt = fs[fs["rt_s"].notna()].copy()
    v = rt[rt["valid"]].copy()
    nd = desc["numbers"]
    near = fs_rt["rt_s"].between(NEAR_LO, NEAR_HI)
    problems = []
    if len(fs) != int(nd["fs_per_1000_starts"]["n_fs"]) or len(started) != int(nd["fs_per_1000_starts"]["n_starts"]):
        problems.append("false starts / starts")
    if len(fs_rt) != int(nd["fs_recorded_with_rt"]["value"]):
        problems.append("false starts with an RT")
    if int(near.sum()) != int(nd["fs_near_threshold_090_100"]["value"]):
        problems.append("near-threshold total")
    by = {str(k): int(x) for k, x in fs_rt[near].groupby("comp_year").size().items()}
    if by != {str(k): int(x) for k, x in nd["fs_near_threshold_090_100"]["by_meet"].items()}:
        problems.append("near-threshold by championship")
    if len(v) != int(nd["n_valid"]["value"]):
        problems.append("valid starts")
    if problems:
        raise SystemExit(f"record recount does not reproduce descriptive.json: {problems}")
    raw_path = [p for p in used if Path(p).name == "rt_athletes.csv"][0]
    raw = pd.read_csv(raw_path, encoding="utf-8-sig", low_memory=False)
    m = classify_records(rt, raw)
    mis = m["mis_note"]
    # consistency of the correction: every 'not a false start' row is found once, none has RT < 0.100 or an FS status
    bad = []
    if int(mis.sum()) != m["n_raw_not_fs_notes"]:
        bad.append(f"'not a false start' rows matched {int(mis.sum())} of {m['n_raw_not_fs_notes']}")
    if bool((mis & (rt["rt_s"] < FS_THRESHOLD)).any()):
        bad.append("a 'not a false start' row has RT < 0.100 s")
    if bool((mis & rt["status"].fillna("").astype(str).str.contains(r"\bFS\b", regex=True)).any()):
        bad.append("a 'not a false start' row has status FS")
    if bad:
        raise SystemExit(f"false-start correction inconsistent: {bad}")
    rt["started_corr"] = (rt["rt_s"].notna() | rt["is_fs"]) & ~m["ph_dns"]
    rt["valid_corr"] = (rt["rt_s"].between(FS_THRESHOLD, 0.300) & ~m["fs_corr"]
                        & ~rt["is_dns"].fillna(False).astype(bool))
    return rt, m, started, fs, fs_rt, v, used + rused


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--descriptive", required=True)
    ap.add_argument("--fairness", required=True, help="fairness.json: P0 must reproduce its 'meets' table")
    ap.add_argument("--offset-draws", type=int, default=25, help="offset redraws per reference bootstrap fit")
    args = ap.parse_args()
    if args.mock:
        raise SystemExit("guardband.py has no mock mode (it reads only registered real outputs)")
    out = resolve_out(args, "guardband")
    desc = json.loads(Path(args.descriptive).read_text(encoding="utf-8"))
    fair = json.loads(Path(args.fairness).read_text(encoding="utf-8"))
    for nm, d in (("descriptive", desc), ("fairness", fair)):
        if d.get("mock"):
            raise SystemExit(f"{nm} input is MOCK")
    nd, ref = desc["numbers"], desc["extra"]["reference_fits"]
    me = pd.DataFrame(desc["tables"]["meet_effects"])[["comp_year", "deviation_ms", "se", "n"]]
    me = me.sort_values("comp_year").reset_index(drop=True)
    champs = me["comp_year"].tolist()
    ci_of = {c: i for i, c in enumerate(champs)}
    ohat, se = me["deviation_ms"].to_numpy(float), me["se"].to_numpy(float)
    numbers, tables = {}, {}
    extra = {"prereg": "analysis/prereg_guardband.md", "assumptions": ASSUMPTIONS,
             "design_constants": {"threshold_s": FS_THRESHOLD, "k_primary": K_PRIMARY, "k_sensitivity": list(K_SENS),
                                  "cut_bar": CUT_BAR, "share_bar": SHARE_BAR, "offset_draws": args.offset_draws,
                                  "g_grid_ms": [float(G_GRID_MS[0]), float(G_GRID_MS[-1]), 0.5],
                                  "primary_cell": list(PRIMARY_CELL), "championships": champs}}

    # ---- u and g ---------------------------------------------------------------------------------------------------
    u = float(nd["sd_championship_ms"]["value"])
    u_lo, u_hi = (float(x) for x in nd["sd_championship_ms"]["ci95"])
    sd_race = float(nd["sd_race_ms"]["value"])
    u_mom = float(np.sqrt(max(0.0, ohat.var(ddof=1) - float(np.mean(se ** 2)))))
    u_raw = float(ohat.std(ddof=1))
    u_comb = float(np.sqrt(u ** 2 + sd_race ** 2))
    u_res_max = float(se.max())
    g = {"p1": K_PRIMARY * u, "p1_k1": 1.0 * u, "p1_k2": 2.0 * u, "p1_u_ci_low": K_PRIMARY * u_lo,
         "p1_u_ci_high": K_PRIMARY * u_hi, "p1_u_mom": K_PRIMARY * u_mom, "p1_u_raw": K_PRIMARY * u_raw,
         "p1_u_comb": K_PRIMARY * u_comb}
    u_of = {"p1": u, "p1_k1": u, "p1_k2": u, "p1_u_ci_low": u_lo, "p1_u_ci_high": u_hi, "p1_u_mom": u_mom,
            "p1_u_raw": u_raw, "p1_u_comb": u_comb}
    k_of = {"p1": K_PRIMARY, "p1_k1": 1.0, "p1_k2": 2.0}
    numbers["u_ms"] = num(sig(u), ci=(sig(u_lo), sig(u_hi)), unit="ms",
                          desc="u (primary): between-championship SD of athlete-adjusted RT offsets = "
                               "descriptive.sd_championship_ms (REML random-intercept SD; net of estimation error by "
                               "construction)", source="descriptive.sd_championship_ms")
    numbers["u_mom_ms"] = num(sig(u_mom), unit="ms", desc="u sensitivity: sqrt(var(offset estimates) - mean(SE^2)) over "
                                                          "the 18 athlete-adjusted offsets (moment estimator, net)")
    numbers["u_raw_ms"] = num(sig(u_raw), unit="ms", desc="u sensitivity: SD of the 18 estimated offsets (not net)")
    numbers["u_comb_ms"] = num(sig(u_comb), unit="ms", desc="u sensitivity: sqrt(u^2 + race SD^2) (adds the "
                                                            "between-race component)", sd_race_ms=sig(sd_race))
    numbers["u_res_max_ms"] = num(sig(u_res_max), unit="ms", desc="largest SE of a championship offset estimate "
                                                                  "(P3 common residual u_c,Max analogue)",
                                  champ=champs[int(np.argmax(se))])
    for s, gv in g.items():
        key = "g_ms" if s == "p1" else f"g_ms_{s[3:]}"
        lim = FS_THRESHOLD - gv / 1000.0
        eff = float(np.ceil(round(lim * 1000.0, 9)) / 1000.0)
        numbers[key] = num(sig(gv), unit="ms", desc=f"guard band g = k x u: {POLICY_DESC[s]}",
                           k=k_of.get(s, K_PRIMARY), u_ms=sig(u_of[s]), limit_s=sig(lim, 6),
                           limit_effective_s=round(eff, 3),
                           note="effective limit = smallest recorded RT (0.001 s grid) that is not flagged")

    pol = {"p0": ("P0", {}), **{s: ("P1", {"g_ms": gv}) for s, gv in g.items()},
           "p2": ("P2", {}), "p3": ("P3", {"k": K_PRIMARY}), "p3_k1": ("P3", {"k": 1.0}),
           "p3_k2": ("P3", {"k": 2.0}), "p3_umax": ("P3", {"k": K_PRIMARY, "u_res_ms": u_res_max})}
    dev = {s: limit_dev_ms(p, ohat, se, **kw) for s, (p, kw) in pol.items()}

    # ---- (a) modelled legitimate-flag rates ------------------------------------------------------------------------
    rng = np.random.default_rng(args.seed + 701)
    n_ref = len(ref["M_exgauss"]["boot_params"])
    z = rng.standard_normal((n_ref, args.offset_draws, len(champs)))
    o_star = ohat + se * z                                                   # true offsets, (n_ref, D, 18)

    def cell(sex, fam, slugs):
        p0, draws = ref[f"{sex}_{fam}"]["params"], ref[f"{sex}_{fam}"]["boot_params"]
        if len(draws) != n_ref:
            raise SystemExit(f"{sex}_{fam}: {len(draws)} bootstrap fits, expected {n_ref}")
        pt, bd = {}, {}
        for s in slugs:
            pt[s] = 1000.0 * flag_prob(fam, p0, dev[s], ohat)
            bd[s] = np.stack([1000.0 * flag_prob(fam, bp, dev[s], o_star[i])
                              for i, bp in enumerate(draws)]).reshape(-1, len(champs))
        return pt, bd

    # P0 must reproduce fairness.json 'meets' for every sex x family
    fm = pd.DataFrame(fair["tables"]["meets"])
    worst = 0.0
    for sex in ("M", "W"):
        for fam in FAMILIES:
            sub = fm[(fm["sex"] == sex) & (fm["family"] == fam)].set_index("comp_year")["p_median_hold"]
            mine = flag_prob(fam, ref[f"{sex}_{fam}"]["params"], dev["p0"], ohat)
            for c, x in zip(champs, mine):
                rel_d = abs(x - sub[c]) / max(abs(sub[c]), 1e-300)
                worst = max(worst, rel_d if sub[c] > 1e-12 else abs(x - sub[c]))
    if worst > 1e-4:
        raise SystemExit(f"P0 does not reproduce fairness.json meets (worst relative difference {worst:.3g})")
    extra["check_p0_vs_fairness_meets_max_rel_diff"] = sig(worst, 3)

    pt, bd = cell(*PRIMARY_CELL, list(pol))
    S_pt = {s: summarise(pt[s]) for s in pol}
    S_bd = {s: summarise(bd[s]) for s in pol}
    fmax = fair["numbers"]["meet_p_max_M"]
    if champs[int(S_pt["p0"]["argmax"])] != fmax["meet"] or abs(S_pt["p0"]["max"] - 1000 * fmax["value"]) > 1e-3 * 1000 * fmax["value"]:
        raise SystemExit("P0 maximum does not reproduce fairness.json meet_p_max_M")
    q25o, q75o = np.percentile(ohat, [25, 75])
    pr0 = ref["M_exgauss"]["params"]
    iqr_off = float(p_fs("exgauss", pr0, q25o / 1000) / p_fs("exgauss", pr0, q75o / 1000))
    if abs(iqr_off - fair["numbers"]["meet_iqr_fold_change"]["value"]) > 1e-3 * iqr_off:
        raise SystemExit("offset-percentile middle-half fold does not reproduce fairness.json meet_iqr_fold_change")

    def champ_of(s):
        r = pt[s]
        if np.ptp(r) <= 1e-9 * max(r.max(), 1e-300):
            return "all equal (plug-in)"
        return champs[int(S_pt[s]["argmax"])]

    sim = " (SIMULATION; men, ex-Gaussian reference shifted by the championship offset; plug-in point, CI over " \
          "reference bootstrap fits x offset redraws; for P2/P3 the plug-in assumes exact offset estimates, so the " \
          "point can lie outside the CI; draw_median = median over the draws)"
    for s in pol:
        a, b = S_pt[s], S_bd[s]
        numbers[f"a_{s}_max_per1000"] = num(sig(a["max"]), ci=pct_ci(b["max"]), unit="per 1,000 starts",
                                            draw_median=sig(np.median(b["max"])),
                                            desc=f"(a) highest modelled rate of legitimate starts flagged across 18 "
                                                 f"championships, {POLICY_DESC[s]}{sim}", champ=champ_of(s))
        numbers[f"a_{s}_median_per1000"] = num(sig(a["median"]), ci=pct_ci(b["median"]), unit="per 1,000 starts",
                                               draw_median=sig(np.median(b["median"])),
                                               desc=f"(a) median over 18 championships of the modelled legitimate-flag "
                                                    f"rate, {POLICY_DESC[s]}{sim}")
        numbers[f"a_{s}_fold_max_median"] = num(sig(a["fold_max_median"]), ci=pct_ci(b["fold_max_median"]),
                                                draw_median=sig(np.median(b["fold_max_median"])),
                                                desc=f"(a) max / median modelled legitimate-flag rate across 18 "
                                                     f"championships, {POLICY_DESC[s]}{sim}")
        numbers[f"a_{s}_fold_iqr"] = num(sig(a["fold_iqr"]), ci=pct_ci(b["fold_iqr"]),
                                         desc=f"(a) middle-half fold: 75th / 25th percentile of the 18 championship "
                                              f"rates, {POLICY_DESC[s]}{sim}")
        if s != "p0":
            numbers[f"a_{s}_cut_max"] = num(sig(ratio(S_pt["p0"]["max"], a["max"])),
                                            ci=pct_ci(ratio(S_bd["p0"]["max"], b["max"])),
                                            draw_median=sig(np.median(ratio(S_bd["p0"]["max"], b["max"]))),
                                            desc=f"(a) fold cut of the highest modelled legitimate-flag rate, P0 max / "
                                                 f"policy max, {POLICY_DESC[s]}{sim}")
            numbers[f"a_{s}_cut_median"] = num(sig(ratio(S_pt["p0"]["median"], a["median"])),
                                               ci=pct_ci(ratio(S_bd["p0"]["median"], b["median"])),
                                               desc=f"(a) fold cut of the median modelled legitimate-flag rate, P0 / "
                                                    f"policy, {POLICY_DESC[s]}{sim}")
    # offset-percentile middle-half fold (fairness.json's definition), for P0 (= fairness) and P1 (uniform shift)
    for s in ("p0", "p1"):
        val = float(p_fs("exgauss", pr0, (q25o - dev[s][0]) / 1000) / p_fs("exgauss", pr0, (q75o - dev[s][0]) / 1000))
        numbers[f"a_{s}_fold_iqr_offsetq"] = num(sig(val), desc=f"(a) supplementary: rate at the 25th vs 75th percentile "
                                                                f"championship offset ({q25o:.1f} vs {q75o:.1f} ms), "
                                                                f"fairness.json's definition, {POLICY_DESC[s]}{sim}")
    ref_rate = 1000.0 * float(p_fs("exgauss", pr0, 0.0))
    numbers["a_ref_rate_per1000"] = num(sig(ref_rate), unit="per 1,000 starts",
                                        desc="(a) modelled rate at an average championship (offset 0) under P0 = the "
                                             "P2 plug-in rate at every championship (men, ex-Gaussian; SIMULATION)")

    # sensitivity cells (women; men shifted lognormal / shifted Wald)
    sens_rows = []
    cells = {PRIMARY_CELL: (pt, bd)}
    for sex, fam in SENS_CELLS:
        cells[(sex, fam)] = cell(sex, fam, SENS_POLICIES)
    for (sex, fam), (cpt, cbd) in cells.items():
        sp = {s: summarise(cpt[s]) for s in SENS_POLICIES}
        sb = {s: summarise(cbd[s]) for s in SENS_POLICIES}
        for s in SENS_POLICIES:
            row = {"sex": sex, "family": fam, "policy": s, "max_per1000": float(sp[s]["max"]),
                   "max_champ": champs[int(sp[s]["argmax"])] if np.ptp(cpt[s]) > 1e-9 * max(cpt[s].max(), 1e-300)
                   else "all equal (plug-in)",
                   "median_per1000": float(sp[s]["median"]), "fold_max_median": float(sp[s]["fold_max_median"]),
                   "cut_max": float(ratio(sp["p0"]["max"], sp[s]["max"])) if s != "p0" else 1.0}
            lo_hi = pct_ci(sb[s]["max"])
            row.update({"max_lo": lo_hi[0], "max_hi": lo_hi[1]})
            sens_rows.append(row)
            if (sex, fam) == PRIMARY_CELL:
                continue
            tag = f"s_{sex}_{fam}_{s}"
            lab = f"sex={sex}, {fam} reference (sensitivity; SIMULATION)"
            numbers[f"{tag}_max_per1000"] = num(sig(sp[s]["max"]), ci=pct_ci(sb[s]["max"]), unit="per 1,000 starts",
                                                desc=f"(a) highest modelled legitimate-flag rate, {POLICY_DESC[s]}, {lab}",
                                                champ=row["max_champ"])
            numbers[f"{tag}_median_per1000"] = num(sig(sp[s]["median"]), ci=pct_ci(sb[s]["median"]),
                                                   unit="per 1,000 starts",
                                                   desc=f"(a) median modelled legitimate-flag rate, {POLICY_DESC[s]}, {lab}")
            numbers[f"{tag}_fold_max_median"] = num(sig(sp[s]["fold_max_median"]), ci=pct_ci(sb[s]["fold_max_median"]),
                                                    desc=f"(a) max / median modelled rate, {POLICY_DESC[s]}, {lab}")
            if s != "p0":
                numbers[f"{tag}_cut_max"] = num(sig(ratio(sp["p0"]["max"], sp[s]["max"])),
                                                ci=pct_ci(ratio(sb["p0"]["max"], sb[s]["max"])),
                                                desc=f"(a) P0 max / policy max, {POLICY_DESC[s]}, {lab}")
    tables["sensitivity_cells"] = pd.DataFrame(sens_rows)

    # ---- (b), (b2), (c) records ------------------------------------------------------------------------------------
    rt, m, started, fs, fs_rt_desc, v_desc, rec_inputs = load_records(desc)
    missing = sorted(set(started["comp_year"]) - set(champs))
    if missing:
        raise SystemExit(f"championships with starts but no offset: {missing}")
    sets = {"meas": m["fs_meas"], "note": m["fs_note"], "desc": m["fs_desc_rt"]}
    fs_rt = rt[sets["desc"]].sort_values(["comp_year", "rt_s", "race_id"]).copy()       # superset of the other sets
    fs_ci = fs_rt["comp_year"].map(ci_of).to_numpy(int)
    rt_fs = fs_rt["rt_s"].to_numpy(float)
    in_set = {k: sets[k].loc[fs_rt.index].to_numpy(bool) for k in sets}
    n_set = {k: int(in_set[k].sum()) for k in sets}
    n_meas = n_set["meas"]
    st_corr = rt["started_corr"]
    n_corr = int(m["fs_corr"].sum())
    numbers["b_n_fs_total"] = num(n_corr, desc="recorded false starts, corrected: descriptive.py's is_fs minus rows "
                                               "whose notes say 'not a false start' and minus DNS rows carrying a 0.000 "
                                               "RT placeholder (Fiore file)", n_starts=int(st_corr.sum()),
                                  per_1000_starts=sig(1000.0 * n_corr / int(st_corr.sum())))
    numbers["b_n_fs_with_rt"] = num(n_meas, desc="(b)/(c) primary denominator: " + SET_DESC["meas"])
    numbers["b_n_fs_no_rt"] = num(n_corr - n_meas, desc="corrected recorded false starts without a measured RT (no "
                                                        "RT-based policy can evaluate them; includes Fiore DQ rows "
                                                        "with a 0.000 placeholder)")
    numbers["b_n_fs_note_with_rt"] = num(n_set["note"], desc="(c) sensitivity denominator: " + SET_DESC["note"])
    numbers["b_n_fs_desc_with_rt"] = num(n_set["desc"], desc="descriptive.json fs_recorded_with_rt (recounted): "
                                                             + SET_DESC["desc"])
    numbers["b_n_fs_desc_total"] = num(int(len(fs)), desc="descriptive.json recorded false starts n_fs (recounted)",
                                       n_starts=int(len(started)))
    mis_fs = m["mis_note"] & m["fs_desc"]
    numbers["b_n_misclassified_not_fs_note"] = num(
        int(mis_fs.sum()), desc="rows counted as false starts by descriptive.py although their raw notes say 'not a "
                                "false start' (non-start DQs such as TR22.6 hurdles or 163.3(a) lane): the regex "
                                "'false.?start' in common.normalize_rt matches the phrase (upstream issue)",
        with_rt=int((mis_fs & rt["rt_s"].notna()).sum()), raw_rows_with_note=int(m["n_raw_not_fs_notes"]))
    numbers["b_n_fiore_rt0_placeholders"] = num(
        int((m["ph"] & m["fs_desc"]).sum()), desc="Fiore-file rows with RT 0.000 (a missing-RT placeholder; their "
                                                  "result is DNS or DQ) counted as false starts with an RT by "
                                                  "descriptive.py (upstream issue)",
        dns=int((m["ph_dns"] & m["fs_desc"]).sum()))
    numbers["b_n_fs_rt_ge_100"] = num(int((~is_flagged(rt_fs, 0.0) & in_set["meas"]).sum()),
                                      desc="primary-set false starts whose measured RT is >= 0.100 s (flagged by "
                                           "label, not by the RT rule; unchanged by every policy here)")
    fs_tab = fs_rt[["comp_year", "race_id", "sex", "athlete", "rt_s", "source", "status"]].copy()
    fs_tab["result"] = fs_rt["result"].astype(str)
    fs_tab["in_primary_set"] = in_set["meas"]
    fs_tab["noted_not_a_false_start"] = m["mis_note"].loc[fs_rt.index].to_numpy(bool)
    fs_tab["fiore_rt0_placeholder"] = m["ph"].loc[fs_rt.index].to_numpy(bool)
    fs_tab["flagged_by_rt_rule"] = is_flagged(rt_fs, 0.0)
    vc = rt[rt["valid_corr"]]
    v_ci = vc["comp_year"].map(ci_of).to_numpy(int)
    rt_v = vc["rt_s"].to_numpy(float)
    vd_ci = v_desc["comp_year"].map(ci_of).to_numpy(int)
    unfl, newf = {}, {}
    for s in pol:
        if s == "p0":
            continue
        u_all = unflagged(rt_fs, dev[s][fs_ci])
        fs_tab[f"unflagged_{s}"] = u_all
        unfl[s] = u_all & in_set["meas"]
        cnt = pd.Series(unfl[s], index=fs_rt.index).groupby(fs_rt["comp_year"]).sum()
        by = {c: int(x) for c, x in cnt.items() if x > 0}
        k_ = int(unfl[s].sum())
        lo_, hi_ = wilson_ci(k_, n_meas)
        numbers[f"b_{s}_n_unflagged"] = num(k_, desc=f"(b) recorded false starts with a measured RT that would no "
                                                     f"longer be flagged, {POLICY_DESC[s]} (records)",
                                            by_champ=by, n_fs_with_rt=n_meas, share=sig(k_ / n_meas),
                                            share_ci95=[sig(lo_), sig(hi_)],
                                            n_unflagged_in_descriptive_set=int((u_all & in_set["desc"]).sum()))
        if s.startswith(("p2", "p3")):
            nf = newly_flagged(rt_v, dev[s][v_ci])
            newf[s] = nf
            nf_d = int(newly_flagged(v_desc["rt_s"].to_numpy(float), dev[s][vd_ci]).sum())
            cnt = pd.Series(nf).groupby(vc["comp_year"].to_numpy()).sum()
            by = {c: int(x) for c, x in cnt.items() if x > 0}
            numbers[f"b2_{s}_n_newly_flagged"] = num(int(nf.sum()), desc=f"(b2) legal starts (RT 0.100-0.300 s, not a "
                                                                         f"false start, corrected classification) that "
                                                                         f"would be newly flagged at slow-scoring "
                                                                         f"championships, {POLICY_DESC[s]} (records)",
                                                     by_champ=by, n_valid=int(len(vc)),
                                                     per_1000_valid=sig(1000.0 * nf.sum() / len(vc)),
                                                     n_in_descriptive_valid_set=nf_d, n_valid_descriptive=int(len(v_desc)))
    tables["false_starts"] = fs_tab

    # (c) cost proxy for P1 (primary and sensitivities)
    yr = fs_rt["comp_year"].str[-4:].astype(int).to_numpy()
    for s in g:
        key = "c" if s == "p1" else f"c_{s[3:]}"
        u_all = fs_tab[f"unflagged_{s}"].to_numpy(bool)
        k_ = int((u_all & in_set["meas"]).sum())
        lo_, hi_ = wilson_ci(k_, n_meas)
        lim = FS_THRESHOLD - g[s] / 1000.0
        n_ge = int((~is_flagged(rt_fs, -g[s]) & in_set["meas"]).sum())
        fields = {"band_s": [sig(lim, 6), FS_THRESHOLD], "count": k_, "n_fs_with_rt": n_meas,
                  "n_fs_rt_ge_limit": n_ge, "g_ms": sig(g[s])}
        if s == "p1":
            for lab, y0 in (("2015on", YEAR_OFFICIAL), ("2010on", YEAR_ZERO_TOL)):
                msk = in_set["meas"] & (yr >= y0)
                kk, nn = int((u_all & msk).sum()), int(msk.sum())
                l2, h2 = wilson_ci(kk, nn)
                numbers[f"c_share_band_{lab}"] = num(sig(kk / nn) if nn else None, ci=(sig(l2), sig(h2)),
                                                     desc=f"(c) breakdown: share of primary-set false starts from {y0} "
                                                          f"on whose RT lies in [0.100 - g, 0.100), P1 primary (Wilson "
                                                          f"CI; records)", count=kk, n_fs_with_rt=nn)
            for sk in ("note", "desc"):
                kk, nn = int((u_all & in_set[sk]).sum()), n_set[sk]
                l2, h2 = wilson_ci(kk, nn)
                numbers[f"c_share_band_{sk}"] = num(sig(kk / nn), ci=(sig(l2), sig(h2)),
                                                    desc=f"(c) sensitivity, P1 primary: share in [0.100 - g, 0.100) "
                                                         f"with the denominator {SET_DESC[sk]} (Wilson CI)",
                                                    count=kk, n_fs_with_rt=nn)
        numbers[f"{key}_share_band"] = num(sig(k_ / n_meas), ci=(sig(lo_), sig(hi_)),
                                           desc=f"(c) cost proxy: share of recorded false starts with a measured RT "
                                                f"whose RT lies in [0.100 - g, 0.100), {POLICY_DESC[s]} (Wilson CI; "
                                                f"records)", **fields)
        numbers[f"{key}_n_fs_ge_limit"] = num(n_ge, desc=f"(c) recorded false starts with a measured RT >= 0.100 - g "
                                                         f"at all (including any at or above 0.100 s), "
                                                         f"{POLICY_DESC[s]}", g_ms=sig(g[s]), n_fs_with_rt=n_meas)

    # ---- verdict (primary) and the rule applied to the sensitivity cells (descriptive) --------------------------------
    cut_p1, share_p1 = numbers["a_p1_cut_max"]["value"], numbers["c_share_band"]["value"]
    lo_cut = numbers["a_p1_cut_max"]["ci95"][0]
    sens_v = {}
    for s in g:
        if s == "p1":
            continue
        sens_v[s] = verdict(numbers[f"a_{s}_cut_max"]["value"], numbers[f"c_{s[3:]}_share_band"]["value"])
    for sex, fam in SENS_CELLS:
        sens_v[f"{sex}_{fam}"] = verdict(numbers[f"s_{sex}_{fam}_p1_cut_max"]["value"], share_p1)
    numbers["verdict"] = num(verdict(cut_p1, share_p1),
                             desc="pre-registered verdict (analysis/prereg_guardband.md): PROTECTIVE AT LOW HISTORICAL "
                                  "COST if the P1 guard band (k = 1.645, u = between-championship SD; men, ex-Gaussian) "
                                  "cuts the highest modelled legitimate-flag rate >= 10-fold AND changes <= 10% of "
                                  "recorded false starts with a measured RT; otherwise the trade-off label. Primary "
                                  "denominator = corrected classification (prereg deviation 1)",
                             cut_max=cut_p1, share_changed=share_p1, crit_cut_ge_10=bool(cut_p1 >= CUT_BAR),
                             crit_share_le_010=bool(share_p1 <= SHARE_BAR),
                             cut_ci_low_ge_10=bool(lo_cut is not None and lo_cut >= CUT_BAR),
                             cut_ci95=numbers["a_p1_cut_max"]["ci95"], g_ms=numbers["g_ms"]["value"],
                             reading_note_fix_only=verdict(cut_p1, numbers["c_share_band_note"]["value"]),
                             reading_descriptive_definition=verdict(cut_p1, numbers["c_share_band_desc"]["value"]),
                             reading_descriptive_definition_note="artefact: its denominator counts 32 non-start DQs "
                                                                 "noted 'not a false start' and 5 Fiore 0.000 RT "
                                                                 "placeholders as false starts; not to be quoted",
                             sensitivity_verdicts=sens_v)

    # ---- tables: per championship; P1 trade-off curve --------------------------------------------------------------
    rows = []
    for i, c in enumerate(champs):
        in_c = fs_ci == i
        row = {"comp_year": c, "offset_ms": ohat[i], "se_ms": se[i], "n_valid_model": int(me.loc[i, "n"]),
               "starts_corr": int((st_corr & (rt["comp_year"] == c)).sum()),
               "fs_corr": int((m["fs_corr"] & (rt["comp_year"] == c)).sum()),
               "fs_meas_rt": int((in_set["meas"] & in_c).sum()), "fs_desc": int((fs["comp_year"] == c).sum())}
        for s in MAIN_TABLE_POLICIES:
            row[f"limit_s_{s}"] = FS_THRESHOLD + dev[s][i] / 1000.0
            row[f"rate_{s}"] = pt[s][i]
            row[f"rate_{s}_lo"], row[f"rate_{s}_hi"] = np.percentile(bd[s][:, i], [2.5, 97.5])
            if s != "p0":
                row[f"unflagged_{s}"] = int(unfl[s][in_c].sum())
            if s in newf:
                row[f"newly_flagged_{s}"] = int(newf[s][v_ci == i].sum())
        rows.append(row)
    tables["championships"] = pd.DataFrame(rows)
    curve = []
    for gv in G_GRID_MS:
        d = limit_dev_ms("P1", ohat, se, g_ms=float(gv))
        r = 1000.0 * flag_prob("exgauss", pr0, d, ohat)
        sm = summarise(r)
        k_ = int((unflagged(rt_fs, d[fs_ci]) & in_set["meas"]).sum())
        curve.append({"g_ms": float(gv), "limit_s": FS_THRESHOLD - gv / 1000.0, "max_per1000": float(sm["max"]),
                      "max_champ": champs[int(sm["argmax"])], "median_per1000": float(sm["median"]),
                      "fold_max_median": float(sm["fold_max_median"]),
                      "cut_max": float(ratio(S_pt["p0"]["max"], sm["max"])), "fs_unflagged": k_,
                      "share_unflagged": k_ / n_meas})
    tables["tradeoff_p1"] = pd.DataFrame(curve)
    cv = tables["tradeoff_p1"]
    ok_cut = cv[cv["cut_max"] >= CUT_BAR]
    ok_share = cv[cv["share_unflagged"] <= SHARE_BAR]
    both = cv[(cv["cut_max"] >= CUT_BAR) & (cv["share_unflagged"] <= SHARE_BAR)]
    r_cut, r_share = ok_cut.iloc[0], ok_share.iloc[-1]
    numbers["curve_g_min_cut10_ms"] = num(float(r_cut["g_ms"]), unit="ms",
                                          desc="P1 trade-off curve (descriptive; 0.5 ms grid): smallest g whose cut of "
                                               "the highest modelled legitimate-flag rate is >= 10-fold (men, "
                                               "ex-Gaussian; SIMULATION) and the share of recorded false starts it "
                                               "changes", cut_max=sig(r_cut["cut_max"]), share=sig(r_cut["share_unflagged"]),
                                          fs_unflagged=int(r_cut["fs_unflagged"]))
    numbers["curve_g_max_share010_ms"] = num(float(r_share["g_ms"]), unit="ms",
                                             desc="P1 trade-off curve (descriptive; 0.5 ms grid): largest g that changes "
                                                  "<= 10% of recorded false starts with a measured RT, and its cut "
                                                  "(SIMULATION for the cut)", cut_max=sig(r_share["cut_max"]),
                                             share=sig(r_share["share_unflagged"]),
                                             fs_unflagged=int(r_share["fs_unflagged"]))
    numbers["curve_any_g_meets_both"] = num(bool(len(both) > 0),
                                            desc="P1 trade-off curve (descriptive): does any g on the 0-30 ms grid meet "
                                                 "both bars (cut >= 10-fold and <= 10% of recorded false starts changed)?",
                                            n_grid=int(len(cv)))
    extra["check_offset_percentile_iqr_fold_p0"] = sig(iqr_off)
    extra["note_fold_iqr"] = ("a_<policy>_fold_iqr is the 75th / 25th percentile of the 18 championship rates (prereg "
                              "definition); fairness.json's meet_iqr_fold_change evaluates the rate at the 25th / 75th "
                              "percentile offsets instead (a_p0_fold_iqr_offsetq reproduces it). The two differ by "
                              "construction (interpolation of a nonlinear transform).")

    inputs = [Path(args.descriptive), Path(args.fairness)] + list(rec_inputs)
    p = write_result(out, "guard", numbers, inputs, False, tables=tables, extra=extra, seed=args.seed)
    for k, val in numbers.items():
        print(f"{k:40s} {val.get('value')!s:>14} {val.get('ci95', '')} {val.get('champ', '')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
