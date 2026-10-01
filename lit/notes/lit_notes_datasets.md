# lit notes: datasets (search pass of the literature review)
Started 2026-09-28 ~22:50 PT. Tags follow the literature-verification rule (updated 2026-09-29):
- [V-FT] = checked in the repository files/README or the paper's full text; the relevant variable names or methods lines are quoted.
- [V-ABS] = abstract or repository metadata only.
- [S] = secondary source.
- [U] = unverified.

Licence strings are copied as shown on the repository. For OSF nodes with no licence set, the API returns `license: null` and the page shows none; this is recorded as "No licence shown (OSF API license: null)".
Relevance keys: (i) cross-domain comparison with elite sprint RT-FP curves (sprint FP ~1.3-2.5 s, auditory go, simple RT); (ii) sequential FP effects; (iii) anticipation / sub-100 ms response rates vs FP.

## A. Sports datasets

### A1. Fiore thesis repo: `ofiore/Thesis`, `Data/rxntime.csv` [V-FT]
- Landing: https://github.com/ofiore/Thesis ; file: https://raw.githubusercontent.com/ofiore/Thesis/main/Data/rxntime.csv (98,636 bytes; `Data/GLMMData.csv` is byte-identical in size, same header).
- Host: GitHub. Repo created 2023-02-07, last push 2025-04-15. **Licence: none shown** (no LICENSE file; GitHub API `license: null`), so default copyright applies; the underlying facts come from World Athletics results pages. Safest route: re-scrape from WA ourselves and cite Fiore as a cross-check, not redistribute his CSV.
- Contents (checked 2026-09-28 with pandas): 2,805 rows, 7 columns `Year, Stage, TotalTime, ReactionTime, Gender, Batch, Event`. 355 unique `Batch` (= race) IDs. Years: 1999, 2001, ..., 2019 (odd years), 2022, 2023, all World Championships (WCH) only.
  - By event: M 100 m 362 rows; W 100 m 369; M 110 mH 938; W 100 mH 769 (2001-2023); M 200 m 367 (README says not used in his analysis).
  - Stage: H 917, S 1,373, F 515. README: 1999 had a QF round; README does not say how QF was coded. The S > H imbalance means heats may be incomplete or QF merged into S. **Needs checking before use.**
  - RT: n = 2,794 numeric; mean 0.1543 s, SD 0.027, median 0.152, IQR 0.139-0.166, max 0.397. 15 values < 0.100: three negative (-0.137, -0.117, -0.104), five exactly 0.000, and 0.053, 0.063, 0.071, 0.078, 0.093, 0.095, 0.099. The zeros and negatives are likely DQ, placeholder or system-coding artefacts. TotalTime codes: D 33, DNF 29, DQ 27, DNS 12, plus 2 rule-coded DQs.
- **Missing:** athlete name/ID, lane, heat number (`Batch` is an arbitrary integer), wind, timing vendor, date, foreperiod. It cannot be joined to video without re-deriving race identity, e.g. by matching TotalTime sequences to WA results pages.
- Also in the repo: `Data/Clusrank*.csv` (athlete-clustered RT comparisons: WCH 2019 vs 2022, 2022 vs 2023, 2022 national champs vs WCH), `Manuscript/manuscript.tex` + `supp.tex` (the arXiv 2506.11460 paper source), and `references/milloz2021sprint.pdf` (a copy of Milloz et al. Sports Med 2021).
- Relevance: RT outcome data only, no FP. Good as (1) a cross-check of our WA scrape, (2) a large prior for the unconditional RT distribution and the sub-0.100 s tail, including the 2022 Eugene cluster of Devon Allen-type RTs. It is not a foreperiod dataset.

## B. Lab foreperiod datasets (trial-level unless noted)

### B1. Yarrow, Saurels, Arnold, Tal-Perry & Solomon: SIP-theN-SPuRT data + code [V-FT data; V-ABS paper] (**high priority; also a key related paper**)
- Paper: Yarrow K, Saurels BW, Arnold DH, Tal-Perry N, Solomon JA (2026 preprint, "forthcoming"). "How beliefs about the warning-target foreperiod inform temporal preparation to determine simple reaction times." PsyArXiv, doi:10.31234/osf.io/69xvk_v1, posted 2026-04-17/19. Preprint licence string: "CC-By Attribution 4.0 International". **The abstract's first sentence uses our exact scenario: "as when a sprinter learns the constant foreperiod from set to go".** It models the **trade-off between RT and anticipatory errors** with a trial-by-trial updated subjective FP distribution (history effects). Best-fitting model: the preparation signal follows the subjective hazard, then saturates at a physiological limit. 9 model variants compared, with basis functions elapsed-time vs PDF vs hazard. The parent should cite this and position against it: lab only, no sport data.
- Data: https://doi.org/10.25383/city.30715439 (City, University of London Figshare; published 2025-11-25; licence string **"CC BY 4.0"**). One file, `Share.zip` (2.04 MB): https://ndownloader.figshare.com/files/59844110 . Contains R + Stan code and trial-by-trial data, one file per participant. Downloaded and checked in `scratchpad/ds_yarrow/`.
  - **E1:** 51 participant files (36 analysed per the readme), 29,959 trials with RT. Online (Prolific, PsychoPy 2021.1.4), task name `ForePeriodSimpleRTVisCost` (visual target). FP 0.5-1.5 s, discrete values 0.77-1.50 s. Two FP distributions (`Distribution` 0/1: mean FP 1.02 vs 1.25 s, i.e. early- vs late-weighted), crossed with a cost-for-anticipation condition (`Costcon`) and reward/cost columns. Columns include `ActualRT`, `ActualForePeriod`. **Anticipations kept:** 5.95% of trials have ActualRT < 0 (response before target) and 8.4% are < 0.100 s.
  - **E2:** 27 files, 21,330 trials. Re-shared from Visalli et al. (OSF ckqa5; see B2). Gaussian FP distributions with mean 0.5-2.1 s (9 levels) x SD 25-200 ms (8 levels). FP range 0.26-2.5 s. Columns `FP, FPrt, targetRT, FPAcc` (premature response during FP flagged by FPAcc = 0; 522 trials), `trialType`, `distMean`, `distSD`.
  - **E3:** 8 participants, 29,373 trials. Tab-delimited, no header: trial, FP, response type (hand/foot), stimulus intensity (low/high), response (-1 none), RT. FP 0.79-2.0 s (mean 1.25). 9.8% of RTs < 0.1 s, including negatives (anticipations). Stimulus modality not stated in the readme [U]; check the preprint.
- Relevance: (i) **high.** Gaussian FP distributions with means up to 2.1 s and SD 25-200 ms (E2) mimic a starter's hold distribution (Otsuka: mean 1.78 s, SD 0.158 s). (ii) trial order preserved, so sequential effects and belief updating can be estimated. (iii) **Best available for anticipations and sub-100 ms responses vs FP** (E1, E3), with ready-made Stan models of the RT/anticipation trade-off. Caveat: visual targets in E1/E2 and keypress responses.

### A2. Otsuka, Kurihara & Isaka 2017: championship FP distribution (83 races) [V-FT], **no per-race data released**
- Paper: Front Psychol 8:810, doi:10.3389/fpsyg.2017.00810, PMC5435752 (CC BY). Full text read 2026-09-28.
- Verified text: "a total of 88 male and female large-scale 100-m races over the last 5 years were recorded from publicly available television broadcasts. The competitions included the 2012 Olympics and the World Championships in 2011, 2013, and 2015 ... from heats to finals. The races whose set and start signal could be clearly heard without the voice of the announcer were analyzed, for a total of 83 races ... analyzed by intervals of 10 ms using sound editing software (EDIUS Neo 3) ... Onsets of the starter's set and gun signals were visually determined by sound wave information." Result: "FP length ... was 1.780 ± 0.017 s (SD: 0.158 s)". Figure 1 is a histogram with a normal curve.
- No supplement and no data availability statement (grep of full text finds neither). The histogram could be digitized to get binned counts as an external benchmark for our own FP distribution (WCH 2011/13/15, OG 2012).
- Lab arm: 20 male sprinters, FPs of mean ±1 and ±2 SD (1.465 / 1.622 / 1.780 / 1.938 / 2.096 s), randomized. Warning tone 70 dB; imperative tone 120 dB from a trumpet horn ~30 cm from the ear. **One trial per condition.** Whole-body RT 156 / 133 / 125 / 129 / 117 ms (SS to LL).
- Relevance: the direct methodological precedent for broadcast-audio FP measurement (manual, waveform-based, 10 ms resolution, 83/88 = 94% of races usable), and an external validation target (mean 1.780, SD 0.158 s).

### A3. Dalmaijer, Nijenhuis & Van der Stigchel 2015: speed skating ready-start intervals [V-FT], **no open data**
- Paper: "Life is unfair, and so are racing sports: some athletes can randomly benefit from alerting effects due to inconsistent starting procedures." Front Psychol 6:1618, doi:10.3389/fpsyg.2015.01618 (CC BY). Also a 2016 Commentary: doi:10.3389/fpsyg.2016.00119.
- 500 m speed skating, Vancouver 2010. 148 races, of which 3 were excluded for falls. Verbatim: "(3 out of 148 individual races)". Interval = onset of "Ready?" to onset of the shot, from TV-broadcast audio, inspected visually in Audacity. Reported: 5% (men) and 27% (women) of finishing-time variance explained; +1 s interval → +299 ms (men) / +672 ms (women) finishing time. False starts in 6 men's and 2 women's races.
- No data availability statement or repository link: a grep of the full-text HTML (curl, 2026-09-29) finds no data statement and no osf/github link [V-FT]. Closest cross-sport analogue for a methods and prior-art comparison. Could request the data from the authors (Dalmaijer usually shares code on GitHub; not checked).

### B2. Visalli, Capizzi, Ambrosini, Kopp & Vallesi 2021: "FPbayes" Gaussian-FP belief-updating task [V-FT]
- Paper: "Electroencephalographic correlates of temporal Bayesian belief updating and surprise", NeuroImage (2021), doi:10.1016/j.neuroimage.2021.117867 (Crossref-confirmed). Companion paper: Visalli, Capizzi, Ambrosini, Mazzonetto & Vallesi 2019, "Bayesian modeling of temporal expectations in the human brain", NeuroImage, doi:10.1016/j.neuroimage.2019.116097.
- OSF: https://osf.io/ckqa5/ (created 2020-04-01; **No licence shown (OSF API license: null)**). Child component: sdy8j, "P3-like signatures of temporal predictions: a computational EEG study" (preprint osf.io/78gm6).
- Files:
  - `behavioral_analysis/FPbayes_behav_ALL.csv` (3.73 MB; https://osf.io/download/r93fg/). Columns: id, run, block, trialType, distMean, distSD, trial, FP, FPrt, targetRT, FPAcc, targetAcc, ztr, rt, logrt, ..., DKL (Bayesian surprise), IS (information surprise).
  - Raw per-participant CSVs: the `datasets/` folder listing returned an OSF 502 error.
  - `bayesian_model/`: MATLAB Bayesian observer, with generative Gaussian mean/SD vectors.
  - Raw EEG plus ICA.
  - `task.zip` (0.04 MB): the task script.
- Design (from the readme and the data):
  - FP is drawn from **Gaussian generative distributions**: mean 0.5-2.1 s (9 levels) x SD 25-200 ms (8 levels), changing across blocks.
  - Trial types, signalled by colour: "update" (7: FP drawn from a new distribution), "uniform" (0), "predictable" (1).
  - Every participant saw the same trial sequence.
  - Premature responses during the FP are flagged (FPAcc).
  - 27 participant files, also redistributed as Yarrow E2.
- Relevance:
  - (i) **The best lab analogue of a starter-specific, roughly Gaussian hold distribution.** The sprint hold (mean ~1.78 s, SD ~0.16 s) sits inside the design grid.
  - (ii) Trial-level learning and updating, so a "starter-specific belief" model can be tested.
  - (iii) Premature-response flags.
  - Caveats: visual task [U, check the paper]; choice vs simple RT [U].

### B3. Salet, Kruijne, van Rijn, Los & Meeter 2022: fMTP supplement [V-FT] (**high priority**)
- Paper: Psychological Review 129(5):911-948, doi:10.1037/rev0000356 (PMID 35420847). Verified abstract sentence: "In a critical experiment using a **Gaussian distribution of foreperiods**, we show the data to be consistent with fMTP's predictions and to deviate from the hazard function."
- OSF: https://osf.io/eu7sd/ (**No licence shown (OSF API license: null)**). README verified.
- Trial-level experiment data:
  - `experiment/exp1clock.csv`: 11.0 MB; 20 participants; 13,120 rows.
  - `exp1noclock.csv`: 12.1 MB; 22 participants; 14,432 rows.
  - `exp2standardFP.csv`: 11.3 MB; 21 participants; 13,776 rows; E-Prime export with `SOA` and **`SOAn-1`** (previous FP) columns.
  - The OpenSesame files have `fp`, `catch`, `response_time`, `correct`, plus a `Clock` manipulation (visible clock vs none).
- **FP design, verified from the data:** 1.30 / 1.95 / 2.60 s with the mode at 1.95 s (trial ratio about 1 : 4.8 : 1), plus catch trials coded at 3.25 s (~12.5% of trials). This peaked, Gaussian-like distribution covers almost exactly the sprint hold range.
- Mean RT by FP:
  - My quick pass over all trials: exp1clock 399 / 339 / 348 ms; exp1noclock 413 / 360 / 356 ms.
  - Their summary file `replication_trillenberg.csv`: Standard_FP 362 / 330 / 329 ms.
  - So RT falls to the mode, then flattens (slight rise in the clock condition).
- Catch-trial false alarms: 47/1,680 (2.8%, clock) and 93/1,848 (5.0%, no clock). This is my count of catch rows with a response; verify the coding before citing.
- `model_code/`:
  - Python for fMTP, hazard and subjective-hazard models (`hazard.py`; `get_phi_sub_hz.py` for the Weber-fraction kernel).
  - A tutorial notebook.
  - **Digitized classic datasets** in `model_code/empirical_data/`:
    - `niemi1979.csv`: RT at FP 0.5-3.0 s, dimmed vs bright stimulus.
    - `trillenberg2000.csv`: **aging (uniform) vs Gaussian vs non-aging distributions at FP 1.3 / 1.95 / 2.6 s.** GAUSS 337 / 274 / 290 ms (late-FP rebound); AGE 339 / 305 / 302; N_AGE 297 / 291 / 294.
    - `los2013.csv`: go/no-go x previous FP.
    - `losheuvel_dist.csv` and `losheuvel_seq.csv`: Los & van den Heuvel 2001.
    - `steinborn2012.csv`: second-order sequential effects.
    - `seq_effects.csv` and `sub_avg.csv`: exp / anti-exp / uniform groups x FP x FPn-1 over 0.4-1.6 s. This looks like the Los, Kruijne & Meeter 2017 "Hazard versus history" data. `sub_avg` has 2,048 subject-level rows.
    - `transfer.csv`.
- Relevance:
  - (i) **High.** A lab Gaussian-FP curve at 1.3-2.6 s can be overlaid directly on sprint RT-by-hold. The Trillenberg rebound at 2.6 s vs Salet's flat replication is an open question that sprint data can inform.
  - (ii) The previous-FP columns support estimates of sequential effects.
  - (iii) Catch trials give false-alarm rates.
  - The hazard, subjective-hazard and fMTP code is ready to use: **fit the same models to the sprint data.**
  - Caveats: choice RT (there is an arrow-direction column); visual targets [U]; no licence, so cite and re-derive rather than redistribute.

### B4. Houshmand Chatroudi, Mioni & Yotsumoto 2024: "On the nonlinearity of the foreperiod effect" [V-FT files; V-ABS findings]
- Paper: Sci Rep 14:2780, doi:10.1038/s41598-024-53347-y (CC BY). Author Correction: doi:10.1038/s41598-025-94097-9. Verified abstract: n = 109; linear fits were poor and **a 3-parameter exponential-decay fit was best**, justified by Weber-fraction time uncertainty.
- OSF: https://osf.io/km27b/ (**No licence shown (OSF API license: null)**). Both files are downloaded to the scratchpad (`ds_chatroudi_*.xlsx`):
  - `Material/datasetLab.xlsx`: 0.49 MB; 12,432 trials; columns Experimenter, Gender, Age, Education, SoggID, ForeperiodDuration, RT.
  - `datasetOnline.xlsx`: 0.31 MB; 6,720 trials; adds Block and **TrialOrder**.
  - Also R analyzers and MATLAB figure scripts.
- Design: FP 0.48-1.92 s in 0.24 s steps (7 levels; presumably uniform). Modality [U].
- Relevance:
  - (i) A benchmark for curve shape: fit their exponential-decay model to sprint RT vs hold and compare the parameters.
  - (ii) The online set has TrialOrder, so sequential effects can be estimated.
  - (iii) RTs only; no anticipation coding seen.

### B5. PVT (psychomotor vigilance) datasets with trial-level ISI [V-FT files]
In PVT work, a "false start" is conventionally an RT < 100 ms.
- **Welhaf et al., "Individual Differences in Working Memory Capacity and Temporal Preparation":** https://osf.io/cnsf5/ (2023; **No licence shown (OSF API license: null)**).
  - `Data/R&U2020_E1_PVTraw.csv` (2.71 MB): 161 participants; 13,891 rows (12,603 real trials); `waittime` = ISI 1-10 s in uniform steps; `EndFlash.RT`.
  - Also `Data/Robison2020PVT.txt` (52 MB), `PVT.csv` (24 MB), WMC `.sav` files, and an Rmd, "WMC & Foreperiod Effects".
- **Welhaf, "Age Differences in Implicit Temporal Preparation":** https://osf.io/zmqxf/ (2025; **No licence shown (OSF API license: null)**).
  - `PVT.csv` (23.8 MB; Gorilla export).
  - `Maybrier_PVT.csv` (0.27 MB): 80 participants; 6,346 trials; columns sub, block, trial, **ISI** (1.0-10.0 s), ISIbin, rt, type. 1.1% of RTs are < 100 ms.
- Relevance:
  - (iii) **A large-N cross-domain comparison of the "false start" (RT < 100 ms) rate vs FP/ISI.** PVT work uses the same 100 ms cut-off as athletics (Basner & Dinges convention [U]).
  - (i) Weak: the ISIs (1-10 s) are much longer than sprint holds, and the stimulus is visual.
- Also noted, not inspected in depth: https://osf.io/yujw6/ (CC BY 4.0), "Pupillometry and the vigilance decrement", which includes a psychomotor-vigilance experiment (visual).

### B6. StartReact composite IPD: Sadler, Peters, Santangelo, Maslovat & Carlsen 2022 [V-FT files; V-ABS findings]
**Relevant to legitimate sub-100 ms responses to loud go signals.**
- Paper: Behav Brain Res 426:113839, doi:10.1016/j.bbr.2022.113839 (PMID 35306096). Composite individual-participant data from 25 datasets (2006-2019). Control RT was longer in females (p = .017); **there was no sex difference under a startling acoustic stimulus (SAS).**
- OSF: https://osf.io/cu2er/ (**No licence shown (OSF API license: null)**).
  - `data_file.csv` (0.06 MB; 818 rows = participant x condition means). Columns: Study, SubStudy, Article, UniqSubject, Age, Sex, Condition (Control/SAS), Stimulus (e.g. "Auditory 82 dB", "Tone 124 dB", "White noise 120 dB"), RT (s), PropSCM.
  - Plus an R script.
- My quick summary:
  - Control mean RT: F 0.147 s, M 0.141 s (min 0.079).
  - SAS mean RT: 0.085 s for both sexes (min 0.052).
  - **82.6% of participant-mean SAS RTs are < 0.100 s**, and so are 9.3% of control means.
  - RT is probably EMG-onset premotor RT [U]; check each article.
- Relevance: (iii) this calibrates how far below 100 ms a *prepared* response can legitimately go when the go signal is ~120 dB. A start gun played through speakers behind the blocks is loud. Pairs with Brown et al. 2008 ("Go" signal intensity and the sprint start).
- Related paper, no data: Leow, Uchida, Egberts, Riek, Lipp, Tresilian & Marinovic 2018, Neuroscience, doi:10.1016/j.neuroscience.2018.10.008 (mini meta-analysis). It finds that **foreperiod variability confounds startle-trial RT effects**, and that foreperiod predictability shifts RT to intense acoustic stimuli. Repository copy: Curtin figshare 31689346 (all rights reserved).

### B7. TEP-Task: "Unifying temporal preparation: The temporal preparation task" [V-FT listing; V-ABS paper]
- Published version: Capizzi, Attout, Mioni & Charras (2026), Behavior Research Methods 58:52, doi:10.3758/s13428-025-02908-8 (Crossref-confirmed). Preprint: doi:10.31234/osf.io/xdp9s_v2; licence string "CC-By Attribution 4.0 International".
- Data: https://osf.io/rnc4v/ (**No licence shown (OSF API license: null)**).
  - 109 + 65 + 44 participants (sessions 1-2); raw xlsx files (13.8 MB and 6.1 MB).
  - Cleaned CSVs for the **FP effect (FPED)**, the **sequential effect (SQED)**, and temporal orienting (visual TOEXVIS and **auditory TOEXAUD**).
  - Hierarchical Bayesian model fits and test-retest ICCs.
- Relevance: (ii) the test-retest reliability of individual FP and sequential effects bears on whether an athlete's FP sensitivity is a stable trait (useful as a modelling prior). Medium.

### B8. Other lab items checked
- **Crowe, Los, Schindler & Kent 2021**, QJEP 74(8):1432-1438, doi:10.1177/1747021821995452 (PMC8261779). **Auditory** warning and go tones through headphones at ~50 dB. FPs 0.4 / 0.8 / 1.2 / 1.6 s, with an exponential (8:4:2:1) or anti-exponential (1:2:4:8) acquisition phase, then a uniform transfer phase. **Exp 2 is simple RT with an unfilled (silent) FP, the closest procedural match to "set" → silence → gun.** The PMC full text has no data availability statement [V-FT; grep for "data availab", "OSF", "repository" found none]. Methods lines [V-FT]: "Foreperiod interval (400, 800, 1,200, 1,600 ms)"; "The ratio of foreperiods was 8: 4: 2: 1 ... in the exponential condition, and 1: 2: 4: 8 ... in the anti-exponential condition". The OSF registrations 7fbzn, mqb42 and 5zd9m hold protocols only, no data.
- **Huang & Chao 2025**, PLOS Biol, "Human brain integrates both unconditional and conditional timing statistics to guide expectation and behavior", doi:10.1371/journal.pbio.3003459. Data: https://doi.org/10.17605/OSF.IO/VEDHP (verified statement: "raw data ... publicly available"). FP1 → FP2 sequence paradigm contrasting unconditional and conditional hazard, with blurred PDF/HF files and false-alarm counts. Mostly MEG/EEG (head models are 300-440 MB each); the behaviour is in `figures_tables/*.xlsx`. Relevance (ii), conditional (sequential) hazard: medium.
- **Implicit temporal expectation & mind wandering**: https://osf.io/w7bv8/ (Cognition 2020, doi:10.1016/j.cognition.2020.104242). Experiment 1 and 2 data components; variable-FP design; not inspected further.
- **"Implicitly learning when to be ready: from instances to categories"** (PBR brief report; preprint CC BY): data node https://osf.io/s7xp6/ (ProjectTemplate layout). Low relevance.
- **Developmental temporal expectation (2026)**: https://osf.io/zfwu5/. `cleaned_data/all_studies_cleaned.csv` (0.76 MB): several studies, children vs adults, FP duration x previous FP. Low.
- **Butler, Ngabo & Missal 2019**, "Time after time: support for memory accounts of temporal preparation" (PsyArXiv 5t8b7; "No license"). No data link. Low.
- **Tavano, Schröger & Kotz 2019**, PLOS ONE, doi:10.1371/journal.pone.0222420, "Beta power encodes contextual estimates of temporal event probability in the human brain". See B9 for its data status.
- **Han & Proctor 2022**, J Cognition, doi:10.5334/joc.235, "Change of variable-foreperiod effects within an experiment: a Bayesian modeling approach". See B9 for its data status.

### B9. Grabenhorst, Poeppel & Michalareas: Set-Go RT curves in **audition** and vision [V-FT] (**high priority for cross-domain curves**)
- **2026 PNAS dataset.** "The anticipation of imminent events is time-scale invariant", PNAS 123(2):e2518982123, doi:10.1073/pnas.2518982123 (PMC12799109).
  - Data: Edmond (MPG Dataverse), doi:10.17617/3.MEAGMS. **Licence string on the repository: "CC0 1.0".** One file, `data_2025_18982.mat` (0.02 MB; file id 333801; https://edmond.mpg.de/api/access/datafile/333801). Downloaded to the scratchpad (`ds_grab2025.mat`).
  - Verified content: variable `RTGTMat`, shape (13, 15, 3, 3, 2). The repository description reads: "13 participants x 15 Go times x 3 time spans (short, medium, long) x 3 Go time distribution conditions (uniform, exponential, flipped exponential) x 2 sensory modalities (audition, vision). The data comprise mean RT, averaged within-participant, within Go time." RT range 0.139-0.709 s.
  - Design, from the methods text [V-FT]: "The time between Set and Go, the Go time, was drawn from truncated uniform, exponential, and flipped exponential distributions. Each distribution was defined over three Go-time spans of different duration, ∆t = (1, 1.7, 2.4) s, each beginning at t = 0.4 s." "In 9.09 % of trials, no Go cue was presented" (catch trials). "RT = (0.05, 0.75) s" was the inclusion window, so RT < 0.05 s were excluded as early guesses. The **long span covers 0.4-2.8 s, which includes the sprint hold range**; the auditory condition matches the sprint go signal's modality.
  - Finding [V-ABS]: RT tracks the event **probability density function (PDF)**, not the hazard rate, and anticipation precision is scale invariant ("contradicts Weber's law").
- **2021 PNAS dataset.** "Two sources of uncertainty independently modulate temporal expectancy", PNAS 118(16):e2019342118, doi:10.1073/pnas.2019342118 (PMC8072397).
  - PMC data statement [V-FT]: "Anonymized RT data have been deposited in Edmond". The old imeji link now redirects. Current record: doi:10.17617/3.YC3SGA, "dataPNAS202019342". **Licence string: "CC BY-SA 4.0".** One file, `dataPNAS202019342.mat` (6 KB); variable `data`, shape (25, 32), values 0.18-1.43 [V-FT]. The structure is not documented on the record; it probably holds participant-level mean RT per condition and needs the paper's SI to decode [U].
  - Finding [V-ABS]: "the HR fails to account for behavior", and a PDF-based expectancy model is proposed; results hold in vision and audition.
- **2025 Nat Commun (MEG).** "Neural signatures of temporal anticipation in human cortex represent event probability density", Nat Commun 16:2602, doi:10.1038/s41467-025-57813-7.
  - Data statement [V-FT]: "The reaction time data used in the modeling are provided in this paper (Supplementary Data 1)". MEG and eye-tracking data are "will be made publicly available upon project completion".
  - Set-Go task in audition and vision; Go times from truncated exponential or flipped exponential distributions.
- **2019 Nat Commun.** "The anticipation of events in time", doi:10.1038/s41467-019-13849-0. Data statement [V-FT]: "available from the corresponding author upon reasonable request". **Not open.**
- Relevance:
  - (i) **Best open auditory Set-Go curves over a span that includes 1.3-2.5 s, in a paradigm that literally uses a "Set" cue.** The 15 Go times give a smooth curve.
  - The PDF-vs-hazard contrast is exactly the model comparison proposed for the sprint data (novelty candidate b).
  - (iii) No anticipation rates (only means, with early guesses excluded).
  - Low effort: tiny .mat files, CC0 or CC BY-SA.

### A4. World Athletics results pages: per-heat Seiko **"Waveform"** JPGs (Ready Time + per-lane RT + force traces) [V-FT]
Found by the RT data pipeline; coverage probed here on request. Tiny probes only: each competition's results page JSON (`eventPhaseDocuments`, `typeName`) was fetched on 2026-09-28/29.
- **What the JPG shows**, read from `wf_oregon_110h_f.jpg`, a Seiko waveform for WCH 2022 M 110 mH final, "Heat : 001 Attempt : 002 Ready Time : 1.854 sec":
  - one panel per lane, with a force trace from -2.0 to +1.0 s around the gun (0.0);
  - the RT printed per lane (e.g. "0.108 sec (Quickest)"), with a red marker at the detected onset;
  - a magenta vertical line at about -1.85 s, matching the Ready Time;
  - lanes of disqualified athletes are blank (Devon Allen, lane 3, was DQ'd in attempt 001).
  - **Inference, not verified:** "Ready Time" is the set→gun interval (foreperiod), because the magenta marker sits at -Ready Time. Seiko's own definition has not been found.
  - "Attempt" counts starts (002 = the restart after a false start). Only one JPG per heat is listed, so recalled first attempts are probably not published [U].
- File URL pattern (200 OK, image/jpeg, ~465 KB): `https://media.aws.iaaf.org/competitiondocuments/waveform/<compId>/<SEX>_<EVENT>_<phase>_<heat>.jpg`, e.g. `.../waveform/7190593/M_100_f_1.jpg`.

| Competition | Comp ID | Timing | Waveform JPGs? | Probed |
|---|---|---|---|---|
| WCH Berlin 2009 | 6998524 | Seiko | **No** (SL2/RS1/Photofinish only) | M 100 F |
| WCH Daegu 2011 | 7003367 | Seiko | **No** | M 100 F |
| WCH Moscow 2013 | 7003368 | Seiko | **No** | M 100 F |
| WCH Beijing 2015 | 7078726 | Seiko | **No** | M 100 F |
| WCH London 2017 | 7093740 | Seiko | **No** | M 100 F |
| WCH Doha 2019 | 7125365 | Seiko | **No** ("Race Analysis" RS5 PDFs exist) | M 100 F, M 100 H |
| WCH Oregon 2022 | 7137279 | Seiko | **Yes, every heat** | M 100 F, W 100 H, M 110H F |
| WCH Budapest 2023 | 7138987 | Seiko | **Yes, every heat** (also "Officiating Video Clip" MP4s) | M 100 F, M 110H H |
| WCH Tokyo 2025 | 7190593 | Seiko | **Yes, every heat** incl. preliminary round, W 100H, M 200 | M 100 F/H/PR, W 100H H, M 200 H |
| WIC Belgrade 2022 | 7138985 | ? | **No** | M 60 F |
| WIC Glasgow 2024 | 7180312 | ? | **Yes** (final + every heat) | M 60 F/H |
| WIC Nanjing 2025 | 7136586 | ? | **Yes** | M 60 F |
| WIC Kujawy Pomorze (Toruń) 2026 | ? | ? | not probed (slug not resolved) | - |
| OG Tokyo 2020 | 7132391 | Omega | **No documents listed at all** | M 100 F |
| OG Paris 2024 | 7153115 | Omega | **No documents listed at all** | M 100 F |
| DL Zurich 2025 | 7199686 | ? | none found (calendar page has no documents; competitions-path probe 404) | M 100 F |

- Relevance: **the highest-value sports dataset found.** It gives an official hold time per race (no audio measurement needed) plus per-athlete RT and force-onset traces, for WCH 2022, 2023 and 2025 (roughly 65-70 races per championship across the 100/200 m and sprint hurdles, men and women, all rounds) and WIC 2024/2025 (60 m, 60 mH; ~40 races each). My rough total is ~250-300 JPGs, estimated from heat counts, not enumerated. It turns the broadcast-audio method (novelty a) into a validation target: audio FP vs Seiko Ready Time on the same heats. The earlier years (2009-2019) and the Olympics have no waveforms, so audio measurement is the only route there. That split is a natural design: Seiko 2022-25 as ground truth, audio extending coverage back to 2009 plus the Olympics.
- Caveats:
  - The definition of Ready Time (from "set" command onset? from starter arm/button?) is unverified.
  - WA terms of use apply. Publish derived numbers plus URLs; do not re-host the JPGs.
  - The force-trace onset rule (the Seiko threshold) is not documented on the image.

### B10. Herbst, Fiedler & Obleser 2018: **auditory** targets, FP distributions centred on 1.8 s with graded spread [V-FT] (**strong cross-domain analogue**)
- Paper: "Tracking temporal hazard in the human electroencephalogram using a forward encoding model", eNeuro 5(2), doi:10.1523/ENEURO.0017-18.2018 (PMC5938715). PMC statement [V-FT]: "The data and custom-written analyses scripts are available at the Open Science Framework: https://osf.io/qbhma/". It re-analyses Experiment II of Herbst & Obleser (2017).
- OSF: https://osf.io/qbhma/. **Licence string: "CC-By Attribution 4.0 International"** (node_license year 2018).
- Behavioural file: `Data/Behavioural/DATA_DisTime_EEGII_24sbs.txt` (0.96 MB; https://osf.io/download/vkxen/), tab-delimited. Columns [V-FT]: `sbname, Rep.type, Rep.corr, Rep.RT, Rep.conf, DurTrial, Rep.dur, cond, FPst, FP, ToneFreq, ISI, trial, iblock`.
- Contents: 24 participants, 13,104 trials. **FP 0.5-3.1 s, mean 1.8 s in every condition.** Six conditions (1-6) differ in spread:
  - SD 0.78 s (cond 1/4, broad);
  - SD 0.42 s with IQR 1.69-1.91 s (cond 2/5);
  - FP mostly exactly 1.8 s (cond 3/6).
  - `FPst` takes 0.05 / 0.15 / 0.95, which I read as a predictability parameter [U].
  - The target is a tone (`ToneFreq`), and the task is pitch discrimination, i.e. choice RT with accuracy and confidence.
  - Also: raw EEG (~0.5 GB per participant, large) and R scripts, including `02_ResponseTimes_HazardFunctions.R`.
- Relevance:
  - (i) **An auditory go stimulus, with the FP distribution centred at 1.8 s (sprint mean hold ≈ 1.78 s, Otsuka 2017) and a graded spread.** This is a direct lab model of *starter consistency* (narrow vs wide hold distributions).
  - (ii) Trial order is available.
  - (iii) No anticipation coding (choice task).
  - Caveats: choice RT, not simple RT; responses via a button box.

### B11. Han & Proctor 2022 (J Cognition): two-FP designs, trial-level [V-FT]
- Paper: "Change of Variable-Foreperiod Effects within an Experiment: A Bayesian Modeling Approach", J Cognition 5(1):40 (Crossref-confirmed), doi:10.5334/joc.235 (PMC9400609). PMC statement [V-FT]: "The trial-level data of the four experiments and the codes for the modeling process in the current study are available on OSF ... https://osf.io/um34f/?view_only=a3a7d05f2798445885eb2b88a795640f".
- The node is private (API 404) but reachable with the view-only key. **Licence: none shown** (view-only link).
- Files: `Raw Data (MS E1..E4).csv` (0.38-0.84 MB each) and `Bayesian Modeling.R`. Columns [V-FT]: `Subject, Block, Trial, FP, Sequence, RT`.
  - E1: FP ∈ {400, 1400} ms, 75 participants, 18,562 trials.
  - E2: FP ∈ {50, 200} ms, 126 participants, 31,093 trials.
  - E3 and E4 not inspected.
- Relevance: (ii) clean FPn-1 x FPn sequential-effect estimates with large N, and a Bayesian model of how the FP effect changes within a session (a "fatigue/learning across heats" analogue). (i) Low: short FPs, two-point distributions.

### A5. Mirshams Shahshahani 2018: Olympic sprint RT, all heats, 2004-2016 (Deep Blue Data) [V-ABS via DataCite metadata; files not opened]
- DataCite: doi:10.7302/z20v8b11, "Downloaded IAAF Sprint Results in all Heats for 2004 - 2016 Olympics for both Men and Women". Creator: Mirshams Shahshahani, Payam. University of Michigan, 2018. **Rights: CC0** (rightsUri http://creativecommons.org/publicdomain/zero/1.0/). Landing page: https://deepblue.lib.umich.edu/data/concern/data_sets/cr56n184r.
- **Deep Blue returns HTTP 403 to scripted requests, so files and sizes were not verified; download manually in a browser.**
- Metadata technical info [V-ABS]: "1- The results of 100 m, 100 m Hurdles, and 110 m Hurdles sprints were copied for 2004 - 2016 Olympics for all the Heats for both Men and Women. 2- The results of all the sprints shorter the 800 m were copied for 2008 - 2016 Olympics for all the Heats". Two Excel sheets plus a documentation file (file sets 2v23vv06j, 9s161685j, qn59q4716).
- IsReferencedBy: doi:10.1371/journal.pone.0198633 (Mirshams Shahshahani, Lipps, Galecki & Ashton-Miller 2018, PLOS ONE, "On the apparent decrease in Olympic sprinter reaction times").
- Relevance: **fills the Olympics gap** (Omega timing: OG 2004, 2008, 2012, 2016), complementing Fiore's WCH/Seiko data. It enables a vendor/meet comparison of RT distributions and sub-0.100 tails. No FP: hold times for the OG must come from broadcast audio.

### A6. World Athletics / Leeds Beckett biomechanics reports [V-FT for one report]
- 38 event reports for WCH London 2017 (press release: https://worldathletics.org/news/press-release/2017-world-championships-athletics-biomechani), plus WIC Birmingham 2018 reports. Example checked: "Biomechanical Report for the World Indoor Championships 2018: 60 Metres Women" (49 pp; https://worldathletics.org/download/download?filename=1062c381-6278-484f-bfaa-df42f4ab70f9.pdf...).
- Verified in the text: finals only (8 athletes). Temporal and kinematic "set position" and block-phase variables. "Total block time ... Calculated as official reaction time (provided by Seiko) + total push time". **No hold time or set-to-gun interval reported** (no matches for "hold", "set command" or "starter" in that sense).
- The report's discussion section has useful historical notes for the lit review, citing Young 2001: detection threshold "set at 30kg at the Munich 1972 Olympic Games"; later "27kg in Los Angeles 1984". A 0.099 s or faster RT "automatically induces an acoustic signal to recall the athletes".
- Relevance: low for FP (finals only, no hold time). Useful for set-position kinematics and for the timing-system history.

### A7. Other sports sources noted
- **WA results pages and PDFs (all championships):** per-athlete RT, lane, heat. DQs carry rule codes (TR16.8, formerly 162.7). **Lists of false-start DQs can be derived from the results** (Fiore's data contains codes such as `DR162.7`). No curated open DQ list was found.
- **Swimming:** Kaggle "Olympic Swimming Results 2016-2024" (https://www.kaggle.com/datasets/batuhansalman/olympic-swimming-results-2016-2024) could not be inspected: Kaggle renders client-side, so columns and licence are unverified [U]. Omega/World Aquatics result PDFs typically print a per-swimmer RT column [U, not checked this session]. No open dataset of "take your marks" hold times was found.
- **Kaggle athletics databases** (e.g. "World Athletics Database", https://www.kaggle.com/datasets/mexwell/world-athletics-database, 13 CSVs, 394 MB per the search snippet [U]). These are rankings and results, not RT. Low.
- **JAAF biomechanics reports** (Japanese national projects): not checked [U].
- **Haugen, Shalfawi & Tønnessen 2013:** the Taylor & Francis supplementary-material page returned HTTP 403, so whether supplementary data exist is unknown [U]. No public dataset of their 267 TV-measured holding times is known.

## Key points for the literature review (not only datasets)
1. **Seiko waveform JPGs (A4)** give an official per-heat "Ready Time" (most likely set→gun; inferred), per-lane RT and force traces. They exist only for WCH 2022, 2023 and 2025 and WIC 2024 and 2025. WCH 2009-2019, WIC 2022 and the Olympics (2020, 2024) have none. This changes novelty (a): the audio method becomes a *validated extension* to years and meets without waveforms, with Seiko as ground truth.
2. **Closest related work found:** Yarrow et al. 2026 (PsyArXiv 69xvk; B1). A lab model of how beliefs about the FP distribution drive simple RT *and anticipatory errors*. Its abstract opens with the set→go sprint example, but it uses no sport data. Position our paper against it.
3. **PDF-vs-hazard debate:** Grabenhorst et al. (2019 Nat Commun; 2021 PNAS; 2025 Nat Commun; 2026 PNAS) argue that RT tracks the event PDF, not the hazard. Salet et al. 2022 (fMTP) show a Gaussian FP distribution at 1.3/1.95/2.6 s deviating from hazard predictions. Both have open data in the sprint FP range (B3, B9), so the same model comparison can be run on sprint data.
4. **Superseded preprint:** Fiore, Schifano & Yan's arXiv 2506.11460 is published as *The American Statistician* 79(4):500-507 (2025), doi:10.1080/00031305.2025.2515869 [V-ABS: Crossref metadata]. Cite the journal version.
5. **Olympic RTs 2004-2016 (Omega):** Deep Blue Data, CC0, doi:10.7302/z20v8b11 (A5), linked to Mirshams Shahshahani et al. 2018 PLOS ONE.
6. **FP distribution benchmarks:**
   - Otsuka 2017: 83 championship races (WCH 2011/13/15, OG 2012), mean 1.780 s, SD 0.158 s, measured from TV audio at 10 ms resolution; no per-race data (A2).
   - Dalmaijer et al. 2015: speed skating, 148 races, TV audio in Audacity, longer ready-start interval → slower times; no data (A3).
   - Haugen 2013's 267 TV-measured holds are not public.
7. **Lab analogue of starter consistency:** Herbst et al. 2018 (B10) used auditory targets with FP distributions all centred on 1.8 s and graded spread (CC BY 4.0).

## Top 5 to use
1. **WA Seiko Waveform JPGs, WCH 2022/2023/2025 + WIC 2024/2025 (A4).**
   - What it enables: the core sprint analysis on official data. RT vs Ready Time per athlete (mixed model with athlete, heat and starter/session effects); the sub-0.100 s tail as a function of FP; within-session sequential effects; empirical starter FP distributions, which feed hazard vs PDF vs fMTP predictors.
   - It also gives **ground truth for validating the broadcast-audio FP pipeline** (Bland-Altman agreement of audio FP vs Ready Time on the same heats).
   - Effort: medium. Roughly 250-300 JPGs (estimated) need OCR of the header and lane RTs (the data pipeline is on it). Ready Time's exact definition should be confirmed (Seiko documentation, or cross-check against the audio "set" onset on a few heats).
2. **Grabenhorst, Poeppel & Michalareas 2026 Set-Go data (Edmond, CC0 1.0; B9).**
   - What it enables: overlay auditory and visual lab RT-by-Go-time curves (Go times 0.4-2.8 s; uniform, exponential and flipped-exponential distributions; 13 participants x 15 Go times) on the sprint RT-by-hold curve. Fit identical PDF-based and hazard-based predictors to both. Report sprint vs lab slopes in ms per 100 ms of FP, with bootstrap CIs.
   - Effort: very low (a 23 KB .mat file; about 1 h).
3. **Salet et al. 2022 fMTP supplement (OSF eu7sd; no licence shown; B3).**
   - What it enables: trial-level data with a **Gaussian-like FP distribution at 1.30/1.95/2.60 s plus catch trials**, previous-FP columns, and ready-to-run Python for hazard, subjective hazard (Weber-fraction blur) and fMTP. Digitized Trillenberg 2000 data compare aging vs Gaussian vs non-aging distributions at the same three FPs.
   - Run these models on the sprint data unchanged; compare the late-FP rebound (Trillenberg) vs flattening (Salet) with sprint RT at long holds, where Haugen's positive r would fit a rebound.
   - Effort: low to medium (three 11-12 MB CSVs; 2-4 h). Cite; do not redistribute (no licence).
4. **Yarrow et al. 2026 data and code (City figshare, CC BY 4.0; B1).** Includes Visalli et al.'s Gaussian-FP data as E2.
   - What it enables: trial-level anticipations (RT < 0 and < 0.100 s) under different FP distributions and anticipation costs, plus Stan models of the RT/anticipation trade-off. Use it to calibrate how the rate of "too early" responses rises with FP and hazard, the lab counterpart of the foreperiod-dependent sub-0.100 s probability (novelty c).
   - E2 has Gaussian FP means up to 2.1 s with SD 25-200 ms, bracketing a starter's hold distribution (SD ~0.16 s).
   - Effort: medium (2 MB zip; R/Stan; 0.5-2 days for a faithful refit, 1-2 h for descriptives).
5. **Historical RT distributions without FP: Fiore `rxntime.csv` (WCH 1999-2023, Seiko; no licence shown; A1) and Mirshams Shahshahani Deep Blue data (OG 2004-2016, Omega; CC0; A5).**
   - What it enables: fit the unconditional RT distribution (e.g. shifted lognormal or ex-Gaussian, left-censored at 0.100 s) to about 2,800 WCH and several thousand OG starts. Compare the sub-0.100 s tail by vendor, meet, sex and round. This gives the prior that the FP-conditional model (from #1) shifts.
   - It also cross-checks the data pipeline's WA scrape.
   - Effort: low (Fiore CSV is ready; the Deep Blue files need a manual browser download because scripts get 403).
- Honourable mentions:
  - Herbst et al. 2018 (B10; auditory, FP centred at 1.8 s, graded spread = starter consistency).
  - Sadler et al. 2022 StartReact composite (B6; legitimate prepared responses to ~120 dB stimuli: 83% of participant means < 0.100 s, likely EMG onset).
  - PVT sets (B5; "false starts" < 100 ms vs ISI, large N).
  - Chatroudi et al. 2024 (B4; exponential-decay curve form).
  - Han & Proctor 2022 (B11; sequential effects).

## BibTeX
All entries fetched 2026-09-29 by DOI content negotiation (curl -H "Accept: application/x-bibtex" https://doi.org/<DOI>). Crossref and DataCite metadata are otherwise as returned; DataCite keys were renamed to readable ones. Check author and title spelling before final use (e.g. curly quotes).

```bibtex
@article{Otsuka_2017, title={Timing of Gun Fire Influences Sprinters’ Multiple Joint Reaction Times of Whole Body in Block Start}, volume={8}, ISSN={1664-1078}, url={http://dx.doi.org/10.3389/fpsyg.2017.00810}, DOI={10.3389/fpsyg.2017.00810}, journal={Frontiers in Psychology}, publisher={Frontiers Media SA}, author={Otsuka, Mitsuo and Kurihara, Toshiyuki and Isaka, Tadao}, year={2017}, month=May }

@article{Dalmaijer_2015, title={Life is unfair, and so are racing sports: some athletes can randomly benefit from alerting effects due to inconsistent starting procedures}, volume={6}, ISSN={1664-1078}, url={http://dx.doi.org/10.3389/fpsyg.2015.01618}, DOI={10.3389/fpsyg.2015.01618}, journal={Frontiers in Psychology}, publisher={Frontiers Media SA}, author={Dalmaijer, Edwin S. and Nijenhuis, Beorn G. and Van der Stigchel, Stefan}, year={2015}, month=Oct }

@article{Dalmaijer_2016, title={Commentary: Life is unfair, and so are racing sports: some athletes can randomly benefit from alerting effects due to inconsistent starting procedures}, volume={7}, ISSN={1664-1078}, url={http://dx.doi.org/10.3389/fpsyg.2016.00119}, DOI={10.3389/fpsyg.2016.00119}, journal={Frontiers in Psychology}, publisher={Frontiers Media SA}, author={Dalmaijer, Edwin S. and Nijenhuis, Beorn G. and Van der Stigchel, Stefan}, year={2016}, month=Feb }

@article{Yarrow_2026, title={How beliefs about the warning-target foreperiod inform temporal preparation to determine simple reaction times}, url={http://dx.doi.org/10.31234/osf.io/69xvk_v1}, DOI={10.31234/osf.io/69xvk_v1}, publisher={Center for Open Science}, author={Yarrow, Kielan and Saurels, Blake William and Arnold, Derek and Tal-Perry, Noam and Solomon, Joshua}, year={2026}, month=Apr }

@misc{Yarrow_2025_data,
doi = {10.25383/CITY.30715439.V1},
url = {https://city.figshare.com/articles/dataset/Data_and_code_accompanying_a_paper_entitled_How_beliefs_about_the_warning-target_foreperiod_inform_temporal_preparation_to_determine_simple_reaction_times_/30715439/1},
author = {Yarrow, Kielan},
keywords = {Sensory processes, perception and performance, Cognition},
title = {Data and code accompanying a paper entitled "How beliefs about the warning-target foreperiod inform temporal preparation to determine simple reaction times"},
publisher = {City, University of London},
year = {2025},
copyright = {Creative Commons Attribution 4.0 International}
}

@article{Visalli_2021, title={Electroencephalographic correlates of temporal Bayesian belief updating and surprise}, volume={231}, ISSN={1053-8119}, url={http://dx.doi.org/10.1016/j.neuroimage.2021.117867}, DOI={10.1016/j.neuroimage.2021.117867}, journal={NeuroImage}, publisher={Elsevier BV}, author={Visalli, Antonino and Capizzi, Mariagrazia and Ambrosini, Ettore and Kopp, Bruno and Vallesi, Antonino}, year={2021}, month=May, pages={117867} }

@article{Visalli_2019, title={Bayesian modeling of temporal expectations in the human brain}, volume={202}, ISSN={1053-8119}, url={http://dx.doi.org/10.1016/j.neuroimage.2019.116097}, DOI={10.1016/j.neuroimage.2019.116097}, journal={NeuroImage}, publisher={Elsevier BV}, author={Visalli, Antonino and Capizzi, Mariagrazia and Ambrosini, Ettore and Mazzonetto, Ilaria and Vallesi, Antonino}, year={2019}, month=Nov, pages={116097} }

@article{Salet_2022, title={FMTP: A unifying computational framework of temporal preparation across time scales.}, volume={129}, ISSN={0033-295X}, url={http://dx.doi.org/10.1037/rev0000356}, DOI={10.1037/rev0000356}, number={5}, journal={Psychological Review}, publisher={American Psychological Association (APA)}, author={Salet, Josh M. and Kruijne, Wouter and van Rijn, Hedderik and Los, Sander A. and Meeter, Martijn}, year={2022}, month=Oct, pages={911–948} }

@article{Houshmand_Chatroudi_2024, title={On the nonlinearity of the foreperiod effect}, volume={14}, ISSN={2045-2322}, url={http://dx.doi.org/10.1038/s41598-024-53347-y}, DOI={10.1038/s41598-024-53347-y}, number={1}, journal={Scientific Reports}, publisher={Springer Science and Business Media LLC}, author={Houshmand Chatroudi, Amirmahmoud and Mioni, Giovanna and Yotsumoto, Yuko}, year={2024}, month=Feb }

@article{Sadler_2022, title={Retrospective composite analysis of StartReact data indicates sex differences in simple reaction time are not attributable to response preparation}, volume={426}, ISSN={0166-4328}, url={http://dx.doi.org/10.1016/j.bbr.2022.113839}, DOI={10.1016/j.bbr.2022.113839}, journal={Behavioural Brain Research}, publisher={Elsevier BV}, author={Sadler, Christin M. and Peters, Kathleen J. and Santangelo, Cassandra M. and Maslovat, Dana and Carlsen, Anthony N.}, year={2022}, month=May, pages={113839} }

@article{Leow_2018, title={Triggering Mechanisms for Motor Actions: The Effects of Expectation on Reaction Times to Intense Acoustic Stimuli}, volume={393}, ISSN={0306-4522}, url={http://dx.doi.org/10.1016/j.neuroscience.2018.10.008}, DOI={10.1016/j.neuroscience.2018.10.008}, journal={Neuroscience}, publisher={Elsevier BV}, author={Leow, Li-Ann and Uchida, Aya and Egberts, Jamie-Lee and Riek, Stephan and Lipp, Ottmar V. and Tresilian, James and Marinovic, Welber}, year={2018}, month=Nov, pages={226–235} }

@article{Capizzi_2026, title={Unifying temporal preparation: The temporal preparation task (TEP-Task)}, volume={58}, ISSN={1554-3528}, url={http://dx.doi.org/10.3758/s13428-025-02908-8}, DOI={10.3758/s13428-025-02908-8}, number={2}, journal={Behavior Research Methods}, publisher={Springer Science and Business Media LLC}, author={Capizzi, Mariagrazia and Attout, Lucie and Mioni, Giovanna and Charras, Pom}, year={2026}, month=Jan }

@article{Crowe_2021, title={Transfer effects in auditory temporal preparation occur using an unfilled but not filled foreperiod}, volume={74}, ISSN={1747-0226}, url={http://dx.doi.org/10.1177/1747021821995452}, DOI={10.1177/1747021821995452}, number={8}, journal={Quarterly Journal of Experimental Psychology}, publisher={SAGE Publications}, author={Crowe, Emily M and Los, Sander A and Schindler, Louise and Kent, Christopher}, year={2021}, month=Feb, pages={1432–1438} }

@article{Huang_2025, title={Human brain integrates both unconditional and conditional timing statistics to guide expectation and behavior}, volume={23}, ISSN={1545-7885}, url={http://dx.doi.org/10.1371/journal.pbio.3003459}, DOI={10.1371/journal.pbio.3003459}, number={10}, journal={PLOS Biology}, publisher={Public Library of Science (PLoS)}, author={Huang, Yiyuan Teresa and Chao, Zenas C.}, editor={de Diego Balaguer, Ruth}, year={2025}, month=Oct, pages={e3003459} }

@article{Grabenhorst_2026, title={The anticipation of imminent events is time-scale invariant}, volume={123}, ISSN={1091-6490}, url={http://dx.doi.org/10.1073/pnas.2518982123}, DOI={10.1073/pnas.2518982123}, number={2}, journal={Proceedings of the National Academy of Sciences}, publisher={National Academy of Sciences}, author={Grabenhorst, Matthias and Poeppel, David and Michalareas, Georgios}, year={2026}, month=Jan }

@article{Grabenhorst_2021, title={Two sources of uncertainty independently modulate temporal expectancy}, volume={118}, ISSN={1091-6490}, url={http://dx.doi.org/10.1073/pnas.2019342118}, DOI={10.1073/pnas.2019342118}, number={16}, journal={Proceedings of the National Academy of Sciences}, publisher={National Academy of Sciences}, author={Grabenhorst, Matthias and Maloney, Laurence T. and Poeppel, David and Michalareas, Georgios}, year={2021}, month=Apr }

@article{Grabenhorst_2025, title={Neural signatures of temporal anticipation in human cortex represent event probability density}, volume={16}, ISSN={2041-1723}, url={http://dx.doi.org/10.1038/s41467-025-57813-7}, DOI={10.1038/s41467-025-57813-7}, number={1}, journal={Nature Communications}, publisher={Springer Science and Business Media LLC}, author={Grabenhorst, Matthias and Poeppel, David and Michalareas, Georgios}, year={2025}, month=Mar }

@article{Grabenhorst_2019, title={The anticipation of events in time}, volume={10}, ISSN={2041-1723}, url={http://dx.doi.org/10.1038/s41467-019-13849-0}, DOI={10.1038/s41467-019-13849-0}, number={1}, journal={Nature Communications}, publisher={Springer Science and Business Media LLC}, author={Grabenhorst, Matthias and Michalareas, Georgios and Maloney, Laurence T. and Poeppel, David}, year={2019}, month=Dec }

@misc{Grabenhorst_2025_data_timescale,
doi = {10.17617/3.MEAGMS},
url = {https://edmond.mpg.de/citation?persistentId=doi:10.17617/3.MEAGMS},
author = {Grabenhorst, Matthias},
title = {The anticipation of imminent events is time-scale invariant},
publisher = {Edmond},
year = {2025}
}

@misc{Grabenhorst_2021_data,
doi = {10.17617/3.YC3SGA},
url = {https://edmond.mpg.de/citation?persistentId=doi:10.17617/3.YC3SGA},
author = {Grabenhorst, n/a},
title = {dataPNAS202019342},
publisher = {Edmond},
year = {2021}
}

@article{Herbst_2018, title={Tracking Temporal Hazard in the Human Electroencephalogram Using a Forward Encoding Model}, volume={5}, ISSN={2373-2822}, url={http://dx.doi.org/10.1523/ENEURO.0017-18.2018}, DOI={10.1523/eneuro.0017-18.2018}, number={2}, journal={eneuro}, publisher={Society for Neuroscience}, author={Herbst, Sophie K. and Fiedler, Lorenz and Obleser, Jonas}, year={2018}, month=Mar, pages={ENEURO.0017–18.2018} }

@article{Han_2022, title={Change of Variable-Foreperiod Effects within an Experiment: A Bayesian Modeling Approach}, volume={5}, ISSN={2514-4820}, url={http://dx.doi.org/10.5334/joc.235}, DOI={10.5334/joc.235}, number={1}, journal={Journal of Cognition}, publisher={Ubiquity Press, Ltd.}, author={Han, Tianfang and Proctor, Robert W.}, year={2022} }

@misc{MirshamsShahshahani_2018_data,
doi = {10.7302/Z20V8B11},
url = {http://deepblue.lib.umich.edu/data/concern/generic_works/cr56n184r},
author = {Mirshams Shahshahani, Payam},
keywords = {Engineering, Health Sciences, Science, Other, General Information Sources, minimum reaction time, sprinter, Olympics, Athletics, sex difference, starting block, false start},
title = {Downloaded IAAF Sprint Results in all Heats for 2004 - 2016 Olympics for both Men and Women},
publisher = {University of Michigan},
year = {2018}
}

@article{Mirshams_Shahshahani_2018, title={On the apparent decrease in Olympic sprinter reaction times}, volume={13}, ISSN={1932-6203}, url={http://dx.doi.org/10.1371/journal.pone.0198633}, DOI={10.1371/journal.pone.0198633}, number={6}, journal={PLOS ONE}, publisher={Public Library of Science (PLoS)}, author={Mirshams Shahshahani, Payam and Lipps, David B. and Galecki, Andrzej T. and Ashton-Miller, James A.}, editor={Piacentini, Maria Francesca}, year={2018}, month=June, pages={e0198633} }

@article{Massar_2020, title={Dissociable influences of implicit temporal expectation on attentional performance and mind wandering}, volume={199}, ISSN={0010-0277}, url={http://dx.doi.org/10.1016/j.cognition.2020.104242}, DOI={10.1016/j.cognition.2020.104242}, journal={Cognition}, publisher={Elsevier BV}, author={Massar, Stijn A.A. and Poh, Jia-Hou and Lim, Julian and Chee, Michael W.L.}, year={2020}, month=June, pages={104242} }

@article{Los_2017, title={Hazard versus history: Temporal preparation is driven by past experience.}, volume={43}, ISSN={0096-1523}, url={http://dx.doi.org/10.1037/xhp0000279}, DOI={10.1037/xhp0000279}, number={1}, journal={Journal of Experimental Psychology: Human Perception and Performance}, publisher={American Psychological Association (APA)}, author={Los, Sander A. and Kruijne, Wouter and Meeter, Martijn}, year={2017}, month=Jan, pages={78–88} }

@misc{Fiore_2025_arXiv,
doi = {10.48550/ARXIV.2506.11460},
url = {https://arxiv.org/abs/2506.11460},
author = {Fiore, Owen and Schifano, Elizabeth D. and Yan, Jun},
keywords = {Applications (stat.AP), FOS: Computer and information sciences, FOS: Computer and information sciences},
title = {On Devon Allen's Disqualification at the 2022 World Track and Field Championships},
publisher = {arXiv},
year = {2025},
copyright = {Creative Commons Attribution 4.0 International}
}

@article{Fiore_2025, title={On Devon Allen’s Disqualification at the 2022 World Track and Field Championships}, volume={79}, ISSN={1537-2731}, url={http://dx.doi.org/10.1080/00031305.2025.2515869}, DOI={10.1080/00031305.2025.2515869}, number={4}, journal={The American Statistician}, publisher={Informa UK Limited}, author={Fiore, Owen and Schifano, Elizabeth D. and Yan, Jun}, year={2025}, month=July, pages={500–507} }

```

_End of dataset notes. Scratch files: ds_refs.bib (same BibTeX), ds_yarrow/, ds_chatroudi_*.xlsx, ds_grab2021.mat, ds_grab2025.mat, ds_fiore_rxntime.csv, ds_wic2018_60W.pdf, ds_osf.py (OSF API inspector), ds_share_*.json (OSF SHARE search dumps)._
