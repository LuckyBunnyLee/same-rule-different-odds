"""Deliverable 4 - descriptive analysis of championship reaction times (RT data alone).

Inputs : data/derived/rt_athletes.csv (+ rt_fiore.csv when present), data/derived/races.csv
Output : one deterministic JSON (--out) with numbers + tables + RT-distribution fits.

Contents
  1. Coverage and data flags (valid starts, false starts, identified athletes).
  2. RT summaries by sex, round, event, championship, timing system and rule era
     (race-clustered bootstrap CIs for mean and median).
  3. Crossed random-intercept model (championship-year, race, athlete), REML:
     sex / round / event contrasts, variance components, race ICC within championship.
  4. Meet (championship-year) effects: fixed-effect deviations and an ML likelihood-ratio
     test for between-meet heterogeneity; Omega vs Seiko contrast (comp-level, few clusters).
  5. Trend across years and rule eras (only when >= 5 distinct years are available).
  6. Frequency of RTs near 0.100 s and recorded false starts.
  7. Truncated ML fits (ex-Gaussian, shifted lognormal, shifted Wald) per sex, with the
     extrapolated mass below 0.100 s and a race-clustered bootstrap CI.

Valid start = RT in [0.100, 0.300] s, not a false start (RT < 0.100 or TR16.8 label), not DNS.
Athletes without an identity (Fiore rows) get a unique pseudo-ID, so their athlete effect is
absorbed as independent noise rather than dropped.

Usage: .venv\\Scripts\\python.exe analysis\\descriptive.py --out analysis/outputs/descriptive.json
"""
from __future__ import annotations

import _env  # noqa: F401  (deterministic BLAS; must precede numpy)

import argparse
import sys
import time

import numpy as np
import pandas as pd
import patsy

import rtdist
from common import (FS_THRESHOLD, ROUND_ORDER, add_common_args, attach_races, dedupe_sources,
                    load_races, load_rt, num, resolve_out, rule_era, valid_rt_mask, wilson_ci,
                    write_result)
from lmm import fit_formula, lrt, ratio_ci, sd_ci

Z975 = 1.959963984540054


# ------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------

def boot_summary(df: pd.DataFrame, by: list, value="rt_ms", cluster="race_id", n_boot=1000, seed=1):
    """Per-group n, races, mean/median (race-clustered bootstrap 95% CI), SD, IQR, P5/P95."""
    rng = np.random.default_rng(seed)
    rows = []
    for key, g in df.groupby(by, sort=True, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        arrs = [a.to_numpy(float) for _, a in g.groupby(cluster, sort=True)[value]]
        k = len(arrs)
        x = g[value].to_numpy(float)
        bs = np.empty((n_boot, 2))
        for b in range(n_boot):
            v = np.concatenate([arrs[i] for i in rng.integers(0, k, k)])
            bs[b] = (v.mean(), np.median(v))
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        row = dict(zip(by, key))
        row.update({"n": len(x), "races": k, "mean": x.mean(), "mean_lo": lo[0], "mean_hi": hi[0],
                    "median": np.median(x), "median_lo": lo[1], "median_hi": hi[1],
                    "sd": x.std(ddof=1) if len(x) > 1 else np.nan,
                    "q25": np.percentile(x, 25), "q75": np.percentile(x, 75),
                    "p05": np.percentile(x, 5), "p95": np.percentile(x, 95),
                    "share_lt120": float((x < 120).mean()), "share_lt110": float((x < 110).mean())})
        rows.append(row)
    return pd.DataFrame(rows)


def boot_share(df, mask_col, cluster="race_id", n_boot=1000, seed=2):
    """Share of rows with mask_col True, with race-clustered bootstrap CI."""
    rng = np.random.default_rng(seed)
    g = df.groupby(cluster, sort=True)[mask_col].agg(["sum", "count"])
    s, c = g["sum"].to_numpy(float), g["count"].to_numpy(float)
    k = len(s)
    est = s.sum() / c.sum()
    bs = np.empty(n_boot)
    for b in range(n_boot):
        i = rng.integers(0, k, k)
        bs[b] = s[i].sum() / c[i].sum()
    return float(est), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(s.sum()), int(c.sum())


def coef_ms(res, name, desc):
    est, lo, hi = res.coef(name)
    return num(round(est, 3), ci=(round(lo, 3), round(hi, 3)), unit="ms", desc=desc)


# ------------------------------------------------------------------------------------------

def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--boot", type=int, default=1000, help="bootstrap replicates for summaries")
    ap.add_argument("--fit-boot", type=int, default=200, help="bootstrap replicates for tail mass")
    ap.add_argument("--meet-boot", type=int, default=100, help="bootstrap replicates for per-meet tail mass")
    ap.add_argument("--min-starts", type=int, default=4, help="min valid starts for the fast-athlete split-half")
    args = ap.parse_args()
    out = resolve_out(args, "descriptive")
    t0 = time.time()

    def tick(label):
        print(f"[time] {label}: {time.time() - t0:.0f}s", file=sys.stderr, flush=True)

    rt, used = load_rt(args.mock)
    if rt.empty:
        raise SystemExit("no RT data found")
    races, rused = load_races(args.mock)
    rt = attach_races(dedupe_sources(rt), races)
    rt["era"] = rt["year"].map(rule_era)
    rt["timing"] = rt.get("race_timing", pd.Series(np.nan, index=rt.index))
    rt["valid"] = valid_rt_mask(rt)
    started = rt[rt["rt_s"].notna() | rt["is_fs"]].copy()
    v = rt[rt["valid"]].copy()
    v["rt_ms"] = v["rt_s"] * 1000.0
    # athletes without identity -> unique pseudo IDs (independent athlete effects)
    ak = v["athlete_key"].astype(object)
    miss = ak.isna() | (ak.astype(str) == "None")
    v["athlete_id2"] = np.where(miss, "anon_" + v.index.astype(str), ak.astype(str))
    rounds_present = [r for r in ROUND_ORDER if r in set(v["round"])]
    v["round"] = pd.Categorical(v["round"], categories=rounds_present + sorted(set(v["round"]) - set(rounds_present)))

    numbers, tables, extra = {}, {}, {}
    comps = sorted(v["comp_year"].unique())
    years = sorted(v["year"].unique())
    extra["sources"] = sorted(rt["source"].unique())
    extra["comp_years"] = comps

    # ---- 1. coverage ------------------------------------------------------------------------
    numbers["n_rows"] = num(int(len(rt)), desc="athlete rows after de-duplicating sources")
    numbers["n_starts_with_rt"] = num(int(rt["rt_s"].notna().sum()), desc="rows with a recorded RT")
    numbers["n_valid"] = num(int(len(v)), desc="valid starts (RT 0.100-0.300 s, not FS, not DNS)")
    numbers["n_races"] = num(int(v["race_id"].nunique()), desc="races with >= 1 valid start")
    numbers["n_comp_years"] = num(len(comps), desc="championships (comp x year)")
    numbers["year_min"] = num(int(min(years)), desc="first championship year")
    numbers["year_max"] = num(int(max(years)), desc="last championship year")
    numbers["n_athletes_identified"] = num(int(v.loc[~miss, "athlete_id2"].nunique()),
                                           desc="distinct identified athletes among valid starts")
    numbers["n_rt_gt_300"] = num(int((rt["rt_s"] > 0.300).sum()), desc="RTs above 0.300 s (excluded)")
    n_fs = int(started["is_fs"].sum())
    lo, hi = wilson_ci(n_fs, len(started))
    numbers["fs_per_1000_starts"] = num(round(1000 * n_fs / len(started), 3),
                                        ci=(round(1000 * lo, 3), round(1000 * hi, 3)),
                                        desc="recorded false starts per 1,000 starts (RT<0.100 or TR16.8; Wilson CI)",
                                        n_fs=n_fs, n_starts=int(len(started)))
    numbers["n_dq_non_fs_valid_rt"] = num(int((rt["is_dq"] & rt["valid"]).sum()),
                                          desc="DQs for non-start reasons whose legal RT is kept")

    # ---- 2. summaries ----------------------------------------------------------------------
    for by in (["sex"], ["round"], ["event"], ["comp_year"], ["timing"], ["era"],
               ["sex", "comp_year"], ["sex", "era"], ["sex", "event"]):
        sub = v.dropna(subset=by)
        if sub.empty:
            continue
        t = boot_summary(sub, by, n_boot=args.boot, seed=args.seed)
        tables["summary_by_" + "_".join(by)] = t
    for _, r in tables["summary_by_sex"].iterrows():
        numbers[f"median_rt_ms_{r['sex']}"] = num(round(r["median"], 2), ci=(round(r["median_lo"], 2), round(r["median_hi"], 2)),
                                                  unit="ms", desc=f"median valid RT, sex={r['sex']} (race-cluster bootstrap CI)")
        numbers[f"mean_rt_ms_{r['sex']}"] = num(round(r["mean"], 2), ci=(round(r["mean_lo"], 2), round(r["mean_hi"], 2)),
                                                unit="ms", desc=f"mean valid RT, sex={r['sex']}")
        numbers[f"sd_rt_ms_{r['sex']}"] = num(round(r["sd"], 2), unit="ms", desc=f"SD of valid RT, sex={r['sex']}")
    if "summary_by_timing" in tables:
        for _, r in tables["summary_by_timing"].iterrows():
            numbers[f"median_rt_ms_timing_{r['timing']}"] = num(
                round(r["median"], 2), ci=(round(r["median_lo"], 2), round(r["median_hi"], 2)), unit="ms",
                desc=f"median valid RT, timing system {r['timing']} (unadjusted)")

    tick("summaries")
    # ---- 3. crossed random-intercept model ------------------------------------------------------
    fx = "C(sex, Treatment('M')) + C(round, Treatment('R1')) + C(event_type, Treatment('flat'))"
    m1 = fit_formula(fx, v, "rt_ms", ["comp_year", "race_id", "athlete_id2"], method="REML")
    extra["m1_coef"] = m1.coef_table().reset_index().rename(columns={"index": "term"}).to_dict("records")
    extra["m1_var_ms2"] = {**m1.var_comp, "residual": m1.sigma2}
    numbers["sex_diff_W_minus_M_ms"] = coef_ms(m1, "C(sex, Treatment('M'))[T.W]",
                                               "women minus men, adjusted for round, event type, championship/race/athlete effects")
    for r in rounds_present:
        if r == "R1":
            continue
        nm = f"C(round, Treatment('R1'))[T.{r}]"
        if nm in m1.names:
            numbers[f"round_{r}_minus_R1_ms"] = coef_ms(m1, nm, f"round {r} minus first round (adjusted)")
    for e in ("200m", "hurdles"):
        nm = f"C(event_type, Treatment('flat'))[T.{e}]"
        if nm in m1.names:
            numbers[f"event_{e}_minus_flat_ms"] = coef_ms(m1, nm, f"{e} minus flat sprints (100 m, indoor 60 m), adjusted")
    for comp_name, key in (("comp_year", "championship"), ("race_id", "race"), ("athlete_id2", "athlete")):
        sd, lo_, hi_ = sd_ci(m1, comp_name)
        numbers[f"sd_{key}_ms"] = num(round(sd, 3), ci=(round(lo_, 3), round(hi_, 3)), unit="ms",
                                      desc=f"random-intercept SD: {key} (REML, delta-method CI)")
    numbers["sd_residual_ms"] = num(round(float(np.sqrt(m1.sigma2)), 3), unit="ms", desc="residual SD (REML)")
    icc, ilo, ihi = ratio_ci(m1, ["race_id"], ["race_id", "athlete_id2"])
    numbers["icc_race_within_compyear"] = num(round(icc, 4), ci=(round(ilo, 4), round(ihi, 4)),
                                              desc="race variance / (race + athlete + residual): within-championship race ICC")
    ish, slo, shi = ratio_ci(m1, ["athlete_id2"], ["race_id", "athlete_id2"])
    numbers["share_athlete_within_compyear"] = num(round(ish, 4), ci=(round(slo, 4), round(shi, 4)),
                                                   desc="athlete variance / (race + athlete + residual)")
    csh, clo, chi = ratio_ci(m1, ["comp_year"], ["comp_year", "race_id", "athlete_id2"])
    numbers["share_compyear_total"] = num(round(csh, 4), ci=(round(clo, 4), round(chi, 4)),
                                          desc="championship variance / total RT variance")
    sd_within = float(np.sqrt(m1.var_comp["race_id"] + m1.var_comp["athlete_id2"] + m1.sigma2))
    numbers["sd_rt_within_compyear"] = num(round(sd_within, 3), unit="ms",
                                           desc="SD of RT within championship after sex/round/event (race+athlete+residual)")

    tick("crossed model")
    # ---- 4. meet effects ------------------------------------------------------------------------
    if len(comps) >= 2:
        mf = fit_formula(fx + " + C(comp_year, Sum)", v, "rt_ms", ["race_id", "athlete_id2"], method="ML")
        m0 = fit_formula(fx, v, "rt_ms", ["race_id", "athlete_id2"], method="ML")
        stat, df_, p = lrt(mf, m0)
        numbers["lrt_meet_chi2"] = num(round(stat, 3), desc="LRT: championship fixed effects vs none (ML)",
                                       df=df_, p=float(f"{p:.3g}"))
        names = mf.names
        idx = [i for i, n in enumerate(names) if n.startswith("C(comp_year, Sum)")]
        levels = sorted(v["comp_year"].unique())
        rows = []
        for j, lev in enumerate(levels):
            L = np.zeros(len(names))
            if j < len(idx):
                L[idx[j]] = 1.0
            else:
                L[idx] = -1.0
            est, lo_, hi_, se = mf.contrast(L)
            rows.append({"comp_year": lev, "deviation_ms": est, "lo": lo_, "hi": hi_, "se": se,
                         "n": int((v["comp_year"] == lev).sum())})
        me = pd.DataFrame(rows)
        tables["meet_effects"] = me
        numbers["meet_effect_range_ms"] = num(round(float(me["deviation_ms"].max() - me["deviation_ms"].min()), 3),
                                              unit="ms", desc="max minus min championship deviation (adjusted)",
                                              fastest=me.loc[me["deviation_ms"].idxmin(), "comp_year"],
                                              slowest=me.loc[me["deviation_ms"].idxmax(), "comp_year"])
    timing_levels = sorted(v["timing"].dropna().unique())
    if len(timing_levels) == 2:
        vt = v.dropna(subset=["timing"])
        mt = fit_formula(fx + f" + C(timing, Treatment('{timing_levels[1]}'))", vt, "rt_ms",
                         ["comp_year", "race_id", "athlete_id2"], method="REML")
        nm = f"C(timing, Treatment('{timing_levels[1]}'))[T.{timing_levels[0]}]"
        k_t = vt.groupby("timing")["comp_year"].nunique().to_dict()
        numbers["timing_diff_ms"] = coef_ms(mt, nm, f"{timing_levels[0]} minus {timing_levels[1]} (adjusted; comp-level contrast)")
        numbers["timing_diff_ms"]["n_comps"] = {str(a): int(b) for a, b in k_t.items()}

    tick("meet effects")
    # ---- 5. trend and eras ---------------------------------------------------------------------------
    if max(years) - min(years) >= 10:
        v["decade_c"] = (v["year"] - 2010) / 10.0
        mtr = fit_formula(fx + " + decade_c", v, "rt_ms", ["comp_year", "race_id", "athlete_id2"], method="REML")
        numbers["trend_ms_per_decade"] = coef_ms(mtr, "decade_c", "linear trend in RT per decade (championship random effect)")
        if v["era"].nunique() >= 2:
            eras = sorted(v["era"].unique(), key=lambda e: {"pre-2003": 0, "2003-2009": 1, "2010+": 2}[e])
            mer = fit_formula(fx + f" + C(era, Treatment('{eras[0]}'))", v, "rt_ms",
                              ["comp_year", "race_id", "athlete_id2"], method="REML")
            for e in eras[1:]:
                numbers[f"era_{e}_minus_{eras[0]}_ms"] = coef_ms(mer, f"C(era, Treatment('{eras[0]}'))[T.{e}]",
                                                              f"rule era {e} minus {eras[0]} (adjusted)")

    tick("trend/eras")
    # ---- 6. near-threshold ---------------------------------------------------------------------------
    v["lt105"] = v["rt_s"] < 0.105
    v["lt110"] = v["rt_s"] < 0.110
    v["lt120"] = v["rt_s"] < 0.120
    for col, lab in (("lt105", "0.100-0.105"), ("lt110", "0.100-0.110"), ("lt120", "0.100-0.120")):
        for sex in sorted(v["sex"].unique()):
            est, lo_, hi_, k_, n_ = boot_share(v[v["sex"] == sex], col, seed=args.seed)
            numbers[f"share_{col}_{sex}"] = num(round(est, 5), ci=(round(lo_, 5), round(hi_, 5)),
                                                desc=f"share of valid RTs in [{lab}) s, sex={sex} (race-cluster bootstrap)",
                                                k=k_, n=n_)
    started["fs"] = started["is_fs"].astype(bool)
    fs_rows = []
    for by in ("sex", "era", "comp_year"):
        for key, g in started.groupby(by, sort=True):
            k_, n_ = int(g["fs"].sum()), int(len(g))
            lo_, hi_ = wilson_ci(k_, n_)
            fs_rows.append({"by": by, "level": key, "fs": k_, "starts": n_,
                            "per_1000": 1000 * k_ / n_, "lo": 1000 * lo_, "hi": 1000 * hi_})
    tables["false_starts"] = pd.DataFrame(fs_rows)
    bins = np.round(np.arange(0.060, 0.2501, 0.002), 3)
    hist_rows = []
    for sex in sorted(started["sex"].unique()):
        x = started.loc[(started["sex"] == sex) & started["rt_s"].notna(), "rt_s"].to_numpy(float)
        c, _ = np.histogram(x, bins=bins)
        hist_rows += [{"sex": sex, "lo": float(bins[i]), "hi": float(bins[i + 1]), "count": int(c[i])}
                      for i in range(len(c))]
    tables["hist_2ms"] = pd.DataFrame(hist_rows)
    tables["year_sex"] = tables["summary_by_sex_comp_year"].merge(
        v.groupby("comp_year")[["year", "comp"]].first().reset_index(), on="comp_year")

    tick("near-threshold")
    # ---- 7. distribution fits ----------------------------------------------------------------------
    # 7a pooled per sex on raw RT (mixes meets; comparable to published unconditional tails)
    fits, fit_rows = {}, []
    rng = np.random.default_rng(args.seed + 7)
    for sex in sorted(v["sex"].unique()):
        vs = v[v["sex"] == sex]
        x = vs["rt_s"].to_numpy(float)
        per_race = [g.to_numpy(float) for _, g in vs.groupby("race_id", sort=True)["rt_s"]]
        for lo_t in (0.100, 0.110):
            fam_fits = rtdist.fit_all(x, lo=lo_t, hi=0.300)
            boots = {f: [] for f in fam_fits}
            if lo_t == 0.100 and args.fit_boot > 0:
                for b in range(min(args.fit_boot, 100)):
                    xb = np.concatenate([per_race[i] for i in rng.integers(0, len(per_race), len(per_race))])
                    for f in fam_fits:
                        boots[f].append(rtdist.mass_below(rtdist.fit_family(xb, f, lo_t, 0.300, start=fam_fits[f].params), FS_THRESHOLD))
            for f, fit in fam_fits.items():
                ks, ksp = rtdist.truncated_ks(fit, x)
                row = {"sex": sex, "family": f, "lo": lo_t, "n": fit.n, "aic": fit.aic, "loglik": fit.loglik,
                       "ks": ks, "ks_p_approx": ksp, "mass_below_100": rtdist.mass_below(fit, FS_THRESHOLD),
                       **{f"p_{k}": val for k, val in fit.params.items()}}
                if boots[f]:
                    row["mass_lo"], row["mass_hi"] = np.percentile(boots[f], [2.5, 97.5])
                fit_rows.append(row)
                if lo_t == 0.100:
                    fits[f"pooled_{sex}_{f}"] = fit.as_dict()
    fit_df = pd.DataFrame(fit_rows)
    tables["dist_fits_pooled"] = fit_df
    for sex in sorted(v["sex"].unique()):
        sub = fit_df[(fit_df["sex"] == sex) & (fit_df["lo"] == 0.100)].sort_values("aic")
        numbers[f"best_family_pooled_{sex}"] = num(sub.iloc[0]["family"], desc=f"lowest-AIC family (pooled raw RT), sex={sex}",
                                                   aic_gap_next=float(sub["aic"].iloc[1] - sub["aic"].iloc[0]))
        for _, r in sub.iterrows():
            ci = (float(f"{r['mass_lo']:.4g}"), float(f"{r['mass_hi']:.4g}")) if pd.notna(r.get("mass_lo")) else None
            numbers[f"tail_mass_pooled_{r['family']}_{sex}"] = num(
                float(f"{r['mass_below_100']:.4g}"), ci=ci,
                desc=f"fitted P(RT<0.100) for a gun-triggered start, pooled over meets, {r['family']}, sex={sex} "
                     "(left-truncated fit; race-cluster bootstrap CI) - an extrapolation")

    tick("7a pooled fits")
    # 7b per meet x sex (raw RT): how the threshold's implied false-positive rate varies by meet
    meet_rows = []
    rng_m = np.random.default_rng(args.seed + 11)
    for (cy, sex), g in v.groupby(["comp_year", "sex"], sort=True):
        x = g["rt_s"].to_numpy(float)
        per_race = [a.to_numpy(float) for _, a in g.groupby("race_id", sort=True)["rt_s"]]
        for f in ("exgauss", "slognorm"):
            fit = rtdist.fit_family(x, f, 0.100, 0.300)
            m = rtdist.mass_below(fit, FS_THRESHOLD)
            nb_ = args.meet_boot if f == "exgauss" else 0      # CIs for the primary family only (runtime)
            bs = [rtdist.mass_below(rtdist.fit_family(np.concatenate(
                [per_race[i] for i in rng_m.integers(0, len(per_race), len(per_race))]), f, 0.100, 0.300, start=fit.params), FS_THRESHOLD)
                for _ in range(nb_)]
            meet_rows.append({"comp_year": cy, "sex": sex, "family": f, "n": len(x), "races": len(per_race),
                              "mass_below_100": m,
                              "lo": np.percentile(bs, 2.5) if bs else np.nan,
                              "hi": np.percentile(bs, 97.5) if bs else np.nan,
                              **{f"p_{k}": val for k, val in fit.params.items()}})
    mt_df = pd.DataFrame(meet_rows)
    tables["tail_mass_by_meet"] = mt_df
    for sex in sorted(v["sex"].unique()):
        sub = mt_df[(mt_df["sex"] == sex) & (mt_df["family"] == "exgauss")]
        hi_r, lo_r = sub.loc[sub["mass_below_100"].idxmax()], sub.loc[sub["mass_below_100"].idxmin()]
        numbers[f"tail_mass_meet_max_{sex}"] = num(float(f"{hi_r['mass_below_100']:.4g}"),
                                                   ci=(float(f"{hi_r['lo']:.4g}"), float(f"{hi_r['hi']:.4g}")),
                                                   desc=f"highest per-meet fitted P(RT<0.100), ex-Gaussian, sex={sex}",
                                                   meet=hi_r["comp_year"])
        numbers[f"tail_mass_meet_min_{sex}"] = num(float(f"{lo_r['mass_below_100']:.4g}"),
                                                   ci=(float(f"{lo_r['lo']:.4g}"), float(f"{lo_r['hi']:.4g}")),
                                                   desc=f"lowest per-meet fitted P(RT<0.100), ex-Gaussian, sex={sex}",
                                                   meet=lo_r["comp_year"])

    tick("7b per-meet fits")
    # 7c reference distribution: RT at an average meet, first round, 100 m (meet + round/event
    #     effects removed with the ML meet model), fitted with per-observation truncation.
    ref, ref_rows = {}, []
    if len(comps) >= 2:
        Xmf = patsy.dmatrix(mf.design_info, v, return_type="dataframe")
        cols = [i for i, n in enumerate(mf.names) if n.startswith(("C(comp_year", "C(round", "C(event_type"))]
        shift_ms = Xmf.to_numpy()[:, cols] @ mf.beta[cols]
    else:
        shift_ms = np.zeros(len(v))
    v["ref_ms"] = v["rt_ms"] - shift_ms
    v["ref_lo_ms"] = 100.0 - shift_ms
    v["ref_hi_ms"] = 300.0 - shift_ms
    rng_r = np.random.default_rng(args.seed + 13)
    for sex in sorted(v["sex"].unique()):
        vs = v[v["sex"] == sex]
        x = (vs["ref_ms"] / 1000).to_numpy()
        lo_a = (vs["ref_lo_ms"] / 1000).to_numpy()
        hi_a = (vs["ref_hi_ms"] / 1000).to_numpy()
        race_arr = vs["race_id"].to_numpy()
        grp = [np.flatnonzero(race_arr == r) for r in sorted(set(race_arr))]
        for f in ("exgauss", "slognorm", "swald"):
            fit = rtdist.fit_family(x, f, lo_a, hi_a)
            draws = []
            for _ in range(args.fit_boot):
                ii = np.concatenate([grp[i] for i in rng_r.integers(0, len(grp), len(grp))])
                draws.append(rtdist.fit_family(x[ii], f, lo_a[ii], hi_a[ii], start=fit.params).params)
            ms = [rtdist.mass_below(rtdist.Fit(f, d, 0, 0, 0.1, 0.3), FS_THRESHOLD) for d in draws]
            ref[f"{sex}_{f}"] = {"params": fit.params, "loglik": fit.loglik, "aic": fit.aic, "n": fit.n,
                                 "boot_params": draws}
            ref_rows.append({"sex": sex, "family": f, "n": fit.n, "aic": fit.aic,
                             "mass_below_100": rtdist.mass_below(fit, FS_THRESHOLD),
                             "lo": np.percentile(ms, 2.5) if ms else np.nan,
                             "hi": np.percentile(ms, 97.5) if ms else np.nan,
                             **{f"p_{k}": val for k, val in fit.params.items()}})
    ref_df = pd.DataFrame(ref_rows)
    tables["dist_fits_reference"] = ref_df
    for _, r in ref_df.iterrows():
        ci = (float(f"{r['lo']:.4g}"), float(f"{r['hi']:.4g}")) if pd.notna(r["lo"]) else None
        numbers[f"tail_mass_ref_{r['family']}_{r['sex']}"] = num(
            float(f"{r['mass_below_100']:.4g}"), ci=ci,
            desc=f"fitted P(RT<0.100), average championship / first round / flat sprint, {r['family']}, sex={r['sex']} "
                 "(per-observation truncation; race-cluster bootstrap CI) - an extrapolation")

    tick("7c reference fits")
    # 7d within-athlete distribution: conditional residuals of the crossed REML model
    within = {}
    Xm1 = patsy.dmatrix(m1.design_info, v, return_type="dataframe").to_numpy()
    zu = (v["comp_year"].astype(str).map(m1.blups["comp_year"]).to_numpy(float) +
          v["race_id"].astype(str).map(m1.blups["race_id"]).to_numpy(float) +
          v["athlete_id2"].astype(str).map(m1.blups["athlete_id2"]).to_numpy(float))
    fitted_ms = Xm1 @ m1.beta + zu
    e_ms = v["rt_ms"].to_numpy() - fitted_ms
    for sex in sorted(v["sex"].unique()):
        msk = (v["sex"] == sex).to_numpy()
        e = e_ms[msk] / 1000
        lo_e = (100.0 - fitted_ms[msk]) / 1000
        hi_e = (300.0 - fitted_ms[msk]) / 1000
        fe = rtdist.fit_family(e, "exgauss", lo_e, hi_e)
        within[sex] = {"params_s": fe.params, "n": fe.n, "resid_sd_ms": float(np.std(e_ms[msk])),
                       "note": "ex-Gaussian fitted to conditional residuals (BLUP shrinkage leaves some "
                               "between-athlete variance in them, so within-athlete spread is if anything overstated)"}
        numbers[f"within_sigma_ms_{sex}"] = num(round(fe.params["sigma"] * 1000, 3), unit="ms",
                                                desc=f"within-athlete ex-Gaussian sigma (conditional residuals), sex={sex}")
        numbers[f"within_tau_ms_{sex}"] = num(round(fe.params["tau"] * 1000, 3), unit="ms",
                                              desc=f"within-athlete ex-Gaussian tau (conditional residuals), sex={sex}")
    # 7e fast athletes, selected without regression-to-the-mean bias: split each identified
    #    athlete's starts at random into halves A/B, rank athletes by their half-A mean
    #    (meet/round/event/sex-adjusted), fit the half-B starts of the fastest quartile.
    fast = {}
    if len(comps) >= 2 and (~miss).any():
        sex_col = [i for i, n in enumerate(mf.names) if n.startswith("C(sex")]
        sex_shift = Xmf.to_numpy()[:, sex_col] @ mf.beta[sex_col] if sex_col else np.zeros(len(v))
        v["adj_ms"] = v["ref_ms"] - sex_shift
        v["adj_lo_ms"] = v["ref_lo_ms"] - sex_shift
        v["adj_hi_ms"] = v["ref_hi_ms"] - sex_shift
        ids = v.loc[~miss].groupby("athlete_id2").size()
        elig = sorted(ids[ids >= args.min_starts].index)
        rng_f = np.random.default_rng(args.seed + 17)
        half = pd.Series(index=v.index, dtype=object)
        for a in elig:
            idx = v.index[v["athlete_id2"] == a].to_numpy()
            perm = rng_f.permutation(len(idx))
            half.loc[idx[perm[: len(idx) // 2]]] = "A"
            half.loc[idx[perm[len(idx) // 2:]]] = "B"
        v["half"] = half
        ma = v[v["half"] == "A"].groupby("athlete_id2")["adj_ms"].mean()
        cut = ma.quantile(0.25)
        fast_ids = sorted(ma[ma <= cut].index)
        b_all = v[v["half"] == "B"]
        b_fast = b_all[b_all["athlete_id2"].isin(fast_ids)]
        x = (b_fast["adj_ms"] / 1000).to_numpy()
        lo_a = (b_fast["adj_lo_ms"] / 1000).to_numpy()
        hi_a = (b_fast["adj_hi_ms"] / 1000).to_numpy()
        ff = rtdist.fit_family(x, "exgauss", lo_a, hi_a)
        grp_a = [np.flatnonzero(b_fast["athlete_id2"].to_numpy() == a) for a in fast_ids]
        grp_a = [g_ for g_ in grp_a if len(g_)]
        draws = []
        for _ in range(args.fit_boot):
            ii = np.concatenate([grp_a[i] for i in rng_f.integers(0, len(grp_a), len(grp_a))])
            draws.append(rtdist.fit_family(x[ii], "exgauss", lo_a[ii], hi_a[ii], start=ff.params).params)
        ms = [rtdist.cdf("exgauss", d_, FS_THRESHOLD) for d_ in draws]
        fast = {"params": ff.params, "boot_params": draws, "n_starts": int(len(x)), "n_athletes": len(grp_a),
                "n_eligible_athletes": len(elig), "min_starts": args.min_starts,
                "reference_level": "men, first round, flat sprint (100 m / indoor 60 m), average championship",
                "halfB_mean_fast_ms": float(b_fast["adj_ms"].mean()),
                "halfB_mean_all_ms": float(b_all["adj_ms"].mean()),
                "halfA_cut_ms": float(cut)}
        numbers["fast_group_halfB_mean_diff_ms"] = num(
            round(fast["halfB_mean_fast_ms"] - fast["halfB_mean_all_ms"], 3), unit="ms",
            desc="held-out (half-B) mean RT of the fastest-quartile athletes minus all eligible athletes "
                 "(selection on half A, so no regression-to-the-mean bias)",
            n_athletes=len(grp_a), n_eligible=len(elig))
        numbers["tail_mass_fast_group"] = num(
            float(f"{rtdist.cdf('exgauss', ff.params, FS_THRESHOLD):.4g}"),
            ci=(float(f"{np.percentile(ms, 2.5):.4g}"), float(f"{np.percentile(ms, 97.5):.4g}")) if ms else None,
            desc="fitted P(RT<0.100) per start for fastest-quartile athletes (held-out starts, ex-Gaussian, "
                 "reference level men/first round/flat sprint/average championship; athlete-cluster bootstrap) - an extrapolation")
    extra["fast_group"] = fast
    # near-threshold false starts: recorded FS with RT in [0.090, 0.100) are the ones a
    # faster-scoring system or a hold effect could plausibly produce from a legitimate reaction
    fsr = started[started["is_fs"] & started["rt_s"].notna()]
    near = fsr["rt_s"].between(0.090, 0.0999)
    numbers["fs_recorded_with_rt"] = num(int(len(fsr)), desc="recorded false starts with an RT value")
    numbers["fs_near_threshold_090_100"] = num(int(near.sum()), desc="recorded false starts with RT in [0.090, 0.100) s",
                                               by_meet={str(k): int(val) for k, val in
                                                        fsr[near].groupby("comp_year").size().items()})

    extra["reference_fits"] = ref
    extra["within_athlete"] = within
    extra["variance_components_ms2"] = {"comp_year": m1.var_comp["comp_year"], "race": m1.var_comp["race_id"],
                                        "athlete": m1.var_comp["athlete_id2"], "residual": m1.sigma2}

    tick("7d/7e")
    inputs = used + rused
    p = write_result(out, "descriptive", numbers, inputs, args.mock, tables=tables,
                     extra={**extra, "fits_pooled": fits}, seed=args.seed)
    for k, val in numbers.items():
        print(f"{k:42s} {val.get('value')!s:>12}  {val.get('ci95', '')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
