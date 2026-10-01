"""Non-blind verification sheets: automated marks drawn on the audio of every measured start that has no blind
manual annotation. Used for gross-error screening only (verdicts go to verification_visual.csv); timing accuracy
is reported from the blind annotations, never from these sheets.

Usage:
  python analysis/measure/verification_sheets.py --measured analysis/measure/results/starts_measured.csv \
      --manual analysis/measure/manual_annotations.csv --audio-dir data/video/audio \
      --outdir analysis/measure/figures/verify
"""
import argparse
import os

import pandas as pd

from plot_start import plot_start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measured", required=True)
    ap.add_argument("--manual", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    m = pd.read_csv(a.measured)
    man = pd.read_csv(a.manual)
    done = set(zip(man.race_id, man.attempt.fillna(-1).astype(int)))
    for _, r in m.iterrows():
        if (r.race_id, int(r.attempt)) in done or (isinstance(r.fail, str) and r.fail):
            continue
        audio = [os.path.join(a.audio_dir, f) for f in sorted(os.listdir(a.audio_dir)) if f.startswith(r.video_id + ".")][0]
        name = f"{r.race_id}_att{int(r.attempt)}"
        out = os.path.join(a.outdir, name + ".png")
        if os.path.exists(out):
            continue
        off = r.t_set_off if pd.notna(r.t_set_off) else None
        plot_start(audio, r.t_gun, r.t_set_on, off, None, out=out,
                   title=f"{name} ({r.video_id})  auto fp_on={r.fp_on_s:.3f}s  qc={r.qc_flag}")
        print("ok", name, flush=True)


if __name__ == "__main__":
    main()
