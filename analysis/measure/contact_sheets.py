"""Compact non-blind contact sheets (4 starts per image) for gross-error screening of automated marks.

Usage:
  python analysis/measure/contact_sheets.py --measured analysis/measure/results/starts_measured.csv \
      --manual analysis/measure/manual_annotations.csv --audio-dir data/video/audio \
      --outdir analysis/measure/figures/contact
Each cell: spectrogram (0-12 kHz) over [set onset - 1.2 s, gun + 0.4 s] and 0.15-1 kHz / 3-10 kHz envelopes;
green = automated set onset, orange = set offset, red = gun. Cell titles carry the index used in
verification_visual.csv.
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal

import fpmeasure as fm


def cell(axs, audio, r, idx):
    sr = 48000
    t0 = r.t_set_on - 1.2
    t1 = r.t_gun + 0.4
    x = fm.load_audio(audio, sr=sr, start=t0, dur=t1 - t0)
    f, tt, S = signal.spectrogram(x, fs=sr, nperseg=1024, noverlap=768)
    L = 10 * np.log10(S + 1e-14)
    axs[0].pcolormesh(t0 + tt, f / 1000, L, shading="auto", cmap="magma", vmin=np.percentile(L, 5), vmax=np.percentile(L, 99.7))
    axs[0].set_ylim(0, 12)
    for (lo, hi), c in (((150, 1000), "tab:blue"), ((3000, 10000), "tab:red")):
        y = signal.sosfiltfilt(fm.band_sos(lo, hi, sr), x.astype(np.float64))
        t, e, w = fm.env_db(y, sr, 0.005, 0.002)
        axs[1].plot(t0 + t, e, c, lw=0.6)
    for ax in axs:
        for tm, c in ((r.t_set_on, "lime"), (r.t_set_off, "orange"), (r.t_gun, "red")):
            if pd.notna(tm):
                ax.axvline(tm, color=c, lw=1.0)
        ax.set_xlim(t0, t1)
        ax.tick_params(labelsize=6)
    axs[1].grid(True, alpha=0.3)
    axs[0].set_title(f"[{idx}] {r.race_id} att{int(r.attempt)} fp={r.fp_on_s:.3f} {r.qc_flag}"[:95], fontsize=7)


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
    u = m[[(r, int(t)) not in done for r, t in zip(m.race_id, m.attempt)]].reset_index(drop=True)
    u = u[u.fail.isna()].reset_index(drop=True) if "fail" in u.columns else u
    u.insert(0, "idx", range(len(u)))
    u[["idx", "race_id", "attempt", "video_id", "t_set_on", "t_gun", "fp_on_s", "qc_flag"]].to_csv(
        os.path.join(a.outdir, "index.csv"), index=False, lineterminator="\n")
    for page in range(0, len(u), 4):
        fig, axes = plt.subplots(4, 2, figsize=(16, 9), gridspec_kw={"height_ratios": [1.3, 1, 1.3, 1]})
        for k in range(4):
            j = page + k
            col, row = k % 2, (k // 2) * 2
            if j >= len(u):
                axes[row, col].axis("off")
                axes[row + 1, col].axis("off")
                continue
            r = u.iloc[j]
            audio = [os.path.join(a.audio_dir, f) for f in sorted(os.listdir(a.audio_dir)) if f.startswith(r.video_id + ".")][0]
            cell((axes[row, col], axes[row + 1, col]), audio, r, int(r.idx))
        fig.tight_layout()
        fig.savefig(os.path.join(a.outdir, f"page{page // 4:02d}.png"), dpi=70)
        plt.close(fig)
        print("page", page // 4, flush=True)


if __name__ == "__main__":
    main()
