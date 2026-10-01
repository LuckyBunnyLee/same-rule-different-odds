"""EXPLORATORY scratch: download audio-only (bestaudio) for given YouTube ids into analysis/probe/audio/
(gitignored; never redistributed). One at a time, --limit-rate 800K, CREATE_NO_WINDOW."""
import os, subprocess, sys, glob
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
YTDLP = os.path.join(ROOT, ".venv", "Scripts", "yt-dlp.exe")
D = os.path.join(ROOT, "analysis", "probe", "audio")
flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
for vid in sys.argv[1:]:
    if [p for p in glob.glob(os.path.join(D, vid + ".*")) if not p.endswith((".part", ".ytdl"))]:
        print("have", vid); continue
    cmd = [YTDLP, "-f", "bestaudio", "--js-runtimes", "node", "--no-playlist", "--no-progress", "--limit-rate", "800K",
           "-o", os.path.join(D, vid + ".%(ext)s"), f"https://www.youtube.com/watch?v={vid}"]
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    print(vid, r.returncode, (r.stderr or "").strip().splitlines()[-1:] if r.returncode else "")
