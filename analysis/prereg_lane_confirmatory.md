# Pre-registration: confirmatory tests of the WCH2025 home-straight lane effect

Committed 2026-10-01, before any of the data named below was examined: no broadcast footage of the WCH2025 starts has
been looked at for the starter's position, no results from other meets at the Japan National Stadium have been
fetched, and the lanes in the WCH2025 combined-event file (`analysis/probe_scratch/combined_rt.csv`) have never been
analysed (only its medians by date were). Deviations will be recorded as dated addenda below; every result will be
reported, whatever it shows.

## Hypothesis H-L (exploratory origin: `notes/lane_geometry/`)

At the WCH2025 home-straight start used for the 100 m and 100 mH (13-15 Sep), athletes reacted to the start sound
arriving through the air from one point near the start line, at about the starter's position, rather than to the speaker
behind each block. Exploratory evidence, on the data that suggested it (351 starts, 44 races, days 1-4):
- within-race lane slope: 2.84 ms per lane at the 100 m line, 0.54 at the 110 mH line (10 m behind);
- a pure airborne-delay model (c = 348.6 m/s at 28.5 C, no free scale) puts the source 4.2 m ahead of the 100 m line at
  the inner edge of lane 1 (bound), reproducing the 100 m line slope (2.72 ms per lane); with a free scale, x_s 5.4 m,
  alpha 1.12; race-cluster bootstrap 95%: x_s 1.4 to 22.5 m, y_s -1.3 to 0 m, alpha 0.7 to 3.0;
- not used in the fit: the same 24 athletes were 22.2 ms [15.9, 28.6] slower at the 100 m line than at their 200 m
  start; the fitted source predicts a mean airborne delay of 21.6 ms.
The 110 mH line does not fit a source fixed in space. Coordinates: x along the track from that race's start line
(+ = ahead, toward the finish); y lateral from the inner edge of lane 1 (- = infield); lanes 1.22 m.

## Test L1: position of the start-sound source in footage (primary)

**Data.** Official World Athletics or host-broadcast footage (official channels; `data/derived/video_sources.csv` and the
same channels' other uploads) of WCH2025 starts: line A = 100 m (men, women) and 100 mH on 13-15 Sep; line B = 110 mH on
15-16 Sep. All rounds; every clip in which the starter (the official who fires the start, usually on a raised stand) is
visible together with enough track markings to scale the frame.

**Measurement.** For each usable start, estimate the starter's position (x, y) relative to that race's start line and
the inner edge of lane 1, using known geometry: lane width 1.22 m; the start line; 100 mH hurdle 1 at 13.00 m, 110 mH
hurdle 1 at 13.72 m; the 110 mH line 10 m behind the 100 m line; lane numbers and other markings. Give each estimate
an uncertainty. Note any visible loudspeaker or other possible start-sound source near the starter, and whether the
starter's position changes between rounds or days. Estimates by a second, independent reader (human) are reported
separately; neither reader sees the other's numbers first. Footage, frames and crops stay local (not redistributed).

**Predictions** (bootstrap ranges above, widened by 1 m for measurement error):
- P1 (line A): the source is at or inside the track's inner edge and ahead of the line: y in [-2.3, +0.5] m and
  x in [0.4, 23.5] m.
- P2 (line B, secondary): the source's position relative to the 110 mH line lies outside the P1 region, in line with the
  weak gradient there.

**Decision rule (primary, line A; median over usable starts):** supports H-L if the median (x, y) lies in the P1
region; contradicts H-L if the median is behind the line (x < -1 m) or more than 3.3 m inside the track (y < -3.3 m);
otherwise inconclusive. Supporting means the geometry is physically plausible; it does not by itself show that athletes
reacted to the airborne sound.

## Test L2: other meets at the Japan National Stadium (Tokyo)

**Data.** Every meet at the Japan National Stadium from 2021 to 2026 with lane and reaction time per athlete for 100 m,
100 mH, 110 mH and 200 m (World Athletics results pages or official results PDFs), for example the Seiko Golden Grand
Prix. Fetched and kept locally under the same rules as the other World Athletics data (not redistributed).

**Analysis.** Within-race lane slope of RT (ms per lane), race-cluster bootstrap, exactly as `recent_probe.lane_slope`,
for the 100 m line (100 m and 100 mH) and separately for the 110 mH line; RT adjusted for athlete with the main model's
athlete effects where an athlete is in our data, unadjusted otherwise (both reported; adjusted is primary where at least
half the starts are covered). Where the same athletes ran the 100 m and the 200 m at one meet, their mean 100 m-line minus
200 m RT, with a bootstrap CI.

**Predictions and reading.** (a) If H-L reflects the stadium's usual start configuration: a positive 100 m line slope
(95% CI lower bound > 0), point estimate near 2.7 ms per lane, and same athletes slower at the 100 m line than at the
200 m start. (b) If the effect was specific to the WCH2025 installation or sessions: no positive slope. Outcome (a)
supports a stadium-level mechanism; outcome (b) is consistent with a WCH2025-specific cause and does not refute H-L for
WCH2025. Fewer than 10 usable races: reported as descriptive only.

## Test L3: WCH2025 home-straight starts after 16 Sep (combined events)

**Data.** `analysis/probe_scratch/combined_rt.csv`, WCH2025 heptathlon 100 mH (19 Sep), decathlon 100 m (20 Sep) and
decathlon 110 mH (21 Sep), all at the home-straight start; valid RT 0.100-0.300 s.

**Analysis and prediction.** Within-race lane slope, race-cluster bootstrap, unadjusted (combined-event athletes are
mostly not in our data), pooled over the three events and per event. If the cause was confined to 13-16 Sep (as the
200 m starts on 17-19 Sep suggest), the slope is below the days 1-4 value: consistent with that if its 95% CI excludes
2.7 ms per lane; inconclusive if the CI includes both 0 and 2.7; against it if the CI excludes 0 on the positive side.

## Integrity

This file was committed and pushed to the public repository before any L1-L3 data was examined, so the push time is
the public record. The exploratory analysis that produced the hypothesis (`notes/lane_geometry/`) was committed before
this plan. Results go in `notes/lane_confirmatory/`, with code, and enter the full paper whatever they show.
