"""Single source of truth for the RT data pipeline commands.

  .venv/Scripts/python.exe data/scripts/pipeline.py --fetch      # network steps (cached, polite)
  .venv/Scripts/python.exe data/scripts/pipeline.py --build      # offline: all derived tables
  .venv/Scripts/python.exe data/scripts/pipeline.py --producers  # merge our entries into producers.json

The --build commands are exactly the ones recorded in ../../producers.json
(output path -> command, run from the repo root with the venv interpreter), and
each writes a single file named by --out, so scripts/verify_producers.py can
re-run them into a temp dir and compare bytes. Network/OCR steps (--fetch) fill
data/raw/ and are not byte-verifiable; their provenance is the per-file
.meta.json sidecars and data/raw/manifest.csv (URL, retrieved_at, sha256).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The analysed subset. Change here (and re-run --fetch/--build/--producers).
OUT_COMPS = "WCH2015,WCH2017,WCH2019,WCH2022,WCH2023,WCH2025,OG2020,OG2024"
OUT_EVENTS = "100m,100mH,110mH,200m"
IN_COMPS = "WIC2024,WIC2025"                    # extension: indoor 60m/60mH (Seiko holds)
IN_EVENTS = "60m,60mH"
COMPS = f"{OUT_COMPS},{IN_COMPS}"
EVENTS = f"{OUT_EVENTS},{IN_EVENTS}"
SEIKO = "WCH2015,WCH2017,WCH2019,WCH2022,WCH2023,WCH2025,WIC2024,WIC2025"   # WA hosts PDFs/waveforms only here

FETCH = [
    f"data/scripts/fetch_wa_results.py --comps {OUT_COMPS} --events {OUT_EVENTS}",
    f"data/scripts/fetch_wa_results.py --comps {IN_COMPS} --events {IN_EVENTS}",
    f"data/scripts/fetch_docs.py --kind pdf --comps {SEIKO} --events {EVENTS}",
    f"data/scripts/fetch_docs.py --kind waveform --comps {SEIKO} --events {EVENTS}",
    "data/scripts/fetch_fiore.py",
    "data/scripts/ocr_waveforms.py --ocr-dir data/raw/wa/waveform_ocr",
]

D = "data/derived"
SUB = f"--comps {COMPS} --events {EVENTS}"
PRODUCERS = {   # in dependency order
    f"{D}/rt_pdf_results.csv": f"data/scripts/parse_pdfs.py {SUB} --out {D}/rt_pdf_results.csv",
    f"{D}/rt_waveform.csv": (f"data/scripts/build_waveform.py --table races {SUB} "
                             f"--ocr-dir data/raw/wa/waveform_ocr --out {D}/rt_waveform.csv"),
    f"{D}/rt_waveform_lanes.csv": (f"data/scripts/build_waveform.py --table lanes {SUB} "
                                   f"--ocr-dir data/raw/wa/waveform_ocr --out {D}/rt_waveform_lanes.csv"),
    f"{D}/rt_athletes.csv": (f"data/scripts/build_rt.py --table athletes {SUB} "
                             f"--pdf {D}/rt_pdf_results.csv --waveform {D}/rt_waveform.csv "
                             f"--out {D}/rt_athletes.csv"),
    f"{D}/races.csv": (f"data/scripts/build_rt.py --table races {SUB} "
                       f"--pdf {D}/rt_pdf_results.csv --waveform {D}/rt_waveform.csv "
                       f"--out {D}/races.csv"),
    f"{D}/rt_fiore.csv": (f"data/scripts/build_fiore.py --fiore data/raw/fiore/rxntime.csv "
                          f"--athletes {D}/rt_athletes.csv --out {D}/rt_fiore.csv"),
    f"{D}/rt_qc_flags.csv": (f"data/scripts/qc_rt.py --report flags --athletes {D}/rt_athletes.csv "
                             f"--races {D}/races.csv --out {D}/rt_qc_flags.csv"),
    f"{D}/rt_coverage.csv": (f"data/scripts/qc_rt.py --report coverage --athletes {D}/rt_athletes.csv "
                             f"--races {D}/races.csv --out {D}/rt_coverage.csv"),
}


CHECKS = [   # invariant guards; fail the build if a documented property breaks
    (f"data/scripts/check_data.py --athletes {D}/rt_athletes.csv --races {D}/races.csv "
     f"--waveform {D}/rt_waveform.csv"),
]


def run(cmd: str) -> None:
    print(f"$ python {cmd}", flush=True)
    r = subprocess.run([sys.executable, *cmd.split()], cwd=ROOT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        sys.exit(f"step failed ({r.returncode}): {cmd}")


def write_producers() -> None:
    p = ROOT / "producers.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    cur.update(PRODUCERS)                     # other stages' entries are kept
    p.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"producers.json: {len(PRODUCERS)} data entries merged ({len(cur)} total)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--producers", action="store_true")
    a = ap.parse_args(argv)
    if a.fetch:
        for c in FETCH:
            run(c)
    if a.build:
        for c in list(PRODUCERS.values()) + CHECKS:
            run(c)
    if a.producers:
        write_producers()
    return 0


if __name__ == "__main__":
    sys.exit(main())
