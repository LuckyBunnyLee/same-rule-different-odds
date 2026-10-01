# Reaction-time (RT) data

> **Public copy.** Raw third-party downloads (World Athletics results pages, results PDFs and start-information
> images; Fiore et al.'s `rxntime.csv`) are not redistributed here. Their URLs, retrieval times and sha256 are in
> `data/raw/manifest.csv`. `rt_fiore.csv` is rebuilt locally by `scripts/fetch_third_party.py`. See `../DATA.md`.

Part of the RT data collection. Current scope: 625 races, 4,904 athlete-starts and
4,805 RTs.

| group | competitions | events | rounds |
|---|---|---|---|
| core | WCH 2019 Doha, 2022 Eugene, 2023 Budapest, 2025 Tokyo; OG 2020 Tokyo (held 2021), 2024 Paris | 100m (M/W), 100mH (W), 110mH (M) | **all**, incl. preliminary rounds and Paris repechages |
| extension | same | 200m (M/W) | all |
| extension | WCH 2015 Beijing, 2017 London | 100m, 100mH, 110mH, 200m | all |
| extension | WIC (World Indoor Championships) 2024 Glasgow, 2025 Nanjing | 60m (M/W), 60mH (M/W) | all; added because they carry Seiko holds |

All numbers below come from the generated files, as built on 2026-09-29 by the
commands in `data/scripts/pipeline.py`. The same commands are recorded in
`../producers.json`.

## Outputs (`data/derived/`)

| file | one row per | what it is |
|---|---|---|
| `rt_athletes.csv` | athlete-start | official RT, result, lane, status, false-start and start-card labels |
| `races.csv` | race (heat) | round/heat keys, date, scheduled and actual start time, wind, weather, FS/DQ/card summary, validated Seiko hold, document links |
| `rt_waveform.csv` | race with a Seiko waveform image | start attempt number and **Seiko "Ready Time"** (set-to-gun hold, see caveat), with validation fields |
| `rt_waveform_lanes.csv` | lane in a waveform image | per-lane OCR (RT, bib, name), red RT-marker time, force-onset estimate, compared with the official values |
| `rt_pdf_results.csv` | athlete line in an official results PDF | parsed WCH/WIC PDFs: actual start time, weather, rule codes, `Fn` column, cards, NOTE lines |
| `rt_fiore.csv` | row of Fiore's `rxntime.csv` | Fiore's thesis data, mapped to `race_id`/athlete |
| `rt_qc_flags.csv` | flagged item | quality-check output |
| `rt_coverage.csv` | comp x event x sex | coverage (table below) |

Key: `race_id = {comp}{year}-{event}-{sex}-{round}-H{heat}`, e.g. `WCH2023-100m-W-R1-H3`.
- `comp` is WCH, OG or **WIC**.
- `event` is 100m / 100mH / 110mH / 200m, or **60m / 60mH** (WIC).
- `round` is PR, R1, SF or F, plus **RP**: repechage, OG2024 hurdles and 200m. R2
  is reserved for quarter-finals. WA's "Heats" and "Round 1" both map to R1.
- `heat` is the official WA heat number. Finals are `H1`.
- OG Tokyo keeps the official year (`OG2020-...`). `date` holds the real 2021
  dates.

## Sources and provenance

| source | what we take | files (retrieved 2026-09-29, UTC) |
|---|---|---|
| worldathletics.org results pages, e.g. `/competitions/world-athletics-championships/world-athletics-championships-budapest-2023-7138987/results/men/100-metres/round-1/result` | the embedded Next.js `__NEXT_DATA__` JSON: per heat (`unit`), the start list (lane = `start`), results (`resultMark`, `resultWind`, `reactionTime`, rank, Q/q, PB/SB), scheduled `unitDateTime`, document links | 182 pages, 06:03-09:44 |
| `media.aws.iaaf.org/competitiondocuments/pdf/<id>/AT-...RS6.pdf`: Seiko official results PDFs, **WCH and WIC only** | actual START TIME, temperature, humidity, rule codes, `Fn`, start cards, NOTE lines | 270 PDFs (phase and unit level), 06:20-09:48 |
| `media.aws.iaaf.org/competitiondocuments/waveform/<id>/<X>_<ev>_<rd>_<heat>.jpg`: Seiko start-information images, **WCH2022/2023/2025 and WIC2024/2025 only** | header "Heat / Attempt / Ready Time"; per-lane RT, bib, name; marker lines; force traces | 277 images, 06:21-09:41 |
| github.com/ofiore/Thesis `Data/rxntime.csv` @ `3cf1db7` (2024-11-26) | 2,805 WCH RTs, 1999-2023 | 06:23 |

- Every download sits in `data/raw/` with a `<file>.meta.json` sidecar (URL,
  final URL, status, bytes, sha256, `retrieved_at`), and is logged in
  `data/raw/manifest.csv`.
- Row-level `source_url` and `retrieved_at` are in `rt_athletes.csv` and
  `races.csv`.
- PDFs and JPGs (about 190 MB) are git-ignored (see `.gitignore`), since
  they can be re-downloaded. We publish derived values plus URLs only.
- OCR output (`data/raw/wa/waveform_ocr/`) is included. Results pages and the Fiore file are
  not redistributed in this public copy (see `../DATA.md`).
- WA hosts **no PDFs or waveforms for the Olympics** (Omega timing), and no
  waveforms for WCH2015-2019.
- The "Officiating Video Clip" links (7 races) return HTTP 403.

## How to re-run

From the repository root, with `PY=.venv/Scripts/python.exe`:

```
$PY data/scripts/pipeline.py --fetch      # network + OCR steps; cached and resumable, >= 2.5 s between requests
$PY data/scripts/pipeline.py --build      # offline: rebuild all 8 derived tables, then run check_data.py
$PY data/scripts/pipeline.py --producers  # merge our commands into ../producers.json
$PY scripts/verify_producers.py producers.json --only data/derived/rt_athletes.csv ...
```

- The analysed subset is defined once in `pipeline.py` (`OUT_COMPS`,
  `OUT_EVENTS`, `IN_COMPS`, `IN_EVENTS`) and spelled out in every recorded
  command (`--comps ... --events ...`). Each build command writes one file
  (`--out`).
- Last verification (2026-09-29): 8/8 producers reproduced byte-for-byte. The
  guard also failed as expected on a tampered file.
- `check_data.py` asserts the invariants this README relies on: key format and
  uniqueness, table consistency, status vocabulary, no RT < 0.100 s outside FS,
  holds only where validated, and FS ⇒ Seiko attempt ≥ 2. It was shown to fail
  on deliberately broken copies.
- OCR engine: RapidOCR (`rapidocr_onnxruntime==1.4.4`, CPU). It is installed in
  `.venv`.

## Method

1. **WA results JSON** (`build_rt.py`).
   - One race per `unit`.
   - Results are joined to the start list by competitor id, falling back to bib
     and then name. WA sometimes uses different ids for the same athlete (10
     rows, noted).
   - `status` comes from the mark.
   - An RT printed as `0.000` (1 row, on both site and PDF) is treated as
     missing.
2. **Official PDFs** (`parse_pdfs.py`).
   - Extraction uses pdfplumber (x_tolerance 1, so PLACE and BIB separate) plus
     regexes.
   - Per-heat athlete counts equal the WA JSON counts in every one of the 471
     WCH/WIC heats. PDF rows are joined on `race_id` + lane.
   - **False starts**: `status = FS` when the rule is TR16.8 (2020-),
     IAAF 162.8 (2018-19) or 162.7 (2010-17). It also applies to `TR*` when the
     NOTE says "False start" and names this bib or no bib. `fs_evidence` records
     the rule.
   - **`Fn`** is the start attempt at which the false start happened. For
     example, WCH2015 110mH-M R1 H2 has F1 (RT -0.024) and F2 (RT -0.048).
   - Other DQs keep their code in `dq_rule`, e.g. TR22.6.2 hurdle, TR17.3.1 lane,
     163.2(b) obstruction.
   - **Start cards**: a "Y" before the name is a yellow card (warning), and "L"
     is a lane mark (TR17.4.3). They go to `start_card`, with the NOTE reason in
     `card_note` (e.g. "Disturbing the start").
   - **Post-race DQs** (`DQ-post`, 5): DQ on the site but ranked in the PDF, so
     the start was legal and the RT is valid.
   - When site and PDF RT disagree, the PDF wins (5 cases). The site truncates
     some negative RTs, e.g. -0.030 vs -0.036.
   - The PDF START TIME is the **actual** start. The JSON time is the scheduled
     one.
3. **Olympics (no PDF).** A DQ with RT < 0.100 s is labelled `FS` with
   `fs_evidence = "inferred: ..."` (2 rows). OG2020 DQ rows have no RT on WA, so
   their false starts cannot be identified and stay `DQ`.
4. **Seiko waveforms** (`ocr_waveforms.py`, then `build_waveform.py`).
   - **Layout.** Each 1800x2700 image has nine lane panels on a -2.0 to +1.0 s
     axis (0 = gun), a magenta line at the "ready" (Set) mark, and a red line at
     each lane's detected reaction.
   - **OCR.** The header is OCR'd (`Heat : 001  Attempt : 002  Ready Time :
     1.810 sec`). Lane text is OCR'd after painting out the magenta line.
   - **Marker lines.** Their pixel columns are measured. A linear map is fitted
     on 2,107 red lines whose OCR text equals the official RT: x = 1199.44 +
     600.40·t, residual SD 0.28 px (0.5 ms).
   - **Re-keying.** An image whose header shows a different heat is re-keyed
     when that heat has no image (1 case: WCH2023 110mH-M SF, where the "heat 1"
     link shows heat 2).
   - **`wf_ok` requires all of the following:**
     - OCR heat = WA heat;
     - 0.5 s ≤ hold ≤ 6.0 s. 9.999 is a sentinel; 0.000 and 0.103 are artefacts
       with no Set mark;
     - OCR hold within 4 ms of the magenta-line estimate, or the hold is > 2.0 s
       so the marker is off-chart (`wf_crosschecked` False);
     - every lane's OCR RT equals the official RT.
   - **Results:**
     - 270/277 images pass.
     - In valid races, lane RTs match 2061/2061 and bibs 2000/2000 (all
       images).
     - The OCR minus marker difference is mean 1.1 ms, SD 0.6, max 2.8 over 230
       cross-checked images, i.e. a sub-pixel drawing offset.
     - I read 24 headers by eye (seeded sample plus flagged ones), and 24/24
       agreed with the OCR.
   - **Force onset (descriptive).** Per lane, `onset_5pct_s` is the first time
     ≥ +0.05 s at which the blue force trace rises ≥ max(3 px, 5% of its peak)
     above the pre-gun baseline. `red_minus_onset_ms` is the red detection
     line's time minus that onset.
5. **Fiore data** (`build_fiore.py`).
   - Each `Batch` is matched to the race with the most identical (result 0.01 s,
     RT 0.001 s) pairs in the same year, event and sex. This needs at least
     max(3, 60%) matches and a unique best.
   - Pooled batches are split row by row, and mis-filed rows are re-assigned.
   - Athletes are then matched within the race.

## Column notes

**rt_athletes.csv.** The specified columns come first: race_id, comp, year,
event, sex, round, heat, lane, athlete, country (WA code), rt_s (s; negative =
moved before the gun), result, place, wind (m/s), status, notes, source_url,
retrieved_at. Extras follow:
- athlete_id: WA competitor id.
- bib, qual, record.
- rt_raw: the site string.
- wa_phase, wa_unit_id.
- pdf_fn, in_pdf, dq_rule, fs_evidence.
- start_card, card_note.

`status` is one of: OK, FS (false start), DQ (other or unknown), DQ-post
(post-race; RT valid), DNF, DNS, NR (on the start list but not in the results).

**A false starter's RT belongs to the aborted start**, not to the restart the
others ran. Exclude FS rows when relating RT to the valid start's hold.

**races.csv:**
- `date`, `sched_start_local`: WA `unitDateTime`, **local** wall-clock time.
  WA appends a spurious "Z". This was checked against the PDF START TIMEs and an
  external schedule: Budapest men's 100m final 19:10 CEST = 13:10 ET.
- `actual_start_local`: PDF.
- `tz`.
- `n_athletes`, `n_started`, `n_rt`, `wind`.
- `n_fs`, `n_fs_inferred`, `n_dq`, `n_dns`, `n_dnf`, `dq_detail`.
- `n_yellow`, `card_detail`, `pdf_fn_marks`.
- `temperature_c`, `humidity_pct`, `pdf_notes`.
- `wf_attempt`: Seiko attempt of the imaged start, usually the valid one, so
  ≥ 2 means at least one aborted start.
- `wf_ready_time_s`: filled **only when `wf_ok`**.
- `wf_ok`, `wf_crosschecked`, `wf_notes`.
- Document URLs.

**rt_waveform.csv:**
- `wf_ready_time_s`: printed, 1 ms.
- `wf_ready_time_px_s`: magenta marker, 1.67 ms per px.
- `wf_ready_diff_ms`, `wf_attempt`, validation counts, `wf_linked_from`.
- `wf_stamp` / `wf_title`: the image's own label and clock. The clock is **not**
  a race time; Budapest day-1 stamps read JST.

**"Ready Time" is our reading, not a documented definition.** Seiko prints the
time from the "ready" mark to the gun. "Ready" is Seiko's word for the Set
command (用意). How the mark is triggered (starter switch or microphone) is **not
verified**. Validate against broadcast audio before calling it the acoustic
set-to-gun interval.

**rt_fiore.csv.** Fiore's columns:
- Year.
- Stage: H/S/F.
- TotalTime: s, or DNF/DQ/D/DNS/rule code.
- ReactionTime: s.
- Gender: M/F.
- Batch: race id; ids are "not meaningful" and not always unique.
- Event: '100 Dash', '100 Hurdles', '110 Hurdles', '200 Dash'.

Our mapping columns follow: comp, year, event, sex, round_guess, race_id,
athlete, lane, match_pairs / batch_n / runner_up_pairs, map_note, row_note,
source_url.

## Coverage (`qc_rt.py --report coverage --markdown`)

"races_with_seiko_hold" counts races with a validated hold. "rts_with_seiko_hold"
counts non-FS RTs in those races.

| comp | year | event | sex | races | rounds | races_with_seiko_hold | false_starts | starts | starts_with_rt | rts_with_seiko_hold |
|---|---|---|---|---|---|---|---|---|---|---|
| WIC | 2025 | 60m | M | 12 | R1/SF/F | 11 | 0 | 90 | 90 | 82 |
| WIC | 2025 | 60m | W | 10 | R1/SF/F | 10 | 0 | 74 | 73 | 73 |
| WIC | 2025 | 60mH | M | 9 | R1/SF/F | 8 | 0 | 66 | 65 | 59 |
| WIC | 2025 | 60mH | W | 9 | R1/SF/F | 9 | 0 | 67 | 67 | 67 |
| WIC | 2024 | 60m | M | 11 | R1/SF/F | 10 | 0 | 82 | 81 | 74 |
| WIC | 2024 | 60m | W | 11 | R1/SF/F | 11 | 0 | 85 | 84 | 84 |
| WIC | 2024 | 60mH | M | 10 | R1/SF/F | 10 | 2 | 74 | 73 | 71 |
| WIC | 2024 | 60mH | W | 10 | R1/SF/F | 10 | 0 | 73 | 73 | 73 |
| WCH | 2025 | 100m | M | 14 | PR/R1/SF/F | 14 | 1 | 113 | 113 | 112 |
| WCH | 2025 | 100m | W | 11 | R1/SF/F | 9 | 0 | 93 | 92 | 75 |
| WCH | 2025 | 100mH | W | 10 | R1/SF/F | 10 | 1 | 77 | 76 | 75 |
| WCH | 2025 | 110mH | M | 9 | R1/SF/F | 9 | 0 | 74 | 73 | 73 |
| WCH | 2025 | 200m | M | 10 | R1/SF/F | 10 | 0 | 84 | 83 | 83 |
| WCH | 2025 | 200m | W | 10 | R1/SF/F | 10 | 1 | 81 | 80 | 79 |
| WCH | 2023 | 100m | M | 15 | PR/R1/SF/F | 15 | 2 | 117 | 115 | 113 |
| WCH | 2023 | 100m | W | 11 | R1/SF/F | 11 | 2 | 89 | 87 | 87 |
| WCH | 2023 | 100mH | W | 9 | R1/SF/F | 9 | 0 | 75 | 75 | 75 |
| WCH | 2023 | 110mH | M | 9 | R1/SF/F | 8 | 1 | 78 | 78 | 70 |
| WCH | 2023 | 200m | M | 11 | R1/SF/F | 11 | 1 | 90 | 88 | 88 |
| WCH | 2023 | 200m | W | 10 | R1/SF/F | 9 | 0 | 77 | 76 | 68 |
| WCH | 2022 | 100m | M | 15 | PR/R1/SF/F | 14 | 1 | 117 | 113 | 104 |
| WCH | 2022 | 100m | W | 11 | R1/SF/F | 11 | 2 | 81 | 81 | 79 |
| WCH | 2022 | 100mH | W | 11 | R1/SF/F | 11 | 0 | 74 | 74 | 74 |
| WCH | 2022 | 110mH | M | 9 | R1/SF/F | 9 | 1 | 72 | 71 | 70 |
| WCH | 2022 | 200m | M | 11 | R1/SF/F | 11 | 0 | 81 | 76 | 76 |
| WCH | 2022 | 200m | W | 10 | R1/SF/F | 10 | 0 | 77 | 76 | 76 |
| WCH | 2019 | 100m | M | 14 | PR/R1/SF/F | 0 | 0 | 109 | 106 | 0 |
| WCH | 2019 | 100m | W | 10 | R1/SF/F | 0 | 0 | 79 | 77 | 0 |
| WCH | 2019 | 100mH | W | 9 | R1/SF/F | 0 | 1 | 70 | 70 | 0 |
| WCH | 2019 | 110mH | M | 9 | R1/SF/F | 0 | 1 | 74 | 72 | 0 |
| WCH | 2019 | 200m | M | 11 | R1/SF/F | 0 | 0 | 85 | 82 | 0 |
| WCH | 2019 | 200m | W | 10 | R1/SF/F | 0 | 0 | 80 | 75 | 0 |
| WCH | 2017 | 100m | M | 14 | PR/R1/SF/F | 0 | 2 | 108 | 105 | 0 |
| WCH | 2017 | 100m | W | 10 | R1/SF/F | 0 | 1 | 79 | 79 | 0 |
| WCH | 2017 | 100mH | W | 9 | R1/SF/F | 0 | 0 | 72 | 72 | 0 |
| WCH | 2017 | 110mH | M | 9 | R1/SF/F | 0 | 0 | 73 | 73 | 0 |
| WCH | 2017 | 200m | M | 12 | R1/SF/F | 0 | 0 | 84 | 82 | 0 |
| WCH | 2017 | 200m | W | 11 | R1/SF/F | 0 | 1 | 81 | 77 | 0 |
| WCH | 2015 | 100m | M | 14 | PR/R1/SF/F | 0 | 2 | 116 | 112 | 0 |
| WCH | 2015 | 100m | W | 11 | R1/SF/F | 0 | 2 | 86 | 84 | 0 |
| WCH | 2015 | 100mH | W | 9 | R1/SF/F | 0 | 1 | 69 | 69 | 0 |
| WCH | 2015 | 110mH | M | 9 | R1/SF/F | 0 | 3 | 75 | 75 | 0 |
| WCH | 2015 | 200m | M | 11 | R1/SF/F | 0 | 1 | 92 | 89 | 0 |
| WCH | 2015 | 200m | W | 11 | R1/SF/F | 0 | 0 | 83 | 81 | 0 |
| OG | 2024 | 100m | M | 18 | PR/R1/SF/F | 0 | 1 | 153 | 150 | 0 |
| OG | 2024 | 100m | W | 16 | PR/R1/SF/F | 0 | 0 | 143 | 142 | 0 |
| OG | 2024 | 100mH | W | 12 | R1/RP/SF/F | 0 | 0 | 93 | 93 | 0 |
| OG | 2024 | 110mH | M | 12 | R1/RP/SF/F | 0 | 1 | 93 | 92 | 0 |
| OG | 2024 | 200m | M | 14 | R1/RP/SF/F | 0 | 0 | 102 | 96 | 0 |
| OG | 2024 | 200m | W | 14 | R1/RP/SF/F | 0 | 0 | 106 | 101 | 0 |
| OG | 2020 | 100m | M | 14 | PR/R1/SF/F | 0 | 0 | 121 | 115 | 0 |
| OG | 2020 | 100m | W | 14 | PR/R1/SF/F | 0 | 0 | 113 | 112 | 0 |
| OG | 2020 | 100mH | W | 9 | R1/SF/F | 0 | 0 | 73 | 65 | 0 |
| OG | 2020 | 110mH | M | 9 | R1/SF/F | 0 | 0 | 74 | 72 | 0 |
| OG | 2020 | 200m | M | 11 | R1/SF/F | 0 | 0 | 82 | 80 | 0 |
| OG | 2020 | 200m | W | 11 | R1/SF/F | 0 | 0 | 75 | 74 | 0 |
| ALL |  |  |  | 625 |  | 270 | 32 | 4904 | 4805 | 2060 |

- **Status counts:** OK 4707, DNS 71, DQ 53, DNF 36, FS 32 (30 from official
  PDFs, 2 inferred), DQ-post 5.
- **Start cards:** 12 yellow and 4 lane marks.
- **Actual start time:** known for all 471 WCH/WIC races.
- **Fiore:** 2,805 rows. All 1,158 rows for 2015/2017/2019/2022/2023 map to a
  race_id and an athlete. The years 1999-2013 are not loaded.
- **Core scope (WCH2019-25 and OG, 100m/100mH/110mH):** 280 races, 2,255
  starts and 2,214 RTs.

## Quality checks (`rt_qc_flags.csv`, 95 flags)

- **Lanes.** No race has more than 9 athletes or a duplicate lane. Two solo
  races exist and are real: WCH2017-200m-M-R1-H8 (a solo re-run) and
  WCH2022-100mH-W-R1-H7 (a solo re-run; Fiore files her under heat 6).
- **RT outside 0.08-0.40 s: 19.** All are false starts, down to -0.379 s.
  There are 0 RTs < 0.100 s that are not labelled FS (a guarded invariant).
- **Missing RT: 28.**
  - OG2020 women's 100mH R1 heat 4: all 7 RTs are missing on WA.
  - DQ rows without RT: OG2020 5 and OG2024 2 (several are known false starts;
    the reason is unverified), plus WCH 2.
  - False starters with no printed RT: 8 (WCH2015 4, WCH2017 1, WCH2023 3).
  - Finishers with no RT: 3, plus 1 printed "0.000".
- **Duplicates:** none.
- **Source disagreements: 36, all annotated.** 16 names (married/updated), 10
  id mismatches, 5 truncated negative RTs replaced by the PDF, 5 post-race DQs.
- **Aborted starts.** 10 races have Seiko attempt ≥ 2 without a false-start DQ.
  5 of these carry a yellow card for "disturbing the start". The rest are
  recalls with no recorded cause.

## Data quirks to respect in analysis

- **RT levels differ strongly by championship.** Median valid RT:
  - WCH2022: 0.136 s;
  - WCH2015: 0.157;
  - WCH2017: 0.158;
  - WCH2019: 0.156;
  - WCH2023: 0.156;
  - OG2020: 0.149;
  - OG2024: 0.154;
  - WIC2024: 0.147;
  - WIC2025: 0.155;
  - WCH2025: 0.173 (minimum 0.117).

  Use a championship fixed effect.
- **Descriptive detector check (preliminary).** The red RT-detection line sits
  at the same place on the displayed force rise in every Seiko championship:
  - median `red_minus_onset_ms` is -4.2 ms, IQR -4.2 to -4.2, for WCH2022,
    WCH2023 and WCH2025 (about 480-500 lanes each);
  - WIC IQR is -4.2 to -2.5;
  - median force onsets shift in step with the RTs: 0.141 / 0.158 / 0.176 s
    for WCH 2022 / 2023 / 2025.

  So the championship offsets are *not* a different threshold applied to the
  displayed trace. They arise upstream: in the athletes, the sensors/filtering,
  or the time base. The images cannot tell these apart.
- **WIC2025 holds are anomalous.** Over the 38 valid races the median is 3.25 s
  and the minimum 1.86 s, against about 1.4-1.7 s everywhere else. In 36 of
  those races the marker is off-chart, so there is no cross-check. The "ready" trigger may differ at this meet. Do not pool it
  without verification. Values above 6 s (9.999) are excluded, and 4.0-4.5 s
  holds are kept but flagged.
- **Seiko holds exist for WCH2022/23/25 and WIC2024/25 only.** Usually only the
  valid start is imaged. One WIC2025 image shows an aborted attempt, and it is
  flagged invalid. Aborted attempts' holds are not observed.
- **Holds under 1.0 s: 3** (0.806, 0.846, 0.991). They are printed and
  cross-checked, but unusual. Verify them on video.
- WA website data changes after the meet (post-race DQs, renamed athletes). The
  PDFs are at-the-time snapshots.
