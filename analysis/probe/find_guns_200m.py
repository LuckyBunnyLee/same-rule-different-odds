"""EXPLORATORY scratch: locate start guns in the WCH2025 200m full-round compilations (audio only), using the
measurement pipeline's candidate detector (analysis/measure/fpmeasure.py; pure functions only) on 300 s chunks.
Writes analysis/probe/guns_200m_wch2025.csv (one row per candidate with score >= threshold)."""
import os, subprocess, sys
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "analysis", "measure"))
import fpmeasure as fm  # noqa
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
def load(path, sr, start, dur):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{max(start,0):.4f}", "-i", path,
           "-t", f"{dur:.4f}", "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True, creationflags=FLAGS).stdout, dtype=np.float32).copy()
rows = []
for vid, lab in [("NjJAn9hcsv8", "200m-M"), ("AXbIf9u_G70", "200m-W")]:
    path = os.path.join(ROOT, "analysis", "probe", "audio", vid + ".webm")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True, creationflags=FLAGS).stdout)
    step, pad = 300.0, 15.0
    t = 0.0
    while t < dur:
        s0 = max(0.0, t - pad)
        x = load(path, fm.SR, s0, step + 2 * pad)
        cands, E = fm.detect_candidates(x, fm.SR)
        for c in cands:
            tt = s0 + c["t"]
            if not (t <= tt < t + step):
                continue
            rows.append(dict(video_id=vid, label=lab, t=round(tt, 3), score=round(c["score"], 2), gun_jump=round(c["gun_jump"], 1),
                             race_loud=round(c["race_loud"], 1), set_gap=round(c["set_gap"], 3) if np.isfinite(c["set_gap"]) else None,
                             set_snr=round(c["set_snr"], 1), n_bursts=c["n_bursts"], hold_excess=round(c["hold_excess"], 1)))
        t += step
        print(lab, int(t), len(rows), flush=True)
df = pd.DataFrame(rows).sort_values(["video_id", "t"])
df.to_csv(os.path.join(ROOT, "analysis", "probe", "guns_200m_wch2025_candidates.csv"), index=False)
print(df.sort_values("score", ascending=False).groupby("video_id").head(16).sort_values(["video_id", "t"]).to_string())
