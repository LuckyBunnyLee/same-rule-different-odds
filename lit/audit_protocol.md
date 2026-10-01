# Literature audit protocol: championship-level variation in published championship-RT studies

Part of the systematic literature audit. Written and committed **before any study was coded**, 2026-09-30 ~17:20 PT.
Any later change is appended to §9 (Deviations) with a time stamp; nothing above §9 is edited after the protocol commit.

## 1. Question and the quantity reported

How much of the published literature that analyses **official reaction times (RTs) from championship competition** draws
conclusions from designs that are exposed to championship-level variation (differences between championships in
measurement system, start procedure, conditions or field that shift every athlete's RT at that meet)?

The audit produces generated counts (never typed) for a sentence of the form: "Of N published studies analysing official
championship RTs, K drew conclusions from designs that pool, contrast or generalise championships without modelling them."
The counts describe **design exposure**, not error. A vulnerable design can still reach a correct conclusion; the audit
never claims that a coded study is wrong.

## 2. Sources and queries

All searches run 2026-09-30 by `lit/tools/audit_search.py`; raw records are saved under `lit/audit_search/` with the exact
query string, URL, retrieval time and the hit count each source reports.

**Concept groups** (the suggested terms, widened by three terms that the repo's known studies use: "response time",
used by Brosnan et al. 2017; "IAAF" and "World Athletics", used in place of "championship" by several papers; and hurdle*,
because sprint hurdles are block-start events):

- G1 (outcome): "reaction time" OR "reaction times" OR "response time" OR "start reaction"
- G2 (setting): sprint* OR "false start" OR "false starts" OR "starting block" OR "starting blocks" OR "block start" OR hurdle*
- G3 (competition): championship* OR Olympic* OR "World Championships" OR "world indoor" OR IAAF OR "World Athletics"
- Query = G1 AND G2 AND G3; publication years 1990–2026.

**Per-source syntax** (the script stores the literal string sent):

| Source | Field / syntax | Limits |
|---|---|---|
| OpenAlex (`api.openalex.org/works`) | `filter=title_and_abstract.search:<boolean>` (uppercase AND/OR, quoted phrases; OpenAlex stems words, so `sprint` stands for sprint*), `publication_year:1990-2026` | all pages |
| PubMed (E-utilities `esearch`/`efetch`) | `[tiab]` on every term, truncation `sprint*[tiab]`, `hurdle*[tiab]`, `championship*[tiab]`, `olympic*[tiab]`, date `1990:2026[dp]` | all records |
| Semantic Scholar (`/graph/v1/paper/search/bulk`) | boolean syntax (`+` AND, `|` OR, quoted phrases, `*` prefix), `year=1990-2026` | all pages; retried with back-off if rate-limited (HTTP 429); recorded as unreachable if it never answers |
| Google Scholar | `("reaction time" OR "response time") (sprint OR sprinter OR sprinters OR "false start" OR "starting blocks") (championships OR Olympic OR IAAF OR "World Athletics")`, 1990–2026 | reported hit count recorded; the first 100 results (10 pages) screened if the site serves them; stop at the first CAPTCHA and record how far it got |

**Citation chasing** (one round, not iterated): seeds are the championship-RT studies already in
`lit/systematic_forensics.md` §2 and §4 that have a DOI, plus the review Milloz, Hayes & Harrison 2021 (a hub, used for
chasing only). Backward = the seed's reference list (OpenAlex `referenced_works`); forward = works citing the seed
(OpenAlex `cites:` filter). The seed list and per-seed counts are saved with the raw records.

**Repo studies.** Every championship-RT study named in `lit/systematic_forensics.md`, `lit/review.md`,
`lit/novelty-final-check.md`, `lit/notes/lit_notes_sports.md` and `lit/policy_mechanism.md` enters screening as source
"repo", whether or not a search found it. Non-English entries already in the repo (Japanese, German-abstract) are screened
like any other record; no new non-English search is run.

## 3. Screening

- **De-duplication**: by DOI (lower-cased), then by normalised title (lower case, alphanumerics only) plus year ±1.
  The record kept is the one with a DOI; the others are logged as duplicates.
- **Stage 1, automatic off-topic exclusion** (reproducible, conservative): a record whose title **and** available abstract
  contain none of the athletics terms {sprint, sprinter, athletics, track and field, track-and-field, 100 m, 100-m, 100m,
  200 m, 60 m, hurdle, false start, starting block, block start, IAAF, World Athletics} is excluded as "off-topic (auto)".
  Records with no abstract are never auto-excluded; they go to stage 2 on the title.
- **Stage 2, title/abstract screening** by one reviewer (an AI model) against §4. Each record gets one decision and one
  reason code in `lit/audit_screening.csv`.
- **Stage 3, eligibility** on the best available text (full text where open, else abstract, else a secondary description).
  The access level reached is recorded.
- Single-reviewer screening and coding is a limitation (§8); a second coder is recommended before the full paper.

## 4. Eligibility

**Include** (all must hold):
1. Publication type: peer-reviewed journal article, peer-reviewed conference paper (including ISBS proceedings),
   *New Studies in Athletics* (NSA) article, or thesis (master's or doctoral).
2. Data: **official RTs** (start-information-system values published or supplied by the organiser or timing company)
   from **championship competition**: Olympic Games, World Championships (outdoor, indoor, U20, U18/youth),
   continental championships, Commonwealth Games, Universiade, national championships. One-day meetings only (e.g.
   Diamond League) do not qualify on their own; a study that pools them with championships qualifies.
3. Event: athletics block-start events (60–400 m, hurdles, relay first legs), any sex or age group, including para
   athletics.
4. Claim: reports at least one effect, comparison, correlation or threshold about RT that it interprets (an
   **inferential claim**: a test, an interval, a model coefficient, or a threshold/limit estimate presented as evidence).

**Exclude, recorded separately (not in the denominator):**
- **E-LAB**: lab-only RT data (including studies whose only competition component is a hold duration or other non-RT
  measure). Listed as context.
- **E-DESC**: official championship RTs, but purely descriptive (means/tables without a comparison, test or threshold
  presented as evidence). Listed and flagged.
- **E-REV**: reviews, commentaries, viewpoints, rule histories with no primary RT analysis.
- **E-TYPE**: championship-RT analysis in a publication type outside item 1 (conference abstract, departmental bulletin,
  magazine, blog, forum, news). Listed; enters only the grey-literature sensitivity count (§7).
- **E-SPORT**: other sports (swimming, skating, cycling, e-sports), non-sprint athletics events, or non-athletes.
- **E-OFF**: off-topic (cognitive RT, clinical, etc.), including the automatic stage-1 exclusions.
- **E-DUP**: duplicates (including a conference version of a later journal article reporting the same data and finding;
  the journal version is kept).
- **E-NA**: no abstract or text reachable and no secondary description adequate to establish eligibility.

## 5. Coding (per finding, then per study)

**Finding.** Each distinct effect, comparison, correlation or threshold that the study reports **and interprets in its
abstract or conclusions** is one row of `lit/audit_studies.csv`. Means reported without a comparison are not findings.
A study's findings are coded from the most authoritative text reached; the verification tag is per finding.

**Design class** (exactly one per finding; `k` = number of championships contributing data to the finding):

| Class | Rule |
|---|---|
| **P** | k ≥ 2 championships pooled into one analysis with **no championship or venue term** (no fixed or random championship effect, no per-championship stratification, no within-championship centring) and the finding is not an era/period contrast. Includes contrasts between groups present at every meet (sex, round) estimated from the pooled data. |
| **S** | k = 1 championship and the conclusion is **generalised** beyond that championship: stated as a property of sprinters, of RT, of the rule, of equipment or of competitions in general, or used for a rule, threshold, equipment or training recommendation. |
| **E** | A contrast between eras/periods (rule eras, years) **or another championship-level factor** (timing vendor/device, venue type) whose levels are constant within a championship, so that championships are nested in the factor's levels, with no championship term. Includes within-athlete comparisons across championships, and a single championship standing for a level. |
| **M** | Championship/venue is modelled: a fixed or random championship effect, per-championship estimates, within-championship centring, or the championship difference itself is the reported quantity. |
| **W** | Within-championship comparison only, and the conclusion is restricted to that championship (or to within-meet contrasts with every championship treated as a block). |
| **U** | Unclear: the text reached does not allow one of the above. **Unknowns are never filled in by assumption.** |

Coding rules for hard cases, fixed now:
- If the text reached does not say whether championship was modelled, the class is **U**, unless the reported numbers
  themselves pin the design (e.g. a single pooled percentile or a pooled correlation reported as the result). The
  evidence used is quoted or pointed to in `notes`.
- A contrast across championships attributed to a factor confounded with championship (rule era, vendor) is **E** even
  if each era has several championships, unless championship is modelled (then **M**).
- A model with a venue effect whose reported conclusion is a quantity **averaged (integrated) over venues** is **M** with
  `m_averages_venues = yes`.

**Effect type** (one per finding): `hold_foreperiod`, `rule_era`, `sex`, `threshold_limit` (minimum legitimate RT,
tail probability, recommended threshold), `lane`, `round`, `performance_correlation`, `other` (age, vendor/device,
event, level, trend over years, nationality...; the specific type goes in `notes`).

**depends_on_between_contrast** (yes / no / unclear): **yes** if the finding's point estimate or its conclusion would
change if championship-level differences were removed, i.e. the comparison is (partly) between championships (pooled
correlations or thresholds across meets, era/vendor contrasts, single-meet levels generalised); **no** if the contrast is
entirely within championship (sex, lane or round at one meet, within-championship models).

**Other columns**: citation, year, DOI, publication type, access (`OA`, `closed`, `unknown`), data source (official
results source and timing vendor where stated), championships, k, events, conclusion scope, direction/result (for
conflict grouping), verification tag, evidence/notes. Verification tags: **[V-FT]** full text, **[V-ABS]** abstract,
**[S]** secondary source, **[U]** unverified. Where the repo's forensics coding exists it is reused **only after
re-checking it against these rules**, and any change is noted.

## 6. Definition of "vulnerable"

A finding is **vulnerable** if its design class is **P, S or E**, or **M with `m_averages_venues = yes`**.
Findings coded W, M (not averaging) or U are not vulnerable in the primary count. The rule is applied by
`analysis/lit_audit.py`, which recomputes it from the class columns and fails if the stored `vulnerable` column disagrees.

A **study** is vulnerable if at least one of its findings is.

## 7. Reported counts

Primary (all included studies; class U counted as not vulnerable):
1. **Studies**: K = studies with ≥ 1 vulnerable finding, out of N included studies; share K/N.
2. **Findings**: vulnerable findings out of all coded findings.
3. **Conflicts**: a **conflict group** is an effect type on which ≥ 2 included studies report results that disagree:
   opposite signs, or a significant effect in one and a reported null in another, or threshold/limit estimates that lead
   to opposite recommendations relative to 0.100 s (raise vs keep/lower). Reported: the number of conflict groups, the
   findings and studies in them, and how many of those findings are vulnerable.
4. Breakdowns by effect type and by design class.

Sensitivities (reported beside the primary, never instead of it):
- **strict**: vulnerable **and** `depends_on_between_contrast = yes` (exposure of the point estimate, not only of P values
  or generalisation);
- **U as vulnerable** (upper bound) — the primary already treats U as not vulnerable (lower bound);
- **verified-only**: findings whose design coding rests on [V-FT] or [V-ABS] evidence only;
- **grey literature added**: E-TYPE studies coded with the same rules and added to N and K.

## 8. Limits stated in advance

- Not exhaustive: four databases, one round of citation chasing, English queries.
- English-dominant: non-English work enters only through the repo or English-indexed metadata.
- Many full texts are closed; those studies are coded from abstracts or secondary descriptions, which raises the share
  of class U and makes the primary count a lower bound in that respect.
- One reviewer; no inter-rater reliability.
- The audit classifies designs, not the truth of findings.

## 9. Deviations (appended after the protocol commit)

Appended 2026-09-30 ~17:40 PT, after screening and coding. None changes the class definitions, the vulnerable rule or
the reported counts defined above; each is a clarification forced by a case the text above did not settle.

1. **Publication type.** Journal articles were accepted as peer-reviewed without checking each journal's review
   policy (several are small open-access journals). Conference papers were accepted only from ISBS and from an
   IEEE-published conference (Mukai et al. 2020); other proceedings (Cairo 2011; World Congress of Performance
   Analysis of Sport 2008), congress abstracts (JSPE, ACSM/MSSE), a departmental bulletin, an edited-book chapter and
   web reports went to E-TYPE and were coded for the grey-literature sensitivity only.
2. **Language.** The task restricts the audit to English plus non-English entries already in the repo. Records whose
   full text is not in English and that were not in the repo were excluded as **E-LANG** even when an English abstract
   is indexed (Chinese, Czech, Serbian, Korean, Finnish and Spanish items; 13 records). Their notes say what they
   analysed; several would have been coded E or S (e.g. a Berlin 2009 vs Daegu 2011 rule contrast).
3. **Era contrasts.** Section 5 says era contrasts are E "unless championship is modelled", and also that unknown
   modelling gives U. Where these collide (Brosnan et al. 2017; Han et al. 2025: closed full texts), the era rule was
   applied: an era coefficient cannot be estimated alongside championship fixed effects, so only a reported
   championship random effect would make the design M, and neither abstract reports one.
4. **Pooled group contrasts.** A sex, round or event contrast estimated over several championships was coded P only
   when the reported analysis pins the pooling (a pooled correlation, percentile, t-test or one threshold per sex, or a
   secondary source that read the full text, e.g. Pushkar et al. 2014 on Tonnessen et al. 2013); otherwise U
   (Collet 1999, Mukai et al. 2020, Juhas et al. 2015).
5. **Findings outside the abstract.** One finding interpreted in a full text the repo had verified but absent from the
   abstract was coded (Lipps et al. 2011, no lane effect at Beijing), because the lane conflict depends on it.
6. **Conflict groups** require a stated direction; findings without one (Paradisis 2013; the round contrast of
   Mitasik et al. 2020b; Yokokura et al. 2011) are coded but not assigned to a group. Direction labels are recorded
   in a `direction` column.
7. **Extra columns** beyond section 5: `direction`, `reports_champ_difference` (the finding itself is a
   between-championship RT difference), `design_tag` (the evidence level for the design class, used by the
   verified-only sensitivity), `forensics_check` (agreement with `lit/systematic_forensics.md`), `in_primary`.
8. **Search mechanics.** Semantic Scholar's bulk endpoint answered (no back-off needed); Google Scholar served all 10
   pages (100 results) of a reported 6,980; one round of OpenAlex citation chasing from 18 seeds (all resolved).
   Google Scholar result tags ("[PDF]", "[HTML]") were stripped before title de-duplication; record ids carry a title
   hash so that near-identical titles cannot collide. A study is one publication; companion papers on the same
   championship data but different findings (Delalija & Babic 2008; Babic & Delalija 2009a, 2009b) count separately.


### Note (2026-09-30, added during the analysis)

A false-start classification fix in `analysis/common.py` (commit 5a12182) required rerunning every producer. The
literature audit reads no RT data; `analysis/outputs/lit_audit.json` was regenerated byte-identical, so nothing here
changed.
