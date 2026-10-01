# Pre-registration: systematic (athlete-independent) variation in official RT

Status: written and committed on 2026-09-30, BEFORE any of the estimands below were computed.
Producer (to be written after this file is committed): `analysis/systematic.py` -> `analysis/outputs/systematic.json`,
merged into `analysis/numbers.json` under the prefix `systematic.*`. Existing keys and results are not modified.

**What was already known when this was written.** The existing results in `analysis/numbers.json` were visible,
among them the per-championship Ready Time medians (`fp_models.fp_median_<champ>`), the athlete-adjusted
championship offsets (`descriptive.json` table `meet_effects`), the calibration offsets
(`calibration.offset_mean_<champ>_s`) and the within-championship slope (`fp_models.slope_ms_per_100ms`).
The sign of H1(d) (championships with longer mean Ready Time have slower RT offsets) was therefore foreseeable,
and a positive naive pooled correlation was anticipated. Nothing below had been computed: not the (b) model,
the naive correlations, the simulations or any H2 quantity.

Design constants used below (not measurements): Haugen et al. 2013 r = 0.16 (positive: longer hold, slower RT);
"non-trivial probability" = 0.05; H2 materiality bar = 10 ms; published threshold proposals 0.094 s
(Fiore et al. 2025, men, 1e-3 tail) and 0.119 s (Brosnan et al. 2017), a 25 ms gap; barrier tail = 1e-3.
Seed 20260928 (sub-streams offset by fixed constants in the code).

---

## H1: a false-positive mechanism for the hold effect

**Claim tested.** Championship-level RT offsets that co-vary with championship-level hold (Ready Time)
distributions make a naive pooled correlation between hold and RT Haugen-sized, even though the
within-championship association is not.

**Sample (identical to `fp_models.py`).** Valid RTs (0.100-0.300 s, not a false start, not DNS) from
`rt_athletes.csv` in races with a validated Seiko Ready Time (`rt_waveform.csv`, `wf_ok`), WIC2025 excluded:
the 232-race, 1,765-RT sample with 4 championships (WCH2022, WCH2023, WCH2025, WIC2024). The script asserts
that it rebuilds exactly `fp_models.n_races` races and `fp_models.n_rts` RTs.
`fp_c100` = (Ready Time - 1.78 s) x 10, as in `fp_models.py`.

### Estimands

- **(a) Within-championship model** (existing): `fp_models.FX` + `fp_c100` (championship, sex, round, event-type
  fixed effects) with crossed race and athlete random intercepts, ML. Slope (ms per 100 ms) with Wald 95% CI,
  and the r-equivalent exactly as in `fp_models.py` (slope x pooled within-championship SD of Ready Time /
  within-championship SD of RT from the REML null model). The script asserts that the slope reproduces
  `fp_models.slope_ms_per_100ms` (|difference| < 0.001); if it does not, stop.
  Haugen-sized slope on this scale = `fp_models.haugen_slope_same_scale` (recomputed).
- **(b) Same model WITHOUT championship effects**: sex + round + event type + `fp_c100`, crossed race and
  athlete random intercepts kept, ML. Slope with Wald 95% CI; r-equivalent = slope x overall SD of race-level
  Ready Time / SD of RT from the REML null model of the same specification (race + athlete + residual).
- **(c) Naive athlete-level Pearson r** across all starts, pooled over championships (Haugen-style):
  - (c1) uncentred: corr(Ready Time of the race, RT) over the 1,765 starts. **Primary naive estimand.**
  - (c2) per-championship centred: Ready Time and RT each centred on their championship mean (start-weighted),
    then pooled. Mechanism control: expected NOT to be Haugen-sized if the mechanism is between-championship.
  - (c-fp) secondary: as (c1) but on the audio-calibrated foreperiod scale, Ready Time + the championship's
    calibration offset (`calibration.offset_mean_<champ>_s`; WIC2024 has no audio pairs and gets the pooled
    `calibration.offset_mean_s`). Mimics TV-measured holds. Not in the decision rule (imputed WIC2024 offset,
    3-15 pairs per championship).
  - Secondary descriptives, not in the decision rule: (c1) by sex, and (c1) restricted to 100 m.
  - Intervals: the race-cluster bootstrap 95% percentile CI (races resampled within championship,
    B = 2,000) is the decision interval. The naive Fisher-z CI and naive p (starts treated as independent, which
    is what a naive analysis reports) are also recorded.
- **(d) Descriptive only**: championship mean Ready Time (race-level) vs championship RT offset (athlete-adjusted
  deviation from `descriptive.json` `meet_effects`; the within-sample offsets from model (a) are also tabulated).
  Pearson and Spearman correlations across championships, no inference (n = 4-5 points):
  - primary: the 4 championships of the H1 sample;
  - as requested, 5 championships adding WIC2025 (its Ready Times are anomalous and excluded elsewhere; flagged);
  - foreperiod scale: the 3 championships with audio pairs (mean Ready Time + calibration offset).

### Structural simulations (SIMULATION; every output labelled as such)

Each simulated dataset is analysed with the naive pooled athlete-level correlation. Reported for every
simulation: mean, SD, 2.5/50/97.5 percentiles of r, P(r >= 0.16) and P(|r| >= 0.16). 10,000 datasets per setting.
Residuals, race and athlete effects are normal with the fitted variances; simulated RTs are not re-truncated.

- **S1, observed structure (primary simulation).** The observed design is kept (races, athletes, their Ready
  Times, championship, sex, round, event type). RT = fixed effects + true slope x `fp_c100` + race + athlete +
  residual. True within-championship slope = 0 (parameters from the ML null model, championship offsets included)
  and, separately, = the (a) estimate (parameters from the ML (a) model). Outputs:
  - S1-ready: naive r on the official Ready Time scale. **In the decision rule.**
  - S1-fp: naive r on the foreperiod scale, hold = Ready Time + championship calibration offset (WIC2024 pooled)
    + N(0, `calibration.offset_sd_within_comp_s`) per race, i.e. the championship-specific Ready Time definition
    shift that a TV-based hold measurement would carry. Secondary (same reason as (c-fp)).
  - S1-centred: the (c2) statistic (control).
  - S1-control: slope 0 and all championship offsets set to 0 (shows what remains without championship
    structure). Control only.
- **S2, exchangeable championships.** As S1 (same design, same slope settings), but in each dataset the
  championship-level quantities are redrawn independently of each other: RT offsets ~ N(0, SD) with
  SD = `descriptive.sd_championship_ms` (18 championships), and championship mean Ready Times ~ N(grand mean,
  SD_between), SD_between = REML between-championship SD of race-level Ready Times in the H1 sample; within-
  championship Ready Time deviations are kept. Removes the dependence on the observed alignment of the four
  championships: answers how often pooling this many championships gives a Haugen-sized r by chance.
- **S3, Haugen 2013 design.** Added when `lit/systematic_forensics.md` contains its Haugen section. The design
  (number of championships, heats, athletes, unit of analysis, subgroups, hold range) is taken from that file and
  written into a dated addendum below, committed BEFORE S3 is run. Parameters are ours, fixed now:
  championship, race, athlete and residual SDs from the 18-championship model (`descriptive.sd_*`);
  hold on the TV (audio) scale with between- and within-championship SDs estimated by REML from
  `data/derived/foreperiods.csv` (valid attempts with a foreperiod value, race level, championship random effect);
  holds truncated to Haugen's reported range if the file gives one; true within-championship effect = 0.
  Primary statistic: P(|r| >= 0.16) (also P(r >= 0.16)) for the naive pooled correlation in Haugen's unit of
  analysis (per subgroup if Haugen reported r per sex and era). If the file does not appear, S3 is reported as
  not run.

### Decision rule (H1)

- **W (within still excludes)**: the (a) slope 95% CI excludes the Haugen-sized slope in both directions.
- Criteria that a naive or pooled analysis produces Haugen-sized associations:
  - R1: (b) r-equivalent 95% CI upper bound >= 0.16;
  - R2: (c1) naive pooled r, race-cluster 95% CI upper bound >= 0.16 (includes 0.16 or lies above it);
  - Q1: S1-ready, true slope 0: P(r >= 0.16) >= 0.05;
  - Q2: S2, true slope 0: P(r >= 0.16) >= 0.05;
  - Q3: S3 (if run), true effect 0: P(|r| >= 0.16) >= 0.05.
- **Verdict**: "SUPPORTS the mechanism" if W and at least one of R1, R2, Q1, Q2, Q3; otherwise "NOT REPRODUCED".
  The rule is disjunctive over five pre-specified criteria and therefore lenient, so every criterion's outcome is
  reported, with a grade: "observed structure" when R1, R2 or Q1 holds (our own championships produce it);
  "simulation only" when only Q2 or Q3 holds (possible under exchangeable championships, not shown in our data).
- Reported alongside, without changing the verdict: whether (c2) stays below 0.16 (consistent with a
  between-championship mechanism) and the S1 slope = estimate results.

---

## H2: sensitivity of "human limit" estimates to championship structure

**Sample (identical to `descriptive.py`).** All valid RTs (`rt_athletes.csv` + `rt_fiore.csv`, de-duplicated),
by sex; the script asserts `descriptive.n_valid` rows. Families: ex-Gaussian (primary; lowest AIC for both sexes in
`descriptive.json`), shifted lognormal, shifted Wald, fitted with `rtdist.fit_family` (left truncation 0.100 s,
right 0.300 s), as in the existing code.

### Estimands (each sex x family)

- P(RT < 0.100) = the fitted untruncated CDF at 0.100 s (a gun-triggered start; an extrapolation).
- Barrier = the 0.001 quantile of the fitted untruncated distribution, in ms (as Fiore et al. 2025).
- **(a) Pooled**: fitted to raw RTs pooled over championships. The script asserts that P(RT < 0.100) equals
  `descriptive.tail_mass_pooled_<family>_<sex>` (4 significant digits).
- **(b) Championship-adjusted**: athlete-adjusted championship offsets from the ML model of `descriptive.py`
  (sex, round, event type + championship sum-contrast fixed effects; race and athlete random intercepts),
  centred on their start-weighted mean for that sex so pooled and adjusted samples share the same mean; each RT
  minus its championship offset, with per-observation truncation bounds [0.100 - offset, 0.300 - offset].
- **(c) Per championship**: raw RTs of one championship, where that sex has >= 100 valid RTs in >= 10 races.
- Uncertainty: race-cluster bootstrap, races resampled within championship. (a) and (b) use the same resample in
  each replicate (paired, B = 200); (b) also redraws the offsets from their estimated joint sampling distribution
  (normal, ML covariance) in each replicate. (c): B = 100 per championship, ex-Gaussian only (point estimates for
  all families).

### Reported quantities

- (a), (b) and (c) P(RT < 0.100) and barrier, with CIs (for (c), ex-Gaussian CIs only).
- **Pooled-vs-adjusted shift** = barrier(a) - barrier(b), ms, paired bootstrap CI.
- **Per-championship spread** = max - min of the (c) barriers across eligible championships (ex-Gaussian primary;
  all families reported), with the championships at the extremes. Noise guard: between-championship SD tau of
  the barrier from a DerSimonian-Laird random-effects model on the (c) estimates with bootstrap SEs, the implied
  95% prediction-interval width 2 x 1.96 x tau, and Cochran's Q p-value.
- **Family-to-family spread** = max - min of the barrier across the three families, for (a), (b) and the median
  over championships in (c).

### Decision rule (H2)

Primary cell: men, ex-Gaussian (Fiore et al.'s 0.094 s barrier is for men).
- C1: per-championship spread >= 10 ms AND noise guard 2 x 1.96 x tau >= 10 ms.
- C2: |pooled-vs-adjusted shift| >= 10 ms (point estimate; whether its CI lower bound also clears 10 ms is reported).
- **Verdict**: "CONSEQUENTIAL" if C1 or C2 in the primary cell; otherwise "NOT CONSEQUENTIAL". 10 ms is 40% of the
  25 ms gap between the published proposals; each spread is also reported as a fraction of that gap. Women and the
  other families are reported as agreeing or not, without changing the verdict. If the family-to-family spread
  of (a) or (b) is >= 10 ms, the report states that the 1e-3 barrier is not identified by these data independently
  of the family choice.

---

## Integrity

- The new numbers enter `numbers.json` only through `make_numbers.py` under `systematic.*`; no existing producer
  or key changes. After the rerun, every existing producer is re-verified byte-for-byte; if any existing number
  moves, work stops and the change is reported.
- Tests: `analysis/tests/test_systematic.py` (unit tests of the new statistics, verdict consistency with the
  stored numbers, each guard shown to fire).
- Deviations from this plan, if any, are listed in the addendum below with reasons, before results are reported.

## Addenda

### Addendum 1 (2026-09-30, after development runs of H1 and H2, before any result was reported)

- **Post-hoc sensitivity added (not in any decision rule).** Raw per-championship fits (H2(c)) mix the
  championship offset with each championship's round and event composition (for example, WIC contributes only
  60 m / 60 m hurdles, and 1999-2013 come from a different source table). A composition-adjusted variant is
  therefore reported: each RT minus its round + event-type fixed effect from the same ML model (reference: first
  round, flat sprint), per-observation truncation, ex-Gaussian point estimate per eligible championship, and the
  resulting max - min spread (`systematic.h2_champ_barrier_range_ms_exgauss_<sex>_compadj`). It was added after
  seeing the development H2 output and is labelled POST-HOC wherever it appears.
- **Implementation details not spelled out above.** Every verdict flag is computed from the stored (rounded)
  values so the claim guard in `analysis/tests/test_systematic.py` reproduces it exactly. H1(c) secondary subsets
  are men, women and 100 m. In S1 and S2 the fixed-effect design (sex, round, event type) enters the simulated RTs
  exactly as fitted. S2 uses the variance components of the model that matches its slope setting (null model for
  slope 0, model (a) for slope = estimate).
- **Unchanged:** all estimands, thresholds, samples and decision rules above.

### Addendum 2 (2026-09-30): S3 design, fixed before S3 was run

`lit/systematic_forensics.md` (v1, section 1 complete) reconstructs Haugen et al. 2013: 100 m, 1997-2011, World and
European Championships (up to 12), 267 TV-timed heats (about 11 per championship per sex), about 7.5 valid starts
per heat, 571 athletes, r reported per sex x rule-period cell (about 5 championships per cell), athlete-level
starts, Pearson r, no championship term; "1.3-2.2 s" most likely the range of championship mean holds. Nothing in
it is verified from Haugen's full text (closed). The design is transcribed into `analysis/haugen_design.csv`
(design constants with the file's confidence tags) and passed to `systematic.py --haugen-design`.

- **Primary S3 cell** (`cell5`): 5 championships x 11 heats x 7.5 starts (heats of 7 and 8; 83 starts per
  championship), about 3 starts per athlete, athletes nested within championship. Holds on the audio scale with
  the pre-registered REML between- and within-championship SDs from `foreperiods.csv`; mean 1.75 s (midpoint of the
  reported range; the mean does not affect r). RT: championship, race, athlete and residual SDs of the
  18-championship model. Championship mean holds and championship RT offsets independent; true effect 0.
- **Truncation.** The prereg said holds are truncated to Haugen's reported range "if the file gives one". The file
  gives it but reads it as the range of championship means, so the primary cell keeps championship means inside
  1.3-2.2 s; heat-level truncation (the literal reading) is reported as sensitivity `cell5_heattrunc`.
- **No extra TV measurement error** is added: the REML within-championship SD of our audio foreperiods already
  contains an audio measurement error of the size the file assumes for Haugen's video timing.
- **Sensitivities (reported, not in the rule):** `cell5_litsd` (hold SDs 0.25 / 0.16 s, the file's defaults),
  `cell5_heattrunc`, `all12` (all 12 championships pooled).
- **Statistics:** Q3 uses P(|r| >= 0.16) of the primary cell, as pre-registered. Secondary: P(r >= 0.16) and, as in
  the file, P(r >= 0.16 and naive p < 0.001) with the rate of naive p < 0.001 (Haugen reported P < 0.001).
- One S3 run covers Haugen's three significant cells (men 1997-2003, men 2003-2009, women 1997-2003): they share
  the design, and men and women at one championship share its holds and offsets, so they are not independent.

### Addendum 3 (2026-09-30, ~11:00 PT): confounder audit H3-H5 (+ optional O2), fixed before computing

Approved by the author. Committed before any H3-H5/O2 quantity was computed.
**Already visible when this was written:** the athlete-adjusted championship offsets (`descriptive.json` table
`meet_effects`, printed during H2), so the direction of subset contrasts built from them was partly foreseeable;
`descriptive.era_*` and `descriptive.sex_diff_W_minus_M_ms`; the literature review's example contrasts (WCH2011 or
WCH2022 minus WCH1999/2001) and its Fiore planning output (barrier 94 / 97 / 85 ms); Fiore et al.'s published tables
(read to transcribe parameters). Not computed: every H3 subset or null distribution, the H4 interaction model, every
H5 venue-quantile barrier, O2.

Samples: H3 and H4 use the H2 sample (all valid RTs, 18 championships) and the H2 offsets model (sex, round, event
type + sum-coded championship; race and athlete random intercepts; ML). New keys: `systematic.h3_*`, `h4_*`, `h5_*`,
`o2_*`. H1/H2 code paths and random streams are untouched, and the existing `systematic.*` keys must reproduce exactly.

**H3: rule-era contrasts depend on which championships represent each era.**
- Eras as in Haugen et al. and `common.rule_era`: pre-2003 = WCH1999, WCH2001; 2003-2009 = WCH2003, 2005, 2007,
  2009; 2010+ (zero tolerance) = the 10 outdoor championships WCH2011, 2013, 2015, 2017, 2019, 2022, 2023, 2025,
  OG2020, OG2024. World Indoors are excluded (60 m only; neither published design used indoor meets); sensitivity:
  WIC2024/2025 added to 2010+. Era mean = unweighted mean of its championships' offsets.
- Contrasts: C1 = 2003-2009 minus pre-2003; **C2 = 2010+ minus 2003-2009 (zero tolerance; primary)**; C3 = 2010+
  minus pre-2003 (Haugen's 15-year span, published +30 ms); C4 = 2010+ minus all pre-2010 (Han's contrast, published
  -4 ms). Full-data estimate Delta_all with an SE from the offsets' covariance (conditional on the championships).
- (A) Haugen-matched subsets: k = 5, 5, 2 per era, capped at availability (2, 4, 2); every combination
  (45 designs). Per contrast: min, median, max, share of designs with the sign opposite to Delta_all, share positive.
- (B) Random-championship model: tau = between-championship SD of offsets within era, pooled over eras (pooled
  within-era variance minus the mean squared offset SE, floored at 0). A contrast from k1 and k2 championships
  ~ N(Delta_all, tau^2 (1/k1 + 1/k2) + its measurement variance); P(opposite sign) = Phi(-|Delta_all| / SD).
  Designs: Haugen (C1: 5 vs 5; C2 and C3: 2 vs 5) and Han (C4: 11 vs 8 senior championships).
- (C) Same-rule null: within the 10 outdoor 2010+ championships, every split into disjoint groups of 2 and 5
  (2,520 designs): the "era contrast" produced with no rule change. Report its 2.5/97.5 percentiles, max |.|, and
  the shares with |.| >= 30 ms and >= 4 ms. For Han's sizes (11 vs 8): the parametric half-width 1.96 tau sqrt(1/11 + 1/8).
- Named contrasts (literature review's example): WCH2011 minus mean(WCH1999, WCH2001); WCH2022 minus the same.
- Sensitivity (reported, not in the rules): (A)-(C) on raw championship mean RT (both sexes, unadjusted); WIC added.
- **Decision rules.** Sign: "SAMPLING CAN FLIP THE SIGN" if, for C2, the share of opposite-sign designs is >= 0.10
  under (A) or P(opposite sign) >= 0.10 under (B, Haugen design); otherwise "SIGN STABLE UNDER SAMPLING".
  Published effects: Haugen's +30 ms (C3; group sizes 2 and 5) and Han's -4 ms (C4; sizes 11 and 8) are each
  "WITHIN SAME-RULE NOISE" if |effect| <= the same-rule 95% half-width for those sizes ((C) percentile half-width
  (q97.5 - q2.5)/2 for 2 vs 5; parametric for 11 vs 8), otherwise "EXCEEDS SAME-RULE NOISE".

**H4: the sex gap depends on the championship.**
- Model: the H2 offsets model plus a sex x championship interaction (sum-coded), ML. Per-championship gap (women
  minus men) with Wald CI; average gap (main effect); LRT interaction vs additive (df 17); DerSimonian-Laird tau of
  the per-championship gaps; 95% prediction interval = average +/- 1.96 tau; range (max - min) with championships;
  counts of negative point estimates and of CIs excluding 0 in each direction. Secondary: flat sprints only.
- **Decision rule.** "CHAMPIONSHIP-DEPENDENT (sign not stable)" if LRT p < 0.05 and the prediction interval includes
  0; "VARIES IN SIZE, NOT SIGN" if LRT p < 0.05 and it excludes 0; "NO EVIDENCE OF VARIATION" if LRT p >= 0.05.
- Context: Lipps et al. 2011 (one championship, Beijing 2008) vs Mirshams Shahshahani et al. 2018 (gap gone by 2012).
  Caveat fixed now: athletes are linked across championships only from 2015; hurdles differ by sex (100 mH vs
  110 mH), which loads onto the gap (hence the flat-sprint secondary).

**H5: venue dependence inside Fiore et al.'s own published model.**
- Parameters transcribed from the manuscript source (github.com/ofiore/Thesis at commit 85d9a60b6874,
  `Manuscript/manuscript.tex` Table 2 and `Manuscript/supp.tex` women's table) into `analysis/fiore2025_params.csv`
  with their published tail probabilities and barriers: men including 2022 (primary), men excluding 2022, women.
- Model as in their code (`Code/ReactionBarrierAnalysis.Rmd`, `simfit`): RT ~ GG(mu, sigma, nu), log mu = beta0 + v,
  log sigma = gamma0 + h, v ~ N(0, tau_v^2), h ~ N(0, tau_h^2); their 10^7-draw Monte Carlo is replaced by
  Gauss-Hermite quadrature (80 nodes per dimension; deterministic).
- Estimands: marginal P(RT < 0.080, 0.090, 0.100) and barriers at tails 1e-2, 1e-3, 1e-4 (reproduction check);
  the same at the median venue (v = 0); 1e-3 barriers at venue quantiles 2.5%, 25%, 75%, 97.5% of N(0, tau_v^2);
  **X = barrier(97.5% venue) - barrier(2.5% venue)** (primary, men incl. 2022), the interquartile-venue difference,
  and marginal minus median-venue.
- Secondary: per-year venue effects, if they can be read exactly from the vector figure
  `Manuscript/ComparisonOfVenueEffects.pdf` (removed from the published paper; axis calibrated from its tick labels),
  giving the barrier at each of the 13 WCH venues and its range; otherwise the 2022 value digitised by the novelty
  check (-0.131), labelled as digitised.
- **Decision rules.** "REPRODUCED" if every published marginal P(RT < 0.100) is matched within 5% (relative) and every
  published barrier within 1 ms (P(RT < 0.080) for women, about one event in 10^7 draws, is reported only);
  otherwise "NOT REPRODUCED" with the differences. "VENUE MATERIAL WITHIN FIORE ET AL.'S MODEL" if X >= 10 ms (the
  H2 bar), otherwise "NOT MATERIAL".

**O2 (optional, if time allows): RT vs 100 m time, pooled vs within championship (Tonnessen et al. 2013 design).**
- 100 m outdoor (WCH2015-2025, OG2020, OG2024), valid RT and a numeric time, per sex: Pearson r pooled; after
  centring both variables within championship; within race (centred within race). Race-cluster bootstrap within
  championship (paired, B = 2,000).
- **Decision rule.** "CHAMPIONSHIP-CONFOUNDED" if |r_pooled - r_championship-centred| >= 0.10 and its paired 95% CI
  excludes 0; otherwise "NOT CONFOUNDED BY CHAMPIONSHIP".

### Addendum 4 (2026-09-30, ~10:50 PT): H1-S4 and H6, fixed before computing

Requested by the author. Committed before any S4 or H6 quantity was computed (the H3-H5/O2 code of
addendum 3 was written but not yet run). **Already visible:** `calibration.r_corrected` and
`calibration.r_ci_high_at_b_low` (the calibrated within-championship r and its conservative upper bound),
`descriptive.fs_near_threshold_090_100` (all near-threshold false starts at one championship), the offsets table, and
Haugen et al.'s reported cells (lit/systematic_forensics.md section 1.2).

**H1-S4: did Haugen et al. analyse within championships? (SIMULATION)**
- Haugen's reported cells: men 1997-2003 r = 0.16, women 1997-2003 r = 0.17, men 2003-2009 r = 0.16 (all P < 0.001);
  women 2003-2009 not significant.
- Design: two rule eras x two sexes; each era = 5 championships shared by the sexes (the S3 `cell5` layout per sex:
  11 heats x 7.5 starts per championship, about 3 starts per athlete); championship mean holds (truncated to
  1.3-2.2 s) and championship RT offsets shared by men and women of that championship and independent of each other;
  heats, athletes and residuals separate by sex. Hold SDs and RT SDs as in S3. A true hold effect beta acts on every
  start (within and between championships), scaled so that the within-championship correlation equals r_w.
- Two analyses of every simulated study: (i) WITHIN (hold and RT centred within championship, per cell);
  (ii) POOLED (uncentred, per cell; Haugen-style).
- Pattern = r >= 0.16 (men 1997-2003), >= 0.17 (women 1997-2003) and >= 0.16 (men 2003-2009). Secondary "full
  pattern" adds women 2003-2009 with naive p >= 0.05.
- Settings: r_w = our estimate (`calibration.r_corrected`) and our conservative calibrated upper bound
  (`calibration.r_ci_high_at_b_low`); POOLED also at r_w = 0. 20,000 studies per setting.
- P(pattern | WITHIN) = product of the three per-cell probabilities (cells share no heats or athletes and the
  championship components are removed by centring); each per-cell probability is the simulated share when at
  least 200 of the 20,000 studies reach the threshold, otherwise the normal approximation with the simulated mean and
  SD. P(pattern | POOLED) = the joint simulated share (cells within an era share championships).
- Likelihood ratio LR = P(pattern | POOLED) / P(pattern | WITHIN), at the same r_w.
- Inversion: the smallest r_w on a 0.005 grid (0 to 0.30; 5,000 studies per point) with P(pattern | WITHIN) >= 0.05,
  linearly interpolated: r_star.
- **Decision rules.** Likelihood: "FAVOURS POOLED" if LR >= 10 at our estimate, "FAVOURS WITHIN" if LR <= 0.1,
  otherwise "INCONCLUSIVE" (LR at the upper bound reported alongside). Inversion: "WITHIN READING NEEDS r_w ABOVE OUR
  CI" if r_star > `calibration.r_ci_high_at_b_low`, otherwise "WITHIN READING COMPATIBLE WITH OUR CI".
- Stated caveat (sensitivity, not a rule): before 2010 each race allowed one false start, which may have changed
  anticipation, so the within effect then could genuinely differ from ours; r_star says how large it would have to be.

**H6: is championship-level variation getting worse, and does it put the 0.100 s rule at risk from the system?**
- Offsets: the athlete-adjusted championship offsets (H2 model). Periods: pre-2010 (WCH1999-2009, 6), 2010-2019
  (WCH2011-2019, 5), 2020-2025 (OG2020, WCH2022, WCH2023, WCH2025, OG2024, 5); outdoor only; sensitivity: WIC2024/2025
  added to 2020-2025.
- (a) Dispersion: SD of offsets within each period; ratio SD(2020-2025) / SD(pre-2010) (primary) and
  SD(2020-2025) / SD(2010-2019), with bootstrap CIs (championships resampled within period and offsets redrawn from
  their sampling distribution, B = 5,000; percentile). Sensitivity: F-distribution CI of the variance ratio. Trend:
  slope (ms per decade) of |offset - linear time trend| on year over the 16 outdoor championships, bootstrap CI
  (championships resampled); the plain |offset| slope as a sensitivity.
- (b) Modelled rate of legitimate sub-0.100 s starts at each championship: the reference ex-Gaussian of
  `descriptive.json` (men) shifted by the championship's offset (the `fairness.json` model), per 1,000 starts; period
  medians and maxima, and each championship listed. Descriptive only.
- (c) Near-threshold recorded false starts (RT 0.090-0.100 s): count by championship and period (factual).
- **Decision rule (a).** "WORSENING" if the bootstrap 95% CI of SD(2020-2025) / SD(pre-2010) lies above 1;
  "IMPROVING" if it lies below 1; otherwise "PERSISTING, NOT WORSENING".
- **Update (2026-09-30, ~10:55 PT): H1-S4 and H6 are delegated to trend.py** (a separate producer,
  `analysis/trend.py` with its own pre-registration `analysis/prereg_addendum_trend.md`). The addendum 4 text above
  is kept as written; none of it is computed in `systematic.py`.

### Addendum 5 (2026-09-30, ~11:15 PT): post-hoc diagnostics after the development run of H3-H5/O2

Added after seeing the development output; none changes a pre-registered verdict, and each is labelled POST-HOC.
- **H5, men excluding 2022:** the printed parameters (Table 2, row "Excluding 2022") do not reproduce that row's
  published tail probability and barriers, while the other two sets do. Two diagnostics: (i) the intercept beta0
  that reproduces each set's published P(RT < 0.100) with its other printed parameters (`h5_<set>_implied_beta0`);
  (ii) the shift between the two panels of Fiore et al.'s venue-effects figure (mean top-panel effect over the 12
  shared years minus the mean bottom-panel effect), the change of intercept that removing 2022 implies.
- **H4:** every negative per-championship sex gap came from 1999-2009, which come from a different source table
  (rt_fiore: other round and event composition, anonymous athletes). Sensitivity: the same model restricted to the
  12 championships from 2015 on (athlete-identified; `h4_modern_*`).
- Correction to addendum 5: the 2015-on subset has 10 championships (WCH2015-2025, OG2020, OG2024, WIC2024, WIC2025), not 12.
- Note on times: the "~HH:MM PT" stamps in addenda 3-5 are approximate (they ran ahead of the clock); the git commit
  times of each addendum are authoritative and precede the corresponding computations.


### Note (2026-09-30, after the false-start classification fix, commit 5a12182)

A data-cleaning bug in `common.normalize_rt` was fixed: the false-start label regex matched inside "(not a false
start)" (hurdle and lane DQs counted as false starts, their legal RTs dropped from the valid set), and the Fiore et
al. file's RT 0.000 placeholders were treated as measured RTs. Every producer was rerun and every verdict recomputed
on the corrected data. **No verdict changed** (H1 SUPPORTS the mechanism, observed structure; H2 CONSEQUENTIAL; H3
SAMPLING CAN FLIP THE SIGN, Haugen EXCEEDS and Han WITHIN same-rule noise; H4 CHAMPIONSHIP-DEPENDENT; H5 NOT
REPRODUCED for the excluding-2022 row only, VENUE MATERIAL; O2 NOT CONFOUNDED). The numbers behind them moved slightly;
every change is listed in `notes/bugfix_rerun_diff.md`.
