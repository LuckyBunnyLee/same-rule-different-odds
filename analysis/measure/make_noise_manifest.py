"""Deterministic list of real-broadcast noise windows (no starter commands) for the synthetic benchmark.

Usage:
  python analysis/measure/make_noise_manifest.py --curated analysis/measure/race_starts_curated.csv \
      --out analysis/measure/benchmark_noise_manifest.csv

For every curated start (gun time g) three 12 s windows are proposed:
  commentary : [g-75, g-63]   pre-race introductions (commentary, PA, crowd)
  hush       : [g-25, g-13]   the quiet period around "On your marks" (may contain that command, never "Set")
  race       : [g+1.5, g+13.5] crowd and commentary during the race
A window is dropped if it overlaps [g'-5, g'+1] of any start g' in the same recording, or starts before 5 s.
  hold       : [end of voicing + 0.15, gun - 0.03] of clean manually annotated starts: the real background
               during the set-to-gun hold (short; the benchmark stitches several with crossfades)
"""
import argparse

import pandas as pd

WINDOWS = {"commentary": (-75.0, -63.0), "hush": (-25.0, -13.0), "race": (1.5, 13.5)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated", required=True)
    ap.add_argument("--manual", required=True)
    ap.add_argument("--split", required=True, choices=["dev", "all"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cur = pd.read_csv(a.curated)
    if a.split == "dev":
        cur = cur[cur.source.astype(str).str.startswith("manual_annotation_sheet_S")]
    rows = []
    for vid, g in cur.groupby("video_id", sort=True):
        guns = sorted(g.t_gun_hint.tolist())
        for t in guns:
            for typ, (d0, d1) in WINDOWS.items():
                w0, w1 = round(t + d0, 2), round(t + d1, 2)
                if w0 < 5:
                    continue
                if any(w0 < gg + 1.0 and w1 > gg - 5.0 for gg in guns):
                    continue
                rows.append(dict(video_id=vid, noise_type=typ, t0=w0, t1=w1, ref_gun=t))
    man = pd.read_csv(a.manual)
    if a.split == "dev" and "split" in man.columns:
        man = man[man.split.fillna("dev") == "dev"]
    man = man[(man.clean == 1) & man.t_voicing_end.notna() & man.t_gun.notna()]
    for _, r in man.iterrows():
        t0, t1 = round(r.t_voicing_end + 0.15, 3), round(r.t_gun - 0.03, 3)
        if t1 - t0 >= 0.5:
            rows.append(dict(video_id=r.video_id, noise_type="hold", t0=t0, t1=t1, ref_gun=r.t_gun))
    out = pd.DataFrame(rows).drop_duplicates(["video_id", "t0"]).sort_values(["noise_type", "video_id", "t0"])
    out.to_csv(a.out, index=False, lineterminator="\n")
    print(out.groupby("noise_type").size().to_dict())


if __name__ == "__main__":
    main()
