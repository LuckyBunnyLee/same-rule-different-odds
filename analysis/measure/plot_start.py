"""Diagnostic figure for one measured start: spectrogram + band envelopes around "Set" and the gun.

Markers: set onset (green), set offset (orange), gun onset (red), optional reference mark (magenta dashed,
e.g. gun - Seiko Ready Time). A blind mode draws no markers (for manual annotation before seeing the output).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import fpmeasure as fm


def _bands(ax, x, sr, t0):
    t = t0 + np.arange(len(x)) / sr
    for (lo, hi), c, lab in (((150, 1000), "tab:blue", "0.15-1 kHz"), ((1000, 3000), "tab:green", "1-3 kHz"),
                             ((3000, 10000), "tab:red", "3-10 kHz")):
        y = signal.sosfiltfilt(fm.band_sos(lo, hi, sr), x.astype(np.float64))
        tt, e, w = fm.env_db(y, sr, 0.005, 0.001)
        ax.plot(t0 + tt, e, c, lw=0.7, label=lab)
    ax.set_ylabel("dB")
    ax.grid(True, alpha=0.3)


def plot_start(audio_path, t_gun, t_set_on=None, t_set_off=None, t_ref=None, title="", out="start.png",
               pre=4.0, post=0.6, blind=False, sr=48000, zoom_half=0.45):
    t0 = t_gun - pre
    x = fm.load_audio(audio_path, sr=sr, start=t0, dur=pre + post)
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.2, 1, 1.1])
    ax_sp = fig.add_subplot(gs[0, :])
    ax_en = fig.add_subplot(gs[1, :], sharex=ax_sp)
    f, tt, S = signal.spectrogram(x, fs=sr, nperseg=1024, noverlap=896)
    ax_sp.pcolormesh(t0 + tt, f / 1000, 10 * np.log10(S + 1e-14), shading="auto", cmap="magma",
                     vmin=np.percentile(10 * np.log10(S + 1e-14), 5), vmax=np.percentile(10 * np.log10(S + 1e-14), 99.7))
    ax_sp.set_ylim(0, 14)
    ax_sp.set_ylabel("kHz")
    _bands(ax_en, x, sr, t0)
    ax_en.legend(loc="upper left", fontsize=7)
    ax_en.set_xlabel("time in recording (s)")
    ax_en.set_xlim(t0, t_gun + post)
    zooms = []
    if t_set_on is not None or blind:
        zc = t_set_on + 0.15 if t_set_on is not None else t_gun - 2.0
        zooms.append(("set", zc - zoom_half, zc + zoom_half))
    zooms.append(("gun", t_gun - 0.12, t_gun + 0.08))
    for j, (name, a, b) in enumerate(zooms[:2]):
        ax = fig.add_subplot(gs[2, j])
        i0, i1 = int((a - t0) * sr), int((b - t0) * sr)
        xs = x[max(0, i0):max(0, i1)]
        if len(xs) > 100:
            _bands(ax, xs, sr, a)
            ax.set_xlim(a, b)
            step = 0.05 if name == "set" else 0.01
            ax.set_xticks(np.round(np.arange(np.ceil(a / step) * step, b, step), 3))
            ax.tick_params(axis="x", labelrotation=90, labelsize=7)
            ax.set_title(f"zoom: {name}", fontsize=9)
        if not blind:
            _marks(ax, t_gun, t_set_on, t_set_off, t_ref)
    if not blind:
        for ax in (ax_sp, ax_en):
            _marks(ax, t_gun, t_set_on, t_set_off, t_ref)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=72)
    plt.close(fig)


def _marks(ax, t_gun, t_on, t_off, t_ref):
    for t, c, ls in ((t_on, "lime", "-"), (t_off, "orange", "-"), (t_gun, "red", "-"), (t_ref, "magenta", "--")):
        if t is not None and np.isfinite(t):
            ax.axvline(t, color=c, ls=ls, lw=1.1)
