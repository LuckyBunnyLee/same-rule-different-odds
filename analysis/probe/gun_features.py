"""EXPLORATORY scratch (recent_probe): acoustic features of the start signal as recorded in broadcast audio.

Only relative, within-recording quantities are meaningful: broadcast gain, compression, limiting, codec and
microphone placement are unknown, so absolute level at the blocks and trigger-to-speaker latency are NOT
measurable from these recordings.
"""
import subprocess

import numpy as np
from scipy import signal

FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SR = 48000


def load(path, start, dur, sr=SR):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{max(start, 0):.4f}", "-i", path,
           "-t", f"{dur:.4f}", "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True, creationflags=FLAGS).stdout
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def bp(x, lo, hi, sr=SR):
    sos = signal.butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x)


def env(x, w, sr=SR, hop=0.0005):
    n = int(w * sr)
    h = max(1, int(hop * sr))
    c = np.concatenate([[0.0], np.cumsum(x ** 2)])
    starts = np.arange(0, len(x) - n, h)
    p = (c[starts + n] - c[starts]) / n
    return (starts + n / 2) / sr, 10 * np.log10(np.maximum(p, 1e-14))


def features(path, t_gun, t_set_on=None, t_set_off=None, pre=4.0, post=0.8):
    """Features of the gun near absolute file time t_gun (s). Window [t_gun - pre, t_gun + post]."""
    t0 = t_gun - pre
    x = load(path, t0, pre + post)
    if len(x) < int((pre + post - 0.05) * SR):
        return None
    g = pre
    # onset: 2-12 kHz 1 ms envelope; walk back from the first floor + 50%-of-rise crossing to floor + 6 dB
    y = bp(x, 2000, 12000)
    t, e = env(y, 0.001)
    nz = (t > g - 0.30) & (t < g - 0.03)
    fl = np.median(e[nz])
    sd = np.clip(1.4826 * np.median(np.abs(e[nz] - fl)), 0.5, 4)
    zone = np.where((t > g - 0.03) & (t < g + 0.06))[0]
    pk = zone[np.argmax(e[zone])]
    rise_db = float(e[pk] - fl)
    hi_ = np.where((t >= g - 0.03) & (t <= t[pk]) & (e >= fl + 0.5 * rise_db))[0]
    k = hi_[0] if len(hi_) else pk
    j = k
    while j > 0 and e[j] > fl + max(6, 2.5 * sd) and t[j] > g - 0.06:
        j -= 1
    on = float(t[j])
    # broadband 300-12000 Hz, 1 ms envelope
    yb = bp(x, 300, 12000)
    tb, eb = env(yb, 0.001)
    nzb = (tb > on - 0.30) & (tb < on - 0.02)
    flb = np.median(eb[nzb])
    w = (tb >= on) & (tb <= on + 0.6)
    tw, ew = tb[w], eb[w]
    n80 = int(0.08 / 0.0005)
    ipk = int(np.argmax(ew[:n80]))
    pk_db = ew[ipk]
    amp = 10 ** ((ew - flb) / 20)
    a_pk = 10 ** ((pk_db - flb) / 20)
    i10 = int(np.argmax(amp[: ipk + 1] >= 0.1 * a_pk))
    i90 = int(np.argmax(amp[: ipk + 1] >= 0.9 * a_pk))
    rise_ms = (tw[i90] - tw[i10]) * 1000

    def dur_below(d):
        after = np.where(ew[ipk:] < pk_db - d)[0]
        return float((tw[ipk + after[0]] - on) * 1000) if len(after) else np.nan

    dur10, dur20 = dur_below(10), dur_below(20)
    seg = ew[: int(0.10 / 0.0005)]
    pks, _ = signal.find_peaks(seg, height=pk_db - 6, distance=int(0.004 / 0.0005), prominence=3)
    two_step_ms = float((tw[pks[1]] - tw[pks[0]]) * 1000) if len(pks) >= 2 else 0.0
    # spectrum: first 40 ms after onset minus 300 ms of pre-gun noise
    i_on = int(on * SR)
    nseg = int(0.040 * SR)
    sig = x[i_on: i_on + nseg]
    noi = x[int((on - 0.34) * SR): int((on - 0.04) * SR)]
    f, Ps = signal.welch(sig, SR, nperseg=nseg, window="hann")
    _, Pn = signal.welch(noi, SR, nperseg=nseg, window="hann")
    ex = np.maximum(Ps - Pn, 1e-20)
    band = (f >= 200) & (f <= 16000)
    fb, eb2 = f[band], ex[band]
    peak_hz = float(fb[np.argmax(eb2)])
    centroid = float(np.sum(fb * eb2) / np.sum(eb2))
    b2 = (fb >= 300) & (fb <= 12000)
    flat = float(np.exp(np.mean(np.log(eb2[b2]))) / np.mean(eb2[b2]))
    hf_share = float(eb2[fb >= 4000].sum() / eb2.sum())
    # 80 ms zero-padded spectrum: prominent tonal peaks
    n2 = int(0.080 * SR)
    sig2 = x[i_on: i_on + n2] * np.hanning(n2)
    F = np.abs(np.fft.rfft(sig2, n=16384)) ** 2
    ff = np.fft.rfftfreq(16384, 1 / SR)
    m = (ff >= 200) & (ff <= 12000)
    LdB = 10 * np.log10(F[m] + 1e-20)
    pk_idx, _ = signal.find_peaks(LdB, prominence=10, distance=20)
    tonal = sorted([(float(LdB[i]), float(ff[m][i])) for i in pk_idx], reverse=True)[:3]
    out = dict(onset_s=round(t0 + on, 4), onset_shift_ms=round((on - g) * 1000, 1), hf_rise_db=round(rise_db, 1),
               rise_ms=round(rise_ms, 2), t_peak_ms=round((tw[ipk] - on) * 1000, 1), dur10_ms=round(dur10, 1),
               dur20_ms=round(dur20, 1), two_step_ms=round(two_step_ms, 1), peak_hz=round(peak_hz),
               centroid_hz=round(centroid), flatness=round(flat, 3), hf_share=round(hf_share, 3),
               tonal_f1=round(tonal[0][1]) if tonal else None, tonal_f2=round(tonal[1][1]) if len(tonal) > 1 else None,
               n_tonal=len(pk_idx))
    # gun vs 'Set' level, same band (300-8000 Hz), 20 ms RMS peaks, within one recording
    if t_set_on is not None and np.isfinite(t_set_on) and t_set_on - t0 > 0.05:
        ys = bp(x, 300, 8000)
        ts, es = env(ys, 0.020, hop=0.002)
        so = t_set_on - t0
        se = (t_set_off - t0) if (t_set_off is not None and np.isfinite(t_set_off)) else so + 0.6
        ms = (ts >= so) & (ts <= min(se + 0.05, g - 0.1))
        mg = (ts >= on) & (ts <= on + 0.10)
        nzs = (ts > on - 0.5) & (ts < on - 0.05)
        if ms.sum() > 3 and mg.sum() > 3 and nzs.sum() > 3:
            out["gun_minus_set_db"] = round(float(es[mg].max() - es[ms].max()), 1)
            out["set_snr_db"] = round(float(es[ms].max() - np.median(es[nzs])), 1)
            out["gun_snr_db"] = round(float(es[mg].max() - np.median(es[nzs])), 1)
    return out
