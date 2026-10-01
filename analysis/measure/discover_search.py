"""Search YouTube (via yt-dlp) for broadcast uploads of in-scope races and snapshot the raw results.

The snapshot (JSONL, one line per search hit, with query and retrieval time) is the provenance record;
video_sources.csv is then built deterministically from snapshots + curation by build_video_sources.py.

Usage:
  python analysis/measure/discover_search.py --races data/derived/races.csv --comps OG2020 OG2024 \
      --out analysis/measure/discovery/search_OG_<date>.jsonl
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
YTDLP = os.path.join(ROOT, ".venv", "Scripts", "yt-dlp.exe")

COMP_NAMES = {
    "WCH2019": ["World Athletics Championships Doha 2019", "Doha 2019 World Championships"],
    "WCH2022": ["World Athletics Championships Oregon 2022", "Eugene 2022 World Championships"],
    "WCH2023": ["World Athletics Championships Budapest 2023", "Budapest 2023 World Championships"],
    "WCH2025": ["World Athletics Championships Tokyo 2025", "Tokyo 2025 World Championships"],
    "OG2020": ["Tokyo 2020 Olympics", "Tokyo Olympics athletics"],
    "OG2024": ["Paris 2024 Olympics", "Paris Olympics athletics"],
}
EVENT_WORDS = {"100m": "100m", "100mH": "100m hurdles", "110mH": "110m hurdles"}
SEX_WORDS = {"M": "men's", "W": "women's"}
ROUND_WORDS = {"PR": "preliminary round", "R1": "heat", "SF": "semi-final", "F": "final", "RP": "repechage"}


def search(q, n):
    cmd = [YTDLP, "--flat-playlist", "--js-runtimes", "node", "--dump-json", f"ytsearch{n}:{q}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    hits = []
    for line in r.stdout.splitlines():
        try:
            j = json.loads(line)
        except Exception:
            continue
        hits.append({k: j.get(k) for k in ("id", "title", "channel", "channel_id", "duration", "view_count", "url")})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", required=True)
    ap.add_argument("--comps", nargs="+", required=True)
    ap.add_argument("--per-heat", action="store_true", help="also run one query per heat")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    races = pd.read_csv(a.races)
    races["compyear"] = races["comp"] + races["year"].astype(str)
    races = races[races.compyear.isin(a.comps)]
    queries = []
    for (cy, ev, sx, rd), g in races.groupby(["compyear", "event", "sex", "round"]):
        for cname in COMP_NAMES[cy]:
            queries.append((cy, ev, sx, rd, None, f"{cname} {SEX_WORDS[sx]} {EVENT_WORDS[ev]} {ROUND_WORDS[rd]}"))
        if a.per_heat and rd != "F":
            for h in sorted(str(v) for v in g["heat"].unique()):
                queries.append((cy, ev, sx, rd, h, f"{COMP_NAMES[cy][0]} {SEX_WORDS[sx]} {EVENT_WORDS[ev]} "
                                                   f"{ROUND_WORDS[rd]} {str(h).lstrip('H')}"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "a", encoding="utf-8") as f:
        for i, (cy, ev, sx, rd, h, q) in enumerate(queries):
            when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            hits = search(q, a.n)
            for rank, hit in enumerate(hits):
                f.write(json.dumps({"query": q, "compyear": cy, "event": ev, "sex": sx, "round": rd, "heat": h,
                                    "rank": rank, "retrieved_at": when, **hit}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i + 1}/{len(queries)}] {len(hits):2d} hits  {q}", flush=True)


if __name__ == "__main__":
    main()
