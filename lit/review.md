# Literature review: starter foreperiod, sprint reaction time and the 0.100 s rule

Part of the literature review. Version 1, 2026-09-29.

Companion files:
- `definitions.md`: the operational terms used here.
- `novelty.md`: ranked contributions.
- `datasets.md`: additional data.
- `refs.bib`: all citations; BibTeX keys are given in brackets where helpful.

**Verification tags** (repo skill `literature-verification`):
- **[V-FT]**: checked in the full text, primary document or data files; the specific line was found.
- **[V-FT\*]**: full text read through a fetch tool's quoted summary. Re-check the quote before it goes into the paper.
- **[V-ABS]**: abstract only.
- **[S]**: secondary description.
- **[U]**: unverified.

Search coverage:
- PubMed E-utilities, PMC full texts, Crossref/OpenAlex/Semantic Scholar citation graphs (every paper citing Haugen 2013, Otsuka 2017 and Dalmaijer 2015).
- Open repositories: OSF, Figshare, Edmond, Deep Blue.
- World Athletics documents; patents; J-STAGE (Japanese).
- Targeted web searches, 2026-09-28/29.

Paywalled items (several Springer, APA and T&F papers) stay [V-ABS] or [S]. Absence claims mean "not found in these searches".

---

## 0. Summary in ten lines

1. **The baseline is thin.** Haugen et al. 2013 is the only championship-scale study relating the starter's hold to RT: 267 heats measured from TV, holds 1.3–2.2 s, r = +0.16 to +0.17, i.e. slower RT after longer holds [V-ABS]. The full text is closed, and its measurement method is unverified.
2. **Measuring holds from broadcast audio has been done, manually.**
   - Otsuka et al. 2017: 83 races (WCH 2011/13/15, OG 2012), mean 1.780 s, SD 0.158 s [V-FT].
   - Dalmaijer et al. 2015: 148 Olympic speed-skating races [V-FT].
   - Nobody has automated or validated it.
3. **Official hold data exist.** Seiko start "waveform" images on World Athletics results pages print a per-heat `Ready Time`, probably set → gun, for WCH 2022/23/25 and WIC 2024/25 (datasets.md). No prior analysis of them was found.
4. **Field and lab disagree on the sign.**
   - Field: Haugen's positive r; Dalmaijer's skating times get worse after longer ready intervals.
   - Lab: Otsuka's sprinters speed up from 156 to 117 ms across 1.465–2.096 s [V-FT].
   - Foreperiod theory predicts *either* sign depending on what athletes condition on (§5.11).
5. **The 0.100 s rule rests on weak and conflicting evidence.**
   - Its origin is poorly documented (§3).
   - Tail-based re-estimates conflict: Brosnan 2017 argues for raising it to 115/119 ms [V-ABS]; Fiore et al. 2025 for lowering it to about 0.094 s at a 10⁻³ tail [V-FT].
   - **None conditions on the foreperiod.**
6. **Official RT is a vendor-specific force-detection time, not movement onset.** Detection criteria are proprietary, differ between Seiko and Omega, and have changed over time (§4). Between-meet calibration shifts are large; Fiore et al. found WCH 2022 systematically faster [V-FT].
7. **Cognitive science offers three competing accounts of temporal preparation:**
   - hazard / conditional probability;
   - reciprocal PDF (Grabenhorst);
   - memory / trace conditioning (fMTP).

   Lab data in the sprint hold range exist for each, but none has been tested on real starts. Bausenhart & Ulrich (2026): "surprisingly little research has been devoted to examining the role of temporal predictions in such fields more closely" [V-FT].
8. **Anticipations rise with elapsed waiting time** (Tucker et al. 2009; Leow et al. 2018). DQ'd responses are removed from RT data, so selection can bias RT–hold slopes (§5.6).
9. **Loud go signals plus high readiness produce responses around 70–90 ms** (StartReact; §5.8). Legitimate sub-0.100 s responses therefore depend on preparation state, which depends on the hold.
10. **Other sports regulate the foreperiod**: ISU 1–1.5 s; FIA random 0.2–3.0 s; rowing "distinct and variable pause". Athletics enforces a strict RT threshold but leaves the hold entirely to the starter (§6).

---

## 1. Baseline: Haugen, Shalfawi & Tønnessen (2013) [Haugen2013]

- **Citation.** Haugen TA, Shalfawi S, Tønnessen E (2013). The effect of different starting procedures on sprinters' reaction time. *J Sports Sci* 31(7):699–705. doi:10.1080/02640414.2012.746724. PMID 23199011.
- **Access.** Closed. No legal full-text copy was found:
  - Unpaywall/OpenAlex: `closed`; Semantic Scholar: `CLOSED`.
  - CORE, archive.org and Bing PDF searches: nothing.
  - ResearchGate: 403. T&F supplementary page: 403.
  - Obtain it through interlibrary loan or the authors if exact method text is needed.

**Abstract [V-ABS]:**
- **Design.** "We examined the effect of different false start rules and starters' holding time on athletics sprinters' reaction times."
- **Sample.** RTs from 210 women (25.2 ± 3.8 y) and 361 men (24.8 ± 3.8 y), 100 m, international senior championships 1997–2011.
- **Holds.** "Holding time calculations were based on television recordings from the analysed heats (n = 267)."
- **Rule effect.** "Mean reaction times have increased by 20% (0.03 s, P < 0.001) during a 15 year period due to stricter false start rules."
- **Holds and RT.**
  - "Starters' holding times were between 1.3 and 2.2 s."
  - Men: r = 0.16 in 1997–2003 and r = 0.16 in 2003–2009 (P < 0.001).
  - Women: r = 0.17 in 1997–2003; not significant in 2003–2009.
  - Positive r means *slower* RT after longer holds.
- **Dispersion.** "While the interquartile range of reaction time decreased with longer holding time for female sprinters, the opposite trend was observed among the males."
- **Conclusion.** RT and 100 m performance "can vary 0.03–0.05 s depending on false start regulations and holding time."

**Secondary descriptions:**
- **Haugen & Buchheit 2016** [HaugenBuchheit2016] (*Sports Med* 46(5):641–656; author manuscript read, [V-FT] for its wording) [S about Haugen 2013]:
  - Defines holding time as the "time between 'set' and 'go'-signal".
  - Tabulates about 0.02 s ("trivial") faster RT for shorter holds. The table row is garbled: "decreasing starters' holding time from 1.3 to 2.2 s".
  - Cites Karlin 1959: "reaction time increases as a function of the preparatory interval". That is fixed-foreperiod logic.
  - States: "No studies have so far investigated how different countdown procedures prior to start signal affect monitored reaction time."
- **Tønnessen, Haugen & Shalfawi 2013** [Tonnessen2013] (*J Strength Cond Res* 27:885–892) [V-ABS]: 1,319 sprinters, WCH 2003–2009, Seiko "silent gun" timing; RT men 0.166 ± 0.030 s, women 0.176 ± 0.034 s; RT vs 100 m time r = 0.292 (men), 0.328 (women).

**Unknown [U]:**
- Whether the hold was measured from the onset or the offset of "set".
- Audio vs video frames, and the frame rate.
- Rater reliability.
- How restarts were handled.
- Whether correlations were pooled at athlete level (clustering ignored); P < 0.001 at r ≈ 0.16 suggests so, which is an inference.

**What Haugen leaves open:**
- No tail or DQ-risk analysis, only IQR trends.
- No expectation model.
- No measurement-error estimate.
- Only 2010–2011 data fall under zero tolerance.
- No released hold data.

---

## 2. Hold-time and reaction-time studies in racing sports

### 2.1 Hold (foreperiod) studies

**Otsuka, Kurihara & Isaka (2017)** [Otsuka2017], *Front Psychol* 8:810 [V-FT, PMC5435752].

*Field arm:*
- "88 male and female large-scale 100-m races ... recorded from publicly available television broadcasts" of OG 2012 and WCH 2011/2013/2015, "from heats to finals".
- 83 races kept where the set and start signal "could be clearly heard without the voice of the announcer".
- "analyzed by intervals of 10 ms using sound editing software (EDIUS Neo 3)"; "Onsets of the starter's set and gun signals were visually determined by sound wave information".
- Result: "1.780 ± 0.017 s (SD: 0.158 s)".
- No per-race data or data statement.
- Limitation (authors'): broadcast capture means the measured foreperiods "likely involve some error compared to that which sprinters actually heard".

*Lab arm:*
- 20 experienced male sprinters, one start per foreperiod (1.465/1.622/1.780/1.938/2.096 s = mean −2…+2 SD), randomized.
- 20% catch trials; 70 dB warning tone; 120 dB horn about 30 cm from the ear.
- RT from force-plate onset (baseline mean ± adaptive SD, 1000 Hz).

*Results:*
- Whole-body RT 156 ± 8 / 133 ± 6 / 125 ± 4 / 129 ± 5 / 117 ± 5 ms; F(4,76) = 33.6, partial η² = 0.302.
- At the longest foreperiod the shoulders "initially reacted within 100 ms". One participant's front shoulder reacted at 61 ms, which "might lead to a false start motion in competitive races".

*Recommendations:*
- Record foreperiod "in addition to wind speed".
- Fix it (e.g., 1.769 s) with catch trials.

**Dalmaijer, Nijenhuis & Van der Stigchel (2015; 2016)** [Dalmaijer2015; Dalmaijer2016], *Front Psychol* [V-FT, PMC4623299 / PMC4746233].
- **Data.** Speed skating 500 m, Vancouver 2010. Ready-start intervals taken "directly from the audio trace of the television broadcast ... by visual inspection in Audacity", from "the onset of the referee saying 'Ready?'" to "the onset of the starting shot".
- **Result.** Longer intervals went with worse finishing times: r² = 0.05 (men), 0.27 (women); +299 ms (men) and +672 ms (women) per s.
- **Framing.** "Alerting": RT is best about 500 ms after a cue and worsens over several seconds.
- **Proposal.** A fixed, computer-controlled interval, acknowledging it "will increase athletes' ability to anticipate".
- **2016 commentary.** Within-skater differences: +174 ms per s of finish time (p = 0.003, R² = 12%) and +59 ms per s at 100 m (R² = 13%). "Alerting could only be part of the story."

**Julin (2003)** [Julin2003NSA], *New Stud Athl* 18(1):7–10 [V-FT]. A rules officer's viewpoint.
- **Hold length.** At least 2 s is needed; consistent practice gives "a holding time varying between 2.0 and 2.7 seconds". "That span of 0.7 s should be compared to the diminutive time window of 0.04 s" (perfect guess 0.10 vs normal RT ~0.14).
- **Long holds.** "Often it has been stated that a long holding time creates false starts - but actually, it is the other way around!"
- **Anecdotes.** Munich 1972 had "just two (2!!) recalls in the 228 races". At the 1988 US Olympic Trials holds were "never below 2.5 seconds and the average was something like 2.7".
- **Fairness claim.** A start whose SIS spread exceeds 0.04 s "has not been fair".
- An informal time-uncertainty (hazard-style) argument that has never been tested with data.

**Practitioner guidance** [Zemper2023Starters; WA2022StartingGuidelines].
- **Zemper's USATF monograph** [V-FT]:
  - "The 'hold' is the length of time between the initiation of the 'Set' command and the start signal".
  - Minimum 1.5 s; recommended "1.8 to 2.4 or 2.5 seconds".
  - Never fire "at the exact same length of time after the 'Set' command. Athletes will pick up on this".
  - "For any starter, the fastest starts (i.e., the shortest hold times) tend to be the first start of the day and any start after a false start."
- **World Athletics Starting Guidelines** (Dec 2022, §6.2; the same wording appears in 2012 and 2018): "There is no perfect holding time in the set position" [V-FT via sports search pass]. No number is given.

**Racing-start psychology in the lab.**
- **Crowe & Kent 2019** [Crowe2019], *QJEP* 72(11):2672–2679 [V-ABS]. Motivated explicitly by "Set"/"Go" starts. No one-week transfer of auditory foreperiod-distribution learning, and limited same-session transfer.
- **Crowe, Los, Schindler & Kent 2021** [Crowe2021], *QJEP* 74(8):1432–1438 [V-FT via datasets search pass]. Auditory tones; foreperiods 0.4–1.6 s. Transfer occurred with an unfilled foreperiod but not a filled one.
- **Yarrow et al. 2026** [Yarrow2026], PsyArXiv [V-ABS]. Opens "as when a sprinter learns the constant foreperiod from set to go". Models the RT/anticipation trade-off with a trial-by-trial subjective foreperiod distribution. The best model follows a subjective hazard and then saturates. Lab data only; open data and code (datasets.md B1).

### 2.2 Reaction-time distribution and rule-effect studies (none model the hold)

- **Fiore, Schifano & Yan (2025)** [Fiore2025], *The American Statistician* 79(4):500–507. Numbers checked in the arXiv 2506.11460 v1 full text [V-FT].
  - **Data.** WCH 1999–2023; men's 100 m and 110 mH semis and finals, n = 776. Positive DQ RTs kept; negative RTs dropped.
  - **Model.** Generalized gamma GAMLSS with a venue effect on log µ and a heat effect on log σ.
    - Men: β0 = −1.910, γ0 = −2.200, ν = −1.178, τ_v = 0.058, **τ_h = 0.320**.
    - Women: n = 732, τ_h = 0.111.
  - **Tail.** P(RT < 0.100) = 2.76·10⁻³ for men ("one in 362 starts"); 5.46·10⁻⁴ for women.
  - **Barriers.** 0.094 s (men) and 0.102 s (women) at a 10⁻³ tail.
  - **2022.** RTs faster than 2019, 2023 and national meets for the same athletes. Attributed to timing systems; no vendor is named.
  - **No foreperiod covariate.** The heat effect is speculatively attributed to "faster athletes influencing others".
  - **Rule-history error.** They say zero tolerance began in 2011; it began 1 Jan 2010 (§3).
  - *Our reproduction:* their men's tail probability comes out at 2.78·10⁻³ from the published parameters (`lit/planning/gg_tail_planning.py`). In that model the tail is dominated by heat-level dispersion: the 90th-percentile heat has about 18× the median heat's P(RT < 0.100).
- **Brosnan, Hayes & Harrison (2017)** [Brosnan2017], *J Sports Sci* 35(10):929–935 [V-ABS].
  - World and European Championships 1999–2014; ex-Gaussian fits compared across "sex, ruling periods and competition rounds".
  - "Revised RT thresholds of 115 ms and 119 ms", i.e. raise the limit and make it sex-specific.
  - The abstract does not state the direction of the rule-period effect [U].
- **Han, Zhou & Zhang (2025)** [Han2025IJPAS], *Int J Perf Anal Sport* [V-ABS].
  - 100 m semis and finals across 7 OG, 12 WCH and 13 U20 WCH, 2000–2024.
  - Zero tolerance "significantly reduced the average reaction time" (β = −0.004). This is the **opposite direction** to Haugen and Brosnan, and is plausibly confounded by detector changes (§4).
- **Tønnessen et al. 2013** (above).
- **Collet 1999** [Collet1999] [V-ABS]: RT falls from heats to final in finalists; RT is "a skill dependent upon experience and learning".
- **Mitašík et al. 2020** [Mitasik2020] [V-FT via search pass]: 200 m, WCH 1999–2009 vs 2011–2019; slower RTs after the rule change.
- **Ntolaptsis & Panoutsakopoulos 2021** [Ntolaptsis2021] [V-FT via search pass]: 60 mH; no rule-change difference; RT vs time r = 0.228.
- **Bezodis, Willwacher & Salo 2019** [Bezodis2019] [V-FT via search pass]: narrative review. RT is affected by rule changes, "holding time", signal intensity and focus of attention, in one sentence.

### 2.3 How fast can a legitimate start be?

- **Mero & Komi 1990** [MeroKomi1990] [V-ABS]: 8 sprinters; total RT about 0.12 s (horizontal force 10% above baseline). Often named as the basis of the 100 ms rule [S].
- **Pain & Hibbs 2007** [PainHibbs2007] [V-FT, Loughborough accepted manuscript via search pass].
  - 9 athletes; piezoelectric footplates at 2000 Hz.
  - "20% of all starts in the first two conditions had a reaction time of less than 100 ms". One athlete's mean was 87 ms.
  - Detection method matters: "Using a simple threshold of force detection increased the measure of reaction time by 26 ms on average"; video at 500 Hz added 60 ms.
  - Rear-leg premotor times were about 65 ms.
  - Their foreperiod was random within a 3–4 s window, which they use to argue sub-100 ms RTs were not guesses.
  - "Until 1990 the false start criterion was 120 ms."
- **Komi, Ishikawa & Salmi 2009** [Komi2009NSA], IAAF-commissioned. Full text not accessed. The WA news summary [S] reports reactions "as fast as 80ms" and a recommendation to lower the limit "to 80 or 85ms". A secondary blog says a 25 kg threshold delayed RT by 35 ms [S].
- **Milloz, Harrison & Hayes 2020** [Milloz2020ISBS] [V-FT via search pass].
  - Hand-force plate vs a WA-certified SIS (TimeTronics): 0.067 ± 0.035 s vs 0.138 ± 0.032 s.
  - For SIS readings of 100–119 ms, hand RT was 0.047 s.
  - Related University of Limerick patent: US 11,517,804.
- **Brown, Kenwell, Maraj & Collins 2008** [Brown2008Go] [V-FT, author PDF].
  - Go-signal intensity 80/100/120 dB gave RT 138/128/120 ms; startle trials 18 ms faster.
  - Their foreperiod was **fixed** at 3 s, with about 10% catch trials.
  - Athens 2004: lane 1 (nearest the pistol) 160 ms vs lanes 2–8 175 ± 5 ms.

---

## 3. False-start rules: history, origin of 0.100 s, critiques

**Timeline** (sports search pass, from WA news items and rulebooks; [V-FT/web] unless noted):

| Date | Rule | Source |
|---|---|---|
| 1921 IAAF | "On your marks", "Ready", gun "after a pause of at least 2 seconds" | Zemper 2008 rules history [S] |
| 1934 NCAA | "a minimum two second hold" | Zemper 2008 [S] |
| up to 1990 | False-start RT criterion 120 ms, then 100 ms | Pain & Hibbs 2007 [V-FT] |
| pre-2003 | DQ on an athlete's own 2nd false start | Lipps 2011 [V-FT]; Zemper [V-FT] |
| 1 Jan 2003 | First false start charged to the field; any later one → DQ (adopted 2001) | WA news; Julin 2003 [V-FT] |
| 12 Aug 2009 | IAAF Congress, Berlin, vote 97–55: zero tolerance | WA news [V-FT/web] |
| 1 Jan 2010 | Zero tolerance in force (then Rule 162.7; now TR 16.8). Combined events keep one false start per race (TR 39.8.3, 2026) | WA rulebook 2026 [V-FT] |
| 2021–2025 | TR 16 amendments (16.5, 16.5.3, 16.8 Note, 16.9, 16.10); 0.100 s unchanged | WA amendment table [V-FT] |
| Aug 2026 | Ultimate Championship regulations: certified SIS with auto-recall; no start-rule change | WA C3.1 [V-FT] |

**False-start counts** in events ≤ 400 m incl. relays (IAAF "Comparison of false starts") [V-FT]:
- 2003 rule: WCH 2007 26; OG 2008 33; WCH 2009 25 (mean 28).
- Zero tolerance: WCH 2011 10.

**Current text** (Book C, 1 Jul 2026) [V-FT, rulebook text]:
- TR 16.3: "Once the Starter is satisfied that all athletes are steady in the 'Set' position, the gun shall be fired."
- Official commentary: "There is no rule that enables to determine the time that elapses between ... the command 'Set' and the gun shot."
- TR 16.6: a possible false start is signalled "when the reaction time is less than 0.100 second" by a certified SIS.
- TR 16.7 defines commencement. TR 16.8: "Except in Combined Events, any athlete responsible for a false start shall be disqualified by the Starter."
- **The rulebook defines no onset criterion, threshold or algorithm for RT, and no sex-specific threshold.**

**Origin of 0.100 s.** Poorly documented. Accounts:
- Mero & Komi 1990 [S].
- "normal human reaction time to sound is in the range of 0.14-0.16 second" minus "a 'safety factor' of 0.04 second" (Zemper, no citation) [V-FT quote; history S].
- 120 ms until 1990 (Pain & Hibbs) [V-FT].
- Milloz et al. 2021 [Milloz2021] (review, [V-ABS]): "The lack of scientific evidence about the definition of the 100 ms false start threshold by the WA is criticized in the literature". Its body, and whatever it says about foreperiods, could not be read [U].

**Critiques:**
- **Lipps et al. 2011** [Lipps2011] [V-FT, PMC3198384]:
  - Beijing 2008 (Swiss Timing/Omega). The threshold value was withheld: "this kind of information is not public"; 25 kgf is assumed as the de facto standard.
  - 99.9% lower bounds: 109 ms (men), 121 ms (women). Women get a 21 ms "window of opportunity".
  - Proposal: "a 22% lower starting block force threshold for women".
- **Mirshams Shahshahani et al. 2018** [MirshamsShahshahani2018] [V-FT, PMC6021049]: OG minimum RTs fell 2004 → 2016, and the sex gap vanished in 2012. Attributed to Swiss Timing reducing the (unpublished) force threshold.
- **Brosnan 2017** (raise the limit) vs **Komi 2009 / Fiore 2025** (lower it): directly opposed conclusions from different data and distributional assumptions.

---

## 4. How RT is measured at championships

**Who timed what** (sports search pass) [V-FT/web unless noted]:

| Competitions | Timer / SIS |
|---|---|
| World Championships 1987–2025, every edition | Seiko. New "starting information system" introduced at Doha 2019 (Seiko site). WA-certified block FL-6000 |
| Olympic Games 1996–2004 | Swatch (Swiss Timing technical) |
| Olympic Games 2008–2024; Diamond League 2010– | Omega / Swiss Timing |
| National and lower levels | FinishLynx ReacTime (accelerometer), TimeTronics FalseStart III Pro, others |

**Detection methods** (what is public):

- **Seiko.**
  - *Patent JP2759769B2* (Seiko Precision; filed 1995; inventors Yokokura & Takane) [V-FT, patent text]:
    - 1 kHz sampling.
    - A comparator fires when the block signal exceeds its own ±25 ms moving average, delayed 50 ms, by a 3 kg-equivalent margin. This detects the newly generated 3–25 Hz components of a start.
    - It replaced a conventional absolute threshold of 23 kg. The patent notes athletes at rest apply "about 5 kg to 15 kg".
    - Outputs from −0.5 s to +0.1 s around the gun count as illegal starts. Earlier outputs (the move into the "ready" = set position) are cancelled.
  - *Yokokura 2000* (Trans SICE 36(2):159–164) [V-ABS]: the conventional threshold was "about 200 to 400N".
  - *Seiko RM-200 catalogue* [V-FT]: RT to 1/1000 s; the signal detects changes "regardless of the athlete's body weight"; results go to the starter's headset; auto-recall.
  - *Pain & Hibbs 2007* [V-FT]: Seiko "in the past used a 20 kg threshold above baseline ... More recently ... steepest rise of the curve". Whether today's system still follows the 1995 patent is [U].
- **Omega / Swiss Timing.**
  - 1984: first pressure-based device [V-FT/web].
  - Beijing 2008: undisclosed force threshold (Lipps) [V-FT].
  - *Patent US 8,992,386* (priority June 2011): "no longer depends on a determined force threshold, but only on the variation in the force on the block" [V-FT/web].
  - London 2012 press material: force on the back block; "without changing any settings" [V-FT/web].
  - *ASC3 datasheet (2015)*: RTs recorded from 0.3 s before to 0.7 s after the gun; 1 ms precision; block speaker gunshot "114 dB @ 1m"; threshold undisclosed [V-FT].
  - Omega marketing: force sampled "4,000 times per second" [V-FT/web].
- **FinishLynx.** Accelerometer threshold "illustratively at about 1.5 g" (US 6,002,336), which it contrasts with force systems at about 250 N [V-FT/web].
- **Certification.** No public WA specification of detection criteria or test protocol was found [V-FT by absence]. Willwacher et al. 2013 [Willwacher2013] built a pneumatic test rig from 438 recorded starts and flagged "the need for further improvements ... especially with respect to the criterion" [V-ABS].
- **Historical thresholds.** "30kg at the Munich 1972 Olympic Games", later "27kg in Los Angeles 1984", per a WA/Leeds Beckett biomechanics report citing Young 2001 [V-FT in the report; primary not checked].

**Consequences for analysis.**
- Official RT = physiological latency + criterion-dependent detection delay.
  - That delay is +26 ms for a threshold vs an onset algorithm (Pain & Hibbs) and about 70 ms for foot blocks vs hand force (Milloz 2020).
  - It can differ by sex (Lipps; Mirshams Shahshahani) and by meet (Fiore; our data pipeline finds championship offsets spanning 42 ms, STATUS 00:10).
- **Force detection and temporal preparation can interact** (§5.7).

**Speakers and the "silent gun"** (conflicting claims):
- Omega: speakers "since 1984" [V-FT via Brown 2008].
- Atlanta 1996: athletes heard the air-borne gun (Julin & Dapena 2003) [S].
- Athens 2004: pistol near lane 1 plus speakers; a lane-1 advantage (Brown 2008) [V-FT].
- Haugen & Buchheit say "1995" [V-FT quote]; Lipps says Beijing 2008 was "the first" [V-FT quote]; Fiore says "2010" [V-FT quote].
- **Working assumption:** sound-travel lane effects are negligible from about 2008–10. Keep lane as a covariate.

**2022 and 2025 anomalies.**
- WA said the Oregon 2022 equipment was "functioning as normal". Per LetsRun, timers said it was the same system as the previous three Worlds and calibrated correctly [S; source 403].
- Tokyo 2025 slow RTs are discussed only on forums [S/U].
- **No primary documentation of a configuration change was found.** Use championship fixed effects. The Seiko waveform images allow a direct check of detection latency: the red detection marker vs the visible force rise.

---

## 5. Cognitive science of the foreperiod

Source notes (about 95 papers, with verbatim quotes) are in `lit/notes/lit_notes_cogsci.md`. Sports-side notes are in `lit/notes/lit_notes_sports.md`. The most current comprehensive review is **Bausenhart & Ulrich 2026** [Bausenhart2026Prepared] [V-FT].

### 5.1 Fixed vs variable foreperiods

- **The classic dissociation.**
  - Fixed foreperiod: RT *rises* with foreperiod.
  - Variable foreperiod: RT *falls* with foreperiod (Woodrow 1914; Karlin 1959; Drazin 1961; review Niemi & Näätänen 1981 [Niemi1981Foreperiod]) [S / V-ABS].
  - Los, Kruijne & Meeter 2014 [V-FT]: "mean RT increases in the constant-FP paradigm, but decreases in the variable-FP paradigm, typically according to an exponential decay function".
- **Why fixed foreperiods cost more as they lengthen.** Preparation spreads over a "range of expected moments" that grows roughly in proportion to the foreperiod: the scalar property (Treisman 1964 and Gibbon 1977, as cited by Bausenhart & Ulrich 2026; not read by us). Longer fixed foreperiods give less precise preparation (Bausenhart & Ulrich 2026) [V-FT].
- **Curve shape.**
  - Houshmand Chatroudi, Mioni & Yotsumoto 2024 [HoushmandChatroudi2024Nonlinearity] [V-FT]: n = 109, uniform foreperiods 0.48–1.92 s. A 3-parameter exponential decay beats linear or log-linear fits. **Model the foreperiod nonlinearly.**
  - Karlin 1959 (via Los 2014) [S]: when the foreperiod range is small relative to its mean, the RT–foreperiod function flattens. Championship holds have a CV of about 0.09 (0.158/1.78).
- **Alerting vs expectancy.**
  - Dalmaijer et al. 2015 [V-FT] frame the skating result as *alerting*, a non-specific arousal boost that decays over seconds, as distinct from temporal expectancy (citing Posner & Boies 1971; Sanders 1998).
  - Alerting predicts a monotonic *increase* of RT with hold, the same sign as Haugen.
- **Leg-extension analogue.** Fukushi & Ohtsuki 2004 [Fukushi2004Independence] [V-ABS]: maximal isometric leg extension to a tone after 0.5–10 s foreperiods reproduces the constant/variable dissociation, and force is controlled independently of RT.

### 5.2 Conditional probability (hazard)

- **Definition.** h(t) = f(t)/(1 − F(t)): the probability the signal occurs now, given it has not occurred yet.
- **The expectancy account.** Rising hazard over a variable foreperiod explains the downward variable-foreperiod function (Elithorn & Lawrence 1955; Näätänen 1970; Luce 1986) [S / V-ABS].
- **Non-aging distributions.** Exponential distributions have constant hazard and "can strongly reduce or even abolish the variable FP effect" (Bausenhart & Ulrich 2026, citing Näätänen 1970, 1971; Nickerson & Burnham 1969; Trillenberg et al. 2000; and others) [V-FT].
- **The closest classic analogue: Trillenberg et al. 2000** [Trillenberg2000Cnv] [V-ABS].
  - Foreperiods 1.3/1.95/2.6 s under aging, non-aging and *Gaussian* distributions, which almost exactly brackets championship holds.
  - RTs were "determined by the probability of the imperative stimulus".
  - Digitized means in the fMTP supplement [V-FT, data file]:
    - Gaussian: 337/274/290 ms, a **rebound after the mode**;
    - aging: 339/305/302 ms;
    - non-aging: 297/291/294 ms.
- **Catch trials matter for the hazard.**
  - With catch trials the CDF ceiling is 1 − P(catch), so the hazard stays finite at the right tail (Grabenhorst 2019 [V-FT]).
  - **In athletics, aborted starts ("stand up") act as catch trials.** A small abort probability makes the objective hazard peak just above the modal hold and then fall (search-pass computations; see §5.11).

### 5.3 Subjective hazard and neural correlates

- **Janssen & Shadlen 2005** [Janssen2005Representation] [V-FT, submitted version via Lirias].
  - "Because the brain cannot estimate elapsed time precisely, the mathematical functions are replaced by blurred versions, which we term subjective hazard rates"; "The Weber fraction was fixed ... φ = 0.26".
  - Unimodal go times 0.5–2 s: "reaction time decreased with longer waiting times". Partial r(RT, anticipation) = −0.24.
  - LIP activity tracks the subjective hazard.
- **Cui, Stetson, Montague & Eagleman 2009** [Cui2009Readygo] [V-ABS]. Framed as "when a sprinter waits for the starting pistol". The post-go SMA signal amplitude encodes the *cumulative* hazard; this vanishes with a countdown.
- **Other neural and behavioural links:**
  - Coull 2009; Coull, Cotti & Vidal 2016 (parietal/frontal tracking of evolving hazard) [V-ABS].
  - Nobre, Correa & Coull 2007; Nobre & van Ede 2018 (reviews) [V-ABS].
  - Herbst, Fiedler & Obleser 2018 (EEG hazard tracking from SMA; auditory targets; foreperiod mean 1.8 s) [V-ABS].
  - Schoffelen et al. 2005 (corticospinal coherence tracks readiness) [V-ABS].
  - Tsunoda & Kakei 2008 (uniform 1–2 s foreperiod: RT inversely related to hazard; LATER-model analysis) [V-ABS].
  - Oswal, Ogden & Carpenter 2007 (LATER: expectation is low-pass filtered) [V-ABS].

### 5.4 Reciprocal-PDF and Bayesian accounts

- **Grabenhorst et al. 2019** [Grabenhorst2019Anticipation] [V-FT].
  - Set–go task; go times 0.4–1.4 s from exponential or flipped-exponential PDFs; 9.09% catch trials; vision, audition and somatosensation.
  - "perceptual systems use the reciprocal PDF and not the HR".
  - The standard "temporally-blurred, mirrored HR" model "failed to fit the data adequately".
  - "Probabilistic blurring" (uncertainty set by the PDF) beat Weber blurring; φ = 0.21 was used for temporal blurring.
- **Grabenhorst et al. 2021** [Grabenhorst2021Two] [V-ABS; methods V-FT\*]. Separates *whether* (catch probability; "highly dynamic and monotonically increases across time") from *when* (PDF). "The HR fails to account for behavior."
- **Grabenhorst et al. 2025** [Grabenhorst2025Neural] [V-ABS]. MEG: RT "approximates the event probability density function, but not hazard rate".
- **Grabenhorst et al. 2026** [Grabenhorst2026Anticipation] [V-FT].
  - Go-time spans of 1, 1.7 and 2.4 s (up to 0.4–2.8 s), auditory and visual.
  - RT "scales with the event distribution", and precision is scale invariant, which "contradicts Weber's law".
  - For uniform distributions RT is U-shaped.
  - Open CC0 data (datasets.md B9).
- **Bayesian observers.** Visalli, Capizzi, Ambrosini et al. 2019/2021/2023 [Visalli2019Bayesian; Visalli2021Electroencephalographic; Visalli2023Plike] [V-ABS]: ideal-observer models of how temporal priors are *updated* trial by trial, including Gaussian foreperiod distributions with means up to 2.1 s. This is a citable model class for "starter-specific" expectation learning. Open data.
- **Conditional (sequential) statistics.** Huang & Chao 2025 [Huang2025Human] [V-ABS]: RT integrates unconditional and conditional (FP1 → FP2) timing statistics. An athlete may combine a starter's overall hold distribution with the hold of an aborted first attempt.

### 5.5 Memory, trace conditioning and sequential effects

- **The sequential effect.** RT is slower when the previous foreperiod was longer than the current one. The asymmetry is largest for short current foreperiods and vanishes at the longest (Los et al. 2014 [V-FT]; Karlin 1959; Vallesi & Shallice 2007).
- **Size.** 24 ms at a 400 ms current foreperiod vs 8 ms at 1,400 ms (Han & Proctor 2022a [V-FT via search pass]). About −9 ms per step in continuous distributions (Welhaf 2026 [V-FT via search pass]). Weaker for dense foreperiod sets (Steinborn et al. 2008 [S]).
- **Trace conditioning / multiple-trace theory (MTP).**
  - Los & van den Heuvel 2001; Los, Knol & Boers 2001; Los, Kruijne & Meeter 2014 [V-ABS].
  - The warning signal acts as a conditioned stimulus. During the foreperiod "inhibition is applied to prevent premature response".
  - Each trial leaves a memory trace.
- **Hazard vs history.**
  - Los, Kruijne & Meeter 2017 [Los2017Hazard] [V-ABS]: "temporal preparation is driven by past experience, not by current hazard".
  - Mattiesing et al. 2017 [Mattiesing2017Timing] [V-ABS]: acquisition effects persist **one week** later.
  - Crowe & Kent 2019 [V-ABS]: for **auditory** signals, no one-week transfer.
- **fMTP.** Salet et al. 2022 [Salet2022Fmtp] [V-ABS article; V-FT OSF supplement].
  - A formal model spanning seconds to weeks.
  - Critical experiment with a Gaussian distribution at 1.3/1.95/2.6 s: RT 361.8 → 330.4 → 328.9 ms, "no change in RT from FP2 to FP3" (BF = 94.7 for the null). This deviates from the hazard prediction.
  - Code for hazard, subjective hazard and fMTP is open.
- **Dual-process evidence.**
  - Vallesi & Shallice 2007 [V-ABS]: sequential effects appear at age 4–5; the foreperiod effect develops later.
  - Vallesi, Shallice & Walsh 2007 [V-ABS]: right-DLPFC TMS removes the foreperiod effect, not the sequential effect.
  - So there is a strategic hazard-monitoring component and an automatic sequential component (Bausenhart & Ulrich 2026 [V-FT]).
- **Cue specificity.**
  - Los et al. 2021 [Los2021Warning] [V-ABS]: only highly distinct warning stimuli carry separate foreperiod expectations.
  - Steinborn et al. 2009 [V-ABS]: switching warning-signal modality attenuates sequential effects.
  - Implication: a starter's voice may act as a retrieval cue only if distinctive enough.

### 5.6 Anticipations, false alarms and the 100 ms convention

- **Models of premature responding:**
  - Deadline model (Ollman & Billington 1972 [S]): respond at detection or at a planned deadline, whichever comes first.
  - Race between time estimation and detection (Kornblum 1973; Hsu 2005, who estimates the true/anticipatory cut-off from data [V-ABS]; Tiefenau et al. 2006 [V-ABS]).
  - Motor Readiness Model (Näätänen 1971): readiness "approaches—but does not prematurely cross—the action limit", and "can also account for premature responses if motor readiness is noisy and approaches the motor limit closely" (Bausenhart & Ulrich 2026) [V-FT].
- **Anticipations rise with waiting time:**
  - **Tucker et al. 2009** [Tucker2009Variable] [V-ABS; details V-FT\*]: PVT with random 2–10 s waits. Mean RT fell 69.31 ms and false starts rose 5.71 percentage points as the wait grew.
  - **Leow et al. 2018** [Leow2018Triggering] [V-FT]: with a 114 dB go signal, "the probability of falsely starting a response increased as the IS was presented later". In predictable blocks at the latest go time (1.8 s), mean RT was 103 ms with 26% false starts; in unpredictable blocks false starts were < 5%.
  - Boulinguez et al. 2008 [V-ABS]: "77%" of EMG-detected errors were responses to the *warning* signal. Covert "twitches" are real.
- **The 100 ms convention.**
  - The PVT defines "false starts" as responses without a stimulus or RT < 100 ms (Basner & Dinges 2011 [V-ABS; definition V-FT\*]), the same number World Athletics uses.
  - Whelan 2008 [S]: fast-RT cut-offs are "between 100 ms and 200 ms", a task-dependent convention rather than a constant.
- **Consequence for field data.** DQ'd responses are removed. If anticipations rise with hold length, valid RTs at long holds are left-truncated, which inflates mean RT at long holds and can create a positive RT–hold slope even when readiness rises (§5.11). Use censored or race-model analyses.

### 5.7 Response force and preparation (why detection method matters)

- **Mattes & Ulrich 1997** [Mattes1997Response] [V-ABS; design V-FT via Bausenhart & Ulrich 2026].
  - Foreperiods 500, 1,750 and 3,000 ms; constant vs variable.
  - "responses were weaker when temporal preparation was high (short constant or long variable FPs) and stronger when preparation was low."
- **Van der Lubbe et al. 2004** [VanderLubbe2004Being] [V-ABS]: force is higher after brief current foreperiods, and does not follow sequential RT effects.
- **Implication (inference, untested).** Start systems fire on force or force change. If highly prepared starts are "softer", official RT could carry a *preparation-dependent detection lag* that runs against the true latency effect. Testable with the Seiko force traces: slope at onset vs hold.

### 5.8 StartReact: loud go signals release prepared actions early

- **Valls-Solé et al. 1999** [VallsSole1999Patterned] [V-ABS; numbers V-FT\*]. A 130 dB stimulus "almost halved" latency: rising onto tiptoe 237.6 → 122.6 ms. The shortest agonist latency was 65 ms.
- **Latencies under startle:**
  - Carlsen et al. 2004 [V-ABS]: prepared movements released early by startle.
  - Cressman et al. 2006 [V-ABS]: about 70 ms "regardless of FP" (2.5–5.5 s).
  - Carlsen & Maslovat 2026 [V-ABS]: "< 80 ms".
- **Release depends on expected timing.** **Carlsen & Mackinnon 2010** [Carlsen2010Motor] [V-FT]:
  - With 2–3 s variable foreperiods, a startle 1,500 ms before the expected go released the response in about 60% of trials, rising to about 90% at 500 and 150 ms.
  - Startle-released EMG onset was 92.5 ms vs 195.4 ms in control trials.
  - Preparation is scheduled by expected timing.
- **Expectation and loudness are confounded.** Leow et al. 2018 [V-FT] meta-analysis: SCM+ minus SCM− premotor RT −16.9 ms [−23.7, −10.1], and "foreperiod predictability can induce differences in RT that would be of similar size".
- **Sadler et al. 2022** composite [V-FT data via datasets search pass]: the mean startle-trial RT was about 0.085 s. Likely EMG onset [U].
- **In sprinting.** Brown et al. 2008 is the only sprint-start startle study found [V-FT; PubMed search 2026-09-28]. The block speaker plays the gun at 114 dB @ 1 m (Swiss Timing ASC3) [V-FT].
- **Synthesis.** Legitimate sub-0.100 s responses are plausible when readiness is maximal, and readiness is timed by expectation. **No study has tested hold-dependent sub-0.100 s probability in sprinting.**

### 5.9 Athletes and sports psychology

- **Attentional focus.**
  - Buckolz 1980 [V-ABS]: attend to response preparation.
  - Ille et al. 2013 [V-ABS] and Kovacs, Miles & Baweja 2018 [V-ABS]: an external focus shortens RT (premotor 157.75 vs 181.90 ms), a central effect.
- **Expertise.**
  - Wang et al. 2013 [V-ABS]: tennis players beat controls at short foreperiods; swimmers do not differ from tennis players.
  - Nuri et al. 2013 [V-ABS]: sprinters are better on auditory choice RT.
- **State.** Langner et al. 2010 [V-ABS]: fatigue slows RT overall but not temporal preparation.
- **Ageing.** Vallesi et al. 2009 [V-ABS] vs Welhaf 2026 [V-ABS]: mixed evidence that ageing removes the variable-foreperiod benefit. Relevant to masters athletics.
- **Gap.** No TMS or corticospinal-excitability study of the sprint "set" position was found. Candidate mechanisms for the costs of holding the set posture (Dalmaijer 2016's "subtle increase in muscle fatigue") are untested.

### 5.10 Rhythm

- Rhythm-based and interval-based predictions produce similar anticipatory effects, but only rhythms carry obligatory costs when violated (Breska & Deouell 2017) [V-ABS].
- The start has one warning and one go, so no periodic sequence. Rhythmic entrainment is unlikely to drive hold effects. A starter's "set" prosody or cadence (the "On your marks" → "Set" interval) is at most a weak retrieval cue. Exploratory only (search-pass assessment; inference).

### 5.11 Synthesis: what each account predicts for championship RT vs hold

Assumptions:
- Holds roughly Gaussian, mean 1.78 s, SD 0.158 s (Otsuka [V-FT]).
- Blur φ = 0.21–0.26.

The shapes below are **theoretical illustrations, not data and not for the abstract.** The literature search computed them first. I re-derived the key numbers independently in `lit/planning/fp_model_shapes.py` (output `fp_model_shapes.out.txt`):
- objective hazard at 1.465–2.096 s: 0.35 → 15.0;
- abort-adjusted hazard peaks at 2.05/2.02/1.96/1.92 s for c = 1/2/5/10%;
- blurred-PDF peak at 1.76/1.71/1.64 s for φ = 0.10/0.21/0.30.

| Account | RT–hold shape over ~1.3–2.2 s | Fastest at | Sign of linear r | Sub-0.100 s / false-start risk vs hold |
|---|---|---|---|---|
| Fixed-foreperiod time uncertainty, or alerting decay | rising | shortest holds | **+** (as Haugen) | anticipation (deadline) risk rises once the hold passes the athlete's internal deadline |
| Objective hazard, no aborts | steeply falling | longest holds | − | rises steeply with hold |
| Objective hazard with a small abort ("catch") rate | rise then collapse; peak at about 1.92–2.05 s for 10%–1% aborts | just above the modal hold | ≈ 0 / − | peaks just beyond the mode |
| Weber-blurred subjective hazard (φ 0.21–0.26) | falling, saturating | longest holds | − (weaker) | rises and flattens |
| Blurred reciprocal PDF (Grabenhorst) | asymmetric U; minimum about 1.71 s | slightly *below* the mean hold | **+** if most holds are above ~1.7 s | readiness peaks near the mode, so long holds give **slower valid RTs and more false starts** (a dissociation) |
| Memory / fMTP | falls to the mode, then plateau (lab: 361.8 → 330.4 → 328.9 ms) | from the mode on | weakly − | inhibition prevents premature responses; risk highest when the hold is long relative to the athlete's history |

**What discriminates them** in field data:
1. The location of the fastest hold relative to the modal hold.
2. The slope above the mode: PDF +, hazard −, fMTP ≈ 0.
3. Whether false-start probability and valid-RT speed move together (hazard) or dissociate (PDF).

**Why Haugen (field, r > 0) and Otsuka (lab, speeding) can both be right** (hypotheses):
1. **Design.** Otsuka's athletes saw five starts, one per foreperiod, with 20% catch trials and a 120 dB horn by the ear. Hazard-like elapsed-time expectancy could dominate.
2. **Selection.** Valid field RTs exclude DQ'd anticipations, which rise with the hold (§5.6).
3. **Rules.** Haugen's data are from pre-2010 regimes that permitted a first false start (per athlete to 2002, per field 2003–09), when anticipation strategies paid. Under zero tolerance, athletes may inhibit more as the hold lengthens (Motor Readiness / MTP inhibition).
4. **Force detection.** Softer, well-prepared responses may cross the threshold later (§5.7).
5. **Posture.** Fatigue or tremor in the set position, which no lab study models.

Each hypothesis is testable with official holds plus per-athlete RTs and force traces (novelty.md).

---

## 6. Start signals in other sports

Sports search pass, from rulebooks [V-FT unless noted].

| Sport | Hold rule | Type | RT threshold |
|---|---|---|---|
| Swimming (World Aquatics SW 4, 2023–25) | "When all swimmers are stationary, the starter shall give the starting signal." Speakers at each block | Variable, starter-controlled (like athletics) | None for individual starts. Relay take-off tolerance −0.03 s is a *device* differential (Daktronics patent) |
| Speed skating, long track (ISU 2024, Rule 253 §3.2) | "distinct interval ... should be between 1 and 1.5 seconds" after stillness | Codified narrow window | Starter judgement; warning, then DQ |
| Short track (ISU Comm. 2510, 2022) | Starter "will wait a defined period of time" | Near-fixed | Zero-false-start trial |
| Rowing (US Rowing 2023, 2-306) | "after a distinct and variable pause, calling out 'Go!'" | Codified variable | Crossing early = false start |
| Formula 1 (FIA light signals) | 5 red lights at 1 s intervals, then "a preset delay of between 0.2 and 3.0 seconds" | **Randomised** | Transponder jump-start detection [S] |
| Track cycling (UCI 3.2.016) | 50 s countdown; machine release | Fixed, fully predictable | n/a |
| Motorcycle speedway (Markowski et al. 2023) | Referee-controlled tape lift | Variable (not measured) | Warning |

Swimming RT research: auditory start training cut swim-start RT by 13 ± 9 ms (Papic et al. 2019 [V-ABS]). No swimming hold-time study was found.

**Takeaways.**
- Regulated hold distributions have sporting precedent: a window (ISU), a mandated variable pause (rowing), a random preset delay (F1).
- Speed skating is the only racing sport with a published field test of hold effects (Dalmaijer 2015/2016).

---

## 7. Automated measurement of start foreperiods: prior art and tools

- **Manual prior art only:**
  - Otsuka 2017: EDIUS waveform, 10 ms resolution, 83/88 races usable.
  - Dalmaijer 2015: Audacity.
  - Haugen 2013: method unknown.
- **Sports audio event detection** exists for other purposes but not for start foreperiods [V-ABS / metadata V]:
  - referee whistles: Kathirvel, Manikandan & Soman 2011, *IJCA*, doi:10.5120/1729-2340;
  - tennis events: Huang & Cox 2010, Interspeech, doi:10.21437/interspeech.2010-428; Yan et al. 2014, *Image Vis Comput*, doi:10.1016/j.imavis.2014.08.004.
- **Tools for the measurement pipeline** [metadata V]:
  - ASR: Whisper (Radford et al. 2023, ICML). Its word timestamps are coarse, so refine them with forced alignment (WhisperX: Bain et al. 2023, doi:10.21437/interspeech.2023-78; Montreal Forced Aligner: McAuliffe et al. 2017, doi:10.21437/interspeech.2017-1386).
  - Onset detection: Bello et al. 2005, doi:10.1109/tsa.2005.851998. librosa: McFee et al. 2015, doi:10.25080/majora-7b98e3ed-003.
  - Agreement statistics: Bland & Altman 1986; Koo & Li 2016 for ICC.
- **Ground truth now exists:** Seiko `Ready Time` for WCH 2022–25 and WIC 2024–25. The definition must still be confirmed (definitions.md §2).

---

## 8. Gaps: what nobody has done (as far as these searches show)

1. **Foreperiod-conditional false-start risk.** P(RT < 0.100 | hold) for legitimate responses, or DQ probability vs hold, in any sport.
2. **A field test of temporal-preparation theories** (hazard vs PDF vs memory), despite the sprint start being the textbook example (Cui 2009; Crowe & Kent 2019; Yarrow 2026).
3. **An automated, validated foreperiod measurement,** or any public hold-time dataset.
4. **Sequential or state-dependent holds.** Zemper's claim that holds are shortest at the first start of a session and after a false start is untested. Nor has any study tested athlete-level carry-over from a previous round's hold.
5. **Starter- or session-specific hold distributions** and their effect on RT.
6. **Hold-dependent force profiles** and the detection-lag interaction.
7. **The set-position physiology** (corticospinal excitability) during the hold.
8. **A quantitative evaluation of start-procedure designs** (fixed, jittered, non-aging, catch trials). Proposals so far are informal (Otsuka; Dalmaijer; Julin).
