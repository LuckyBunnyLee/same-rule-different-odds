"""Blind annotation sheets for manual reading of "Set" onset/offset and gun onset (no detector markers,
no reference marks). Window positions come from coarse hints; the analyst reads times off the zoom panels.

Usage: python analysis/measure/annotation_sheets.py --hints analysis/measure/annotation_hints.csv \
           --audio-dir data/video/audio --outdir analysis/measure/figures/annotation
hints CSV columns: sheet_id, video_id, t_gun_hint, t_set_hint
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


def env(x, sr, lo, hi, win=0.005):
    y = signal.sosfiltfilt(fm.band_sos(lo, hi, sr), x.astype(np.float64))
    t, e, w = fm.env_db(y, sr, win, 0.0005)
    return t, e


def sheet(audio, t_gun, t_set, out, title, sr=48000):
    a0 = min(t_set - 1.5, t_gun - 4.0)
    x = fm.load_audio(audio, sr=sr, start=a0, dur=(t_gun + 0.6) - a0)
    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1.3, 1])
    ax = fig.add_subplot(gs[0])
    f, tt, S = signal.spectrogram(x, fs=sr, nperseg=1024, noverlap=896)
    L = 10 * np.log10(S + 1e-14)
    ax.pcolormesh(a0 + tt, f / 1000, L, shading="auto", cmap="magma", vmin=np.percentile(L, 5), vmax=np.percentile(L, 99.7))
    ax.set_ylim(0, 14)
    ax.set_ylabel("kHz")
    ax.set_xticks(np.arange(np.ceil(a0 * 2) / 2, t_gun + 0.6, 0.5))
    ax.tick_params(axis="x", labelsize=7)
    ax.set_title(title, fontsize=10)
    for row, (z0, z1, step, minor) in ((1, (t_set - 0.3, t_set + 0.9, 0.05, 0.01)), (2, (t_gun - 0.05, t_gun + 0.03, 0.005, 0.001))):
        ax = fig.add_subplot(gs[row])
        i0, i1 = int((z0 - a0) * sr), int((z1 - a0) * sr)
        xs = x[max(0, i0 - 2400): i1 + 2400]
        base = a0 + max(0, i0 - 2400) / sr
        for (lo, hi), c in (((150, 1000), "tab:blue"), ((1000, 3000), "tab:green"), ((3000, 10000), "tab:red")):
            t, e = env(xs, sr, lo, hi, 0.005 if row == 1 else 0.001)
            ax.plot(base + t, e, c, lw=0.8)
        ax2 = ax.twinx()
        ax2.plot(base + np.arange(len(xs)) / sr, xs, color="0.6", lw=0.3, alpha=0.6)
        ax2.set_yticks([])
        ax.set_xlim(z0, z1)
        ax.set_xticks(np.round(np.arange(np.ceil(z0 / step) * step, z1, step), 4))
        ax.set_xticks(np.round(np.arange(np.ceil(z0 / minor) * minor, z1, minor), 4), minor=True)
        ax.grid(True, which="major", alpha=0.5)
        ax.grid(True, which="minor", alpha=0.15)
        ax.tick_params(axis="x", labelrotation=90, labelsize=7)
        ax.set_ylabel("dB (5 ms RMS)" if row == 1 else "dB (1 ms RMS)")
        ax.set_title("SET zoom (blue 0.15-1k, green 1-3k, red 3-10k)" if row == 1 else "GUN zoom", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=72)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hints", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    h = pd.read_csv(a.hints)
    for _, r in h.iterrows():
        audio = [os.path.join(a.audio_dir, f) for f in os.listdir(a.audio_dir) if f.startswith(r.video_id + ".")][0]
        sheet(audio, r.t_gun_hint, r.t_set_hint, os.path.join(a.outdir, f"{r.sheet_id}.png"), f"{r.sheet_id}  ({r.video_id})")
        print("ok", r.sheet_id, flush=True)


if __name__ == "__main__":
    main()
