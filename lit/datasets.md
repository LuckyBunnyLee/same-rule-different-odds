# Additional datasets that could strengthen the paper

Part of the literature review. Version 1, 2026-09-29.

Verification: repository pages and files were opened through their APIs, and small files were downloaded and inspected, on 2026-09-28/29. Licences are copied exactly as each repository shows them. I re-checked a sample myself (Edmond CC0, the Salet OSF node with no licence, the Herbst OSF node CC BY 4.0, Yarrow figshare CC BY 4.0).

**Tags**
- **[V-FT]**: files or README or methods text checked.
- **[V-ABS]**: metadata or abstract only.
- **[U]**: unverified.

Relevance keys:
- **(i)** cross-domain comparison with sprint RT–foreperiod curves (sprint holds about 1.3–2.5 s, auditory go signal, simple RT);
- **(ii)** sequential foreperiod effects;
- **(iii)** anticipation or sub-100 ms response rates as a function of foreperiod.

## Headline

1. **Official hold times exist for recent Seiko-timed championships** (found by the data pipeline; coverage probed by me).
   - World Athletics results pages link one Seiko start "waveform" JPG per heat. Each shows `Attempt`, `Ready Time` (probably set → gun; see definitions.md §2), per-lane RT, and per-lane block-force traces from −2 to +1 s.
   - They exist **only for WCH 2022, 2023 and 2025 and WIC 2024 and 2025.**
   - None exist for WCH 2009–2019, WIC 2022, OG 2020 or OG 2024 (Omega), or the one Diamond League meet probed.
   - This makes Seiko 2022–25 the ground truth, and broadcast audio the way to extend coverage back to 2009 and to the Olympics.
2. **There are open lab foreperiod datasets inside the sprint hold range, including auditory "Set–Go" data:**
   - Grabenhorst et al. 2026 (CC0);
   - Salet et al. 2022 (a Gaussian-like distribution at 1.30/1.95/2.60 s with catch trials, plus ready-made hazard and fMTP code);
   - Herbst et al. 2018 (auditory, distributions centred on 1.8 s with graded spread);
   - Yarrow et al. 2026 (trial-level anticipations with Stan models of the RT/anticipation trade-off).
3. **Olympic RTs 2004–2016 (Omega) are CC0 on Deep Blue.** They complement Fiore's World Championships (Seiko) file for vendor comparisons.

## Summary table

| # | Dataset | What it adds | Size / coverage | Licence (as shown) | Tag | Priority |
|---|---|---|---|---|---|---|
| A4 | **WA Seiko start waveform JPGs** | Official hold (`Ready Time`), attempt number, per-lane RT and force traces | About 250–300 heats (estimate, not enumerated): WCH 2022/23/25 and WIC 2024/25; ~465 KB each | World Athletics terms of use; publish derived numbers plus URLs only | V-FT (image read; coverage probed via results-page JSON) | **1** |
| B9 | Grabenhorst, Poeppel & Michalareas 2026 Set–Go data | Auditory **and** visual RT vs Go time 0.4–2.8 s; uniform, exponential and flipped-exponential distributions | 23 KB .mat; 13 participants × 15 Go times × 3 spans × 3 distributions × 2 modalities (means) | CC0 1.0 | V-FT | **2** |
| B3 | Salet et al. 2022 fMTP supplement (OSF eu7sd) | Trial-level data, foreperiods 1.30/1.95/2.60 s (peaked) plus catch trials, previous-foreperiod columns; Python for hazard, subjective hazard and fMTP; digitized classic datasets (Trillenberg 2000 aging, Gaussian and non-aging at the same foreperiods) | 3 CSVs of 11–12 MB (20–22 participants each) | No licence shown (OSF API `license: null`) | V-FT | **3** |
| B1 | Yarrow et al. 2026 data and code (City figshare) | Trial-level anticipations (RT < 0 and < 0.100 s) vs foreperiod and distribution; Stan models; includes Visalli et al.'s Gaussian-foreperiod data | `Share.zip` 2.04 MB; E1 29,959 trials; E2 21,330; E3 29,373 | CC BY 4.0 | V-FT (data); V-ABS (paper) | **4** |
| A1+A5 | Fiore `rxntime.csv` (WCH 1999–2023) and Mirshams Shahshahani Deep Blue (OG 2004–2016) | Unconditional RT distributions and sub-0.100 s tails by vendor, meet, sex and round (no foreperiod) | 2,805 rows / 355 races; OG: 2 Excel sheets (sizes unverified) | Fiore: none shown (GitHub `license: null`). Deep Blue: CC0 | V-FT / V-ABS | **5** |
| B10 | Herbst, Fiedler & Obleser 2018 (OSF qbhma) | **Auditory** targets; foreperiod 0.5–3.1 s, **mean 1.8 s** in every condition with graded spread (SD 0.78 vs 0.42 s vs mostly fixed), a lab model of starter consistency | 0.96 MB behavioural txt; 24 participants; 13,104 trials | CC-By Attribution 4.0 International | V-FT | Honourable mention |
| B6 | Sadler et al. 2022 StartReact composite (OSF cu2er) | Legitimate *prepared* responses to ~120 dB stimuli; per-participant means, control vs startle | 0.06 MB CSV; 818 rows from 25 datasets | No licence shown | V-FT | Honourable mention |
| B5 | PVT sets (Welhaf et al., OSF cnsf5 and zmqxf) | "False start" (RT < 100 ms) rate vs wait time, large N | 2.7 MB (161 participants); 0.27 MB (80 participants) | No licence shown | V-FT | Low–medium |
| B4 | Houshmand Chatroudi, Mioni & Yotsumoto 2024 (OSF km27b) | Curve-shape benchmark (exponential decay); an online set with trial order | 12,432 lab + 6,720 online trials; foreperiod 0.48–1.92 s | No licence shown | V-FT (files); V-ABS (findings) | Low–medium |
| B11 | Han & Proctor 2022 (OSF um34f, view-only) | Clean FP(n−1) × FP(n) sequential effects with large N | E1 75 participants / 18,562 trials (400/1,400 ms) | None shown (view-only link) | V-FT | Low |
| B7 | Capizzi et al. 2026 TEP-Task (OSF rnc4v) | Test–retest reliability of individual foreperiod and sequential effects (a prior on athlete-level sensitivity) | 109 + 65 + 44 participants | No licence shown | V-FT (listing) | Low |
| B2 | Visalli et al. 2021 FPbayes (OSF ckqa5) | Gaussian generative foreperiod distributions (means 0.5–2.1 s × SD 25–200 ms), trial-level belief updating, premature-response flags | 3.73 MB CSV; 27 participants | No licence shown | V-FT | Medium (also inside B1) |
| A6 | WA / Leeds Beckett biomechanics reports (WCH 2017, WIC 2018) | Set-position and block-phase kinematics, finals only; **no hold times** | 38 reports (2017) + WIC 2018 | WA document terms | V-FT (one report) | Low (history notes only) |

## A. Sports datasets (details)

**A4. Seiko start waveform JPGs on World Athletics results pages.** The highest-value find.
- **URL pattern** (200 OK, `image/jpeg`): `https://media.aws.iaaf.org/competitiondocuments/waveform/<compId>/<SEX>_<EVENT>_<phase>_<heat>.jpg`, e.g. `.../waveform/7137279/M_110H_f_1.jpg`.
- **Competition IDs with waveforms:** WCH 2022 `7137279`, WCH 2023 `7138987` (which also has "Officiating Video Clip" MP4s), WCH 2025 `7190593` (preliminary round included), WIC 2024 `7180312`, WIC 2025 `7136586`.
- **Without waveforms:** WCH 2009 `6998524`, 2011 `7003367`, 2013 `7003368`, 2015 `7078726`, 2017 `7093740`, 2019 `7125365` (2019 has RS5 "Race Analysis" PDFs); WIC 2022 `7138985`; OG 2020 `7132391`; OG 2024 `7153115`; DL Zurich 2025 `7199686`.
- **Content, read from WCH 2022 M 110 mH final:**
  - header "Heat : 001 Attempt : 002 Ready Time : 1.854 sec";
  - a magenta marker at −1.85 s;
  - a red detection marker per lane and the printed RT;
  - DQ lanes blank.
- **Caveats.**
  - The meaning of `Ready Time` and how it is triggered are [U].
  - Only one JPG is listed per heat, so recalled first attempts are probably not published [U].
  - The detection rule is not documented on the image; for the 1995 patent see definitions.md §3.
- **What it enables.**
  - C1: the RT–hold relation and the sub-0.100 s tail on official holds.
  - C3: empirical starter and session distributions, and hazard/PDF predictors.
  - C6: within-session sequences, using the printed times; athlete-linked rounds.
  - C9: settle times and steadiness from the force traces.
  - A check of the detection-latency regime across meets (red marker vs the visible force rise; see STATUS 00:49).
  - C2: audio vs official agreement.

**A1. `ofiore/Thesis`, `Data/rxntime.csv`.** https://github.com/ofiore/Thesis
- 98,636 bytes; 2,805 rows. Columns `Year, Stage, TotalTime, ReactionTime, Gender, Batch, Event`; 355 races; WCH odd years 1999–2019, plus 2022 and 2023.
- Licence: none shown, so re-scrape from World Athletics and use this only as a cross-check.
- 15 values below 0.100, including zeros and negatives that are probably coding artefacts.
- No athlete, lane or heat identifiers; no foreperiod. The Stage counts (heats H 917 vs semis S 1,373) suggest quarterfinal rows were merged into S. Check before use.

**A5. Mirshams Shahshahani (2018) Olympic sprint results, all heats, 2004–2016.** doi:10.7302/z20v8b11. https://deepblue.lib.umich.edu/data/concern/data_sets/cr56n184r
- CC0.
- 100 m, 100 mH and 110 mH at OG 2004–2016, plus all sprints under 800 m at OG 2008–2016.
- Scripted requests get 403, so **download it manually in a browser.**
- Linked paper: Mirshams Shahshahani et al. 2018, PLOS ONE.

**A2 and A3. Benchmarks, not datasets.**
- Otsuka et al. 2017: 83 championship races, mean 1.780 s, SD 0.158 s [V-FT]; no per-race data or data statement. The Fig. 1 histogram could be digitized as an external check on our hold distribution for WCH 2011/13/15 and OG 2012.
- Dalmaijer et al. 2015: 148 skating races [V-FT]; no data statement or repository. The authors could be asked.
- Haugen et al. 2013: the 267 TV-measured holds are not public; the T&F supplement page returned 403 [U].

**A6. Biomechanics reports.**
- Finals only; no set-to-gun interval [V-FT for the WIC 2018 women's 60 m report].
- They supply history: detection threshold "set at 30kg at the Munich 1972 Olympic Games", later "27kg in Los Angeles 1984" (the report cites Young 2001) [V-FT in the report; primary not checked].

**A7. Other sports.**
- False-start DQs can be derived from World Athletics results rule codes (TR16.8, formerly 162.7). No curated open DQ list was found.
- Swimming: no open "take your marks" hold dataset was found. Kaggle Olympic swimming results were not inspectable [U].

## B. Lab foreperiod datasets (details)

**B9. Grabenhorst, Poeppel & Michalareas 2026, PNAS 123(2):e2518982123.** Data: Edmond doi:10.17617/3.MEAGMS, file `data_2025_18982.mat`, 23,687 bytes, CC0 1.0.
- Variable `RTGTMat` has shape 13 × 15 × 3 × 3 × 2: participants × Go times × spans × distributions × modality. Values are within-participant mean RTs.
- Go times start at 0.4 s with spans of 1, 1.7 and 2.4 s, so the long span covers **0.4–2.8 s**.
- 9.09% catch trials; RTs < 0.05 s excluded as guesses.
- Their earlier sets:
  - 2021 PNAS: Edmond doi:10.17617/3.YC3SGA, CC BY-SA 4.0, a 6 KB .mat whose structure needs the paper's SI.
  - 2025 Nat Commun: RT data in Supplementary Data 1.
  - 2019 Nat Commun: data "upon reasonable request", i.e. not open.
- **Use:** overlay lab and sprint curves (C7), and run the same PDF vs hazard predictors (C3).

**B3. Salet et al. 2022, Psych Rev 129(5):911–948, OSF eu7sd.**
- Files: `experiment/exp1clock.csv` (11.0 MB, 20 participants), `exp1noclock.csv` (12.1 MB, 22 participants), `exp2standardFP.csv` (11.3 MB, 21 participants; includes an `SOAn-1` previous-foreperiod column).
- Foreperiods 1.30/1.95/2.60 s at a ratio of about 1 : 4.8 : 1, with catch trials coded 3.25 s (~12.5%).
- `model_code/` has `hazard.py` and `get_phi_sub_hz.py` (the Weber-blur kernel).
- `model_code/empirical_data/` holds digitized classic data:
  - `trillenberg2000.csv`, mean RT at 1.3/1.95/2.6 s:
    - Gaussian distribution: 337/274/290 ms, a **late rebound**;
    - aging (uniform): 339/305/302 ms;
    - non-aging: 297/291/294 ms.
  - `los2013.csv`, `losheuvel_*.csv`, `steinborn2012.csv`, `niemi1979.csv`, and `seq_effects.csv`/`sub_avg.csv` (probably the Los et al. 2017 "Hazard versus history" data).
- No licence is shown, so cite and re-derive; do not redistribute.
- Choice RT; visual targets [U].

**B1. Yarrow et al. 2026 data.** City figshare doi:10.25383/city.30715439, `Share.zip` (2,035,751 bytes), CC BY 4.0.
- E1: online, visual; foreperiod 0.77–1.50 s; early- vs late-weighted distributions × an anticipation-cost condition; 5.95% RT < 0 and 8.4% RT < 0.100 s.
- E2: Visalli et al. Gaussian foreperiods, means 0.5–2.1 s × SD 25–200 ms; premature-response flag `FPAcc`.
- E3: 8 participants, 29,373 trials; foreperiod 0.79–2.0 s; 9.8% RT < 0.1 s; modality [U].
- **Use:** calibrate how "too early" responses rise with foreperiod and hazard (C1), and borrow the SIP-theN-SPuRT Stan models.

**B10. Herbst, Fiedler & Obleser 2018, eNeuro, OSF qbhma.** CC-By Attribution 4.0 International.
- `Data/Behavioural/DATA_DisTime_EEGII_24sbs.txt` (0.96 MB): 24 participants, 13,104 trials.
- Auditory target (pitch discrimination, so choice RT). Foreperiod mean 1.8 s in all conditions, with spread varied.
- **Use:** how hold consistency (spread) changes the RT–foreperiod curve at the sprint mean hold.

**B6. Sadler et al. 2022, Behav Brain Res 426:113839, OSF cu2er.**
- Participant × condition means from 25 StartReact datasets.
- The search pass's summary: startle mean RT 0.085 s; 82.6% of participant-mean startle RTs < 0.100 s; RT is probably EMG onset [U].
- Related paper, no data: Leow et al. 2018, Neuroscience 393:226–235. It reports that foreperiod variability confounds startle-trial RT effects and that foreperiod predictability shifts RT to intense sounds [V-ABS via the search pass].

**B5. PVT data.**
- Welhaf et al. OSF cnsf5: `Data/R&U2020_E1_PVTraw.csv`, 161 participants, `waittime` 1–10 s.
- Welhaf OSF zmqxf: `Maybrier_PVT.csv`, 80 participants, 6,346 trials, 1.1% RT < 100 ms.
- Visual stimuli, and waits much longer than sprint holds. Use only for "false start rate vs wait time" framing.

**B8. Other lab items checked (low priority).**
- Crowe, Los, Schindler & Kent 2021, QJEP 74(8):1432–1438: auditory, unfilled foreperiod, 0.4–1.6 s; **no data statement** [V-FT].
- Huang & Chao 2025, PLOS Biol: conditional timing statistics; OSF VEDHP, mostly MEG.
- Massar et al. 2020, Cognition: OSF w7bv8.
- Developmental set: OSF zfwu5.

## Top 5 to use (in order)

1. **A4 Seiko waveforms.** The core official-hold analysis (C1, C3, C6, C9) and ground truth for C2. Effort: medium. The data pipeline is doing the OCR; the `Ready Time` definition must be confirmed against broadcast audio on about 10 heats.
2. **B9 Grabenhorst 2026 (CC0).** Auditory Set–Go curves spanning 0.4–2.8 s, for a lab vs sprint overlay (C7) and a PDF vs hazard fit (C3). Effort: about 1 h.
3. **B3 Salet 2022 fMTP.** A peaked foreperiod distribution at 1.30/1.95/2.60 s with catch trials, plus ready-to-run hazard, subjective-hazard and fMTP code to apply unchanged to the sprint data. Trillenberg's Gaussian "late rebound" vs Salet's flattening maps directly onto Haugen's positive slope at long holds. Effort: 2–4 h.
4. **B1 Yarrow 2026 (CC BY).** Anticipations vs foreperiod, and a published model of the RT/anticipation trade-off; the lab counterpart of C1. Effort: 1–2 h for descriptives, 0.5–2 days for a refit.
5. **A1 + A5.** Unconditional RT tails by vendor and meet (World Championships Seiko vs Olympics Omega). This is the prior that the foreperiod-conditional model shifts, and a cross-check on our World Athletics scrape. Effort: low; Deep Blue needs a manual download.

## Licensing and handling rules for this repo

- **World Athletics material** (results, waveform JPGs, video): store derived numbers and source URLs only. Do not re-host images or video (see BRIEF, Integrity).
- **Data with no licence shown** (OSF `license: null`, GitHub with no LICENSE): cite, and download for analysis locally if needed, but **do not redistribute** raw files in our repo. Publish derived summaries with attribution.
- **CC0, CC BY and CC BY-SA:** may be redistributed with attribution (and share-alike for CC BY-SA).

Full per-dataset notes, with more column lists and the search pass's download log, are in `lit/notes/lit_notes_datasets.md`. BibTeX for every item is in `refs.bib`.
