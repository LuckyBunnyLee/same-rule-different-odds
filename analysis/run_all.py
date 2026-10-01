"""Run the whole analysis pipeline end to end, register producers, and verify them.

Real mode (default): descriptive -> fp_models -> detector -> calibration -> power -> fairness -> systematic
-> figures -> producers.json
(analysis/* entries only, merged into the shared file) -> numbers.json -> results.md -> verify.
Mock mode (--mock): regenerates MOCK data and runs the compute scripts into analysis/mock/
(nothing is registered and nothing reaches numbers.json or results.md).

Usage:  .venv\\Scripts\\python.exe analysis\\run_all.py [--mock] [--skip-verify] [--fast]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
O, F = "analysis/outputs", "analysis/figures"

SEED = "--seed 20260928"
COMPUTE = [
    (f"{O}/descriptive.json", f"analysis/descriptive.py {SEED} --boot 1000 --fit-boot 200 --meet-boot 100 "
                              f"--min-starts 4 --out {O}/descriptive.json"),
    (f"{O}/fp_models.json", f"analysis/fp_models.py {SEED} --fp-source seiko --exclude-fp-comps WIC2025 --boot 500 "
                            f"--perm 5000 --phi 0.26 --phi-pdf 0.21 --catch 0.05 --out {O}/fp_models.json"),
    (f"{O}/detector.json", f"analysis/detector_check.py {SEED} --out {O}/detector.json"),
    (f"{O}/calibration.json", f"analysis/calibration.py {SEED} --boot 5000 --mc 20000 "
                              f"--fp-models {O}/fp_models.json --out {O}/calibration.json"),
    (f"{O}/power.json", f"analysis/power_analysis.py {SEED} --sims 10000 --m 8 --r 0.16 --validate-sims 200 "
                        f"--descriptive {O}/descriptive.json --out {O}/power.json"),
    (f"{O}/fairness.json", f"analysis/fairness_sim.py {SEED} --phi 0.25 --descriptive {O}/descriptive.json "
                           f"--fp-models {O}/fp_models.json --calibration {O}/calibration.json --out {O}/fairness.json"),
    (f"{O}/systematic.json", f"analysis/systematic.py {SEED} --descriptive {O}/descriptive.json --fp-models "
                             f"{O}/fp_models.json --calibration {O}/calibration.json --boot-r 2000 --sims 10000 "
                             f"--boot-h2 200 --boot-champ 100 --min-n 100 --min-races 10 "
                             f"--haugen-design analysis/haugen_design.csv --fiore-params analysis/fiore2025_params.csv "
                             f"--fiore-venue-pdf analysis/external/fiore2025/ComparisonOfVenueEffects.pdf "
                             f"--out {O}/systematic.json"),
    # trend.py (H1-S4, H6; analysis/prereg_addendum_trend.md)
    (f"{O}/trend.json", f"analysis/trend.py {SEED} --descriptive {O}/descriptive.json --calibration "
                        f"{O}/calibration.json --fairness {O}/fairness.json --sims 20000 --boot 5000 "
                        f"--perm 10000 --out {O}/trend.json"),
    # EXPLORATORY probe of 2022-2025 (not pre-registered): the probe's producer, run without --notes so that
    # verification never rewrites notes/recent_probe.md, and an adapter that publishes the quotable keys as probe.*
    (f"{O}/recent_probe.json", f"analysis/recent_probe.py --seed 20260930 --boot 2000 --out {O}/recent_probe.json"),
    (f"{O}/probe.json", f"analysis/probe_numbers.py --probe {O}/recent_probe.json --out {O}/probe.json"),
    # literature audit (lit/audit_protocol.md)
    (f"{O}/lit_audit.json", f"analysis/lit_audit.py --studies lit/audit_studies.csv --screening lit/audit_screening.csv "
                            f"--search-log lit/audit_search/search_log.json --out {O}/lit_audit.json"),
    # guard band (analysis/prereg_guardband.md)
    (f"{O}/guardband.json", f"analysis/guardband.py {SEED} --descriptive {O}/descriptive.json "
                            f"--fairness {O}/fairness.json --offset-draws 25 --out {O}/guardband.json"),
    # registered counts shown in the confound figure (fits k/n per fixed line; below/above the rule)
    (f"{O}/fig.json", f"analysis/fig_numbers.py --systematic {O}/systematic.json --guardband {O}/guardband.json "
                        f"--out {O}/fig.json"),
]
FIGS = [
    (f"{F}/power.png", f"analysis/make_figures.py --fig power --power {O}/power.json --out {F}/power.png"),
    (f"{F}/fairness.png", f"analysis/make_figures.py --fig fairness --fairness {O}/fairness.json "
                          f"--descriptive {O}/descriptive.json --out {F}/fairness.png"),
    (f"{F}/holds.png", f"analysis/make_figures.py --fig holds --fp {O}/fp_models.json "
                       f"--descriptive {O}/descriptive.json --out {F}/holds.png"),
    (f"{F}/rt_hist.png", f"analysis/make_figures.py --fig rt_hist --descriptive {O}/descriptive.json --out {F}/rt_hist.png"),
    (f"{F}/terciles.png", f"analysis/make_figures.py --fig terciles --fp {O}/fp_models.json --out {F}/terciles.png"),
    (f"{F}/policies.png", f"analysis/make_figures.py --fig policies --fairness {O}/fairness.json --out {F}/policies.png"),
    (f"{F}/story_wide.png", f"analysis/make_figures.py --fig story_wide --fp {O}/fp_models.json "
                            f"--descriptive {O}/descriptive.json --out {F}/story_wide.png"),       # abstract Figure 1
    (f"{F}/confound.png", f"analysis/make_figures.py --fig confound --systematic {O}/systematic.json "
                          f"--guardband {O}/guardband.json --fignums {O}/fig.json --out {F}/confound.png"),                                          # confounder-audit figure
]
SUMMARY = [
    ("analysis/numbers.json", f"analysis/make_numbers.py --producers producers.json --in {O}/descriptive.json "
                              f"{O}/fp_models.json {O}/calibration.json {O}/detector.json {O}/power.json "
                              f"{O}/fairness.json {O}/systematic.json {O}/trend.json {O}/probe.json {O}/lit_audit.json "
                              f"{O}/guardband.json {O}/fig.json "
                              f"--extra analysis/measure/numbers.json:measure "
                              f"--out analysis/numbers.json"),
    ("analysis/results.md", "analysis/build_results.py --numbers analysis/numbers.json --final --out analysis/results.md"),
]


def run(cmd: str):
    print(f"\n>>> {cmd}", flush=True)
    r = subprocess.run([sys.executable, *cmd.split()], cwd=ROOT,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))   # no console pop-ups on Windows
    if r.returncode != 0:
        raise SystemExit(f"FAILED ({r.returncode}): {cmd}")


def register(entries):
    """Merge analysis/* producers into the shared producers.json (other stages' keys untouched)."""
    p = ROOT / "producers.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    # analysis/measure/* belongs to the measurement pipeline: never drop its entries
    cur = {k: v for k, v in cur.items() if not (k.startswith("analysis/") and not k.startswith("analysis/measure/"))}
    cur.update(dict(entries))
    p.write_text(json.dumps(dict(sorted(cur.items())), indent=2) + "\n", encoding="utf-8")
    print(f"registered {len(entries)} analysis producers in producers.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--skip-compute", action="store_true", help="reuse existing result JSONs")
    a = ap.parse_args()
    if a.mock:
        run("analysis/make_mock.py")
        for cmd in ("analysis/descriptive.py --mock --boot 200 --fit-boot 50 --meet-boot 20",
                    "analysis/fp_models.py --mock --fp-source audio --boot 50 --perm 500",
                    "analysis/power_analysis.py --mock --sims 2000 --validate-sims 0",
                    "analysis/fairness_sim.py --mock --descriptive analysis/mock/outputs/descriptive.json "
                    "--fp-models analysis/mock/outputs/fp_models.json"):
            run(cmd)
        print("\nMOCK pipeline finished (outputs in analysis/mock/; nothing registered)")
        return
    if not a.skip_compute:
        for _, cmd in COMPUTE:
            run(cmd)
    for _, cmd in FIGS:
        run(cmd)
    register(COMPUTE + FIGS + SUMMARY)
    for _, cmd in SUMMARY:
        run(cmd)
    if not a.skip_verify:
        only = [k for k, _ in COMPUTE + FIGS + SUMMARY]
        run("scripts/verify_producers.py producers.json --only " + " ".join(only))


if __name__ == "__main__":
    main()
