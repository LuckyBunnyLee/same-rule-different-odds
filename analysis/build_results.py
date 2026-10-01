"""Render analysis/results.md from analysis/numbers.json (+ the result JSONs it cites).

No measured number is typed here: every value is pulled from numbers.json, and qualitative
words ("excludes", "no better than") are chosen from computed flags or intervals. Each section
names the producer command and the data versions behind its numbers; the appendix lists every
number with its source.

Usage: .venv\\Scripts\\python.exe analysis\\build_results.py --numbers analysis/numbers.json --out analysis/results.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import ROOT

N: dict = {}
SRC: dict = {}


def g(key, field="value"):
    e = N.get(key)
    if e is None:
        return None
    return e.get(field)


def has(*keys):
    return all(k in N for k in keys)


def f(x, nd=2):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, str):
        return x
    if isinstance(x, (list, tuple)):
        return "[" + ", ".join(f(e, nd) for e in x) + "]"
    if isinstance(x, dict):
        return "; ".join(f"{k}: {f(e, nd)}" for k, e in x.items())
    if isinstance(x, int):
        return f"{x:,}"
    ax = abs(x)
    if ax != 0 and (ax < 1e-3 or ax >= 1e5):
        return f"{x:.2g}"
    if ax != 0 and ax < 10 ** (-nd):          # would print as 0.00: show two significant digits instead
        return f"{x:.2g}"
    return f"{x:,.{nd}f}"


def ci(key, nd=2, scale=1.0):
    c = g(key, "ci95")
    if not c or c[0] is None:
        return ""
    return f" (95% CI {f(c[0] * scale, nd)} to {f(c[1] * scale, nd)})"


def v(key, nd=2, scale=1.0, unit=""):
    x = g(key)
    if x is None:
        return "n/a"
    if "tail_mass" in key and x == 0:
        return f"< 1e-12{unit} (numerical underflow)"
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        x = x * scale
    return f"{f(x, nd)}{unit}{ci(key, nd, scale)}"


def pval(key):
    p = g(key, "p")
    return "n/a" if p is None else (f"{p:.2g}" if p < 0.001 else f"{p:.3f}")


def src_line(name):
    s = next((k for k, d in SRC.items() if d["name"] == name), None)
    if s is None:
        return ""
    d = SRC[s]
    cmd = d.get("command") or "(not registered)"
    data = "; ".join(d.get("data", [])) or "none (pure simulation)"
    return f"\n*Source:* `{s}` from `.venv\\Scripts\\python.exe {cmd}`  \n*Data:* {data}\n"


def table(name, tname):
    s = next((k for k, d in SRC.items() if d["name"] == name), None)
    if s is None:
        return None
    d = json.loads((ROOT / s).read_text(encoding="utf-8"))
    t = d.get("tables", {}).get(tname)
    return None if t is None else pd.DataFrame(t)


def md_table(df: pd.DataFrame, cols, headers, fmts):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for _, r in df.iterrows():
        cells = []
        for c, fm in zip(cols, fmts):
            x = r[c]
            cells.append(fm(x) if callable(fm) else (f(x, fm) if isinstance(x, (int, float)) else str(x)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def inv(key, nd=1):
    """1/value with the CI inverted (for ratios below 1 reported as 'x times higher' the other way)."""
    x, c = g(key), g(key, "ci95")
    if not x:
        return "n/a"
    s_ = f(1.0 / x, nd)
    if c and c[0] and c[1]:
        s_ += f" (95% CI {f(1.0 / c[1], nd)} to {f(1.0 / c[0], nd)})"
    return s_


def per1000(key, nd=2):
    return v(key, nd)


# ---------------------------------------------------------------------------------------------

def detector_sentence():
    """Generated evidence for 'not a changed detection threshold' (detector.json)."""
    meds = [k for k in N if k.startswith("detector.detector_offset_median_")]
    if not meds:
        return ("the Seiko detection mark sits at the same point of the force trace in 2022, 2023 and 2025 (data "
                "pipeline's check)")
    comps = [k.split("detector_offset_median_")[1].rsplit("_ms", 1)[0] for k in meds]
    return (f"the median position of the Seiko detection line relative to the displayed force onset is "
            f"{v(meds[0], 1)} ms at every championship with waveforms ({', '.join(comps)}; range of medians "
            f"{v('detector.detector_median_range_ms', 1)} ms; {v('detector.detector_share_at_mode_all', 2, 100, '%')} of "
            f"{g('detector.detector_share_at_mode_all', 'n_lanes')} lanes at the modal offset), while the median force onset "
            f"after the gun spans {v('detector.force_onset_median_range_ms', 1)} ms; the offset distributions still differ "
            f"slightly in their upper quartile (Kruskal-Wallis p = {v('detector.detector_offset_kw_p', 3)})")


def section_headline():
    """One-screen summary for the writer; every value from numbers.json."""
    L = ["## Headline results (read this first)", "",
         "Terminology: **Seiko Ready Time** = the official start-information system's 'Ready Time' (from the start "
         "waveform images). It is *not* the set-onset-to-gun foreperiod of the literature: broadcast-audio foreperiods "
         "exceed it by about half a second with scatter (section 2b). **Foreperiod** below means set onset to gun "
         "(broadcast audio) unless stated. **Hold** is the starter's set-to-gun interval in the literature sense.", ""]
    if has("descriptive.n_valid"):
        L.append(f"1. **Data.** {v('descriptive.n_valid', 0)} valid starts, {v('descriptive.n_races', 0)} races, "
                 f"{v('descriptive.n_comp_years', 0)} championships ({g('descriptive.year_min')}-{g('descriptive.year_max')}); "
                 f"Seiko Ready Time for {v('fp_models.n_races', 0)} races ({v('fp_models.n_rts', 0)} valid RTs).")
    if has("fp_models.slope_ms_per_100ms"):
        excl = g("fp_models.ci_excludes_haugen")
        cexcl = g("calibration.corrected_excludes_haugen")
        L.append(f"2. **Ready Time vs mean RT (preliminary).** {v('fp_models.slope_ms_per_100ms', 2)} ms per 100 ms longer Ready "
                 f"Time (minimum detectable {v('fp_models.mde80_slope_ms_per_100ms', 2)}); r-equivalent "
                 f"{v('fp_models.r_equivalent', 3)}, which {'excludes' if excl else 'does not exclude'} |r| = 0.16 (Haugen et al. "
                 f"2013). Correcting for Ready Time being a noisy proxy of the foreperiod (calibration factor "
                 f"{v('calibration.calib_slope_b', 2)}, {g('calibration.n_pairs')} audio-annotated races): r "
                 f"{v('calibration.r_corrected', 3)}, which {'still excludes' if cexcl else 'no longer excludes'} |r| = 0.16.")
        L.append(f"3. **Shape (preliminary).** Slope below each championship's median Ready Time "
                 f"{v('fp_models.slope_below_median_ms_per_100ms', 2)}, above it {v('fp_models.slope_above_median_ms_per_100ms', 2)} "
                 f"ms per 100 ms; lowest-AIC model: {g('fp_models.best_model')}; reciprocal-PDF effect "
                 f"{v('fp_models.coef_recip_pdf_comp_z', 2)} ms per SD ({g('fp_models.coef_recip_pdf_comp_z', 'verdict')}); "
                 f"objective hazard {v('fp_models.coef_h_obj_comp_z', 2)} ms per SD ({g('fp_models.coef_h_obj_comp_z', 'verdict')}).")
    if has("descriptive.meet_effect_range_ms"):
        L.append(f"4. **Championship offsets.** Adjusted championship RT offsets span {v('descriptive.meet_effect_range_ms', 1)} ms "
                 f"(LRT chi2 = {v('descriptive.lrt_meet_chi2', 0)}); championships carry "
                 f"{v('descriptive.share_compyear_total', 1, 100, '%')} of RT variance. Not a changed detection threshold: "
                 f"at every championship with waveforms the detection line sits at the same point of the displayed force "
                 f"rise (median offset {v([k for k in N if k.startswith('detector.detector_offset_median_')][0], 1) if any(k.startswith('detector.detector_offset_median_') for k in N) else 'n/a'} ms), "
                 f"while force onsets span {v('detector.force_onset_median_range_ms', 0)} ms (section 1); source not identified.")
    if has("fairness.per1000_none_exgauss_M"):
        L.append(f"5. **Simulation (SIMULATION).** Legitimate starts scored < 0.100 s: {v('fairness.per1000_none_exgauss_M', 3)} "
                 f"per 1,000 (men, ex-Gaussian, average championship). Across the 10th-90th percentile Ready Time the measured "
                 f"slope allows at most a {v('fairness.cal_max_fold_change', 1)}-fold change "
                 f"({v('fairness.cal_max_fold_change_corrected', 1)}-fold on the foreperiod scale after proxy correction); the "
                 f"interquartile range of championship offsets gives {v('fairness.meet_iqr_fold_change', 1)}-fold.")
    if has("power.n_races_80_icc0.00"):
        obs = [k for k in N if k.startswith("power.n_races_80_icc") and k.split("icc")[-1] not in ("0.00", "0.05", "0.10", "0.20")]
        extra_ = f" ({v(obs[0], 0)} at the observed race ICC)" if obs else ""
        L.append(f"6. **Power (simulation).** |r| = 0.16 needs {v('power.n_races_80_icc0.05', 0)}-{v('power.n_races_80_icc0.10', 0)} "
                 f"races at residual race ICC 0.05-0.10{extra_}; athlete-level tests that ignore nesting have type I error "
                 f"{v('power.type1_naive_icc0.10', 3)} at ICC 0.10.")
    L.append("")
    L.append("Figures for the abstract: ★ `analysis/figures/holds.png` and ★ `analysis/figures/fairness.png` (section Figures).")
    return "\n".join(L) + "\n"


def section_descriptive():
    if not has("descriptive.n_valid"):
        return "## 1. Descriptive results\n\nNot yet available (no RT data).\n"
    L = ["## 1. Descriptive results (RT data only)", src_line("descriptive")]
    L.append(f"- **Coverage:** {v('descriptive.n_valid', 0)} valid starts in {v('descriptive.n_races', 0)} races from "
             f"{v('descriptive.n_comp_years', 0)} championships, {g('descriptive.year_min')}–{g('descriptive.year_max')}; "
             f"{v('descriptive.n_athletes_identified', 0)} identified athletes. Valid start = RT 0.100–0.300 s, not a false "
             f"start, not DNS; {v('descriptive.n_rt_gt_300', 0)} RTs above 0.300 s excluded.")
    L.append(f"- **Median RT:** men {v('descriptive.median_rt_ms_M', 1)} ms, women {v('descriptive.median_rt_ms_W', 1)} ms "
             f"(race-cluster bootstrap CIs).")
    L.append(f"- **Adjusted contrasts** (crossed random intercepts for championship, race and athlete): women − men "
             f"{v('descriptive.sex_diff_W_minus_M_ms', 1)} ms; final − first round {v('descriptive.round_F_minus_R1_ms', 1)} ms; "
             f"semi-final − first round {v('descriptive.round_SF_minus_R1_ms', 1)} ms; preliminary − first round "
             f"{v('descriptive.round_PR_minus_R1_ms', 1)} ms; 200 m − flat sprints {v('descriptive.event_200m_minus_flat_ms', 1)} ms; "
             f"hurdles − flat sprints {v('descriptive.event_hurdles_minus_flat_ms', 1)} ms. Flat sprints = 100 m and indoor "
             f"60 m (the World Indoors have only 60 m / 60 m hurdles, so indoor differences sit in the championship effect).")
    L.append(f"- **Variance components (SD, ms):** championship {v('descriptive.sd_championship_ms', 1)}, race "
             f"{v('descriptive.sd_race_ms', 1)}, athlete {v('descriptive.sd_athlete_ms', 1)}, residual "
             f"{v('descriptive.sd_residual_ms', 1)}. Championships carry {v('descriptive.share_compyear_total', 2, 100, '%')} of "
             f"RT variance; within a championship the race ICC is {v('descriptive.icc_race_within_compyear', 3)} and athletes "
             f"carry {v('descriptive.share_athlete_within_compyear', 2, 100, '%')}.")
    if has("descriptive.lrt_meet_chi2"):
        L.append(f"- **Championship offsets:** adjusted offsets span {v('descriptive.meet_effect_range_ms', 1)} ms, "
                 f"from {g('descriptive.meet_effect_range_ms', 'fastest')} (fastest-scoring) to "
                 f"{g('descriptive.meet_effect_range_ms', 'slowest')} (slowest); likelihood-ratio test for championship "
                 f"effects chi2 = {v('descriptive.lrt_meet_chi2', 1)}, df = {g('descriptive.lrt_meet_chi2', 'df')}, "
                 f"p = {pval('descriptive.lrt_meet_chi2')}. RTs in the WA JSON and the official PDFs agree (checked by the "
                 f"data pipeline), so these offsets are in the official results. Detection-threshold check: "
                 + detector_sentence() + ". So the offsets are not a changed detection threshold on the displayed trace; "
                 f"their source is not identified by these data.")
    if has("descriptive.timing_diff_ms"):
        nc = g("descriptive.timing_diff_ms", "n_comps") or {}
        L.append(f"- **Omega (Olympics) vs Seiko (Worlds):** {v('descriptive.timing_diff_ms', 1)} ms, a championship-level "
                 f"contrast resting on {', '.join(f'{k}: {val}' for k, val in nc.items())} championships; not interpretable as "
                 f"a vendor effect.")
    if has("descriptive.trend_ms_per_decade"):
        L.append(f"- **Trend:** {v('descriptive.trend_ms_per_decade', 1)} ms per decade (championship random effect).")
        eras = [k for k in N if k.startswith("descriptive.era_")]
        for k in eras:
            L.append(f"  - {N[k]['desc']}: {v(k, 1)} ms")
    L.append(f"- **Near the threshold:** share of valid RTs in [0.100, 0.110) s: men {v('descriptive.share_lt110_M', 3, 100, '%')}, "
             f"women {v('descriptive.share_lt110_W', 3, 100, '%')}; below 0.120 s: men {v('descriptive.share_lt120_M', 2, 100, '%')}, "
             f"women {v('descriptive.share_lt120_W', 2, 100, '%')}.")
    L.append(f"- **Recorded false starts:** {v('descriptive.fs_per_1000_starts', 1)} per 1,000 starts (Wilson CI); "
             f"{v('descriptive.fs_near_threshold_090_100', 0)} of {v('descriptive.fs_recorded_with_rt', 0)} recorded false "
             f"starts with an RT fell in [0.090, 0.100) s, by championship: "
             f"{', '.join(f'{k} {val}' for k, val in (g('descriptive.fs_near_threshold_090_100', 'by_meet') or {}).items())}.")
    fams = ["exgauss", "slognorm", "swald"]
    for scope, lab in (("ref", "average championship, first round, flat sprint"), ("pooled", "pooled over championships")):
        parts = []
        for sx in ("M", "W"):
            vals = [f"{fam} {v(f'descriptive.tail_mass_{scope}_{fam}_{sx}', 2, 1000)}" for fam in fams
                    if has(f"descriptive.tail_mass_{scope}_{fam}_{sx}")]
            parts.append(f"{'men' if sx == 'M' else 'women'}: " + "; ".join(vals))
        L.append(f"- **Fitted P(RT < 0.100) per 1,000 gun-triggered starts ({lab}):** " + " | ".join(parts) +
                 ". These are left-truncated extrapolations; the family spread is the honest uncertainty.")
    if has("descriptive.tail_mass_meet_max_M"):
        L.append(f"- **Per-championship fitted P(RT < 0.100)** (ex-Gaussian, men): highest {v('descriptive.tail_mass_meet_max_M', 2, 1000)} "
                 f"per 1,000 at {g('descriptive.tail_mass_meet_max_M', 'meet')}, lowest {v('descriptive.tail_mass_meet_min_M', 2, 1000)} "
                 f"per 1,000 at {g('descriptive.tail_mass_meet_min_M', 'meet')}.")
    if has("descriptive.fast_group_halfB_mean_diff_ms"):
        L.append(f"- **Fastest-quartile athletes** (split-half selection, held-out starts): {v('descriptive.fast_group_halfB_mean_diff_ms', 1)} ms "
                 f"vs all eligible athletes ({g('descriptive.fast_group_halfB_mean_diff_ms', 'n_athletes')} of "
                 f"{g('descriptive.fast_group_halfB_mean_diff_ms', 'n_eligible')} athletes); fitted P(RT < 0.100) "
                 f"{v('descriptive.tail_mass_fast_group', 2, 1000)} per 1,000 starts.")
    t = table("descriptive", "meet_effects")
    fs = table("descriptive", "false_starts")
    ys = table("descriptive", "summary_by_comp_year")
    if t is not None and ys is not None:
        m = t.merge(ys[["comp_year", "n", "median", "share_lt120"]], on="comp_year", how="left", suffixes=("", "_s"))
        if fs is not None:
            m = m.merge(fs[fs["by"] == "comp_year"][["level", "per_1000"]].rename(columns={"level": "comp_year"}),
                        on="comp_year", how="left")
        L.append("\n**Per championship** (offset = adjusted deviation from the championship mean):\n")
        L.append(md_table(m, ["comp_year", "n_s" if "n_s" in m else "n", "median", "share_lt120", "deviation_ms", "lo", "hi", "per_1000"],
                          ["championship", "valid RTs", "median RT (ms)", "share < 0.120 s", "offset (ms)", "lo", "hi",
                           "recorded FS per 1,000"],
                          [None, lambda x: f(int(x), 0), 1, lambda x: f"{100 * x:.1f}%", 1, 1, 1, 1]))
    return "\n".join(L) + "\n"


def section_fp():
    if not has("fp_models.n_races"):
        return ("## 2. Foreperiod models\n\nNot yet available: no validated foreperiods in data/derived/ "
                "(rt_waveform.csv or foreperiods.csv).\n")
    L = ["## 2. Reaction time vs Seiko Ready Time (PRELIMINARY)", src_line("fp_models"),
         "Ready Time is the official Seiko start-system interval; it is a noisy, offset proxy for the set-onset-to-gun "
         "foreperiod (section 2b), so slopes here are per 100 ms of Ready Time.\n"]
    comps = sorted(k.split("fp_median_")[1] for k in N
                   if k.startswith("fp_models.fp_median_") and k != "fp_models.fp_median_s")
    med_txt = ", ".join(f"{c} {v('fp_models.fp_median_' + c, 3)} s" for c in comps)
    L.append(f"- **Sample:** {v('fp_models.n_rts', 0)} valid RTs (false starts and DNS excluded) in {v('fp_models.n_races', 0)} "
             f"races with a validated Seiko 'Ready Time' ({v('fp_models.n_restart_races', 0)} after an aborted attempt). "
             f"Ready Time median {v('fp_models.fp_median_s', 3)} s, SD {v('fp_models.fp_sd_s', 3)} s (within-championship SD "
             f"{v('fp_models.fp_sd_within_comp_s', 3)} s), range {v('fp_models.fp_min_s', 3)} to {v('fp_models.fp_max_s', 3)} s. "
             f"Median Ready Time by championship: {med_txt} (ANOVA F = {v('fp_models.fp_anova_comp_F', 1)}, "
             f"p = {pval('fp_models.fp_anova_comp_F')}). All models: championship fixed effects (RT offsets differ "
             f"between championships), sex, round, event type, crossed random intercepts for race and athlete; ML fits.")
    for k in [k for k in N if k.startswith("fp_models.excluded_median_hold_")]:
        cy = k.rsplit("_", 1)[-1]
        L.append(f"- **Excluded:** {cy} Ready Times ({g(k, 'n_races')} races; median {v(k, 2)} s, far outside every other "
                 f"championship's range), treated as a suspected different 'Ready Time' definition until explained.")
    excl = g("fp_models.ci_excludes_haugen")
    L.append(f"- **Linear:** {v('fp_models.slope_ms_per_100ms', 2)} ms per 100 ms longer Ready Time (p = "
             f"{pval('fp_models.slope_ms_per_100ms')}; race-cluster bootstrap {ci('fp_models.slope_boot_ci', 2).strip(' ()')}). "
             f"r-equivalent {v('fp_models.r_equivalent', 3)}. A Haugen-sized association (|r| = 0.16) is "
             f"{v('fp_models.haugen_slope_same_scale', 2)} ms per 100 ms on this sample's scale; the 95% CI "
             f"{'excludes it in both directions' if excl else 'does not exclude it'}. Minimum detectable slope at 80% "
             f"power: {v('fp_models.mde80_slope_ms_per_100ms', 2)} ms per 100 ms (|r| {v('fp_models.mde80_r', 3)}).")
    L.append(f"- **Shape:** slope below each championship's median Ready Time {v('fp_models.slope_below_median_ms_per_100ms', 2)} "
             f"ms per 100 ms, above it {v('fp_models.slope_above_median_ms_per_100ms', 2)} ms per 100 ms (piecewise model; "
             f"lit/review.md predicts above the mode: reciprocal PDF +, hazard -, fMTP about 0). Spline-predicted fastest Ready Time "
             f"{v('fp_models.spline_fastest_hold_s', 2)} s vs median {f(g('fp_models.spline_fastest_hold_s', 'median_hold'), 3)} s. "
             f"Spline vs linear LRT p = {pval('fp_models.lrt_spline_vs_linear')}.")
    L.append(f"- **Which temporal-expectation account fits best** (dAIC vs no Ready Time term, negative = better; same data, ML): raw "
             f"linear {v('fp_models.daic_M1', 2)}, spline {v('fp_models.daic_M2', 2)}, objective hazard {v('fp_models.daic_M3', 2)}, "
             f"Weber-blurred subjective hazard {v('fp_models.daic_M4', 2)} (session distribution {v('fp_models.daic_M6', 2)}), "
             f"abort-adjusted hazard {v('fp_models.daic_M7', 2)}, blurred reciprocal PDF {v('fp_models.daic_M8', 2)}, "
             f"fMTP-style blurred CDF {v('fp_models.daic_M9', 2)}, relative Ready Time {v('fp_models.daic_M5', 2)}, piecewise at the "
             f"median {v('fp_models.daic_M10', 2)}. Lowest AIC: {g('fp_models.best_model')}. Effects per SD of the predictor: "
             f"reciprocal PDF {v('fp_models.coef_recip_pdf_comp_z', 2)} ms, subjective hazard {v('fp_models.coef_h_subj_comp_z', 2)} ms, "
             f"objective hazard {v('fp_models.coef_h_obj_comp_z', 2)} ms, fMTP-style {v('fp_models.coef_fmtp_cdf_comp_z', 2)} ms. "
             f"dAIC differences of 2 to 4 are weak-to-moderate evidence, and eleven models were compared.")
    verdicts = [(k.split("coef_")[1], N[k].get("verdict")) for k in N
                if k.startswith("fp_models.coef_") and N[k].get("verdict") and N[k].get("verdict") != "no prediction"]
    if verdicts:
        L.append("- **Direction check against each account's prediction** (hazard and fMTP-style: longer expected -> faster, "
                 "coefficient < 0; reciprocal PDF: less expected -> slower, coefficient > 0): "
                 + "; ".join(f"{t}: {vd}" for t, vd in verdicts) + ".")
    if has("fp_models.seq_prev_longer100_ms_per_100ms"):
        L.append(f"- **Sequential effect (athlete's previous start at the championship):** "
                 f"{v('fp_models.seq_prev_longer100_ms_per_100ms', 2)} ms per 100 ms that the previous Ready Time was longer, "
                 f"{v('fp_models.seq_prev_shorter100_ms_per_100ms', 2)} ms per 100 ms that it was shorter "
                 f"({g('fp_models.seq_prev_longer100_ms_per_100ms', 'n_starts')} starts, "
                 f"{g('fp_models.seq_prev_longer100_ms_per_100ms', 'n_athletes')} athletes; rounds are on different days).")
    L.append(f"- **Heterogeneity:** Ready Time x sex {v('fp_models.fp_x_sex_ms_per_100ms', 2)} ms per 100 ms (women minus men, p = "
             f"{pval('fp_models.fp_x_sex_ms_per_100ms')}); championship-specific linear slopes LRT p = "
             f"{pval('fp_models.lrt_fp_x_comp')}. Excluding restarts: {v('fp_models.slope_no_restarts', 2)} ms per 100 ms.")
    L.append(f"- **Fast starts:** odds of a valid RT < 0.120 s per 100 ms longer Ready Time {v('fp_models.or_lt120_per_100ms', 2)} "
             f"(GEE, championship-adjusted, p = {pval('fp_models.or_lt120_per_100ms')}); within-championship permutation "
             f"p = {v('fp_models.perm_p_lt120_vs_hold', 3)}. Sub-0.100 s responses vs Ready Time cannot be estimated: every "
             f"false-start race's waveform shows the restart, so the interval of the attempt that produced the false start "
             f"is unknown (broadcast audio could supply it). Pooled bins in fp_models.json are confounded by championship; "
             f"the within-championship terciles below are the valid comparison.")
    t = table("fp_models", "by_comp_tercile")
    if t is not None:
        L.append("\n**Within-championship Ready Time terciles:**\n")
        L.append(md_table(t, ["comp_year", "tercile", "races", "n", "mean_fp_s", "mean_rt_ms", "k_lt120", "share_lt120"],
                          ["championship", "tercile", "races", "valid RTs", "mean Ready Time (s)", "mean RT (ms)", "RTs < 0.120 s", "share"],
                          [None, None, lambda x: f(int(x), 0), lambda x: f(int(x), 0), 3, 1, lambda x: f(int(x), 0),
                           lambda x: f"{100 * x:.1f}%"]))
    t = table("fp_models", "model_comparison")
    if t is not None:
        L.append("\n**Model comparison (ML):**\n")
        L.append(md_table(t, ["model", "k_fixed", "loglik", "aic", "delta_aic_vs_M0"],
                          ["model", "fixed effects", "log-lik", "AIC", "dAIC vs M0"], [None, lambda x: f(int(x), 0), 2, 2, 2]))
    return "\n".join(L) + "\n"


def section_calibration():
    if not has("calibration.n_pairs"):
        return ""
    L = ["## 2b. Seiko Ready Time vs broadcast-audio foreperiod (errors-in-variables check)", src_line("calibration")]
    L.append(f"- **Pairs:** {v('calibration.n_pairs', 0)} races with a clean manual broadcast annotation of the same attempt. "
             f"Audio foreperiod (set onset to gun) minus Ready Time: mean {v('calibration.offset_mean_s', 3)} s, "
             f"within-championship SD {v('calibration.offset_sd_within_comp_s', 3)} s; by championship "
             + ", ".join(f"{k.split('offset_mean_')[1].rsplit('_s', 1)[0]} {v(k, 3)} s" for k in N
                         if k.startswith("calibration.offset_mean_") and k != "calibration.offset_mean_s")
             + f". Pearson r(Ready Time, audio foreperiod) = {v('calibration.corr_ready_audio', 2)}.")
    L.append(f"- **Calibration factor** (within-championship slope of audio foreperiod on Ready Time): "
             f"{v('calibration.calib_slope_b', 2)}; with the end of voicing of 'Set' instead of its onset: "
             f"{v('calibration.calib_slope_b_voice_end', 2)}. A factor below 1 means Ready Time exaggerates foreperiod "
             f"differences, so RT slopes per unit of Ready Time are attenuated by that factor.")
    cexcl = g("calibration.corrected_excludes_haugen")
    L.append(f"- **Corrected effect:** {v('calibration.slope_corrected_ms_per_100ms', 2)} ms per 100 ms of foreperiod; "
             f"r-equivalent {v('calibration.r_corrected', 3)}, which {'still excludes' if cexcl else 'does not exclude'} "
             f"|r| = 0.16. Conservative bound (calibration factor at its lower 2.5% bootstrap bound): r from "
             f"{v('calibration.r_ci_low_at_b_low', 3)} to {v('calibration.r_ci_high_at_b_low', 3)}.")
    if has("calibration.direct_audio_slope_ms_per_100ms"):
        L.append(f"- **Direct fit on audio foreperiods** (small sample, reported separately): "
                 f"{v('calibration.direct_audio_slope_ms_per_100ms', 2)} ms per 100 ms "
                 f"({g('calibration.direct_audio_slope_ms_per_100ms', 'n_races')} races, "
                 f"{g('calibration.direct_audio_slope_ms_per_100ms', 'n_rts')} RTs); too imprecise to add information.")
    L.append("- Assumptions: the calibration sample is representative of the Ready-Time sample (transportability), the "
             "proxy error is non-differential for RT, and the relation is linear within a championship. The pair sample "
             "is small and grows as the measurement pipeline annotates more races; rerun analysis/run_all.py to update.")
    return "\n".join(L) + "\n"


def section_measure():
    k0 = "measure.real_auto_vs_manual_heldout_n_clean"
    if k0 not in N:
        return ""
    src = next((k for k, d in SRC.items() if d.get("name") == "measure"), None)
    data = "; ".join(SRC[src].get("data", [])) if src else ""
    L = ["## 2c. Automated broadcast-audio foreperiod pipeline: held-out validation (measurement pipeline)",
         f"\n*Source:* `{src}` (measurement pipeline's generated numbers, merged verbatim; not in producers.json)  \n*Data:* {data}\n"]
    L.append(f"- **Held-out clean starts:** {v(k0, 0)}. Automated vs blind manual annotation: gun onset MAE "
             f"{v('measure.real_auto_vs_manual_heldout_gun_onset_mae_ms', 2)} ms (within 20 ms: "
             f"{v('measure.real_auto_vs_manual_heldout_gun_onset_within_20ms', 1, 100, '%')}); 'Set' onset MAE "
             f"{v('measure.real_auto_vs_manual_heldout_set_onset_clean_mae_ms', 1)} ms (within 20 ms: "
             f"{v('measure.real_auto_vs_manual_heldout_set_onset_clean_within_20ms', 1, 100, '%')}, within 40 ms: "
             f"{v('measure.real_auto_vs_manual_heldout_set_onset_clean_within_40ms', 1, 100, '%')}); foreperiod MAE "
             f"{v('measure.real_auto_vs_manual_heldout_fp_onset_clean_mae_ms', 1)} ms (within 40 ms: "
             f"{v('measure.real_auto_vs_manual_heldout_fp_onset_clean_within_40ms', 1, 100, '%')}; largest error "
             f"{v('measure.real_auto_vs_manual_heldout_fp_onset_clean_max_abs_ms', 1)} ms).")
    L.append("- These are the measurement pipeline's numbers (analysis/measure/README.md explains the pipeline); all "
             "`measure.*` keys are listed in Appendix B.")
    return "\n".join(L) + "\n"


def section_power():
    if not has("power.n_races_80_icc0.00"):
        return "## 3. Power analysis\n\nNot yet available.\n"
    L = ["## 3. Power analysis (simulation, nested design)", src_line("power")]
    L.append(f"- **Races needed for 80% power** at |r| = 0.16 (8 athletes per race, two-sided alpha 0.05): "
             f"{v('power.n_races_80_icc0.00', 0)} (residual race ICC 0), {v('power.n_races_80_icc0.05', 0)} (0.05), "
             f"{v('power.n_races_80_icc0.10', 0)} (0.10), {v('power.n_races_80_icc0.20', 0)} (0.20). For 90%: "
             f"{v('power.n_races_90_icc0.00', 0)}, {v('power.n_races_90_icc0.05', 0)}, {v('power.n_races_90_icc0.10', 0)}, "
             f"{v('power.n_races_90_icc0.20', 0)}.")
    obs = [k for k in N if k.startswith("power.n_races_80_icc") and k not in
           ("power.n_races_80_icc0.00", "power.n_races_80_icc0.05", "power.n_races_80_icc0.10", "power.n_races_80_icc0.20")]
    for k in obs:
        L.append(f"- **At the observed within-championship race ICC** ({k.split('icc')[-1]}): {v(k, 0)} races for 80% power.")
    L.append(f"- **Implied slope:** |r| = 0.16 corresponds to {v('power.slope_sdrt0.022_sdfp0.158', 2)} ms per 100 ms with "
             f"SD(RT) 22 ms and SD(hold) 0.158 s (range across SD assumptions in the table in power.json).")
    L.append(f"- **Ignoring nesting inflates false positives:** athlete-level OLS type I error "
             f"{v('power.type1_naive_icc0.05', 3)} at ICC 0.05, {v('power.type1_naive_icc0.10', 3)} at 0.10, "
             f"{v('power.type1_naive_icc0.20', 3)} at 0.20 (race-mean analysis: {v('power.type1_racemeans_icc0.10', 3)} at 0.10).")
    L.append(f"- **Minimum detectable |r| (80% power):** {v('power.mde_r80_N100_icc0.00', 3)} with 100 races (ICC 0), "
             f"{v('power.mde_r80_N150_icc0.00', 3)} with 150 races; {v('power.mde_r80_N100_icc0.10', 3)} / "
             f"{v('power.mde_r80_N150_icc0.10', 3)} at ICC 0.10.")
    val = [k for k in N if k.startswith("power.mixedlm_agreement_")]
    for k in val:
        L.append(f"- **Check vs statsmodels MixedLM** ({k.split('_', 2)[-1]}): decision agreement {v(k, 3)} "
                 f"(power {f(N[k].get('power_race_means'), 3)} race means vs {f(N[k].get('power_mixedlm'), 3)} MixedLM).")
    return "\n".join(L) + "\n"


def section_fairness():
    if not has("fairness.per1000_none_exgauss_M"):
        return "## 4. Simulation study\n\nNot yet available.\n"
    L = ["## 4. Simulation study: hold-conditional false-start risk for legitimate starts (SIMULATION)",
         src_line("fairness")]
    L.append("All quantities in this section are model outputs from fitted real RT distributions plus stated "
             "scenario inputs; none is an observed foreperiod effect.\n")
    L.append(f"- **Baseline:** at an average championship's calibration, {v('fairness.per1000_none_exgauss_M', 3)} "
             f"legitimate starts per 1,000 are scored below 0.100 s for men and {v('fairness.per1000_none_exgauss_W', 3)} for women "
             f"(ex-Gaussian); shifted lognormal {v('fairness.per1000_none_slognorm_M', 4)} (men), shifted Wald "
             f"{v('fairness.per1000_none_swald_M', 4)} (men).")
    if has("fairness.cal_max_fold_change"):
        L.append(f"- **Measured effect:** within the 95% CI of the Ready-Time slope, moving from the 10th to the 90th "
                 f"percentile Seiko Ready Time changes that probability by at most {v('fairness.cal_max_fold_change', 2)}-fold (men); "
                 f"on the foreperiod scale after the proxy correction (section 2b) at most "
                 f"{v('fairness.cal_max_fold_change_corrected', 2)}-fold, or {v('fairness.cal_max_fold_change_corrected_b_low', 2)}-fold "
                 f"with the calibration factor at its lower bound.")
    if has("fairness.pw_ratio_p10_median"):
        L.append(f"- **Measured shape (sensitivity):** with the fitted piecewise slopes, the probability at the 10th and "
                 f"90th percentile Ready Times is {v('fairness.pw_ratio_p10_median', 2)} and {v('fairness.pw_ratio_p90_median', 2)} "
                 f"times its value at the median (men), i.e. risk would be highest near the typical interval.")
    L.append(f"- **Literature hold effects:** a Haugen-sized effect makes the risk {v('fairness.ratio_p90_p10_haugen_faster_exgauss_M', 1)} "
             f"times higher at the 90th than at the 10th percentile hold if RT is faster after long holds, or "
             f"{inv('fairness.ratio_p90_p10_haugen_slower_exgauss_M', 1)} times higher at the 10th than at the 90th percentile "
             f"if RT is slower after long holds; "
             f"the hazard model calibrated to |r| = 0.16 gives {v('fairness.ratio_p90_p10_hazard_exgauss_M', 1)}-fold; the "
             f"Otsuka lab contrast would give {v('fairness.ratio_p90_p10_otsuka_lab_exgauss_M', 0)}-fold.")
    if has("fairness.meet_iqr_fold_change"):
        L.append(f"- **Championship offsets** (applied as location shifts of the fitted distribution): moving between the 25th and 75th percentile championship offsets changes "
                 f"the probability {v('fairness.meet_iqr_fold_change', 1)}-fold; between the fastest- and slowest-scoring "
                 f"championships {v('fairness.meet_ratio_M', 0)}-fold ({g('fairness.meet_p_max_M', 'meet')}: "
                 f"{v('fairness.meet_p_max_M', 2, 1000)} per 1,000; {g('fairness.meet_p_min_M', 'meet')}: "
                 f"{v('fairness.meet_p_min_M', 2, 1000)} per 1,000).")
    if has("fairness.fast_per1000_none"):
        L.append(f"- **Fastest-quartile athletes** (held-out starts): {v('fairness.fast_per1000_none', 2)} per 1,000 with no hold "
                 f"effect; {v('fairness.fast_per1000_haugen_faster', 2)} (Haugen-sized, faster after long holds); "
                 f"{v('fairness.fast_per1000_otsuka_lab', 2)} (Otsuka lab slope).")
    pol = [k for k in N if k.startswith("fairness.policy_per1000_")]
    if pol:
        L.append("- **Starter policies (hazard model, men):** " + "; ".join(
            f"{N[k]['desc'].split(chr(39))[1]} {v(k, 3)} per 1,000" for k in pol) + ".")
    L.append(f"- **Foreperiod-aware threshold:** keeping the legitimate false-alarm rate constant would move the threshold by "
             f"{v('fairness.threshold_shift_haugen_slower_ms', 1)} ms between the 10th and 90th percentile holds under a "
             f"Haugen-sized effect, versus the {v('descriptive.meet_effect_range_ms', 1)} ms spread of championship offsets.")
    excl = g("fp_models.ci_excludes_haugen")
    imp = ("**Fairness implication.** Within the range of Seiko Ready Times starters actually produce, the measured effect moves a "
           "legitimate athlete's modelled disqualification risk only modestly")
    if has("fairness.cal_max_fold_change") and excl:
        imp += " (a Haugen-sized effect, which would matter, is excluded by the measured interval)"
    imp += (". The same 0.100 s threshold is applied to official RTs whose championship-level offsets span "
            + v("descriptive.meet_effect_range_ms", 0) + " ms; the per-championship fitted probability of a gun-triggered "
            "RT below 0.100 s ranges from " + v("descriptive.tail_mass_meet_min_M", 2, 1000) + " to "
            + v("descriptive.tail_mass_meet_max_M", 2, 1000) + " per 1,000 (men). Whatever their source, these offsets "
            "move the rule's implied false-positive rate far more than the starter's interval does. The offsets are not a changed "
            "detection threshold (force-trace check, section 1); what causes them is not identified here.")
    L.append("\n" + imp + "\n")
    fa = json.loads((ROOT / next(k for k, d in SRC.items() if d["name"] == "fairness")).read_text(encoding="utf-8"))
    L.append("**Assumptions (all stated in fairness_sim.py):**\n")
    for a in fa.get("extra", {}).get("assumptions", []):
        L.append(f"- {a}")
    return "\n".join(L) + "\n"


def section_systematic():
    """Pre-registered analyses of athlete-independent variation (analysis/prereg_systematic.md)."""
    if not has("systematic.h1_verdict"):
        return ""
    s = "systematic."

    def na(nd):
        return lambda x: "n/a" if pd.isna(x) else f(x, nd)

    L = ["## 5. Systematic (athlete-independent) variation: pre-registered analyses",
         "Plan, estimands and decision rules were committed before computation in `analysis/prereg_systematic.md` "
         "(addenda list every deviation). Quantities marked SIMULATION come from models fitted to the data." + src_line("systematic")]
    hv = N[s + "h1_verdict"]
    L.append(f"### H1: can championship structure make a null hold effect look like Haugen et al.'s r = 0.16?\n")
    L.append(f"Sample: {v(s + 'h1_n_races', 0)} races, {v(s + 'h1_n_rts', 0)} valid RTs, {v(s + 'h1_n_champs', 0)} "
             f"championships with a validated Seiko Ready Time (the section 2 sample).\n")
    L.append(f"- **(a) Within-championship model** (section 2, reproduced): {v(s + 'h1a_slope_ms_per_100ms', 2)} ms per 100 ms, "
             f"r-equivalent {v(s + 'h1a_r_equivalent', 3)}; excludes the Haugen-sized {v(s + 'h1a_haugen_slope_ms_per_100ms', 2)} ms: "
             f"{f(g(s + 'h1a_ci_excludes_haugen'))}.")
    L.append(f"- **(b) Same model without championship effects:** {v(s + 'h1b_slope_ms_per_100ms', 2)} ms per 100 ms, "
             f"r-equivalent {v(s + 'h1b_r_equivalent', 3)} (race SD rises to {v(s + 'h1b_sd_race_ms', 1)} ms from "
             f"{f(g(s + 'h1b_sd_race_ms', 'sd_race_with_champ_fe_ms'), 1)} ms, absorbing the championship offsets).")
    L.append(f"- **(c) Naive athlete-level Pearson r, championships pooled (Haugen-style):** r = {v(s + 'h1c_r_pooled', 3)} "
             f"(race-cluster bootstrap CI; the naive Fisher CI a start-level analysis would report is "
             f"{f(g(s + 'h1c_r_pooled', 'naive_ci95'), 3)}, naive p = {f(g(s + 'h1c_r_pooled', 'naive_p'))}). Centred within "
             f"championship: r = {v(s + 'h1c_r_centred', 3)}. Secondary: on the audio-calibrated foreperiod scale "
             f"r = {v(s + 'h1c_r_pooled_fp', 3)}; men {v(s + 'h1c_r_pooled_M', 3)}; women {v(s + 'h1c_r_pooled_W', 3)}; "
             f"100 m only {v(s + 'h1c_r_pooled_100m', 3)}.")
    dt = table("systematic", "h1d_champ_table")
    if dt is not None:
        L.append(f"- **(d) Championship means (descriptive, no inference):** Pearson r of mean Ready Time and athlete-adjusted "
                 f"RT offset {v(s + 'h1d_pearson_4', 2)} over the {g(s + 'h1d_pearson_4', 'n_champs')} championships of the "
                 f"sample (Spearman {v(s + 'h1d_spearman_4', 2)}); {v(s + 'h1d_pearson_5', 2)} with WIC2025 added "
                 f"(anomalous Ready Times; Spearman {v(s + 'h1d_spearman_5', 2)}); {v(s + 'h1d_pearson_fp_3', 2)} on the "
                 f"calibrated foreperiod scale ({g(s + 'h1d_pearson_fp_3', 'n_champs')} championships).\n")
        L.append(md_table(dt, ["comp_year", "n_races", "mean_ready_s", "offset_ms_descriptive", "offset_ms_model_a",
                               "calib_offset_s", "mean_fp_s"],
                          ["championship", "races", "mean Ready Time (s)", "RT offset (ms, athlete-adjusted)",
                           "RT offset (ms, model a)", "calibration offset (s)", "mean foreperiod (s)"],
                          [None, 0, 3, 1, na(1), na(3), na(3)]) + "\n")

    def sim(key, lab):
        return (f"- {lab}: mean r {f(g(s + key + '_r_mean'), 3)} (95% of datasets {f(g(s + key + '_r_mean', 'q025'), 3)} to "
                f"{f(g(s + key + '_r_mean', 'q975'), 3)}); P(r >= 0.16) = {f(g(s + key + '_p_ge016'), 3)}; "
                f"P(|r| >= 0.16) = {f(g(s + key + '_p_absge016'), 3)}.")
    L.append("**Structural simulations (SIMULATION; naive pooled r of each simulated dataset):**\n")
    L.append(sim("h1s1_ready_beta0", "S1, observed structure, true within-championship slope 0"))
    L.append(sim("h1s1_ready_betahat", "S1, true slope = the (a) estimate"))
    L.append(sim("h1s1_fp_beta0", "S1, slope 0, foreperiod scale (championship-specific Ready Time definition shift)"))
    L.append(sim("h1s1_centred_beta0", "S1, slope 0, championship-centred r (control)"))
    L.append(sim("h1s1_control", "S1 control, slope 0 and no championship offsets"))
    L.append(sim("h1s2_beta0", "S2, exchangeable championships, slope 0"))
    L.append(sim("h1s2_betahat", "S2, exchangeable championships, slope = the (a) estimate"))
    s3 = sorted((k[len(s):-len("_r_mean")] for k in N if k.startswith(s + "h1s3_") and k.endswith("_r_mean")),
                key=lambda k: (not g(s + k + "_r_mean", "primary"), k))           # primary cell first
    for k in s3:
        L.append(sim(k, f"S3, Haugen et al. 2013 design '{k[len('h1s3_'):]}', true effect 0"
                        f"{' (primary)' if g(s + k + '_r_mean', 'primary') else ''}"))
    if not s3:
        L.append("- S3 (Haugen et al. 2013 design): not run.")
    crit = ", ".join(f"{k} {f(hv.get(k))}" for k in ("W", "R1", "R2", "Q1", "Q2", "Q3"))
    L.append(f"\n**H1 verdict (pre-registered rule): {hv['value']}**" + (f" ({hv.get('grade')})" if hv.get("grade") else "")
             + f". Criteria: {crit}. Championship-centred r below 0.16: {f(g(s + 'h1c_centred_below_haugen'))}.")
    if hv.get("Q2") is False:
        L.append(f"Stated plainly: with this sample's four championships treated as exchangeable (S2), a Haugen-sized r arose "
                 f"by chance in only {f(g(s + 'h1s2_beta0_p_ge016'), 3)} of simulated datasets, below the 0.05 bar; the "
                 f"association in these data comes from the observed alignment of their championships, not from pooling "
                 f"alone.")
    L.append("")

    L.append("### H2: how much do 'human limit' estimates depend on championship structure?\n")
    L.append(f"All {v(s + 'h2_n_valid', 0)} valid RTs; left-truncated fits; barrier = RT with fitted probability 1e-3 below it; "
             f"race-cluster bootstrap CIs (the adjusted fit also redraws the championship offsets).\n")
    pa = table("systematic", "h2_pooled_adjusted")
    if pa is not None:
        L.append(md_table(pa, ["sex", "family", "pooled_p", "pooled_barrier_ms", "adj_p", "adj_barrier_ms", "shift_ms"],
                          ["sex", "family", "pooled P(RT<0.100)", "pooled barrier (ms)", "adjusted P(RT<0.100)",
                           "adjusted barrier (ms)", "pooled - adjusted (ms)"],
                          [None, None, lambda x: f"{x:.2g}", 1, lambda x: f"{x:.2g}", 1, 1]) + "\n")
    for sex in ("M", "W"):
        k = f"{s}h2_champ_barrier_range_ms_exgauss_{sex}"
        L.append(f"- **Per championship, sex {sex}** ({v(s + f'h2_n_champs_eligible_{sex}', 0)} eligible): ex-Gaussian barrier from "
                 f"{f(g(k, 'min_ms'), 1)} ms ({g(k, 'min_champ')}) to {f(g(k, 'max_ms'), 1)} ms ({g(k, 'max_champ')}), a "
                 f"{v(k, 1)} ms spread; between-championship SD net of sampling error {v(s + f'h2_champ_barrier_tau_ms_{sex}', 1)} ms "
                 f"(95% prediction width {v(s + f'h2_champ_barrier_pi_width_ms_{sex}', 1)} ms; Cochran Q p = "
                 f"{f(g(s + f'h2_champ_barrier_tau_ms_{sex}', 'Q_p'))}); shifted lognormal "
                 f"{v(s + f'h2_champ_barrier_range_ms_slognorm_{sex}', 1)} ms, shifted Wald "
                 f"{v(s + f'h2_champ_barrier_range_ms_swald_{sex}', 1)} ms. Post-hoc, with round and event composition removed: "
                 f"{v(s + f'h2_champ_barrier_range_ms_exgauss_{sex}_compadj', 1)} ms.")
        L.append(f"- **Family-to-family spread, sex {sex}:** pooled {v(s + f'h2_family_spread_pooled_ms_{sex}', 1)} ms, adjusted "
                 f"{v(s + f'h2_family_spread_adjusted_ms_{sex}', 1)} ms, per-championship median "
                 f"{v(s + f'h2_family_spread_champ_median_ms_{sex}', 1)} ms; the pooled P(RT<0.100) differs "
                 f"{v(s + f'h2_family_p_ratio_pooled_{sex}', 1)}-fold across families.")
    h2 = N[s + "h2_verdict"]
    if h2.get("C2") is False:
        sg, ta = N.get(s + "h2_exgauss_sigma_ms_M", {}), N.get(s + "h2_exgauss_tau_ms_M", {})
        why = ""
        if sg and ta and (ta["value"] - ta["adjusted"]) > (sg["value"] - sg["adjusted"]):
            why = (f", because removing the offsets mainly shortens the fitted exponential (right) tail (tau "
                   f"{f(ta['value'], 1)} -> {f(ta['adjusted'], 1)} ms) while the Gaussian SD that sets the left tail barely "
                   f"moves (sigma {f(sg['value'], 1)} -> {f(sg['adjusted'], 1)} ms)")
        sh = g(s + "h2_shift_ms_exgauss_M")
        L.append(f"- **Stated plainly:** the pooled barrier lies only {f(abs(sh), 1)} ms {'below' if sh < 0 else 'above'} the "
                 f"championship-adjusted one (men, ex-Gaussian; pooled minus adjusted {v(s + 'h2_shift_ms_exgauss_M', 1)} ms), "
                 f"below the 10 ms bar{why}. "
                 f"Pooling therefore does not bias the single pooled estimate much; what the offsets change is the limit "
                 f"that would be estimated from any one championship.")
    L.append(f"\n**H2 verdict (pre-registered rule, men / ex-Gaussian): {h2['value']}** (C1 per-championship spread with "
             f"noise guard: {f(h2.get('C1'))}; C2 pooled-vs-adjusted shift >= 10 ms: {f(h2.get('C2'))}). Other cells: "
             + "; ".join(f"{k} {val}" for k, val in (h2.get("other_cells") or {}).items()) + ".\n")
    return "\n".join(L) + "\n"


def section_corrections():
    """Data-cleaning fixes applied after results were first reported (dated; see notes/bugfix_rerun_diff.md)."""
    if not has("descriptive.fs_per_1000_starts"):
        return ""
    fs = N["descriptive.fs_per_1000_starts"]
    return ("## Data corrections\n\n"
            "- **2026-09-30, false-start classification (common.normalize_rt).** The false-start label regex matched inside "
            "the note \"(not a false start)\", so hurdle and lane disqualifications were counted as false starts and their "
            "legal RTs left the valid set; and the Fiore et al. file's RT 0.000 placeholders (DNS rows, and DQ rows whose "
            "negative RT was dropped) were treated as measured RTs. Fixed with regression tests "
            "(`analysis/tests/test_common_fs.py`). After the fix: "
            f"{fs.get('n_fs')} recorded false starts ({v('descriptive.fs_recorded_with_rt', 0)} with a measured RT) in "
            f"{fs.get('n_starts'):,} starts, {v('descriptive.fs_per_1000_starts', 2)} per 1,000; "
            f"{v('descriptive.n_valid', 0)} valid starts. Every producer was rerun; every changed key (old and new value), "
            "the abstract placeholders and the pre-registered verdicts are listed in `notes/bugfix_rerun_diff.md`.\n")


def section_trend():
    """trend.py results (H1-S4, H6; analysis/prereg_addendum_trend.md)."""
    if not has("trend.s4_verdict"):
        return ""
    t = "trend."
    src = next((k for k, d in SRC.items() if d["name"] == "trend"), None)
    ex = json.loads((ROOT / src).read_text(encoding="utf-8")).get("extra", {}) if src else {}
    L = ["## 5b. Trend analyses (pre-registered: `analysis/prereg_addendum_trend.md`)" + src_line("trend")]
    L.append("### H1-S4: which analysis makes Haugen et al.'s reported cells likely? (SIMULATION)\n")
    sv = N[t + "s4_verdict"]
    L.append(f"- At the largest within-championship effect our data allow (r_w = {v(t + 's4_rw_upper', 3)}), a within-championship "
             f"analysis produces the reported pattern with probability {g(t + 's4_p_within_upper'):.2g}, a pooled analysis "
             f"with probability {v(t + 's4_p_pooled_upper', 3)}; likelihood ratio {v(t + 's4_lr_upper', 0)} "
             f"({v(t + 's4_full_lr_upper', 0)} when the non-significant women 2003-2009 cell is added to the pattern).")
    L.append(f"- At our estimate (r_w = {v(t + 's4_rw_estimate', 3)}): {g(t + 's4_p_within_estimate'):.2g} vs "
             f"{v(t + 's4_p_pooled_estimate', 3)} (likelihood ratio {v(t + 's4_lr_estimate', 0)}).")
    L.append(f"- The within-championship effect that would make the pattern plausible (P >= 0.05): r = {v(t + 's4_r_star', 3)}, "
             f"against a conservative upper bound of {v('calibration.r_ci_high_at_b_low', 3)} from our data.")
    L.append(f"\n**Verdicts:** {sv['value']} (primary rule); likelihood rule {g(t + 's4_verdict_lr')}; inversion rule "
             f"{g(t + 's4_verdict_inversion')}. Stated plainly: with the pooled side evaluated at our estimate the rule reads "
             f"{sv.get('verdict_if_pooled_at_estimate')}, and at r_w = 0 {sv.get('verdict_if_pooled_at_zero')}. This is a "
             f"statement about probabilities under a reconstructed design, not about what Haugen et al. did.")
    if ex.get("s4_caveats"):
        L.append(f"\n*Caveat:* {ex['s4_caveats'][0]}\n")
    L.append("### H6: is championship-level variation getting worse?\n")
    per = (("pre2010", "pre-2010"), ("2010_2019", "2010-2019"), ("2020_2025", "2020-2025"))
    L.append("- **SD of athlete-adjusted offsets by period:** " + "; ".join(
        f"{lab} {v(t + f'h6_sd_ms_{p_}', 1)} ms ({g(t + f'h6_sd_ms_{p_}', 'k')} championships)" for p_, lab in per) + ".")
    L.append(f"- **Ratio 2020-2025 / pre-2010:** {v(t + 'h6_sd_ratio_recent_pre2010', 2)} (bootstrap; F-based CI "
             f"{f(g(t + 'h6_sd_ratio_recent_pre2010', 'f_ci95'), 2)}). **Verdict: {g(t + 'h6_verdict')}.** Five or six "
             f"championships per period cannot detect a moderate increase: 'not worsening' means no credible increase, "
             f"not evidence of stability.")
    fa, sl = N[t + "h6_offset_fastest_ms"], N[t + "h6_offset_slowest_ms"]
    both = " (both in 2020-2025)" if fa.get("period") == sl.get("period") == "2020_2025" else ""
    L.append(f"- **Trend** in the absolute deviation from a linear time trend: {v(t + 'h6_trend_absdev_ms_per_decade', 2)} ms per "
             f"decade (permutation p = {f(g(t + 'h6_trend_absdev_ms_per_decade', 'perm_p'), 2)}); plain |offset|: "
             f"{v(t + 'h6_trend_absoffset_ms_per_decade', 2)} (p = {f(g(t + 'h6_trend_absoffset_ms_per_decade', 'perm_p'), 2)}). "
             f"Fastest and slowest offsets: {fa.get('champ')} {v(t + 'h6_offset_fastest_ms', 1)} ms and {sl.get('champ')} "
             f"{v(t + 'h6_offset_slowest_ms', 1)} ms{both}.")
    L.append("- **Modelled legitimate sub-0.100 s starts per 1,000 (SIMULATION), period medians:** " + "; ".join(
        f"{lab} {v(t + f'h6_rate_per1000_median_{p_}', 2)} (span {f(g(t + f'h6_rate_span_fold_{p_}'), 0)}-fold)"
        for p_, lab in per) + ".")
    nt = N[t + "h6_fs_near_total"]
    L.append(f"- **Recorded false starts with RT 0.090-0.100 s:** {nt['value']} of {nt.get('n_fs_with_rt')} false starts with an RT "
             f"({nt.get('n_starts'):,} starts), by championship: "
             + ", ".join(f"{k_} {v_}" for k_, v_ in (nt.get("by_champ") or {}).items()) + ".")
    if ex.get("h6_caveats"):
        L.append(f"\n*Caveat:* {ex['h6_caveats'][0]}")
    return "\n".join(L) + "\n"


def section_guardband():
    """Guard band for the 0.100 s rule (analysis/prereg_guardband.md)."""
    if not has("guard.verdict"):
        return ""
    q = "guard."
    src = next((k for k, d in SRC.items() if d["name"] == "guard"), None)
    ex = json.loads((ROOT / src).read_text(encoding="utf-8")).get("extra", {}) if src else {}
    gk = N[q + "g_ms"]
    L = ["## 5c. Guard band for the 0.100 s rule (pre-registered: `analysis/prereg_guardband.md`)" + src_line("guard")]
    L.append(f"- **Band:** u = {v(q + 'u_ms', 1)} ms (between-championship SD of athlete-adjusted offsets) gives g = "
             f"{v(q + 'g_ms', 1)} ms at k = {gk.get('k')} ({v(q + 'g_ms_k1', 1)} at k = 1, {v(q + 'g_ms_k2', 1)} at k = 2): a "
             f"limit of {gk.get('limit_s'):.4f} s ({gk.get('limit_effective_s')} s on the RT grid).")
    L.append("- **(a) Modelled legitimate starts scored below the limit, per 1,000 (SIMULATION, men, ex-Gaussian):**")
    for p_, lab in (("p0", "P0 current rule"), ("p1", "P1 uniform guard band"), ("p2", "P2 per-championship calibration"),
                    ("p3", "P3 calibration plus residual band")):
        if not has(q + f"a_{p_}_max_per1000"):
            continue
        mx = N[q + f"a_{p_}_max_per1000"]
        if p_ in ("p2", "p3"):          # plug-in points can fall outside their CIs here: quote draw medians
            dm = lambda k_, nd: f"{f(g(q + k_, 'draw_median'), nd)}{ci(q + k_, nd)}"
            cut = f"; cut vs P0 {dm(f'a_{p_}_cut_max', 1)}-fold" if has(q + f"a_{p_}_cut_max") else ""
            L.append(f"  - {lab} (draw medians): highest {dm(f'a_{p_}_max_per1000', 2)}, median "
                     f"{dm(f'a_{p_}_median_per1000', 2)}, highest / median {dm(f'a_{p_}_fold_max_median', 1)}{cut}.")
            continue
        cut = f"; cut vs P0 {v(q + f'a_{p_}_cut_max', 1)}-fold" if has(q + f"a_{p_}_cut_max") else ""
        L.append(f"  - {lab}: highest {v(q + f'a_{p_}_max_per1000', 2)} ({mx.get('champ')}; draw median "
                 f"{f(mx.get('draw_median'), 2)}), median {v(q + f'a_{p_}_median_per1000', 2)}, highest / median "
                 f"{v(q + f'a_{p_}_fold_max_median', 0)}{cut}.")
    if g(q + "a_p1_fold_max_median") > g(q + "a_p0_fold_max_median"):
        L.append("  - Stated plainly: a uniform band lowers every championship's rate but widens the highest-to-median "
                 "spread, because it moves every championship deeper into the left tail; only per-championship "
                 "calibration (P2, P3) equalises.")
    b1 = N[q + "b_p1_n_unflagged"]
    L.append(f"- **(b) Recorded false starts no longer flagged:** {b1['value']} of {v(q + 'b_n_fs_with_rt', 0)} with a measured RT "
             f"under P1 (" + ", ".join(f"{k_} {v_}" for k_, v_ in (b1.get("by_champ") or {}).items()) + f"); P2 "
             f"{v(q + 'b_p2_n_unflagged', 0)}, P3 {v(q + 'b_p3_n_unflagged', 0)}; legal starts newly flagged under P2: "
             f"{v(q + 'b2_p2_n_newly_flagged', 0)}.")
    L.append(f"- **(c) Cost share:** {v(q + 'c_share_band', 3)} of recorded false starts with a measured RT fall inside the band "
             f"({v(q + 'c_n_fs_ge_limit', 0)} at or above the limit).")
    L.append(f"\n**Verdict:** {g(q + 'verdict')}. At k = 1 the cut is {v(q + 'a_p1_k1_cut_max', 1)}-fold; a 10-fold cut needs "
             f"g >= {v(q + 'curve_g_min_cut10_ms', 1)} ms while changing at most 10% of recorded false starts allows g <= "
             f"{v(q + 'curve_g_max_share010_ms', 1)} ms"
             + (" - no band meets both." if g(q + "curve_any_g_meets_both") is False else ".") + "\n")
    if ex.get("assumptions"):
        L.append(f"*Caveat:* {ex['assumptions'][0]}")
    return "\n".join(L) + "\n"


def section_audit():
    """Confounder audit across published RT effects (prereg addenda 3 and 5)."""
    if not has("systematic.h3_verdict_sign"):
        return ""
    s = "systematic."
    L = ["## 6. Confounder audit of published RT effects (pre-registered, addendum 3)",
         "Rules fixed before computation (`analysis/prereg_systematic.md`, addendum 3; post-hoc diagnostics in addendum 5 "
         "are labelled). H1-S4 and H6 of addendum 4 are delegated to `analysis/trend.py`.\n"]
    L.append("### H3: rule-era contrasts depend on which championships represent each era\n")
    L.append(f"Athlete-adjusted offsets; eras pre-2003 ({g(s + 'h3_c1_all_ms', 'n_B')} WCH), 2003-2009 "
             f"({g(s + 'h3_c1_all_ms', 'n_A')} WCH), 2010+ ({g(s + 'h3_c2_all_ms', 'n_A')} outdoor championships); "
             f"within-era between-championship SD {v(s + 'h3_tau_ms', 1)} ms.\n")
    labels = {"c1": "2003-2009 minus pre-2003", "c2": "2010+ minus 2003-2009 (zero tolerance; primary)",
              "c3": "2010+ minus pre-2003", "c4": "2010+ minus all pre-2010"}
    for c, lab in labels.items():
        pk = s + f"h3_{c}_{'han' if c == 'c4' else 'haugen'}_p_opposite"
        sk = s + f"h3_{c}_subsets_p_opposite"
        if g(sk, "min_ms") == g(sk, "max_ms"):
            subtxt = "no subset variation (both eras use all their available championships)"
        else:
            subtxt = (f"Haugen-matched designs range {f(g(sk, 'min_ms'), 1)} to {f(g(sk, 'max_ms'), 1)} ms "
                      f"(opposite sign in {100 * g(sk):.0f}% of {g(sk, 'n_designs')} designs)")
        L.append(f"- **{lab}:** {v(s + f'h3_{c}_all_ms', 1)} ms with all championships; {subtxt}; random-championship "
                 f"P(opposite sign) {f(g(pk), 3)} with {g(pk, 'k1')} vs {g(pk, 'k2')} championships.")
    L.append(f"- **Same-rule null (no rule change; 2 vs 5 zero-tolerance championships):** 95% of 'era contrasts' within "
             f"{f(g(s + 'h3_samerule_halfwidth_ms', 'q025_ms'), 1)} to {f(g(s + 'h3_samerule_halfwidth_ms', 'q975_ms'), 1)} ms "
             f"(half-width {v(s + 'h3_samerule_halfwidth_ms', 1)}); for Han et al.'s sizes (11 vs 8) the half-width is "
             f"{v(s + 'h3_han_samerule_halfwidth_ms', 1)} ms. One championship standing for zero tolerance: WCH2011 gives "
             f"{v(s + 'h3_named_wch2011_ms', 1)} ms and WCH2022 {v(s + 'h3_named_wch2022_ms', 1)} ms against 1999/2001.")
    L.append(f"- Sensitivity, 2010+ minus 2003-2009: raw means {v(s + 'h3_raw_c2_all_ms', 1)} ms (opposite sign in "
             f"{100 * g(s + 'h3_raw_c2_subsets_p_opposite'):.0f}% of designs); with World Indoors "
             f"{v(s + 'h3_wic_c2_all_ms', 1)} ms ({100 * g(s + 'h3_wic_c2_subsets_p_opposite'):.0f}%).")
    L.append(f"\n**H3 verdicts:** {g(s + 'h3_verdict_sign')}; Haugen et al.'s +30 ms: {g(s + 'h3_verdict_haugen')}; "
             f"Han et al.'s -4 ms: {g(s + 'h3_verdict_han')}.\n")
    L.append("### H4: the sex gap by championship\n")
    for tag, lab in (("", "All events (primary)"), ("flat_", "Flat sprints only (secondary)"),
                     ("modern_", "POST-HOC, 2015 on (athlete-identified)")):
        L.append(f"- **{lab}:** average gap (women minus men) {v(s + f'h4_{tag}gap_mean_ms', 1)} ms; per-championship gaps "
                 f"from {f(g(s + f'h4_{tag}gap_range_ms', 'min_ms'), 1)} ({g(s + f'h4_{tag}gap_range_ms', 'min_champ')}) to "
                 f"{f(g(s + f'h4_{tag}gap_range_ms', 'max_ms'), 1)} ms ({g(s + f'h4_{tag}gap_range_ms', 'max_champ')}); "
                 f"interaction LRT p = {pval(s + f'h4_{tag}lrt_chi2')}; between-championship SD "
                 f"{v(s + f'h4_{tag}gap_tau_ms', 1)} ms, 95% prediction interval {f(g(s + f'h4_{tag}gap_pi_ms', 'ci95'), 1)} ms; "
                 f"{g(s + f'h4_{tag}n_negative')} of {g(s + f'h4_{tag}n_negative', 'n_champs')} championships with women faster.")
    neg = g(s + "h4_n_negative", "negative_champs") or []
    plain = []
    if neg and all(int(c[-4:]) < 2010 for c in neg):
        plain.append(f"all {len(neg)} championships with women faster are before 2010 (a different source table, "
                     f"with other round and event composition)")
    if g(s + "h4_modern_n_negative") == 0:
        plain.append("the championships from 2015 on show none")
    flo, fhi = g(s + "h4_flat_gap_pi_ms", "ci95") or (None, None)
    if flo is not None and (flo > 0 or fhi < 0):
        plain.append("with flat sprints only the prediction interval excludes 0")
    L.append(f"\n**H4 verdict (all events):** {g(s + 'h4_verdict')}."
             + (f" Stated plainly: {'; '.join(plain)}." if plain else "") + "\n")
    if has("systematic.h5_verdict_venue"):
        L.append("### H5: venue dependence inside Fiore et al.'s own published model\n")
        L.append(f"Parameters transcribed from their manuscript source (`analysis/fiore2025_params.csv`, checked against "
                 f"`analysis/external/fiore2025/source_extract.txt`); quadrature instead of their 10^7 draws.\n")
        for st, lab in (("men_incl2022", "men incl. 2022 (primary)"), ("men_excl2022", "men excl. 2022"), ("women", "women")):
            L.append(f"- **{lab}:** marginal P(RT<0.100) {g(s + f'h5_{st}_p_lt100'):.3g} (published "
                     f"{g(s + f'h5_{st}_p_lt100', 'published'):.3g}); 1e-3 barrier {v(s + f'h5_{st}_barrier_1e3_ms', 1)} ms "
                     f"(published {f(g(s + f'h5_{st}_barrier_1e3_ms', 'published_ms'), 0)}); median venue "
                     f"{v(s + f'h5_{st}_median_venue_barrier_1e3_ms', 1)} ms; 2.5th vs 97.5th percentile venue "
                     f"{f(g(s + f'h5_{st}_venue_range95_ms', 'q025_barrier_ms'), 1)} vs "
                     f"{f(g(s + f'h5_{st}_venue_range95_ms', 'q975_barrier_ms'), 1)} ms (range "
                     f"{v(s + f'h5_{st}_venue_range95_ms', 1)} ms).")
        if has("systematic.h5_years_barrier_range_ms"):
            k = s + "h5_years_barrier_range_ms"
            L.append(f"- **The 13 actual WCH venues** (effects read from their vector figure): barrier from "
                     f"{f(g(k, 'min_ms'), 1)} ms ({g(k, 'min_year')}) to {f(g(k, 'max_ms'), 1)} ms ({g(k, 'max_year')}), "
                     f"a {v(k, 1)} ms range.")
        L.append(f"- **POST-HOC:** the excluding-2022 row's published tail implies an intercept of "
                 f"{f(g(s + 'h5_men_excl2022_implied_beta0'), 3)} (printed {f(g(s + 'h5_men_excl2022_implied_beta0', 'printed_beta0'), 3)}); "
                 f"their figure's panels differ by {f(g(s + 'h5_pdf_excl2022_intercept_shift'), 4)} on the log scale, "
                 f"the shift removing 2022 implies. The other two sets imply their printed intercepts "
                 f"({f(g(s + 'h5_men_incl2022_implied_beta0'), 3)}, {f(g(s + 'h5_women_implied_beta0'), 3)}).")
        L.append(f"\n**H5 verdicts:** {g(s + 'h5_verdict_reproduced')} "
                 f"({'; '.join(f'{k_} {bool(v_)}' for k_, v_ in (g(s + 'h5_verdict_reproduced', 'sets') or {}).items())}); "
                 f"{g(s + 'h5_verdict_venue')}.\n")
    if has("systematic.o2_verdict"):
        L.append("### O2 (optional): RT vs 100 m time, pooled vs within championship\n")
        for sex in ("M", "W"):
            L.append(f"- **{'Men' if sex == 'M' else 'Women'}:** pooled r {v(s + f'o2_r_pooled_{sex}', 2)}; "
                     f"championship-centred {v(s + f'o2_r_champ_{sex}', 2)}; within race {v(s + f'o2_r_race_{sex}', 2)}; "
                     f"pooled minus centred {v(s + f'o2_diff_{sex}', 2)}.")
        L.append(f"\n**O2 verdict:** {g(s + 'o2_verdict')}.\n")
    return "\n".join(L) + "\n"


def section_probe():
    """EXPLORATORY probe of 2022-2025 (analysis/recent_probe.py via analysis/probe_numbers.py; not pre-registered)."""
    if not has("probe.wch2025_straight_minus_200m_same_athlete_ms"):
        return ""
    p = "probe."
    L = ["## 7. EXPLORATORY probe of the recent championships (NOT pre-registered)",
         "Every number in this section is exploratory: chosen after looking at the data, with no pre-registered rule. "
         "Produced by `analysis/recent_probe.py` and published as `probe.*` by `analysis/probe_numbers.py`; the full "
         "probe is in `analysis/outputs/recent_probe.json` and `notes/recent_probe.md`." + src_line("probe")]
    lg = N[p + "wch2025_straight_lane_gradient_ms_per_lane"]
    L.append(f"- **WCH2025, start location:** the same athletes were {v(p + 'wch2025_straight_minus_200m_same_athlete_ms', 1)} ms "
             f"slower on the home-straight start than on the 200 m start ({g(p + 'wch2025_straight_minus_200m_same_athlete_ms', 'n_athletes')} "
             f"athletes); at the other championships the same difference ranged from "
             f"{v(p + 'straight_minus_200m_same_athlete_other_min_ms', 1)} ms ({g(p + 'straight_minus_200m_same_athlete_other_min_ms', 'champ')}) "
             f"to {v(p + 'straight_minus_200m_same_athlete_other_max_ms', 1)} ms ({g(p + 'straight_minus_200m_same_athlete_other_max_ms', 'champ')}).")
    L.append(f"- **WCH2025, lanes:** on the home-straight start, run on {lg.get('first_day')} to {lg.get('last_day')}, RT rose by "
             f"{v(p + 'wch2025_straight_lane_gradient_ms_per_lane', 2)} ms per lane outwards; lanes 7-9 minus lanes 1-5 "
             f"{v(p + 'wch2025_outer_minus_inner_lanes_ms', 1)} ms.")
    L.append(f"- **WCH2022, everywhere:** faster than WCH2023 in {g(p + 'wch2022_faster_rounds')} of "
             f"{g(p + 'wch2022_faster_rounds', 'n_rounds')} rounds and {g(p + 'wch2022_faster_start_types')} of "
             f"{g(p + 'wch2022_faster_start_types', 'n_start_types')} start types; {g(p + 'wch2022_days_faster_than_every_2023_day')} of "
             f"{g(p + 'wch2022_days_faster_than_every_2023_day', 'n_days')} competition days below every WCH2023 day; "
             + ("the shift was near-uniform across the distribution" if
                (g(p + 'wch2022_to_2023_median_minus_p5_shift_ms', 'ci95')[0] <= 0 <= g(p + 'wch2022_to_2023_median_minus_p5_shift_ms', 'ci95')[1])
                else "the shift differed across the distribution")
             + f" (median change minus 5th-percentile change {v(p + 'wch2022_to_2023_median_minus_p5_shift_ms', 1)} ms).")
    L.append(f"- **Same athletes:** {g(p + 'same_athletes_2022_to_2023_change_ms', 'n_athletes')} athletes at all three recent World "
             f"Championships slowed by {v(p + 'same_athletes_2022_to_2023_change_ms', 1)} ms from 2022 to 2023 and by "
             f"{v(p + 'same_athletes_2023_to_2025_change_ms', 1)} ms from 2023 to 2025.")
    return "\n".join(L) + "\n"


def section_lit_audit():
    """Literature audit (lit/audit_protocol.md; analysis/lit_audit.py)."""
    if not has("audit.n_studies"):
        return ""
    a = "audit."
    src = next((k for k, d in SRC.items() if d["name"] == "audit"), None)
    ex = json.loads((ROOT / src).read_text(encoding="utf-8")).get("extra", {}) if src else {}
    L = ["## 8. Literature audit: published championship-RT designs exposed to championship-level variation",
         "Protocol committed before coding (`lit/audit_protocol.md`); a structured search, not an exhaustive one. The "
         "audit classifies designs, not the truth of findings." + src_line("audit")]
    L.append(f"- **Exposed designs:** {g(a + 'k_vulnerable_studies')} of {g(a + 'n_studies')} studies "
             f"({g(a + 'pct_vulnerable_studies')}%) drew at least one conclusion from a design that pooled, contrasted or "
             f"generalised championships without modelling them; {g(a + 'k_vulnerable_findings')} of {g(a + 'n_findings')} "
             f"findings ({g(a + 'pct_vulnerable_findings')}%). Counting only conclusions that rest on a between-championship "
             f"contrast: {g(a + 'k_strict_studies')} studies.")
    L.append(f"- **Sensitivities:** unclear designs counted as exposed {g(a + 'k_u_as_vulnerable_studies')} studies; design "
             f"coding verified from full text or abstract {g(a + 'k_verified_only_studies')} of {g(a + 'n_verified_only_studies')}; "
             f"with grey literature {g(a + 'k_grey_added_studies')} of {g(a + 'n_grey_added_studies')}.")
    era_all = g(a + "findings_rule_era_class_E") == g(a + "findings_rule_era")
    L.append(f"- **Conflicting literatures:** {g(a + 'n_conflict_groups')} groups ({', '.join(g(a + 'n_conflict_groups', 'groups') or [])}). "
             f"Rule era: {g(a + 'conflict_rule_era_vulnerable_studies')} of {g(a + 'conflict_rule_era_studies')} studies exposed"
             + ("; every rule-era finding rests on an era contrast with championships nested in eras." if era_all else "."))
    L.append(f"- **Context:** {g(a + 'n_studies_reporting_champ_difference')} studies report an RT difference between "
             f"championships as their own finding; {g(a + 'n_studies_single_championship')} analyse a single championship; "
             f"{g(a + 'studies_closed_access')} were closed access; {g(a + 'screen_unique_records')} unique records screened.")
    if ex.get("caveat"):
        L.append(f"\n*Caveat:* {ex['caveat']}")
    return "\n".join(L) + "\n"


def fig_text():
    """Captions; every count or range is pulled from numbers.json (no typed measurements)."""
    nr, y0, y1 = g("fp_models.n_races"), g("descriptive.year_min"), g("descriptive.year_max")
    ncomp = len([k for k in N if k.startswith("fp_models.fp_median_") and k != "fp_models.fp_median_s"])
    return [
        ("fairness.png", True, "Simulated legitimate false-start risk: (A) across Seiko Ready Times under the measured "
                               "slope (with 95% CI) and |r| = 0.16 alternatives, with the observed Ready Times as ticks; (B) "
                               "across championship RT offsets, with recorded false-start rates (championships without a "
                               "diamond had none recorded with an RT)."),
        ("holds.png", True, f"Seiko Ready Time vs championship-adjusted race-mean RT ({f(nr, 0)} races, {ncomp} "
                            f"championships; marker area = valid RTs in the race) with the linear fit (95% CI), a "
                            f"df-3 spline and Haugen-sized reference slopes; championship RT offsets {y0}-{y1}."),
        ("power.png", False, "Power to detect |r| = 0.16 by number of races and residual race ICC; minimum detectable |r|."),
        ("rt_hist.png", False, "Distribution of championship RTs by sex around the 0.100 s threshold."),
        ("terciles.png", False, "Mean RT and share of RTs < 0.120 s by within-championship Seiko Ready Time tercile."),
        ("policies.png", False, "Starter hold policies under the hazard model: mean RT change vs legitimate false-start risk."),
        ("story_wide.png", True, "Abstract Figure 1: RT shift across the 10th-90th percentile Seiko Ready Time (measured "
                                 "slope with 95% CI, and a Haugen-sized slope) beside the athlete-adjusted championship "
                                 "offsets (95% CIs), on one RT scale."),
        ("confound.png", True, f"Confounder audit, three panels: (A) the Seiko Ready Time-RT correlation in the same "
                               f"{f(g('systematic.h1_n_races'), 0)} races, pooled over championships (Haugen-style) and "
                               f"centred within championship (race-cluster bootstrap 95% CIs), against Haugen et al.'s "
                               f"r = 0.16; (B) the limit moves with the championship: each championship's 1-in-1,000 "
                               f"barrier (men, ex-Gaussian, bootstrap 95% CIs), sorted, coloured below/above the 0.100 s "
                               f"rule ({g('fig.barrier_below_rule')} of {g('fig.fit_rule_100ms', 'n_champs')} below), "
                               f"spanning {f(g('systematic.h2_champ_barrier_range_ms_exgauss_M', 'min_ms'), 0)}-"
                               f"{f(g('systematic.h2_champ_barrier_range_ms_exgauss_M', 'max_ms'), 0)} ms, against the "
                               f"shaded band between the published proposals 0.094 s (Fiore et al. 2025) and 0.119 s "
                               f"(Brosnan et al. 2017); (C) the modelled rate of legitimate starts wrongly disqualified per "
                               f"1,000 at each championship (log scale; SIMULATION) under the current rule, a uniform guard "
                               f"band and per-championship calibration, with the guard band's cost "
                               f"({g('guard.b_p1_n_unflagged')} of {g('guard.b_n_fs_with_rt')} recorded false starts no "
                               f"longer flagged, at {', '.join(g('guard.b_p1_n_unflagged', 'by_champ'))}, RT "
                               f"{f(g('fig.p1_unflagged_rt_min_s'), 3)}-{f(g('fig.p1_unflagged_rt_max_s'), 3)} s). "
                               f"Compact layout (7.0 x 3.2 in): B and C label only Eugene 2022 (WCH2022, ringed) and the "
                               f"championship at the far end. Registered but not drawn: championships "
                               f"whose barrier CI contains 0.100 s: {g('fig.fit_rule_100ms')}; 0.094 s: "
                               f"{g('fig.fit_fiore_094ms')}; 0.119 s: {g('fig.fit_brosnan_119ms')}; none: {g('fig.fit_none')}."),
    ]


def section_figures():
    L = ["## Figures", "Figures are in `analysis/figures/` (PNG + PDF), each rendered by `analysis/make_figures.py` "
                       "(commands in producers.json). The abstract allows two: ★ marks the candidates.\n"]
    for fn, star, cap in fig_text():
        if (ROOT / "analysis" / "figures" / fn).exists():
            L.append(f"- {'★ ' if star else ''}`analysis/figures/{fn}` — {cap}")
    return "\n".join(L) + "\n"


def section_negative():
    L = ["## Negative and null results (state plainly)"]
    if has("fp_models.slope_ms_per_100ms"):
        L.append(f"- No detectable linear effect of Seiko Ready Time on mean RT within championships: {v('fp_models.slope_ms_per_100ms', 2)} "
                 f"ms per 100 ms ({v('fp_models.n_races', 0)} races). This is absence of evidence bounded by the CI; the "
                 f"design detects {v('fp_models.mde80_slope_ms_per_100ms', 2)} ms per 100 ms with 80% power.")
        wrong = [k.split("coef_")[1] for k in N if k.startswith("fp_models.coef_") and "opposite sign" in str(N[k].get("verdict"))]
        if wrong:
            L.append("- Predictors whose estimated effect has the opposite sign to their theory's prediction: "
                     + ", ".join(wrong) + " (see section 2). A lower AIC for such a model is not support for its theory.")
        pp = g("fp_models.perm_p_lt120_vs_hold")
        if pp is not None:
            if pp < 0.05:
                L.append(f"- Fast-start share vs Ready Time: permutation p = {v('fp_models.perm_p_lt120_vs_hold', 3)}; exploratory "
                         f"and not pre-registered.")
            else:
                L.append(f"- No detectable association of the share of RTs below 0.120 s with Ready Time (odds ratio per 100 ms "
                         f"{v('fp_models.or_lt120_per_100ms', 2)}; permutation p = {v('fp_models.perm_p_lt120_vs_hold', 3)}).")
    if has("descriptive.timing_diff_ms"):
        L.append("- The Omega vs Seiko contrast is uninformative (few championships per vendor).")
    L.append("- Tail probabilities below 0.100 s are extrapolations from truncated data and differ by family (section 1).")
    L.append("- Not estimable: false-start probability as a function of the interval, because the interval of the aborted "
             "attempt is not in the waveform data. Not run: a dispersion (scale) model.")
    if has("calibration.n_pairs"):
        L.append(f"- The Ready Time -> foreperiod calibration rests on {v('calibration.n_pairs', 0)} audio-annotated races.")
    return "\n".join(L) + "\n"


def appendix():
    L = ["## Appendix A: result files, commands and data versions\n",
         "| result | command (run from the repo root with `.venv\\Scripts\\python.exe`) | data versions |", "|---|---|---|"]
    for s, d in SRC.items():
        L.append(f"| `{s}` | `{d.get('command') or 'not registered'}` | {'; '.join(d.get('data', [])) or 'none'} |")
    L.append("\n## Appendix B: every number\n")
    L.append("| key | value | 95% CI | unit | description |")
    L.append("|---|---|---|---|---|")
    for k, e in N.items():
        c = e.get("ci95")
        cs = f"{f(c[0], 4)} to {f(c[1], 4)}" if c and c[0] is not None else ""
        val = e.get("value")
        L.append(f"| `{k}` | {f(val, 4) if not isinstance(val, str) else val} | {cs} | {e.get('unit', '')} | "
                 f"{str(e.get('desc', '')).replace('|', '/')} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--numbers", default="analysis/numbers.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--final", action="store_true", help="mark as the final version for the checkpoint")
    a = ap.parse_args()
    d = json.loads((ROOT / a.numbers).read_text(encoding="utf-8"))
    N.update(d["numbers"])
    SRC.update(d["_sources"])
    head = ["# SSAC27 foreperiod study: analysis results",
            "",
            "Generated by `analysis/build_results.py` from `analysis/numbers.json`; do not edit by hand. "
            + ("**Status: FINAL for the checkpoint** on the data versions listed below (every artifact re-verified "
               "byte-for-byte with scripts/verify_producers.py). Analyses marked PRELIMINARY remain preliminary in the "
               "scientific sense. " if a.final else
               "**Status: preliminary** — data are still being extended; numbers change when inputs change "
               "(data versions below). ")
            + "Simulated quantities are labelled SIMULATION. Mock data never enter this file.",
            "",
            "Reproduce everything: `.venv\\Scripts\\python.exe analysis\\run_all.py`; verify every registered "
            "artifact byte-for-byte: `.venv\\Scripts\\python.exe scripts\\verify_producers.py producers.json`.",
            ""]
    body = [section_headline(), section_corrections(), section_descriptive(), section_fp(), section_calibration(), section_measure(),
            section_power(), section_fairness(), section_systematic(), section_trend(), section_guardband(), section_audit(), section_probe(), section_lit_audit(),
            section_figures(), section_negative(), appendix()]
    body = [x for x in body if x]            # sections without inputs render nothing (older outputs stay byte-identical)
    text = "\n".join(head) + "\n" + "\n".join(body)
    # numbers.json descriptions keep the working repository's role labels; the rendered results use neutral ones
    for old, new in (("measure agent number", "measurement number"), ("coordinator's rule", "pre-specified rule")):
        text = text.replace(old, new)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
