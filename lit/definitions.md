# Operational definitions (adopt these repo-wide)

Part of the literature review. Version 1.1, 2026-09-29.

**Tags**
- **[V-FT]**: checked in the full text or primary document; a quote or location is given.
- **[V-ABS]**: checked in the abstract only.
- **[S]**: from a secondary source.
- **[U]**: unverified.

Citations are keyed to `refs.bib`.

---

## 1. Event timestamps in a start

All times are in seconds on a common clock for the race (a broadcast audio timeline, or the start-system clock).

| Symbol | Event | How to measure |
|---|---|---|
| `t_oym` | Onset of the starter's "On your marks" | Acoustic onset in audio |
| `t_set` | **Onset of the starter's "Set" command.** This is the *warning signal*. | The first sample where the command's energy rises above the local noise floor by a fixed criterion. In practice this is the onset of the /s/ frication, which carries energy mainly above about 4 kHz. Refine any ASR word timestamp to this acoustic onset. |
| `t_set_end` | Offset of "Set" | Acoustic offset |
| `t_steady_i` | Athlete *i* motionless in the set position | Video (manual or pose-based), or the pre-gun block-force trace settling (Seiko waveforms; see §5) |
| `t_steady_all` | `max_i t_steady_i`, the last athlete steady | Derived |
| `t_gun` | **Onset of the start signal** (electronic "gun"). This is the *imperative signal*. | Acoustic transient onset in audio, or 0 s on the start-system clock |
| `t_resp_i` | Athlete *i*'s response as registered by the start information system (SIS) | SIS only (not observable in video to 1 ms) |

## 2. Foreperiod (hold) variants

**Primary definition, used everywhere unless stated: `FP = t_gun − t_set` ("set-onset foreperiod").**

Why this one:
- **It is the standard foreperiod.** Warning-signal *onset* to imperative-signal *onset* is the foreperiod of the reaction-time literature (Niemi & Näätänen 1981; Bausenhart & Ulrich 2026 [V-FT]).
- **It is what the sprint and racing-sport studies measured.**
  - Otsuka et al. 2017 [V-FT]: "Onsets of the starter's set and gun signals were visually determined by sound wave information", from TV audio, at 10 ms resolution, in 83 races (WCH 2011/2013/2015, OG 2012). They report mean 1.780 s, SD 0.158 s.
  - Dalmaijer et al. 2015 [V-FT]: "the ready-start intervals were defined as the time between the onset of the referee saying 'Ready?' and the onset of the starting shot" (speed skating, Audacity).
  - Haugen et al. 2013: holds were computed "based on television recordings" of 267 heats [V-ABS]. The event definition, "time between 'set' and 'go'-signal", is [S], from Haugen & Buchheit 2016, a review by the same first author. **The Haugen 2013 full text was not accessible:** it is closed access, and no repository copy was found via Unpaywall, OpenAlex, Semantic Scholar, CORE or archive.org, and ResearchGate returned 403. So the exact event definition and measurement method are **[U]**.
- **It matches how starters define the hold.** Zemper's USATF starters monograph (2023 edition) [V-FT]: "The 'hold' is the length of time between the initiation of the 'Set' command and the start signal for races started out of blocks." The 2009 edition read "the firing of the gun".
- **It can be measured from audio alone**, so it is independent of broadcast audio–video sync.

Secondary variants (report on a validation subset or as sensitivity checks):

| Name | Definition | Why it matters |
|---|---|---|
| `FP_end` | `t_gun − t_set_end` | Some lab designs time from warning offset. It also removes variation in how long each starter takes to say "Set". |
| `HOLD_steady` ("steady hold") | `t_gun − t_steady_all` | The starter's actual decision interval. TR 16.3 [V-FT]: "Once the Starter is satisfied that all athletes are steady in the 'Set' position, the gun shall be fired." World Athletics commentary [V-FT]: "There is no rule that enables to determine the time that elapses between … the command 'Set' and the gun shot. The Starter shall let the athletes go once they are all motionless in the correct starting position." The set-onset foreperiod is therefore partly *endogenous*: it waits for the slowest settler. There is no numeric hold in any edition of the World Athletics Starting Guidelines (2012, 2018, Dec 2022 §6.2: "There is no perfect holding time in the set position"), per the sports search pass [V-FT by search pass]. The 1921 IAAF rules did have a minimum ("after a pause of at least 2 seconds"), per Zemper 2008 [S]. |
| `FP_own` ("individual steady hold") | `t_gun − t_steady_i` | The athlete-specific preparatory interval after the athlete reaches the set posture. |
| `RISE_i` | `t_steady_i − t_set` | Time athlete *i* takes to rise into and settle in the set position. Zemper 2023 [V-FT]: "Any hold of less than 1.5 seconds does not allow the athletes sufficient time to get into the set position." One panellist in the 2007 Starters Case Book (Pierre 2007, appended to the 2009 PAUSATF starters PDF) gives a start-to-end-of-motion range of ".25 to 1.25 seconds" [V-FT, practitioner opinion]. The Seiko patent's example shows the move into "ready" (set) around −1.4 s before the gun [V-FT]. |
| `CADENCE` | `t_set − t_oym` | A possible rhythm cue. Zemper: "there is no specified amount of time before the 'Set' command" [V-FT]. |
| `READY_seiko` | The `Ready Time` printed on Seiko start "waveform" images that are linked from World Athletics results pages (found by the data pipeline) | Seiko's English term "Ready" is its translation of the "Set" command (Japanese 用意; the Seiko patent uses "ready" for the set posture [V-FT]). On the image, a magenta marker sits at −`Ready Time` on the −2…+1 s axis, with the gun at 0. So `READY_seiko` is *probably* set → gun. **What triggers the marker (a starter or operator switch, or voice detection) is [U].** Treat it as a separate variable until it is validated against `FP` from broadcast audio. |

Practical rule: store all variants that are available per race, with a `fp_source` column (`audio_auto`, `audio_manual`, `seiko_ready`) and a `fp_confidence` column.

## 3. Reaction time

- **Official RT.** The time from the start signal to the athlete's response as registered by the certified SIS. It is shown to 0.001 s in results.
  - World Athletics defines RT only operationally. Technical Rules (Book C, C2.1, version dated 1 Jul 2026), TR 16.6 [V-FT, rulebook text]:

    > "When a World Athletics certified Start Information System is in use, the Starter and/or an assigned Recaller shall wear headphones in order to clearly hear the acoustic signal emitted when the System indicates a possible false start (i.e. when the reaction time is less than 0.100 second). As soon as the Starter and/or assigned Recaller hears the acoustic signal, and if the gun was fired, there shall be a recall and the Starter shall immediately examine the reaction times and other available information from the Start Information System in order to confirm which, if any, athlete(s) is/are responsible for the recall."

    Note to TR 16.6: the SIS evidence "shall be used as a resource by the relevant officials to assist in making a correct decision."
  - **The rulebook does not define the signal onset, the force threshold or the detection algorithm.** Those are properties of the certified vendor system.
  - TR 15: at World Rankings competitions, blocks "shall be linked to a World Athletics certified Start Information System" [V-FT].
  - Hardware context:
    - Sensors in the starting-block footplates.
    - Loudspeakers in or behind each block deliver the signal simultaneously (Seiko RM-200 catalogue [V-FT]).
  - The date of the "silent gun" is disputed:
    - Fiore et al. 2025 write that "silent gun" systems were introduced "in 2010", citing Tønnessen et al. 2013 [V-FT in Fiore].
    - Block loudspeakers were already in use at Atlanta 1996, where athletes reportedly still heard the gun through the air (Julin & Dapena 2003, as cited by Zemper [S]).
    - Treat the adoption date as [U].
- **What official RT is not.** It is *not* true movement onset. It is the time a vendor-specific detector fires on block force, so it includes detection latency:
  - *Seiko (patent JP2759769B2, 1995; the current firmware may differ)* [V-FT]:
    - 1 kHz sampling.
    - A comparator fires when the signal exceeds a ±25 ms moving average (delayed 50 ms) plus a 3 kg-equivalent margin, i.e. detection of new 3–25 Hz components.
    - This replaced a conventional absolute threshold (23 kg) whose delay "var[ied] greatly depending on athlete's kicking force".
    - Outputs between −0.5 s and +0.1 s relative to the gun count as a false start; outputs earlier than −0.5 s (the move into the set posture) are cancelled.
  - *Omega / Swiss Timing*:
    - Beijing 2008: a force threshold whose value Swiss Timing would not disclose ("this kind of information is not public"; Lipps et al. 2011) [V-FT].
    - Patent US 8,992,386 (priority June 2011): detection "no longer depends on a determined force threshold, but only on the variation in the force on the block" [V-FT/web, sports search pass].
    - ASC3 datasheet (2015): RTs recorded from 0.3 s before to 0.7 s after the gun; 1 ms precision; block speaker at 114 dB @ 1 m; threshold undisclosed [V-FT, sports search pass].
  - *FinishLynx*: accelerometer threshold of about 1.5 g (US 6,002,336) [V-FT/web].
  - *Force-threshold systems generally*: Pain & Hibbs 2007 [V-FT, sports search pass]: "Using a simple threshold of force detection increased the measure of reaction time by 26 ms on average." Detection criteria are proprietary, differ by vendor, and have changed over time (review.md §4). **Always model competition (vendor or detector regime) as a fixed effect.**
- **Other RT notions** (do not mix them with official RT):
  - **Premotor RT**: EMG onset.
  - **Force-onset RT**: the first detectable force change by an offline algorithm, as in Otsuka et al. 2017's baseline mean ± adjusted SD method [V-FT].
  - **Joint RT**: onset of the moment at a joint (Otsuka et al. 2017).
  - Milloz et al. 2021 note that arm-force onset precedes foot-force onset [V-ABS].

## 4. Response classes

| Term | Operational definition in this repo |
|---|---|
| Legal start | Official RT ≥ 0.100 s and no pre-gun movement ruled by the starter or referee. |
| False start (rule) | Two routes: the TR 16.7 commencement definition, or an SIS RT < 0.100 s (TR 16.6), with the starter confirming.<br><br>TR 16.7 [V-FT]: an athlete "shall not commence their start until after receiving the report of the gun". Commencement from a crouch start is "any motion by an athlete that includes or results in one or both feet losing contact with the foot plate(s) of the starting blocks or one or both hands losing contact with the ground". A movement begun before the gun and continued into the start is also a false start.<br><br>TR 16.8 [V-FT]: "Except in Combined Events, any athlete responsible for a false start shall be disqualified by the Starter." Zero tolerance has applied since 1 Jan 2010 (IAAF "Comparison of false starts" quotes the 2010 Rule 162.7 [V-FT]).<br><br>Combined events still allow one false start per race: TR 39.8.3 [V-FT, rulebook text]. |
| Restart | Any start after a recalled start in the same race. Flag with `attempt ≥ 2`, which Seiko waveforms print as `Attempt : 00N` [V-FT, image]. |
| Aborted start ("catch-trial analogue") | A start stopped by the starter *before* the gun, e.g. "stand up" under TR 16.5 or a recall without a false start (green card). Functionally a catch trial, because the expected gun never comes. It affects the hazard the athletes experience (review.md §5.2, §5.11). Record it if visible in video; it is **not** in results pages. |
| Anticipation (cognitive science) | A response initiated before the imperative stimulus could have been processed, i.e. timed from the warning signal. By convention in RT research it is operationalized as RT < 100 ms (e.g., PVT "false starts"). See review.md for sources. |
| Legitimate sub-0.100 s response | A gun-triggered reaction that registers < 0.100 s. It is unobservable directly and can only be estimated from a distributional model fitted to legal RTs (Fiore et al. 2025 [V-FT]; Brosnan et al. 2017). These are the *false positives* of the rule. |
| DQ-RT | The RT printed for a disqualified start. Fiore et al. include positive DQ RTs to estimate the left tail and exclude negative ones [V-FT]. |

## 5. Settling and steadiness (for candidate C9)

- **Settle time `t_steady_i` from force traces.** The last time before the gun that athlete *i*'s block-force trace leaves a noise band. The band is estimated from the final 300 ms before the gun (a design constant that can be changed). Traces come from Seiko waveform images (digitized).
- **Pre-gun steadiness.** The SD of the force trace in successive 100 ms windows after `t_steady_i`. Use it to test whether steadiness decays over long holds, a belief among starters that "2.2 – 2.5 seconds is on the back side of the concentration curve" (Starters Case Book, Pierre 2007) [V-FT, practitioner opinion only].

## 6. Race and session identifiers

- **`race_id`** = `{comp}{year}-{event}-{sex}-{round}-{heat}` (brief). A restart keeps the `race_id` and adds `attempt`.
- **`session_id`** = `{comp}{year}-{event}-{sex}-{round}`. This is the set of heats run consecutively, usually by the same start team. It is the operational proxy for "starter" because starter identity is not published. Zemper notes differences "in voice and rhythm between starters" and advises keeping one starter per event across rounds [V-FT].
- **`starter_id`**: only if it can be identified reliably (e.g., official lists or voice clustering); otherwise leave null. Do not infer it silently.
- **`session_order`**: the heat's position within its session, from start times in results or waveform timestamps.
- **`first_start_of_day`**: a flag for the first start of the day.
- **`after_false_start`**: whether a false start occurred earlier in the session.

These three are for testing a practitioner claim (Zemper 2023, verbatim [V-FT]): "For any starter, the fastest starts (i.e., the shortest hold times) tend to be the first start of the day and any start after a false start." That is a testable statement that holds are state-dependent, i.e. *endogenous*.

## 7. Temporal-expectation quantities (for C3 and C6)

Let *f* be the foreperiod density that athletes plausibly condition on: the championship-wide or session-specific empirical distribution of `FP`, estimated with a kernel density; *F* is its CDF.

- **Objective hazard**: `h(t) = f(t) / (1 − F(t))`.
- **Subjective (blurred) hazard**: the hazard computed from `f` convolved with a Gaussian of SD `φ·t`, where `φ` is a Weber fraction (grid 0.1–0.3). This follows the scalar-timing formulation of Janssen & Shadlen 2005, who used φ = 0.26 [V-FT, submitted version]. Grabenhorst et al. 2019/2026 used φ = 0.21 [V-FT]. Grabenhorst et al. 2026 found no Weber growth of RT spread [V-FT], so treat φ as a fitted parameter.
- **Abort-adjusted hazard**: with an abort ("catch") probability `c`, `h_c(t) = (1 − c)·f(t) / (1 − (1 − c)·F(t))`. This is the standard catch-trial correction (Grabenhorst 2019 [V-FT]: the CDF ceiling is 1 − P(catch)).
- **Blurred PDF**: `f` convolved as above, not divided by the survivor function. This is the Grabenhorst et al. 2019/2021 account; Bausenhart & Ulrich 2026 describe it as "the reciprocal event probability density function—mathematically simpler and more stable than hazard rate" [V-FT in Bausenhart & Ulrich].
- **Aging vs non-aging distributions.**
  - Aging: hazard rises with elapsed time (e.g., uniform or Gaussian holds).
  - Non-aging: constant hazard (exponential, usually with a floor).
  - Bausenhart & Ulrich 2026 [V-FT]: "using uneven or even non-aging FP distributions—can strongly reduce or even abolish the variable FP effect."
- **Sequential terms**:
  - `FP_prev_session`: the previous race's `FP` in the same session.
  - `FP_prev_own`: the `FP` of athlete *i*'s own previous round.

## 8. Measurement-error reporting (for C2)

For any automated foreperiod, report against a manual consensus reference:
- bias and 95% limits of agreement (Bland–Altman);
- ICC (two-way, absolute agreement);
- detection rate;
- a per-race `fp_confidence`.

Treat `FP` as measured with error in models (errors-in-variables or simulation extrapolation) whenever the limits of agreement are more than about 10% of the SD of the foreperiod across races (≈16 ms if the SD is ≈0.16 s). This threshold is a design constant.
