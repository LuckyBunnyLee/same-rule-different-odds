<!--
README template. Render with: python scripts/render_readme.py
Every measured number is a {{placeholder}} resolved from analysis/numbers.json (same syntax as paper/render.py).
Qualitative claims that the numbers could contradict are pinned by asserts; the renderer fails if one is false.
-->
# Same Rule, Different Odds: When the Start, Not the Sprinter, Breaks the Human Limit

**SSAC27 author (anonymised for review)**. Research paper for the MIT Sloan Sports Analytics Conference 2027 (Other Sports track).

This repository contains the data, code, pre-specified analysis plans, result files and figures behind the paper's abstract (`paper/abstract.md`). Every number below is read from `analysis/numbers.json`, the single generated file that the abstract also draws on. This README is itself rendered from `README.template.md` by `scripts/render_readme.py`.

## Summary

<!-- assert: [descriptive.meet_effect_range_ms] > (119 - 94) -->
<!-- assert: [systematic.h1c_r_pooled@lo] > 0.16 - 0.04 and [systematic.h1c_r_centred@hi] < 0.16 -->
<!-- assert: [systematic.h2_champ_barrier_range_ms_exgauss_M@min_ms] < 100 and [systematic.h2_champ_barrier_range_ms_exgauss_M@max_ms] > 100 -->
<!-- assert: [systematic.h2_champ_barrier_tau_ms_M@Q_p] < 0.001 -->
In sprinting, a reaction time (RT) under 0.100 s is a false start. We analysed {{descriptive.n_valid|,d}} official RTs from {{descriptive.n_comp_years}} global championships ({{descriptive.year_min}}-{{descriptive.year_max}}) and found that the championship itself shifts RTs: athlete-adjusted championship offsets span {{descriptive.meet_effect_range_ms|.1f}} ms, more than the gap between the two published men's limit estimates (0.094 s and 0.115 s). Re-analysing the same races as published designs did, pooled over championships, gives a hold-RT correlation of r = {{systematic.h1c_r_pooled|.2f}}; within championships it is {{systematic.h1c_r_centred|.2f}} (95% CI {{systematic.h1c_r_centred@lo|.2f}} to {{systematic.h1c_r_centred@hi|.2f}}). Per-championship "human limit" estimates run from {{systematic.h2_champ_barrier_range_ms_exgauss_M@min_ms|.1f}} to {{systematic.h2_champ_barrier_range_ms_exgauss_M@max_ms|.1f}} ms, on both sides of the rule. A uniform guard band would cut the worst modelled odds of a legitimate start being disqualified but would also clear recorded false starts; only per-championship calibration equalises the odds. Championship-level variation in official RT can manufacture effects as large as published ones and move the human limit; its source is not identified here.

## 1. The question and why it matters

World Athletics disqualifies any athlete whose start-system RT is below 0.100 s. The rule, the men's limit estimates behind proposals to change it (0.094 s, Fiore et al. 2025; 0.115 s, Brosnan et al. 2017, whose women's value is 0.119 s) and a literature of RT effects (starter holds, Haugen et al. 2013, r = 0.16; rule eras; sex; round) all treat an RT from one championship as comparable with an RT from another. We ask whether that holds, and what it means for findings and for the rule if it does not. The question matters because a disqualification is final, and because conclusions drawn from pooled championship data are used to argue for or against moving the line.

## 2. Data

Full provenance, source URLs, retrieval dates, licences and the list of files are in [DATA.md](DATA.md). In short:

- **World Athletics results** (public results pages and official results PDFs): per-athlete RTs, results, lanes and false-start labels for World Championships 2015-2025, Olympic Games 2020 and 2024 and World Indoor Championships 2024-2025 (`data/derived/rt_athletes.csv`, `races.csv`).
- **Seiko start-information images** (World Athletics): per-race "Ready Time" and per-lane force traces, read by OCR (`data/derived/rt_waveform.csv`, `rt_waveform_lanes.csv`; Ready Time for {{fp_models.n_races}} races and {{fp_models.n_rts|,d}} valid RTs).
- **Fiore et al.'s compiled World Championships RTs** (github.com/ofiore/Thesis; the source for the {{descriptive.year_min}}-2013 World Championships). That repository has no licence, so the file is not redistributed: `scripts/fetch_third_party.py` downloads it from a pinned commit, checks its sha256 and rebuilds `data/derived/rt_fiore.csv`; our own derived columns are in `data/derived/rt_fiore_mapping.csv`.
- **Broadcast audio** (official channels): set-to-gun foreperiods measured automatically and by blind reading (`data/derived/foreperiods.csv`, `analysis/measure/manual_annotations.csv`). Only derived timings and video identifiers are published, never audio or video.
- **Published designs and parameters** transcribed from the papers: `analysis/haugen_design.csv`, `analysis/fiore2025_params.csv`.
- **Literature audit**: frozen search results (bibliographic metadata), screening table and coding of included studies (`lit/audit_*`).

In total the analysis uses {{descriptive.n_valid|,d}} valid starts (RT 0.100-0.300 s, not a false start) in {{descriptive.n_races|,d}} races, from {{descriptive.n_athletes_identified|,d}} identified athletes.

## 3. Methods

- **Mixed models.** RT is modelled with crossed random intercepts for championship, race and athlete, with sex, round and event as fixed effects (`analysis/descriptive.py`, `analysis/lmm.py`). Championship offsets are the athlete-adjusted championship deviations; left-truncated ex-Gaussian, shifted-lognormal and shifted-Wald fits give tail probabilities below 0.100 s.
- **Ready Time calibration.** Seiko's Ready Time is not the set-to-gun foreperiod of the literature: in {{calibration.n_pairs}} races with a clean blind reading of broadcast audio it starts on average {{calibration.offset_mean_s|.2f}} s after the onset of "set". A regression-calibration factor ({{calibration.calib_slope_b|.2f}}, 95% CI {{calibration.calib_slope_b@lo|.2f}} to {{calibration.calib_slope_b@hi|.2f}}) converts Ready-Time slopes to the foreperiod scale (`analysis/calibration.py`). The automated audio pipeline is validated on held-out starts (foreperiod mean absolute error {{measure.real_auto_vs_manual_heldout_fp_onset_clean_mae_ms|.1f}} ms on {{measure.real_auto_vs_manual_heldout_n_clean}} clean starts; `analysis/measure/`).
- **Published-design re-analysis (H1).** The same races are analysed as a pooled, Haugen-style design and within championship (`analysis/systematic.py`).
- **Simulations.** Structural simulations generate data with no hold effect under the observed championship structure, under exchangeable championships and under a reconstruction of Haugen et al.'s design (S1-S4; `analysis/systematic.py`, `analysis/trend.py`); `analysis/fairness_sim.py` models the rate at which legitimate, gun-triggered starts are scored below 0.100 s. All simulated quantities are labelled SIMULATION in the result files.
- **Per-championship barriers (H2).** The RT with a fitted 1-in-1,000 probability below it, estimated per championship, pooled, and adjusted for championship offsets.
- **Fiore et al. re-run (H5).** Their published generalised-gamma model is re-evaluated by quadrature from the transcribed parameters, and the venue effects are read from their vector figure.
- **Guard band.** A WADA-inspired uniform guard band (k = 1.645 times the between-championship SD) is compared with per-championship calibration (`analysis/guardband.py`).
- **Literature audit.** A structured search (OpenAlex, PubMed, Semantic Scholar, Google Scholar, one round of citation chasing; {{audit.screen_unique_records}} unique records screened) and coding of every included study's design against a protocol fixed before coding (`lit/audit_protocol.md`, `analysis/lit_audit.py`).
- **Exploratory probe (not pre-specified).** After seeing the data we looked at the recent championships by start line, lane, round and day (`analysis/recent_probe.py`, published as `probe.*` keys whose descriptions all begin "EXPLORATORY"). These results are hypothesis-generating only.

## 4. Key results

![Figure 1](analysis/figures/confound.png)

**Figure 1.** (A) The Ready Time-RT correlation in the same {{fp_models.n_races}} races, pooled over championships and centred within championship, against Haugen et al.'s r = 0.16. (B) Each championship's 1-in-1,000 barrier (men, ex-Gaussian, bootstrap 95% CIs) against the 0.100 s rule and the published proposals. (C) Modelled rate of legitimate starts scored below the limit at each championship under the current rule, a uniform guard band and per-championship calibration (log scale; SIMULATION).

<!-- assert: [descriptive.meet_effect_range_ms@fastest] == 'WCH2022' and [descriptive.meet_effect_range_ms@slowest] == 'WCH2025' -->
<!-- assert: [detector.detector_median_range_ms] == 0 -->
1. **Championships shift RTs.** Athlete-adjusted offsets span {{descriptive.meet_effect_range_ms|.1f}} ms, from the {{descriptive.meet_effect_range_ms@fastest|champ}} (fastest) to the {{descriptive.meet_effect_range_ms@slowest|champ}} (slowest); championships carry {{descriptive.share_compyear_total|pct|.1f}}% (95% CI {{descriptive.share_compyear_total@lo|pct|.1f}} to {{descriptive.share_compyear_total@hi|pct|.1f}}) of RT variance. On the Seiko force traces the detection line sits at the same point of the force rise at every championship with waveforms (median positions differ by {{detector.detector_median_range_ms|.1f}} ms) while force onsets after the gun span {{detector.force_onset_median_range_ms|.0f}} ms, so the offsets are not a changed detection threshold; what causes them is not identified.
<!-- assert: [fp_models.slope_ms_per_100ms@lo] < 0 and [fp_models.slope_ms_per_100ms@hi] > 0 -->
<!-- assert: [fp_models.r_equivalent@hi] < 0.16 -->
2. **No detectable hold effect within championships.** RT changes by {{fp_models.slope_ms_per_100ms|.2f}} ms per 100 ms of Ready Time (95% CI {{fp_models.slope_ms_per_100ms@lo|.2f}} to {{fp_models.slope_ms_per_100ms@hi|.2f}}; the minimum detectable slope at 80% power is {{fp_models.mde80_slope_ms_per_100ms|.2f}} ms per 100 ms), an r-equivalent of {{fp_models.r_equivalent|.3f}} (95% CI {{fp_models.r_equivalent@lo|.3f}} to {{fp_models.r_equivalent@hi|.3f}}) that excludes |r| = 0.16. Dropping the championship effects raises the slope to {{systematic.h1b_slope_ms_per_100ms|.2f}} ms per 100 ms (95% CI {{systematic.h1b_slope_ms_per_100ms@lo|.2f}} to {{systematic.h1b_slope_ms_per_100ms@hi|.2f}}).
<!-- assert: [systematic.h1_verdict] == 'SUPPORTS the mechanism' -->
3. **Pooling manufactures a Haugen-sized correlation (H1).** The naive pooled r is {{systematic.h1c_r_pooled|.2f}} (95% CI {{systematic.h1c_r_pooled@lo|.2f}} to {{systematic.h1c_r_pooled@hi|.2f}}); centred within championship it is {{systematic.h1c_r_centred|.2f}} (95% CI {{systematic.h1c_r_centred@lo|.2f}} to {{systematic.h1c_r_centred@hi|.2f}}). In a reconstruction of Haugen et al.'s design with no hold effect, |r| ≥ 0.16 arose in {{systematic.h1s3_cell5_p_absge016|pct|.0f}}% of simulated datasets (SIMULATION). Pre-specified verdict: {{systematic.h1_verdict}}.
<!-- assert: [fig.barrier_below_rule] > 0 and [fig.barrier_above_rule] > 0 -->
4. **The human limit moves with the championship (H2, H5).** The per-championship 1-in-1,000 barrier (men, ex-Gaussian) runs from {{systematic.h2_champ_barrier_range_ms_exgauss_M@min_ms|.1f}} ms ({{systematic.h2_champ_barrier_range_ms_exgauss_M@min_champ|champ}}) to {{systematic.h2_champ_barrier_range_ms_exgauss_M@max_ms|.1f}} ms ({{systematic.h2_champ_barrier_range_ms_exgauss_M@max_champ|champ}}); {{fig.barrier_below_rule}} of {{fig.barrier_below_rule@n_champs}} championships lie below 0.100 s. Net of bootstrap sampling error, the between-championship SD of the barrier is {{systematic.h2_champ_barrier_tau_ms_M|.1f}} ms (DerSimonian-Laird heterogeneity test: Q = {{systematic.h2_champ_barrier_tau_ms_M@Q|.1f}} across {{systematic.h2_champ_barrier_tau_ms_M@k}} championships, test p in `systematic.json`), so the spread is not sampling noise. Verdict: {{systematic.h2_verdict}}. Inside Fiore et al.'s own model, venue moves the barrier by {{systematic.h5_years_barrier_range_ms|.1f}} ms across the {{systematic.h5_years_barrier_range_ms@n_years}} World Championships venues ({{systematic.h5_verdict_venue}}). Their main values reproduce: the men's barrier with 2022 is {{systematic.h5_men_incl2022_barrier_1e3_ms|.1f}} ms against their {{systematic.h5_men_incl2022_barrier_1e3_ms@published_ms|.0f}} ms, and the women's {{systematic.h5_women_barrier_1e3_ms|.1f}} ms against {{systematic.h5_women_barrier_1e3_ms@published_ms|.0f}} ms. One secondary set (men without 2022) gives {{systematic.h5_men_excl2022_barrier_1e3_ms|.1f}} ms against {{systematic.h5_men_excl2022_barrier_1e3_ms@published_ms|.0f}} ms, consistent with a typo in its printed intercept (the intercept that reproduces their published probability is {{systematic.h5_men_excl2022_implied_beta0|.3f}}; printed {{systematic.h5_men_excl2022_implied_beta0@printed_beta0|.2f}}). Because the pre-registered rule required every set to match, its formal verdict is {{systematic.h5_verdict_reproduced}}.
5. **Other published effects (H3, H4, O2).** Rule-era contrasts: {{systematic.h3_verdict_sign}} (Haugen et al.'s era effect {{systematic.h3_verdict_haugen}}; Han et al.'s {{systematic.h3_verdict_han}}). Sex gap by championship: {{systematic.h4_verdict}}. RT versus 100 m time: {{systematic.o2_verdict}}.
<!-- assert: [guard.a_p1_cut_max@lo] > 1 and [guard.b_p1_n_unflagged] > 0 and [guard.a_p1_fold_max_median] > [guard.a_p0_fold_max_median] -->
6. **Who the rule catches, and a guard band (SIMULATION).** At an average championship {{fairness.per1000_none_exgauss_M|.2f}} (95% CI {{fairness.per1000_none_exgauss_M@lo|.2f}} to {{fairness.per1000_none_exgauss_M@hi|.2f}}) legitimate starts per 1,000 are scored below 0.100 s (men, ex-Gaussian); across the middle half of championships that rate varies {{fairness.meet_iqr_fold_change|.1f}}-fold, and it is highest at the {{guard.a_p0_max_per1000@champ|champ}} ({{guard.a_p0_max_per1000|.1f}} per 1,000). A uniform {{guard.g_ms|.1f}} ms guard band cuts the highest rate {{guard.a_p1_cut_max|.1f}}-fold (95% CI {{guard.a_p1_cut_max@lo|.1f}} to {{guard.a_p1_cut_max@hi|.1f}}) but widens the highest-to-median spread and would clear {{guard.b_p1_n_unflagged}} of the {{guard.b_p1_n_unflagged@n_fs_with_rt}} recorded false starts with a measured RT; per-championship calibration brings the highest-to-median ratio to {{guard.a_p2_fold_max_median@draw_median|.1f}} (bootstrap 95% CI {{guard.a_p2_fold_max_median@lo|.1f}} to {{guard.a_p2_fold_max_median@hi|.1f}}), against {{guard.a_p0_fold_max_median|.0f}} under the current rule. Verdict: {{guard.verdict}}.
<!-- assert: [audit.k_vulnerable_studies] > [audit.n_studies] / 2 -->
7. **The literature is exposed.** {{audit.k_vulnerable_studies}} of {{audit.n_studies}} audited studies ({{audit.pct_vulnerable_studies}}%) drew at least one conclusion from a design that pooled, contrasted or generalised championships without modelling them ({{audit.k_vulnerable_findings}} of {{audit.n_findings}} findings; {{audit.k_strict_studies}} studies when only conclusions resting on a between-championship contrast count). The audit classifies designs, not the truth of findings.
<!-- assert: [trend.h6_verdict] == 'PERSISTING, NOT WORSENING' -->
8. **Not getting worse, but persisting (H6).** The spread of championship offsets in 2020-2025 relative to pre-2010 is {{trend.h6_sd_ratio_recent_pre2010|.2f}} (95% CI {{trend.h6_sd_ratio_recent_pre2010@lo|.2f}} to {{trend.h6_sd_ratio_recent_pre2010@hi|.2f}}); verdict {{trend.h6_verdict}}. Five or six championships per period cannot detect a moderate increase.
<!-- assert: [probe.wch2025_straight_lane_gradient_ms_per_lane@lo] > 0 -->
9. **Exploratory, not pre-specified.** The same {{probe.same_athletes_2022_to_2023_change_ms@n_athletes}} athletes were {{probe.same_athletes_2022_to_2023_change_ms|.1f}} ms (95% CI {{probe.same_athletes_2022_to_2023_change_ms@lo|.1f}} to {{probe.same_athletes_2022_to_2023_change_ms@hi|.1f}}) slower in 2023 than in 2022, the WCH2022 effect Fiore et al. (2025) first reported for the same athletes. At the {{descriptive.meet_effect_range_ms@slowest|champ}}, the same athletes were {{probe.wch2025_straight_minus_200m_same_athlete_ms|.1f}} ms (95% CI {{probe.wch2025_straight_minus_200m_same_athlete_ms@lo|.1f}} to {{probe.wch2025_straight_minus_200m_same_athlete_ms@hi|.1f}}) slower on the home-straight start than on the 200 m start, and on that start RT rose by {{probe.wch2025_straight_lane_gradient_ms_per_lane|.2f}} ms per lane outwards (95% CI {{probe.wch2025_straight_lane_gradient_ms_per_lane@lo|.2f}} to {{probe.wch2025_straight_lane_gradient_ms_per_lane@hi|.2f}}) over {{probe.wch2025_straight_lane_gradient_ms_per_lane@n_days|word}} days.

The full set of results, with every estimate and its interval, is in [analysis/results.md](analysis/results.md) (generated from `analysis/numbers.json`).

## 5. Pre-specification and data corrections

Decision rules for the confirmatory analyses were written and committed before the corresponding quantities were computed: `analysis/prereg_systematic.md` (H1-H5, O2, with dated addenda listing every deviation), `analysis/prereg_addendum_trend.md` (H1-S4, H6), `analysis/prereg_guardband.md` (guard band) and `lit/audit_protocol.md` (literature audit). Post-hoc diagnostics are labelled as such in the result files, and the recent-championship probe is labelled exploratory throughout. Commit times for each plan and its first result are in [`notes/plan_timestamps.md`](notes/plan_timestamps.md).

**Data correction (2026-09-30).** A regular expression in `analysis/common.py` that labels false starts matched inside the note "(not a false start)", so hurdle and lane disqualifications were counted as false starts and their legal RTs left the valid set; RT 0.000 placeholders in Fiore et al.'s file were also read as measured RTs. After the fix (with regression tests in `analysis/tests/test_common_fs.py`) there are {{trend.h6_fs_near_total@n_fs}} recorded false starts ({{trend.h6_fs_near_total@n_fs_with_rt}} with a measured RT) in {{trend.h6_fs_near_total@n_starts|,d}} starts and {{descriptive.n_valid|,d}} valid starts. Every producer was rerun on the corrected data. No pre-specified verdict changed; every number that moved is listed with its old and new value in [notes/bugfix_rerun_diff.md](notes/bugfix_rerun_diff.md).

## 6. Limitations

- **Cause not identified.** The force-trace check rules out a changed detection threshold on the displayed trace, but not signal arrival, loudness or other upstream differences. The offsets are a property of the official results, whatever their source.
- **Ready Time is a proxy.** It is an offset, noisy proxy for the foreperiod; the calibration rests on {{calibration.n_pairs}} races, read by a single blind reader. That reader was an AI model reading rendered audio-envelope plots, not a human, and there is no second annotator (`analysis/measure/README.md`).
- **Tails are extrapolations.** Probabilities below 0.100 s come from left-truncated fits to valid starts; the distribution family changes absolute rates several-fold, so only relative comparisons are emphasised.
- **Simulated is simulated.** Fairness, guard-band and structural-simulation quantities are model outputs under stated assumptions (listed in the result files), not observed disqualification rates.
- **Different sources by era.** 1999-2013 RTs come from Fiore et al.'s compilation, in which a false start is visible only as an RT below 0.100 s; from 2015 the official PDF labels are used. Near-threshold counts compare only within one source.
- **Literature audit.** The search is structured, not exhaustive, and English-dominant; screening and coding were done by a single reviewer (an AI model) following the protocol; closed-access studies were coded from abstracts or secondary sources.
- **Exploratory findings** (the last point of section 4) were chosen after looking at the data and carry no confirmatory weight.

## 7. How to reproduce

Verified on Windows 11 with Python 3.13.11: starting from a fresh clone and a new virtual environment built from `requirements.txt`, `scripts/fetch_third_party.py` followed by `analysis/run_all.py` regenerated every committed output byte-for-byte (result files, figures, `analysis/numbers.json`, `analysis/results.md`), every analysis producer passed verification, the six data tables whose inputs ship were rebuilt byte-for-byte, and the tests passed.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
.venv\Scripts\python scripts\fetch_third_party.py           # Fiore et al. files: download, verify sha256, rebuild rt_fiore.csv
.venv\Scripts\python analysis\run_all.py                    # every analysis, figure, numbers.json and results.md, then verification
.venv\Scripts\python paper\render.py --final                # renders paper/abstract.md from analysis/numbers.json
.venv\Scripts\python -m pytest analysis/tests analysis/measure/tests
```

- `analysis/run_all.py` runs each producer registered in `producers.json` (every command names its inputs, seed and `--out`), merges the results into `analysis/numbers.json`, writes `analysis/results.md`, and finally runs `scripts/verify_producers.py`, which re-runs every analysis producer into a temporary folder and demands byte-identical output. On a laptop CPU the analyses take roughly half an hour to an hour, and the verification pass about as long again (`--skip-verify` skips it).
- To verify the data tables whose inputs ship with the repository (after the fetch step): `python scripts/verify_producers.py producers.json --only data/derived/rt_fiore.csv data/derived/rt_fiore_mapping.csv data/derived/rt_coverage.csv data/derived/rt_qc_flags.csv data/derived/foreperiods.csv data/derived/video_sources.csv`. `rt_athletes.csv`, `races.csv`, `rt_pdf_results.csv`, `rt_waveform.csv` and `rt_waveform_lanes.csv` are built from World Athletics pages, PDFs and start-information images that are not redistributed; `data/scripts/pipeline.py --fetch` re-downloads them (pages may have changed since retrieval) and needs `requirements-full.txt`.
- `requirements.txt` pins the exact versions used. BLAS threads are fixed to one (`analysis/_env.py`) so that results are deterministic. Byte-identical figures need the same matplotlib and fonts; on Linux or macOS, regenerated text files use LF line endings, so byte comparisons with the committed (Windows-built) files can differ while the numbers agree.
- `scripts/scan_secrets.py` scans the repository for tokens, keys, local paths and e-mail addresses.
- A GitHub Actions check (`.github/workflows/ci.yml`) runs on every push: the unit tests, a byte-for-byte re-run of five producers (`fig.json`, `probe.json`, `lit_audit.json`, `numbers.json`, `results.md`) and the mock pipeline. It runs on Windows with the same Python, OpenBLAS kernel and NumPy instruction set as the machine that produced the outputs, which carry Windows line endings, so a Linux re-run differs byte for byte by construction.

## 8. Repository map

| path | contents |
|---|---|
| `analysis/` | analysis code (`run_all.py` drives everything), pre-specified analysis plans (`prereg_*.md`), transcribed design inputs |
| `analysis/outputs/` | result JSONs and CSVs, one per producer |
| `analysis/numbers.json` | every reported number, with source command and data versions |
| `analysis/results.md` | all results in prose and tables (generated) |
| `analysis/figures/` | figures (PNG and PDF); Figure 1 is `confound.png` |
| `analysis/measure/` | broadcast-audio foreperiod pipeline, blind readings, validation results |
| `analysis/probe/` | input tables of the exploratory probe and the scripts that produced them |
| `analysis/tests/` | tests, including guards that fail if a claim in the results stops being true |
| `analysis/external/fiore2025/` | provenance of Fiore et al.'s files (fetched, not redistributed) |
| `data/derived/` | derived data tables used by the analysis |
| `data/raw/` | download manifest (URLs, retrieval times, sha256) and OCR output of the start-information images |
| `data/scripts/` | data collection and table-building code |
| `lit/` | literature audit (protocol, search results as metadata, screening, coding) and literature notes |
| `notes/` | data-correction record and the exploratory probe's write-up |
| `paper/` | abstract template, renderer and rendered abstract |
| `scripts/` | producer verification, third-party fetch, README renderer, secret scan |
| `producers.json` | output path to the exact command that produces it |

The literature notes in `lit/` are dated working notes; numbers in them predate the final analysis, which is authoritative in `analysis/numbers.json`.

## 9. Citation

```
SSAC27 author (anonymised for review). Same Rule, Different Odds: When the Start, Not the Sprinter,
Breaks the Human Limit. MIT Sloan Sports Analytics Conference 2027, Research Paper Competition.
```

A `CITATION.cff` with the same placeholder is included; it will be completed after review.

## 10. License

- **Code** (all scripts and code files): MIT License, see [LICENSE](LICENSE).
- **Our derived data, results and figures**: Creative Commons Attribution 4.0 International (CC BY 4.0), see [LICENSE-DATA.md](LICENSE-DATA.md).
- **Third-party data keep their own terms.** World Athletics results and start-information images are World Athletics' public results; we publish derived values with source URLs. Fiore et al.'s files are not redistributed (no licence); they are fetched from their repository. Literature search results are included as bibliographic metadata only. Details in [DATA.md](DATA.md).
