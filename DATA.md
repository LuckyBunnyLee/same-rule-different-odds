# Data: sources, provenance and licences

This file lists every data file the analysis uses, where it came from, when it was retrieved, what we did to it, and
under which terms it can be reused. Exact data versions (sha256 prefix and row count of every input) are recorded in
each result JSON and collected in `analysis/numbers.json` (`_data_versions`). The SSAC rules ask for the data used in
the research; everything below is included except where a third party's terms do not allow redistribution, in which
case a script fetches the file from its source and verifies it.

## 1. Sources

### 1.1 World Athletics official results (public)

| source | what we take | retrieved (UTC) | files |
|---|---|---|---|
| worldathletics.org results pages, e.g. `https://worldathletics.org/competitions/world-athletics-championships/world-athletics-championships-budapest-2023-7138987/results/men/100-metres/round-1/result` | the page's embedded results JSON: start lists, lanes, results, reaction times, scheduled times, document links | 2026-09-29 06:03-09:44 | 182 pages |
| `media.aws.iaaf.org/competitiondocuments/pdf/...` (official results PDFs, World Championships and World Indoors) | actual start time, weather, rule codes (false starts: TR16.8), cards, notes | 2026-09-29 06:20-09:48 | 270 PDFs |
| `media.aws.iaaf.org/competitiondocuments/waveform/...` (Seiko start-information images, World Championships 2022/2023/2025 and World Indoors 2024/2025) | header (heat, attempt, "Ready Time"), per-lane RT, bib and name, marker lines and force traces, read by OCR and pixel analysis | 2026-09-29 06:21-09:41 | 277 images |

- Competitions: World Championships 2015, 2017, 2019, 2022, 2023, 2025; Olympic Games 2020 (held 2021) and 2024;
  World Indoor Championships 2024 and 2025. Events: 100 m, 100 m hurdles, 110 m hurdles, 200 m, 60 m, 60 m hurdles.
- **Provenance:** `data/raw/manifest.csv` lists every download (URL, final URL, HTTP status, bytes, sha256, retrieval
  time; 737 rows). Row-level `source_url` and `retrieved_at` are also in `rt_athletes.csv` and `races.csv`.
- **Not redistributed:** the raw pages, PDFs and images (World Athletics website content). `data/scripts/pipeline.py
  --fetch` re-downloads them from the URLs in the manifest; pages may have changed since retrieval, so the manifest's
  sha256 values identify the versions used.
- **Included:** derived tables (below) and our OCR output of the start-information images
  (`data/raw/wa/waveform_ocr/*.json`; `data/scripts/build_waveform.py` rebuilds `rt_waveform.csv` and
  `rt_waveform_lanes.csv` from it together with the re-downloaded pages and images).

### 1.2 Fiore et al.: World Championships RTs 1999-2023 (github.com/ofiore/Thesis)

- **Files used:** `Data/rxntime.csv` at commit `3cf1db7adebb493f3a5c2e957a1b09cf0986a7cd` (retrieved
  2026-09-29T06:23:23Z, sha256 `5b8d3144a577...`), and the manuscript sources at commit
  `85d9a60b68741f308cd1670e2e425c1f4a640341` (retrieved 2026-09-30T17:35:42Z): `Manuscript/manuscript.tex`,
  `Manuscript/supp.tex`, `Code/ReactionBarrierAnalysis.Rmd` and the vector figure `Manuscript/ComparisonOfVenueEffects.pdf`
  (full URLs and sha256 in `analysis/external/fiore2025/SOURCE.json` and `scripts/fetch_third_party.py`).
- **Licence finding (checked 2026-09-30):** the repository has no LICENSE file and GitHub reports no licence for it, so
  redistribution is not clearly permitted. Its `Data/README.md` states that the data were copied from World Athletics
  results pages.
- **What we do instead:** `scripts/fetch_third_party.py` downloads the files above from the pinned commits into
  git-ignored paths, checks each sha256, rebuilds `data/derived/rt_fiore.csv` with the registered command
  (`data/scripts/build_fiore.py`) and checks that the rebuilt file is byte-identical to the one the analysis used
  (sha256 `dff5cb184d1b...`).
- **Which columns are theirs and which are ours** (`rt_fiore.csv`):
  - copied from `rxntime.csv` (not redistributed): `Year`, `Stage`, `TotalTime`, `ReactionTime`, `Gender`, `Batch`, `Event`;
  - our transformation (included as `data/derived/rt_fiore_mapping.csv`, keyed by `fiore_row`, the 1-based data row of
    `rxntime.csv`; produced by `data/scripts/fiore_mapping.py`): `comp`, `year`, `event`, `sex`, `round_guess` (recodes
    to our keys), `race_id` (each source batch matched to a World Athletics race by (result, RT) pairs), `athlete` and
    `lane` (matched within the race, from `rt_athletes.csv`), `match_pairs`, `batch_n`, `runner_up_pairs`, `map_note`,
    `row_note` (matching diagnostics) and `source_url`.
- **Transcribed published values:** `analysis/fiore2025_params.csv` holds the model parameters and published tail
  probabilities and barriers from Fiore, Schifano & Yan (2025), transcribed by us; after the fetch,
  `analysis/tests/test_systematic.py` checks every value against the manuscript lines (regenerated locally as
  `analysis/external/fiore2025/source_extract.txt`). The venue effects of their figure are read from the fetched vector
  PDF at run time by `analysis/systematic.py`.

### 1.3 Broadcast audio (official broadcast footage)

- **Sources:** race videos on official channels (World Athletics, Olympics), identified by YouTube video id. The
  discovery listings are in `analysis/measure/discovery/` (retrieved 2026-09-28/29) and the chosen video and time for
  each race in `analysis/measure/race_starts_curated.csv` and `data/derived/video_sources.csv` (URL, channel, title,
  retrieval date).
- **Not redistributed:** audio and video. They were downloaded locally for measurement only (`data/video/`, git-ignored)
  and are never part of this repository. The spectrogram sheets rendered from the audio for blind reading are not
  included either; `analysis/measure/annotation_sheets.py` and `contact_sheets.py` regenerate them from the audio.
- **Included (our measurements):** `data/derived/foreperiods.csv` (set onset to gun, per race), automated proposals and
  measurements (`analysis/measure/proposals/*.csv`, `analysis/measure/results/`), the blind readings
  (`analysis/measure/manual_annotations.csv`, with the reader recorded in its `annotator` column) and the non-blind
  visual screening (`analysis/measure/verification_visual.csv`). `analysis/measure/README.md` documents the pipeline
  and its validation.

### 1.4 Exploratory probe inputs (`analysis/probe/`)

- `extra_rt.csv` (400 m, 400 m hurdles and relay starts) and `combined_rt.csv` (decathlon and heptathlon sprint and
  hurdle starts): parsed from World Athletics results pages retrieved 2026-09-30 by `fetch_extra_events.py`,
  `parse_extra.py` and `fetch_combined.py`; every page's URL, retrieval time and sha256 is in
  `analysis/probe/wa_pages_manifest.csv` (the pages themselves are not redistributed); rows carry their source URL.
- `gun_features.csv`, `gun_spectra_peaks.csv`, `gun_spectra_similarity.csv`, `guns_200m_wch2025_candidates.csv`:
  acoustic features of the start signal computed from broadcast audio by `gun_features.py`, `run_gun_features.py`,
  `gun_spectra.py` and `find_guns_200m.py` (relative, within-recording quantities only).
- These scripts are kept for provenance; they need network access or local audio and are not run by
  `analysis/run_all.py`. The notes inside `analysis/outputs/recent_probe.json` name them by these paths.

### 1.5 Published designs (transcribed)

- `analysis/haugen_design.csv`: our reconstruction of the championship design of Haugen, Shalfawi & Tønnessen (2013),
  from the paper, used by the S3 simulations. Each value's basis is tagged in its `source` column ([V-ABS] read from
  the abstract, [INF] inferred).

### 1.6 Literature audit (`lit/`)

- `lit/audit_search/*.json`: frozen search results from OpenAlex, PubMed, Semantic Scholar and Google Scholar and one
  round of OpenAlex citation chasing (retrieved 2026-09-30; queries and counts in `search_log.json`). **Bibliographic
  metadata only:** the abstract and snippet texts the services returned were removed before publication (publisher
  copyright), so `lit/tools/audit_screen.py` needs a fresh `lit/tools/audit_search.py` run to reproduce the keyword
  screening; the frozen screening decisions are in `lit/audit_screening.csv` and `lit/audit_search/screen_decisions.csv`.
- `lit/audit_studies.csv`: our coding of the included studies (one row per finding), following `lit/audit_protocol.md`.
- `lit/refs.bib`, `lit/tools/cache/*.bib`: bibliographic records (Crossref metadata and hand-written entries).
- No third-party PDFs or full texts are included. The literature notes contain short quotations for verification only.

### 1.7 Synthetic data

- `analysis/mock/data/MOCK_*`: synthetic data from `analysis/make_mock.py` (seeded), used by the tests and by
  `analysis/run_all.py --mock`. Mock data never enter `analysis/numbers.json`.

## 2. Files used by the analysis

| file | rows | one row per | source | notes |
|---|---|---|---|---|
| `data/derived/rt_athletes.csv` | 4,904 | athlete-start, 2015-2025 | World Athletics pages and PDFs | official RT, result, lane, status, false-start labels |
| `data/derived/races.csv` | 625 | race (heat) | World Athletics pages and PDFs | keys, times, wind, weather, false-start summary, validated Seiko hold |
| `data/derived/rt_pdf_results.csv` | 3,676 | athlete line in a results PDF | World Athletics PDFs | parsed PDF fields |
| `data/derived/rt_waveform.csv` | 277 | race with a start-information image | World Athletics images (OCR) | attempt and Seiko Ready Time, with validation fields |
| `data/derived/rt_waveform_lanes.csv` | 2,493 | lane in an image | World Athletics images (OCR, pixels) | per-lane RT, marker time, force-onset estimate |
| `data/derived/rt_fiore.csv` | 2,805 | row of Fiore et al.'s file | Fiore et al. + our mapping | **not committed**; rebuilt by `scripts/fetch_third_party.py` |
| `data/derived/rt_fiore_mapping.csv` | 2,805 | row of Fiore et al.'s file | ours | our derived columns of `rt_fiore.csv` only |
| `data/derived/foreperiods.csv` | 105 | race start | broadcast audio (ours) | set-onset-to-gun foreperiod and quality flags |
| `data/derived/video_sources.csv` | 134 | race x video | official channels | video URL, channel, title, match confidence, retrieval date |
| `data/derived/rt_coverage.csv`, `rt_qc_flags.csv` | 57, 95 | coverage cell / flagged item | ours | quality checks |
| `analysis/measure/manual_annotations.csv` | 36 | blind reading | broadcast audio (ours) | set onset, end of voicing, end of word, gun; reader in `annotator` |
| `analysis/measure/results/starts_measured.csv` | 105 | race start | broadcast audio (ours) | automated measurements |
| `analysis/haugen_design.csv` | 4 | design variant | transcribed (ours) | S3 simulation inputs |
| `analysis/fiore2025_params.csv` | 3 | parameter set | transcribed (ours) | Fiore et al.'s published parameters |
| `analysis/probe/extra_rt.csv`, `combined_rt.csv` | 1,593, 430 | athlete-start | World Athletics pages | exploratory probe only |
| `analysis/probe/gun_*.csv` | small | start / cell | broadcast audio (ours) | exploratory probe only |
| `lit/audit_studies.csv` | 89 | coded finding | ours | literature audit |
| `lit/audit_screening.csv` | 558 | screened record | ours (metadata from search services) | literature audit |

`races.csv` has one row for each of the 625 races scraped from World Athletics. The RT analyses also use races that appear only in Fiore et al.'s file (`rt_fiore.csv`, rebuilt by `scripts/fetch_third_party.py`), which has no race pages, so they span 836 races with at least one valid start (`descriptive.n_races`).

Column definitions for the RT tables are in `data/README.md`; the measurement tables are described in
`analysis/measure/README.md`.

## 3. Licences and terms

- **Our derived data, results and figures** (everything above marked "ours", our transformations of public results,
  the result files in `analysis/outputs/`, `analysis/numbers.json` and the figures): CC BY 4.0
  ([LICENSE-DATA.md](LICENSE-DATA.md)).
- **World Athletics results** are public competition results; we publish derived values (facts such as reaction
  times, results and lanes) with the source URL of every row, not World Athletics' pages, documents or images.
  World Athletics' own terms apply to its website content.
- **Fiore et al.'s files** are not redistributed (no licence); they are fetched from their repository by the user.
- **Broadcast audio and video** are not redistributed; only our measurements and the public video identifiers are.
- **Literature search results:** bibliographic metadata only (titles, authors, venues, years, DOIs and service ids).

## 4. Not included, and why

| item | reason | how to obtain |
|---|---|---|
| World Athletics results pages, PDFs and start-information images | third-party website content | `data/scripts/pipeline.py --fetch` (URLs in `data/raw/manifest.csv`) |
| Fiore et al.'s `rxntime.csv`, manuscript sources and venue figure | no licence in the source repository | `scripts/fetch_third_party.py` |
| Broadcast audio and video, and spectrogram sheets rendered from them | broadcaster copyright | video ids in `data/derived/video_sources.csv`; `analysis/measure/download_audio.py`, `annotation_sheets.py` |
| Abstract and snippet texts from literature search services | publisher copyright | `lit/tools/audit_search.py` |
| Raw pages of the exploratory probe | third-party website content | `analysis/probe/fetch_extra_events.py`, `fetch_combined.py` |
