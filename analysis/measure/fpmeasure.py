"""Foreperiod measurement from broadcast audio: "Set" command onset/offset -> starting gun.

Pipeline (full description and validation in README.md next to this file):
  1. Coarse scan. Six band-energy envelopes (150 Hz - 11 kHz) at 5 ms frames. A gun candidate is a frame
     where >= 3 bands, including at least one low (< 1.6 kHz) and one high (> 3.2 kHz) band, rise by >= 8 dB
     within 60 ms relative to the maximum of the preceding 300 ms.
  2. Context features and score. For each candidate: the broadband level jump, its spectral tilt (loudspeaker
     guns rise far more above 1.6 kHz than below 400 Hz, unlike voice onsets), the quietness of the 0.5 s hold
     before it, sustained high-frequency energy after it, race-period loudness (crowd/commentary during the
     following ~9 s versus the preceding 12 s) and a speech burst (the "Set" command) 0.9-4.2 s earlier.
     Scores are compared within a recording (absolute levels depend on the broadcast mix).
  3. Refinement at sample resolution.
       gun onset  = median of three estimators: threshold-backtrack onsets of 2 ms RMS envelopes in the
                    2-10 kHz and 0.3-10 kHz bands, and an AIC change-point on the 2-10 kHz waveform.
       set onset  = median of five estimators: threshold-backtrack onsets (two thresholds) of 5 ms envelopes in
                    the 3-10 kHz band (the /s/ frication) and the 0.3-10 kHz band, plus an AIC change-point on
                    the 3-10 kHz waveform. Half their range is an uncertainty component.
       set offset = start of the first >= 120 ms run in which the 0.3-10 kHz envelope stays below floor + 6 dB.
  4. Foreperiod = gun onset - set onset (primary) and gun onset - set offset (variant), with uncertainty and
     QC flags. Optional faster-whisper word timestamps on a short clip choose the "Set" burst when several
     speech bursts precede the gun.

All times are seconds from the start of the audio file. Only audio is used.
"""
from __future__ import annotations

import os
import re
import subprocess

import numpy as np
from scipy import signal

SR = 24000  # analysis sample rate (Hz)
FRAME = 0.005  # coarse frame hop (s)
BANDS = [(150, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, 11000)]
SPEECH_BANDS = [1, 2, 3]  # 400-3200 Hz
HF_BANDS = [4, 5]  # 3.2-11 kHz

PARAMS = dict(
    cand_band_rise_db=8.0, cand_min_votes=3, cand_min_mean_rise_db=6.0, cand_pre=(0.30, 0.01), cand_post=0.06,
    cand_nms_s=0.8,
    set_search=(4.6, 0.3),  # speech bursts considered in [gun-4.6, gun-0.3]
    fp_plausible=(0.9, 4.2),  # set-gap range used by the start score
    burst_db=8.0, burst_min_dur=0.10, burst_merge_gap=0.04, set_max_dur=0.8, set_join_gap=0.15,
    set_onset_db=(6.0, 10.0), set_floor_win=(1.5, 0.08), set_floor_pct=20,
    offset_drop_db=15.0, offset_gap=0.05,
    gun_floor_win=(0.30, 0.03),
    qc_fp_range=(0.9, 3.8),
)

SET_WORDS = re.compile(r"^(set|sets|sit|sat|said|sept|cet|seth|step|sed|zet|third|sex|seat|sent|cent|sell|says)$")


def fr(v, nd=4):
    """Round for stable serialisation (NaN -> None)."""
    if v is None:
        return None
    try:
        if not np.isfinite(v):
            return None
    except TypeError:
        return v
    return round(float(v), nd)


# ----------------------------------------------------------------------------------------------
# I/O
# ----------------------------------------------------------------------------------------------
def load_audio(path: str, sr: int = SR, start: float | None = None, dur: float | None = None) -> np.ndarray:
    """Decode any audio/video file to mono float32 at `sr` using ffmpeg."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"]
    if start is not None:
        cmd += ["-ss", f"{max(start, 0):.4f}"]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def db(p, floor=1e-12):
    return 10.0 * np.log10(np.maximum(p, floor))


# ----------------------------------------------------------------------------------------------
# Coarse features
# ----------------------------------------------------------------------------------------------
_SOS: dict = {}


def band_sos(lo, hi, sr, order=4):
    key = (lo, hi, sr, order)
    if key not in _SOS:
        nyq = sr / 2
        if hi is None or hi >= nyq * 0.999:
            _SOS[key] = signal.butter(order, lo / nyq, btype="high", output="sos")
        else:
            _SOS[key] = signal.butter(order, [lo / nyq, hi / nyq], btype="band", output="sos")
    return _SOS[key]


def band_env_db(x: np.ndarray, sr: int = SR, frame: float = FRAME, bands=BANDS, chunk_s: float = 120.0):
    """Per-band mean power (dB) in non-overlapping frames of `frame` s. Returns (T, B) float32."""
    hop = int(round(frame * sr))
    n = len(x) // hop
    out = np.empty((n, len(bands)), dtype=np.float32)
    chunk = int(chunk_s * sr) // hop * hop
    for b, (lo, hi) in enumerate(bands):
        sos = band_sos(lo, hi, sr)
        zi = np.zeros((sos.shape[0], 2))
        pos, fi = 0, 0
        while pos < n * hop:
            seg = x[pos: min(pos + chunk, n * hop)].astype(np.float64)
            y, zi = signal.sosfilt(sos, seg, zi=zi)
            p = (y.reshape(-1, hop) ** 2).mean(axis=1)
            out[fi: fi + len(p), b] = db(p)
            fi += len(p)
            pos += chunk
    return out


def _pow_mean_db(Ed):
    return db((10 ** (np.asarray(Ed, dtype=np.float64) / 10.0)).mean(axis=1))


def _smooth(v, w):
    return v if w <= 1 else np.convolve(v, np.ones(w) / w, mode="same")


def _runs(mask):
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(int))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def _seg(E, t0, t1, frame=FRAME):
    i0, i1 = max(0, int(round(t0 / frame))), min(len(E), int(round(t1 / frame)))
    return E[i0:max(i1, i0)]


def gun_candidates(E: np.ndarray, p=PARAMS, frame=FRAME):
    """Sharp transients with energy rising in both a low (< 1.6 kHz) and a high (> 3.2 kHz) band."""
    from numpy.lib.stride_tricks import sliding_window_view

    T, B = E.shape
    w_pre = int(round((p["cand_pre"][0] - p["cand_pre"][1]) / frame))
    lag = int(round(p["cand_pre"][1] / frame))
    w_post = max(1, int(round(p["cand_post"] / frame)))
    Epad = np.concatenate([np.full((w_pre + lag, B), -200.0, dtype=E.dtype), E], axis=0)
    ref = sliding_window_view(Epad, w_pre, axis=0).max(axis=-1)[:T]
    Ep = np.concatenate([E, np.full((w_post - 1, B), -200.0, dtype=E.dtype)], axis=0)
    post = sliding_window_view(Ep, w_post, axis=0).max(axis=-1)
    rise = post - ref
    vote = rise >= p["cand_band_rise_db"]
    votes = vote.sum(axis=1)
    mrise = rise.mean(axis=1)
    ok = (votes >= p["cand_min_votes"]) & vote[:, [0, 1, 2]].any(axis=1) & vote[:, [4, 5]].any(axis=1) & \
         (mrise >= p["cand_min_mean_rise_db"])
    idx = np.where(ok)[0]
    r = int(round(p["cand_nms_s"] / frame))
    taken = np.zeros(T, dtype=bool)
    cands = []
    for i in idx[np.argsort(-mrise[idx], kind="stable")]:
        if taken[max(0, i - r): i + r + 1].any():
            continue
        taken[i] = True
        cands.append(dict(t=float(i * frame), mean_rise=float(mrise[i]), votes=int(votes[i]),
                          band_rise=[float(v) for v in rise[i]]))
    cands.sort(key=lambda c: c["t"])
    return cands


def speech_bursts(E: np.ndarray, t0: float, t1: float, floor_db: float, p=PARAMS, frame=FRAME):
    """Segments in [t0, t1] where the smoothed 400-3200 Hz level exceeds floor + burst_db."""
    i0, i1 = max(0, int(t0 / frame)), min(len(E), int(t1 / frame))
    if i1 <= i0 + 2:
        return []
    S = _pow_mean_db(E[i0:i1, SPEECH_BANDS])
    H = _pow_mean_db(E[i0:i1, HF_BANDS])
    on = _smooth(S, 5) > floor_db + p["burst_db"]
    merged = []
    for a, b in _runs(on):
        if merged and (a - merged[-1][1]) * frame <= p["burst_merge_gap"]:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    out = []
    for a, b in merged:
        if (b - a) * frame < p["burst_min_dur"]:
            continue
        pre0 = max(0, a - int(0.20 / frame))
        hf_floor = float(np.percentile(H, 10))
        out.append(dict(t_start=(i0 + a) * frame, t_end=(i0 + b) * frame, dur=(b - a) * frame,
                        snr=float(S[a:b].max() - floor_db), hf_lead=float(H[a:a + 6].mean() - S[a:a + 6].mean()),
                        s_pre=float(H[pre0:a + 6].max() - hf_floor)))
    return out


def candidate_features(E: np.ndarray, cand: dict, p=PARAMS):
    """Context features of a gun candidate."""
    t = cand["t"]
    S_pre = _seg(E, t - 10.0, t - 0.05)
    hold = _seg(E, t - 0.5, t - 0.05)
    after = _seg(E, t + 0.005, t + 0.10)
    post = _seg(E, t + 0.3, t + 3.0)
    if len(S_pre) < 40 or len(hold) < 5 or len(after) < 5 or len(post) < 20:
        return None
    floor = float(np.percentile(_pow_mean_db(S_pre[:, SPEECH_BANDS]), 10))
    jump_b = np.median(after, axis=0) - np.median(hold, axis=0)
    br = cand["band_rise"]
    f = dict(floor=floor,
             hold_excess=float(np.percentile(_pow_mean_db(hold[:, SPEECH_BANDS]), 90) - floor),
             gun_jump=float(np.mean(jump_b)), gun_jump_3rd=float(np.sort(jump_b)[-3]),
             tilt=float(np.mean(br[3:6]) - br[0]),
             post_excess=float(np.median(_pow_mean_db(post[:, SPEECH_BANDS])) - floor))
    race = _seg(E, t + 1.0, t + 9.0)
    pre = _seg(E, t - 12.0, t - 0.05)
    f["race_loud"] = float(np.median(_pow_mean_db(race)) - np.median(_pow_mean_db(pre))) if len(race) > 20 else 0.0
    sus = _seg(E, t + 0.02, t + 0.25)
    f["hf_sustain"] = float(np.percentile(_pow_mean_db(sus[:, HF_BANDS]), 20) -
                            np.median(_pow_mean_db(hold[:, HF_BANDS])))
    bursts = [b for b in speech_bursts(E, t - p["set_search"][0], t - p["set_search"][1], floor, p)
              if b["t_end"] < t - p["set_search"][1]]
    f["n_bursts"] = len(bursts)
    if bursts:
        b = bursts[-1]
        f.update(set_gap=t - b["t_start"], set_snr=b["snr"], set_dur=b["dur"])
    else:
        f.update(set_gap=np.nan, set_snr=0.0, set_dur=np.nan)
    f["bursts"] = bursts
    return f


def start_score(f: dict, p=PARAMS) -> float:
    """Heuristic start score; compared within a recording. Weights are documented in README.md."""
    if f is None:
        return -99.0
    s = 0.6 * min(f["gun_jump"], 35.0) + 0.3 * float(np.clip(f["tilt"], -10, 40))
    s += 1.0 * float(np.clip(f["race_loud"], -10, 25)) + 0.2 * float(np.clip(f["hf_sustain"], 0, 30))
    s -= 1.5 * max(f["hold_excess"] - 5.0, 0.0)
    s += 0.3 * min(f["set_snr"], 30.0)
    lo, hi = p["fp_plausible"]
    if f["n_bursts"] == 0:
        s -= 15.0
    elif not (lo <= f["set_gap"] <= hi):
        s -= 10.0
    return float(s)


# ----------------------------------------------------------------------------------------------
# Fine refinement
# ----------------------------------------------------------------------------------------------
def env_db(y, sr, win_s, hop_s):
    """RMS envelope in dB; returns (window-centre times relative to y[0], env_db, window length s)."""
    w = max(1, int(round(win_s * sr)))
    h = max(1, int(round(hop_s * sr)))
    c = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    starts = np.arange(0, len(y) - w + 1, h)
    pw = (c[starts + w] - c[starts]) / w
    return (starts + w / 2) / sr, db(pw), w / sr


def robust_floor(e):
    """Noise floor and noise SD of a dB envelope that may contain intermittent speech:
    floor = 10th percentile; SD from the lower quantiles, (P25 - P5) / 0.97, capped to [0.5, 4] dB."""
    p5, p10, p25 = np.percentile(e, [5, 10, 25])
    return float(p10), float(np.clip((p25 - p5) / 0.97, 0.5, 4.0))


def aic_pick(y: np.ndarray):
    """AIC change-point picker (Maeda 1985). Returns sample index of the variance change, or None."""
    n = len(y)
    if n < 40:
        return None
    y = y.astype(np.float64) - np.mean(y)
    c2 = np.cumsum(y ** 2)
    c1 = np.cumsum(y)
    k = np.arange(1, n)
    v1 = c2[k - 1] / k - (c1[k - 1] / k) ** 2
    v2 = (c2[-1] - c2[k - 1]) / (n - k) - ((c1[-1] - c1[k - 1]) / (n - k)) ** 2
    aic = k * np.log(np.maximum(v1, 1e-20)) + (n - k - 1) * np.log(np.maximum(v2, 1e-20))
    aic[:10] = np.inf
    aic[-10:] = np.inf
    return int(np.argmin(aic)) + 1


def _backtrack_onset(t, e, floor, nsd, thr_db, t_lo, t_peak, min_above=0.015, min_below=0.02, hop=0.001):
    """Onset of the energy rise that contains t_peak.

    Walk backward from the peak to the most recent point where the envelope rose through floor + thr (sustained
    for min_above), then continue backward until the envelope has stayed below floor + max(3 dB, 2 sd) for
    min_below (a quiet gap). Earlier speech separated by such a gap is never reached. Returns the window-centre
    time of the last quiet sample, or None."""
    thr = floor + max(thr_db, 3.0 * nsd)
    lo_thr = floor + max(3.0, 2.0 * nsd)
    kp = int(np.searchsorted(t, t_peak))
    kp = min(max(kp, 0), len(e) - 1)
    if e[kp] < thr:
        return None
    n_below = max(1, int(round(min_below / hop)))
    j = kp
    run = 0
    while j > 0 and t[j] > t_lo:
        j -= 1
        if e[j] < lo_thr:
            run += 1
            if run >= n_below:
                return float(t[j + run - 1])  # last quiet window centre (caller adds w/2)
        else:
            run = 0
    return None


def refine_gun(x: np.ndarray, sr: int, t_c: float, p=PARAMS):
    """Onset of the gun transient near coarse time t_c.

    Primary: AIC change point on the 2-10 kHz waveform between (steep crossing - 30 ms) and the envelope peak.
    Check: threshold estimate - from the first crossing of floor + 50% of the rise, walk back to the first
    sample below floor + max(6 dB, 2.5 sd) (no sustain requirement: guns rise within a few ms, and a sustain
    rule walks back into fluctuating commentary). gun_spread = |AIC - threshold| / 2.
    """
    a = max(0, int((t_c - 0.40) * sr))
    b = min(len(x), int((t_c + 0.15) * sr))
    seg = x[a:b].astype(np.float64)
    t0 = a / sr
    ests, info = {}, {}
    for name, (lo, hi) in (("hf", (2000, 10000)), ("bb", (300, 10000))):
        y = signal.sosfiltfilt(band_sos(lo, hi, sr), seg)
        t, e, w = env_db(y, sr, 0.002, 0.0005)
        t = t + t0
        nz = (t >= t_c - p["gun_floor_win"][0]) & (t <= t_c - p["gun_floor_win"][1])
        if nz.sum() < 20:
            continue
        floor = float(np.median(e[nz]))
        nsd = float(np.clip(1.4826 * np.median(np.abs(e[nz] - floor)), 0.5, 4.0))
        zone = np.where((t >= t_c - 0.03) & (t <= t_c + 0.09))[0]
        if len(zone) == 0:
            continue
        pk = zone[np.argmax(e[zone])]
        rise = float(e[pk] - floor)
        info[f"{name}_floor"], info[f"{name}_rise"], info[f"{name}_nsd"] = floor, rise, nsd
        if rise < 6:
            continue
        cross = zone[(zone <= pk) & (e[zone] >= floor + 0.5 * rise)]
        if len(cross) == 0:
            continue
        k = cross[0]
        lo_thr = floor + max(6.0, 2.5 * nsd)
        j = k
        while j > 0 and e[j] > lo_thr and t[j] > t_c - 0.08:
            j -= 1
        ests[f"{name}_thr"] = float(t[j]) + w / 2
        if name == "hf":
            i0 = max(0, int((t[k] - 0.03 - t0) * sr))
            i1 = int((t[pk] - t0) * sr)
            if i1 - i0 > 100:
                kk = aic_pick(y[i0:i1])
                if kk is not None:
                    ests["hf_aic"] = t0 + (i0 + kk) / sr
    if not ests:
        return None
    if "hf_aic" in ests:
        t_gun = ests["hf_aic"]
        ref = ests.get("hf_thr", ests.get("bb_thr", t_gun))
        spread = abs(t_gun - ref) / 2
    else:
        v = np.array(list(ests.values()))
        t_gun = float(np.median(v))
        spread = float((v.max() - v.min()) / 2) if len(v) > 1 else np.nan
    return dict(t_gun=float(t_gun), gun_spread=float(spread), gun_rise_db=info.get("hf_rise", np.nan),
                gun_estimators=ests, **info)


def refine_set(x: np.ndarray, sr: int, t_bs: float, t_be: float, t_gun: float, p=PARAMS):
    """Onset/offset of the "Set" command given a coarse burst [t_bs, t_be] (s)."""
    f0, f1 = p["set_floor_win"]
    a = max(0, int((t_bs - max(f0, 0.5) - 0.05) * sr))
    b = min(len(x), int(min(t_be + 0.6, t_gun - 0.02) * sr))
    if b - a < int(0.3 * sr):
        return None
    seg = x[a:b].astype(np.float64)
    t0 = a / sr
    ests, info = {}, {}
    env = {}
    for name, (lo, hi) in (("hf", (3000, 10000)), ("bb", (300, 10000))):
        y = signal.sosfiltfilt(band_sos(lo, hi, sr), seg)
        t, e, w = env_db(y, sr, 0.005, 0.001)
        t = t + t0
        env[name] = (t, e, w, y)
        nz = (t >= t_bs - f0) & (t <= t_bs - f1)
        if nz.sum() < 50:
            nz = (t >= t_bs - 0.5) & (t <= t_bs - 0.05)
        if nz.sum() < 20:
            continue
        floor, nsd = robust_floor(e[nz])
        loc = (t >= t_bs - 0.45) & (t <= t_bs - 0.20)
        if loc.sum() > 50:  # local background just before the word (non-stationary crowd noise)
            q25, q50, q75 = np.percentile(e[loc], [25, 50, 75])
            floor = max(floor, float(q50) - 1.0)
            nsd = max(nsd, float(np.clip((q75 - q25) / 1.35, 0.5, 4.0)))
        win = (t >= t_bs - 0.35) & (t <= min(t_be + 0.05, t_gun - 0.1))
        if not win.any():
            continue
        wi = np.where(win)[0]
        pk = wi[np.argmax(e[wi])]
        info[f"{name}_floor"], info[f"{name}_snr"], info[f"{name}_nsd"] = floor, float(e[pk] - floor), nsd
        for thr in p["set_onset_db"]:
            on = _backtrack_onset(t, e, floor, nsd, thr, t_bs - 0.35, t[pk])
            if on is not None:
                ests[f"{name}_thr{int(thr)}"] = on + w / 2
    if not ests:
        return None
    # AIC on the 3-10 kHz waveform between (earliest estimate - 0.15 s) and the HF peak
    if "hf" in env:
        t, e, w, y = env["hf"]
        on_min = min(ests.values())
        win = (t >= t_bs - 0.35) & (t <= min(t_be + 0.05, t_gun - 0.1))
        wi = np.where(win)[0]
        pk_t = t[wi[np.argmax(e[wi])]] if len(wi) else None
        if pk_t is not None:
            i0 = max(0, int((on_min - 0.15 - t0) * sr))
            i1 = int((pk_t - t0) * sr)
            if i1 - i0 > 200:
                k = aic_pick(y[i0:i1])
                if k is not None:
                    ests["hf_aic"] = t0 + (i0 + k) / sr
    thr_v = np.array([v for k, v in ests.items() if "_thr" in k])
    v = np.array(list(ests.values()))
    t_on = float(np.median(thr_v)) if len(thr_v) else float(np.median(v))
    spread = float((v.max() - v.min()) / 2) if len(v) > 1 else np.nan
    # offset = end of voicing: 300-3400 Hz envelope (10 ms window); after the word's peak (searched within
    # [onset, onset+0.8 s]), the first point from which the envelope stays >= offset_drop_db below that peak for
    # offset_gap (fallback 10 dB). Chosen on the manual dev annotations; stadium reverberation makes offsets
    # intrinsically less precise than onsets (see README).
    t_off = np.nan
    ysp = signal.sosfiltfilt(band_sos(300, 3400, sr), seg)
    t2, e2, w2 = env_db(ysp, sr, 0.010, 0.001)
    t2 = t2 + t0
    wpk = np.where((t2 >= t_on) & (t2 <= min(t_on + 0.8, t_gun - 0.1)))[0]
    if len(wpk):
        kp = wpk[np.argmax(e2[wpk])]
        gap = int(round(p["offset_gap"] / 0.001))
        for drop in (p["offset_drop_db"], 10.0):
            below = e2 < e2[kp] - drop
            for k in range(kp, len(below) - gap):
                if t2[k] >= t_gun - 0.05:
                    break
                if below[k:k + gap].all():
                    t_off = float(t2[k] - w2 / 2)
                    break
            if np.isfinite(t_off):
                break
    return dict(t_on=t_on, t_off=t_off, onset_spread=spread, set_estimators=ests,
                set_snr=max(info.get("hf_snr", -99.0), info.get("bb_snr", -99.0)), **info)


# ----------------------------------------------------------------------------------------------
# Whisper (optional)
# ----------------------------------------------------------------------------------------------
_WHISPER: dict = {}


def get_whisper(model_name="base.en", threads=8):
    if model_name not in _WHISPER:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models are cached; avoid network checks on a saturated link
        from faster_whisper import WhisperModel

        _WHISPER[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads)
    return _WHISPER[model_name]


def whisper_words(x16: np.ndarray, model_name="base.en", prompt="On your marks. Set.", threads=8):
    m = get_whisper(model_name, threads)
    segs, _ = m.transcribe(x16, language="en", word_timestamps=True, vad_filter=False, beam_size=5,
                           condition_on_previous_text=False, initial_prompt=prompt, temperature=0.0)
    return [(w.word.strip(), float(w.start), float(w.end), float(w.probability)) for s in segs for w in (s.words or [])]


def clean_word(w: str) -> str:
    return re.sub(r"[^a-z]", "", w.lower())


# ----------------------------------------------------------------------------------------------
# Detection
# ----------------------------------------------------------------------------------------------
def detect_candidates(x: np.ndarray, sr: int = SR, p=PARAMS, E=None):
    """All gun candidates with context features and start scores, sorted by time."""
    if E is None:
        E = band_env_db(x, sr)
    out = []
    for c in gun_candidates(E, p):
        f = candidate_features(E, c, p)
        if f is None:
            continue
        c.update(f)
        c["score"] = start_score(f, p)
        out.append(c)
    return out, E


def choose_set_burst(bursts, words, t_gun):
    """Return (burst, how). Prefer the burst matching a whisper set-word; else the last burst."""
    if not bursts:
        return None, "none"
    strong = [b for b in bursts if b["snr"] >= 12.0 and b["dur"] >= 0.12]
    if strong:
        bursts = strong
    if words:
        sw = [w for w in words if SET_WORDS.match(clean_word(w[0])) and t_gun - 4.8 < w[1] < t_gun - 0.3]
        best = None
        for w in sw:
            for b in bursts:
                if min(w[2], b["t_end"]) - max(w[1], b["t_start"] - 0.4) > 0:
                    d = abs(w[2] - b["t_end"])
                    if best is None or d < best[0]:
                        best = (d, b)
        if best is not None:
            return best[1], "whisper"
    s_like = [b for b in bursts if b.get("s_pre", 0.0) >= 15.0]
    if s_like and s_like[-1] is not bursts[-1]:
        # the command starts with /s/: prefer the last burst preceded by fricative energy, unless the last
        # burst is itself strong and s-like-free commentary is unlikely to follow a real "Set" by > 1.5 s
        cand_s = s_like[-1]
        if bursts[-1]["t_start"] - cand_s["t_end"] < 1.5:
            return cand_s, "s_onset_burst"
    last = bursts[-1]
    if len(bursts) >= 2:
        prev = bursts[-2]
        # a weak sound in the hold (e.g. crowd, PA echo) right after a much louder command: take the command
        if last["snr"] < 15.0 and prev["snr"] >= last["snr"] + 8.0 and last["t_start"] - prev["t_end"] <= 1.2:
            return prev, "prev_burst_louder"
    return last, "last_burst"


def extend_set_burst(burst, all_bursts, p=PARAMS):
    """A "Set" word can be split into two bursts (/s/+vowel, or a released /t/). Join the preceding burst when
    the gap is < set_join_gap and the joined span is still one word (<= set_max_dur)."""
    b = dict(burst)
    for prev in sorted([x for x in all_bursts if x["t_end"] <= b["t_start"]], key=lambda x: -x["t_end"]):
        if b["t_start"] - prev["t_end"] < p["set_join_gap"] and b["t_end"] - prev["t_start"] <= p["set_max_dur"]:
            b = dict(b, t_start=prev["t_start"], dur=b["t_end"] - prev["t_start"], snr=max(b["snr"], prev["snr"]))
        else:
            break
    return b


def measure(x: np.ndarray, sr: int, cand: dict, words=None, p=PARAMS):
    """Refine one start candidate into a measurement dict (or None)."""
    g = refine_gun(x, sr, cand["t"], p)
    if g is None:
        return dict(fail="gun_refine_failed", t_cand=cand["t"])
    burst, how = choose_set_burst(cand.get("bursts", []), words, g["t_gun"])
    if burst is None:
        return dict(fail="no_speech_burst_before_gun", t_cand=cand["t"], t_gun=g["t_gun"])
    burst = extend_set_burst(burst, cand.get("bursts", []), p)
    s = refine_set(x, sr, burst["t_start"], burst["t_end"], g["t_gun"], p)
    if s is None and len(cand.get("bursts", [])) > 1:  # fall back to the previous burst
        prev = [b for b in cand["bursts"] if b["t_end"] <= burst["t_start"]]
        if prev:
            burst, how = prev[-1], how + "_fallback_prev"
            s = refine_set(x, sr, burst["t_start"], burst["t_end"], g["t_gun"], p)
    if s is None:
        return dict(fail="set_refine_failed", t_cand=cand["t"], t_gun=g["t_gun"], burst=burst)
    fp_on = g["t_gun"] - s["t_on"]
    fp_off = g["t_gun"] - s["t_off"] if np.isfinite(s["t_off"]) else np.nan
    qc = []
    if words is None:
        qc.append("whisper_not_run")
    elif how != "whisper":
        qc.append("no_whisper_set")
    if s["set_snr"] < 12:
        qc.append("low_snr_set")
    if not np.isfinite(g.get("gun_rise_db", np.nan)) or g["gun_rise_db"] < 12:
        qc.append("low_snr_gun")
    lo, hi = p["qc_fp_range"]
    if not (lo <= fp_on <= hi):
        qc.append("fp_out_of_range")
    if np.isfinite(s["onset_spread"]) and s["onset_spread"] > 0.02:
        qc.append("set_estimators_disagree")
    if not np.isfinite(fp_off):
        qc.append("no_offset")
    if s.get("hf_snr", -99.0) < 10.0 and s.get("bb_snr", -99.0) >= 15.0:
        # no audible /s/ frication (low-pass mix or distant PA): the onset found is likely the vowel onset,
        # biased late by the /s/ duration (typically 0.1-0.2 s)
        qc.append("weak_s_onset")
    prior = [b for b in cand.get("bursts", []) if b["t_start"] < burst["t_start"] and b["t_end"] > burst["t_start"] - 0.35]
    if prior:
        qc.append("speech_before_set")
    after = [b for b in cand.get("bursts", []) if b["t_start"] > burst["t_end"] + 0.05]
    if after:
        qc.append("speech_in_hold")
    unc_on, unc_off = uncertainty(s, g)
    return dict(t_gun=g["t_gun"], t_set_on=s["t_on"], t_set_off=s["t_off"], fp_on=fp_on, fp_off=fp_off,
                unc_on=unc_on, unc_off=unc_off, set_snr=s["set_snr"], gun_rise_db=g.get("gun_rise_db"),
                set_spread=s["onset_spread"], gun_spread=g["gun_spread"], burst_choice=how,
                qc=qc, set_estimators=s["set_estimators"], gun_estimators=g["gun_estimators"],
                burst=dict(t_start=burst["t_start"], t_end=burst["t_end"]))


# Uncertainty model: absolute-error scale by set-SNR bin, calibrated on the synthetic benchmark
# (calibration_synthetic.json written by benchmark.py; defaults below are placeholders until then).
UNC = {"snr_edges": [-99, 12, 20, 30, 999], "set_on": [0.060, 0.030, 0.015, 0.010],
       "set_off": [0.080, 0.050, 0.035, 0.030], "gun": 0.003, "source": "default"}
_cal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration_synthetic.json")
if os.path.exists(_cal):
    import json as _json

    with open(_cal) as _f:
        UNC.update(_json.load(_f))


def uncertainty(s, g):
    k = int(np.clip(np.searchsorted(UNC["snr_edges"], s["set_snr"], side="right") - 1, 0, len(UNC["set_on"]) - 1))
    sp = s["onset_spread"] if np.isfinite(s["onset_spread"]) else 0.0
    gs = g["gun_spread"] if np.isfinite(g["gun_spread"]) else 0.0
    unc_on = float(np.sqrt(UNC["set_on"][k] ** 2 + sp ** 2 + UNC["gun"] ** 2 + gs ** 2))
    unc_off = float(np.sqrt(UNC["set_off"][k] ** 2 + UNC["gun"] ** 2 + gs ** 2))
    return unc_on, unc_off


def resample_to_16k(x: np.ndarray, sr: int):
    if sr == 24000:
        return signal.resample_poly(x.astype(np.float64), 2, 3).astype(np.float32)
    return signal.resample_poly(x.astype(np.float64), 16000, sr).astype(np.float32)


def clip_words(x, sr, t_gun, model="base.en", pre=7.0, post=0.4):
    t0 = max(0.0, t_gun - pre)
    seg = x[int(t0 * sr): int((t_gun + post) * sr)]
    return [(w, a + t0, b + t0, pr) for (w, a, b, pr) in whisper_words(resample_to_16k(seg, sr), model)]


def detect_single(x: np.ndarray, sr: int = SR, use_whisper=True, whisper_model="base.en", p=PARAMS):
    """Single-start recording (one race clip or one synthetic clip): measure the top-scoring candidate."""
    cands, E = detect_candidates(x, sr, p)
    if not cands:
        return None, cands
    best = max(cands, key=lambda c: c["score"])
    words = clip_words(x, sr, best["t"], whisper_model) if use_whisper else None
    m = measure(x, sr, best, words, p)
    if "fail" not in m:
        m["score"] = best["score"]
        m["words"] = words
    return m, cands
