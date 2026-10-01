"""Tests for analysis/probe_numbers.py (EXPLORATORY probe keys, 'probe.*').

G1 every probe.* number in probe.json and numbers.json is labelled 'EXPLORATORY (not pre-registered)'
G2 every value re-derives from recent_probe.json (copied, sign-flipped or counted exactly as documented)
G3 the stale-input check fires when a recorded input hash no longer matches the file
Each guard is shown to fire on a corrupted copy.

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_probe_numbers.py   (or pytest)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_numbers as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"
LABEL = "EXPLORATORY (not pre-registered)"


def check_labels(probe: dict, numbers: dict | None) -> list:
    bad = [k for k, e in probe["numbers"].items() if not str(e.get("desc", "")).startswith(LABEL)]
    if numbers is not None:
        bad += [k for k, e in numbers["numbers"].items() if k.startswith("probe.") and not str(e.get("desc", "")).startswith(LABEL)]
    return [f"not labelled exploratory: {k}" for k in bad]


def check_rederive(probe: dict, rp: dict) -> list:
    want = P.build(rp)
    bad = []
    for k, e in want.items():
        got = probe["numbers"].get(k)
        if got is None or got["value"] != e["value"] or got.get("ci95") != (list(e["ci95"]) if "ci95" in e else None):
            bad.append(f"{k}: stored {None if got is None else (got['value'], got.get('ci95'))} vs re-derived "
                       f"{(e['value'], e.get('ci95'))}")
    w25 = rp["q4_same_athletes"]["within_athlete_200m_minus_straight_ms"]["WCH2025"]
    if probe["numbers"]["wch2025_straight_minus_200m_same_athlete_ms"]["value"] != round(-w25["mean"], 2):
        bad.append("sign flip of the WCH2025 same-athlete difference")
    return bad


def check_stale(rp: dict) -> list:
    rec = P.probe_inputs(rp)
    return [p for p, s_ in rec.items() if P.sha12(ROOT / p) != s_]


def run() -> bool:
    pj, rj = OUT / "probe.json", OUT / "recent_probe.json"
    if not (pj.exists() and rj.exists()):
        print("[skip] probe outputs not built")
        return True
    probe = json.loads(pj.read_text(encoding="utf-8"))
    rp = json.loads(rj.read_text(encoding="utf-8"))
    nums = json.loads((ROOT / "analysis" / "numbers.json").read_text(encoding="utf-8"))
    failures = check_labels(probe, nums) + check_rederive(probe, rp) + [f"stale input {p}" for p in check_stale(rp)]
    fired = []
    c = copy.deepcopy(probe)
    k0 = next(iter(c["numbers"]))
    c["numbers"][k0]["desc"] = "unlabelled"
    fired.append(bool(check_labels(c, None)))
    c = copy.deepcopy(probe)
    c["numbers"]["same_athletes_2022_to_2023_change_ms"]["value"] += 1.0
    fired.append(bool(check_rederive(c, rp)))
    r2 = copy.deepcopy(rp)
    first = next(iter(r2["inputs"]))
    r2["inputs"][first] = "000000000000"
    fired.append(bool(check_stale(r2)))
    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(fired)}/{len(fired)}")
    ok = not failures and all(fired)
    if ok:
        print(f"[ok] probe.json: {len(probe['numbers'])} numbers labelled EXPLORATORY, re-derived from recent_probe.json, "
              f"inputs current")
    return ok


def test_probe_numbers():
    assert run()


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
