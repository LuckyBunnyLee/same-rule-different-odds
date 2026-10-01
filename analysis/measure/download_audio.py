"""Download audio-only streams (bestaudio) for YouTube video ids into data/video/audio/ (gitignored).

Usage:
  python analysis/measure/download_audio.py --ids ID1 ID2 ...
  python analysis/measure/download_audio.py --from-sources data/derived/video_sources.csv
  python analysis/measure/download_audio.py --ids ID --section 3600-3700   # only that time range (s)
  python analysis/measure/download_audio.py --ids ID --video   # low-res video (<=360p) for verification only

Network etiquette (shared, saturated link): downloads run strictly one at a time, audio-only by default,
rate-limited with --limit-rate 800K; prefer --section around a known start.

Audio is never redistributed; only derived timings and URLs are published.
"""
import argparse
import csv
import glob
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
YTDLP = os.path.join(ROOT, ".venv", "Scripts", "yt-dlp.exe")
AUDIO_DIR = os.path.join(ROOT, "data", "video", "audio")
VIDEO_DIR = os.path.join(ROOT, "data", "video", "lowres")


def have(vid, d):
    return [p for p in glob.glob(os.path.join(d, vid + ".*")) if not p.endswith(".part") and not p.endswith(".ytdl")]


def download(vid, video=False, retries=3, section=None, rate="800K"):
    d = VIDEO_DIR if video else AUDIO_DIR
    os.makedirs(d, exist_ok=True)
    name = vid if section is None else f"{vid}__{section.replace('-', '_')}"
    if have(name, d):
        return True
    fmt = "bv*[height<=360]+ba/b[height<=360]" if video else "bestaudio"
    cmd = [YTDLP, "-f", fmt, "--js-runtimes", "node", "--no-playlist", "--no-progress", "--limit-rate", rate,
           "-o", os.path.join(d, name + ".%(ext)s")]
    if section is not None:
        cmd += ["--download-sections", f"*{section}"]
    cmd += [f"https://www.youtube.com/watch?v={vid}"]
    for k in range(retries):
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and have(name, d):
            return True
        time.sleep(5 * (k + 1))
    sys.stderr.write(f"FAILED {vid}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}\n")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--from-sources", default=None)
    ap.add_argument("--ids-file", default=None, help="one video id per line (ids may start with '-')")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--section", default=None, help="start-end in seconds, e.g. 3600-3700")
    ap.add_argument("--limit-rate", default="800K")
    a = ap.parse_args()
    ids = list(a.ids)
    if a.ids_file:
        for line in open(a.ids_file, encoding="utf-8"):
            if line.strip() and not line.startswith("#") and line.strip() not in ids:
                ids.append(line.strip())
    if a.from_sources:
        with open(a.from_sources, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("video_id") and row["video_id"] not in ids:
                    ids.append(row["video_id"])
    for vid in ids:
        ok = download(vid, video=a.video, section=a.section, rate=a.limit_rate)
        print(("ok  " if ok else "FAIL") + " " + vid, flush=True)


if __name__ == "__main__":
    main()
