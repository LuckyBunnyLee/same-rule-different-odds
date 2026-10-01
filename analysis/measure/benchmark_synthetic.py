"""SYNTHETIC benchmark: simulated start clips with known "Set" onset/offset and gun times.

Everything produced here is SIMULATED audio. Real components: broadcast background noise excerpts (listed in
benchmark_noise_manifest.csv) and Windows SAPI text-to-speech voices; the starter voice, the gun, the stadium
reverberation, the crowd surge and the codec round trip are synthetic.

Usage:
  python analysis/measure/benchmark_synthetic.py --tts-dir analysis/measure/work/tts \
      --noise-manifest analysis/measure/benchmark_noise_manifest.csv --audio-dir data/video/audio \
      --snrs 20 10 5 0 -5 --noise-types hush commentary race pink --n-per-cell 20 --seed 20260929 \
      --whisper base.en --jobs 4 --workdir analysis/measure/work/bench \
      --out analysis/measure/results/benchmark_synthetic_trials.csv

Clip recipe (12 s, 48 kHz): background noise (a real broadcast window or seeded pink noise) at -30 dBFS RMS;
optional "On your marks" 1-2 s in; "Set" onset at U(4.0, 6.0) s; foreperiod U(1.2, 2.7) s; gun; a crowd surge
+8..15 dB starting 0.1 s after the gun (real starts are followed by crowd noise). Speech: TTS resampled by
0.92/1.00/1.08 (pitch and tempo), band-passed 200-7000 Hz (loudspeaker), reverberated (exponential-noise impulse
response, RT60 U(0.3, 1.2) s, direct-to-reverberant ratio U(0, 12) dB). "Set" SNR = mean power of the direct
word over its active interval vs noise power over the same interval. Gun: noise burst, 0.5 ms attack,
exponential decay tau U(15, 60) ms, band-passed (low cut U(200, 800) Hz, high cut 9 kHz), same reverb, level
U(15, 35) dB over the noise. Codec round trip: Opus 128 kb/s (70%) or AAC 128 kb/s (30%).
Ground truth: "Set" onset/offset = first/last sample where the dry processed word's 2 ms RMS envelope is within
40 dB of its peak (also the -20 dB end, off20); gun = first sample of the burst.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fpmeasure as fm  # noqa: E402

FS = 48000
CLIP = 12.0


def load_tts(path):
    x, sr = sf.read(path, dtype="float64")
    if x.ndim > 1:
        x = x.mean(axis=1)
    g = np.gcd(FS, sr)
    return signal.resample_poly(x, FS // g, sr // g)


def active_bounds(x, rel_db=40.0):
    w = int(0.002 * FS)
    p = np.convolve(x ** 2, np.ones(w) / w, mode="same")
    e = 10 * np.log10(p + 1e-20)
    idx = np.where(e > e.max() - rel_db)[0]
    return int(idx[0]), int(idx[-1])


def reverb_ir(rng, rt60, drr_db):
    n = int(FS * min(1.5 * rt60, 2.0))
    t = np.arange(n) / FS
    tail = rng.standard_normal(n) * np.exp(-6.908 * t / rt60)  # -60 dB at rt60
    pre = int(FS * rng.uniform(0.010, 0.030))
    tail[:pre] = 0.0
    tail /= np.sqrt(np.sum(tail ** 2)) + 1e-12
    ir = tail * 10 ** (-drr_db / 20.0)
    ir[0] += 1.0  # direct path
    return ir


def pink(rng, n):
    w = rng.standard_normal(n)
    f = np.fft.rfftfreq(n, 1 / FS)
    s = np.fft.rfft(w)
    s[1:] /= np.sqrt(f[1:])
    s[0] = 0
    y = np.fft.irfft(s, n)
    return y / (np.std(y) + 1e-12)


def gun_sound(rng):
    n = int(0.25 * FS)
    t = np.arange(n) / FS
    env = np.minimum(t / 0.0005, 1.0) * np.exp(-t / rng.uniform(0.015, 0.060))
    b = signal.butter(2, [rng.uniform(200, 800) / (FS / 2), 9000 / (FS / 2)], btype="band", output="sos")
    return signal.sosfilt(b, rng.standard_normal(n) * env)


def power(x):
    return float(np.mean(x ** 2)) + 1e-20


def make_trial(k, args, tts_files, noise_rows, noise_cache):
    rng = np.random.default_rng([args.seed, k])
    cell = k // args.n_per_cell
    snr = args.snrs[cell % len(args.snrs)]
    ntype = args.noise_types[(cell // len(args.snrs)) % len(args.noise_types)]
    set_files = [f for f in tts_files if "_set" in os.path.basename(f)]
    tts = set_files[rng.integers(len(set_files))]
    voice = os.path.basename(tts).split("_")[0]
    marks_files = [f for f in tts_files if os.path.basename(f).startswith(voice + "_marks")]
    rfac = [0.92, 1.0, 1.08][rng.integers(3)]
    rt60 = rng.uniform(0.3, 1.2)
    drr = rng.uniform(0.0, 12.0)
    fp = rng.uniform(1.2, 2.7)
    t_place = rng.uniform(4.0, 6.0)
    gnr = rng.uniform(15.0, 35.0)
    surge = rng.uniform(8.0, 15.0)
    codec = "opus" if rng.random() < 0.7 else "aac"
    n = int(CLIP * FS)
    # background
    if ntype == "pink":
        bg = pink(rng, n)
        src = "pink"
    elif ntype == "hold":
        # stitch real set-to-gun hold backgrounds (20 ms raised-cosine crossfades) up to the clip length
        rows = noise_rows[noise_rows.noise_type == "hold"].reset_index(drop=True)
        parts, total, used = [], 0, []
        xf = int(0.02 * FS)
        while total < n + xf:
            r = rows.iloc[rng.integers(len(rows))]
            key = (r.video_id, r.t0)
            if key not in noise_cache:
                noise_cache[key] = fm.load_audio(args.audio_files[r.video_id], sr=FS, start=r.t0,
                                                 dur=r.t1 - r.t0).astype(np.float64)
            s = noise_cache[key]
            s = s / (np.std(s) + 1e-12)
            parts.append(s)
            used.append(f"{r.video_id}@{r.t0}")
            total += len(s) - xf
        bg = parts[0]
        fade = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, xf))
        for s in parts[1:]:
            bg = np.concatenate([bg[:-xf], bg[-xf:] * (1 - fade) + s[:xf] * fade, s[xf:]])
        bg = bg[:n]
        src = "hold:" + "+".join(used[:3]) + ("+..." if len(used) > 3 else "")
    else:
        rows = noise_rows[noise_rows.noise_type == ntype].reset_index(drop=True)
        r = rows.iloc[rng.integers(len(rows))]
        key = (r.video_id, r.t0)
        if key not in noise_cache:
            noise_cache[key] = fm.load_audio(args.audio_files[r.video_id], sr=FS, start=r.t0, dur=CLIP).astype(np.float64)
        bg = noise_cache[key].copy()
        if len(bg) < n:
            bg = np.pad(bg, (0, n - len(bg)))
        bg = bg[:n] / (np.std(bg[:n]) + 1e-12)
        src = f"{r.video_id}@{r.t0}"
    bg *= 10 ** (-30 / 20)
    ir = reverb_ir(rng, rt60, drr)
    lsp = signal.butter(2, [200 / (FS / 2), 7000 / (FS / 2)], btype="band", output="sos")

    def speech(path):
        x = load_tts(path)
        up, down = {0.92: (25, 23), 1.0: (1, 1), 1.08: (25, 27)}[rfac]  # >1 = faster/higher
        x = signal.resample_poly(x, down, up) if rfac != 1.0 else x
        return signal.sosfilt(lsp, x)

    dry = speech(tts)
    on_i, off_i = active_bounds(dry, 40.0)
    _, off20_i = active_bounds(dry, 20.0)
    wet = signal.fftconvolve(dry, ir)[: len(dry) + int(0.8 * FS)]
    start = int(t_place * FS) - on_i
    seg = slice(start + on_i, start + off_i)
    scale = np.sqrt(power(bg[seg]) * 10 ** (snr / 10) / power(dry[on_i:off_i]))
    mix = bg.copy()
    mix[start: start + len(wet)] += scale * wet[: max(0, min(len(wet), n - start))]
    marks = None
    if marks_files and rng.random() < 0.5:
        mk = signal.fftconvolve(speech(marks_files[rng.integers(len(marks_files))]), ir)
        mstart = int(rng.uniform(1.0, 2.0) * FS)
        mix[mstart: mstart + len(mk)] += scale * mk[: n - mstart]
        marks = mstart / FS
    t_gun = t_place + fp
    gi = int(round(t_gun * FS))
    gsnd = signal.fftconvolve(gun_sound(rng), ir)
    gscale = np.sqrt(power(bg[gi: gi + int(0.05 * FS)]) * 10 ** (gnr / 10) / power(gsnd[: int(0.05 * FS)]))
    mix[gi: gi + len(gsnd)] += gscale * gsnd[: n - gi]
    # crowd surge after the gun
    cs = pink(rng, n) * np.std(bg) * 10 ** (surge / 20)
    ramp = np.clip((np.arange(n) / FS - (t_gun + 0.1)) / 0.3, 0, 1)
    mix += cs * ramp
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    truth = dict(trial=k, snr_db=snr, noise_type=ntype, noise_src=src, tts=os.path.basename(tts), voice=voice,
                 resample=rfac, rt60=round(rt60, 3), drr_db=round(drr, 2), gnr_db=round(gnr, 2), surge_db=round(surge, 2),
                 codec=codec, marks_at=None if marks is None else round(marks, 3),
                 true_set_on=round((start + on_i) / FS, 6), true_set_off=round((start + off_i) / FS, 6),
                 true_set_off20=round((start + off20_i) / FS, 6), true_gun=round(gi / FS, 6),
                 true_fp_on=round((gi - start - on_i) / FS, 6), true_fp_off=round((gi - start - off_i) / FS, 6))
    return mix.astype(np.float32), truth


def run_trial(k):
    a = _ARGS
    mix, truth = make_trial(k, a, _TTS, _NOISE, {})
    wav = os.path.join(a.workdir, f"t{k:04d}.wav")
    enc = os.path.join(a.workdir, f"t{k:04d}." + ("webm" if truth["codec"] == "opus" else "m4a"))
    sf.write(wav, mix, FS, subtype="FLOAT")
    codec = ["-c:a", "libopus", "-b:a", "128k"] if truth["codec"] == "opus" else ["-c:a", "aac", "-b:a", "128k"]
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", wav, *codec,
                    "-fflags", "+bitexact", "-flags:a", "+bitexact", enc], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    x = fm.load_audio(enc)
    for p in (wav, enc):
        try:
            os.remove(p)
        except OSError:
            pass
    m, cands = fm.detect_single(x, fm.SR, use_whisper=a.whisper != "none", whisper_model=a.whisper)
    row = dict(truth)
    if m is None or "fail" in m:
        row.update(detected=0, fail=(m or {}).get("fail", "no_candidate"))
        return row
    row.update(detected=1, fail="", det_gun=fm.fr(m["t_gun"], 6), det_set_on=fm.fr(m["t_set_on"], 6),
               det_set_off=fm.fr(m["t_set_off"], 6), det_fp_on=fm.fr(m["fp_on"], 6), det_fp_off=fm.fr(m["fp_off"], 6),
               det_set_snr=fm.fr(m["set_snr"], 2), det_set_spread=fm.fr(m["set_spread"], 5),
               det_gun_spread=fm.fr(m["gun_spread"], 5), burst_choice=m["burst_choice"],
               qc_flag="ok" if not m["qc"] else ";".join(m["qc"]))
    return row


_ARGS = _TTS = _NOISE = None


def _init(args, tts, noise):
    global _ARGS, _TTS, _NOISE
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    _ARGS, _TTS, _NOISE = args, tts, noise


class Args:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts-dir", required=True)
    ap.add_argument("--noise-manifest", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--snrs", nargs="+", type=float, required=True)
    ap.add_argument("--noise-types", nargs="+", required=True)
    ap.add_argument("--n-per-cell", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--whisper", default="base.en")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    os.makedirs(ns.workdir, exist_ok=True)
    tts = sorted(os.path.join(ns.tts_dir, f) for f in os.listdir(ns.tts_dir) if f.endswith(".wav"))
    noise = pd.read_csv(ns.noise_manifest)
    audio_files = {f.split(".")[0]: os.path.join(ns.audio_dir, f) for f in sorted(os.listdir(ns.audio_dir))
                   if not f.endswith((".part", ".log", ".ytdl"))}
    args = Args()
    for k, v in vars(ns).items():
        setattr(args, k, v)
    args.audio_files = audio_files
    n = ns.n_per_cell * len(ns.snrs) * len(ns.noise_types)
    rows = []
    with ProcessPoolExecutor(max_workers=ns.jobs, initializer=_init, initargs=(args, tts, noise)) as ex:
        for i, row in enumerate(ex.map(run_trial, range(n), chunksize=4)):
            rows.append(row)
            if (i + 1) % 20 == 0:
                print(f"{i + 1}/{n}", flush=True)
    out = pd.DataFrame(rows).sort_values("trial")
    os.makedirs(os.path.dirname(os.path.abspath(ns.out)), exist_ok=True)
    out.to_csv(ns.out, index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
