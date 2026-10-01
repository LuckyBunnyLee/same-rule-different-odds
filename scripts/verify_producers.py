#!/usr/bin/env python3
"""Verify that every recorded producer command actually reproduces its output.

This is the check that catches the defect structural checks cannot see.

A real manifest recorded a producer as `summarize_tree_match.py` -- no
arguments. The script's defaults pointed at superseded arms, so the bare command
ran happily and wrote a DIFFERENT headline p-value (1.7e-16 rather than
3.2e-14). Three structural guards were in place; none could see it, because the
command string was structurally fine. Only running it revealed the problem.

Producers live in a JSON file mapping output path -> command, e.g.

  {
    "metrics/blockd.json": "scripts/summarize_holdout.py --rows metrics/blockd_rows.jsonl --out metrics/blockd.json",
    "metrics/tree_match.json": "scripts/summarize_tree_match.py --rows metrics/rows.jsonl --arm treatment --out metrics/tree_match.json"
  }

  python scripts/verify_producers.py producers.json
  python scripts/verify_producers.py producers.json --only metrics/blockd.json

Exit code is non-zero if any producer fails to reproduce its output.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("producers", help="JSON mapping output path -> command")
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--only", nargs="*", default=None, help="verify just these outputs")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    root = Path(a.root).resolve()
    producers = json.loads(Path(a.producers).read_text())
    if a.only:
        producers = {k: v for k, v in producers.items() if k in set(a.only)}

    mismatched: list[str] = []
    unverifiable: list[str] = []
    verified = 0

    with tempfile.TemporaryDirectory() as td:
        for out_rel, cmd in sorted(producers.items()):
            target = root / out_rel
            if not target.exists():
                unverifiable.append(f"{out_rel}: target missing")
                continue

            argv = cmd.split()
            name = Path(out_rel).name

            # Redirect the command's output so verification never touches the
            # real artifact. Without --out we cannot redirect safely: running it
            # would overwrite the very file we are checking.
            if "--out" in argv:
                argv[argv.index("--out") + 1] = f"{td}/{name}"
            else:
                unverifiable.append(f"{out_rel}: command has no --out to redirect")
                continue

            r = subprocess.run([sys.executable, *argv], cwd=root,
                               capture_output=True, text=True, timeout=a.timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            produced = Path(td) / name
            if r.returncode != 0 or not produced.exists():
                tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
                mismatched.append(f"{out_rel}: command failed ({r.returncode}) {tail}")
            elif produced.read_bytes() != target.read_bytes():
                mismatched.append(
                    f"{out_rel}: ran, but produced different bytes than the "
                    f"shipped file -- the recorded command is not the one used")
            else:
                verified += 1
                print(f"ok      {out_rel}")

    for u in unverifiable:
        print(f"SKIP    {u}")
    for m in mismatched:
        print(f"FAIL    {m}")

    print(f"\n{verified} reproduced, {len(unverifiable)} unverifiable, "
          f"{len(mismatched)} mismatched")
    if unverifiable:
        print("Unverifiable producers are reported, not ignored: a command with "
              "no --out cannot be checked without clobbering its own target. "
              "Give every producer an explicit --out.")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
