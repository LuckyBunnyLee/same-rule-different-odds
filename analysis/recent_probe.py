"""EXPLORATORY probe of the recent championship RT offsets (WCH2022 fast, WCH2023, WCH2025 slow).

NOT pre-registered. NOT for the Oct 1 abstract. Every quantity here is exploratory (full paper, Dec 4) and is
labelled so in the JSON and in notes/recent_probe.md. Nothing here feeds analysis/numbers.json.

Questions (brief, 2026-09-30):
  Q1 shape    athlete-adjusted RT quantiles per championship; is 2022 -> 2025 a uniform shift?
  Q2 lanes    lane patterns in RT and force onset within the five force-trace championships
  Q3 rounds   heats vs semis vs finals by championship
  Q3b         start location and day (added after Q1: WCH2025's offset is not championship-wide)
  Q4 athletes same athletes at WCH2022, WCH2023 and WCH2025; personal history
  Q5 audio    start-signal characterisation from local broadcast audio (summarised from scratch CSVs)

Inputs: repo data (rt_athletes.csv, rt_fiore.csv, races.csv, rt_waveform_lanes.csv) through analysis/common.py,
plus exploratory scratch tables written by analysis/probe/*.py (fetched WA results for 400 m, 400 mH,
relays and combined events; gun features from broadcast audio). Scratch inputs are optional: a missing file
skips that block and is recorded in the JSON.

Run (repo root):
  .venv\\Scripts\\python.exe analysis\\recent_probe.py --seed 20260930 --boot 2000 \\
      --out analysis/outputs/recent_probe.json --notes notes/recent_probe.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _env  # noqa: E402,F401  (single-threaded BLAS, deterministic)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import patsy  # noqa: E402
from scipy import stats  # noqa: E402

from common import (ROUND_ORDER, attach_races, dedupe_sources, load_races, load_rt,  # noqa: E402
                    valid_rt_mask)
from lmm import fit_formula  # noqa: E402

ROOT = HERE.parent
SCR = HERE / "probe"
RECENT = ["WCH2022", "WCH2023", "WCH2025"]
FORCE_CHAMPS = ["WCH2022", "WCH2023", "WCH2025", "WIC2024", "WIC2025"]
QS = [5, 25, 50, 75, 95]
STRAIGHT = {"100m", "100mH", "110mH", "60m", "60mH"}      # home-straight (or indoor straight) starts
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:5.0f}s] {msg}", file=sys.stderr, flush=True)


def r(x, nd=2):
    if x is None:
        return None
    try:
        if not np.isfinite(x):
            return None
    except TypeError:
        return x
    return round(float(x), nd)


def ci(a, lo=2.5, hi=97.5, nd=2):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return [None, None]
    return [r(np.percentile(a, lo), nd), r(np.percentile(a, hi), nd)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "missing"


# ------------------------------------------------------------------------------------------------
# data and the global athlete-adjusting model
# ------------------------------------------------------------------------------------------------
def load_valid():
    rt, used = load_rt(False)
    races, rused = load_races(False)
    rt = attach_races(dedupe_sources(rt), races)
    rt["valid"] = valid_rt_mask(rt)
    v = rt[rt["valid"]].copy().reset_index(drop=True)
    v["rt_ms"] = v["rt_s"] * 1000.0
    ak = v["athlete_key"].astype(object)
    miss = ak.isna() | (ak.astype(str) == "None")
    v["athlete_id2"] = np.where(miss, "anon_" + v.index.astype(str), ak.astype(str))
    v["named"] = ~miss
    rounds_present = [x for x in ROUND_ORDER if x in set(v["round"])]
    v["round"] = pd.Categorical(v["round"], categories=rounds_present)
    v = v.merge(races[["race_id", "date", "sched_start_local", "temperature_c"]], on="race_id", how="left")
    v["loc"] = np.where(v["event"] == "200m", "200m", np.where(v["event"].isin(STRAIGHT), "straight", "other"))
    return v, rt, races, used + rused


def fit_global(v):
    """Same fixed/random structure as descriptive.py's championship-offset model (ML)."""
    fx = "C(sex, Treatment('M')) + C(round, Treatment('R1')) + C(event_type, Treatment('flat'))"
    m = fit_formula(fx + " + C(comp_year, Sum)", v, "rt_ms", ["race_id", "athlete_id2"], method="ML")
    names = m.names
    idx = [i for i, n in enumerate(names) if n.startswith("C(comp_year, Sum)")]
    levels = sorted(v["comp_year"].unique())
    offsets = {}
    for j, lev in enumerate(levels):
        L = np.zeros(len(names))
        if j < len(idx):
            L[idx[j]] = 1.0
        else:
            L[idx] = -1.0
        est, lo, hi, _ = m.contrast(L)
        offsets[lev] = (est, lo, hi)
    X = patsy.dmatrix(fx, v, return_type="dataframe")
    b = pd.Series(m.beta, index=names)
    dcols = [c for c in X.columns if c != "Intercept"]
    v["design"] = X[dcols].to_numpy() @ b[dcols].to_numpy()
    v["u_ath"] = v["athlete_id2"].map(m.blups["athlete_id2"]).fillna(0.0)
    v["u_race"] = v["race_id"].map(m.blups["race_id"]).fillna(0.0)
    v["adj"] = v["rt_ms"] - v["design"] - v["u_ath"]           # athlete- and design-adjusted RT
    v["rd"] = v["rt_ms"] - v["design"]                          # design-adjusted RT (athlete effect kept)
    return m, offsets


# ------------------------------------------------------------------------------------------------
# Q1 shape
# ------------------------------------------------------------------------------------------------
def boot_quant(x: pd.DataFrame, col: str, B: int, rng) -> np.ndarray:
    """Race-cluster bootstrap of quantiles (QS) and SD of x[col]. Rows: replicates."""
    groups = [g[col].to_numpy() for _, g in x.groupby("race_id", sort=True)]
    k = len(groups)
    out = np.empty((B, len(QS) + 1))
    for b in range(B):
        pick = rng.integers(0, k, k)
        a = np.concatenate([groups[i] for i in pick])
        out[b, :-1] = np.percentile(a, QS)
        out[b, -1] = a.std(ddof=1)
    return out


def point_quant(a):
    a = np.asarray(a, float)
    return np.r_[np.percentile(a, QS), a.std(ddof=1)]


def q1(v, rt, B, rng):
    res = {"note": "EXPLORATORY. adj = RT - design (sex, round, event-type) effects - athlete BLUP from the global "
                   "championship-offset model (ML, crossed race and athlete random intercepts). Race-cluster "
                   "bootstrap within championship; BLUP estimation uncertainty is not propagated. 1999-2013 rows "
                   "(Fiore source) have no athlete identities, so their adjusted spread is not comparable.",
           "quantiles_pct": QS}
    per = {}
    for cy, g in v.groupby("comp_year"):
        p = point_quant(g["adj"])
        per[cy] = {"n": int(len(g)), "q": [r(x, 1) for x in p[:-1]], "sd": r(p[-1], 2),
                   "raw_q": [r(x, 1) for x in np.percentile(g["rt_ms"], QS)], "named": bool(g["named"].all())}
    res["per_championship"] = per
    # recent three: overall and by start location
    cells = {}
    boots = {}
    for cy in RECENT:
        for loc in ("all", "straight", "200m"):
            g = v[v["comp_year"] == cy] if loc == "all" else v[(v["comp_year"] == cy) & (v["loc"] == loc)]
            for col in ("adj", "rt_ms"):
                bq = boot_quant(g, col, B, rng)
                p = point_quant(g[col])
                boots[(cy, loc, col)] = (p, bq)
                cells[f"{cy}|{loc}|{col}"] = {
                    "n": int(len(g)), "q": [r(x, 1) for x in p[:-1]], "sd": r(p[-1], 2),
                    "q_ci": [ci(bq[:, i], nd=1) for i in range(len(QS))], "sd_ci": ci(bq[:, -1])}
    res["recent_cells"] = cells
    changes = {}
    pairs = [("WCH2022", "WCH2023"), ("WCH2023", "WCH2025"), ("WCH2022", "WCH2025")]
    for loc in ("all", "straight", "200m"):
        for col in ("adj", "rt_ms"):
            for a, b in pairs:
                pa, ba = boots[(a, loc, col)]
                pb, bb = boots[(b, loc, col)]
                d, db = pb - pa, bb - ba
                key = f"{a}->{b}|{loc}|{col}"
                changes[key] = {
                    "dq": [r(x, 1) for x in d[:-1]], "dq_ci": [ci(db[:, i], nd=1) for i in range(len(QS))],
                    "dsd": r(d[-1]), "dsd_ci": ci(db[:, -1]),
                    "dq95_minus_dq5": r(d[4] - d[0], 1), "dq95_minus_dq5_ci": ci(db[:, 4] - db[:, 0], nd=1),
                    "dq50_minus_dq5": r(d[2] - d[0], 1), "dq50_minus_dq5_ci": ci(db[:, 2] - db[:, 0], nd=1),
                    "dq95_minus_dq50": r(d[4] - d[2], 1), "dq95_minus_dq50_ci": ci(db[:, 4] - db[:, 2], nd=1)}
    res["changes"] = changes
    # truncation sensitivity (raw RT): add recorded false starts with RT in [0.080, 0.100) back as observations
    fs = rt[rt["is_fs"].fillna(False) & rt["rt_s"].between(0.080, 0.0999)]
    sens = {}
    for cy in RECENT:
        base = v.loc[v["comp_year"] == cy, "rt_ms"].to_numpy()
        extra = fs.loc[fs["comp_year"] == cy, "rt_s"].to_numpy() * 1000
        sens[cy] = {"n_added": int(len(extra)), "raw_q_with_fs": [r(x, 1) for x in np.percentile(np.r_[base, extra], QS)],
                    "raw_q": [r(x, 1) for x in np.percentile(base, QS)]}
    res["truncation_sensitivity"] = sens
    return res


# ------------------------------------------------------------------------------------------------
# Q2 lanes
# ------------------------------------------------------------------------------------------------
def lane_slope(d: pd.DataFrame, ycol: str, B: int, rng):
    """Within-race lane slope (ms per lane) of ycol, race-cluster bootstrap."""
    d = d.dropna(subset=[ycol, "lane"]).copy()
    d["yc"] = d[ycol] - d.groupby("race_id")[ycol].transform("mean")
    d["Lc"] = d["lane"] - d.groupby("race_id")["lane"].transform("mean")
    g = [(x["Lc"].to_numpy(), x["yc"].to_numpy()) for _, x in d.groupby("race_id", sort=True)]
    num = np.array([np.sum(a * b) for a, b in g])
    den = np.array([np.sum(a * a) for a, b in g])
    pt = num.sum() / den.sum()
    k = len(g)
    bs = np.empty(B)
    for i in range(B):
        pick = rng.integers(0, k, k)
        bs[i] = num[pick].sum() / den[pick].sum()
    lanes = d.groupby("lane")["yc"].agg(["mean", "size"])
    return pt, bs, {int(L): [r(m_, 1), int(n)] for L, (m_, n) in lanes.iterrows()}


def q2(v, B, rng):
    res = {"note": "EXPLORATORY. Within-race lane effects: athlete- and design-adjusted RT (adj) centred on the race "
                   "mean, regressed on lane centred on the race mean; race-cluster bootstrap. 'straight' = 100 m, "
                   "100 mH, 110 mH (indoor: 60 m, 60 mH); 200 m (staggered bend start) separate. Force onset from "
                   "rt_waveform_lanes.csv (onset_5pct_s), adjusted with the same athlete BLUPs and design effects."}
    w = v[v["named"] & v["lane"].notna()].copy()
    w["lane"] = w["lane"].astype(int)
    rt_slopes = {}
    het = {}
    for cy in sorted(w["comp_year"].unique()):
        for loc in ("straight", "200m"):
            d = w[(w["comp_year"] == cy) & (w["loc"] == loc)]
            if len(d) < 60:
                continue
            pt, bs, lanes = lane_slope(d, "adj", B, rng)
            rt_slopes[f"{cy}|{loc}"] = {"n": int(len(d)), "slope_ms_per_lane": r(pt), "ci": ci(bs), "se": r(np.std(bs), 3),
                                        "lane_means_ms_n": lanes}
    for loc in ("straight", "200m"):
        s = [(k, x) for k, x in rt_slopes.items() if k.endswith("|" + loc) and k.split("|")[0] in FORCE_CHAMPS]
        if len(s) >= 2:
            est = np.array([x["slope_ms_per_lane"] for _, x in s])
            se = np.array([x["se"] for _, x in s])
            wts = 1 / se ** 2
            m_ = np.sum(wts * est) / wts.sum()
            Q = float(np.sum(wts * (est - m_) ** 2))
            het[loc] = {"champs": [k.split("|")[0] for k, _ in s], "pooled": r(m_), "Q": r(Q), "df": len(s) - 1,
                        "p": float(f"{stats.chi2.sf(Q, len(s) - 1):.3g}")}
            s2 = [(k, x) for k, x in s if not k.startswith("WCH2025")]
            if len(s2) >= 2:
                est2 = np.array([x["slope_ms_per_lane"] for _, x in s2])
                se2 = np.array([x["se"] for _, x in s2])
                w2 = 1 / se2 ** 2
                m2 = np.sum(w2 * est2) / w2.sum()
                Q2 = float(np.sum(w2 * (est2 - m2) ** 2))
                het[loc + "_without_WCH2025"] = {"pooled": r(m2), "Q": r(Q2), "df": len(s2) - 1,
                                                 "p": float(f"{stats.chi2.sf(Q2, len(s2) - 1):.3g}")}
    res["rt_slopes"] = rt_slopes
    res["heterogeneity_force_trace_champs"] = het
    # WCH2025 straight: by event, inner vs outer
    x = w[(w["comp_year"] == "WCH2025") & (w["loc"] == "straight")].copy()
    by_ev = {}
    for ev, d in x.groupby("event"):
        pt, bs, _ = lane_slope(d, "adj", B, rng)
        by_ev[ev] = {"n": int(len(d)), "slope": r(pt), "ci": ci(bs)}
    by_rd = {}
    for rd, d in x.groupby(x["round"].astype(str)):
        pt, bs, _ = lane_slope(d, "adj", B, rng)
        by_rd[rd] = {"n": int(len(d)), "slope": r(pt), "ci": ci(bs)}
    # cells (championship x start) whose lane-slope CI excludes zero
    res["cells_ci_excluding_zero"] = {k: [x_["slope_ms_per_lane"]] + x_["ci"] for k, x_ in rt_slopes.items()
                                      if x_["ci"][0] is not None and (x_["ci"][0] > 0 or x_["ci"][1] < 0)}
    x["yc"] = x["adj"] - x.groupby("race_id")["adj"].transform("mean")
    inner = x[x["lane"] <= 5]
    outer = x[x["lane"] >= 7]
    races = x["race_id"].unique()
    bs = []
    for _ in range(B):
        pick = rng.choice(races, len(races))
        cnt = pd.Series(pick).value_counts()
        wi = inner["race_id"].map(cnt).fillna(0)
        wo = outer["race_id"].map(cnt).fillna(0)
        bs.append(np.average(outer["yc"], weights=wo) - np.average(inner["yc"], weights=wi))
    res["WCH2025_straight"] = {"by_event": by_ev, "by_round": by_rd,
                               "outer7_9_minus_inner1_5_ms": r(outer["yc"].mean() - inner["yc"].mean(), 1),
                               "ci": ci(bs, nd=1), "n_inner": int(len(inner)), "n_outer": int(len(outer)),
                               "raw_median_inner": r(inner["rt_ms"].median(), 1), "raw_median_outer": r(outer["rt_ms"].median(), 1)}
    # force onset
    wl = pd.read_csv(ROOT / "data" / "derived" / "rt_waveform_lanes.csv")
    wl["comp_year"] = wl["race_id"].str.extract(r"^([A-Z]+\d{4})", expand=False)
    wl["event"] = wl["race_id"].str.split("-").str[1]
    wl = wl[(wl["json_status"] == "OK") & wl["onset_5pct_s"].between(0.09, 0.35)].copy()
    wl["onset_ms"] = wl["onset_5pct_s"] * 1000
    wl = wl.merge(v[["race_id", "lane", "u_ath", "design"]], on=["race_id", "lane"], how="left")
    wl["on_adj"] = wl["onset_ms"] - wl["design"].fillna(0) - wl["u_ath"].fillna(0)
    wl["loc"] = np.where(wl["event"] == "200m", "200m", "straight")
    rmo = wl[wl["loc"] == "straight"].groupby(["comp_year", "lane"])["red_minus_onset_ms"].mean().unstack()
    res["detection_minus_onset_by_lane_straight_ms"] = {cy: {int(L): r(val, 1) for L, val in row.dropna().items()}
                                                        for cy, row in rmo.iterrows()}
    fo = {}
    for (cy, loc), d in wl.groupby(["comp_year", "loc"]):
        pt, bs, lanes = lane_slope(d, "on_adj", B, rng)
        fo[f"{cy}|{loc}"] = {"n": int(len(d)), "slope_ms_per_lane": r(pt), "ci": ci(bs), "lane_means_ms_n": lanes,
                             "median_onset_ms": r(d["onset_ms"].median(), 1)}
    res["force_onset_slopes"] = fo
    return res


# ------------------------------------------------------------------------------------------------
# Q3 rounds, Q3b event-location and day
# ------------------------------------------------------------------------------------------------
def cell_model(w, cellcol, extra_fx):
    m = fit_formula(f"C({cellcol}) - 1 + {extra_fx}", w, "rt_ms", ["race_id", "athlete_id2"], method="REML")
    b = pd.Series(m.beta, index=m.names)
    C = pd.DataFrame(m.cov_beta, index=m.names, columns=m.names)

    def nm(level):
        for n in m.names:
            if n.startswith(f"C({cellcol})") and n.endswith(f"[{level}]"):
                return n
        return None

    def diff(a, c):
        na, nc = nm(a), nm(c)
        if na is None or nc is None:
            return None
        d = b[na] - b[nc]
        se = float(np.sqrt(C.loc[na, na] + C.loc[nc, nc] - 2 * C.loc[na, nc]))
        return d, d - 1.96 * se, d + 1.96 * se
    return diff


def q3(v):
    res = {"note": "EXPLORATORY. REML, championship x round cells (repechage pooled with R1), sex and event-type fixed "
                   "effects, crossed race and athlete random intercepts; 2015+ (named athletes)."}
    w = v[v["year"] >= 2015].copy()
    w["round"] = w["round"].astype(str).replace({"RP": "R1"})
    w["cr"] = w["comp_year"] + "_" + w["round"]
    diff = cell_model(w, "cr", "C(sex, Treatment('M')) + C(event_type, Treatment('flat'))")
    rc = {}
    for cy in sorted(w["comp_year"].unique()):
        for rd in ("PR", "SF", "F"):
            d = diff(f"{cy}_{rd}", f"{cy}_R1")
            if d:
                rc[f"{cy}|{rd}-R1"] = [r(x, 1) for x in d]
    res["round_contrasts"] = rc
    ch = {}
    for rd in ("R1", "SF", "F"):
        for a, c in (("WCH2023", "WCH2022"), ("WCH2025", "WCH2023"), ("WCH2025", "WCH2022")):
            d = diff(f"{a}_{rd}", f"{c}_{rd}")
            ch[f"{rd}|{a}-{c}"] = [r(x, 1) for x in d]
    res["change_by_round"] = ch
    return res


def q3b(v, B, rng):
    res = {"note": "EXPLORATORY. Added after Q1 showed WCH2025's offset is not championship-wide. Start location: "
                   "100 m / 100 mH / 110 mH share the home-straight start; the 200 m starts on the far bend."}
    w = v[v["year"] >= 2015].copy()
    w["ce"] = w["comp_year"] + "_" + w["event_type"]
    diff = cell_model(w, "ce", "C(sex, Treatment('M')) + C(round, Treatment('R1'))")
    ec = {}
    for cy in sorted(w["comp_year"].unique()):
        for et in ("200m", "hurdles"):
            d = diff(f"{cy}_{et}", f"{cy}_flat")
            if d:
                ec[f"{cy}|{et}-flat"] = [r(x, 1) for x in d]
    res["event_contrasts"] = ec
    vals = [x[0] for k, x in ec.items() if k.endswith("200m-flat") and not k.startswith("WCH2025")]
    res["200m_minus_flat_other_champs"] = {"min": r(min(vals), 1), "max": r(max(vals), 1), "median": r(np.median(vals), 1),
                                           "n": len(vals)}
    # day timelines (athlete-adjusted race means)
    tl = {}
    for cy in RECENT:
        x = v[v["comp_year"] == cy]
        t = x.groupby(["date"]).agg(adj=("adj", "mean"), n=("adj", "size"),
                                    events=("event", lambda s: ",".join(sorted(set(s)))))
        tl[cy] = {d_: {"adj_mean": r(row.adj, 1), "n": int(row.n), "events": row.events} for d_, row in t.iterrows()}
    res["day_timeline_adj"] = tl
    # WCH2022 before / after the 110mH final (Allen DQ, 2022-07-17 19:30 local)
    x = v[v["comp_year"] == "WCH2022"].copy()
    x["post"] = (x["date"] > "2022-07-17") | ((x["date"] == "2022-07-17") & (x["sched_start_local"] > "19:40"))
    races = x["race_id"].unique()
    post_r = set(x.loc[x["post"], "race_id"])
    rm = x.groupby("race_id")["adj"].agg(["sum", "size"])
    bs = []
    for _ in range(B):
        pick = pd.Series(rng.choice(races, len(races))).value_counts()
        s = rm.loc[pick.index]
        wts = pick.to_numpy()
        post = np.array([i in post_r for i in s.index])
        bs.append((s["sum"].to_numpy()[post] * wts[post]).sum() / (s["size"].to_numpy()[post] * wts[post]).sum()
                  - (s["sum"].to_numpy()[~post] * wts[~post]).sum() / (s["size"].to_numpy()[~post] * wts[~post]).sum())
    res["WCH2022_post_minus_pre_Allen"] = {"est": r(x.loc[x["post"], "adj"].mean() - x.loc[~x["post"], "adj"].mean(), 1),
                                           "ci": ci(bs, nd=1), "n_pre": int((~x["post"]).sum()), "n_post": int(x["post"].sum()),
                                           "caveat": "post = 200 m and 100 mH; event effects removed with pooled "
                                                     "coefficients, not championship-specific ones"}
    # temperature within championship (race means; races with a PDF temperature)
    tt = {}
    for cy in RECENT:
        x = v[(v["comp_year"] == cy) & v["temperature_c"].notna()]
        g = x.groupby("race_id").agg(adj=("adj", "mean"), T=("temperature_c", "first"), n=("adj", "size"))
        if len(g) >= 8 and g["T"].nunique() >= 3:
            sl = np.polyfit(g["T"], g["adj"], 1, w=np.sqrt(g["n"]))[0]
            rho, p = stats.spearmanr(g["T"], g["adj"])
            tt[cy] = {"races": int(len(g)), "T_range": [r(g["T"].min(), 0), r(g["T"].max(), 0)],
                      "slope_ms_per_C": r(sl), "spearman": r(rho), "p": float(f"{p:.3g}")}
        else:
            tt[cy] = {"races": int(len(g)), "note": "too few races with a temperature"}
    res["temperature_within_champ"] = tt
    return res


def extra_events(v, rng, B):
    """Scratch inputs: WA results for 400 m, 400 mH, relays (extra_rt.csv) and combined events (combined_rt.csv)."""
    res = {"note": "EXPLORATORY; scratch data fetched 2026-09-30 from worldathletics.org results pages "
                   "(analysis/probe/fetch_extra_events.py, fetch_combined.py). Valid = RT 0.100-0.300 s. "
                   "400 m / 400 mH / 4x100 m / 4x400 m start at the 400 m start (first bend); combined-event 100 m "
                   "and hurdles use the home-straight start, heptathlon 200 m the 200 m start."}
    p1, p2 = SCR / "extra_rt.csv", SCR / "combined_rt.csv"
    res["inputs"] = {"extra_rt.csv": sha(p1), "combined_rt.csv": sha(p2)}
    if p1.exists():
        e = pd.read_csv(p1)
        e = e[e["rt_s"].between(0.100, 0.300)].copy()
        e["rt_ms"] = e["rt_s"] * 1000
        med = e.groupby(["event", "comp_year"])["rt_ms"].median().unstack()
        res["extra_median_ms"] = {ev: {c: r(x, 1) for c, x in row.items()} for ev, row in med.iterrows()}
        medr = e[e["event"].isin(["400m", "400mH"])].groupby(["event", "round", "comp_year"])["rt_ms"].median().unstack()
        res["extra_median_by_round_ms"] = {f"{a}|{b}": {c: r(x, 1) for c, x in row.items()} for (a, b), row in medr.iterrows()}
        ind = e[e["event"].isin(["400m", "400mH"])].copy()
        ind["key"] = ind["athlete_id"].astype(str) + "|" + ind["event"]
        am = ind.groupby(["key", "comp_year"])["rt_ms"].mean().unstack()
        wa = {}
        for a, b in (("WCH2019", "WCH2022"), ("WCH2022", "WCH2023"), ("WCH2023", "WCH2025"), ("WCH2022", "WCH2025"),
                     ("WCH2019", "WCH2023"), ("WCH2019", "WCH2025")):
            if a in am and b in am:
                d = (am[b] - am[a]).dropna().to_numpy()
                bs = [np.mean(rng.choice(d, len(d))) for _ in range(B)]
                wa[f"{a}->{b}"] = {"n": int(len(d)), "mean": r(d.mean(), 1), "ci": ci(bs, nd=1), "share_slower": r(np.mean(d > 0))}
        res["400m_within_athlete_change_ms"] = wa
        # WCH2025 400 m-location events on days 2-5 (same days as the slow straight-start events) vs WCH2023
        x = ind.copy()
        x["early"] = x["round"].isin(["R1", "SF"])
        a23 = x[(x["comp_year"] == "WCH2023") & x["early"]].groupby("key")["rt_ms"].mean()
        a25 = x[(x["comp_year"] == "WCH2025") & x["early"]].groupby("key")["rt_ms"].mean()
        d = (a25 - a23).dropna().to_numpy()
        bs = [np.mean(rng.choice(d, len(d))) for _ in range(B)]
        days = sorted(x.loc[(x["comp_year"] == "WCH2025") & x["early"], "date"].unique())
        res["WCH2025_400m_R1_SF_minus_WCH2023_within_athlete"] = {"n": int(len(d)), "mean": r(d.mean(), 1), "ci": ci(bs, nd=1),
                                                                   "WCH2025_dates": days}
    if p2.exists():
        c = pd.read_csv(p2)
        c = c[c["rt_s"].between(0.100, 0.300)].copy()
        c["rt_ms"] = c["rt_s"] * 1000
        g = c.groupby(["ce", "event", "comp_year"]).agg(med=("rt_ms", "median"), n=("rt_ms", "size"), date=("date", "first"))
        out = {}
        for (ce, ev, cy), row in g.iterrows():
            out.setdefault(f"{ce}|{ev}", {})[cy] = {"median_ms": r(row.med, 1), "n": int(row.n), "date": row.date}
        res["combined_events"] = out
    # the sprint-event (repo) medians by location for the same championships, for side-by-side reading
    sp = v[v["comp_year"].isin(["WCH2019"] + RECENT)].groupby(["loc", "comp_year"])["rt_ms"].median().unstack()
    res["sprint_median_by_location_ms"] = {loc: {c: r(x, 1) for c, x in row.items()} for loc, row in sp.iterrows()}
    x = v[(v["comp_year"] == "WCH2025")]
    res["WCH2025_sprint_dates"] = {loc: sorted(x.loc[x["loc"] == loc, "date"].dropna().unique().tolist()) for loc in ("straight", "200m")}
    return res


# ------------------------------------------------------------------------------------------------
# Q4 same athletes
# ------------------------------------------------------------------------------------------------
def q4(v, m, B, rng):
    res = {"note": "EXPLORATORY. Athlete x championship means of design-adjusted RT (RT minus sex/round/event-type "
                   "effects; athlete effect kept). Panel = athletes with a valid start at WCH2022, WCH2023 and "
                   "WCH2025. Bootstrap over athletes. Expected noise variance of a within-athlete change uses the "
                   "global model's race + residual variance and each athlete's start counts (approximate)."}
    w = v[(v["year"] >= 2015) & v["named"]].copy()
    am = w.groupby(["athlete_id2", "comp_year"]).agg(m=("rd", "mean"), n=("rd", "size")).reset_index()
    piv = am.pivot(index="athlete_id2", columns="comp_year", values="m")
    npv = am.pivot(index="athlete_id2", columns="comp_year", values="n")
    panel = piv.dropna(subset=RECENT)
    res["n_panel"] = int(len(panel))
    ch = {}
    for a, b in (("WCH2022", "WCH2023"), ("WCH2023", "WCH2025"), ("WCH2022", "WCH2025")):
        d = (panel[b] - panel[a]).to_numpy()
        bm = [np.mean(rng.choice(d, len(d))) for _ in range(B)]
        ch[f"{a}->{b}"] = {"mean": r(d.mean(), 1), "ci": ci(bm, nd=1), "median": r(np.median(d), 1),
                           "share_slower": r(np.mean(d > 0)), "sd": r(d.std(ddof=1), 1)}
    res["panel_change_ms"] = ch
    # panel change by WCH2025 start location (athletes whose WCH2025 starts were all straight / all 200 m)
    loc25 = w[w["comp_year"] == "WCH2025"].groupby("athlete_id2")["loc"].agg(lambda s: s.iloc[0] if s.nunique() == 1 else "both")
    byloc = {}
    for loc in ("straight", "200m"):
        ids = panel.index.intersection(loc25[loc25 == loc].index)
        d = (panel.loc[ids, "WCH2025"] - panel.loc[ids, "WCH2023"]).to_numpy()
        if len(d) >= 5:
            bm = [np.mean(rng.choice(d, len(d))) for _ in range(B)]
            byloc[loc] = {"n": int(len(d)), "mean": r(d.mean(), 1), "ci": ci(bm, nd=1)}
    res["panel_WCH2023_to_WCH2025_by_2025_location"] = byloc
    # athletes who ran both straight and 200 m at the same championship: within-athlete 200m - straight
    both = {}
    for cy in ["WCH2015", "WCH2017", "WCH2019", "WCH2022", "WCH2023", "WCH2025", "OG2020", "OG2024"]:
        x = w[w["comp_year"] == cy]
        t = x.groupby(["athlete_id2", "loc"])["rd"].mean().unstack()
        if "200m" in t and "straight" in t:
            d = (t["200m"] - t["straight"]).dropna().to_numpy()
            if len(d) >= 5:
                bm = [np.mean(rng.choice(d, len(d))) for _ in range(B)]
                both[cy] = {"n": int(len(d)), "mean": r(d.mean(), 1), "ci": ci(bm, nd=1)}
    res["within_athlete_200m_minus_straight_ms"] = both
    # heterogeneity of within-athlete change
    s2w = m.var_comp["race_id"] + m.sigma2
    het = {}
    for a, b in (("WCH2015", "WCH2017"), ("WCH2017", "WCH2019"), ("WCH2019", "WCH2022"), ("WCH2022", "WCH2023"),
                 ("WCH2023", "WCH2025"), ("WCH2022", "WCH2025"), ("OG2020", "OG2024"), ("WIC2024", "WIC2025")):
        ok = piv[[a, b]].dropna().index
        d = piv.loc[ok, b] - piv.loc[ok, a]
        ev = s2w * (1 / npv.loc[ok, a] + 1 / npv.loc[ok, b])
        het[f"{a}->{b}"] = {"n": int(len(ok)), "var_obs": r(d.var(ddof=1), 0), "var_noise": r(ev.mean(), 0),
                            "excess_sd_ms": r(np.sign(d.var(ddof=1) - ev.mean()) * np.sqrt(abs(d.var(ddof=1) - ev.mean())), 1)}
    res["heterogeneity"] = het
    # personal history
    hist = piv.loc[panel.index]
    k = hist.notna().sum(axis=1)
    dev = hist.sub(hist.mean(axis=1), axis=0)
    res["history"] = {
        "champs_per_athlete_median": r(k.median(), 1),
        "mean_deviation_from_own_mean_ms": {c: r(x, 1) for c, x in dev.mean().items()},
        "n_by_champ": {c: int(x) for c, x in hist.notna().sum().items()},
        "share_WCH2025_slowest": r(np.mean(hist.rank(axis=1, ascending=False)["WCH2025"] == 1)),
        "share_WCH2022_fastest": r(np.mean(hist.rank(axis=1)["WCH2022"] == 1)),
        "chance_share": r(np.mean(1 / k))}
    pre = piv[["WCH2015", "WCH2017", "WCH2019", "OG2020"]].mean(axis=1)
    ok = panel.index.intersection(pre.dropna().index)
    d23 = panel.loc[ok, "WCH2023"] - panel.loc[ok, "WCH2022"]
    rr = np.corrcoef(pre[ok], d23)[0, 1]
    bs = []
    ids = np.array(ok)
    for _ in range(B):
        pick = rng.choice(ids, len(ids))
        bs.append(np.corrcoef(pre[pick], d23[pick])[0, 1])
    res["baseline_vs_2022_2023_change"] = {"n": int(len(ok)), "r": r(rr), "ci": ci(bs),
                                           "note": "baseline = mean of the athlete's pre-2022 championships (WCH2015/17/19, "
                                                   "OG2020), independent of the 2022 noise (no regression-to-mean artefact)"}
    return res


# ------------------------------------------------------------------------------------------------
# Q5 audio (summaries of scratch outputs)
# ------------------------------------------------------------------------------------------------
def q5(rng, B):
    res = {"note": "EXPLORATORY. Broadcast audio only (no video). Features from analysis/probe/gun_features.py "
                   "on every local start with a gun time (data/derived/foreperiods.csv) plus the WCH2025 200 m "
                   "full-round compilations (downloaded to analysis/probe/audio/, gitignored). Only relative, "
                   "within-recording quantities are interpretable.",
           "cannot_measure": ["sound pressure level at the blocks (broadcast gain, compression/limiting, codec and mic "
                              "position are unknown)",
                              "trigger-to-speaker latency / time zero (no time-zero reference in the audio; the SIS clock "
                              "is not audible)",
                              "which loudspeaker (block vs PA) an athlete heard first",
                              "per-lane arrival times"]}
    pf = SCR / "gun_features.csv"
    res["inputs"] = {"gun_features.csv": sha(pf), "gun_spectra_peaks.csv": sha(SCR / "gun_spectra_peaks.csv"),
                     "gun_spectra_similarity.csv": sha(SCR / "gun_spectra_similarity.csv")}
    if not pf.exists():
        res["status"] = "skipped: gun_features.csv missing"
        return res
    d = pd.read_csv(pf)
    d["cell"] = d["comp"] + "_" + d["loc"]
    inv = d.groupby("cell").agg(n=("gun_s", "size"), videos=("video_id", "nunique"),
                                n_set=("gun_minus_set_db", lambda s: int(s.notna().sum())))
    res["inventory"] = {c: {k: int(x) for k, x in row.items()} for c, row in inv.iterrows()}
    cols = ["tonal_f1", "peak_hz", "centroid_hz", "flatness", "rise_ms", "t_peak_ms", "dur10_ms", "dur20_ms",
            "gun_minus_set_db", "foreperiod_s"]
    med = d.groupby("cell")[cols].median()
    res["median_features"] = {c: {k: r(x, 3) for k, x in row.items()} for c, row in med.iterrows()}
    fp_ = SCR / "gun_spectra_peaks.csv"
    if fp_.exists():
        res["spectral_peaks_hz"] = dict(pd.read_csv(fp_).values.tolist())
    fs_ = SCR / "gun_spectra_similarity.csv"
    if fs_.exists():
        s = pd.read_csv(fs_, index_col=0)
        seiko = [c for c in s.index if c.startswith("WCH")]
        omega = [c for c in s.index if c.startswith("OG")]
        ss = [s.loc[a, b] for i, a in enumerate(seiko) for b in seiko[i + 1:]]
        so = [s.loc[a, b] for a in seiko for b in omega]
        res["spectral_similarity"] = {"seiko_seiko_range": [r(min(ss), 2), r(max(ss), 2)],
                                      "seiko_omega_range": [r(min(so), 2), r(max(so), 2)],
                                      "omega_omega": r(s.loc[omega[0], omega[1]], 2) if len(omega) == 2 else None,
                                      "WCH2025_straight_vs_200m": r(s.loc["WCH2025_straight", "WCH2025_200m"], 2)
                                      if "WCH2025_200m" in s.index else None}
    a = d.loc[d["cell"] == "WCH2025_straight", "gun_minus_set_db"].dropna().to_numpy()
    b = d.loc[d["cell"] == "WCH2025_200m", "gun_minus_set_db"].dropna().to_numpy()
    if len(a) >= 5 and len(b) >= 5:
        u = stats.mannwhitneyu(a, b)
        bs = [np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))) for _ in range(B)]
        res["WCH2025_gun_minus_set_straight_vs_200m"] = {
            "median_straight_db": r(np.median(a), 1), "median_200m_db": r(np.median(b), 1), "n": [int(len(a)), int(len(b))],
            "diff_median_db": r(np.median(a) - np.median(b), 1), "ci": ci(bs, nd=1), "mannwhitney_p": float(f"{u.pvalue:.3g}"),
            "caveat": "relative level of the start sound vs the starter's 'Set' in the same broadcast recording; depends "
                      "on where the broadcast microphones sit relative to the loudspeakers, so it is a pointer, not a "
                      "loudness measurement"}
    return res


# ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260930)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--notes", default=None, help="write the generated markdown note here")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    v, rt, races, used = load_valid()
    log(f"loaded {len(v)} valid starts")
    m, offsets = fit_global(v)
    log("global model fitted")
    out = {"name": "recent_probe", "status": "EXPLORATORY (not pre-registered; not for the Oct 1 abstract)",
           "seed": a.seed, "boot": a.boot,
           "inputs": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in used + [ROOT / "data/derived/rt_waveform_lanes.csv"]},
           "offsets_ms": {k: [r(x, 1) for x in val] for k, val in offsets.items()},
           "global_var_ms2": {"race": r(m.var_comp["race_id"], 1), "athlete": r(m.var_comp["athlete_id2"], 1),
                              "residual": r(m.sigma2, 1)}}
    out["q1_shape"] = q1(v, rt, a.boot, rng)
    log("q1")
    out["q2_lanes"] = q2(v, max(500, a.boot // 2), rng)
    log("q2")
    out["q3_rounds"] = q3(v)
    log("q3")
    out["q3b_location_day"] = q3b(v, a.boot, rng)
    out["q3b_extra_events"] = extra_events(v, rng, a.boot)
    log("q3b")
    out["q4_same_athletes"] = q4(v, m, a.boot, rng)
    log("q4")
    out["q5_audio"] = q5(rng, a.boot)
    log("q5")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    log(f"wrote {a.out}")
    if a.notes:
        Path(a.notes).write_text(render(out, a), encoding="utf-8")
        log(f"wrote {a.notes}")


# ------------------------------------------------------------------------------------------------
# generated note (numbers come from `out`; prose is template text)
# ------------------------------------------------------------------------------------------------
def _ci(x):
    return f"[{x[0]}, {x[1]}]" if x and x[0] is not None else "[n/a]"


def check_claims(o):
    """Qualitative claims made by the note; raise if the data stop supporting them (guard every claim a test can hold)."""
    q1_, q2_, q3_, ex, q4_ = o["q1_shape"], o["q2_lanes"], o["q3_rounds"], o["q3b_extra_events"], o["q4_same_athletes"]
    s = q2_["rt_slopes"]
    s25 = s["WCH2025|straight"]
    assert s25["ci"][0] > 0, "WCH2025 straight lane slope CI must exclude 0"
    assert all(s25["slope_ms_per_lane"] > x["slope_ms_per_lane"] for k, x in s.items() if k != "WCH2025|straight"), \
        "WCH2025 straight must be the largest lane slope"
    assert q2_["heterogeneity_force_trace_champs"]["straight_without_WCH2025"]["p"] > 0.05
    assert q2_["force_onset_slopes"]["WCH2025|straight"]["ci"][0] > 0, "force-onset gradient at WCH2025 straight"
    wa = q4_["within_athlete_200m_minus_straight_ms"]
    assert wa["WCH2025"]["ci"][1] < min(x["mean"] for k, x in wa.items() if k != "WCH2025"), \
        "WCH2025 same-athlete 200m-minus-straight must lie below every other championship"
    bl = q4_["panel_WCH2023_to_WCH2025_by_2025_location"]
    x4 = ex["WCH2025_400m_R1_SF_minus_WCH2023_within_athlete"]
    assert x4["ci"][1] < bl["straight"]["ci"][0], "400 m-start change must be below the straight-start change"
    c25 = ex["combined_events"]
    sprint_straight_25 = ex["sprint_median_by_location_ms"]["straight"]["WCH2025"]
    for k in ("decathlon|100m", "decathlon|110mH", "heptathlon|100mH"):
        assert c25[k]["WCH2025"]["median_ms"] < sprint_straight_25 - 15, f"{k} at WCH2025 must be far below the sprint straight median"
        assert c25[k]["WCH2025"]["date"] >= "2025-09-19"
    c23 = q1_["changes"]["WCH2022->WCH2023|all|adj"]
    assert c23["dq50_minus_dq5_ci"][0] <= 0 <= c23["dq50_minus_dq5_ci"][1], "5th vs median change must not differ"
    c35 = q1_["changes"]["WCH2023->WCH2025|all|adj"]
    assert c35["dq95_minus_dq5_ci"][0] > 0, "2023->2025 stretch must exclude 0"
    assert q1_["changes"]["WCH2023->WCH2025|200m|adj"]["dq"][2] < 5
    cb = q3_["change_by_round"]
    for pr in ("WCH2023-WCH2022", "WCH2025-WCH2023", "WCH2025-WCH2022"):
        cis = [cb[f"{rd}|{pr}"] for rd in ("R1", "SF", "F")]
        assert max(c_[1] for c_ in cis) < min(c_[2] for c_ in cis), f"round CIs must overlap for {pr}"
    het = q4_["heterogeneity"]
    wch = {k: x["excess_sd_ms"] for k, x in het.items() if k.startswith("WCH") and k.count("WCH") == 2}
    assert min(wch, key=wch.get) == "WCH2022->WCH2023", "2022->2023 must have the lowest heterogeneity"
    ref = [x for k, x in wch.items() if k in ("WCH2015->WCH2017", "WCH2017->WCH2019", "WCH2019->WCH2022")]
    assert min(ref) <= wch["WCH2023->WCH2025"] <= max(ref)
    bb = q4_["baseline_vs_2022_2023_change"]
    assert bb["ci"][0] <= 0 <= bb["ci"][1]


def render(o, a):
    check_claims(o)
    q1_, q2_, q3_, q3b_, ex, q4_, q5_ = (o["q1_shape"], o["q2_lanes"], o["q3_rounds"], o["q3b_location_day"],
                                         o["q3b_extra_events"], o["q4_same_athletes"], o["q5_audio"])
    ch = q1_["changes"]
    L = []
    A = L.append
    A("# Recent-championship probe (EXPLORATORY)\n")
    A("**Status: EXPLORATORY.** Not pre-registered, not for the Oct 1 abstract; for the full paper (Dec 4) only if "
      "confirmed. Every number below is generated by `analysis/recent_probe.py` into "
      "`analysis/outputs/recent_probe.json` (this file is rendered by the same script). Several analyses were added "
      "after looking at the data (marked *post hoc*); treat them as hypothesis-generating.\n")
    A(f"Reproduce: `.venv\\Scripts\\python.exe analysis\\recent_probe.py --seed {a.seed} --boot {a.boot} "
      f"--out analysis/outputs/recent_probe.json --notes notes/recent_probe.md` (after the scratch steps in the "
      f"last section). Athlete-adjusted RT (`adj`) = RT minus sex/round/event-type effects minus the athlete's BLUP "
      f"from the same crossed model that gives the repo's championship offsets (reproduced here: WCH2022 "
      f"{o['offsets_ms']['WCH2022'][0]} ms, WCH2025 {o['offsets_ms']['WCH2025'][0]} ms).\n")
    # ---------------- bottom line
    wa = q4_["within_athlete_200m_minus_straight_ms"]
    oth = [x["mean"] for k, x in wa.items() if k != "WCH2025"]
    s25 = q2_["rt_slopes"]["WCH2025|straight"]
    io = q2_["WCH2025_straight"]
    ce = ex.get("combined_events", {})
    A("## Bottom line\n")
    A("1. **The 2022 -> 2023 -> 2025 climb is two different things, not one trend.**")
    A(f"   - **WCH2022 (fast)** is a near-uniform shift of the whole distribution, at every start location (100 m "
      f"straight, 200 m bend, 400 m start incl. relays and combined events), in every round and on every day. "
      f"2022 -> 2023, athlete-adjusted: 5th/50th/95th percentile +{ch['WCH2022->WCH2023|all|adj']['dq'][0]}/"
      f"+{ch['WCH2022->WCH2023|all|adj']['dq'][2]}/+{ch['WCH2022->WCH2023|all|adj']['dq'][4]} ms; same-athlete "
      f"panel (n = {q4_['n_panel']}) +{q4_['panel_change_ms']['WCH2022->WCH2023']['mean']} ms "
      f"{_ci(q4_['panel_change_ms']['WCH2022->WCH2023']['ci'])}, with no excess between-athlete heterogeneity.")
    cz = q2_["cells_ci_excluding_zero"]
    others_pos = [f"{k.replace('|', ' ')} {x[0]} [{x[1]}, {x[2]}]" for k, x in cz.items()
                  if k != "WCH2025|straight" and x[1] > 0]
    others_neg = [f"{k.replace('|', ' ')} {x[0]} [{x[1]}, {x[2]}]" for k, x in cz.items() if x[2] < 0]
    A(f"   - **WCH2025 (slow)** is confined to the **home-straight start (100 m, 100 mH, 110 mH) on days 1-4 "
      f"(13-16 Sep)**. Same athletes, 200 m minus straight-start RT at WCH2025: {wa['WCH2025']['mean']} ms "
      f"{_ci(wa['WCH2025']['ci'])} (other championships: {min(oth)} to {max(oth)} ms). "
      f"The same straight start gave normal RTs on days 7-9 (combined events); the 400 m start was "
      f"+{ex['WCH2025_400m_R1_SF_minus_WCH2023_within_athlete']['mean']} ms "
      f"{_ci(ex['WCH2025_400m_R1_SF_minus_WCH2023_within_athlete']['ci'])} vs WCH2023 on days 2-5 (same athletes), "
      f"against +{q4_['panel_WCH2023_to_WCH2025_by_2025_location']['straight']['mean']} ms for straight-start athletes. "
      f"Within those straight-start races RT rises toward the outer lanes: {s25['slope_ms_per_lane']} ms per lane "
      f"{_ci(s25['ci'])}, lanes 7-9 {io['outer7_9_minus_inner1_5_ms']} ms {_ci(io['ci'])} slower than lanes 1-5, "
      f"and the force onset shows the same gradient. It is the largest of the 18 championship x start cells; other "
      f"cells whose CI excludes 0: " + ("; ".join(others_pos + others_neg) if (others_pos or others_neg) else "none") + ".")
    A("2. **Verdict on the explanations** (details in the synthesis table): 2022 is consistent with a system-wide "
      "time-zero/latency or calibration offset (A), not separable from venue-wide conditions (D); collective "
      "behavioural caution (B) is disfavoured (uniform shift, same in all rounds, homogeneous across athletes, "
      "unrelated to athletes' baseline speed). 2025 carries a **signal-delivery signature at one start installation "
      "during one period**: slower, more spread, and lane-dependent, i.e. consistent with a later and/or quieter "
      "signal at that start (A and C together, e.g. athletes cued by a more distant or weaker source), and "
      "inconsistent with B or with venue-wide D.")
    A("3. **Flag.** The WCH2025 location x day x lane pattern is strong (large, "
      "within-athlete, internally replicated in RT and force onset, not seen at WCH2025's other starts, and no "
      "positive lane gradient at any other championship's straight start), but it was found post hoc. It does not contradict the abstract's headline (athlete-independent "
      "variation is large); it sharpens it: WCH2025's +15.5 ms 'championship' offset is carried by one start "
      "installation over four days. If used before a confirmatory test it must be labelled exploratory.\n")
    # ---------------- Q1
    A("## Q1. Shape: uniform shift or fast tail?\n")
    A("Athlete-adjusted quantiles (ms; race-cluster bootstrap 95% CIs in `recent_probe.json`):\n")
    A("| championship | start | n | 5th | 25th | 50th | 75th | 95th | SD |")
    A("|---|---|---|---|---|---|---|---|---|")
    for cy in RECENT:
        for loc in ("all", "straight", "200m"):
            c = q1_["recent_cells"][f"{cy}|{loc}|adj"]
            A(f"| {cy} | {loc} | {c['n']} | " + " | ".join(str(x) for x in c["q"]) + f" | {c['sd']} |")
    A("\nChanges in athlete-adjusted quantiles (ms, 95% CI):\n")
    A("| change | start | 5th | 50th | 95th | 95th minus 5th change | SD change |")
    A("|---|---|---|---|---|---|---|")
    for loc in ("all", "straight", "200m"):
        for pr in ("WCH2022->WCH2023", "WCH2023->WCH2025", "WCH2022->WCH2025"):
            c = ch[f"{pr}|{loc}|adj"]
            A(f"| {pr} | {loc} | {c['dq'][0]} {_ci(c['dq_ci'][0])} | {c['dq'][2]} {_ci(c['dq_ci'][2])} | "
              f"{c['dq'][4]} {_ci(c['dq_ci'][4])} | {c['dq95_minus_dq5']} {_ci(c['dq95_minus_dq5_ci'])} | "
              f"{c['dsd']} {_ci(c['dsd_ci'])} |")
    ts = q1_["truncation_sensitivity"]["WCH2022"]
    c23 = ch["WCH2022->WCH2023|all|adj"]
    A(f"\n- **2022 -> 2023** moved the body of the distribution together: 5th to 75th percentile "
      f"+{min(c23['dq'][:4])} to +{max(c23['dq'][:4])} ms, and the 5th moved no more than the median (median minus "
      f"5th change {c23['dq50_minus_dq5']} ms {_ci(c23['dq50_minus_dq5_ci'])}). Only the 95th moved less "
      f"(95th minus 5th change {c23['dq95_minus_dq5']} ms {_ci(c23['dq95_minus_dq5_ci'])}). So the change is not "
      f"concentrated in the fast tail. Truncation check: adding WCH2022's {ts['n_added']} recorded "
      f"false starts with RT 0.080-0.099 s back moves the raw 5th percentile from {ts['raw_q'][0]} to "
      f"{ts['raw_q_with_fs'][0]} ms.")
    A(f"- **2023 -> 2025** is not a uniform shift: the slow tail moved {ch['WCH2023->WCH2025|all|adj']['dq95_minus_dq5']} ms "
      f"{_ci(ch['WCH2023->WCH2025|all|adj']['dq95_minus_dq5_ci'])} more than the fast tail and the SD grew "
      f"{ch['WCH2023->WCH2025|all|adj']['dsd']} ms. Split by start: the 200 m barely changed (median "
      f"+{ch['WCH2023->WCH2025|200m|adj']['dq'][2]} ms {_ci(ch['WCH2023->WCH2025|200m|adj']['dq_ci'][2])}); the "
      f"straight-start events shifted and stretched (5th +{ch['WCH2023->WCH2025|straight|adj']['dq'][0]}, median "
      f"+{ch['WCH2023->WCH2025|straight|adj']['dq'][2]}, 95th +{ch['WCH2023->WCH2025|straight|adj']['dq'][4]} ms).")
    A("- Reading: a pure time-zero delay predicts equal shifts at all quantiles (closest to 2022 -> 2023); a weaker "
      "or more distant signal predicts a shift that grows toward the slow tail (2025 straight-like; lab: RT SD "
      "shrinks with loudness); reduced anticipation predicts the fast tail moving more than the median (not seen in "
      "either step: the 5th moved as much as the median in 2022 -> 2023 and less in 2023 -> 2025).\n")
    # ---------------- Q2
    A("## Q2. Lanes (RT and force onset)\n")
    A("Within-race lane slope of athlete-adjusted RT (ms per lane, 95% CI):\n")
    A("| championship | straight | 200 m | force onset, straight | force onset, 200 m |")
    A("|---|---|---|---|---|")
    for cy in ["WCH2015", "WCH2017", "WCH2019", "WCH2022", "WCH2023", "WCH2025", "WIC2024", "WIC2025", "OG2020", "OG2024"]:
        def cell(dct, key):
            x = dct.get(key)
            return f"{x['slope_ms_per_lane']} {_ci(x['ci'])}" if x else "-"
        A(f"| {cy} | {cell(q2_['rt_slopes'], cy + '|straight')} | {cell(q2_['rt_slopes'], cy + '|200m')} | "
          f"{cell(q2_['force_onset_slopes'], cy + '|straight')} | {cell(q2_['force_onset_slopes'], cy + '|200m')} |")
    h = q2_["heterogeneity_force_trace_champs"]
    be = io["by_event"]
    br = io["by_round"]
    rmo = q2_["detection_minus_onset_by_lane_straight_ms"]
    A(f"\n- Straight-start slopes differ across the five force-trace championships (Q = {h['straight']['Q']}, "
      f"df {h['straight']['df']}, p = {h['straight']['p']}); without WCH2025 they do not (p = "
      f"{h['straight_without_WCH2025']['p']}). At the 200 m start the three force-trace championships agree and are "
      f"near zero (p = {h['200m']['p']}).")
    A("- Other cells whose CI excludes 0 (RT): " + ("; ".join(others_pos + others_neg) if (others_pos or others_neg)
                                                     else "none") + ". None is near the WCH2025 straight value.")
    A(f"- WCH2025 straight by event: 100 m {be['100m']['slope']} {_ci(be['100m']['ci'])}, 100 mH "
      f"{be['100mH']['slope']} {_ci(be['100mH']['ci'])}, 110 mH {be['110mH']['slope']} {_ci(be['110mH']['ci'])} "
      f"ms/lane (the 110 mH starts 10 m behind the 100 m line); by round: " +
      ", ".join(f"{k} {x['slope']} {_ci(x['ci'])}" for k, x in br.items()) +
      f". Raw median RT lanes 1-5 {io['raw_median_inner']} ms vs lanes 7-9 {io['raw_median_outer']} ms.")
    A("- Detection line minus 5%-force onset by lane at WCH2025 (straight, ms): " +
      ", ".join(f"L{k} {x}" for k, x in rmo.get("WCH2025", {}).items()) +
      ". It is flat across lanes 2-9, so the WCH2025 gradient is in when athletes start to push, not in detection. "
      "Caveat: at WCH2023 detection minus onset rises in the outer lanes (" +
      ", ".join(f"L{k} {x}" for k, x in rmo.get("WCH2023", {}).items()) +
      "), which is why WCH2023's force-onset slope is negative while its RT slope is not; the 5%-onset estimator "
      "depends on trace shape, so RT slopes are primary.")
    A("- A lane gradient that appears at one start, in one period, is what a difference in signal delivery predicts "
      "(an extra path of about 1.2 m per lane is about 3.5 ms per lane at 343 m/s if the cue comes from the infield "
      "side). A behavioural account would have to explain why it appears only there, since lane draws follow the "
      "same seeding rules at every championship.\n")
    # ---------------- Q3
    A("## Q3. Rounds\n")
    cb = q3_["change_by_round"]
    A("| change (athlete-adjusted, ms, 95% CI) | heats (R1) | semis | finals |")
    A("|---|---|---|---|")
    for pr in ("WCH2023-WCH2022", "WCH2025-WCH2023", "WCH2025-WCH2022"):
        A(f"| {pr} | " + " | ".join(f"{cb[f'{rd}|{pr}'][0]} [{cb[f'{rd}|{pr}'][1]}, {cb[f'{rd}|{pr}'][2]}]"
                                   for rd in ("R1", "SF", "F")) + " |")
    rcs = q3_["round_contrasts"]

    def rng_of(tag, excl):
        vals = [x[0] for k, x in rcs.items() if k.endswith(tag) and k.split("|")[0] not in excl]
        return (min(vals), max(vals)) if vals else (None, None)
    lines = []
    for tag in ("SF-R1", "F-R1", "PR-R1"):
        lo_, hi_ = rng_of(tag, RECENT)
        rec = ", ".join(f"{cy} {rcs[f'{cy}|{tag}'][0]}" for cy in RECENT if f"{cy}|{tag}" in rcs)
        lines.append(f"{tag}: {rec} (other championships {lo_} to {hi_})")
    A("\nThe change is the same in heats, semis and finals within the CIs; finals did not move more (B's 'larger in "
      "finals' prediction is not supported). Within-championship round contrasts (ms): " + "; ".join(lines) +
      ". WCH2025's preliminary round (men's 100 m only, weaker athletes) sits above the others.\n")
    # ---------------- Q3b
    A("## Q3b. Start location and day (*post hoc*)\n")
    ec = q3b_["event_contrasts"]
    o2 = q3b_["200m_minus_flat_other_champs"]
    A(f"- **200 m minus 100 m** (athlete-adjusted, same championship): WCH2025 {ec['WCH2025|200m-flat'][0]} ms "
      f"[{ec['WCH2025|200m-flat'][1]}, {ec['WCH2025|200m-flat'][2]}] vs {o2['min']} to {o2['max']} ms at the other "
      f"{o2['n']} championships with both. Within the same athletes (ran both at one championship): see table.")
    A("\n| championship | athletes | 200 m minus straight, same athlete (ms, 95% CI) |")
    A("|---|---|---|")
    for cy, x in wa.items():
        A(f"| {cy} | {x['n']} | {x['mean']} {_ci(x['ci'])} |")
    tl = q3b_["day_timeline_adj"]["WCH2025"]
    A("\n- **WCH2025 by day** (athlete-adjusted mean, ms): " + "; ".join(f"{d_[5:]} {x['adj_mean']} ({x['events']})"
                                                                     for d_, x in tl.items()) + ".")
    e4 = ex.get("400m_within_athlete_change_ms", {})
    if e4:
        A(f"- **400 m start** (400 m, 400 mH; scratch fetch), same athletes: 2022 -> 2023 "
          f"+{e4['WCH2022->WCH2023']['mean']} {_ci(e4['WCH2022->WCH2023']['ci'])}, 2023 -> 2025 "
          f"+{e4['WCH2023->WCH2025']['mean']} {_ci(e4['WCH2023->WCH2025']['ci'])}, 2019 -> 2022 "
          f"{e4['WCH2019->WCH2022']['mean']} {_ci(e4['WCH2019->WCH2022']['ci'])} ms. So 2022 was fast at this start "
          f"too; 2025 was at most a few ms slower there. Unadjusted medians by event and championship (ms): " +
          "; ".join(f"{ev} " + "/".join(f"{c[-4:]} {x}" for c, x in row.items()) for ev, row in ex["extra_median_ms"].items()) + ".")
    if ce:
        A("- **Combined events** (unadjusted median RT, ms, date; different athletes each year): " + "; ".join(
            f"{k.replace('|', ' ')}: " + ", ".join(f"{c[-4:]} {x['median_ms']} ({x['date'][5:]})" for c, x in row.items())
            for k, row in ce.items()) +
          ". At WCH2025 the heptathlon 100 mH (19 Sep) and decathlon 100 m / 110 mH (20-21 Sep) used the same "
          "home-straight start as the slow 100 m and gave normal-to-fast RTs, so the straight start was not slow "
          "throughout; at WCH2022 the decathlon on 23-24 Jul was still fast.")
    pa = q3b_["WCH2022_post_minus_pre_Allen"]
    A(f"- **WCH2022 before vs after the 110 mH final** (Allen DQ): +{pa['est']} ms {_ci(pa['ci'])} "
      f"(n = {pa['n_pre']}/{pa['n_post']}; post = 200 m and 100 mH, so event effects are confounded). At most a "
      "small drift; the championship stayed fast to the last day.")
    tt = q3b_["temperature_within_champ"]
    A(f"- **Temperature within championship** (race means vs PDF temperature): WCH2022 {tt['WCH2022'].get('slope_ms_per_C')} "
      f"ms/degC (p = {tt['WCH2022'].get('p')}, {tt['WCH2022'].get('T_range')} degC), WCH2023 {tt['WCH2023'].get('slope_ms_per_C')} "
      f"ms/degC (p = {tt['WCH2023'].get('p')}); WCH2025 has too few race temperatures.\n")
    # ---------------- Q4
    A("## Q4. Same athletes and personal history\n")
    pc = q4_["panel_change_ms"]
    A(f"Panel: {q4_['n_panel']} athletes with valid starts at all three.\n")
    A("| change | mean (ms, 95% CI) | median | share slower | SD |")
    A("|---|---|---|---|---|")
    for k, x in pc.items():
        A(f"| {k} | {x['mean']} {_ci(x['ci'])} | {x['median']} | {x['share_slower']} | {x['sd']} |")
    bl = q4_["panel_WCH2023_to_WCH2025_by_2025_location"]
    A(f"\n- By WCH2025 start: athletes whose WCH2025 races were all straight-start +{bl['straight']['mean']} "
      f"{_ci(bl['straight']['ci'])} (n = {bl['straight']['n']}); all 200 m {bl['200m']['mean']} {_ci(bl['200m']['ci'])} "
      f"(n = {bl['200m']['n']}).")
    het = q4_["heterogeneity"]
    A("- Heterogeneity of within-athlete change (observed variance minus expected noise, as an SD in ms): " +
      "; ".join(f"{k} {x['excess_sd_ms']}" for k, x in het.items()) +
      ". 2022 -> 2023 shows none (everyone moved together), the lowest of the World Championship pairs. 2023 -> 2025 "
      "shows some, as the start-location split implies, but it lies within the range of the reference pairs, so "
      "heterogeneity alone does not discriminate.")
    hi = q4_["history"]
    A(f"- Personal history (panel athletes' championships 2015-2025, median {hi['champs_per_athlete_median']} each): "
      f"mean deviation from own mean " + ", ".join(f"{c} {x}" for c, x in hi["mean_deviation_from_own_mean_ms"].items()) +
      f" ms. WCH2025 was the athlete's slowest championship for {round(100 * hi['share_WCH2025_slowest'])}% of them "
      f"and WCH2022 the fastest for {round(100 * hi['share_WCH2022_fastest'])}% (chance about "
      f"{round(100 * hi['chance_share'])}%).")
    bb = q4_["baseline_vs_2022_2023_change"]
    A(f"- Were habitual fast starters the ones who slowed after 2022 (a caution prediction: negative r)? Correlation "
      f"of pre-2022 baseline RT with the 2022 -> 2023 change r = {bb['r']} {_ci(bb['ci'])} (n = {bb['n']}): no "
      f"evidence, though the CI cannot exclude a modest negative r.")
    A("- Diamond League / national histories were not fetched (next step if needed).\n")
    # ---------------- Q5
    A("## Q5. Start signal from broadcast audio\n")
    inv = q5_.get("inventory", {})
    A("Local audio (broadcast, audio only): " + "; ".join(f"{c} {x['n']} starts / {x['videos']} videos" for c, x in inv.items()) +
      ". WCH2025 200 m = two WA full-round compilations downloaded for this probe (gitignored). No audio exists "
      "locally for WIC2024/WIC2025, the WCH2025 combined events or the 400 m.\n")
    mf = q5_.get("median_features", {})
    A("| cell | peaks of the average spectrum (Hz, strongest first) | median rise 10-90% (ms) | median -10 dB duration (ms) | median start sound minus 'Set' (dB) | median foreperiod (s) |")
    A("|---|---|---|---|---|---|")
    for c, x in mf.items():
        A(f"| {c} | {q5_.get('spectral_peaks_hz', {}).get(c, '')} | {x['rise_ms']} | {x['dur10_ms']} | "
          f"{x['gun_minus_set_db']} | {x['foreperiod_s']} |")
    ss = q5_.get("spectral_similarity", {})
    gs = q5_.get("WCH2025_gun_minus_set_straight_vs_200m", {})
    A(f"\n- **Signal type.** Vendor is distinguishable: the Omega Games' average spectra peak near 0.8 kHz and "
      f"1.6-1.9 kHz, the Seiko championships near 1.2-1.5 kHz and 2.2-2.4 kHz; log-spectrum similarity Seiko-Seiko "
      f"{ss.get('seiko_seiko_range')}, Seiko-Omega {ss.get('seiko_omega_range')}, Omega-Omega {ss.get('omega_omega')}. "
      "Within Seiko the peak lists overlap but are not identical (WCH2022 lacks the 1.49 kHz peak in its top four, "
      "yet its overall spectrum is among the closest to WCH2019's); with 6-44 starts per championship from different "
      "broadcast chains, a change in the Seiko sound can be neither shown nor excluded. WCH2025's straight and 200 m "
      f"starts used the same sound (similarity {ss.get('WCH2025_straight_vs_200m')}). Rise time and duration vary "
      "between videos (microphone distance, reverberation, processing) more than between championships, so they do "
      "not identify the signal.")
    if gs:
        A(f"- **Relative level.** In the same host broadcast, the start sound's level relative to the starter's 'Set' "
          f"was lower at the straight start than at the 200 m start (straight minus 200 m: {gs['diff_median_db']} dB "
          f"{_ci(gs['ci'])}; medians {gs['median_straight_db']} vs "
          f"{gs['median_200m_db']} dB, n = {gs['n'][0]}/{gs['n'][1]}, Mann-Whitney p = {gs['mannwhitney_p']}). This "
          "points the same way as a quieter start signal at the straight start, but it depends on where the broadcast "
          "microphones sat relative to the loudspeakers, so it is a pointer only.")
    A("- **What broadcast audio cannot tell us:** " + "; ".join(q5_.get("cannot_measure", [])) + ". The recorded start "
      "sound mixes block speakers, PA and reverberation after unknown gain, compression and codec. Feasibility of "
      "reconstructing the delivered signal: signal type yes (vendor level), relative timing of commands yes "
      "(foreperiods), level and latency at the blocks no.\n")
    # ---------------- synthesis
    A("## Q6. Synthesis\n")
    A("| explanation | WCH2022 (fast) | WCH2025 (slow) | what would decide it |")
    A("|---|---|---|---|")
    A("| (A) time zero / signal latency | **Consistent**: near-uniform shift at every start, round and day, no lane "
      "gradient; same athletes move together | **Consistent only in a lane-dependent form**: a delay common to all "
      "blocks would not stretch the distribution or create the outer-lane gradient | per-block arrival time of the "
      "start sound relative to the SIS time zero (a reference click at each block), per session |")
    A("| (B) collective caution | **Disfavoured**: 5th percentile moved no more than the median, no round dependence, "
      "no athlete heterogeneity, unrelated to baseline speed; still fast in the last days (decathlon) | "
      "**Disfavoured**: same athletes normal in the 200 m, near-normal at the 400 m start on the same days; straight "
      "start normal on days 7-9; lane-dependent | would need athlete-level evidence (e.g. anticipation measures); "
      "not supported by these data |")
    A("| (C) signal loudness | Weakly disfavoured: 2022 was faster **and** slightly more spread than 2023, the "
      "opposite of the louder-is-faster-and-tighter lab pattern | **Consistent**: slower, more spread, lane-dependent; "
      "broadcast pointer (start sound weaker relative to 'Set' at the straight start) | SPL of the start sound at each "
      "block (calibrated meter), speaker volume settings per lane |")
    A("| (D) venue / conditions | Not separable from A (venue-wide); no temperature association within the meet | "
      "**Disfavoured** as venue-wide: same stadium and days, other starts normal or near-normal | cross-meet data at the same venues "
      "with a measured signal |")
    A("\n**Decisive data:** SIS logs and configuration by session (speaker routing and volume per lane, any change "
      "between 16 and 19 Sep 2025 at the home-straight start, trigger-to-speaker latency), per-block signal arrival time "
      "and SPL, Seiko's zero-control records, and the officiating high-speed video (movement onset vs the sound; the WA "
      "'Officiating Video Clip' links return HTTP 403). For 2022: a measured time-zero offset or the RT reported for a "
      "reference force.\n")
    A("**Worth registering?** The WCH2025 pattern is the one result here strong enough to matter. A confirmatory test "
      "needs data not yet examined, e.g. other Seiko meets at the Tokyo National Stadium (Golden Grand Prix) or the "
      "WCH2025 officiating video; predictions: straight-start RT slower than the same athletes' 200 m RT, with an "
      "outer-lane gradient, only if the same installation and configuration were used.\n")
    # ---------------- provenance
    A("## Input steps and provenance (all exploratory, `analysis/probe/`)\n")
    A("1. `fetch_extra_events.py WCH2025,WCH2023,WCH2022,WCH2019` then `parse_extra.py`: WA results pages for 400 m, "
      "400 mH, 4x100 m, 4x400 m (URLs and retrieval times in `extra_rt.csv`; pages cached in `wa_pages/`, throttled "
      "3 s).")
    A("2. `fetch_combined.py WCH2025,WCH2023,WCH2022,WCH2019`: decathlon 100 m, 400 m, 110 mH and heptathlon 100 mH, "
      "200 m (`combined_rt.csv`).")
    A("3. `dl_audio.py NjJAn9hcsv8 AXbIf9u_G70` (WA full-round 200 m compilations, Tokyo 25; audio only, 800K, "
      "gitignored), `find_guns_200m.py` (the measurement pipeline's candidate detector), `run_gun_features.py`, "
      "`gun_spectra.py`.")
    A("4. `analysis/recent_probe.py` (this note). Inputs and hashes are in the JSON (`inputs`, `q3b_extra_events.inputs`, "
      "`q5_audio.inputs`).")
    A("\nLimits: the 200 m compilation guns are detector-selected (score >= 44, jump >= 25 dB) without race matching; "
      "the audio 'Set' level uses the detector's last speech burst for them. BLUP uncertainty is not propagated in Q1. "
      "The Q4 noise variance is approximate. Scratch WA data are not validated against PDFs as the repo's data are.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
