"""Step 1: download World Athletics results pages (all rounds) into data/raw/wa/pages/.

For each competition x event we fetch the Final page, read the list of phases
(``allEventPhasesByDiscipline`` in the page's embedded __NEXT_DATA__ JSON), then
fetch every other phase page. Raw HTML is stored gzipped with a .meta.json
sidecar (URL, retrieval time, sha256). Already-cached pages are not refetched.

Usage (from the ssac/ folder):
  .venv/Scripts/python.exe data/scripts/fetch_wa_results.py --comps WCH2023,WCH2025
  .venv/Scripts/python.exe data/scripts/fetch_wa_results.py --comps all --events 100m,100mH,110mH,200m
"""
from __future__ import annotations

import argparse
import sys

from config import ALL_EVENTS, COMPETITIONS, comp_key, results_url
from wa_http import RAW, extract_next_data, fetch, read_cached_text

PAGES = RAW / "wa" / "pages"


def page_cache_path(c: dict, sex_slug: str, disc_slug: str, phase_slug: str):
    return PAGES / comp_key(c) / f"{sex_slug}-{disc_slug}-{phase_slug}.html.gz"


def fetch_phase(c, sex_slug, disc_slug, phase_slug):
    url = results_url(c, sex_slug, disc_slug, phase_slug)
    path = page_cache_path(c, sex_slug, disc_slug, phase_slug)
    meta = fetch(url, path, gz=True)
    if meta["status"] != 200:
        return meta, None
    data = extract_next_data(read_cached_text(path))
    return meta, data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--comps", default="WCH2023,WCH2025",
                    help="comma list like WCH2023,OG2024 or 'all'")
    ap.add_argument("--events", default="100m,100mH,110mH",
                    help="comma list of event codes (100m,100mH,110mH,200m)")
    args = ap.parse_args(argv)

    comps = COMPETITIONS if args.comps == "all" else [
        c for c in COMPETITIONS if comp_key(c) in args.comps.split(",")]
    wanted = args.events.split(",")
    events = [e for e in ALL_EVENTS if e[0] in wanted]

    for c in comps:
        for ev, sex, sex_slug, disc_slug in events:
            meta, data = fetch_phase(c, sex_slug, disc_slug, "final")
            tag = f"{comp_key(c)} {ev} {sex}"
            if data is None:
                print(f"[miss] {tag}: final page HTTP {meta['status']}", flush=True)
                continue
            pp = data["props"]["pageProps"]
            phases = pp.get("allEventPhasesByDiscipline") or []
            ev_name = (pp.get("event") or {}).get("name")
            print(f"[ok]   {tag}: {ev_name} | phases: "
                  + ", ".join(p["phaseName"] for p in phases), flush=True)
            for p in phases:
                slug = p["phaseNameUrlSlug"]
                if slug == "final":
                    continue
                m2, d2 = fetch_phase(c, sex_slug, disc_slug, slug)
                state = "cache" if m2.get("from_cache") else "net"
                print(f"         - {slug}: HTTP {m2['status']} ({state})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
