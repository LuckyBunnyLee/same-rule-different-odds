"""EXPLORATORY scratch: run gun_features over every locally available start (foreperiods.csv guns plus the
WCH2025 200m compilation guns found by find_guns_200m.py). Writes analysis/probe/gun_features.csv."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gun_features import features  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
fp = pd.read_csv(os.path.join(ROOT, "data/derived/foreperiods.csv"))
rows = []
for _, r in fp.iterrows():
    path = os.path.join(ROOT, "data/video/audio", r.video_id + ".webm")
    if not os.path.exists(path):
        continue
    son = r.gun_s - r.foreperiod_s if np.isfinite(r.foreperiod_s) else None
    f = features(path, r.gun_s, son, r.set_offset_s if np.isfinite(r.set_offset_s) else None)
    if f is None:
        continue
    rows.append(dict(race_id=r.race_id, attempt=r.attempt, status=r.attempt_status, video_id=r.video_id, gun_s=r.gun_s,
                     foreperiod_s=r.foreperiod_s, source="foreperiods.csv", **f))
g = pd.read_csv(os.path.join(ROOT, "analysis/probe/guns_200m_wch2025_candidates.csv"))
g = g[(g.score >= 44) & (g.gun_jump >= 25)]
for _, r in g.iterrows():
    path = os.path.join(ROOT, "analysis/probe/audio", r.video_id + ".webm")
    if not os.path.exists(path):
        continue
    son = r.t - r.set_gap if np.isfinite(r.set_gap) else None
    f = features(path, r.t, son, None)
    if f is None:
        continue
    rows.append(dict(race_id=f"WCH2025-{r.label}-compilation", attempt=np.nan, status="valid (detector)",
                     video_id=r.video_id, gun_s=r.t, foreperiod_s=r.set_gap, source="probe 200m compilation", **f))
df = pd.DataFrame(rows)
df["comp"] = df.race_id.str.extract(r"^([A-Z]+\d{4})", expand=False)
df["loc"] = np.where(df.race_id.str.contains("200m"), "200m", "straight")
df.to_csv(os.path.join(ROOT, "analysis/probe/gun_features.csv"), index=False)
cols = ["peak_hz", "centroid_hz", "flatness", "hf_share", "rise_ms", "t_peak_ms", "dur10_ms", "dur20_ms",
        "two_step_ms", "hf_rise_db", "gun_minus_set_db", "foreperiod_s", "tonal_f1"]
pd.set_option("display.width", 250)
print(df.groupby(["comp", "loc"])[cols].median().round(2).to_string())
print(df.groupby(["comp", "loc"]).size())
