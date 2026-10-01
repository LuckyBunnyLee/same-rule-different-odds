"""Whole-file faster-whisper transcription with word timestamps, cached as JSON (work/transcripts/<id>.<model>.json).

Usage: python transcribe.py <audio_path> [model]
Used to locate starter commands ("On your marks", "Set") and commentary cues (heat numbers) in long videos.
"""
import json, os, sys, time
import numpy as np
import fpmeasure as fm

HERE = os.path.dirname(os.path.abspath(__file__))


def transcribe_file(path, model_name="base.en", threads=8, force=False):
    vid = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(HERE, "work", "transcripts", f"{vid}.{model_name}.json")
    if os.path.exists(out) and not force:
        with open(out) as f:
            return json.load(f)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    x16 = fm.load_audio(path, sr=16000)
    m = fm.get_whisper(model_name, threads)
    t0 = time.time()
    segs, info = m.transcribe(x16, language="en", word_timestamps=True, vad_filter=False, beam_size=5,
                              condition_on_previous_text=False)
    res = {"file": os.path.basename(path), "model": model_name, "segments": []}
    for s in segs:
        res["segments"].append({"start": s.start, "end": s.end, "text": s.text,
                                "words": [[w.word.strip(), w.start, w.end, w.probability] for w in (s.words or [])]})
    res["elapsed_s"] = time.time() - t0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(res, f)
    return res


if __name__ == "__main__":
    r = transcribe_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "base.en")
    print(r["file"], len(r["segments"]), "segments", f"{r.get('elapsed_s', 0):.0f}s")
