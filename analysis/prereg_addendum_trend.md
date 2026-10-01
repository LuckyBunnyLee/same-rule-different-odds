# Pre-registration (trend.py): H1-S4 and H6

Status: written and committed on 2026-09-30 (about 11:05 PT) BEFORE any H1-S4 or H6 quantity was computed.
Producer (written after this file is committed): `analysis/trend.py` -> `analysis/outputs/trend.json` (result name
`trend`, so its keys enter `analysis/numbers.json` as `trend.*` through `make_numbers.py`). No existing producer, key,
result or shared file is modified. The producer is registered in `analysis/run_all.py`.

**Relation to `analysis/prereg_systematic.md` addendum 4.** Addendum 4 (committed 10:47 PT, before this file) fixed the
design and decision rules of H1-S4 and H6 and delegated both to this producer. This file adopts addendum 4 as written,
adds the pre-specified decision rule for H1-S4 as the primary S4 verdict, and fixes the details addendum 4 left open.
Every addendum 4 rule is still computed and reported. Each difference is listed in "Changes relative to addendum 4".

**Already visible when this was written.**
- `results.md` sections 1-5, including the per-championship offsets and their CIs (`descriptive.json` table
  `meet_effects`). The H6(a) period SDs and their ratio can therefore be worked out by hand from a visible table; the analyst
  noticed this while reading it and made a rough mental calculation. The H6(a) periods, statistic and rule were
  fixed in addendum 4 before this analysis started and are adopted unchanged.
- `fairness.json` table `meets` (the modelled per-championship rates of H6(b)) and `descriptive.json` table
  `false_starts` plus `fs_near_threshold_090_100` (the H6(c) counts), printed while checking inputs.
- `calibration.r_corrected` (with CI) and `calibration.r_ci_high_at_b_low`; the S3 inputs and results in
  `systematic.json` (`h1s3_*`, `extra.simulation_parameters.S3`).
- While designing H1-S4, back-of-envelope normal approximations (not simulations) suggested that P(pattern | POOLED) is
  below 0.05 at a true within effect of 0 and above it at our upper bound, and that P(pattern | WITHIN) at the upper
  bound is of order 0.01. Because the pre-specified rule does not say at which true effect the POOLED side is evaluated,
  the primary reading is fixed below with its reason, and the rule's outcome under the other two readings is reported
  too, so nothing depends on the choice silently.

**Design constants (not measurements).** Haugen et al. 2013 cells: men 1997-2003 r = 0.16, women 1997-2003 r = 0.17,
men 2003-2009 r = 0.16, all P < 0.001; women 2003-2009 not significant; no 2010-2011 correlation reported. Pattern bars
0.01 and 0.05 (pre-specified); likelihood-ratio bars 10 and 0.1 (addendum 4). Seed 20260928; sub-streams offset by fixed
constants in the code.

---

## H1-S4: did Haugen et al. analyse within championships? (SIMULATION)

The question is answered statistically: how probable is Haugen's reported pattern if their correlations had been
computed within championships, and how probable if computed on pooled starts (the S3 design)?

### Data-generating model (one simulated Haugen study)

- Two rule eras ("1997-2003" and "2003-2009") x two sexes. Each era has K championships, shared by the sexes and
  independent between eras.
- Per championship: mean hold m_c ~ N(1.75 s, sd_b^2), truncated to 1.3-2.2 s (redrawn until inside, as S3's
  `_truncnorm_rows`); RT offset g_c ~ N(0, sd_champ^2), independent of m_c. Men and women of a championship share m_c
  and g_c.
- Per sex: H heats per championship (S3's `haugen_layout`: fractional starts per heat, athletes nested in championship,
  about 3 starts each, never twice in one heat). Heat hold h = m_c + N(0, sd_w^2); heat RT effect u ~ N(0, sd_race^2);
  athlete a ~ N(0, sd_ath^2); residual e ~ N(0, sd_res^2). Heats, athletes and residuals are separate by sex.
- RT = g_c + beta (h - 1.75) + u + a + e. The true hold effect beta acts on every start, within and between
  championships. It is scaled so that the population within-championship correlation of hold and RT equals r_w:
  beta = r_w sqrt(sd_race^2 + sd_ath^2 + sd_res^2) / (sd_w sqrt(1 - r_w^2)).
- Parameters are S3's, recomputed identically (not read from `systematic.json`, which was being regenerated separately):
  sd_b and sd_w are the REML between- and within-championship SDs of the audio foreperiods (`foreperiods.csv`, valid
  attempts with a foreperiod, last valid attempt per race, championship random effect); sd_champ, sd_race, sd_ath and
  sd_res are `descriptive.sd_championship_ms`, `sd_race_ms`, `sd_athlete_ms` and `sd_residual_ms`.
  `analysis/tests/test_trend.py` checks equality with the S3 inputs stored in `systematic.json`.

### Two analyses of every simulated study, per sex x era cell

- (i) WITHIN: hold and RT centred within championship, then Pearson r over the cell's starts.
- (ii) POOLED: uncentred Pearson r over the cell's starts (Haugen-style; S3's statistic).
- The naive p of each r comes from the t-test with n - 2 df, n = starts in the cell.
- Common random numbers: each simulated cell is stored as its sufficient statistics (centred sums of squares and cross
  products of hold with the non-hold part of RT). Every r_w is then evaluated on the same simulated studies, so each
  probability is monotone in r_w.

### Pattern

- **Primary pattern P3** (Haugen's significant cells): men 1997-2003 r >= 0.16, women 1997-2003 r >= 0.17 and men
  2003-2009 r >= 0.16, each also with naive p < 0.001, as reported.
- **Secondary, full pattern P4:** P3 plus women 2003-2009 with naive p >= 0.05 (two-sided).
- **Sensitivity:** P3 with rounding-lenient thresholds 0.155 / 0.165 / 0.155 (the lowest values that round to the
  reported ones).

### Probabilities

- P(P3 | WITHIN, r_w) = the product of the three per-cell probabilities. The cells share no heats, athletes or
  residuals, and centring removes the shared championship components, so the within-analysis cells are independent.
  Per-cell probability: the simulated share when at least 200 of the 20,000 studies meet the cell's condition;
  otherwise the normal approximation with the simulated mean and SD of r, at threshold max(reported r, r needed for
  naive p < 0.001).
- P(P3 | POOLED, r_w) = the joint simulated share over 20,000 studies. Cells of one era share championships, so they are
  not multiplied.
- P4 likewise: WITHIN multiplies in the women 2003-2009 cell; POOLED uses the joint share.
- Settings: r_w = 0; our estimate r_est = `calibration.r_corrected`; our conservative upper bound
  r_up = `calibration.r_ci_high_at_b_low`; and r_w = 0.16 (Haugen-sized, context only, not in any rule).
- Likelihood ratio LR(r_w) = P(P3 | POOLED, r_w) / P(P3 | WITHIN, r_w), at the same r_w.
- Monte Carlo SEs are reported: binomial for joint shares; delta method for products.

### Design uncertainty (propagated)

Haugen's sample sizes are reconstructed, not reported (`lit/systematic_forensics.md` section 1.2, [INF] tags).
- Grid centred on S3's `cell5`: K in {4, 5, 6} championships per era x H in {9, 11, 13} heats per championship per sex,
  with 7.5 starts per heat and 3 starts per athlete. That is 9 designs with 272 to 588 starts per cell; `cell5`
  (K = 5, H = 11, 415 starts per cell) is the centre.
- **Primary: design-averaged probabilities**, uniform weights over the 9 designs. This is the marginal probability of the
  pattern over the design uncertainty; LR = ratio of design-averaged probabilities. Designs too small for r = 0.16 to
  reach p < 0.001 are not excluded: the p < 0.001 condition in P3 lowers their probability under both analyses.
- Reported alongside: `cell5` alone; the minimum and maximum over designs; the primary rule evaluated in each design,
  with the share of designs meeting it; and a hold-SD sensitivity (the `cell5` layout with S3's `cell5_litsd` SDs,
  0.25 s between and 0.16 s within).

### Inversion

- r_star = the smallest r_w on the grid 0, 0.005, ..., 0.300 with design-averaged P(P3 | WITHIN, r_w) >= 0.05,
  linearly interpolated between grid points. All grid points use the same 20,000 studies (common random numbers).
  Also computed for `cell5` alone.
- r_star is compared with the `calibration.r_corrected` CI and with r_up.

### Decision rules

- **Primary (pre-specified rule).** "WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE" if
  P(P3 | WITHIN, r_up) < 0.01 and P(P3 | POOLED, r_up) >= 0.05 (design-averaged). "WITHIN-CHAMPIONSHIP ANALYSIS NOT
  EXCLUDED" if P(P3 | WITHIN, r_up) >= 0.01. Otherwise "INCONCLUSIVE (pattern improbable under both analyses)".
  - Why both sides use r_up: both probabilities increase with r_w (common random numbers make this exact; the code
    checks it). So r_up gives each analysis its most favourable value within our interval, a profile over the interval.
    Evaluating the POOLED side at a smaller r_w would compare the two analyses at different true effects.
  - Reported alongside: the rule's outcome with the POOLED side at r_est and at r_w = 0.
- **Addendum 4 rules**, computed and reported unchanged:
  - Likelihood: "FAVOURS POOLED" if LR(r_est) >= 10; "FAVOURS WITHIN" if LR(r_est) <= 0.1; otherwise "INCONCLUSIVE".
    LR(r_up) is reported alongside.
  - Inversion: "WITHIN READING NEEDS r_w ABOVE OUR CI" if r_star > r_up; otherwise "WITHIN READING COMPATIBLE WITH OUR CI".
- **Wording stays probabilistic.** Write, for example, "a within-championship analysis would produce Haugen's reported
  pattern with probability below 0.01 even at the largest within-championship effect our data allow". Never write
  "Haugen did not analyse within championships".

### Key sensitivity (stated with every S4 result)

- Before 2010 a false start did not disqualify outright. Before 2003 an athlete was disqualified for their own second
  false start; from 2003 to 2009 the first false start in a race was charged to the field. Anticipation may have paid
  then. The within-championship effect in 1997-2009 could therefore genuinely differ from ours, which is measured in
  2022-2025 under zero tolerance. r_star says how large it would have had to be; P3 at r_w = 0.16 is reported for
  context.
- Other stated caveats:
  - Haugen's design is a reconstruction (full text closed).
  - Championship mean holds and offsets are independent here. An alignment like the one in our 2022-2025 data would
    favour POOLED further.
  - Both sexes get the same design.
  - The within-analysis probabilities in the far tail rest on the normal approximation.

---

## H6: is championship-level variation getting worse, and does it put the 0.100 s rule at risk from the system?

**Offsets:** the athlete-adjusted championship offsets exactly as produced by `descriptive.py` (`descriptive.json`
table `meet_effects`: `deviation_ms`, `se`), read from `analysis/outputs`; not refitted.
**Periods (outdoor):**
- pre-2010 = WCH1999, 2001, 2003, 2005, 2007, 2009 (6);
- 2010-2019 = WCH2011, 2013, 2015, 2017, 2019 (5);
- 2020-2025 = OG2020, WCH2022, WCH2023, WCH2025, OG2024 (5).

**Year** = year held (OG2020 was held in 2021).

### (a) Dispersion and trend

- SD (ddof 1) of the offsets within each period.
  - **Primary ratio:** SD(2020-2025) / SD(pre-2010).
  - **Secondary ratio:** SD(2020-2025) / SD(2010-2019).
- **Bootstrap:** B = 5,000; percentile 95% CIs for each SD and each ratio. In each replicate, championships are resampled
  with replacement within each period, and each drawn offset is redrawn as estimate + se x N(0, 1).
  `descriptive.json` stores per-championship SEs but not their joint covariance, so redraws are independent; for
  sum-coded deviations the omitted covariances are small and negative.
- Sensitivity: the F-distribution 95% CI of the variance ratio, square-rooted to the SD scale.
- Descriptive: noise-corrected SD per period, sqrt(max(0, variance - mean se^2)).
- **Trend over the 16 outdoor championships, 1999-2025.**
  - Primary: slope (ms per decade) of |offset - linear time trend| on year. The residuals come from an OLS fit of offset
    on year, then |residual| is regressed on year. Pairs bootstrap CI (championships resampled, both steps refitted,
    B = 5,000), plus a two-sided permutation p (years permuted over championships, 10,000 permutations).
  - Sensitivity: the plain |offset| slope, with the same CI and p.
- Fastest-scoring (most negative) and slowest-scoring offsets with their championship and year: overall (16 outdoor
  championships; also all 18) and per period.
- Sensitivities (reported, not in the rule):
  - WIC2024/2025 added to 2020-2025 (addendum 4);
  - Seiko only: WCH championships only, so OG2020 and OG2024 (Omega) are dropped and the timing vendor is constant.

### (b) Modelled rate of legitimate sub-0.100 s starts

- The fairness model, reused read-only: P(RT < 0.100) for a gun-triggered start = the men's reference ex-Gaussian of
  `descriptive.json` (average championship, first round, flat sprint) shifted by the championship's offset
  (`fairness_sim.p_fs`), per 1,000 starts. The code asserts that it reproduces `fairness.json` table `meets`
  (relative difference < 1e-4).
- Descriptive CIs: each of the 200 bootstrap reference fits in `descriptive.json` paired with one offset redraw
  (estimate + se x N(0, 1)); percentile 95%.
- Per period: median, minimum, maximum and max/min ratio, with each championship listed. Descriptive only.

### (c) Near-threshold recorded false starts (factual)

- Recorded false starts with RT in [0.090, 0.100) s, by championship and period. They are recounted from the data with
  `descriptive.py`'s definitions (started = RT recorded or false start; the code asserts that the totals, the
  per-championship starts and the false-start counts equal `descriptive.json`).
- Reported with denominators: starts, all false starts and false starts with an RT per championship. Per period: count
  per 1,000 starts with a Wilson CI.
- Stated caveat: false-start recording differs by source. From 2015 it comes from official PDF labels plus RT; the
  1999-2013 rows come from Fiore et al.'s file, where a false start is visible only as an RT below 0.100 s. Counts
  therefore compare across championships of one source only.

### Decision rule (H6)

- "WORSENING" if the bootstrap 95% CI of SD(2020-2025) / SD(pre-2010) lies entirely above 1; "IMPROVING" if it lies
  entirely below 1; otherwise "PERSISTING, NOT WORSENING" (addendum 4; the pre-specified rule is the same).
  "Not worsening" means no credible increase. It is not evidence of stability, and the CI width is reported with it.
- The same classification is reported, outside the rule, for the secondary ratio and for each sensitivity. (b) and (c)
  are descriptive.

---

## Changes relative to addendum 4

1. S4 pattern: adds naive p < 0.001 in the three significant cells, as reported. At `cell5` this moves the men's
   threshold from 0.16 to the value p < 0.001 requires at 415 starts, just above 0.16.
2. S4: sample-size uncertainty is propagated over a 9-design grid; the design-averaged probabilities are primary, and
   `cell5` alone is reported.
3. S4: common random numbers. The inversion reuses the same 20,000 studies at every grid point, where addendum 4 drew
   5,000 new studies per point.
4. S4: the pre-specified rule is the primary verdict; addendum 4's likelihood and inversion rules are reported.
5. S4 additions, none in a rule: r_w = 0.16 context setting; rounding-lenient thresholds; lit-SD sensitivity; Monte
   Carlo SEs.
6. H6(a): offsets are redrawn independently per championship with their `descriptive.json` SEs (joint covariance not
   stored).
7. H6(a) additions: year = year held; permutation p for the trend; Seiko-only sensitivity; noise-corrected SDs
   (descriptive).
8. H6(b): descriptive CIs from `descriptive.json`'s bootstrap reference fits with offset redraws.
9. H6(c): denominators, false starts with an RT, per-period Wilson CIs, and the source caveat.

## Integrity

- New numbers enter `numbers.json` only through `make_numbers.py`, as `trend.*`, once the
  producer is registered in `analysis/run_all.py`.
- Every verdict flag is computed from the stored, rounded values, so the claim guards reproduce it exactly.
- `analysis/tests/test_trend.py` covers:
  - unit tests of the new statistics;
  - agreement of the S4 simulator with S3's machinery;
  - verdicts recomputed from the stored numbers, each guard shown to fire on a corrupted copy.
- The producer is rerun and compared byte for byte before commit.
- Deviations discovered while implementing are appended below, with reasons, before any result is reported.

## Deviations found while implementing

Appended 2026-09-30 after the registered run and before any result was reported. No estimand, threshold, sample,
setting or decision rule changed.

1. Timestamp: the status line above says "about 11:05 PT"; the commit (55a54d5) was made at 10:59 PT.
2. Monte Carlo SE of the WITHIN products is reported only when every factor is a simulated share. For normal-approximated
   factors the error is approximation error, which a binomial SE would misstate; they are flagged
   (`n_cells_normal_approx`, `cell5_all_cells_simulated_share`) and their SE field is None.
3. Added a reimplementation check key, `s4_cell5_pooled_cell_m9703_p`: pooled r at r_w = 0 in one cell (men 1997-2003)
   of `cell5`, at threshold max(0.16, r for p < 0.001). It is compared with S3's registered `h1s3_cell5_p_ge016_sig`
   in `test_trend.py`. It is a check, not a result.
4. H6(b): the overall highest and lowest modelled rates over all 18 championships (`h6_rate_per1000_max` / `_min`) are
   reported in addition to the per-period summaries. Descriptive.
5. H6(c): `h6_fs_near_top_champ_count` pins the count at the championship with the most near-threshold false starts,
   so an "all at one championship" statement is generated, not typed. Factual.


### Note (2026-09-30, added after the false-start classification fix, commit 5a12182)

A data-cleaning bug in `common.normalize_rt` was fixed (non-start DQs noted "(not a false start)" were counted as false
starts; the Fiore et al. file's RT 0.000 placeholders were treated as measured RTs). trend.py was rerun on the
corrected data. **No verdict changed** (S4: WITHIN-CHAMPIONSHIP ANALYSIS STATISTICALLY IMPLAUSIBLE, FAVOURS POOLED,
WITHIN READING NEEDS r_w ABOVE OUR CI; H6: PERSISTING, NOT WORSENING). The near-threshold denominators changed (false
starts with an RT); every changed number is listed in `notes/bugfix_rerun_diff.md`.
