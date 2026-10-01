# Audio foreperiod measurement tool (`analysis/measure/`)

Measures the sprint-start **foreperiod** (the starter's "Set" command to the gun) from the **audio track** of
broadcast race recordings. It is an audio tool: it never looks at video frames. Video platforms are only the
source of the audio, and only derived timings plus source URLs are published (audio stays in `data/video/`,
which is gitignored and never redistributed).

## Status (generated counts are in `numbers.json`; see `real_foreperiods_*`)

`data/derived/foreperiods.csv` holds one row per start attempt: valid starts plus recalled attempts (false
starts). Every row carries a review status in `manual_check`:
- `agree` / `override`: blind manual reading;
- `visual_ok` / `visual_corrected`: non-blind screening of the automated marks;
- `unidentifiable` / `visual_unidentifiable`: the "Set" onset cannot be identified, for example because of
  commentary over the command. These rows have a blank foreperiod.

Coverage by championship and the recalled attempts are listed in `numbers.json`. The coverage is
opportunistic:
- WCH2025: full-round compilations for all four events.
- WCH2019: semi-finals and finals.
- WCH2022 and WCH2023: finals plus the heats covered by single-race clips.
- OG2020: official replays of both 100 m semi-final rounds, the 110 mH semi-finals and the men's 100 m final
  (unidentifiable).
- OG2024: SportsMax heat and semi-final clips and official finals. Most SportsMax clips have commentary over
  the command.

## What it measures, and what it does not

Per start attempt (one race can have several attempts when a start is recalled):

| output | definition |
|---|---|
| `gun_s` | acoustic onset of the starting gun (electronic gun sound from the start-line loudspeakers) in the recording |
| `set_onset_s` | acoustic onset of the spoken "Set" command, i.e. the start of the /s/ frication |
| `set_offset_s` | end of voicing of "Set" (secondary; imprecise in reverberant stadiums, see validation) |
| `foreperiod_s` | `gun_s - set_onset_s` (**primary definition: command onset to gun**) |
| `foreperiod_offset_s` | `gun_s - set_offset_s` (variant: end of command to gun) |
| `uncertainty_s` | 1-sigma-like uncertainty of `foreperiod_s` (calibration + estimator spread, below) |
| `qc_flag` | `ok` or a `;`-separated list of flags (below) |

It does **not** measure: reaction times (those come from official results), the "On your marks" to "Set"
interval, athlete movement, or anything from video frames. It does not identify *which* race a recording shows;
that comes from curated matching (titles, commentary names versus start lists, and Seiko attempt numbers).
It assumes that the command and the gun reach the broadcast mix through the same path, so the relative latency
between them is about zero. Both are played through the start-line loudspeakers, but a broadcast could take the
starter's voice and the gun through different chains. This assumption is **not verified** (see Limitations).

Rule context (verified in the WA Technical Rules, C2.1, in force from 1 Nov 2019, amended 31 Jan 2020, TR 16.2
Note; source: https://worldathletics.org/download/download?filename=1a53ca10-7f30-46e4-83fe-e7ff5fda2c60.pdf&urlslug=C2.1,
retrieved 2026-09-28): at World Championships and Olympic Games (International Competition paragraph 1.1),
**starter commands are given in English only**. So "Set" is English in all in-scope competitions, including
Tokyo 2020 and Tokyo 2025. The same rule text states that there is no fixed interval between "Set" and the gun:
the starter fires once all athletes are steady.

## Pipeline

`fpmeasure.py` holds the library, and every script listed below has an explicit `--out`.

0. **Discovery and download.**
   - `discover_search.py` snapshots YouTube search results (JSONL with query and retrieval time), plus a flat
     listing of the World Athletics channel (`discovery/wa_channel_videos*.tsv`).
   - `download_audio.py` fetches **audio only** (`bestaudio`), strictly one file at a time, rate-limited with
     `--limit-rate 800K`, with optional `--section`.
1. **Coarse scan** (`band_env_db`, `gun_candidates`). The audio is decoded to 24 kHz mono and reduced to six
   band-power envelopes (150-400, 400-800, 800-1600, 1600-3200, 3200-6400, 6400-11000 Hz) at 5 ms frames.
   - A **gun candidate** is a frame where at least 3 bands rise by 8 dB or more within 60 ms, relative to the
     maximum of the preceding 300 ms. The voting bands must include at least one low band (< 1.6 kHz) and one
     high band (> 3.2 kHz), and the mean rise must be at least 6 dB.
   - Non-maximum suppression uses a 0.8 s radius.
2. **Context features and start score** (`candidate_features`, `start_score`). Scores are compared *within a
   recording*, because absolute levels depend on the broadcast mix (the Doha 2019 guns rise about 15 dB, the
   Tokyo 2025 guns about 35 dB). The score is:
   `0.6*gun_jump + 0.3*tilt + 1.0*race_loud + 0.2*hf_sustain - 1.5*max(hold_excess-5,0) + 0.3*set_snr`,
   with -15 when there is no speech burst and -10 when the burst lies outside 0.9-4.2 s before the gun.
   - For single-race videos the top candidate is used.
   - For multi-race compilations, starts are curated from the ranked candidates, the commentary transcript
     (faster-whisper `base.en`), athlete names versus start lists, and Seiko attempt numbers
     (`race_starts_curated.csv`).
3. **"Set" burst selection** (`choose_set_burst`, `extend_set_burst`).
   - Speech bursts are segments where the 400-3200 Hz level exceeds the local floor + 8 dB for 100 ms or more
     (bursts closer than 40 ms are merged).
   - Among bursts with SNR >= 12 dB, the one overlapping a whisper "set"-like word (`base.en`, 7 s clip, prompt
     "On your marks. Set.") is chosen. Otherwise the last burst is chosen, unless that burst is weak
     (< 15 dB) and the burst before it, within 1.2 s, is at least 8 dB louder (a noise in the hold).
   - A burst split in two by the /s/-vowel or /t/ gap is re-joined (gap < 150 ms, joined length <= 0.8 s).
4. **Refinement at sample level** (`refine_gun`, `refine_set`).
   - *Gun*: the median of three estimators, namely threshold-backtrack onsets of 2 ms RMS envelopes in the
     2-10 kHz and 0.3-10 kHz bands, and an AIC change point (Maeda 1985) on the 2-10 kHz waveform.
   - *Set onset*: the median of the threshold-backtrack estimators (thresholds of 6 and 10 dB, in the 3-10 kHz
     /s/ band and the 0.3-10 kHz band).
     - The method walks back from the burst peak to the last run of 20 ms or more below floor + max(3 dB, 2 SD).
     - The floor is the larger of the 10th percentile of the preceding 1.5 s and the local median of
       [-0.45, -0.20] s before the burst. This robust floor handles intermittent commentary.
     - The latency of the centred RMS window is corrected by +w/2.
     - An AIC estimate is kept as a diagnostic, and half the estimator range is reported as `set_spread_s`.
   - *Set offset*: the 300-3400 Hz 10 ms envelope; after the word's peak, the first point from which it stays
     15 dB or more below that peak for 50 ms (fallback: 10 dB).
5. **QC and uncertainty** (`measure`, `uncertainty`). See the tables below.
6. **Outputs.**
   - `measure_starts.py` produces `results/starts_measured.csv`, with one row per curated start and all
     estimators.
   - `build_foreperiods.py` produces `data/derived/foreperiods.csv`.
   - `validate_*.py` produce `results/*.json`, and `make_numbers.py` produces `numbers.json`.

### Why these discriminators

- **Low-and-high band voting plus a 60 ms window.** Loudspeaker guns are broadband, but their bands can rise
  tens of ms apart. At Doha 2019 the high band rose about 30-50 ms before the mid bands, and a frame-synchronous
  rule missed every gun. Requiring a low band rejects /s/ and /t/ onsets, which rise only in the high bands.
- **Tilt.** Guns rise 30-50 dB at 1.6-11 kHz but only 5-15 dB at 150-400 Hz. Commentary onsets after a pause
  rise strongly at low frequencies. This separated the commentary confounders seen in the Tokyo 2025
  compilation.
- **race_loud** (median level over the 1-9 s after the gun minus the 12 s before it). A real start is followed
  by about 10 s of crowd and commentary. This was the only feature that separated the true guns in the Doha
  2019 semi-final broadcast from PA announcements. It is **low for recalled starts**, which are therefore
  curated explicitly (Seiko attempt numbers, commentary).
- **hold_excess.** The hold between "Set" and the gun is normally quiet, because athletes are steady and the
  crowd is hushed.
- **/s/-band onset.** "Set" always begins with the voiceless fricative /s/ (energy at 3-10 kHz). Its onset is
  the physical start of the command. Voicing starts 80-200 ms later, so a speech-band detector alone would be
  biased late.

### QC flags

| flag | meaning |
|---|---|
| `ok` | no flag raised |
| `whisper_not_run` / `no_whisper_set` | no whisper "set"-like word supported the chosen burst, so the choice is acoustic only |
| `low_snr_set` | "Set" peak less than 12 dB above the local floor |
| `low_snr_gun` | gun rise less than 12 dB (2-10 kHz) |
| `fp_out_of_range` | foreperiod outside 0.9-3.8 s: probably the wrong burst or candidate |
| `set_estimators_disagree` | onset estimators (including AIC) span more than 40 ms, typically a gradual /s/ or overlapping sound |
| `no_offset` | voicing end not found before the gun |
| `speech_before_set` | another speech burst ends within 350 ms before the chosen "Set" burst (commentary may mask or merge with the onset) |
| `speech_in_hold` | a speech-like burst lies between "Set" and the gun |
| `weak_s_onset` | no /s/ frication above the noise (HF SNR < 10 dB with speech-band SNR >= 15 dB) or none visible on review: onset = vowel onset, biased late by the /s/ duration (~0.1-0.2 s); +0.10 s uncertainty |
| `set_not_identifiable` | the reviewer could not identify the "Set" onset (commentary over the command, heavy noise): foreperiod left blank |
| `measurement_failed` | no gun candidate near the curated time, or refinement failed |

### Uncertainty

`uncertainty_s = sqrt(u_set(SNR)^2 + set_spread^2 + u_gun^2 + gun_spread^2)`, where `u_set` is the 68th
percentile of |set-onset error| in the measured set-SNR bin (< 12, 12-20, 20-30 and > 30 dB). The percentiles
come from non-gross **synthetic** trials (`calibration_synthetic.json`, written by
`summarize_benchmark.py --calibration-only`).
- The < 12 dB bin has fewer than 5 non-gross synthetic trials, so it keeps a conservative 60 ms default.
- `set_spread` and `gun_spread` are half the disagreement between estimators.
- `set_spread` is included because it captures ambiguity that the SNR alone does not.
- Manual overrides use the reading uncertainty combined with 5 ms.

Held-out validation (below) shows that the calibration is optimistic for starts preceded by commentary. Treat
`uncertainty_s` as a lower bound when `qc_flag` is not `ok`.

## Validation

Three independent checks.
- **(a)** A **synthetic** benchmark with known truth. It is **simulated audio**, and it is labelled as such
  everywhere.
- **(b)** Blind manual reading of real broadcasts (`annotation_sheets.py` renders sheets **without** detector
  marks or reference values; the readings are in `manual_annotations.csv`).
- **(c)** Comparison with the official Seiko "Ready Time" printed on WA start waveforms
  (`data/derived/rt_waveform.csv`, owned by the data pipeline).

Protocol caveats:
- The manual reader is an AI model (not a human), reading 10 ms-gridded envelope plots, which introduces ±5-20 ms of reading
  uncertainty per onset (recorded per row).
- For the 10 Tokyo 2025 men's 100 m starts, the reader had seen Seiko values before annotating, so blinding
  there is partial.
- **Dev split.** The first 22 annotated starts (sheets S01-S24) were also used to fix detector bugs, so the
  "dev" agreement is **in-sample**.
- **Held-out split.** After the detector was frozen, 12 further starts (sheets H01-H12) were drawn with a
  seeded random sample (seed 20260929) from the 30 unchecked Tokyo 2025 starts. They were rendered blind and
  read before any comparison, and are scored separately (`annotation_key_heldout.csv` maps sheets to races).
- **Gun reading convention.** For two-step or staggered guns, the reader marks the *first* arrival.
- **Non-blind visual screening.** Every remaining automated measurement (starts without a blind reading) was
  screened for gross errors on compact contact sheets (`contact_sheets.py`, `figures/contact/`), with the
  automated marks drawn. Verdicts (ok / corrected / unidentifiable) are in `verification_visual.csv`.
- **Scope of that screening.** It is **not** an accuracy measurement: it only removes wrong-event errors and
  commentary-masked starts. Accuracy claims rest on the blind splits and the synthetic benchmark.
- **Weak /s/.** Where no /s/ is visible (the onset is the vowel onset), 0.10 s is added in quadrature to the
  uncertainty and `weak_s_onset` is set.

**Synthetic benchmark design** (`benchmark_synthetic.py`, seed 20260929; everything is SIMULATED except the
real backgrounds and the SAPI voices):
- Clips are 12 s long. "Set" comes from Windows SAPI TTS: 4 voices (David and Zira en-US, Helena es-ES and
  Hortense fr-FR, i.e. accented English), 3 spellings and 3 rates, resampled by 0.92/1.00/1.08.
- The speech is band-limited like a loudspeaker and reverberated (RT60 0.3-1.2 s).
- The foreperiod is drawn from U(1.2, 2.7) s. The gun is a synthetic noise burst (decay 15-60 ms, 15-35 dB
  above the background). A crowd surge follows the gun.
- Each clip goes through an Opus or AAC 128 kb/s round trip.
- Four backgrounds are used:
  - realistic: *hold* (real set-to-gun hold audio from the dev races, stitched) and *pink* (stationary noise);
  - stress: *race* (race-period crowd and commentary) and *commentary* (pre-race introductions).
- "Set" SNR is set to +20, +10, +5, 0 or -5 dB, with 12 trials per cell (240 trials).
- Truth is the dry word's -40 dB onset and end, and the first sample of the gun.
- A trial is a gross error when there is no measurement, the gun error exceeds 50 ms, or the set-onset error
  exceeds 250 ms.

The real broadcasts compared here have measured set SNR of mostly 30-48 dB, which is typical of the synthetic
+20 dB condition.

<!-- BEGIN GENERATED RESULTS (render_readme_results.py; do not edit by hand) -->

### (a) Synthetic benchmark (SIMULATED audio; known ground truth)

SYNTHETIC benchmark (simulated start clips; real broadcast backgrounds or pink noise; SAPI TTS 'Set'; synthetic gun, reverb, crowd surge; Opus/AAC round trip). Errors = detected - truth.

Headline (SIMULATED): realistic backgrounds (hold, pink) at SNR >= +10 dB: n = 48, gross errors 6%, foreperiod bias -5.61 ms, MAE 26.76 ms, within +-20 ms 71%, within +-40 ms 79%. All realistic trials: gross 25%; stress backgrounds (race crowd, commentary): gross 52%. Gun MAE (non-gross) 0.54 ms. QC: 23% of trials pass all flags; gross-error rate 2% when qc_flag is ok vs 50% when flagged.

| condition | n | detected | gross errors | fp bias (ms) | fp MAE (ms) | within +-20 ms | within +-40 ms |
|---|---|---|---|---|---|---|---|
| commentary, SNR -5 dB | 12 | 92% | 92% | 114.6 | 114.6 | 0% | 0% |
| commentary, SNR +0 dB | 12 | 92% | 75% | 55.7 | 55.7 | 8% | 17% |
| commentary, SNR +5 dB | 12 | 100% | 50% | -3.1 | 69.8 | 17% | 17% |
| commentary, SNR +10 dB | 12 | 92% | 42% | -70.4 | 71.0 | 25% | 33% |
| commentary, SNR +20 dB | 12 | 83% | 67% | 8.5 | 75.5 | 17% | 17% |
| hold, SNR -5 dB | 12 | 92% | 75% | 62.5 | 65.3 | 8% | 8% |
| hold, SNR +0 dB | 12 | 92% | 50% | -113.0 | 113.0 | 0% | 8% |
| hold, SNR +5 dB | 12 | 92% | 8% | -27.0 | 71.6 | 25% | 25% |
| hold, SNR +10 dB | 12 | 100% | 17% | -27.8 | 67.4 | 17% | 42% |
| hold, SNR +20 dB | 12 | 100% | 8% | 15.9 | 30.5 | 75% | 75% |
| pink, SNR -5 dB | 12 | 67% | 33% | -150.2 | 150.2 | 0% | 0% |
| pink, SNR +0 dB | 12 | 58% | 42% | -95.0 | 95.0 | 0% | 17% |
| pink, SNR +5 dB | 12 | 92% | 17% | -59.2 | 59.2 | 33% | 58% |
| pink, SNR +10 dB | 12 | 100% | 0% | -12.4 | 12.4 | 92% | 100% |
| pink, SNR +20 dB | 12 | 100% | 0% | 0.0 | 3.8 | 100% | 100% |
| race, SNR -5 dB | 12 | 75% | 67% | -97.3 | 97.3 | 0% | 8% |
| race, SNR +0 dB | 12 | 92% | 50% | -5.0 | 49.5 | 17% | 25% |
| race, SNR +5 dB | 12 | 83% | 42% | -45.4 | 76.2 | 8% | 17% |
| race, SNR +10 dB | 12 | 92% | 8% | -40.6 | 54.6 | 25% | 33% |
| race, SNR +20 dB | 12 | 100% | 33% | -0.8 | 11.4 | 50% | 67% |

### (b) Real broadcasts: automated vs blind manual reading, DEV split (in-sample)

Starts matched: 22; clean "Set": 18. Error = automated - manual.

| quantity | n | bias (ms) | MAE (ms) | max abs (ms) | within +-10 ms | within +-20 ms | within +-40 ms |
|---|---|---|---|---|---|---|---|
| gun onset (all matched starts) | 22 | 0.3 | 0.7 | 2.9 | 100% | 100% | 100% |
| set onset (clean) | 18 | -0.2 | 18.3 | 93.0 | 44% | 61% | 89% |
| foreperiod, onset-based (clean) | 18 | 0.6 | 18.7 | 93.6 | 44% | 61% | 89% |
| set offset vs manual end of voicing (clean) | 18 | 30.9 | 60.6 | 168.0 | 17% | 22% | 44% |

### (b) Real broadcasts: automated vs blind manual reading, HELD-OUT split (detector frozen)

Starts matched: 12; clean "Set": 10. Error = automated - manual.

| quantity | n | bias (ms) | MAE (ms) | max abs (ms) | within +-10 ms | within +-20 ms | within +-40 ms |
|---|---|---|---|---|---|---|---|
| gun onset (all matched starts) | 12 | 4.2 | 6.2 | 22.4 | 75% | 83% | 100% |
| set onset (clean) | 10 | -15.5 | 33.7 | 136.0 | 40% | 60% | 70% |
| foreperiod, onset-based (clean) | 10 | 18.5 | 36.2 | 126.6 | 20% | 50% | 70% |
| set offset vs manual end of voicing (clean) | 10 | -21.8 | 62.2 | 256.0 | 10% | 10% | 60% |

### (c) Real broadcasts vs official Seiko Ready Time

Valid (final) start attempts with a validated Ready Time and a clean "Set": **n = 22** of 28 annotated. d = broadcast foreperiod - Ready Time.

| broadcast reference point | n | bias (ms) | SD (ms) | MAE (ms) | min (ms) | max (ms) | within +-20 ms | within +-40 ms |
|---|---|---|---|---|---|---|---|---|
| set onset (manual) | 22 | 523 | 171 | 523 | 202 | 808 | 0% | 0% |
| end of voicing (manual) | 22 | 163 | 160 | 196 | -158 | 405 | 0% | 5% |
| end of word incl. /t/ (manual) | 22 | 121 | 170 | 184 | -212 | 385 | 5% | 5% |
| set onset (automated) | 22 | 524 | 166 | 524 | 186 | 828 | 0% | 0% |
| set offset (automated) | 22 | 142 | 201 | 200 | -317 | 441 | 5% | 5% |

**Final dataset** (all reviewed valid starts in foreperiods.csv with a validated Ready Time, n = 40): onset foreperiod - Ready = 557 ms mean (SD 225 ms, range 186 to 1293 ms; within +-40 ms: 0%). Within-championship residual SD 183 ms, MAD 100 ms, 50% of residuals within 100 ms. r(Ready, onset foreperiod) = 0.6823 (95% CI [0.4709, 0.8196]).

| championship (final dataset) | n | onset - Ready: mean (ms) | SD (ms) | min (ms) | max (ms) |
|---|---|---|---|---|---|
| WCH2022 | 6 | 339 | 99 | 186 | 453 |
| WCH2023 | 6 | 381 | 78 | 292 | 501 |
| WCH2025 | 28 | 641 | 213 | 367 | 1293 |

| championship (blind manual subset) | n | onset - Ready: mean (ms) | SD (ms) | voicing end - Ready: mean (ms) |
|---|---|---|---|---|
| WCH2022 | 3 | 274 | 100 | -54 |
| WCH2023 | 4 | 385 | 93 | 8 |
| WCH2025 | 15 | 610 | 117 | 247 |

Within-championship SD of (onset - Ready) after removing each championship's mean: 107 ms (voicing end: 96 ms). Pearson r(Ready Time, onset foreperiod) = 0.7448 (95% CI [0.4712, 0.8877]), OLS slope 0.6089.

Excluded (listed, not dropped silently):
- WCH2025-100m-M-R1-H1 attempt 1: Set command not identifiable in broadcast audio: commentary runs over the command; Set not identifiable (HF burst 181.37 may be the /s/ but overlaps speech)
- WCH2025-100m-M-R1-H3 attempt 1: Set command not identifiable in broadcast audio: two fricative+vowel groups (920.40 and 920.55); which one is Set is ambiguous
- WCH2025-100m-M-R1-H7 attempt 1: Set command not identifiable in broadcast audio: harmonic burst 2211.50-2211.76 without /s/ onset; commentary nearby; Set ambiguous
- WCH2025-100m-W-R1-H5 attempt 1: Set command not identifiable in broadcast audio: commentary overlaps the command; Set not identifiable; gun two-step (1135.240 first arrival, main 1135.261)
- WCH2025-100m-W-SF-H1 attempt 2: no validated Seiko Ready Time
- WCH2025-100mH-W-R1-H1 attempt 1: Set command not identifiable in broadcast audio: continuous commentary; Set not identifiable
<!-- END GENERATED RESULTS -->

### What the Seiko "Ready Time" is (interpretation of check c)

On every compared race, Ready Time is shorter than the acoustic onset-to-gun interval, and it does not match
the onset within 40 ms on any race. The Seiko "ready" mark (gun minus Ready Time) falls **near the end of the
spoken command**:
- inside the vowel at Oregon 2022;
- at the end of voicing at Budapest 2023;
- 0.1-0.4 s after voicing ends at Tokyo 2025.

The offset is championship-specific, with smaller scatter within a championship. This pattern fits a mark
triggered at or after the end of the command (by the starter, or by a voice or threshold mechanism). It does
not fit a mark at the command onset. The mechanism is **not verified**: no Seiko documentation was found, and
the relative broadcast latency between voice and gun is unknown.

Practical consequences:
1. Ready Time is not the onset-based foreperiod.
2. Across championships it carries an offset of several hundred ms.
3. Within a championship it usually tracks the broadcast foreperiod: among automated measurements with
   `qc_flag == ok`, the OLS slope of Ready Time on the onset foreperiod is close to 1 (`numbers.json`:
   `real_seiko_autoqcok_ols_slope`, `real_seiko_autoqcok_corr_r`). On that subset Ready Time behaves like the
   onset foreperiod minus a championship-specific constant plus about 0.1 s of scatter.
   Over all reviewed starts the slope is lower (`real_seiko_final_ols_slope`), because of the Ready-Time
   outliers described next.

For analysis, the definitions should not be mixed across championships without a championship-level offset.

**Ready Time is not always locked to the spoken command.** In the final dataset (all reviewed valid starts with
a validated Ready Time, `final_dataset_valid` in `results/seiko_validation.json`), the WCH2025 residuals have a
long right tail:
- WCH2025-100m-W-R1-H6: broadcast onset foreperiod 2.50 s vs Ready Time 1.21 s;
- WCH2025-100mH-W-R1-H5: 2.57 s vs 1.35 s.

Both were re-checked on zoom sheets. The race assignment is confirmed by the commentary naming the start-list
athletes, and each start has a clear /s/ onset about 2.5 s before the gun. Nothing is audible where the Ready
mark would fall, about 1.2 s later.

In addition, `rt_waveform.csv` lists Ready Time = 0.103 s for WCH2025-100m-W-R1-H1. This is not physically a
foreperiod.

So Ready Time behaves like a device-side mark that usually follows the end of the command by a
championship-specific lag, but not always. It should be validated, or robustly filtered, before being used as
the foreperiod. The within-championship spread is reported both as SD and as MAD for this reason.

## Known failure modes

- **Commentary over the command.** When a commentator speaks through "Set", the onset is either not
  identifiable (these starts are marked not clean and excluded from timing claims) or merges with speech
  (`speech_before_set`).
- **Gradual /s/ onsets.** Some starters fade the /s/ in over 50-130 ms. The onset then depends on the threshold
  (`set_estimators_disagree`), and the manual reading uncertainty is ±15-20 ms.
- **Reverberation.** Offsets are imprecise (MAE of about 60 ms versus manual reading), so `foreperiod_offset_s`
  is secondary.
- **Recalled starts.** A recalled start has no crowd surge after it (low `race_loud`) and is missed by
  ranking alone, so attempts are curated.
- **Missed starts.** The WCH2022 men's 100 m final upload: the two top-ranked candidates were commentary.
  The start is still unmeasured.
- **Officiating videos.** WA "officiating video" MP4s (linked for 7 races) have 8 audio channels, all digital
  silence (checked on WCH2025-100mH-W-SF-H3), so they cannot serve as an audio reference.
- **Two-step or staggered guns.** Seen in the Tokyo 2025 women's sessions. A first arrival 15-25 ms before the
  main broadband step (possibly the nearest start-line loudspeaker) is picked by the reader, while the AIC
  estimator picks the main step. This gives gun errors of 15-22 ms on the held-out split.
- **Held-out set-onset failures.** Three kinds were seen:
  - commentary ending just before "Set", where the backward walk entered the commentary (-136 ms);
  - a weak "Set" with no visible /s/ (-89 ms against a voiced-onset reading);
  - a weak /s/, where the vowel onset was picked (+51 ms).
  These cases carry `speech_before_set`, `set_estimators_disagree` or `no_whisper_set` flags. In
  `foreperiods.csv`, manual readings override automated values that differ from them by more than 40 ms.
- **Commentary-heavy uploads.** SportsMax Paris 2024 clips have commentary over most commands (unidentifiable).
  The official Tokyo 2020 men's 100 m final replay has tonal noise that masks the command.
- **Weak /s/ in some uploads.** Olympic-channel replays have little energy above 3 kHz, so the /s/ is often
  invisible (`weak_s_onset`).
- **Missed races.** In the Tokyo 2025 women's 100 m compilation, R1-H4 appears only as a replay without its
  start, and SF-H3 is absent from the upload.

## Reproduce

All commands run from the repository root with `.venv/Scripts/python.exe`. The authoritative list, with exact
arguments, is `producers.json`.

```
# 0) discovery snapshots (network; results change over time, so the snapshots are the record)
analysis/measure/parse_channel_listing.py --raw analysis/measure/discovery/wa_channel_videos.tsv --out analysis/measure/discovery/wa_channel_videos_clean.tsv
analysis/measure/discover_search.py --races data/derived/races.csv --comps OG2020 OG2024 --per-heat --n 12 --out analysis/measure/discovery/search_OG_<date>.jsonl
# 1) audio (never redistributed): one file at a time, rate-limited to 800K
analysis/measure/download_audio.py --ids <video ids listed in data/derived/video_sources.csv>
# 2) whole-file transcripts (base.en, offline) and start proposals for compilations
analysis/measure/transcribe.py data/video/audio/<id>.webm base.en
analysis/measure/propose_starts.py --video-id <id> --group WCH2025-100m-W --audio-dir data/video/audio --transcript analysis/measure/work/transcripts/<id>.base.en.json --athletes data/derived/rt_athletes.csv --races data/derived/races.csv --extra 4 --out analysis/measure/proposals/<id>.csv
#    -> curated into analysis/measure/race_starts_curated.csv (race, attempt, gun-time hint, evidence)
# 3) measure curated starts
analysis/measure/measure_starts.py --curated analysis/measure/race_starts_curated.csv --audio-dir data/video/audio --whisper base.en --out analysis/measure/results/starts_measured.csv
# 4) blind annotation sheets (read by the single blind reader; readings in manual_annotations.csv)
analysis/measure/annotation_sheets.py --hints analysis/measure/annotation_hints_heldout.csv --audio-dir data/video/audio --outdir analysis/measure/figures/annotation_heldout
# 5) synthetic benchmark (SIMULATED; TTS from tts_sapi.ps1 on Windows)
powershell -ExecutionPolicy Bypass -File analysis/measure/tts_sapi.ps1 -OutDir analysis/measure/work/tts
analysis/measure/make_noise_manifest.py --curated analysis/measure/race_starts_curated.csv --manual analysis/measure/manual_annotations.csv --split dev --out analysis/measure/benchmark_noise_manifest.csv
analysis/measure/benchmark_synthetic.py --tts-dir analysis/measure/work/tts --noise-manifest analysis/measure/benchmark_noise_manifest.csv --audio-dir data/video/audio --snrs 20 10 5 0 -5 --noise-types hold pink race commentary --n-per-cell 12 --seed 20260929 --whisper base.en --jobs 6 --workdir analysis/measure/work/bench --out analysis/measure/results/benchmark_synthetic_trials.csv
analysis/measure/summarize_benchmark.py --trials analysis/measure/results/benchmark_synthetic_trials.csv --out analysis/measure/results/benchmark_synthetic_summary.json
analysis/measure/summarize_benchmark.py --trials analysis/measure/results/benchmark_synthetic_trials.csv --calibration-only --out analysis/measure/calibration_synthetic.json
# 6) validations, derived tables, numbers, README results
analysis/measure/validate_manual.py --manual analysis/measure/manual_annotations.csv --auto analysis/measure/results/starts_measured.csv --split dev --out analysis/measure/results/auto_vs_manual_dev.json
analysis/measure/validate_manual.py --manual analysis/measure/manual_annotations.csv --auto analysis/measure/results/starts_measured.csv --split heldout --out analysis/measure/results/auto_vs_manual_heldout.json
analysis/measure/validate_seiko.py --manual analysis/measure/manual_annotations.csv --auto analysis/measure/results/starts_measured.csv --waveform data/derived/rt_waveform.csv --foreperiods data/derived/foreperiods.csv --out analysis/measure/results/seiko_validation.json
analysis/measure/build_foreperiods.py --measured analysis/measure/results/starts_measured.csv --manual analysis/measure/manual_annotations.csv --visual analysis/measure/verification_visual.csv --override-ms 40 --out data/derived/foreperiods.csv
analysis/measure/build_video_sources.py --curated analysis/measure/race_starts_curated.csv --candidates analysis/measure/video_candidates_curated.csv --races data/derived/races.csv --athletes data/derived/rt_athletes.csv --wa-listing analysis/measure/discovery/wa_channel_videos_clean.tsv --search analysis/measure/discovery/search_OG_20260929.jsonl analysis/measure/discovery/search_WCH_20260929.jsonl --out data/derived/video_sources.csv
analysis/measure/make_numbers.py --seiko analysis/measure/results/seiko_validation.json --dev analysis/measure/results/auto_vs_manual_dev.json --heldout analysis/measure/results/auto_vs_manual_heldout.json --synthetic analysis/measure/results/benchmark_synthetic_summary.json --foreperiods data/derived/foreperiods.csv --out analysis/measure/numbers.json
analysis/measure/render_readme_results.py --readme analysis/measure/README.md --seiko analysis/measure/results/seiko_validation.json --dev analysis/measure/results/auto_vs_manual_dev.json --heldout analysis/measure/results/auto_vs_manual_heldout.json --synthetic analysis/measure/results/benchmark_synthetic_summary.json --out analysis/measure/README.md
```

The exact producer commands are registered in the repo-root `producers.json`. Whisper runs offline from the local
cache (`HF_HUB_OFFLINE=1`). The `base.en` model is used because `small.en` could not be fully downloaded over
the saturated link.

## Limitations and open questions

- **Relative latency.** The broadcast latency between "Set" and the gun is assumed to be zero, but this is
  unverified. It could add a broadcast-specific constant to every foreperiod.
- **Small first batch.** The Seiko comparison covers 3 championships. WCH2022 and WCH2023 are represented only
  by finals (a handful of races each), so their championship-level offsets are imprecise. See the generated
  tables for the n per championship.
- **Provenance status at the freeze (2026-09-29).**
  - 13 of the 15 registered producers were re-run and reproduce byte-for-byte (`scripts/verify_producers.py`).
  - `results/benchmark_synthetic_trials.csv` (SIMULATED) was produced before the `weak_s_onset` QC flag
    existed. Re-running its registered command reproduces all timings, but `qc_flag` strings can gain
    `weak_s_onset`, which would shift the QC-conditional synthetic rates (`gross_rate_if_qc_ok`). It was not
    re-run because of the freeze.
  - `results/starts_measured.csv` (105 rows) was produced by a full run plus an incremental `--reuse` pass
    with the same code. The 22-row version reproduced byte-for-byte, but the 105-row file has not been
    re-verified end to end (about 30 min of CPU).
- **Visual screening is not blind.** Visual verdicts come from one reviewer who could see the automated marks.
- **Single reader.** Manual readings come from one reader (an AI model, not a human). No second, independent annotator is
  available yet.
