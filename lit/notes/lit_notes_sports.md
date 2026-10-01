# lit notes: sports side (rules, RT measurement, critiques, other sports)

Written by the sports search pass of the literature review, 2026-09-28/29, for lit/review.md, lit/definitions.md and lit/novelty.md.
Local copies of every source (PDF plus .txt) are in `scratchpad/sports_src/`.

**Tags** (repo skill `literature-verification`):
- [V-FT]: I opened the full text and quote it verbatim or give the section.
- [V-FT/web]: a web page or patent read through WebFetch; the quotes are as the tool returned them, so certainty is slightly lower.
- [V-ABS]: abstract only.
- [S]: secondary source.
- [U]: unverified.

Cite published versions: Fiore et al. is *The American Statistician* 79(4):500–507 (2025), doi 10.1080/00031305.2025.2515869, with arXiv 2506.11460 as the open full text.

---

## 0. KEY TAKEAWAYS (read first)

1. **Hold time is unregulated, by design.** The official commentary under WA TR 16 (2026 book) says: "There is no rule
   that enables to determine the time that elapses … between the command 'Set' and the gun shot. The Starter shall let
   the athletes go once they are all motionless in the correct starting position." [V-FT] The WA Starting Guidelines
   (Dec 2022, §6.2; the same wording appears in 2012 and 2018) say: "There is no perfect holding time in the set
   position." [V-FT] So the foreperiod is a **starter-controlled, state-dependent variable**. Other sports codify it
   (item 9).
2. **Broadcast hold-time measurement has been done before, manually.**
   - Haugen et al. 2013: "Holding time calculations were based on television recordings from the analysed heats
     (n = 267)"; range 1.3–2.2 s [V-ABS].
   - **Otsuka et al. 2017** timed 83 100 m races (OG 2012; WCH 2011, 2013, 2015) from broadcast audio: "Onsets of the
     starter's set and gun signals were visually determined by sound wave information", "analyzed by intervals of
     10 ms" in EDIUS. Result: **FP = 1.780 ± 0.017 s (SE), SD 0.158 s** [V-FT, PMC5435752].
   - Consequence: angle (a) cannot claim to be the first audio-based measurement. It can claim to be **automated,
     validated (reliability against manual), scaled, and linked to per-athlete RT**.
3. **How to define the hold (practitioner sources).**
   - Zemper's IAAF-edition Starters monograph defines the hold as "the length of time between the **initiation** of the
     'Set' command and the firing of the gun"; timing should start "at the very beginning of the word 'Set'". It
     recommends 1.8–2.4/2.5 s, with a minimum of 1.5 s [V-FT].
   - Zemper also says: "For any starter, the fastest starts (i.e., the shortest hold times) tend to be the first start
     of the day and any start after a false start". This is a testable claim of **state-dependent starter behaviour**
     [V-FT].
4. **RT is defined only operationally.** TR 16.6 says a possible false start is signalled "when the reaction time is less
   than 0.100 second" as indicated by a *certified* SIS. **No public rule specifies the onset criterion or the threshold**
   [V-FT, by absence].
   - Vendors: Seiko (every WCH from 1987 to Tokyo 2025); Omega/Swiss Timing (OG 2008–2024, with Swatch as timekeeper
     1996–2004; Diamond League since 2010); FinishLynx (accelerometer); TimeTronics (a WA-certified SIS).
   - Detection algorithms differ and have changed over time:
     - absolute force threshold: "a 25 Kgf threshold … de facto standard" (Lipps 2011) [V-FT]; Seiko formerly used 20 kg
       above baseline (Pain & Hibbs 2007) [V-FT];
     - force change: Swiss Timing patent US 8,992,386 (priority June 2011), "no longer depends on a determined force
       threshold"; London 2012 blocks [V-FT/web];
     - accelerometer at about 1.5 g (Lynx patent US 6,002,336) [V-FT/web].
5. **How much the detection method moves the RT.**
   - A threshold criterion adds **26 ms** on average versus the onset algorithm; video (500 Hz) adds 60 ms (Pain & Hibbs
     2007) [V-FT].
   - A 25 kg threshold delays RT by 35 ms (Komi et al. 2009, reported by van Hooren) [S].
   - Hand-force onset is about 70 ms earlier than a WA-certified foot-block SIS: 0.067 ± 0.035 s vs 0.138 ± 0.032 s,
     63 trials (Milloz et al. 2020) [V-FT].
   - Mirshams Shahshahani et al. 2018 attribute the 2004→2016 fall in Olympic minimum RTs (and the disappearance of the
     sex gap in 2012) to reductions in the proprietary force threshold [V-FT].
6. **History of the threshold value.**
   - "Until 1990 the false start criterion was 120 ms" (Pain & Hibbs 2007, intro) [V-FT].
   - The 100 ms value is said to rest on Mero & Komi 1990 (8 Finnish sprinters; TRT about 0.12 s) [S via Fiore / van
     Hooren]. Zemper's alternative account is "normal RT 0.14–0.16 s minus a 0.04 s safety factor" [V-FT quote; history
     S].
7. **False-start rule timeline (verified).**
   - IAAF Congress, 1 Aug 2001: from **1 Jan 2003** the first false start is charged to the field.
   - Aug 2005: a zero-tolerance proposal was withdrawn.
   - **47th Congress, Berlin, 12 Aug 2009 (97–55): zero tolerance from 1 Jan 2010.** Combined Events still allow one
     false start per race (TR 39.8.3, 2026 book).
   - False starts in events of 400 m or less: 26 (WCH 2007), 33 (OG 2008), 25 (WCH 2009) vs 10 (WCH 2011).
8. **Threshold-critique numbers. None of these papers conditions on the foreperiod.**
   - Brosnan et al. 2017: 115 / 119 ms (men / women) from ex-Gaussian fits [V-ABS].
   - Lipps et al. 2011: 99.9% lower bounds of 109 / 121 ms; lower the women's force threshold by 22% [V-FT].
   - Komi et al. 2009: lower the limit to 80–85 ms [S/V-web].
   - Fiore et al. 2025: P(RT < 0.100) = 2.76e-3 for men (about 1 in 362 starts); barrier 0.094 s at a 1e-3 tail
     probability [V-FT].
   - Fiore et al.'s large heat-level random effect on σ (τ_h = 0.32) is a hook for foreperiod or starter effects.
9. **Other sports.**
   - Some codify the hold:
     - ISU long track Rule 253 §3.2(b): "distinct interval … **between 1 and 1.5 seconds**";
     - ISU short track: the Starter "will wait a **defined period of time**";
     - US Rowing 2-306: "after a **distinct and variable** pause";
     - FIA: after 5 red lights at 1 s intervals, "a **preset delay of between 0.2 and 3.0 seconds**";
     - UCI track TT/pursuit: a fixed 50 s countdown with machine release.
   - Swimming: "When all swimmers are stationary", with no interval and no RT threshold; the relay take-off tolerance
     of -0.03 s is a device differential.
   - **Athletics is the outlier: it strictly enforces an RT threshold but leaves the foreperiod entirely to the starter.**
10. **Julin 2003 already argued, qualitatively, from time uncertainty:**
    - "consistently applying Rule 162.2 will have … a holding time varying between 2.0 and 2.7 seconds";
    - "That span of 0.7 s should be compared to the diminutive time window of 0.04 s";
    - "Often it has been stated that a long holding time creates false starts - but actually, it is the other way
      around!"
    - Anecdotes: 1988 US Olympic Trials holds were never under 2.5 s (mean about 2.7 s) with few false starts; Munich
      1972 had 2 recalls in 228 races.
    - [V-FT of Julin; the underlying data are S.] This is prior art for the "wider FP window reduces guessing" argument,
      but it is informal and has no data model.

---

## 1. False-start rules: history and current text

### 1a. Timeline
| Date | Change | Source / tag |
|---|---|---|
| 1921 IAAF | Commands "On your marks", "Ready", gun "after a pause of at least 2 seconds" | Zemper 2008 rules history [V-FT of Zemper; S for the 1921 book] |
| 1934 NCAA | "a minimum two second hold" (count "1,001; 1,002; 1,003"); called up if not steady within 4 s | Zemper 2008 [V-FT/S] |
| 1975 | NCAA adopts "no false start" (high schools follow) | Zemper 2008 [V-FT/S] |
| 1984 | Omega "introducing the first false start detection device … measuring the pressure that each runner exerted against the starting block"; Omega says speakers behind each runner since 1984 | Swatch Group Omega page [V-FT/web]; Brown 2008 citing omegawatches.com [V-FT] |
| up to 1990 | False-start RT criterion 120 ms, then 100 ms | Pain & Hibbs 2007: "Until 1990 the false start criterion was 120 ms, based on these same studies." [V-FT] |
| pre-2003 | Individual rule: disqualified on the athlete's 2nd false start (e.g., Christie, Atlanta 1996) | Lipps 2011 intro [V-FT]; Zemper ("two to the individual", now Masters only) [V-FT] |
| 1 Aug 2001 | IAAF Congress (venue inferred: Edmonton, before WCH 2001) adopts: "The first false start in a race will be charged to the entire field, with a second resulting in the offending athlete, whoever they may be, being disqualified." | WA news 2 Aug 2001 [V-FT/web] |
| 1 Jan 2003 | In force: "Only one false start per race is allowed without the disqualification of the athlete(s) making the false start …". Combined Events: 2 per athlete | WA news 19 Jan 2003 [V-FT/web]; Julin 2003 [V-FT] |
| 3 Aug 2005 | Zero-tolerance proposal withdrawn after opposition ("the technology is such that all equipment is not the same", D. Littlewood) | WA news [V-FT/web] |
| 12 Aug 2009 | 47th IAAF Congress, Berlin: "Except in Combined Events, any athlete responsible for a False Start shall be disqualified." Yes 97, No 55 | WA news 28 Aug 2011 [V-FT/web] |
| 1 Jan 2010 | Zero tolerance in force (Rule 162.7). First senior outdoor WCH under it: Daegu 2011 (Bolt DQ in the 100 m final) | WA news [V-FT/web]; Seiko site [V-FT/web] |
| by Apr 2012 | Green card (start aborted, no athlete at fault) exists in the IAAF Starting Guidelines | IAAF Starting Guidelines Apr 2012 [V-FT]; introduction date [U] |
| 2021–2025 | TR 16 amendments: 16.10 (eff. 1 Nov 2021); 16.5.3 (eff. 1 Nov 2023); 16.5, 16.8 Note, 16.9 (25 Mar 2025); 16.5.3 (eff. 1 Nov 2025). **0.100 s unchanged** | WA Book C amendment table [V-FT] |
| 2026 | Ultimate Championship Technical Regulations (20 Aug 2026) §8.1.3: "Starting blocks fitted with a certified Start Information System including an automatic recall system"; **no start-rule change** | C3.1 regs [V-FT] |

**Error in Fiore et al.:** "Between 2007 and 2009, World Athletics allowed one false start warning … In 2011, this rule
was replaced with the stricter policy." In fact the 2003 rule (one false start per race) applied 2003–2009, and zero
tolerance began on 1 Jan 2010 [V-FT of Fiore vs the WA sources above].

### 1b. False-start counts (IAAF "Comparison of False Starts", PDF, 2011) [V-FT]
https://worldathletics.org/download/download?filename=58540761-210b-4685-8b38-21fd68f70430.pdf&urlSlug=comparison-of-false-starts
Covers all track events of 400 m or less including relays; combined events excluded.
- Under Rule 162.7 (2003 rule): WCH 2007 men 18, women 8 (total 26); OG 2008 men 26, women 7 (33); WCH 2009 men 18,
  women 7 (25). Average 28.
- WCH 2011 (zero tolerance): men 6, women 4 (10).
- Olympic 100 m / 100 mH / 110 mH false starts: 1 (2004), 1 (2008), 3 (2012), 2 (2016). Source: Mirshams Shahshahani
  et al. 2018, Fig 1 caption [V-FT].

### 1c. Current rule text (World Athletics Book C, C1.1 & C2.1, "01 JUL 2026") [V-FT]
Source: https://worldathletics.org/download/download?filename=0ed43077-8e08-492b-a4b3-267f27c18d0b.pdf (linked from
worldathletics.org/about-iaaf/documents/book-of-rules; retrieved 2026-09-28).
**Rule numbering caveat:** pdfplumber drops the margin numerals. Numbers below come from the book's internal
cross-references (e.g., CR 22 says "When a Start Information System is used … Rule 16.6 of the Technical Rules shall be
applied"). Ntolaptsis & Panoutsakopoulos 2021 also cite TR 16.6 (0.100 s) and TR 16.8 (disqualification).
- **TR 15.3/15.4 (blocks and SIS):** at World Rankings competitions (categories 1(a)(b)(c), 2(a)(b)) and for WR
  ratification, "the starting blocks shall be linked to a World Athletics certified Start Information System. This
  system is strongly recommended for other competitions."
- **TR 16.3 (crouch start), key sentence:** "At the 'Set' command, an athlete shall immediately rise to their final
  starting position retaining the contact of the hands with the ground and of the feet with the foot plates of the
  blocks. Once the Starter is satisfied that all athletes are steady in the 'Set' position, the gun shall be fired."
- **Commentary (no hold rule; verbatim):** "There is no rule that enables to determine the time that elapses between
  the commands 'On your marks' and 'Set' on one hand, and on the other hand, between the command 'Set' and the gun shot.
  The Starter shall let the athletes go once they are all motionless in the correct starting position. Which means that
  they may have, for certain starts, to fire the gun quite quickly, but on the other hand, they may also have to wait
  longer in order to make sure that they are all steady in their starting position."
  Also: "as soon as they are steady in their blocks, the Starter shall raise their arm in which they hold the gun, then
  they shall say 'Set'. They shall wait then for all the athletes to be steady and shall then fire the gun."
- **TR 16.5 (abort / discipline):** raising a hand or standing up without valid reason; not taking the final position
  "at once and without delay"; disturbing others "through sound, movement or otherwise". These carry a yellow card
  (red on a second offence), not a false start. A green card is shown when no athlete is at fault.
- **TR 16.6 (SIS; verbatim):** "When a World Athletics certified Start Information System is in use, the Starter and/or
  an assigned Recaller shall wear headphones in order to clearly hear the acoustic signal emitted when the System
  indicates a possible false start (i.e. when the reaction time is less than 0.100 second). As soon as the Starter
  and/or assigned Recaller hears the acoustic signal, and if the gun was fired, there shall be a recall and the Starter
  shall immediately examine the reaction times and other available information from the Start Information System in
  order to confirm which, if any, athlete(s) is/are responsible for the recall." Note: "the evidence of this equipment
  shall be used as a resource by the relevant officials to assist in making a correct decision."
- **TR 16.7 (definition of a false start):** "An athlete, after assuming a full and final starting position, shall not
  commence their start until after receiving the report of the gun." For a crouch start, commencement is "any motion by
  an athlete that includes or results in one or both feet losing contact with the foot plate(s) of the starting blocks
  or one or both hands losing contact with the ground". A continued movement begun before the gun is also a false start.
  On a "rolling start", if the Starter "is sure that the athlete's movement began before the report of the gun, a false
  start should be awarded."
- **TR 16.8:** "Except in Combined Events, any athlete responsible for a false start shall be disqualified by the
  Starter."
- **TR 39.8.3 (Combined Events):** "only one false start per race shall be allowed without the disqualification of the
  athlete(s) responsible for the false start. Any athlete(s) responsible for further false starts in the race shall be
  disqualified by the Starter."
- **CR 22 (Starter; loudspeakers):** "It is recommended, especially for staggered starts, that loudspeakers in the
  individual lanes be used for relaying the commands and the start and any recall signals to all athletes at the same
  time." Without loudspeakers the Starter stands about equidistant from all athletes, or the gun is placed there and
  "discharged by electric contact".
- **No sex-specific threshold** anywhere in the rules [V-FT, by absence]. Lipps 2011: "we could find no suggestion that
  sex-specific force thresholds are currently being used" [V-FT].

---

## 2. Origin of the 0.100 s limit, critiques, and sprint-RT studies

- **Mero & Komi 1990**, Eur J Appl Physiol 61:73–80. Eight male sprinters. "Total reaction time (TRT) was defined as
  the time from the gun signal until a horizontal force was produced with a value 10% above the base line." TRT was
  0.121 s (SD 0.014) with EMG on the front-leg group and 0.119 s (SD 0.011) on the rear-leg group; motor time 0.008–0.057
  s [V-ABS]. Often named as the empirical basis of the 100 ms rule [S: Fiore; van Hooren].
- **Pain & Hibbs 2007**, J Sports Sci 25:79–86. Open accepted manuscript on the Loughborough repository, CC BY-NC-ND
  [V-FT].
  - Setup: 9 athletes; piezoelectric footplates sampled at 2000 Hz; custom onset algorithm.
  - "Five of the athletes had mean reaction times of less than 100 ms in at least one condition and 20% of all starts in
    the first two conditions had a reaction time of less than 100 ms." Athlete 8's mean was 87 ms (SD 4) after removing
    2 likely guesses.
  - "Using a simple threshold of force detection increased the measure of reaction time by 26 ms on average. Using high
    speed video at 500 Hz to determine onset of first visible movement increased the measure of reaction time by 60 ms."
  - Rear-leg pre-motor times were about 65 ms, "comparable with the latencies seen in the startle reflex".
  - **Foreperiod in the protocol:** "the time between set and the start signal was chosen randomly by the starter in a
    window of three to four seconds duration, that started approximately one second after the subject was in the set
    position". Discussion: "the start gun is fired randomly in a three second window after the set. Athlete 8 would have
    needed to guess 8 times to an accuracy of 12 ms in 3000 to obtain this distribution." This is a time-uncertainty
    argument that sub-100 ms responses were not guesses.
  - Systems as of 2006/07: Seiko "in the past used a 20 kg threshold above baseline … More recently they have moved to
    using steepest rise of the curve"; Lynx uses an accelerometer with an "unpublished threshold"; "Omega uses a closure
    system where the athlete's push off closes a sliding switch". Also: "Until 1990 the false start criterion was
    120 ms."
- **Komi, Ishikawa & Salmi 2009**, "IAAF Sprint Start Research Project: Is the 100 ms limit still valid?", New Studies
  in Athletics 24(1):37–47.
  - Full text not accessed: ResearchGate was blocked, and the WA NSA archive file id was not found.
  - WA news summary, 29 Jul 2009 [V-FT/web; it is itself a secondary summary]: "Seven national-level Finnish
    sprinters"; "great variation in individual reaction times"; reactions "as fast as 80ms". The authors "recommend that
    the 100ms limit be lowered to 80 or 85ms" and that the IAAF "urgently examines possibilities for detecting false
    starts kinematically".
  - van Hooren blog [S]: 4 men and 3 women. "When the force threshold was set to 25 kg (old IAAF guideline), the
    average reaction time was delayed by 35 ms"; 3 athletes still reached 25 kg within 100 ms.
- **Lipps, Galecki & Ashton-Miller 2011**, PLoS One 6:e26141, PMC3198384 [V-FT].
  - Beijing 2008 timing: "Swiss Timing, Ltd … using Omega equipment". Each RT was measured to the instant the force
    "increased to a specified force threshold set by Swiss Timing Ltd."
  - Swiss Timing's reply on the threshold: "Unfortunately this kind of information is not public". The authors assume
    "a 25 Kgf threshold for both males and females has become a de facto standard".
  - Sample: fastest RT per athlete, 425 sprinters.
  - "At the 99.9% confidence level, neither men nor women can react in 100 ms, but they can react in as little as
    109 ms and 121 ms". Women's "window of opportunity" is 21 ms. They propose "a 22% lower starting block force
    threshold for women" (19.4 kgf).
  - Lane effect absent, "likely because the 2008 Beijing Olympics were the first to use speakers behind each starting
    block". That claim conflicts with Omega's 1984 statement; see §3d.
- **Tønnessen, Haugen & Shalfawi 2013**, J Strength Cond Res 27:885–892 [V-ABS; full text paywalled].
  - 1,319 sprinters, WCH 2003–2009. "Seiko was the official timekeeper … Seiko uses a silent gun system for time
    initiation and false start detection."
  - RT men 0.166 ± 0.030 s, women 0.176 ± 0.034 s. Male finalists: final 0.142 ± 0.017 s vs round 1 0.161 ± 0.024 s.
  - RT correlates with 100 m time: r = 0.292 (men), 0.328 (women).
- **Haugen, Shalfawi & Tønnessen 2013** (baseline; the main literature review covers it).
  - PubMed abstract [V-ABS]: "Holding time calculations were based on television recordings from the analysed heats
    (n = 267) … Starters' holding times were between 1.3 and 2.2 s".
  - Secondary descriptions I could open: Haugen & Buchheit 2016 (in-press PDF, martin-buchheit.net) [V-FT].
    - They define it as "starters' holding time (time between 'set' and 'go'-signal)".
    - Their Table 1 lists "Faster reaction times when decreasing starters' holding time from 1.3 to 2.2 s [93]: 0.02 s;
      trivial". The row's wording is garbled; it reads as shorter holds giving about 20 ms faster RT, which matches the
      positive r.
    - They cite Karlin 1959: "reaction time increases as a function of the preparatory interval". That is the
      fixed-FP account, not the variable-FP one.
  - **Not found in any accessible source:** whether the hold ran from "set" onset or from settling; audio vs frame
    timing; frame rate; reliability. Brosnan 2017 and Milloz 2021 might say, but both are paywalled. **Treat the
    operational definition as unknown [U].**
- **Brosnan, Hayes & Harrison 2017**, J Sports Sci 35(10):929–935 (online 2016) [V-ABS; paywalled].
  - Data: "all available World and European Championship response-time (RT) data from 1999 to 2014"; ex-Gaussian
    model.
  - "Revised RT thresholds of 115 ms and 119 ms were identified for men and women, respectively", so "the current
    100 ms rule could result in some false starts not being detected". They recommend raising the threshold and making
    it sex-specific.
  - Milloz et al. 2020 restate it as "increases … of 15 ms for men and 19 ms for women" [V-FT]. Fiore et al. cite
    Brosnan's median RT as 0.156 s for 1999–2014 [V-FT].
- **Mirshams Shahshahani, Lipps, Galecki & Ashton-Miller 2018**, PLoS One 13:e0198633, PMC6021049 [V-FT].
  - Data: OG 2004–2016; minimum RT per athlete; LMM on RT^-1.5.
  - "Swiss Timing … uses their ASC3 (Automatic Start Control) false start detection system … with a precision of 1 ms";
    "a given (unpublished) force threshold". "No reaction time is reported in the event of a false start (< 100 ms)".
  - Minimum RTs fell 2004→2016 in both sexes, and the sex difference vanished in 2012. Interpretation: "the force
    threshold was indeed reduced for the women in 2012, but not the men", followed by "fine tuning of those force
    thresholds by Swiss Timing" in 2016. Also: "The IAAF has been examining SIS methods for detecting false starts."
- **Milloz, Hayes & Harrison 2021** (online 2020), Sports Med 51(1):21–31 [V-ABS; paywalled; the reference list was read
  on the Springer page].
  - Abstract: "several SIS use different technologies to deliver the start signal and record response time (RT). The
    lack of scientific evidence about the definition of the 100 ms false start threshold by the WA is criticized … SIS
    technologies, expertise and sex appear to affect the RT detected in competition. A lack of standardization in event
    detection has led to validity and reliability problems … the onset of arm force reaction is the first detectable
    biomechanical event in the start."
  - Their reference list includes Otsuka 2017, Haugen 2013, MacDonald & Meck 2004, Zahn & Rosenthal 1966 and Kennefick
    2014 (corticospinal excitability), plus St Germain 2019 and Carlsen 2004 (startle). **The review probably discusses
    hold time and foreperiod qualitatively. I could not verify what it says [U]**, and novelty claims should allow for
    it.
- **Milloz, Harrison & Hayes 2020**, ISBS Proceedings 38(1), art. 107; doi 10.34961/6110; UL repository, CC BY-NC-SA
  [V-FT].
  - Setup: 20 sprinters (16 M, 4 F), 63 trials. WA-certified SIS **TimeTronics FalseStart III Pro** (Olen, Belgium) plus
    a custom hand force plate at 2000 Hz with a personalised threshold from the set-position signal.
  - Hand-plate RT vs WA SIS RT: 0.067 ± 0.035 s vs 0.138 ± 0.032 s.
  - For trials where the WA SIS read 100–119 ms (n = 10), the hand-plate RT was 0.047 ± 0.019 s. Authors: "probably
    false start according to the theoretical minimum auditory RT".
- **University of Limerick patent US 11,517,804 B2** (Harrison, Barr, Hayes; filed 27 Jul 2018, granted 6 Dec 2022),
  "Method and apparatus for false start detection" [V-FT/web]. Hand/arm force at 2–4 kHz; detection from force change,
  not magnitude; detects "40–100 ms earlier than foot-block systems"; supports 90 or 80 ms thresholds.
- **Crotty, Hayes & Harrison 2022** (online 2019), Sports Biomech 21(5):604–621 [V-ABS]. 19 sprinters on an
  IAAF-approved block system. Triceps-surae EMD correlated with SSRT (r = 0.572); EMD plus signal-processing time
  explained 37% of the variance.
- **Collet 1999**, Percept Mot Skills 88:65–75 [V-ABS]. Finalists' RT falls from heats to final; RT rises with race
  length. RT is "a skill dependent upon experience and learning".
- **Ditroilo & Kilding 2004**, New Stud Athl 19(1):13–19 [V-ABS via BISp, in German]. Comparing WCH 2001 and 2003, RTs of
  athletes who ran both championships did not differ significantly; hurdlers were slower in 2003.
- **Pilianidis, Kasabalis, Mantzouranis & Mavvidis 2012**, Kinesiology 44(1):67–72 [S]. Finals at OG 2000/04/08
  (67 M, 68 F); a sex difference in RT only in the 100 m.
- **Babić & Delalija 2009**, New Stud Athl 24(1):59–68 (sex differences, OG 2004) and 24(1):49–57 (women) [S; cited by
  Fiore and Milloz].
- **Paradisis 2013**, "Reaction time and performance in the short sprints", New Stud Athl 28(1/2):95–103 [S; PDF host
  unreachable].
- **Mitašík, Doležajová, Lednický & Végh 2020**, AFEPUC 60(2):207–216 [V-FT, OA]. WCH 200 m finalists, 1999–2009 vs
  2011–2019. Heat-vs-final differences for men; slower RTs after the rule change; no hold-time analysis.
- **Ntolaptsis & Panoutsakopoulos 2021**, AFEPUC 61(1):72–85 [V-FT, OA]. World Indoor 60 mH (70 performances). RT did
  not differ before vs after the rule change; RT vs time r = 0.228. Cites TR 16.6 and 16.8.
- **Zhang, Lin & Zhang 2021**, Complexity 2021:6633326 [V-ABS; the OA PDF was blocked]. WCH 2011–2019 100/200/hurdles;
  double-log model.
- **Han, Zhou & Zhang 2025**, Int J Perform Anal Sport 26(4):900–919 (Crossref; online Nov 2025) [V-ABS].
  - Data: 100 m semis and finals from 7 OG, 12 WCH and 13 U20 WCH, 2000–2024; GLMs.
  - "the implementation of the Zero False Start rule significantly reduced the average reaction time … (β = -0.004,
    p = 0.001)", with a short-term slowdown followed by adaptation.
  - **This conflicts in direction with Haugen 2013 and Brosnan 2017.** Plausibly confounded by vendor and threshold
    changes after 2012 (Mirshams Shahshahani 2018). No hold time.
- **Fiore, Schifano & Yan 2025**, The American Statistician 79(4):500–507; arXiv 2506.11460; UConn Statistics [V-FT of
  the arXiv version].
  - Allen's RTs: 0.123 (heat), 0.101 (semi), 0.099 (final).
  - Objective 1: Datta–Satten clustered rank-sum test (R `clusrank`). WCH 2022 RTs were faster than the same athletes'
    RTs at the 2022 nationals (17 athletes / 80 RTs per sex), WCH 2019 (34 M / 134, 31 F / 124) and WCH 2023 (45 M /
    161, 47 F / 182). All p ≤ 1.5e-3 (permutation).
  - All 8 US athletes were faster at WCH than at the June 2022 US Championships held at the same venue.
  - **No vendor or algorithm is named.** The timing difference is inferred from RTs.
  - Objective 2: generalized-gamma GAMLSS, venue random effect on μ and heat random effect on σ. Men's 100 m and 110 mH
    semis and finals, WCH 1999–2023, n = 776.
    - P(RT < 0.100) = 2.76e-3 (1.94e-3 excluding 2022); P(< 0.090) = 4.95e-4; P(< 0.080) = 6.84e-5.
    - Suggested barriers (men) at tail probabilities 1e-2 / 1e-3 / 1e-4: 0.108 / 0.094 / 0.082 s. Women (n = 732):
      0.111 / 0.102 / 0.095 s; P(< 0.100) = 5.46e-4.
    - Median 2022 RT 0.129 s. τ_v = 0.058, τ_h = 0.32.
  - Data and code are in the supplementary materials. The BRIEF lists github.com/ofiore/Thesis.
  - **No foreperiod covariate.**
- **Haugen & Buchheit 2016**, Sports Med 46(5):641–656 [V-FT, in-press PDF].
  - "In 1995, IAAF introduced the use of silent gun (start signal from speakers behind each athlete) in their
    international championships". This conflicts with other accounts; see §3d.
  - Loud-gun sound delay: "~3 ms for each metre … inner-lane will hear the sound of a 'loud' gun 0.02-0.03 s earlier
    than their outer-lane … competitors" (100 m); 0.07–0.08 s in the 200 m.
- **Bezodis, Willwacher & Salo 2019**, Sports Med 49:1345–1364, PMC6684547 [V-FT]. RT is affected by "disqualification
  rule changes [33], holding time [34, 35], start signal intensity [36], and the sprinter's focus of attention [37]".
  One sentence only.
- **Julin 2003**, "An alternative approach to solve the false start problem", New Stud Athl 18(1):7–10 [V-FT]. WA NSA
  PDF: https://worldathletics.org/download/downloadnsa?filename=89690dfd-9b5e-4e7e-961c-7a07e4a1db40.pdf . A viewpoint
  piece by a Swedish rules officer; see §0 item 10. Also: "a start … where the starting times recorded by the control
  device has a spread exceeding 0.04s has not been fair".
- **Julin & Dapena 2003**, "Sprinters at the 1996 Olympic Games in Atlanta did not hear the starter's gun through the
  loudspeakers on the starting blocks", New Stud Athl 18:23–27; and **Dapena 2005**, "The 'loud gun' starting system
  currently used at the Olympic Games does not work properly" (web report). Titles are from Milloz's reference list;
  the content is as described by Brown 2008 and Pain & Hibbs 2007 [S]. The PDFs were unreachable.

---

## 3. How RT is measured at championships

### 3a. Who timed what
| Competition | Timer / SIS | Source |
|---|---|---|
| World Championships 1987–2025 (all editions) | **Seiko** | Seiko history page: "since the 2nd World Championships held in Rome in 1987, Seiko has been the official timer for 16 consecutive championships"; the WA-championship page lists 1987 through 2025 including Seville 1999, Edmonton 2001, Oregon 2022, Budapest 2023, Tokyo 2025 [V-FT/web]. Tønnessen 2013 confirms Seiko for 2003–09 [V-ABS] |
| Seiko SIS changes | 1997 Athens color slit video; **2019 Doha "We introduced the latest starting information system"**; WA-certified block FL-6000 "with Start Information System" (cert. E-14-0798) | Seiko site [V-FT/web]; WA certified-equipment list (1 Feb 2022) [V-FT] |
| Olympic Games 1996, 2000, 2004 | **Swatch** (Swatch Group; Swiss Timing did the technical work) | Swatch Group press release, 21 Sep 2004: "Swatch has now successfully participated at three Olympic Games as the Official Timekeeper (1996 in Atlanta, 2000 in Sydney and 2004 in Athens …)" [V-FT/web] |
| Olympic Games 2008–2024 | **Omega** (Swiss Timing equipment) | Same release: Omega for Torino 2006, Beijing 2008, …; Lipps 2011: Beijing = Swiss Timing/Omega [V-FT] |
| Diamond League 2010– | **Omega** | omegawatches.com athletics page: "Since the Diamond League was founded in 2010, OMEGA has proudly taken the role of Official Timekeeper" [V-FT/web] |
| Lower-level / national meets | FinishLynx ReacTime (accelerometer), TimeTronics FalseStart III Pro, others | Zemper monograph [V-FT]; Milloz 2020 [V-FT] |

**Implication:** WCH (Seiko) and OG (Omega) RTs come from different systems. Pool them only with a comp-level effect.
Within WCH, also allow for Seiko SIS changes (2019) and the WCH 2022 anomaly found by Fiore et al.

### 3b. Detection methods (what is public)
- **Omega / Swiss Timing.**
  - 1984: first pressure-based false-start device [V-FT/web].
  - 2006/07: "closure system where the athlete's push off closes a sliding switch" (Pain & Hibbs) [V-FT].
  - Beijing 2008: force threshold (value withheld) (Lipps 2011) [V-FT].
  - **June 2011 priority, patent US 8,992,386 B2** ("Starting device for a competitor in a sports competition"; Swiss
    Timing Ltd; filed 29 May 2012; granted 31 Mar 2015): "the sensor only detects the variation in force on the block";
    "the response time at the start instant thus no longer depends on a determined force threshold, but only on the
    variation in the force on the block" [V-FT/web].
  - London 2012 blocks (Omega, 1 Jun 2012, via my-watchsite): "reaction times are measured entirely by the measurement
    of force against the back block and not by movement"; "can detect the reaction times of every runner – from
    children through world-class sprinters – without changing any settings" [V-FT/web; press-release wording].
  - Omega today: "built-in sensors that measure an athlete's force against the footrest 4,000 times per second"
    (omegawatches official-timekeeper page) [V-FT/web]. Electronic start pistol (flash gun plus sound box) since 2010
    (Vancouver) [V-FT/web].
  - ASC3 datasheet (07/2015, swisstiming.com): "The system memorizes and prints the reaction times occurring in the
    interval of 0.3 second before and 0.7 seconds after the starting gunshot"; timing precision 1 ms; block loudspeaker
    gun shot "114 dB @ 1m"; false start signal 104 dB; IAAF certified [V-FT]. The threshold is not disclosed.
  - WA-certified Swiss Timing blocks: ASB2 3476.700 (cert. E-11-0634) and ASB-3 3457.700 (E-18-0983) (WA list,
    1 Feb 2022) [V-FT].
  - **Timeline hypothesis to test:** a change from absolute threshold to force-change detection around 2011–12, which
    matches Mirshams Shahshahani's 2012 shift in women's RT [inference].
- **Seiko.** "in the past used a 20 kg threshold above baseline … More recently … steepest rise of the curve" (Pain &
  Hibbs 2007) [V-FT]. The Seiko patent JP2759769B2 (1 kHz; 3–25 Hz components above a moving baseline, plus 3 kg;
  replacing a 23 kg absolute threshold) was already verified by the literature review. Not repeated here.
- **FinishLynx.** Patent US 6,002,336 (Lynx System Developers; filed 2 Dec 1997; granted 14 Dec 1999): an accelerometer
  on the block "crossing a threshold, illustratively at about 1.5 g". It contrasts this with force systems using "a
  threshhold force of about 250 Newtons" [V-FT/web]. Zemper: the Lynx accelerometer attaches to the block spine and
  senses backward block motion [V-FT].
- **Certification.** Public WA certification documents list starting blocks as certified equipment (e.g., WA
  certification fee "Starting block USD 700"). **I found no public WA specification of SIS detection criteria or test
  protocol** [V-FT, by absence in docs scanned]. Willwacher et al. 2013 (Procedia Eng 60:124–129) built a pneumatic
  force-pattern machine from 438 starts by 101 athletes to certify false-start apparatus. "Initial testing of false
  start apparatus highlights the need for further improvements … especially with respect to the criterion that is used
  to detect the reaction time from a given sensor waveform" [V-ABS].
- **Pre-race check.** WA Starting Guidelines: the Start Referee, with the Chief Photo Finish Judge and a Starter, "carries
  out an initial check of the SIS and a zero control test" [V-FT].
- **Summary.** Different vendors use different sensors and criteria, and thresholds are proprietary and have changed.
  Therefore **official RT = physiological latency + criterion-dependent detection delay**. The criterion delay is on the
  order of 20–70 ms depending on method (Pain & Hibbs: +26 ms for threshold vs onset; Milloz: about 70 ms foot vs hand).
  It may differ by sex (Lipps) and by meet (Fiore).

### 3c. Controversies
- **Devon Allen, WCH Eugene 2022, 0.099 s** (Fiore et al. above). LetsRun [S]: WA said it had spoken to Seiko, who
  "were standing by the system … the exact same system used at the last 3 worlds and … calibrated correctly".
- **Bolt, Daegu 2011:** the first high-profile zero-tolerance DQ.
- **Christie, Atlanta 1996:** DQ after two false starts; protests about the 100 ms enforcement (Lipps; Pain & Hibbs)
  [V-FT].

### 3d. Speakers and the "silent gun" (conflicting claims)
- Omega: go signal "delivered through the speakers behind each runner since 1984" (Brown 2008, citing omegawatches.com)
  [V-FT].
- Julin & Dapena 2003: at Atlanta 1996 athletes did not hear the gun through the block loudspeakers [S]. Brown 2008
  (Athens 2004 data): the go signal was sent both via speakers and as a loud pistol near lane 1. Lane 1 mean RT was
  160 ms vs 175 ± 5 ms in lanes 2–8 [V-FT].
- Haugen & Buchheit 2016: IAAF "introduced the use of silent gun" in 1995 [V-FT quote; the claim is S]. Tønnessen 2013:
  Seiko used a silent gun at WCH 2003–09 [V-ABS]. Lipps 2011: Beijing 2008 was "the first to use speakers behind each
  starting block" [V-FT quote; probably imprecise]. Fiore 2025: "silent gun" systems from 2010 [V-FT quote; S].
- **Resolution for our paper:** lane-level speakers existed from the 1980s. Until about 2008–10, however, a live pistol
  near lane 1 still gave inside lanes a louder and earlier signal (Brown 2008). Modern electronic guns emit only through
  the speakers (Omega since 2010). For WCH/OG data from 2008 on, sound-travel lane effects should be negligible, but
  keep lane as a covariate.

---

## 4. Starter guidance on hold time
- **WA Starting Guidelines**, current PDF, footer "December 2022":
  https://worldathletics.org/download/download?filename=8c0101f9-d212-45ea-a949-452f292d0990.pdf .
  §6.2: "There is no perfect holding time in the set position. In reality, there must be a discernible hold to ensure
  all Athletes are steady, focussed and in the correct starting position." The same sentence appears in the April 2012
  (§5.2) and June 2018 (§6.2) editions. **No numeric interval** [V-FT].
- **Zemper, E. D., "Starters" monograph** (IAAF edition 2019, bcathletics.org; USATF edition at pausatf.org; 2009 and
  2023 editions also exist) [V-FT; practitioner manual, not peer-reviewed].
  - Definition and timing instruction: see §0 item 3.
  - "Any hold of less than 1.5 seconds does not allow the athletes sufficient time to get into the set position."
  - "a good hold time will range from 1.8 to 2.4 or 2.5 seconds". Short sprints and hurdles "average near the lower
    end"; staggered starts near the upper end.
  - "in some major international championship meets starters have been known to hold the runners for 3 to 3.5
    seconds"; beyond 2.5 s the starter "should be ready to call the runners up".
  - "A starter should never get in the habit of firing the gun at the exact same length of time after the 'Set'
    command. Athletes will pick up on this very quickly, and it is a good recipe for having runners anticipate the gun."
  - "On rare occasions all of the runners … will come up immediately and together … the gun can be fired at less than
    1.8 seconds". Most of the time the starter waits for the slowest athlete to become still. **So the hold equals the
    time for the last athlete to settle plus a scan margin.** This is the mechanism behind "set onset → gun" versus
    "last athlete still → gun".
  - "For any starter, the fastest starts (i.e., the shortest hold times) tend to be the first start of the day and any
    start after a false start." (Testable.)
- **SDHSAA (South Dakota HS) "Starter Information"**: "Any hold of less than 1.5 seconds … A good hold time will range
  from 1.8-2.3 seconds." Derived from Zemper [V-FT].
- **Julin 2003**: at least 2 s is needed; consistent practice gives 2.0–2.7 s. For 1988 US Trials, Munich 1972 and
  European "fast guns", see §0 item 10 [V-FT].
- **Published hold-time measurements I found** (none from the Diamond League, NCAA, youth or masters):
  - Haugen 2013: 1.3–2.2 s, 267 heats [V-ABS].
  - Otsuka 2017: 1.780 s ± SD 0.158 s, 83 races [V-FT].
  - Julin's 1988 anecdotes [V-FT/S].
  - Lab protocols: Pain & Hibbs 2007, random 3–4 s window starting about 1 s after set [V-FT]; Brown 2008, "fixed at
    3 s … to eliminate the influence of a variable foreperiod on RT", with about 10% catch trials [V-FT].
- The literature review also has (not repeated here): per-heat Seiko "Waveform" JPGs linked from WA results with a
  "Ready Time" field.

---

## 5. Start signals in other sports (is the foreperiod fixed, variable or random?)

| Sport | Rule text on the hold | FP type | RT threshold? | Source |
|---|---|---|---|---|
| Swimming (World Aquatics SW 4, 2023–25) | SW 4.1: "On the starter's command 'take your marks', they shall immediately take up a starting position … When all swimmers are stationary, the starter shall give the starting signal." SW 4.3: English commands; "multiple loudspeakers, mounted one at each starting platform". SW 4.4: "Any swimmer initiating a start before the signal may be disqualified." | Variable, starter-controlled, unregulated (like athletics) | **None** for the individual start. Relay take-off judged by equipment to 1/100 s; FR 2.3.6.3: "For the differential in the relays take-off the manufacturer of the device shall be consulted." | World Aquatics Swimming Rules 2023–2025 [V-FT]; FINA Facilities Rules 2021–25 [V-FT] |
| Swimming relay tolerance | "a swimmer will not be disqualified unless the timing system shows a departure more than 0.03 second before the swimmer in the water touches the touchpad"; set because an Omega block signalled 0.024–0.027 s before actual departure | Device-error tolerance, not an RT rule | -0.03 s | Daktronics patent US 7,403,135 B1 (2008) [V-FT/web] |
| Swim-start RT research | Papic et al. 2019: auditory (horn) start training cut RT by 13 ± 9 ms in adolescents (n = 5 vs 5). No hold-time manipulation found | n/a | n/a | [V-ABS] |
| Speed skating, long track (ISU Special Regulations 2024, Rule 253 §3.2) | "There shall be a distinct interval between the moment when the Competitors have taken their starting position and the firing of the shot. This distinct interval should be between 1 and 1.5 seconds." A first false start earns a warning; the next false start by anyone in the pair is a DQ | **Codified narrow window** (1–1.5 s after stillness), so near-fixed | Visual/starter judgement | ISU 2024 regs [V-FT] |
| Short track (ISU Comm. 2510, 13 Sep 2022; Rule 298 test) | "When all Skaters are positioned in their final starting position and stand still … the Starter will wait a defined period of time and then fire the gun." Zero-false-start trial 2022–23; electronic false-start detection to be tested | "Defined period", so near-fixed | Zero false starts (trial) | ISU Comm. 2510 [V-FT] |
| Rowing (US Rowing Rules 2023, 2-306) | "(1) calling out 'Attention!' (2) raising the Starter's flag overhead, and then (3) after a distinct and variable pause, calling out 'Go!'" (the lights version is the same) | **Codified variable** | Crossing early = false start (2 → DQ, per summaries) | US Rowing 2023 [V-FT]; World Rowing text not checked [U] |
| Formula 1 (FIA "Recommended light signals", Appendix H) | 5 red-light pairs at 1 s intervals ("under starter's orders"), then "After a preset delay of between 0.2 and 3.0 seconds, the race is started by all the red start lights being extinguished." | **Explicitly randomised FP (0.2–3.0 s)** after a fixed 1 Hz countdown | Jump start detected by transponders/sensors [S] | FIA PDF [V-FT] |
| Track cycling (UCI Part 3, v. 25.10.2021, art. 3.2.016, verified) | "The starter … shall give the start by means a pistol shot. In cases where the start is to be taken from a starting block … the brakes of the machine shall be released by the electronic system that simultaneously triggers the chronometer. Once the bicycle has been fixed, a clock placed before the rider, counts down the last 50 seconds before the start." | **Fixed, fully predictable** (machine release) | n/a; standing-start sprints allow two starts (3.2.021ter) | UCI regs [V-FT] |
| Motorcycle speedway | Visual signal (tape lift) after the referee's green light. Markowski et al. 2023: 1,261 RTs, 65 riders (2021 PGE Ekstraliga; Pegasus telemetry, 0.01 s); seniors 0.246 s vs juniors 0.258 s; gate A fastest; heat 15 fastest. The authors warn riders can watch the machine's sliders (a cue that anticipates the signal) | Referee-controlled; FP not reported | Warning for moving before the tape lifts | PLoS One 18:e0281138 [V-FT] |
| NFL | The offence controls the snap count; the "hard count" deliberately varies the cadence to draw defensive offside | Strategic, variable | n/a | [U] (not checked) |

**Takeaway for novelty/application.** Precedents exist for a regulated foreperiod distribution: a narrow window (ISU
1–1.5 s), a mandated variable pause (rowing), and an explicit random preset delay (F1, 0.2–3.0 s). A "foreperiod-aware"
athletics rule, such as an electronic hold drawn from a specified (e.g., non-aging) distribution after stillness, has
sporting precedent.

---

## 6. Sprint-start physiology relevant to sub-100 ms RTs
- **Pre-motor / EMG latencies.** Pain & Hibbs 2007: rear-leg pre-motor about 65 ms; "EMG latencies can be under
  60 ms"; the neuromuscular component "can be under 85 ms" [V-FT]. Mero & Komi 1990: motor time 8–57 ms [V-ABS].
- **Measurement criterion dominates.** Threshold +26 ms (Pain & Hibbs); arm-force onset about 70 ms earlier than the
  foot-block SIS (Milloz 2020); relaxed set position +39% RT (Pain & Hibbs, "average increase in reaction time of 39%")
  [V-FT].
- **Go-signal intensity and startle** (Brown, Kenwell, Maraj & Collins 2008, MSSE 40:1142–1148) [V-FT].
  - RT fell from 138 ± 30 (80 dB) to 128 ± 25 (100 dB) to 120 ± 20 ms (120 dB).
  - "When a startle response was evoked, RT was 18 ms lower than for starts with no startle."
  - Lab FP fixed at 3 s, with about 10% catch trials. Commands at 70 dB.
  - For comparison, the Swiss Timing block loudspeaker plays the gunshot at 114 dB @ 1 m [V-FT]. **The go signal is
    loud enough that StartReact-type release of prepared responses is plausible. Its size depends on preparation state,
    and so on the foreperiod** (the cognitive-science search pass should cite Carlsen/Valls-Solé here).
- **Sound travel in the loud-gun era:** about 3 ms per metre (Pain & Hibbs; Haugen & Buchheit) [V-FT].

---

## 7. Implications for our paper (sports side)
1. Measurement confound. Model RT as physiology plus a criterion delay. Include competition/vendor effects (Seiko WCH vs
   Omega OG; Seiko SIS change 2019; WCH 2022 anomaly) and sex × system interactions. Do not interpret absolute sub-0.100
   probabilities across systems without this.
2. The hold is state-dependent by rule (starter waits for stillness). FP is therefore **endogenous**: long holds signal
   an unsettled field. Measure the "last athlete still" time where video allows, or treat it as a limitation. Zemper's
   claim (shorter holds at the first start of a session and after a false start) is a cheap, testable sequential and
   starter effect.
3. Prior art that must be cited to keep novelty claims honest: Haugen 2013 (TV holds vs RT); Otsuka 2017 (manual
   broadcast-audio FP distribution plus lab FP effect); Julin 2003 (informal time-uncertainty argument for longer, wider
   holds); Pain & Hibbs 2007 (time-uncertainty argument for sub-100 legitimacy); Fiore 2025 (unconditional P(sub-100));
   Milloz 2021 (likely a qualitative FP discussion, content unverified).
4. Policy precedents: ISU (codified window), rowing (codified variable pause) and F1 (random 0.2–3.0 s) support a
   "regulated hold distribution" recommendation.

---

## BibTeX
(DOI entries from doi.org content negotiation / Crossref on 2026-09-29, with keys cleaned and issue years used. Non-DOI
entries were assembled from the sources opened. Check the flagged fields.)

```bibtex
@article{Fiore2025Allen,
  author = {Fiore, Owen and Schifano, Elizabeth D. and Yan, Jun},
  title = {On Devon Allen's Disqualification at the 2022 World Track and Field Championships},
  journal = {The American Statistician}, volume = {79}, number = {4}, pages = {500--507}, year = {2025},
  doi = {10.1080/00031305.2025.2515869}, note = {arXiv:2506.11460}
}
@article{Brosnan2017,
  author = {Brosnan, Kevin C. and Hayes, Kevin and Harrison, Andrew J.},
  title = {Effects of false-start disqualification rules on response-times of elite-standard sprinters},
  journal = {Journal of Sports Sciences}, volume = {35}, number = {10}, pages = {929--935}, year = {2017},
  doi = {10.1080/02640414.2016.1201213}
}
@article{Lipps2011,
  author = {Lipps, David B. and Galecki, Andrzej T. and Ashton-Miller, James A.},
  title = {On the Implications of a Sex Difference in the Reaction Times of Sprinters at the {Beijing} {Olympics}},
  journal = {PLoS ONE}, volume = {6}, number = {10}, pages = {e26141}, year = {2011},
  doi = {10.1371/journal.pone.0026141}
}
@article{MirshamsShahshahani2018,
  author = {Mirshams Shahshahani, Payam and Lipps, David B. and Galecki, Andrzej T. and Ashton-Miller, James A.},
  title = {On the apparent decrease in {Olympic} sprinter reaction times},
  journal = {PLoS ONE}, volume = {13}, number = {6}, pages = {e0198633}, year = {2018},
  doi = {10.1371/journal.pone.0198633}
}
@article{Tonnessen2013,
  author = {T{\o}nnessen, Espen and Haugen, Thomas and Shalfawi, Shaher A. I.},
  title = {Reaction Time Aspects of Elite Sprinters in Athletic World Championships},
  journal = {Journal of Strength and Conditioning Research}, volume = {27}, number = {4}, pages = {885--892}, year = {2013},
  doi = {10.1519/JSC.0b013e31826520c3}
}
@article{Haugen2013,
  author = {Haugen, Thomas A. and Shalfawi, Shaher and T{\o}nnessen, Espen},
  title = {The effect of different starting procedures on sprinters' reaction time},
  journal = {Journal of Sports Sciences}, volume = {31}, number = {7}, pages = {699--705}, year = {2013},
  doi = {10.1080/02640414.2012.746724}
}
@article{Otsuka2017,
  author = {Otsuka, Mitsuo and Kurihara, Toshiyuki and Isaka, Tadao},
  title = {Timing of Gun Fire Influences Sprinters' Multiple Joint Reaction Times of Whole Body in Block Start},
  journal = {Frontiers in Psychology}, volume = {8}, pages = {810}, year = {2017},
  doi = {10.3389/fpsyg.2017.00810}
}
@article{PainHibbs2007,
  author = {Pain, Matthew T. G. and Hibbs, Angela},
  title = {Sprint starts and the minimum auditory reaction time},
  journal = {Journal of Sports Sciences}, volume = {25}, number = {1}, pages = {79--86}, year = {2007},
  doi = {10.1080/02640410600718004}
}
@article{MeroKomi1990,
  author = {Mero, Antti and Komi, Paavo V.},
  title = {Reaction time and electromyographic activity during a sprint start},
  journal = {European Journal of Applied Physiology and Occupational Physiology}, volume = {61}, number = {1-2},
  pages = {73--80}, year = {1990}, doi = {10.1007/BF00236697}
}
@article{Collet1999,
  author = {Collet, C.},
  title = {Strategic Aspects of Reaction Time in World-Class Sprinters},
  journal = {Perceptual and Motor Skills}, volume = {88}, number = {1}, pages = {65--75}, year = {1999},
  doi = {10.2466/pms.1999.88.1.65}
}
@article{Milloz2021,
  author = {Milloz, Matthieu and Hayes, Kevin and Harrison, Andrew J.},
  title = {Sprint Start Regulation in Athletics: A Critical Review},
  journal = {Sports Medicine}, volume = {51}, number = {1}, pages = {21--31}, year = {2021},
  doi = {10.1007/s40279-020-01350-4}
}
@inproceedings{Milloz2020ISBS,
  author = {Milloz, Matthieu and Harrison, Andrew J. and Hayes, Kevin},
  title = {Contribution of new start information system prototype to the false start detection in athletics},
  booktitle = {ISBS Proceedings Archive}, volume = {38}, number = {1}, pages = {Article 107}, year = {2020},
  doi = {10.34961/6110}, url = {https://commons.nmu.edu/isbs/vol38/iss1/107}
}
@article{Brown2008,
  author = {Brown, Alexander M. and Kenwell, Zoltan R. and Maraj, Brian K. V. and Collins, David F.},
  title = {``Go'' Signal Intensity Influences the Sprint Start},
  journal = {Medicine \& Science in Sports \& Exercise}, volume = {40}, number = {6}, pages = {1142--1148}, year = {2008},
  doi = {10.1249/MSS.0b013e31816770e1}
}
@article{Crotty2022,
  author = {Crotty, Evan D. and Hayes, Kevin and Harrison, Andrew J.},
  title = {Sprint start performance: the potential influence of triceps surae electromechanical delay},
  journal = {Sports Biomechanics}, volume = {21}, number = {5}, pages = {604--621}, year = {2022},
  doi = {10.1080/14763141.2019.1657932}
}
@article{Han2025,
  author = {Han, Lingyun and Zhou, Chuanshun and Zhang, Hui},
  title = {The long-term effects of Current false Start rules on reaction time and athletic performance},
  journal = {International Journal of Performance Analysis in Sport}, volume = {26}, number = {4}, pages = {900--919},
  year = {2025}, doi = {10.1080/24748668.2025.2579341}, note = {Crossref lists vol. 26(4); online Nov 2025 -- check issue year}
}
@article{Mitasik2020,
  author = {Mita{\v{s}}{\'\i}k, Peter and Dole{\v{z}}ajov{\'a}, Ladislava and Lednick{\'y}, Anton and V{\'e}gh, D{\'a}vid},
  title = {Changes in the Start Reaction Times in the 200 m Run at the World Championships After the Tightening of False Start Rule},
  journal = {Acta Facultatis Educationis Physicae Universitatis Comenianae}, volume = {60}, number = {2}, pages = {207--216},
  year = {2020}, doi = {10.2478/afepuc-2020-0017}
}
@article{Ntolaptsis2021,
  author = {Ntolaptsis, Konstantinos and Panoutsakopoulos, Vassilios},
  title = {Relationship Between Reaction Time, Medal Winning and Performance in the 60 m Hurdle Indoor Event Before and After the Change of False Start Rule},
  journal = {Acta Facultatis Educationis Physicae Universitatis Comenianae}, volume = {61}, number = {1}, pages = {72--85},
  year = {2021}, doi = {10.2478/afepuc-2021-0007}
}
@article{Zhang2021Complexity,
  author = {Zhang, Jing and Lin, Xin-Yu and Zhang, Su},
  title = {Correlation Analysis of Sprint Performance and Reaction Time Based on Double Logarithm Model},
  journal = {Complexity}, volume = {2021}, pages = {6633326}, year = {2021}, doi = {10.1155/2021/6633326},
  note = {Second author given as Xin-Yu Lin (Crossref) vs Xin-Tao Lin (Semantic Scholar) -- verify}
}
@article{Papic2019,
  author = {Papic, Christopher and Sinclair, Peter and Fornusek, Che and Sanders, Ross},
  title = {The effect of auditory stimulus training on swimming start reaction time},
  journal = {Sports Biomechanics}, volume = {18}, number = {4}, pages = {378--389}, year = {2019},
  doi = {10.1080/14763141.2017.1409260}
}
@article{Markowski2023,
  author = {Markowski, Maciej and Szczepan, Stefan and Zato{\'n}, Marek and Martin, Sarah and Michalik, Kamil},
  title = {The importance of reaction time to the starting signal on race results in elite motorcycle speedway racing},
  journal = {PLoS ONE}, volume = {18}, number = {1}, pages = {e0281138}, year = {2023}, doi = {10.1371/journal.pone.0281138}
}
@article{Willwacher2013,
  author = {Willwacher, Steffen and Feldker, Martin-K{\"u}sel and Zohren, Sebastian and Herrmann, Volker and Br{\"u}ggemann, Gert-Peter},
  title = {A Novel Method for the Evaluation and Certification of false Start Apparatus in Sprint Running},
  journal = {Procedia Engineering}, volume = {60}, pages = {124--129}, year = {2013}, doi = {10.1016/j.proeng.2013.07.073}
}
@article{HaugenBuchheit2016,
  author = {Haugen, Thomas and Buchheit, Martin},
  title = {Sprint Running Performance Monitoring: Methodological and Practical Considerations},
  journal = {Sports Medicine}, volume = {46}, number = {5}, pages = {641--656}, year = {2016},
  doi = {10.1007/s40279-015-0446-0}
}
@article{Bezodis2019,
  author = {Bezodis, Neil Edward and Willwacher, Steffen and Salo, Aki Ilkka Tapio},
  title = {The Biomechanics of the Track and Field Sprint Start: A Narrative Review},
  journal = {Sports Medicine}, volume = {49}, number = {9}, pages = {1345--1364}, year = {2019},
  doi = {10.1007/s40279-019-01138-1}
}
@article{Komi2009NSA,
  author = {Komi, Paavo V. and Ishikawa, Masaki and Salmi, Jukka},
  title = {{IAAF} Sprint Start Research Project: Is the 100 ms limit still valid?},
  journal = {New Studies in Athletics}, volume = {24}, number = {1}, pages = {37--47}, year = {2009},
  note = {Full text not accessed; summary via World Athletics news, 29 Jul 2009}
}
@article{Julin2003NSA,
  author = {Julin, A. Lennart},
  title = {An alternative approach to solve the false start problem},
  journal = {New Studies in Athletics}, volume = {18}, number = {1}, pages = {7--10}, year = {2003},
  url = {https://worldathletics.org/download/downloadnsa?filename=89690dfd-9b5e-4e7e-961c-7a07e4a1db40.pdf}
}
@article{JulinDapena2003,
  author = {Julin, A. Lennart and Dapena, Jes{\'u}s},
  title = {Sprinters at the 1996 {Olympic} {Games} in {Atlanta} did not hear the starter's gun through the loudspeakers on the starting blocks},
  journal = {New Studies in Athletics}, volume = {18}, pages = {23--27}, year = {2003}, note = {Not accessed; metadata from Milloz et al. 2021 reference list}
}
@article{DitroiloKilding2004,
  author = {Ditroilo, M. and Kilding, A. E.},
  title = {Has the new false start rule affected the reaction time of elite sprinters?},
  journal = {New Studies in Athletics}, volume = {19}, number = {1}, pages = {13--19}, year = {2004}
}
@article{Pilianidis2012,
  author = {Pilianidis, Theophilos and Kasabalis, Athanasios and Mantzouranis, Nikolaos and Mavvidis, Athanasios},
  title = {Start reaction time and performance at the sprint events in the {Olympic} {Games}},
  journal = {Kinesiology}, volume = {44}, number = {1}, pages = {67--72}, year = {2012}, note = {First names unverified}
}
@article{BabicDelalija2009,
  author = {Babi{\'c}, Vesna and Delalija, Arian},
  title = {Reaction time trends in the sprint and hurdle events at the 2004 {Olympic} {Games}: Differences between male and female athletes},
  journal = {New Studies in Athletics}, volume = {24}, number = {1}, pages = {59--68}, year = {2009}, note = {Not accessed; first names unverified}
}
@article{Paradisis2013NSA,
  author = {Paradisis, Giorgos P.},
  title = {Reaction time and performance in the short sprints},
  journal = {New Studies in Athletics}, volume = {28}, number = {1/2}, pages = {95--103}, year = {2013}, note = {Not accessed}
}
@manual{WA2026Rules,
  author = {{World Athletics}},
  title = {Book C -- C1.1 \& C2.1: Competition Rules \& Technical Rules},
  year = {2026}, note = {Version dated 1 July 2026; TR 15, 16, 39.8.3; CR 22},
  url = {https://worldathletics.org/download/download?filename=0ed43077-8e08-492b-a4b3-267f27c18d0b.pdf}
}
@manual{WA2022StartingGuidelines,
  author = {{World Athletics}}, title = {Starting Guidelines}, year = {2022}, note = {PDF footer ``December 2022''; see also IAAF editions April 2012 and June 2018},
  url = {https://worldathletics.org/download/download?filename=8c0101f9-d212-45ea-a949-452f292d0990.pdf}
}
@misc{IAAF2011FalseStarts,
  author = {{IAAF}}, title = {Comparison of False Starts}, year = {2011},
  url = {https://worldathletics.org/download/download?filename=58540761-210b-4685-8b38-21fd68f70430.pdf&urlSlug=comparison-of-false-starts}
}
@misc{Zemper2019Starters,
  author = {Zemper, Eric D.}, title = {Starters (monograph, {IAAF} edition)}, year = {2019},
  url = {https://www.bcathletics.org/admin/js/elfinder/files/Officials/Manuals/2019%20Starters%20Monograph%20-%20IAAF%202-19.pdf}
}
@misc{Zemper2008RulesHistory,
  author = {Zemper, Eric D.}, title = {The Evolution of Track and Field Rules During the Last Century}, year = {2008},
  note = {Presented at the USA Olympic Team Trials, Eugene, 4 July 2008}, url = {https://usatfne.org/officials/ruleshistory_zemper.pdf}
}
@manual{ISU2024SpeedSkating,
  author = {{International Skating Union}}, title = {Special Regulations \& Technical Rules: Speed Skating 2024}, year = {2024},
  note = {Rule 253 At the Start, para. 3.2(b)}
}
@misc{ISU2022Comm2510,
  author = {{International Skating Union}}, title = {Communication No. 2510: Testing of new rules for the Starting procedure for Short Track Speed Skating (Rule 298)},
  year = {2022}, url = {https://www.shorttrackonline.info/pdf-ISU/2510%20Zero%20False%20Start%20Testing.pdf}
}
@manual{WorldAquatics2023Swimming,
  author = {{World Aquatics (FINA)}}, title = {Swimming Technical Rules 2023--2025}, year = {2023}, note = {SW 4 The Start; valid as of 1 January 2023},
  url = {https://resources.fina.org/fina/document/2023/01/04/65961a45-bde5-4217-b666-ca1f5dc2d1f0/1_Swimming-Technical-Rules.04.01.2023.pdf}
}
@manual{FINA2021Facilities,
  author = {{FINA}}, title = {Facilities Rules 2021--2025}, year = {2021}, note = {FR 2.3.3, FR 2.3.6.3},
  url = {https://resources.fina.org/fina/document/2022/02/08/77c3058d-b549-4543-8524-ad51a857864e/210805-Facilities-Rules_clean.pdf}
}
@misc{FIALightSignals,
  author = {{FIA}}, title = {Recommended light signals for standing starts in circuit events}, note = {Referred to in Appendix H, Art. 4.3.1, International Sporting Code},
  url = {https://www.fia.com/sites/default/files/regulation/file/03__Recommended_light_signals.pdf}
}
@manual{UCI2021Track,
  author = {{Union Cycliste Internationale}}, title = {UCI Cycling Regulations, Part 3: Track Races}, year = {2021}, note = {Version 25.10.2021; art. 3.2.016, 3.2.021ter}
}
@manual{USRowing2023,
  author = {{USRowing}}, title = {The Rules of Rowing, 2023 Edition}, year = {2023}, note = {Rule 2-306}
}
@misc{SwissTimingASC3,
  author = {{Swiss Timing Ltd}}, title = {{ASC3} -- False Start Detection System (datasheet)}, year = {2015},
  url = {https://www.swisstiming.com/fileadmin/Resources/Data/Datasheets/DOCM_AT_ASC3_FalseStartDetectionSystem_0715_EN.pdf}
}
@misc{PatentUS8992386,
  author = {Zanetta, Andr{\'e} and Grimm, C{\'e}dric and Galli, Reto}, title = {Starting device for a competitor in a sports competition},
  howpublished = {US Patent 8,992,386 B2 (Swiss Timing Ltd), priority 7 Jun 2011, granted 31 Mar 2015}, year = {2015}
}
@misc{PatentUS11517804,
  author = {Harrison, Andrew and Barr, Thomas and Hayes, Kevin}, title = {Method and apparatus for false start detection},
  howpublished = {US Patent 11,517,804 B2 (University of Limerick), filed 27 Jul 2018, granted 6 Dec 2022}, year = {2022}
}
@misc{PatentUS6002336,
  author = {Widding, Erik and DeAngelis, Douglas and Barton, Andrew}, title = {Reaction time measurement system},
  howpublished = {US Patent 6,002,336 (Lynx System Developers), filed 2 Dec 1997, granted 14 Dec 1999}, year = {1999}
}
@misc{PatentUS7403135,
  author = {Kaski, Kurt R. and VanBemmel, Allen J. and Warne, Jason C.}, title = {Capacitive relay takeoff swimming platform sensor system},
  howpublished = {US Patent 7,403,135 B1 (Daktronics), filed 30 Apr 2007, granted 22 Jul 2008}, year = {2008}
}
```
