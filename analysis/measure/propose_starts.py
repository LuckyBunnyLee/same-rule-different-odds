"""Propose start candidates in a multi-race recording and suggest the race each belongs to.

Usage:
  python analysis/measure/propose_starts.py --video-id i8spi5W5Wyc --group WCH2025-100m-M \
      --audio-dir data/video/audio --transcript analysis/measure/work/transcripts/i8spi5W5Wyc.base.en.json \
      --athletes data/derived/rt_athletes.csv --races data/derived/races.csv --extra 4 \
      --out analysis/measure/proposals/i8spi5W5Wyc.csv

Candidates are ranked by start score; the top (n_races + extra), at least 30 s apart, are listed in time order.
For each, surnames from each race's start list are fuzzy-matched (difflib ratio >= 0.8, tokens >= 4 letters;
single tokens and adjacent-token concatenations) against transcript words from 150 s before to 30 s after the
candidate. The output is a proposal for curation, not a final assignment.
"""
import argparse
import difflib
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fpmeasure as fm  # noqa: E402


def surnames(name):
    toks = [t for t in re.split(r"[\s\-']+", str(name)) if t.isupper() and len(t) >= 3]
    return [t.lower() for t in toks] or [str(name).split()[-1].lower()]


def words_in(tr, t0, t1):
    ws = []
    for s in tr["segments"]:
        for w in s["words"]:
            if t0 <= w[1] <= t1:
                ws.append(re.sub(r"[^a-z]", "", w[0].lower()))
    ws = [w for w in ws if w]
    return ws + [a + b for a, b in zip(ws, ws[1:])]


def match_count(sn_list, ws):
    hit = 0
    for sns in sn_list:
        ok = False
        for sn in sns:
            for w in ws:
                if len(sn) < 4:
                    ok = ok or w == sn
                elif abs(len(w) - len(sn)) <= 3 and difflib.SequenceMatcher(None, sn, w).ratio() >= 0.8:
                    ok = True
                if ok:
                    break
            if ok:
                break
        hit += ok
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--group", required=True, help="race_id prefix, e.g. WCH2025-100m-W")
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--transcript", required=True, help="whisper JSON, or 'none' (no name matching)")
    ap.add_argument("--athletes", required=True)
    ap.add_argument("--races", required=True)
    ap.add_argument("--extra", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    races = pd.read_csv(a.races)
    races = races[(races.race_id == a.group) | races.race_id.str.startswith(a.group + "-")]
    ath = pd.read_csv(a.athletes)
    starts = {rid: [surnames(n) for n in g.athlete] for rid, g in ath[ath.race_id.isin(races.race_id)].groupby("race_id")}
    tr = json.load(open(a.transcript, encoding="utf-8")) if a.transcript != "none" else {"segments": []}
    path = [os.path.join(a.audio_dir, f) for f in sorted(os.listdir(a.audio_dir)) if f.startswith(a.video_id + ".")][0]
    x = fm.load_audio(path)
    cands, _ = fm.detect_candidates(x)
    k = len(races) + a.extra
    chosen = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if all(abs(c["t"] - d["t"]) >= 30 for d in chosen):
            chosen.append(c)
        if len(chosen) >= k:
            break
    rows = []
    for c in sorted(chosen, key=lambda c: c["t"]):
        ws = words_in(tr, c["t"] - 150, c["t"] + 30)
        sc = sorted(((match_count(v, ws), rid) for rid, v in starts.items()), reverse=True)
        best, second = sc[0], (sc[1] if len(sc) > 1 else (0, ""))
        rows.append(dict(video_id=a.video_id, t_cand=round(c["t"], 3), score=round(c["score"], 2),
                         race_loud=round(c["race_loud"], 2), set_gap=round(c["set_gap"], 3) if c["set_gap"] == c["set_gap"] else None,
                         best_race=best[1], best_hits=best[0], second_race=second[1], second_hits=second[0]))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    pd.DataFrame(rows).to_csv(a.out, index=False, lineterminator="\n")
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    main()
