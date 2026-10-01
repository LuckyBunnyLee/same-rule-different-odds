#!/usr/bin/env python3
"""Fetch the third-party files this repository uses but does not redistribute, verify them, and rebuild
data/derived/rt_fiore.csv.

github.com/ofiore/Thesis (Fiore, Schifano & Yan 2025) has no licence file, so its files are not copied into this
repository. This script downloads them from pinned commits, checks every file against the sha256 recorded when the
analysis was run, and then:

  1. rebuilds data/derived/rt_fiore.csv with the registered producer command (producers.json), which maps each row of
     Fiore et al.'s rxntime.csv to our race_id / athlete keys, and checks its sha256;
  2. regenerates analysis/external/fiore2025/source_extract.txt (the manuscript lines whose parameters are transcribed
     in analysis/fiore2025_params.csv; used only by a test) and checks its sha256.

Everything lands in git-ignored paths. Run from the repository root:

    python scripts/fetch_third_party.py            # download what is missing, verify, rebuild
    python scripts/fetch_third_party.py --check    # verify only (no network)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/ofiore/Thesis"
DATA_COMMIT = "3cf1db7adebb493f3a5c2e957a1b09cf0986a7cd"       # Data/rxntime.csv as used (retrieved 2026-09-29)
MS_COMMIT = "85d9a60b68741f308cd1670e2e425c1f4a640341"         # manuscript sources as used (retrieved 2026-09-30)

# (url, local path, sha256)
FILES = [
    (f"{RAW}/{DATA_COMMIT}/Data/rxntime.csv", "data/raw/fiore/rxntime.csv",
     "5b8d3144a5771e90019ff8283fc4f884ac70577d30193bdcb1047d69f0a607cf"),
    (f"{RAW}/{MS_COMMIT}/Manuscript/ComparisonOfVenueEffects.pdf",
     "analysis/external/fiore2025/ComparisonOfVenueEffects.pdf",
     "1254ba381a51418ee3cdad7c47e975f8daa0de871ca82a6e4135a3a97d2273f2"),
    (f"{RAW}/{MS_COMMIT}/Manuscript/manuscript.tex", "analysis/external/fiore2025/src/Manuscript/manuscript.tex",
     "a118f617ec47860008f6f0d9af44aa57b3be67556089d576c803bd446120949c"),
    (f"{RAW}/{MS_COMMIT}/Manuscript/supp.tex", "analysis/external/fiore2025/src/Manuscript/supp.tex",
     "22c85d394a3ed1e257b059e8611dc3bc0de72cb61f359eb019b3bbcbe5729897"),
    (f"{RAW}/{MS_COMMIT}/Code/ReactionBarrierAnalysis.Rmd",
     "analysis/external/fiore2025/src/Code/ReactionBarrierAnalysis.Rmd",
     "3b6216e07af5cfa0bdd1a37c65e661f0a5a24724f5c0d73c4c062bc25826599f"),
]
RT_FIORE = ("data/derived/rt_fiore.csv", "dff5cb184d1bd38dc19396010ce23b79636094bbb5c01e39658dec3b63a59e2a")
EXTRACT = ("analysis/external/fiore2025/source_extract.txt",
           "0cd2f87a605d66af35f8312e4c89d8d5ed0f4d80647c51f5a1977316d4919b45")
# manuscript lines quoted in the extract: (file, label, first line, last line)
EXTRACT_BLOCKS = [
    ("Manuscript/manuscript.tex", "model", 585, 592),
    ("Manuscript/manuscript.tex", "Table 2, tab:ggfit", 633, 637),
    ("Manuscript/manuscript.tex", "Table 3, tab:Sim_probability", 700, 704),
    ("Manuscript/manuscript.tex", "Table 4, tab:Sim_time", 750, 754),
    ("Manuscript/supp.tex", "tab:womensfit", 148, 151),
    ("Manuscript/supp.tex", "women vs men tail probabilities", 176, 181),
    ("Manuscript/supp.tex", "women vs men barriers", 202, 205),
    ("Code/ReactionBarrierAnalysis.Rmd", "simfit", 201, 215),
    ("Code/ReactionBarrierAnalysis.Rmd",
     "venue-effects figure: top = gg3b incl. 2022, bottom = gg3b_no2022", 136, 168),
]
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ssac27-repro/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def build_extract() -> bytes:
    src = ROOT / "analysis" / "external" / "fiore2025" / "src"
    out = [f"Verbatim extract (for verification only) from github.com/ofiore/Thesis at commit {MS_COMMIT}; "
           "sha256 of each full file in SOURCE.json."]
    cache: dict[str, list[str]] = {}
    for f, label, a, b in EXTRACT_BLOCKS:
        lines = cache.setdefault(f, (src / f).read_bytes().decode("utf-8").splitlines())
        out.append(f"--- {f} ({label}) lines {a}-{b} ---")
        out += [f"{n}: {lines[n - 1]}" for n in range(a, b + 1)]
    return ("\r\n".join(out) + "\r\n").encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify existing files only; never download or rebuild")
    a = ap.parse_args()
    problems = []

    for url, rel, want in FILES:
        p = ROOT / rel
        if not p.exists() or sha256(p) != want:
            if a.check:
                problems.append(f"{rel}: {'missing' if not p.exists() else 'sha256 differs'}")
                continue
            print(f"download {url}")
            download(url, p)
        got = sha256(p)
        print(f"{'ok  ' if got == want else 'FAIL'}  {rel}  sha256 {got[:12]}")
        if got != want:
            problems.append(f"{rel}: sha256 {got} != recorded {want}")

    if not problems and not a.check:
        # 1. rebuild rt_fiore.csv with the registered producer command
        cmd = json.loads((ROOT / "producers.json").read_text(encoding="utf-8"))[RT_FIORE[0]]
        print(f"run   {cmd}")
        r = subprocess.run([sys.executable, *cmd.split()], cwd=ROOT, creationflags=NOWIN)
        if r.returncode != 0:
            problems.append(f"build_fiore.py failed ({r.returncode})")
        # 2. regenerate the manuscript extract used by analysis/tests/test_systematic.py
        (ROOT / EXTRACT[0]).write_bytes(build_extract())

    for rel, want in (RT_FIORE, EXTRACT):
        p = ROOT / rel
        if not p.exists():
            problems.append(f"{rel}: missing")
            continue
        got = sha256(p)
        print(f"{'ok  ' if got == want else 'FAIL'}  {rel}  sha256 {got[:12]}")
        if got != want:
            problems.append(f"{rel}: sha256 {got} != recorded {want}")

    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("\nall third-party inputs present and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
