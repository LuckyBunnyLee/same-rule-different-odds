# Novelty final check: adversarial prior-art search on the final abstract

Part of the novelty check. 2026-09-29. Read-only on the repo except this file. **Status: final.**

- **Checked:** `paper/abstract.md` (final render; `analysis/numbers.json` sha256 90a6808b9ce3).
- **Context read first:** `lit/review.md`, `lit/novelty.md` (both written for the original hold hypothesis), `analysis/results.md`, `paper/judge.md`.
- **Tags** (as in `lit/review.md`): **[V-FT]** the specific line was found in the full text or primary document; **[V-FT\*]** full text read through a fetch tool's summary; **[V-ABS]** abstract only; **[S]** secondary description or search snippet; **[U]** unverified.
- Absence claims mean "not found in the searches listed in section 8".

---

## 1. Bottom line

| Claim | Verdict | Most dangerous prior work | What to do |
|---|---|---|---|
| **1** Championship RT offsets (34 ms, 15% of variance; force traces; rule strictness differs by championship) | **Partially anticipated.** The idea and the size are old; the 18-championship estimate (athlete-adjusted where athletes are identified) and the force-trace test are new | **Fiore et al. 2025 itself**: a venue effect across all 13 WCH 1999–2023, implying about 9 ms SD and about 15% of variance (the abstract's own numbers). Also Nozaki, Yokokura et al. (JSPE 1997–2003: same 0.1 s limit, device-dependent RTs; "unify devices or set device-specific thresholds"), and public LetsRun tabulations of 2022 (fastest) and 2025 (slowest) | Change 1 (must), Change 2 (recommended); section 5 |
| **2** Official hold records (Seiko Ready Time, 232 races) and the precise null excluding Haugen's r = 0.16 | **Novel** | Nothing close. Holds were measured before by stopwatch (Tokyo 1991), TV (Haugen) and broadcast audio (Otsuka), never from official records. Residual risk: Han et al. 2025 (paywalled; its text mentions holding time) | None |
| **3** Ready Time ≠ set-to-gun (starts ~0.52 s after "set") | **Novel as a measurement**; the mechanism is foreshadowed | Seiko patent JP2838769B2 (1994): the system is set to "READY" in response to the starter's "set" call. No public definition of "Ready Time" exists | None in the abstract; cite the patent in the full paper |
| **4** Comparing both factors; fairness simulation (4-fold vs 18-fold) | **Novel as executed**; informal precursors | 2022 forum debate over a "fast starter" vs the timing system (never measured); Haugen 2013 set rule eras beside holds; Fiore's tail with vs without 2022 (×1.4) | None |

---

## 2. The most dangerous prior work: Fiore et al. (2025) itself

The abstract says Fiore et al. "showed one championship's RTs ran systematically fast" and frames the result as
"Extending Fiore et al. from one anomalous championship to 18". **That understates Fiore et al.** Their paper
already models championship-level variation across all 13 World Championships 1999–2023, calls it significant, and
suggests technology as one cause. A referee who has read Fiore et al. (or who co-wrote it) will read the current
sentence as a mischaracterisation (repo skill `literature-verification`, section 2).

**What Fiore et al. published** [V-FT: arXiv 2506.11460 v1 PDF; final `Manuscript/manuscript.tex` and `supp.tex`
in github.com/ofiore/Thesis, last commit 2025-04-15; published abstract via OpenAlex]:

- Published abstract: "we compared RTs across multiple competitions, while a generalized Gamma model with random
  effects for **venue** and heat was applied ... significant differences in RTs between the 2022 World
  Championships and other competitions, suggesting systematic variations in timing systems ... These findings
  highlight important variation sources in evaluating the 0.1-sec disqualification threshold to promote fairness in
  elite competition."
- Model (section 3.2): log(µ_ijk) = β0 + v_i, a venue effect for each championship year, "which is used to contrast
  years". Data: men's 100 m and 110 mH semis and finals, WCH 1999–2023, n = 776.
- Table 2: venue SD τ_v = 0.058 on the log-µ scale with 2022, 0.043 without it.
- Supplement: women's τ_v = 0.057 (n = 732). "The consistency in the venue effect standard deviation across men's
  and women's data indicates that the venue effect is not only statistically significant but also consistent in
  magnitude across genders."
- Section 3.1: "Figure 2 also highlights year-to-year variability in RTs, likely influenced by changes in the
  championship venue and environmental conditions such as humidity, precipitation, and elevation. Furthermore,
  advancements in technology and alterations to false start rules during the study period may have played a role in
  these variations."
- Tail: P(RT < 0.100) = 2.76·10⁻³ with 2022 vs 1.94·10⁻³ without it (×1.4), a championship-dependent rule-risk
  calculation in embryo.

**What their published parameters imply in the abstract's own units** (my computation, Appendix A.1: simulate
their GG model, venue share = Var(E[RT | venue]) / Var(RT)):

| | championship SD | share of RT variance |
|---|---|---|
| Fiore, men, with 2022 (τ_v 0.058) | 8.8 ms | 17.0% |
| Fiore, men, without 2022 (τ_v 0.043) | 6.5 ms | 10.0% |
| Fiore, women (τ_v 0.057) | 8.7 ms | 13.8% |
| **This abstract** (all rounds, crossed athlete effects) | **9.3 ms** (6.6–13.1) | **14.9%** (8.1–25.8) |

So the size of the between-championship component, and its roughly 15% share, is already implied by the published
paper. Fiore et al. never state it as a share, and never list per-championship values in the paper.

**Public but unpublished: per-championship venue effects in their repository.** The arXiv record links the repo
("For associated GitHub repository, see https://github.com/ofiore/Thesis"). It contains
`Manuscript/ComparisonOfVenueEffects.pdf`, a per-year plot of the venue effects that was in the submitted version and
removed after review (`reply.tex`: "Given the confusion it may cause, this figure has been removed").
- It shows 2022 fastest (−0.131 on the log scale) and 2011 slowest (+0.097): about a **33 ms** span at µ = e^−1.91.
- Against the abstract's offsets for the 13 shared World Championships: **Pearson r = 0.89, Spearman 0.84**
  (my digitisation of the plot, ±0.003; Appendix A.2). The abstract's own span over those 13 is 32.4 ms (2022 to
  2013).
- Weak as citable prior art (a deleted figure), but it shows that for 1999–2023 the championship offsets are a
  replication with a different model, not a discovery.

**Our data for 8 of the 18 championships are Fiore et al.'s.** All 1,632 valid RTs for WCH 1999–2013 (26% of
6,376) come from `rt_fiore.csv` (their `rxntime.csv`), which carries no athlete names. `analysis/descriptive.py`
gives each such row its own pseudo-ID, so those eight offsets are **not athlete-adjusted** (checked by running
`common.load_rt(False)` + `dedupe_sources`: 1,632 rows, source `rt_fiore`, athlete missing). The endpoints of the
34 ms span (2022, 2025) are athlete-adjusted.

**What remains genuinely ours on claim 1** (none of it found anywhere else):
1. The slow 2025 regime (Tokyo, September 2025) postdates Fiore et al. (arXiv June 2025), and it is the new maximum.
2. Olympics 2020/2024 (Omega) and World Indoors 2024/2025 in the same model; all rounds and events.
3. Athlete adjustment for 10 championships (Fiore et al. adjusted for athletes only in their 2022 rank tests).
4. **The force-trace check** (detection point unchanged, force onset shifted 35 ms): no precedent found.
5. Converting offsets into rule strictness per championship and setting them against the hold (simulation).

---

## 3. Hits, with overlap by claim

Claims: **1** cross-championship offsets and rule strictness; **2** official hold records at scale and the null vs
Haugen; **3** Ready Time is not set-to-gun; **4** comparing both factors plus the fairness simulation.

### 3a. Claim 1: prior cross-championship comparisons (the concept is old)

| # | Work | What it shows | Verified | Overlap |
|---|---|---|---|---|
| 1 | **Fiore, Schifano & Yan 2025**, *Am Stat* 79(4):500–507, doi:10.1080/00031305.2025.2515869; arXiv 2506.11460; repo github.com/ofiore/Thesis | See section 2: venue random effect over WCH 1999–2023 (τ_v 0.058 men, 0.057 women, "statistically significant"); 2022 anomaly by same-athlete rank tests; "year-to-year variability" possibly from technology; per-year effects in the repo | [V-FT] arXiv PDF, final .tex, supplement, reply to reviewers | **Claim 1 partial (large)**; claim 4 partial (tail with vs without 2022) |
| 2 | **Nozaki, Kaneko & Yokokura 1997**, JSPE 48th congress abstracts p.498, doi:10.20693/jspeconf.48.0_498 ("Problems in false-start judging: differences between false-start devices with different detection methods") | Official RTs, Gothenburg 1995 WCH (Seiko frequency detection) vs Atlanta 1996 OG (force-threshold detection): device gaps of 16–30 ms for straight starts, 56–136 ms from curves. Conclusion: "to judge fairly, some countermeasure is needed, such as unifying the devices or setting the detection RT value individually (currently 0.1 s for both devices)" (my translation) | [V-FT] J-STAGE scan (OCR garbled, numbers and conclusion legible) | **Claim 1 partial**: the "same rule, different odds by start system" idea, 29 years earlier, on two championships, raw means |
| 3 | **Nozaki, Yokokura & Kajiwara 2001**, JSPE 52nd p.514, doi:10.20693/jspeconf.52.0_514; **Nozaki, Yokokura, Kajiwara & Itō 2002**, JSPE 53rd p.516, doi:10.20693/jspeconf.53.0_516; **Nozaki, Yokokura, Kajiwara & Itō 2003**, JSPE 54th p.542, doi:10.20693/jspeconf.54.0_542 | Men's 100 m mean RT Seville 1999 WCH 0.154 s vs Sydney 2000 OG 0.193 s (women 0.160 vs 0.210); Sydney vs Edmonton 2001 overall 0.233 vs 0.166 s (2,456 RTs); 2003, women's straight events Sydney 0.213 > Atlanta 0.177 > Seville 0.154, Edmonton 0.159 s, Olympic (non-Seiko) meets slower. Blamed on detection method; 2003 concludes the IAAF must establish a scheme to test and certify the devices. Full papers in JAAF 陸上競技紀要 14–16 (2001–03) and Meisei bulletins (not online) | [V-FT] 2001 and 2003 read by me (OCR noisy, numbers legible); 2002 read by search passes A/B | **Claim 1 partial**; also anticipates the Conclusion's "audit the start system" |
| 4 | **Yokokura, Fuwa, Kajiwara & Kuragano 2013**, Bull. Meisei Univ. (Informatics) 21:11–16, https://meisei.repo.nii.ac.jp/records/592 | 100 m finals at 7 Seiko-timed WCH 1999–2011 (n = 111): Daegu 2011 significantly slower by 15–35 ms (sexes combined; women 27–44 ms, men 14–28 ms). Blamed on the 2010 rule and Bolt's DQ. States WCH use Seiko's "Dynamic Threshold Level Detection System" (co-invented by Yokokura; since Gothenburg 1995) and OG use Omega's fixed threshold | [V-FT] | Claim 1 partial; offers the rule-era reading of the slow 2011/2013 offsets |
| 5 | **Mirshams Shahshahani, Lipps, Galecki & Ashton-Miller 2018**, *PLoS One* 13:e0198633 | OG 2004–2016 minimum RTs fell; "the most likely explanation ... is a reduction in the proprietary force thresholds"; "The method for calculating reaction time can vary with the company awarded the timing contract" | [V-FT] | Claim 1 partial: championship shifts attributed to detection thresholds (Omega). The abstract's force-trace test reaches a different conclusion (no threshold change) for the Seiko meets that have traces. Different vendor and era, so there is no contradiction, but it deserves one clause in the full paper |
| 6 | **Milloz, Hayes & Harrison 2021**, *Sports Med* 51:21–31 | "The lack of a clear regulation by WA on the validity and reliability of the SIS ... [is] ultimately detrimental to the fairness of competition"; Willwacher's rig found one certified system ~20 ms slower; FP "could be recorded during competition, as is currently done for the wind and RT" | [V-FT] (PDF hosted in Fiore's repo) | Claim 1 conceptual; Conclusion's recommendations. No data |
| 7 | **Pilianidis, Mantzouranis & Kasabalis 2012**, *IJPAS* 12(1), doi:10.1080/24748668.2012.11868587 | Finals at WCH 1997–2009 (n = 161); MANOVA: between-championship RT differences significant only in 110 mH; blamed on the rule change | [V-ABS] paywalled | Claim 1 minor |
| 8 | **Brosnan, Hayes & Harrison 2017**, *J Sports Sci* 35:929–935 | >8,500 RTs, World and European Championships 1999–2014; Fig. 1 boxplots across championships grouped by ruling period; ex-Gaussian by sex, period, round | [V-FT\*] partial text via academia.edu preview; body otherwise paywalled | Claim 1 minor; claim 4 method precedent (ex-Gaussian thresholds) |
| 9 | Descriptive per-championship RT tables: **Mitašík, Doležajová & Lednický** AFEPUC 2021 (doi:10.2478/afepuc-2021-0017, women) and 2022 (62(1):72–82, doi:10.2478/afepuc-2022-0007, men), "Intraindividual evaluation of reaction time at the World Athletics Championships 1999–2019"; **Juhas, Matić & Janković 2015** (doi:10.5937/gfsfv1521043j); **Pavlović 2015** (SportSPA 12(1); OG 2012 vs WCH 2013); **Pavlović et al. 2014** (OG 2004/08/12); **Muñoz-Pérez & Lago-Fuentes ~2021** (WCH 2013–19); **Ditroilo & Kilding 2004** (NSA 19(1):13–19; WCH 2001 vs 2003) | Mean RTs of finalists differ between championships. Mitašík et al. track individual finalists across editions (a descriptive, within-athlete comparison). Explanations offered: rules, age or none | Search pass A: AFEPUC [V-FT] (titles and authors checked by me), others [V-ABS] or [S] | Claim 1 minor each |
| 10 | **Han, Zhou & Zhang 2025**, *IJPAS* 26(4):900–919, doi:10.1080/24748668.2025.2579341 | 100 m semis/finals, 7 OG + 12 WCH + 13 U20 WCH, 2000–2024, GLMs; zero-tolerance β = −0.004 | [V-ABS]; closed. Google Scholar matches its full text for "holding time" OR "hold time", but the snippet is not visible | Claim 1 minor; **residual risk** for claims 2/4 until someone with T&F access checks its variables |
| 11 | **Zhang, Lin & Zhang 2021**, *Complexity* 6633326 | WCH 2011–2019; RT–performance correlation "varies by year of competition" | [V-ABS]; the open-access PDF is behind a Cloudflare challenge | Claim 1 minor |
| 12 | Lab comparisons of detection systems: **Willwacher et al. 2013**; **Milloz et al.** ISBS 2020 (doi:10.34961/6110, 6117); **Harrison & Hayes** ISBS 2018 (10.34961/4261); **Holmes** ISBS 2018 (10.34961/4245); **Pain & Hibbs 2007** | Device and algorithm offsets of about 20–70 ms | [V-ABS] / [V-FT] (Pain & Hibbs, earlier review) | Mechanism for claim 1, no championship comparison |

**Interest note on rows 2–4, 18 and 19.** Nozaki, Kaneko and Yokokura are co-inventors of Seiko's detector (row 13),
so the Japanese series compares their own system with its rivals. That does not weaken it as prior art for the idea,
but it is worth knowing if the full paper leans on their numbers.

**No prior comparison of force traces across championships was found.** Official Seiko waveforms were analysed once
before, at Seville 1999, to review false-start rulings (row 19). The detection-line vs force-onset check across
championships is the one element of claim 1 with no precedent in any source searched.

### 3a′. Claim 1 in journalism and forums (a referee who follows the sport will know these)

| # | Source | What it shows | Verified | Overlap |
|---|---|---|---|---|
| J1 | **LetsRun, R. Johnson, 18 Jul 2022**, "Was Devon Allen Screwed? There's At Least A 99.9% Chance That He Was", https://www.letsrun.com/news/2022/07/was-devon-allen-screwed-theres-at-least-a-99-9-chance-that-he-was/ | Forum user JC100's medians: 2022 lowest of the last 13 global championships in all three sprint events; Doha 2019 vs Eugene semis/finals mean 154.4 vs 133.2 ms; PJ Vazel's count of RTs < 0.115 s at WCH men's 100 m/110 mH, all rounds, "same FS detection provider": 2011–2022 = 0, 0, 0, 2, 3, 25, ending "**Not the same standard, however the 0.100 rule still stands**" | [V-FT] Wayback copy (search pass B), quotes checked by me in the saved text | Claim 1 partial: the abstract's title idea in one tweet; 2022 only; no adjustment |
| J2 | **LetsRun, 19 Jul 2022**, "The Data Keeps Pouring In and It Continues To Look Bad For World Athletics and Great For Devon Allen" | WA statement: systems "calibrated and synchronised ... used for the past three world championships and was functioning as normal"; 200 m round-1 medians fell by more than 0.02 s vs 2019 | [V-FT] (same) | Claim 1 partial (2022 only) |
| J3 | **LetsRun, 1 Aug 2022**, "Devon Allen DQ Update: We've Got Even More Data ..." | All 21 US athletes faster at Worlds than at the US Championships; DL 110 mH finals mean 0.142 vs Worlds semis 0.130; Seiko: "the exact same system used at the last 3 worlds and ... calibrated correctly" | [V-FT] via reader proxy (search pass B), checked by me | Claim 1 partial: same-athlete, 2022 only |
| J4 | **LetsRun forum, Tokyo 2025 Day 2 thread, post #1027, 14 Sep 2025** (thread 13762112) | Mean RT (100 m M/W excl. prelims, 100 mH): 2015 0.158, 2017 0.158, 2019 0.153, 2022 0.139, 2023 0.158, **2025 0.183**; "zero reaction times between 0.100 and 0.134"; speculates a "deliberate allowance of 0.025 seconds" | [V-FT] (saved page, checked by me) | **Claim 1 partial: the slow 2025 regime was tabulated publicly during the championship.** Ours is athlete-adjusted and tests the threshold explanation |
| J5 | **T&FN forum "Reaction times" thread, 18–19 Jul 2022** (JC100 = John Clark) and LetsRun forum threads 11399684 / 11433592 | Championship medians correlate across events, "indicating slight variations in either the equipment and/or the method used"; a 2022 offset of about 0.012 s. Posters ask whether "anyone is controlling for the starter" ("time between 'set' and gun") and argue about an "American style 'fast starter'" at Eugene; JC100 dismisses the fast-gun explanation with Prefontaine Classic RTs | [V-FT] saved pages (search pass B; hold passages checked by me) | Claim 1 minor; **claim 4 informal precursor**: hold vs system was debated qualitatively in 2022; nobody measured it |
| J6 | franceinfo, 15–16 Aug 2022 (starter K. Legrand) | "the Seiko apparatus may be more sensitive than usual" | [S] (search pass B) | The threshold hypothesis that the force traces argue against |
| J7 | A scraped CSV of 5,660 WA RTs (Worlds 1983–2022, Olympics 2000–2021), monkeystyping.neocities.org/TandF/iaafReaction.csv | Public data, no analysis attached | [V-FT] file (search pass B) | None (data only) |

Nothing quantitative on this topic was found in the NYT, WSJ, The Athletic, FiveThirtyEight, Significance or Gelman's
blog, and no World Athletics or Seiko document on detection at Oregon 2022 or Tokyo 2025 beyond the 2022 statements
(Seiko's own history lists a new start system only for Doha 2019).

### 3b. Claims 2 and 3: official hold records and what Ready Time measures

| # | Work | What it shows | Verified | Overlap |
|---|---|---|---|---|
| 13 | **Seiko Precision patent JP2838769B2** (inventors S. Yokokura, N. Suzuki, T. Nozaki, K. Kaneko; priority 1994-08-31, filed 1994-12-28, granted 1998-12-16), "Motion judgment device", https://patents.google.com/patent/JP2838769B2/en | "each component ... is set to 'READY' according to the voice of 'preparation' [用意, i.e. 'set'] of the starter (step a7)"; block signals are recorded from then on; outputs earlier than 0.5 s before the gun are cancelled | [V-FT] machine translation and metadata (search pass C's saved copy, checked by me; Google Patents was throttling my own fetch) | **Claim 3 partial (mechanism only)**: a READY state armed after the call would make Ready Time start after "set" by design. The patent defines no "Ready Time" and measures nothing |
| 14 | Seiko RM-200 catalogue, product pages; WA Starting Guidelines 2012/2018/2022; WA certification documents | No public definition of "Ready Time" anywhere. The catalogue lists "operator" and "starter" switch boxes (function unstated) | [V-FT] (search pass C) | None; supports claim 3's "checked what they measure" as new |
| 15 | **Nozaki & Kaneko 1994**, JSPE 45th p.510, https://www.jstage.jst.go.jp/article/jspeconf/45/0/45_510/_article/-char/ja/ | Tokyo 1991 WCH: 147 holds hand-timed from "yō-i" to the gun; experienced starters 2.09 ± 0.22 s vs inexperienced 1.91 ± 0.27 s | [V-FT] (search pass C) | Claim 2 none (not official, no RT); earliest championship hold data found |
| 16 | **Haugen, Shalfawi & Tønnessen 2013** | Besides r ≈ 0.16, a figure "95% CIs of holding times for the different athletics championships" (women, men), and rule-era effects on RT (+0.03 s); "RT ... can vary 0.03–0.05 s depending on false start regulations and holding time" | [S] ResearchGate figure title via search; full text closed | Claim 4 weak partial: it set a rule-era (championship-level) factor beside the hold, though not per-championship offsets and not on DQ risk |
| 17 | **Otsuka, Kurihara & Isaka 2018**, *JJBSE* 22(4):184–190 (review, Japanese) | Cites Otsuka et al. (in press): a fixed 1.780 s foreperiod gave shorter, more consistent RTs in the lab | [V-FT] (scan; search pass C; title page checked by me) | None (lab) |

**No use of Seiko Ready Time or any official start-system hold record was found** (365 citing works screened by
search pass A; Seiko, WA and Japanese sources by search pass C).

### 3c. Further items from the academic keyword search

| # | Work | What it shows | Verified | Overlap |
|---|---|---|---|---|
| 18 | **Yokokura, Kajiwara & Kuragano 2014**, Bull. Meisei Univ. 22:53–59, https://meisei.repo.nii.ac.jp/records/609 | Approved start devices "do not have the detection system that IAAF decided and the designated verification bodies"; "the false start apparatus is used in a competition by maker's original adjustment"; cites reports that the same athletes' starts give different RTs on different devices; builds a start robot for "unified test and calibration" | [V-FT] (search pass D; abstract lines checked by me) | Claim 1 conceptual; anticipates the Conclusion's audit recommendation |
| 19 | **Nozaki & Yokokura 2000**, JSPE 51st p.438, doi:10.20693/jspeconf.51.0_438 | Official Seiko block-force waveforms for all 227 starts (172 heats) at Seville 1999, analysed to review false-start rulings (54 of 227 flagged) | [V-FT] page image read by me | Precedent for analysing official Seiko traces, at one championship and for rulings. **Not** a cross-championship detection check, so the force-trace novelty stands |
| 20 | **Tomozei, Hurduc & Dumitru 2025**, Studia UBB Educatio Artis Gymnasticae 70(SI2):287–298, doi:10.24193/subbeag.70.sp.iss.2.54 | Age, RT and performance, WCH 2017–2025 including Tokyo. One sentence, citing Valamatos et al. 2022, says 2022–23 RTs clustered faster, plausibly reflecting "instrumentation differences". No analysis | [V-FT] (search pass D; sentence checked by me) | Claim 1 minor |
| 21 | Patent **US 9,202,463** (Newman, 2015) | A timer armed by a spoken "SET"; no hold measurement | [V-FT] (search pass D) | None |

- **(a) Competition hold vs RT after 2013:** nothing beyond Otsuka 2017 (lab arm plus unanalysed broadcast holds).
  None of Otsuka's 81 indexed works follows up on holds. Dalmaijer 2015/2016 (speed skating) remains the only other
  racing-sport field study. No automated audio measurement of holds was found.
- **(c) Fairness simulations comparing meets:** none beyond Fiore 2025, Lipps 2011 and Brosnan 2017.
- **Unverified leads:** a snippet attributing to Tønnessen et al. (2013) the statement that Seiko and Omega "provide
  up to 0.04 seconds difference". It is not in the abstract, and not in Haugen & Buchheit 2016 (checked); the full
  text is closed [U]. A secondary summary suggests Brosnan et al. report World and European medians separately [S].

---

## 4. Verdict per claim

**Claim 1: partially anticipated.**
- *Concept anticipated.* That one 0.100 s limit means different things at different championships because start
  systems differ was argued with official data in 1997 (Nozaki, Kaneko & Yokokura: "unify the devices or set the
  detection RT value individually, currently 0.1 s for both"), repeated in 2001–2003 with a call for IAAF
  certification, restated by Mirshams Shahshahani et al. (2018), Milloz et al. (2021) and Fiore et al. (2025), and
  summed up in 2022 by PJ Vazel: "Not the same standard, however the 0.100 rule still stands."
- *Magnitude anticipated.* Fiore et al.'s published τ_v implies a championship SD of about 8.8 ms and about 14–17% of
  RT variance, against the abstract's 9.3 ms and 15%. Their repo's per-year effects span about 33 ms and correlate
  r = 0.89 with the abstract's offsets.
- *Endpoints publicly known.* 2022 fastest (Fiore; LetsRun 2022); 2025 slowest (LetsRun forum, 14 Sep 2025, raw
  means).
- *New.* Athlete-adjusted offsets (10 championships with identities) across 18 championships including Olympics
  and World Indoors; the variance share with a CI; **the force-trace test, which has no precedent**; and translating
  offsets into legitimate-DQ risk beside the hold.
- *Exposure.* The current wording ("from one anomalous championship") misstates Fiore et al. and would be caught by
  anyone who has read their paper.

**Claim 2: novel.**
- No study, abstract, thesis, patent or news piece uses Seiko's Ready Time or any official start-system hold record.
  That covers four independent sweeps: citation graphs, keyword databases, Japanese sources, journalism.
- Earlier hold data are all unofficial:
  - stopwatch, Tokyo 1991, 147 starts, no RT link (Nozaki & Kaneko 1994);
  - television, 267 heats (Haugen et al. 2013);
  - broadcast audio, 83 races, not linked to RT (Otsuka et al. 2017).
- No elite field study of hold vs RT exists after Haugen et al., so a precise null that excludes their r = 0.16 is new.
- Residual risk: Han et al. (2025) is paywalled and its full text matches "holding time". The abstract lists no hold
  variable, so it most likely cites Haugen. Worth one check by anyone with Taylor & Francis access.

**Claim 3: novel as a measurement.**
- No public document defines Seiko's "Ready Time": not Seiko's catalogue or web pages, not WA's guidelines or
  certification documents.
- Seiko's 1994 patent describes a READY state set "according to the voice of 'preparation' of the starter". That
  makes a lag after "set" plausible by design, so the finding is less surprising, but nobody has measured the
  interval or shown that its offset varies by championship.

**Claim 4: novel as executed.**
- Nobody has set the hold against championship offsets on the rule's legitimate-DQ risk.
- Precursors are informal (2022 forums: "fast starter" vs system) or different in kind: Haugen 2013 put rule eras
  beside holds; Fiore et al. computed the tail with and without 2022; Nozaki et al. proposed device-specific
  thresholds; Brosnan et al. and Lipps et al. derived sex-specific thresholds.

---

## 5. Recommended wording changes

Word counts use `paper/render.py`'s own counter (`count_strict` on `md_to_plain`), applied read-only to
`paper/abstract.md`: **466 now, limit 470.**

**Change 1 (must). Results, claim 1.** Fixes the Fiore mischaracterisation, credits their data, and stops
"athlete-adjusted" covering the eight championships that have no athlete identities.

- Now: "Extending Fiore et al. from one anomalous championship to 18, I found athlete-adjusted offsets spanning 34 ms
  (fastest 2022 World Championships, slowest 2025) and carrying 15% of RT variance (95% CI 8 to 26)."
- Replace with: "**Extending Fiore et al.'s venue analysis and data to 18 championships, I found offsets spanning
  34 ms (fastest 2022 World Championships, slowest 2025; both athlete-adjusted) and carrying 15% of RT variance
  (95% CI 8 to 26).**"
- Count: 468. In `paper/abstract.template.md` (line 46) this is: "Extending Fiore et al.'s venue analysis and data to
  {{descriptive.n_comp_years}} championships, I found offsets spanning ... (fastest ..., slowest ...; both
  athlete-adjusted)". Per the guard rule, pin "both athlete-adjusted" with an assert (the fastest and slowest
  championships contain no `rt_fiore` rows) and prove it fires.

**Change 2 (recommended). Introduction.** After Change 1 the current sentence is incomplete rather than false, so
this is optional.

- Now: "Fiore et al. (2025), analysing Devon Allen's disqualification, showed one championship's RTs ran
  systematically fast."
- Replace with: "Fiore et al. (2025), analysing Devon Allen's disqualification, **found RT levels varying between
  World Championships, with 2022 systematically fast.**"
- Count with Change 1: 472. That breaks only the team's 470 margin rule; SSAC's own limit is not at risk (453
  unsplit words). To keep the margin, cut "Championships mattered more." (→ 469), or leave the Introduction as it is.

**No change needed:**
- The novelty sentence ("To my knowledge, no study has used official hold records at scale, checked what they
  measure, or compared both factors") survived every search. The one residual risk is Han et al. (2025), whose full
  text I could not read.
- Claim 3's sentence. A referee may say the lag is "by design" (Seiko's patented READY state is armed after the
  call). The measurement is still new; cite the patent in the full paper.
- The force-trace sentence, and "The cause remains unidentified." Both are now better supported: no vendor or WA
  document explains the offsets.
- The Conclusion's recommendations are not claimed as new. They echo Nozaki et al. (2002, 2003: IAAF should test and
  certify start devices), Otsuka et al. (2017) and Milloz et al. (2021: record the foreperiod like wind; revisit SIS
  certification).

**For the full paper (Dec 4), not the abstract:**
- Cite the device-dependence line: Nozaki et al. 1997/2001/2002/2003, Yokokura et al. 2013, Mirshams Shahshahani
  et al. 2018, Milloz et al. 2021. Name LetsRun 2022 and the 2025 forum tabulation as public observations.
- Say plainly which parts of claim 1 replicate Fiore et al. (13 championships; r = 0.89 with their venue effects)
  and which are new (2025, Olympics, World Indoors, athlete adjustment, variance share with a CI, force traces).
- Contrast the force-trace result with Mirshams Shahshahani et al.'s threshold explanation (different vendor and
  era; Omega meets have no traces).
- Credit Fiore et al.'s `rxntime.csv` as the source for WCH 1999–2013, and state that those offsets are not
  athlete-adjusted.
- Cite JP2838769B2 for the READY state. An operator arming READY after the call would also explain the
  championship-dependent lag (0.27 / 0.39 / 0.61 s in 2022 / 2023 / 2025); that is a hypothesis, not a result.
- Cite Nozaki & Kaneko 1994 for starter-dependent holds at a championship.

---

## 6. Side findings (not prior art, found during the check)

1. **"Athlete-adjusted" overstates for 8 of 18 championships.** All 1,632 valid RTs for WCH 1999–2013 (26% of
   6,376) are `rt_fiore` rows without athlete names; each gets its own pseudo-ID. The 34 ms endpoints are
   athlete-adjusted; the 15% share mixes adjusted and unadjusted championships. Change 1 fixes the wording.
2. **The Methods' "compiled ... from public results"** is true (Fiore et al.'s file is public and derived from
   World Athletics results) but does not credit their compilation. Change 1 adds "and data".
3. **The offsets replicate Fiore et al. for 1999–2023** (r = 0.89 with their repo venue effects; about 33 ms span
   in both). This is good for validity and should be said, not hidden.
4. **2022's short holds.** Median Ready Time is shortest at WCH 2022 (1.440 s vs 1.686 s in 2023 and 1.677 s in
   2025; `analysis/results.md` §2). That fits the 2022 forum talk of an "American style 'fast starter'" (J5). My
   arithmetic, not a repo result: a 0.25 s shorter Ready Time at the measured slope's upper bound (0.81 ms per
   100 ms) moves RT by about 2 ms, against an 18.5 ms offset. So the hold cannot explain 2022. One line in the full
   paper would answer the forum's question.

---

## 7. What I could not access

- **Paywalled:** Han, Zhou & Zhang 2025 (T&F; the key residual risk, since its full text mentions holding time);
  Brosnan et al. 2017 body (only a partial academia.edu preview); Pilianidis et al. 2012; Haugen et al. 2013 (only
  a ResearchGate figure title).
- **Blocked:** Zhang et al. 2021 (open access but behind a Cloudflare challenge); ResearchGate and Academia pages
  (403); archive.org (429 rate limits); Google Scholar after about 20 pages (CAPTCHA); Google Patents (503 for me;
  search pass C's earlier copy was used).
- **Print or offline only:** the full Meisei and JAAF papers behind the JSPE abstracts (陸上競技紀要 14–16;
  Meisei bulletins 10–14; ICHPER·SD 2003 pp. 246–250); John Clark's book *100m: A New Look at the World's Greatest
  Race*.
- **Not accessed:** T&FN threads 1770362 and 1802137 and pages 6–9 of 1760714 (snippets put the Eugene offset at
  about 0.015 s); LetsRun Tokyo Day 1, page 15 (snippet: "0.030 too slow").
- No Chrome browser was connected, so no browser route around these blocks was available.

---

## 8. Search log

- **Citation graphs** (search pass A): OpenAlex `cites:` filter, Semantic Scholar citations, OpenCitations COCI and
  Google Scholar "cited by" for Fiore 2025, Brosnan 2017, Mirshams Shahshahani 2018, Lipps 2011, Haugen 2013,
  Otsuka 2017, Tønnessen 2013, Milloz 2021, Willwacher 2013, Pain & Hibbs 2007, Ishikawa/Komi 2009 and Han 2025.
  365 unique citing works screened. **Fiore 2025 and Han 2025 have no citers in any index** (checked 2026-09-29).
- **Journalism and grey literature** (search pass B): LetsRun articles and forums 2022 and 2025, T&FN forum, franceinfo,
  CBC, NBC, Trackademic; SSAC paper lists; ISBS, ECSS and ACSM abstract searches.
- **Vendor and WA documents; Japanese literature** (search pass C): Seiko patents (JP2759769B2, JP2838769B2 and others),
  RM-200 catalogue, Seiko history pages, WA Starting Guidelines 2012/2018/2022, WA certification documents,
  J-STAGE (JSPE congress abstracts 1992–2006, SICE papers), CiNii.
- **Academic keywords** (search pass D): about 40 query variants across OpenAlex search, Semantic Scholar search (mostly
  rate-limited), PubMed E-utilities, Europe PMC, the arXiv API, CiNii and J-STAGE. Otsuka's 81 indexed works were
  checked for hold follow-ups.
- **Mine:** Fiore et al. arXiv PDF, GitHub repo (manuscript, supplement, reviewer replies, figures, meeting notes),
  OpenAlex/Crossref metadata; Mirshams Shahshahani 2018 PDF; Milloz 2021 PDF; arXiv API (five queries: nothing
  beyond Fiore); Google Scholar (four queries); J-STAGE PDFs of the JSPE abstracts (1997, 2001, 2003 read); the
  Yokokura 2013 bulletin; Brosnan 2017 academia preview; the repo's own data (read-only) for the athlete-ID check;
  `paper/render.py`'s counter for word budgets.

---

## Appendix A. Reproducing my numbers

These are my checks, not repo results; nothing here feeds `analysis/numbers.json`. Run with
`.venv\Scripts\python.exe` from the repo root.

**A.1 Venue SD and variance share implied by Fiore et al.'s published parameters** (gamlss GG parameterisation:
z = (y/µ)^ν ~ Gamma(θ, rate θ), θ = 1/(σ²ν²); venue effect on log µ, heat effect on log σ). Output: men with 2022,
8.8 ms and 17.0%; men without 2022, 6.5 ms and 10.0%; women, 8.7 ms and 13.8% (Monte Carlo; shares move by about
±0.1 point with the seed).

```python
import numpy as np
rng = np.random.default_rng(7)
def run(b0, g0, nu, tv, th, N=4_000_000):
    h = rng.normal(0, th, N); sig = np.exp(g0 + h); theta = 1 / (sig**2 * nu**2)
    y0 = np.exp(b0) * rng.gamma(theta, 1 / theta)**(1 / nu)        # RT given venue effect 0
    y = np.exp(rng.normal(0, tv, N)) * y0                            # add venue effect on mu
    vv = y0.mean()**2 * np.var(np.exp(rng.normal(0, tv, N)))         # Var(E[RT | venue])
    return 1000 * np.sqrt(vv), vv / y.var()
for lab, p in {"men incl 2022": (-1.910, -2.200, -1.178, 0.058, 0.320),
               "men excl 2022": (-1.910, -2.200, -1.177, 0.043, 0.326),
               "women":         (-1.921, -2.071, -3.691, 0.057, 0.111)}.items():
    sd, share = run(*p); print(f"{lab}: venue SD {sd:.1f} ms, share {100*share:.1f}%")
```

Parameters: Fiore et al., Table 2 (men) and supplement Table (women).

**A.2 Abstract offsets vs Fiore et al.'s repo venue effects.** Venue effects digitised from
`Manuscript/ComparisonOfVenueEffects.pdf` (top panel, with 2022); offsets from `analysis/results.md` §1.
Output: Pearson 0.889, Spearman 0.835; spans 33.7 ms (×148 ms) and 32.4 ms.

```python
import numpy as np; from scipy.stats import spearmanr
fiore = {1999:-.068, 2001:-.026, 2003:.041, 2005:-.002, 2007:.060, 2009:-.016, 2011:.097,
         2013:.057, 2015:-.014, 2017:.003, 2019:.000, 2022:-.131, 2023:-.006}
ours  = {1999:-13.3, 2001:-9.7, 2003:9.2, 2005:-3.9, 2007:1.6, 2009:-4.2, 2011:12.7,
         2013:13.9, 2015:5.4, 2017:4.8, 2019:3.1, 2022:-18.5, 2023:-1.0}
y = sorted(fiore); f = np.array([fiore[k] for k in y]) * 148; o = np.array([ours[k] for k in y])
print(np.corrcoef(f, o)[0, 1], spearmanr(f, o).correlation, np.ptp(f), np.ptp(o))
```

**A.3 Athlete identities.** `common.load_rt(False, "all")`, then `common.dedupe_sources`, then valid starts
(0.100–0.300 s, not FS, not DNS): 6,376 rows, of which 1,632 have source `rt_fiore` and no athlete name, all in
WCH 1999–2013.

**A.4 Word counts.** Import `count_strict` and `md_to_plain` from `paper/render.py` and apply the section 5
replacements to the text of `paper/abstract.md`: 466 now; 468 with Change 1; 472 with Changes 1 and 2; 469 after
also cutting "Championships mattered more."
