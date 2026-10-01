"""Build data/derived/video_sources.csv: one row per (race_id, source video).

Usage:
  python analysis/measure/build_video_sources.py --curated analysis/measure/race_starts_curated.csv \
      --candidates analysis/measure/video_candidates_curated.csv --races data/derived/races.csv \
      --athletes data/derived/rt_athletes.csv --wa-listing analysis/measure/discovery/wa_channel_videos_clean.tsv \
      --search analysis/measure/discovery/search_OG_20260929.jsonl analysis/measure/discovery/search_WCH_20260929.jsonl \
      --out data/derived/video_sources.csv

Rows come from (1) curated measured starts (status 'measured'; match_confidence from the evidence: 'high' when
title/order, commentary start-list names and Seiko attempt numbers agree, 'medium' when names were ambiguous and
the race follows from compilation order, or when the curation evidence is marked MODERATE/WEAK) and (2) curated candidate videos not yet measured (status 'candidate';
'medium' when a single race follows from title + start list, 'low' when only the round is known). Channel, title
and duration come from the WA channel listing (retrieved 2026-09-28) or the search snapshots (2026-09-29).
"""
import argparse
import json

import pandas as pd

MEDIUM = {"WCH2025-100m-W-R1-H2", "WCH2025-100mH-W-R1-H5"}  # names ambiguous; race from compilation order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curated", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--races", required=True)
    ap.add_argument("--athletes", required=True)
    ap.add_argument("--wa-listing", required=True)
    ap.add_argument("--search", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    meta = {}
    wa = pd.read_csv(a.wa_listing, sep="\t", dtype=str, keep_default_na=False)
    for _, r in wa.iterrows():
        meta[r["id"]] = dict(channel="World Athletics", title=r["title"], duration_s=r["duration"], retrieved_at="2026-09-28")
    for p in a.search:
        for line in open(p, encoding="utf-8"):
            j = json.loads(line)
            if j.get("id") and j["id"] not in meta:
                meta[j["id"]] = dict(channel=j.get("channel"), title=j.get("title"),
                                     duration_s=j.get("duration"), retrieved_at=j.get("retrieved_at", "")[:10])
    rows = []
    cur = pd.read_csv(a.curated)
    for (rid, vid), g in cur.groupby(["race_id", "video_id"], sort=True):
        m = meta.get(vid, {})
        att = ";".join(f"att{int(r.attempt)}@{r.t_gun_hint:.1f}s({r.attempt_status})" for _, r in g.sort_values("attempt").iterrows())
        evid = " ".join(g.evidence.astype(str))
        conf = "medium" if (rid in MEDIUM or "MODERATE" in evid or "WEAK" in evid) else "high"
        rows.append(dict(race_id=rid, url=f"https://www.youtube.com/watch?v={vid}", channel=m.get("channel"),
                         title=m.get("title"), duration_s=m.get("duration_s"), match_confidence=conf, status="measured",
                         notes=f"starts: {att}; evidence: {g.evidence.iloc[0]}", video_id=vid,
                         retrieved_at=m.get("retrieved_at")))
    races = pd.read_csv(a.races)
    ath = pd.read_csv(a.athletes)
    cand = pd.read_csv(a.candidates, keep_default_na=False)
    measured = set(zip(cur.race_id, cur.video_id))
    for _, c in cand.iterrows():
        m = meta.get(c.video_id, {})
        group = races[races.race_id.str.startswith(c.race_group + "-")].race_id.tolist()
        if c.athlete_hint:
            hit = ath[ath.race_id.isin(group) & ath.athlete.str.upper().str.contains(c.athlete_hint.upper(), regex=False)]
            group = sorted(hit.race_id.unique().tolist())
            conf = "medium" if len(group) == 1 else "low"
        else:
            conf = "medium" if len(group) == 1 else "low"
        for rid in group:
            if (rid, c.video_id) in measured:
                continue
            rows.append(dict(race_id=rid, url=f"https://www.youtube.com/watch?v={c.video_id}", channel=m.get("channel"),
                             title=m.get("title"), duration_s=m.get("duration_s"), match_confidence=conf,
                             status="candidate", notes=f"{c.match_basis}; {c.notes}", video_id=c.video_id,
                             retrieved_at=m.get("retrieved_at")))
    out = pd.DataFrame(rows).sort_values(["race_id", "status", "video_id"])
    out.to_csv(a.out, index=False, lineterminator="\n")
    print(out.status.value_counts().to_dict(), out.race_id.nunique(), "races")


if __name__ == "__main__":
    main()
