"""Methods figures for the audio foreperiod tool (real broadcast audio; no simulated data).

Usage:
  python analysis/measure/make_figures.py --which seiko --seiko analysis/measure/results/seiko_validation.json \
      --out analysis/measure/figures/fig_seiko_vs_broadcast.png
  python analysis/measure/make_figures.py --which example --manual analysis/measure/manual_annotations.csv \
      --waveform data/derived/rt_waveform.csv --audio-dir data/video/audio --sheet S15 \
      --out analysis/measure/figures/fig_example_start.png

Palette: reference categorical slots 1-3 (blue #2a78d6, orange #eb6834, aqua #1baf7a; validated all-pairs for
scatter), distinct marker shapes as secondary encoding, text in neutral inks.
"""
import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal

import fpmeasure as fm

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
MARKERS = ["o", "s", "^"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "fp"})


def fig_seiko(seiko_path, out):
    s = json.load(open(seiko_path, encoding="utf-8"))
    rows = pd.DataFrame(s["rows"])
    comps = sorted(rows.compyear.unique())
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.4))
    vals = pd.concat([rows.fp_on, rows.fp_vend, rows.wf_ready_time_s])
    lo, hi = float(vals.min()) - 0.1, float(vals.max()) + 0.1
    for ax, col, lab in ((axes[0], "fp_on", "broadcast foreperiod from \"Set\" onset (s)"),
                         (axes[1], "fp_vend", "broadcast foreperiod from end of voicing (s)")):
        ax.plot([lo, hi], [lo, hi], color=INK2, lw=1.0, ls="--", zorder=1)
        ax.text(hi - 0.05, hi - 0.12, "identity", color=INK2, ha="right", va="top", fontsize=8, rotation=45)
        for k, comp in enumerate(comps):
            g = rows[rows.compyear == comp]
            ax.scatter(g[col], g.wf_ready_time_s, s=36, marker=MARKERS[k], color=SERIES[k], edgecolors="white",
                       linewidths=1.0, zorder=3, label=f"{comp} (n={len(g)})")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal")
        ax.set_xlabel(lab)
    axes[0].set_ylabel("official Seiko Ready Time (s)")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8)
    n = s["n_compared"]
    fig.suptitle(f"Seiko Ready Time vs broadcast-audio foreperiod (real broadcasts; n = {n} clean valid starts, "
                 "manual reading)", fontsize=9.5, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig_example(manual, waveform, audio_dir, sheet, out):
    m = pd.read_csv(manual)
    r = m[m.sheet_id == sheet].iloc[0]
    wf = pd.read_csv(waveform).set_index("race_id")
    ready = float(wf.loc[r.race_id, "wf_ready_time_s"]) if r.race_id in wf.index else np.nan
    audio = [os.path.join(audio_dir, f) for f in sorted(os.listdir(audio_dir)) if f.startswith(r.video_id + ".")][0]
    t0, t1 = r.t_set_on - 0.6, r.t_gun + 0.5
    sr = 48000
    x = fm.load_audio(audio, sr=sr, start=t0, dur=t1 - t0)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.0, 5.0), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    f, tt, S = signal.spectrogram(x, fs=sr, nperseg=1024, noverlap=896)
    L = 10 * np.log10(S + 1e-14)
    a1.pcolormesh(tt, f / 1000, L, shading="auto", cmap="Greys", vmin=np.percentile(L, 20), vmax=np.percentile(L, 99.8))
    a1.set_ylim(0, 12)
    a1.set_ylabel("kHz")
    a1.grid(False)
    for (lo, hi), c, lab in (((150, 1000), SERIES[0], "0.15-1 kHz"), ((3000, 10000), SERIES[1], "3-10 kHz (/s/)")):
        y = signal.sosfiltfilt(fm.band_sos(lo, hi, sr), x.astype(np.float64))
        t, e, w = fm.env_db(y, sr, 0.005, 0.001)
        a2.plot(t, e, color=c, lw=1.0, label=lab)
    a2.set_ylabel("level (dB, 5 ms RMS)")
    a2.set_xlabel(f"time from {t0:.2f} s in the recording (s)")
    a2.legend(loc="upper center", frameon=False, fontsize=8, ncol=2)
    marks = [(r.t_set_on - t0, "Set onset", "-"), (r.t_voicing_end - t0, "end of voicing", ":"),
             (r.t_gun - t0, "gun", "-")]
    if np.isfinite(ready):
        marks.append((r.t_gun - ready - t0, "gun - Seiko Ready Time", "--"))
    for ax in (a1, a2):
        for tm, lab, ls in marks:
            ax.axvline(tm, color=INK, lw=1.0, ls=ls)
    ymax = a2.get_ylim()[1]
    for tm, lab, ls in marks:
        a2.text(tm + 0.01, ymax - 2, lab, rotation=90, va="top", ha="left", fontsize=7.5, color=INK)
    fp_on = r.t_gun - r.t_set_on
    fig.suptitle(f"{r.race_id}: foreperiod from Set onset {fp_on:.3f} s; Seiko Ready Time {ready:.3f} s "
                 f"(real broadcast audio, manual reading)", fontsize=9.5, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", required=True, choices=["seiko", "example"])
    ap.add_argument("--seiko")
    ap.add_argument("--manual")
    ap.add_argument("--waveform")
    ap.add_argument("--audio-dir")
    ap.add_argument("--sheet")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.which == "seiko":
        fig_seiko(a.seiko, a.out)
    else:
        fig_example(a.manual, a.waveform, a.audio_dir, a.sheet, a.out)


if __name__ == "__main__":
    main()
