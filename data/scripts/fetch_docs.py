"""Step 3: download official documents linked from the WA results pages.

* ``--kind pdf``      : phase-level 'Official Results' PDFs (RS6), used for DQ
                        rule codes (TR16.8 false start), actual start times, weather.
* ``--kind waveform`` : per-heat Seiko start 'Waveform' JPGs (start attempt number,
                        'Ready Time', per-lane RT and block-force traces).

URLs are read from the cached WA results pages (build_rt.load_all). Files are
cached under data/raw/wa/pdf/<wa competition id>/ and data/raw/wa/waveform/<id>/
with .meta.json sidecars; both folders are git-ignored (re-downloadable).

Usage: .venv/Scripts/python.exe data/scripts/fetch_docs.py --kind pdf --comps WCH2023,WCH2025 [--events 100m,100mH,110mH]
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from wa_http import RAW, fetch


def local_path(url: str, kind: str):
    # .../competitiondocuments/<kind>/<eventId>/<fileName>
    parts = url.split("/competitiondocuments/")[1].split("/")
    return RAW / "wa" / kind / parts[1] / parts[-1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["pdf", "waveform"], required=True)
    ap.add_argument("--comps", required=True, help="comma list, e.g. WCH2022,WCH2023")
    ap.add_argument("--events", default="100m,100mH,110mH")
    args = ap.parse_args(argv)
    from build_rt import load_all
    _, races = load_all(args.comps.split(","), args.events.split(","))
    if args.kind == "pdf":
        urls = sorted(set(races["results_pdf_url"].dropna()) |
                      set(races.get("unit_results_pdf_url", pd.Series(dtype=str)).dropna()))
    else:
        urls = sorted(set(races["waveform_url"].dropna()))
    urls = [u for u in urls if isinstance(u, str) and u.startswith("http")]
    n_net = 0
    for i, u in enumerate(urls, 1):
        meta = fetch(u, local_path(u, args.kind))
        n_net += not meta.get("from_cache")
        if meta["status"] != 200:
            print(f"[{meta['status']}] {u}", flush=True)
        if i % 20 == 0:
            print(f"{i}/{len(urls)} done ({n_net} downloaded)", flush=True)
    print(f"{args.kind}: {len(urls)} urls, {n_net} downloaded this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
