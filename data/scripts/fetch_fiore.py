"""Download Owen Fiore's thesis reaction-time data (github.com/ofiore/Thesis).

Pinned to commit 3cf1db7 (2024-11-26, "reaction time data"), the last commit that
touched Data/rxntime.csv as of 2026-09-28. The repo's Data/README.md (column
documentation) is fetched from the same commit and from main.

Usage: .venv/Scripts/python.exe data/scripts/fetch_fiore.py
"""
from __future__ import annotations

import sys

from wa_http import RAW, fetch

COMMIT = "3cf1db7adebb493f3a5c2e957a1b09cf0986a7cd"
BASE = "https://raw.githubusercontent.com/ofiore/Thesis"
FILES = {
    f"{BASE}/{COMMIT}/Data/rxntime.csv": RAW / "fiore" / "rxntime.csv",
    f"{BASE}/{COMMIT}/Data/README.md": RAW / "fiore" / "README_at_3cf1db7.md",
    f"{BASE}/main/Data/README.md": RAW / "fiore" / "README_main.md",
}


def main():
    for url, path in FILES.items():
        meta = fetch(url, path)
        print(meta["status"], meta["bytes"], url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
