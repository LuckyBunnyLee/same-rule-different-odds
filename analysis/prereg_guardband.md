# Pre-registration (guardband.py): a WADA-style guard band for the 0.100 s false-start rule

Status: written and committed on 2026-09-30 (about 17:45 PT) BEFORE any guard-band quantity was computed.
Producer (written after this file is committed): `analysis/guardband.py` -> `analysis/outputs/guardband.json`
(result name `guard`, so its keys enter `analysis/numbers.json` as `guard.*` through `make_numbers.py`). No existing
producer, key, result or shared file is modified. The producer is registered in `analysis/run_all.py`.

**Question.** World Athletics applies the 0.100 s line as simple acceptance with no declared measurement uncertainty.
Anti-doping handles an analogous problem with a decision limit DL = T + g, g = k x u_c,Max, k = 1.645 (one-sided 95%),
with u_c,Max built from between-laboratory reproducibility (WADA TD2022DL; JCGM 106:2012 "guarded rejection";
`lit/policy_mechanism.md` section 3.4, `lit/systematic_forensics.md` section B1). What would the athletics analogue,
built from between-championship variation, do to (a) the modelled rate at which legitimate starts are flagged and
(b, c) historically flagged false starts?

**Already visible when this was written.**
- `analysis/results.md` sections 1, 4, 5, 5b and 6: the per-championship athlete-adjusted offsets with CIs
  (`descriptive.json` table `meet_effects`); `descriptive.sd_championship_ms` = 9.276 ms (95% CI 6.566 to 13.107);
  the modelled per-championship P0 rates (`fairness.json` table `meets`; highest WCH2022, 14.16 per 1,000;
  middle-half fold 18.2); the men's reference ex-Gaussian parameters; recorded false starts: 73 in all, 64 with an RT,
  4 with RT in [0.090, 0.100), all at WCH2022.
- `lit/systematic_forensics.md` section B1 states the illustrative arithmetic 1.645 x 9.3 ms = about 15 ms.
- Back-of-envelope reasoning (no code run): with g of about 15 ms the highest modelled rate should fall to the order of
  1 per 1,000 or below, and a uniform shift deeper into a Gaussian-dominated left tail widens rather than narrows the
  max/median fold spread. The cost side is unknown to me: I have NOT looked at the RTs of recorded false starts below
  0.090 s.
- One structural check was run: every valid RT lies on a 0.001 s grid.

**Design constants (not measurements).** T = 0.100 s. Coverage factors k = 1.645 (primary), 1 and 2 (sensitivities).
Decision bars: 10-fold and 10%. Seed 20260928. 25 offset redraws per reference-bootstrap draw. P1 trade-off curve over
g = 0 to 30 ms in 0.5 ms steps.

---

## Model (the fairness model, reused read-only)

- A legitimate (gun-triggered) start at championship c has RT = R + o_c.
  - R ~ the reference distribution of `descriptive.json` `extra.reference_fits` (average championship, first round,
    flat sprint; left-truncated fit). **Men, ex-Gaussian is primary**; women ex-Gaussian, and men shifted lognormal and
    shifted Wald, are sensitivities.
  - o_c = the athlete-adjusted championship offset (`meet_effects.deviation_ms`, standard error `se`), a pure location
    shift, as in `fairness_sim.py`.
- Probability that a legitimate start is flagged under acceptance limit L_c: F_R(L_c - o_c), computed with
  `fairness_sim.p_fs` (read-only import).
- Under P0 this must reproduce `fairness.json` table `meets` (men, ex-Gaussian; relative difference < 1e-4), or the
  producer stops.

## Uncertainty u and guard band g

- **Primary u = `descriptive.sd_championship_ms`**: the REML random-intercept SD of championship in the crossed
  championship / race / athlete model. It estimates the SD of the true athlete-adjusted offsets, i.e. it is net of
  their estimation error by construction.
- Sensitivities for u (P1 at k = 1.645):
  - the two ends of the CI of `sd_championship_ms`;
  - u_mom = sqrt(max(0, var(o-hat) - mean(se^2))) over the 18 fixed-effect offsets (moment estimator, net of
    estimation error);
  - u_raw = SD of the 18 fixed-effect offsets (ddof 1; not net);
  - u_comb = sqrt(sd_championship^2 + sd_race^2): adds the between-race component.
- g = k x u, unrounded.

## Policies

- **P0 (current):** flag if RT < 0.100 s.
- **P1 (guard band):** flag if RT < 0.100 - g, g = k x u. Primary k = 1.645; k = 1 and 2 are sensitivities.
- **P2 (per-championship calibration):** flag if RT < 0.100 + o-hat_c, with o-hat_c the championship's estimated
  offset. This is the idealised harmonisation an audit would enable. At slow-scoring championships (o-hat_c > 0) it
  raises the limit.
- **P3 (P2 plus a residual guard band):** flag if RT < 0.100 + o-hat_c - k x se_c. This guards against offset
  estimation error, championship by championship. Primary k = 1.645; k = 1 and 2 are sensitivities. A further
  sensitivity uses one common u_res = max_c se_c, the analogue of WADA's u_c,Max.
- Championships: all 18 in `meet_effects` (16 outdoor and 2 World Indoors), as in `fairness.json`.

## Metrics

**(a) Modelled legitimate-flag rate per 1,000 starts** at each championship under each policy (SIMULATION).
- Summaries over the 18 championships:
  - the maximum, with its championship;
  - the median;
  - the max/median fold;
  - the middle-half fold: 75th / 25th percentile of the 18 rates (numpy linear interpolation);
  - the cut relative to P0: max_P0 / max_policy, and median_P0 / median_policy.
- **Point estimates are plug-in:** point reference parameters, with true offsets taken equal to their estimates. Under
  P2 the plug-in rate is therefore F_R(0.100) at every championship by construction. Its CI shows what offset
  estimation error does.
- **CIs:** 95% percentile intervals over joint draws.
  - Each of the 200 race-cluster bootstrap reference fits stored in `descriptive.json` is combined with 25 redraws of
    the true offsets, o*_c ~ N(o-hat_c, se_c^2), independently per championship.
  - Limits stay fixed at their plug-in values: 0.100 - g for P1; 0.100 + o-hat_c (- k x se_c) for P2 and P3.
  - Summaries (max, median, folds, cut) are computed within each draw.
  - g is a declared constant and is not redrawn; uncertainty in u enters through the sensitivities.
  - These CIs carry reference-fit and offset uncertainty only.
- **Sensitivities:** women (ex-Gaussian, same offsets); men shifted lognormal and shifted Wald; the u and k variants
  of P1; the k and u_c,Max variants of P3.
- **Descriptive trade-off curve (no rule):** P1 over g = 0 to 30 ms in 0.5 ms steps, giving the maximum and median
  modelled rate and the (c) share.

**(b) Recorded false starts that each policy would no longer flag**, counted by championship from the RT data.
- Recorded false start = `descriptive.py`'s definition: `is_fs`, i.e. RT < 0.100 or an explicit false-start label.
  Only false starts with an RT can be evaluated.
- The producer stops unless its recount equals `descriptive.json`:
  - `fs_recorded_with_rt`;
  - `fs_near_threshold_090_100` and its `by_meet`;
  - the `n_fs` / `n_starts` fields of `fs_per_1000_starts`.
- A false start with RT r at championship c is no longer flagged if r >= L_c.
  - RTs are compared on their 0.001 s grid: round(1000 r) >= 1000 L_c - 1e-9.
  - A recorded false start whose RT is already >= 0.100 s (flagged by label, not by the RT rule) is not counted as
    changed. These are reported separately.
- False starts without an RT cannot be evaluated by any RT-based policy. They are reported as a count.

**(b2) Valid starts newly flagged (P2 and P3 only).** Valid starts (descriptive's valid set: RT 0.100-0.300 s, not a
false start, not DNS) with RT < L_c, where L_c > 0.100 at slow-scoring championships. Reported by championship and
per 1,000 valid starts.

**(c) Cost proxy (P1).**
- The share of recorded false starts with an RT whose RT lies in [0.100 - g, 0.100), with a Wilson 95% CI. This equals
  the P1 count of (b) divided by the false starts with an RT. It is the most anticipations a guard band could let
  through among historically flagged starts.
- The number of recorded false starts with RT >= 0.100 - g at all, including any at or above 0.100.
- Breakdowns: 2015 on (official labels, one source); 2010 on (zero-tolerance era).

## Decision rule (fixed now)

- **Primary cell:** men, ex-Gaussian, P1 with k = 1.645 and the primary u, all 18 championships, point estimates.
- **"PROTECTIVE AT LOW HISTORICAL COST"** if both:
  - (i) max_P0 / max_P1 >= 10, and
  - (ii) the (c) share <= 0.10.
- Otherwise the label reports the trade-off plainly:
  - (i) met, (ii) not: "TRADE-OFF: PROTECTIVE BUT CHANGES MORE THAN 10% OF RECORDED FALSE STARTS";
  - (ii) met, (i) not: "TRADE-OFF: LOW HISTORICAL COST BUT CUTS THE MAXIMUM LESS THAN 10-FOLD";
  - neither met: "TRADE-OFF: NEITHER CRITERION MET".
- The same rule applied to the sensitivity cells is reported descriptively and does not change the verdict.
- Also reported: whether the lower end of the CI of the cut is >= 10.

## Assumptions and wording constraints

- **Simulated is simulated.** Every rate in (a) is a model output. The legitimate-RT model extrapolates the left tail
  of valid starts (fitted on 0.100-0.300 s) below 0.100 s. The family choice changes absolute rates several-fold.
- **True anticipations are not observable.** (b) and (c) count historically flagged starts.
  - They are an upper bound on the anticipations a guard band would let through among those starts (some may have
    been legitimate).
  - They say nothing about anticipations under a new rule: athletes' behavioural response is not modelled.
- **The false-start data source differs before 2015.** Those rows come from Fiore et al.'s file, where a false start
  is visible only as an RT below 0.100 s.
- **"Flagged" is not "disqualified" before 2010.** A first false start did not disqualify then (pre-2003: the athlete's
  own second; 2003-2009: charged to the field).
- **Offsets are treated as pure measurement shifts** (the fairness model's assumption). Their source is not identified.
  If part of an offset were genuine athlete behaviour, P2 would penalise or reward real behaviour.
- **P2 and P3 use RT-based offset estimates as a stand-in for an audit.** A real audit would have its own uncertainty.
- **A guard band is an analogy to WADA, not a transfer of its rule.** The literature review advises against putting a
  guard-band number in the abstract (`lit/policy_mechanism.md` sections 3.4 and 4). The author decides.

## Outputs and tests

- Keys (prefix `guard.*`): g values; the (a) summaries per policy and sensitivity, with CIs; the (b) and (b2) counts
  with by-championship fields; the (c) share and counts; the verdict with its two criteria; the input checks.
  Tables: per-championship rates by policy; the false starts each policy would no longer flag; the P1 trade-off
  curve.
- `analysis/tests/test_guardband.py`:
  - unit tests on synthetic data: limits, grid-edge counting, verdict truth table;
  - claim guards on `guardband.json`, each shown to fire on a corrupted copy: the verdict recomputed from stored
    numbers; g = k x u; P0 equals `fairness.json`; counts equal `descriptive.json`; (c) share = (b) count / n;
    P1 <= P0 at every championship; the P2 plug-in rate = F_R(0.100).
- The rerun must be byte-identical.

---

## Deviations and additions (appended after computing; no rule changed)

**Timing correction.** The header says "about 17:45 PT". `git log` shows the pre-registration was committed at
17:30:13 PT (commit e6203c2), before `guardband.py` existed.

**Deviation 1: which rows count as recorded false starts in (b) and (c).** This changes the verdict, against the
favourable label.
- **What was found.** The recount reproduces `descriptive.json` exactly (73 recorded false starts, 64 with an RT). The
  first run showed 33 "false starts with an RT" at or above 0.100 s. Inspection found two problems in
  `common.normalize_rt`'s `is_fs`:
  - 33 rows (32 with an RT) are non-start disqualifications (TR22.6 hurdles, 163.3(a) lane and similar). Their raw
    notes in `rt_athletes.csv` say "(not a false start)" and their status is DQ, but the regex `false.?start` matches
    that phrase.
  - 5 rows from the Fiore et al. file carry an RT of 0.000, a placeholder for a missing RT (3 are DNS, 2 DQ).
- **Why the correction follows the pre-registration.** The plan defines a recorded false start as "RT < 0.100 or an
  explicit false-start label" and says "only false starts with an RT can be evaluated". The noted rows meet neither
  condition, and a 0.000 placeholder is not a measured RT.
- **Correction.**
  - (b) and (c) use the corrected set "recorded false starts with a measured RT": 27 rows, all 24 status-FS rows with
    an RT from `rt_athletes.csv` plus 3 Fiore rows with negative RTs.
  - The corrected total is 37 recorded false starts, 10 of them without a measured RT.
  - The correction is cross-checked in code against the raw notes: all 33 noted rows are found, none has RT < 0.100 s,
    and none has status FS.
- **Sensitivities reported.** "Note fix only" (32 rows, placeholders kept) and the literal `descriptive.py` set (64).
- **Effect on the verdict.**
  - The P1 counts in (b) are the same on every set: the same 4 false starts at WCH2022.
  - The (c) share is 4/27 = 0.148 (primary), 4/32 = 0.125 (note fix only) and 4/64 = 0.0625 (literal set).
  - The two corrected sets read "TRADE-OFF: PROTECTIVE BUT CHANGES MORE THAN 10% OF RECORDED FALSE STARTS". Only the
    literal set reads "PROTECTIVE AT LOW HISTORICAL COST", and it is reported in the verdict's fields marked as an
    artefact.
- **(b2) valid starts** use the same correction: 6,408 rows instead of 6,376, because the 32 non-start DQs keep their
  legal RTs, as `descriptive.py` intends. The newly flagged count is 1 on both sets.
- **Upstream (not fixed here).** The same classification inflates `descriptive.json`'s `fs_per_1000_starts`,
  `fs_recorded_with_rt`, the per-championship false-start rates, and the valid-start set used by every fit. The fix
  belongs in `common.py` (it was made there; see `notes/bugfix_rerun_diff.md`).

**Additions (descriptive, no rule).**
1. `draw_median` fields for the (a) summaries. For P2 and P3 the plug-in point assumes exact offset estimates. Every
   draw adds estimation error, and a maximum over 18 noisy rates exceeds the plug-in, so the point can lie outside its
   CI. The draw median is the central value under estimation error.
2. `a_p0_fold_iqr_offsetq` and `a_p1_fold_iqr_offsetq`: the middle-half fold in `fairness.json`'s definition (rate at
   the 25th / 75th percentile offset). The pre-registered rate-percentile definition gives 18.7 for P0, against
   `fairness.json`'s 18.2. The two differ by construction.
3. Trade-off curve summaries (`curve_*`): the smallest g with a cut of 10-fold or more, the largest g changing at most
   10% of recorded false starts, and whether any g on the grid meets both bars.


### Note (2026-09-30, added after the false-start classification fix, commit 5a12182)

The upstream classification issue this file records as deviation 1 was fixed in `common.normalize_rt` (non-start DQs
noted "(not a false start)" are no longer false starts; the Fiore et al. RT 0.000 placeholders are missing values,
DNS rows not starts, DQ rows false starts without a measured RT). guardband.py was rerun on the corrected data at
integration: its correction now removes nothing (the literal and corrected readings coincide). **The verdict did not
change** (TRADE-OFF: PROTECTIVE BUT CHANGES MORE THAN 10% OF RECORDED FALSE STARTS, as in the pre-fix run with the
correction); the modelled rates moved slightly (changed values: `notes/bugfix_rerun_diff.md` covers the keys merged
before this integration; guard.* keys entered numbers.json only after the fix).
