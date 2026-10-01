# Novelty: ranked candidate contributions

Part of the literature review. **Version 2, 2026-09-29.** This supersedes v1 (23:25 PT on 9/28).

**Tags**
- **[V-FT]**: specific line checked in the full text or data.
- **[V-ABS]**: abstract only.
- **[S]**: secondary source.
- **[U]**: unverified.

Evidence and citations are in `review.md`, terms in `definitions.md`, data in `datasets.md`, and keys in `refs.bib`.

Planning numbers below come from `lit/planning/*.py`. They are **not results** and must not appear in the abstract.

## Bottom line

**Lead with C1: foreperiod-conditional false-start risk.** Measure it on **official Seiko hold times** (World Championships 2022/23/25 and World Indoors 2024/25), and use **C2 (automated broadcast-audio measurement, validated against those official holds)** as the methods contribution that extends coverage to the Olympics and earlier years.

The claim to test: *the starter's hold, which the rules leave entirely to the starter, shifts the RT distribution enough to change the chance that a legitimate reaction is scored below 0.100 s.* Report the size, with uncertainty, across the holds starters actually use.

Why lead with it:
1. **It answers the brief's second question.** It turns "what does this mean for the 0.100 s rule?" into a number: the ratio of false-positive DQ risk between short and long holds, with a CI.
2. **The gap is sharp and recent.**
   - Fiore et al. 2025 give an *unconditional* P(RT < 0.100) of 1 in 362 men's starts. In their model, heat-level dispersion dominates the tail (τ_h = 0.32), and they do not identify its cause [V-FT].
   - Brosnan et al. 2017 (raise the threshold to 115/119 ms) [V-ABS] and Fiore et al. (lower it to about 0.094 s) [V-FT] reach opposite conclusions from tail extrapolation. Neither conditions on anything the starter does.
   - Haugen 2013 found the hold shifts RT and changes its IQR [V-ABS], but did no tail analysis.
3. **The tail amplifies small effects.** Planning calculation on Fiore's published parameters (`gg_tail_planning.py`, which reproduces their 2.76e-3 as 2.78e-3):
   - a −5 ms location shift gives ×1.7 tail probability, and +5 ms gives ×0.58;
   - the 90th-percentile heat's dispersion gives about 18× the median heat's tail.
4. **Theory makes the result informative whichever way it comes out** (review §5.11). Hazard, reciprocal-PDF and memory accounts predict different signs above the modal hold. A positive, negative or null slope each discriminates between accounts, and a tight null ("the rule is hold-robust") is also useful to World Athletics.
5. **It is now cheap and well powered.**
   - Official holds (about 250–300 heats, estimated) plus per-athlete RTs from World Athletics.
   - The analysis's power check: about 50 races give 80% power for a Haugen-sized r at the observed race ICC of 0.04 (STATUS 00:10). My own planning run: 85 races give 84% power for 22 ms/s.
6. **Framing that sells.** The sprint start is the textbook example of temporal preparation. Cui et al. 2009 open with "when a sprinter waits for the starting pistol"; Yarrow et al. 2026 with "as when a sprinter learns the constant foreperiod from set to go" [V-ABS]. Yet Bausenhart & Ulrich 2026 note "surprisingly little research has been devoted to examining the role of temporal predictions in such fields more closely" [V-FT].

**Main risks and how to handle them**
- **Detector regimes.** The analysis's adjusted championship RT offsets span 42 ms (WCH 2022 −18 ms to WCH 2025 +24 ms vs the mean; STATUS 00:10). Estimate the hold effect *within* championship with a fixed effect, and check detection latency on the waveform traces (STATUS 00:49).
- **Selection.** DQ'd anticipations are missing from valid RTs. Model the left tail as censored, keep positive DQ RTs as Fiore did, and report false-start incidence against the hold separately. That needs audio holds for recalled attempts, because waveform images show only the final attempt.
- **Endogenous holds.** Starters wait for the slowest settler (TR 16.3 and its commentary), and Zemper says holds are shortest at the first start of a session and after a false start. Control for round, event, attempt number and session order. C9 gives each athlete's settle time.
- **`Ready Time` definition [U].** Validate against broadcast-audio set onset on about 10 heats before relying on it (measurement pipeline).

**Fallback if official holds are not extracted in time:** lead with C2 (the validated pipeline plus the first open distribution of championship holds) and report C1 as preliminary.

## Ranking

Criteria scored 1–5: N = novelty, R = academic rigor / validity, Rep = reproducibility, A = application, I = interest/impact. Feasibility is H/M/L.

| Rank | Candidate (brief label) | N | R | Rep | A | I | Oct 1 | Dec 4 |
|---|---|---|---|---|---|---|---|---|
| **1** | **C1 Foreperiod-conditional P(RT < 0.100); rule fairness (c)** | 5 | 4 | 5 | 5 | 5 | **H–M** | H |
| 2 | C3 Which temporal expectation drives elite RT? hazard vs PDF vs memory; absolute vs session-relative hold (b) | 5 | 5 | 4 | 3 | 4 | M | H |
| 3 | C2 Automated broadcast-audio foreperiod measurement validated against official Seiko holds (a) | 3 | 4 | 5 | 4 | 3 | H | H |
| 4 | C9 Pre-gun force dynamics from official waveforms: settle time, steadiness decay, onset slope vs hold (subsumes v1's C8) | 5 | 4 | 4 | 3 | 4 | M–L | M–H |
| 5 | C5 "Heat lottery": time-qualifier decisions inside the hold-induced margin | 4 | 3 | 5 | 5 | 5 | M | H |
| 6 | C6 Sequential and state-dependent effects: the athlete's previous-round hold; starter behaviour after false starts or at the first start (d) | 5 | 4 | 4 | 3 | 3 | M–L | M |
| 7 | C4 Start-procedure design evaluation by simulation (fixed vs human vs non-aging holds; catch starts) | 4 | 3 | 5 | 5 | 4 | M | H |
| 8 | C7 Elite RT–foreperiod curve vs open lab curves (e) | 4 | 3 | 5 | 2 | 4 | M | M–H |

What changed from v1:
- C1's Oct 1 feasibility rose (official holds found).
- C3 moved up: official holds by session make it testable, and the theory predictions are now worked out.
- C2 moved to third: manual broadcast measurement is prior art (Otsuka 2017), and the official holds reduce C2's necessity for World Championships.
- The new C9 comes from the waveform force traces.
- C7 rose on feasibility: CC0 auditory Set–Go data covering 0.4–2.8 s now exist.

---

## Positioning against the closest prior work

What each did, and what we add. Every claim here is checked (review.md).

| Work | What it did | What it did not do |
|---|---|---|
| Haugen et al. 2013 [V-ABS] | Holds from TV (267 heats, 1.3–2.2 s); r(RT, hold) ≈ +0.16; IQR trends | No tail or DQ-risk analysis, no expectation model, no measurement-error estimate, no data release. Mostly pre-2010 rules; method details unverifiable (closed access) |
| Otsuka et al. 2017 [V-FT] | Manual broadcast-audio holds (83 races, 1.780 ± 0.158 s); lab foreperiod effect 156 → 117 ms; recommends recording or fixing holds | No automation or validation; did not link championship holds to championship RTs; no tail analysis. Its lab sign is the opposite of Haugen's |
| Dalmaijer et al. 2015/2016 [V-FT] | Speed skating: manual audio intervals, alerting framing, within-skater +174 ms/s | Other sport; finishing times not RTs; no RT tail; proposed fixed intervals informally |
| Fiore et al. 2025 [V-FT] | Unconditional generalized-gamma tail, P(< 0.100) ≈ 1/362; heat effect on σ; 2022 anomaly | No hold covariate; heat effect unexplained; vendor not named; rule-history error |
| Brosnan et al. 2017 [V-ABS] | Ex-Gaussian thresholds 115/119 ms | Unconditional; opposite conclusion to Fiore |
| Julin 2003 [V-FT] | Informal argument that wider, longer holds deter guessing | No data model, no RT analysis |
| Yarrow et al. 2026 [V-ABS] | Lab model of the RT/anticipation trade-off under learned foreperiod distributions (open Stan code) | No sport data. We *apply* such models to real starts |
| Crowe & Kent 2019 [V-ABS] | Auditory foreperiod-memory transfer, motivated by racing starts (no one-week transfer) | Lab only. It gives a falsifiable prior for our C6 |
| Grabenhorst et al. 2019–2026; Salet et al. 2022; Janssen & Shadlen 2005 [V-FT/V-ABS] | Competing lab accounts (PDF, fMTP, subjective hazard) with open data in the 1.3–2.6 s range | Never tested on field data |

---

## C1. Foreperiod-conditional false-start risk (LEAD)

- **Claim.** P(a gun-triggered reaction registers < 0.100 s | hold) varies across the hold range starters use, through hold effects on RT location and dispersion. Report the ratio for short vs long holds (e.g., 10th vs 90th percentile) with a 95% CI. Also report the observed false-start incidence against the hold.
- **Novelty.** First foreperiod-conditional estimate. Prior tail analyses are unconditional (Fiore; Brosnan; Lipps; Komi), and prior hold analyses have no tail (Haugen; Otsuka) (review §2.2–2.3).
- **Mechanism** (review §5.6–5.8):
  - Readiness is scheduled by expected timing (Carlsen & Mackinnon 2010 [V-FT]).
  - Loud go signals release fully prepared actions early; block speakers play at 114 dB @ 1 m; StartReact latencies are about 70–90 ms.
  - Anticipations rise with waiting time (Tucker 2009; Leow 2018 [V-FT]).
- **Data.** Seiko `Ready Time` and `Attempt` per heat; per-athlete RTs (World Athletics); covariates: championship, round, event, sex, lane, session order, attempt.
- **Cheapest verifying experiment.**
  1. Hierarchical generalized-gamma GAMLSS reproducing Fiore's structure (heat effect on log σ), plus hold terms (spline) in log µ and log σ, and a championship fixed effect.
  2. Does hold explain part of τ_h? Compare τ_h with and without hold.
  3. P(< 0.100 | hold) by parametric bootstrap at hold percentiles.
  4. Sensitivity to distribution family (ex-Gaussian, shifted lognormal), to including or excluding positive DQ RTs, and to censoring below 0.100.
  5. Incidence: logistic false-start probability vs hold. **The hold of the recalled attempt is needed.** Seiko images appear to publish only the final attempt (a restart shows `Attempt : 002`), so measure recalled attempts from broadcast audio (C2). This is one more reason C2 matters.
- **Feasibility.**
  - Oct 1: **H–M.** It depends on waveform OCR for about 150+ heats; the analysis code is small.
  - Dec 4: **H**, adding Omega-timed Olympics via C2 audio holds for a vendor contrast.
- **SSAC fit.** Novelty 5; rigor 4 (distributional mixed model, several families, within-meet design); reproducibility 5 (public sources, open code); application 5 (fair DQ adjudication, hold standardization; Devon Allen 2022 context); interest 5.

## C2. Automated broadcast-audio foreperiod measurement, validated against official holds (methods)

- **Claim.** An automated pipeline measures set onset → gun onset from public broadcast audio: ASR plus forced alignment or energy onset for "set", and a transient detector for the gun. It agrees with the official Seiko `Ready Time` within X ms (bias and limits of agreement) on the same heats, and flags low-confidence clips. That lets hold data be built for meets with no official waveforms: World Championships 2009–2019, the Olympics (Omega) and the Diamond League.
- **Novelty.**
  - Prior measurements were manual waveform inspection: Otsuka 2017 (EDIUS, 10 ms, 83/88 races usable) [V-FT]; Dalmaijer 2015 (Audacity) [V-FT]; Haugen 2013 (unknown method) [V-ABS].
  - Sports-audio detection exists only for highlights (whistles, tennis hits).
  - No validated tool and no open hold dataset exist.
  - **Not a first measurement: say "first automated and validated".**
- **Data.** About 20–40 heats with both an official `Ready Time` and a broadcast clip; synthetic audio with known foreperiods at varied SNR.
- **Cheapest experiment.**
  - Agreement: Bland–Altman and ICC(A,1) of audio vs Seiko.
  - Detection rate by broadcast source.
  - A two-upload check for the broadcast-path offset.
  - Otsuka's 94% usable-race rate as an external benchmark.
- **Feasibility.** Oct 1 **H**; Dec 4 **H**.
- **Fit.** Novelty 3; reproducibility 5; application 4 (a federation could publish holds like wind readings, as Otsuka suggested).

## C3. Which temporal expectation drives elite RT?

- **Claim.** Championship RT follows one account more than the others:
  - (a) objective or blurred hazard: speeding with hold;
  - (b) reciprocal PDF: fastest slightly *below* the modal hold, with slowing above it;
  - (c) fMTP / memory: speeding up to the mode, then a plateau;
  - (d) fixed-foreperiod or alerting decay: monotonic slowing.

  It also tests whether athletes condition on the *session's* holds or on a long-run prior.
- **Discriminating predictions** (review §5.11; my verification script `fp_model_shapes.py`):
  1. The fastest hold is about 1.71 s under PDF (φ = 0.21), about 1.92–2.05 s under hazard with 1–10% aborts, and at the top of the range under blurred hazard.
  2. The slope above the mode is positive (PDF), negative (hazard) or about zero (fMTP).
  3. False-start incidence and valid-RT speed move *together* under hazard but *dissociate* under PDF.
- **Novelty.** These accounts are debated in the lab with open data in the 1.3–2.6 s range (Salet 2022 Gaussian 1.3/1.95/2.6 s; Grabenhorst 2026 up to 2.8 s; Trillenberg 2000). They have never been tested on field starts, despite the sprint framing (Cui 2009; Yarrow 2026).
- **Data.** C1 data plus `session_id` (definitions §6).
- **Cheapest experiment.**
  - Build predictors (raw hold; hold z-scored within session; objective, abort-adjusted and blurred hazard; blurred PDF; φ grid 0.1–0.3), using championship-wide vs session-specific densities.
  - Compare them by cross-validated likelihood in the C1 model.
  - Run a simulation identifiability check first: can about 250 heats separate the shapes?
- **Feasibility.** Oct 1 **M** (at minimum the curve shape with a spline and the location of the fastest hold). Dec 4 **H**.
- **Fit.** Novelty 5; rigor 5; application 3; interest 4.

## C9. Pre-gun force dynamics from official waveforms (new)

- **Claim.** The Seiko images show each lane's block-force trace from −2 to +1 s. From them, measure:
  1. each athlete's **settle time** after "set" (the rise into position is visible);
  2. **steadiness** over the hold (does it decay with longer holds, as starters believe?);
  3. the **force-onset slope** after the gun vs hold.

  Point 3 tests the Motor Readiness prediction that prepared responses are "softer" (Mattes & Ulrich 1997, via Bausenhart & Ulrich 2026 [V-FT]). If so, force-triggered official RT carries a hold-dependent detection lag.
- **Novelty.** No published analysis of these traces. No study of set-position physiology during the hold (review §5.9 gap). The athlete-specific effective foreperiod (own settle → gun) is new, and replaces v1's C8.
- **Data.** Digitized traces: blue curve per lane panel, about 1.7 ms/pixel horizontally.
- **Cheapest experiment.**
  - Digitize 20 heats.
  - Check settle-time extraction by visual annotation.
  - Correlate own-settle foreperiod with RT.
  - Measure red-marker vs visible-rise lag by championship (the detector-regime check).
- **Feasibility.** Oct 1 **M–L**; Dec 4 **M–H**.

## C5. "Heat lottery": qualification counterfactuals

- **Claim.** Time-qualifiers ("q") compare athletes from different heats. Some decisions fall inside the RT margin that the heat's hold can create. Report the count of flips under hold adjustment, with bootstrap uncertainty.
- **Novelty.** Dalmaijer made the argument for speed skating [V-FT]. Nobody has done it for sprint qualification.
- **Data.** Per-heat holds, results with Q/q marks, and β from C1.
- **Feasibility.** Oct 1 **M** (trivial once β exists); Dec 4 **H**.
- **Caveat.** An RT shift may not carry fully into finish time.

## C6. Sequential and state-dependent effects (athletes *and* starters)

- **Claims.**
  - (i) *Athlete side.* The hold experienced in an athlete's previous round, or in an aborted first attempt, modulates current RT, with the asymmetric pattern of the lab literature.
  - (ii) *Starter side.* Zemper's claim, verbatim [V-FT]: "For any starter, the fastest starts (i.e., the shortest hold times) tend to be the first start of the day and any start after a false start." That makes holds *endogenous* and state-dependent.
- **Novelty.** Robust in the lab (Los 2014/2017; Salet 2022), never tested in competition. Crowe & Kent 2019 [V-ABS] found no one-week transfer for auditory foreperiods, which gives a falsifiable prior: cross-day effects should be about zero, same-session effects small. Continuous, dense distributions weaken sequential effects (Welhaf 2026; Steinborn 2008), so expect small effects. Report them with CIs.
- **Data.** Athlete-linked rounds (names from World Athletics results), `session_order`, `attempt`.
- **Feasibility.** Oct 1 **M–L** (the starter-side test is quick); Dec 4 **M**.

## C4. Start-procedure design by simulation

- **Claim.** Using the fitted C1/C3 model with parameter uncertainty, compare:
  - current human holds;
  - a fixed hold (Otsuka; Dalmaijer);
  - a jittered Gaussian hold;
  - a non-aging hold (exponential with a floor; constant hazard);
  - catch starts.

  Compare them on starter-induced between-heat RT variance, legitimate DQ risk and anticipation risk.
- **Novelty.** Only informal proposals exist (Otsuka 2017; Dalmaijer 2015; Julin 2003 [V-FT]). Precedents: ISU 1–1.5 s window, FIA random 0.2–3.0 s delay, US Rowing "distinct and variable pause" [V-FT]. Non-aging distributions flatten foreperiod effects in the lab (Bausenhart & Ulrich 2026 [V-FT]; Trillenberg 2000 digitized: 297/291/294 ms).
- **Feasibility.** Oct 1 **M**; label it *simulation* (the simulation-labelling rule). Dec 4 **H**.

## C7. Elite curve vs lab curves

- **Claim.** Placed on common axes, the elite RT–hold curve is flatter, reversed or shifted relative to lab curves covering the same interval range. This quantifies how single, high-stakes, loud-signal starts under a DQ threat alter temporal preparation.
- **Data.**
  - Grabenhorst et al. 2026 auditory Set–Go curves 0.4–2.8 s (CC0).
  - Salet 2022 Gaussian 1.3/1.95/2.6 s.
  - Herbst 2018, auditory, mean 1.8 s with graded spread.
  - Yarrow 2026 anticipations.
- **Cheapest experiment.**
  - Normalize RT to each dataset's median, and express hold in seconds and in units of the distribution's SD.
  - Overlay the curves with bootstrap CIs.
  - Fit the same PDF and hazard predictors to all of them.
- **Feasibility.** Oct 1 **M** (a supplementary figure at most; the abstract allows only 2 tables/figures). Dec 4 **M–H**.

---

## Suggested Oct 1 abstract spine

Only if the data land; every number must come from repo code.

- **Methods.**
  - Official Seiko holds and per-athlete RTs, World Championships 2022–25 (N heats, M starts).
  - Hierarchical generalized-gamma model with hold terms in location and scale, and championship fixed effects.
  - Validation subset: automated broadcast-audio holds vs official (C2).
- **Results.**
  1. Hold distribution (mean, SD, range; by round).
  2. Hold effect on RT location and dispersion with CI, and its share of heat-level variance.
  3. P(RT < 0.100 | hold) at short vs long holds with CI (C1).
  4. Where RT is fastest relative to the modal hold (C3 headline).
  5. Audio-vs-official agreement (C2).
- **Conclusion.** What a hold-conditional error rate implies for the 0.100 s rule: record holds; consider standardized or random electronic holds.

## Planning files (not results)

- `lit/planning/gg_tail_planning.py` (+ `.out.txt`): tail sensitivity on Fiore et al.'s published men's parameters.
- `lit/planning/power_planning.py` (+ `.out.txt`): power for a race-level hold slope.
- `lit/planning/fp_model_shapes.py` (+ `.out.txt`): theoretical predictor shapes for a Gaussian hold distribution (hazard, abort-adjusted hazard, blurred hazard, blurred PDF).
