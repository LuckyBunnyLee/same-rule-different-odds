"""Measure curated starts (one row per start attempt) from local audio.

Usage:
  python analysis/measure/measure_starts.py --curated analysis/measure/race_starts_curated.csv \
      --audio-dir data/video/audio --whisper base.en --out analysis/measure/results/starts_measured.csv

The curated file lists video_id, race_id, attempt, attempt_status and t_gun_hint (s, within +-0.5 s of the
gun). The script picks the nearest gun candidate, refines gun and "Set" onset/offset, and writes one row per
start with estimator details. Deterministic for fixed audio (whisper runs with temperature 0, beam 5).
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fpmeasure as fm  # noqa: E402


def find_audio(audio_dir, vid):
    for f in sorted(os.listdir(audio_dir)):
        if f.startswith(vid + ".") and not f.endswith((".part", ".ytdl", ".log")):
            return os.path.join(audio_dir, f)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--whisper", default="base.en", help="faster-whisper model name, or 'none'")
    ap.add_argument("--reuse", default=None, help="previous output; rows with an identical curated key are copied "
                    "(only valid when the code is unchanged; the registered producer never uses it)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    cur = pd.read_csv(a.curated)
    prev = {}
    if a.reuse and os.path.exists(a.reuse):
        for _, r in pd.read_csv(a.reuse).iterrows():
            prev[(r.video_id, r.race_id, int(r.attempt), r.attempt_status, round(float(r.t_gun_hint), 3))] = r.to_dict()
    rows = []
    cache = {}
    for _, r in cur.iterrows():
        base = dict(video_id=r.video_id, race_id=r.race_id, attempt=int(r.attempt), attempt_status=r.attempt_status,
                    t_gun_hint=r.t_gun_hint)
        key = (r.video_id, r.race_id, int(r.attempt), r.attempt_status, round(float(r.t_gun_hint), 3))
        if key in prev:
            rows.append(prev[key])
            continue
        path = find_audio(a.audio_dir, r.video_id)
        if path is None:
            rows.append({**base, "fail": "audio_missing"})
            continue
        if r.video_id not in cache:
            x = fm.load_audio(path)
            cands, _ = fm.detect_candidates(x)
            cache = {r.video_id: (x, cands)}  # keep one video in memory
        x, cands = cache[r.video_id]
        near = [c for c in cands if abs(c["t"] - r.t_gun_hint) <= 0.5]
        if not near:
            rows.append({**base, "fail": "no_candidate_near_hint"})
            continue
        c = max(near, key=lambda c: c["score"])
        words = fm.clip_words(x, fm.SR, c["t"], a.whisper) if a.whisper != "none" else None
        m = fm.measure(x, fm.SR, c, words)
        if "fail" in m:
            rows.append({**base, "fail": m["fail"]})
            continue
        rows.append({**base, "fail": "",
                     "t_gun": fm.fr(m["t_gun"]), "t_set_on": fm.fr(m["t_set_on"]), "t_set_off": fm.fr(m["t_set_off"]),
                     "fp_on_s": fm.fr(m["fp_on"]), "fp_off_s": fm.fr(m["fp_off"]),
                     "unc_on_s": fm.fr(m["unc_on"]), "unc_off_s": fm.fr(m["unc_off"]),
                     "set_snr_db": fm.fr(m["set_snr"], 2), "gun_rise_db": fm.fr(m["gun_rise_db"], 2),
                     "set_spread_s": fm.fr(m["set_spread"]), "gun_spread_s": fm.fr(m["gun_spread"]),
                     "start_score": fm.fr(c["score"], 2), "burst_choice": m["burst_choice"],
                     "qc_flag": "ok" if not m["qc"] else ";".join(m["qc"]),
                     "set_estimators": json.dumps({k: fm.fr(v) for k, v in sorted(m["set_estimators"].items())}),
                     "gun_estimators": json.dumps({k: fm.fr(v) for k, v in sorted(m["gun_estimators"].items())})})
        print(f"{r.race_id} att{r.attempt}: fp_on={m['fp_on']:.3f} qc={rows[-1]['qc_flag']}", flush=True)
    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    out.to_csv(a.out, index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
