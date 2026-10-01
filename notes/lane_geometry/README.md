# Tokyo 2025 lane gradient: one-sound-source geometry (EXPLORATORY)

Status: exploratory, on data already examined (it generated the hypothesis). Written 2026-10-01 before any
confirmatory data (video of the start, other meets at the stadium) was looked at, so the predictions below are on record.

## What was fitted
WCH2025 home-straight starts, days 1-4 (13-16 Sep): 351 starts, 44 races (100 m 204, 100 mH 75, 110 mH 72). Response:
athlete- and design-adjusted RT centred within race (`recent_probe.py` adjustment). Model: each athlete reacts to sound
travelling through the air at c = 348.6 m/s (28.5 C) from one point (x_s along the track from the 100 m line, y_s
lateral from the inner edge of lane 1); the 110 mH line is 10 m behind; lanes 1.22 m wide. Optional scale alpha.

## Results (output.txt)
- Per-line linear slopes: 100 m / 100 mH line 2.84 ms per lane; 110 mH line 0.54.
- Pure airborne delay (alpha = 1, two parameters): source 4.2 m ahead of the 100 m line at the inner edge of lane 1
  (y_s at its bound, 0 m); fits as well as two free per-line slopes (SSE 71,680 vs 71,797). With alpha free: x_s 5.4 m,
  alpha 1.12 (bootstrap 95%: x_s 1.4 to 22.5 m, y_s -1.3 to 0 m, alpha 0.7 to 3.0).
- It reproduces the 100 m line gradient with no free scale (2.72 vs 2.84 ms per lane).
- Independent level check (not used in the fit): the same 24 athletes were 22.2 ms [15.9, 28.6] slower at the 100 m line
  than at their 200 m start; the fitted source predicts a mean airborne delay of 21.6 ms.
- The 110 mH line does not fit cleanly. A source fixed in space predicts slope 1.32 (observed 0.54 [-0.66, 1.7]) but a
  mean delay of 44.9 ms; a source that moved with the start line predicts the same slope as the 100 m line. A source
  centred behind that line would give a delay with little linear gradient. No same-athlete 200 m comparison exists there.

## Reading
Consistent with athletes at the 100 m line reacting to the start sound arriving through the air from about where a starter
stands (just ahead of the line, inside the track), rather than from the speaker behind each block. Cause still
unidentified: this is a hypothesis from seen data.

## Predictions on record (for the confirmatory step)
1. Broadcast footage of the WCH2025 100 m / 100 mH starts on 13-15 Sep shows the starter (or the start-sound source)
   inside the track, at most 1.3 m from lane 1's inner edge and 1.4 to 22.5 m ahead of the 100 m line; best estimate
   about 4 m ahead.
2. For the 110 mH starts (15-16 Sep), the source position relative to that line differs from the 100 m geometry
   (for example central or behind the blocks), since its gradient was weak.
3. Other championships' straight starts and WCH2025's 200 m starts show no comparable gradient (already seen; not a test).
A formal plan (data, measurements, decision rules) must be committed before footage or other meets are examined.
