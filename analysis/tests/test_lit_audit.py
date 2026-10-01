"""Tests and claim guards for analysis/lit_audit.py (guard every claim a test can hold).

Unit tests
  1. the protocol's vulnerable rule (lit/audit_protocol.md section 6) as a truth table
  2. the shipped coding (lit/audit_studies.csv, lit/audit_screening.csv) passes every validation check
  3. N, K, findings, strict and upper-bound counts recomputed by an independent implementation (csv module, no
     pandas, no import of the producer's counting code) equal the producer's numbers
Claim guards on analysis/outputs/lit_audit.json, each proven to fire on a corrupted copy
  G1 K <= N, share = K / N, percent = round(100 K / N); same for findings
  G2 class counts and effect-type counts each sum to the number of findings
  G3 strict K <= K <= upper-bound K; vulnerable findings in conflict groups <= findings in conflict groups
  G4 n_conflict_groups equals the listed groups, and every group table row names >= 2 directions
  G5 the JSON's headline counts equal the independent recount of the CSV
  G6 every rule-era finding is class E and every rule-era study vulnerable (pins the optional "every" wording;
     if it fails, change the prose)
Firing tests
  F1 validate() reports each of 8 corruptions of the coding (flipped vulnerable flag, unknown class, S finding
     with a restricted conclusion, single-direction conflict group, member without direction, M without the
     averaging flag, primary study missing from the screening includes, multi-championship S finding)
  F2 the claim guards report each of 8 corruptions of the result JSON
  F3 the command line exits non-zero on a corrupted CSV, and reproduces the shipped JSON byte for byte

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_lit_audit.py   (or pytest)
"""
from __future__ import annotations

import copy
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lit_audit as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STUDIES = ROOT / "lit" / "audit_studies.csv"
SCREEN = ROOT / "lit" / "audit_screening.csv"
LOG = ROOT / "lit" / "audit_search" / "search_log.json"
OUT = ROOT / "analysis" / "outputs" / "lit_audit.json"
PY = sys.executable
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CMD = ["analysis/lit_audit.py", "--studies", "lit/audit_studies.csv", "--screening", "lit/audit_screening.csv",
       "--search-log", "lit/audit_search/search_log.json"]


# ---------------------------------------------------------------------------------------------------
# independent recount (plain csv; mirrors the protocol text, not the producer's code)
# ---------------------------------------------------------------------------------------------------

def recount(path: Path = STUDIES) -> dict:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["in_primary"] == "yes"]

    def vul(r):
        return r["design_class"] in ("P", "S", "E") or (r["design_class"] == "M" and r["m_averages_venues"] == "yes")

    studies = {r["study_id"] for r in rows}
    k = {r["study_id"] for r in rows if vul(r)}
    strict = {r["study_id"] for r in rows if vul(r) and r["depends_on_between_contrast"] == "yes"}
    upper = {r["study_id"] for r in rows if vul(r) or r["design_class"] == "U"}
    groups = {r["conflict_group"] for r in rows if r["conflict_group"]}
    return {"n_studies": len(studies), "k_vulnerable_studies": len(k), "n_findings": len(rows),
            "k_vulnerable_findings": sum(vul(r) for r in rows), "k_strict_studies": len(strict),
            "k_u_as_vulnerable_studies": len(upper), "n_conflict_groups": len(groups)}


# ---------------------------------------------------------------------------------------------------
# claim guards on the result JSON
# ---------------------------------------------------------------------------------------------------

def guard_problems(res: dict, rc: dict | None = None) -> list[str]:
    n = {k: v["value"] for k, v in res["numbers"].items()}
    p = []
    if not (0 <= n["k_vulnerable_studies"] <= n["n_studies"]):
        p.append("G1 K outside [0, N]")
    if abs(n["share_vulnerable_studies"] - n["k_vulnerable_studies"] / n["n_studies"]) > 1e-5:
        p.append("G1 share != K / N")
    if n["pct_vulnerable_studies"] != round(100 * n["k_vulnerable_studies"] / n["n_studies"]):
        p.append("G1 percent != round(100 K / N)")
    if abs(n["share_vulnerable_findings"] - n["k_vulnerable_findings"] / n["n_findings"]) > 1e-5:
        p.append("G1 findings share")
    if sum(n[f"findings_class_{c}"] for c in L.CLASSES) != n["n_findings"]:
        p.append("G2 class counts do not sum to findings")
    if sum(n[f"findings_{e}"] for e in L.EFFECTS) != n["n_findings"]:
        p.append("G2 effect counts do not sum to findings")
    if sum(n[f"vulnerable_findings_{e}"] for e in L.EFFECTS) != n["k_vulnerable_findings"]:
        p.append("G2 vulnerable effect counts do not sum to vulnerable findings")
    if not (n["k_strict_studies"] <= n["k_vulnerable_studies"] <= n["k_u_as_vulnerable_studies"]):
        p.append("G3 strict <= K <= upper violated")
    if n["vulnerable_findings_in_conflict_groups"] > n["findings_in_conflict_groups"]:
        p.append("G3 conflict findings")
    groups = res["numbers"]["n_conflict_groups"].get("groups", [])
    if n["n_conflict_groups"] != len(groups) or len(res["tables"]["conflict_groups"]) != len(groups):
        p.append("G4 conflict group count")
    for row in res["tables"]["conflict_groups"]:
        if row["directions"].count(":") < 2:
            p.append(f"G4 group {row['group']} lists fewer than 2 directions")
    if rc is not None:
        for k, v in rc.items():
            if n[k] != v:
                p.append(f"G5 {k}: JSON {n[k]} vs recount {v}")
    # G6 the optional wording "every rule-era study rests on an era contrast" needs all rule-era
    # findings to be class E and all rule-era studies vulnerable; if this fails, change the prose, not the test
    if n["findings_rule_era_class_E"] != n["findings_rule_era"] or \
            n["conflict_rule_era_vulnerable_studies"] != n["conflict_rule_era_studies"]:
        p.append("G6 not every rule-era finding is class E / vulnerable")
    return p


# ---------------------------------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------------------------------

def test_vulnerable_rule():
    for c in ("P", "S", "E"):
        assert L.vulnerable_rule(c, "na")
    assert L.vulnerable_rule("M", "yes")
    assert not L.vulnerable_rule("M", "no")
    for c in ("W", "U"):
        assert not L.vulnerable_rule(c, "na")


def test_shipped_coding_valid():
    errs = L.validate(L.load(STUDIES), L.load(SCREEN))
    assert errs == [], errs


def test_independent_recount_matches_producer():
    df, sc = L.load(STUDIES), L.load(SCREEN)
    numbers, _, _ = L.compute(df, sc, json.loads(LOG.read_text(encoding="utf-8")))
    rc = recount()
    for k, v in rc.items():
        assert numbers[k]["value"] == v, (k, numbers[k]["value"], v)


def test_result_json_guards():
    assert OUT.exists(), "run analysis/lit_audit.py first"
    res = json.loads(OUT.read_text(encoding="utf-8"))
    probs = guard_problems(res, recount())
    assert probs == [], probs


def coding_corruptions(df: pd.DataFrame, sc: pd.DataFrame):
    """Yield (label, corrupted df, corrupted screening)."""
    def first(mask):
        return df.index[mask][0]

    d = df.copy(); i = first(d["vulnerable"] == "yes"); d.loc[i, "vulnerable"] = "no"
    yield "flipped vulnerable flag", d, sc
    d = df.copy(); d.loc[d.index[0], "design_class"] = "X"
    yield "unknown class", d, sc
    d = df.copy(); i = first(d["design_class"] == "S"); d.loc[i, "conclusion_scope"] = "restricted"
    yield "S with restricted conclusion", d, sc
    d = df.copy(); m = (d["conflict_group"] == "threshold_limit") & (d["in_primary"] == "yes")
    d.loc[m, "direction"] = "lower"
    yield "single-direction conflict group", d, sc
    d = df.copy(); i = first(d["conflict_group"] != ""); d.loc[i, "direction"] = ""
    yield "conflict member without direction", d, sc
    d = df.copy(); i = first(d["design_class"] == "M"); d.loc[i, "m_averages_venues"] = "na"
    yield "M without averaging flag", d, sc
    s = sc.copy(); j = s.index[s["decision"] == "include"][0]; s.loc[j, "decision"] = "exclude"
    yield "primary study missing from screening", df.copy(), s
    d = df.copy(); sid = d.loc[first(d["design_class"] == "S"), "study_id"]
    d.loc[d["study_id"] == sid, "n_championships"] = "3"
    yield "S finding with 3 championships", d, sc


def json_corruptions(res: dict):
    def mut(fn):
        c = copy.deepcopy(res)
        fn(c)
        return c
    yield mut(lambda c: c["numbers"]["k_vulnerable_studies"].update(value=c["numbers"]["k_vulnerable_studies"]["value"] + 1))
    yield mut(lambda c: c["numbers"]["share_vulnerable_studies"].update(value=0.5))
    yield mut(lambda c: c["numbers"]["findings_class_P"].update(value=c["numbers"]["findings_class_P"]["value"] + 1))
    yield mut(lambda c: c["numbers"]["k_strict_studies"].update(value=c["numbers"]["k_vulnerable_studies"]["value"] + 1))
    yield mut(lambda c: c["numbers"]["n_conflict_groups"].update(value=c["numbers"]["n_conflict_groups"]["value"] + 1))
    yield mut(lambda c: c["tables"]["conflict_groups"][0].update(directions="positive: X"))
    yield mut(lambda c: c["numbers"]["n_findings"].update(value=c["numbers"]["n_findings"]["value"] - 1))
    yield mut(lambda c: c["numbers"]["findings_rule_era_class_E"].update(
        value=c["numbers"]["findings_rule_era_class_E"]["value"] - 1))


def test_guards_fire():
    df, sc = L.load(STUDIES), L.load(SCREEN)
    fired = []
    for label, d, s in coding_corruptions(df, sc):
        fired.append((label, bool(L.validate(d, s))))
    res = json.loads(OUT.read_text(encoding="utf-8"))
    rc = recount()
    for i, c in enumerate(json_corruptions(res)):
        fired.append((f"json corruption {i + 1}", bool(guard_problems(c, rc))))
    missed = [lab for lab, ok in fired if not ok]
    print(f"guards fired on corrupted input: {sum(ok for _, ok in fired)}/{len(fired)}")
    assert not missed, f"guards did not fire on: {missed}"


def test_cli_fails_on_corruption_and_reproduces():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        # corrupted CSV: flip one stored vulnerable flag -> the producer must refuse to write
        rows = list(csv.DictReader(STUDIES.open(encoding="utf-8", newline="")))
        for r in rows:
            if r["vulnerable"] == "yes":
                r["vulnerable"] = "no"
                break
        bad = tdp / "bad_studies.csv"
        with bad.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        cmd = [PY, CMD[0], "--studies", str(bad), *CMD[3:], "--out", str(tdp / "bad.json")]
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, creationflags=NOWIN)
        assert r.returncode != 0 and not (tdp / "bad.json").exists(), "producer accepted a corrupted coding"
        # clean rerun reproduces the shipped JSON byte for byte
        out = tdp / "lit_audit.json"
        r = subprocess.run([PY, *CMD, "--out", str(out)], cwd=ROOT, capture_output=True, text=True,
                           creationflags=NOWIN)
        assert r.returncode == 0, r.stderr
        assert out.read_bytes() == OUT.read_bytes(), "rerun differs from analysis/outputs/lit_audit.json"


if __name__ == "__main__":
    tests = [test_vulnerable_rule, test_shipped_coding_valid, test_independent_recount_matches_producer,
             test_result_json_guards, test_guards_fire, test_cli_fails_on_corruption_and_reproduces]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    sys.exit(1 if failed else 0)
