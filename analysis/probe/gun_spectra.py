"""EXPLORATORY scratch: championship-average spectra of the recorded start signal (first 80 ms after onset,
excess over 300 ms of pre-gun noise, each start normalised to unit total excess power before averaging).
Prints the prominent peaks per cell and the cosine similarity between cell spectra (log scale, 300-8000 Hz)."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gun_features import SR, load  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
d = pd.read_csv(os.path.join(ROOT, "analysis/probe/gun_features.csv"))
d["cell"] = d.comp + "_" + d["loc"]
N = 8192
ff = np.fft.rfftfreq(N, 1 / SR)
band = (ff >= 300) & (ff <= 8000)
spec = {}
for cell, g in d.groupby("cell"):
    acc = []
    for _, r in g.iterrows():
        base = "analysis/probe/audio" if r.source.startswith("probe") else "data/video/audio"
        path = os.path.join(ROOT, base, r.video_id + ".webm")
        x = load(path, r.onset_s - 0.4, 0.5)
        i0 = int(0.4 * SR)
        n = int(0.080 * SR)
        s = x[i0:i0 + n] * np.hanning(n)
        nz = x[int(0.05 * SR):int(0.35 * SR)]
        Ps = np.abs(np.fft.rfft(s, n=N)) ** 2
        f_, Pn = signal.welch(nz, SR, nperseg=n, window="hann", nfft=N)
        Pn = Pn * (np.sum(np.hanning(n) ** 2)) * SR / 2  # rough scale match to periodogram
        ex = np.maximum(Ps - Pn, 1e-12)
        ex = ex / ex[band].sum()
        acc.append(ex)
    spec[cell] = np.mean(acc, axis=0)
rows = []
for cell, S in spec.items():
    L = 10 * np.log10(S[band] + 1e-15)
    pk, pr = signal.find_peaks(L, prominence=6, distance=30)
    top = sorted(zip(L[pk], ff[band][pk]), reverse=True)[:4]
    rows.append((cell, [int(round(f, -1)) for _, f in top]))
    print(cell, "top peaks (Hz):", [int(round(f, -1)) for _, f in top])
cells = list(spec)
M = np.array([10 * np.log10(spec[c][band] + 1e-15) for c in cells])
M = M - M.mean(axis=1, keepdims=True)
M = M / np.linalg.norm(M, axis=1, keepdims=True)
sim = pd.DataFrame(M @ M.T, index=cells, columns=cells).round(3)
print(sim.to_string())
sim.to_csv(os.path.join(ROOT, "analysis/probe/gun_spectra_similarity.csv"))
pd.DataFrame([(c, ";".join(str(x) for x in pk)) for c, pk in rows], columns=["cell", "top_peaks_hz"]).to_csv(
    os.path.join(ROOT, "analysis/probe/gun_spectra_peaks.csv"), index=False)
