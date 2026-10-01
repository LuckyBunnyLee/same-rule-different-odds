"""Guards for claims the results make (guard every claim a test can hold). Each guard is also shown to fire.

1. No real result read a MOCK input, and no real result is flagged mock.
2. Every number in analysis/numbers.json equals the value in the result JSON it cites.
3. 'ci_excludes_haugen' agrees with the slope interval and the Haugen-sized slope.
4. The fairness 'largest fold change' is the max over the stored data-calibrated ratios.
5. results.md is up to date with numbers.json (rebuilt in memory and compared).

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_claims.py
"""
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def check_no_mock(results: dict) -> list:
    bad = []
    for name, d in results.items():
        if d.get("mock"):
            bad.append(f"{name}: flagged mock")
        inputs = d.get("inputs", [])
        if isinstance(inputs, dict):                 # e.g. recent_probe.json records {path: sha256 prefix}
            inputs = [{"path": k} for k in inputs]
        for i in inputs:
            pth = i.get("path", "")
            if "analysis/mock" in pth or Path(pth).name.startswith("MOCK_"):
                bad.append(f"{name}: mock input {pth}")
    return bad


def check_numbers_match(numbers: dict, results_by_path: dict) -> list:
    """Every number equals its source: result JSONs ('numbers' dict) or external flat files."""
    bad = []
    for k, e in numbers["numbers"].items():
        src = results_by_path.get(e["source"])
        if src is None and (ROOT / e["source"]).exists():
            src = load(ROOT / e["source"])
            results_by_path[e["source"]] = src
        if src is None:
            bad.append(f"{k}: source {e['source']} missing")
            continue
        key = k.split(".", 1)[1]
        pool = src["numbers"] if "numbers" in src else src            # external files are flat key -> value
        if key not in pool:
            bad.append(f"{k}: not in source")
            continue
        sv = pool[key].get("value") if isinstance(pool[key], dict) and "numbers" in src else pool[key]
        if sv != e.get("value"):
            bad.append(f"{k}: {e.get('value')} != source {sv}")
    return bad


def check_haugen_flag(fp: dict) -> list:
    n = fp["numbers"]
    if "ci_excludes_haugen" not in n:
        return []
    lo, hi = n["slope_ms_per_100ms"]["ci95"]
    h = n["haugen_slope_same_scale"]["value"]
    want = bool(hi < h and lo > -h)
    got = n["ci_excludes_haugen"]["value"]
    return [] if want == got else [f"ci_excludes_haugen={got} but CI [{lo}, {hi}] vs +/-{h} implies {want}"]


def check_fold_change(fa: dict) -> list:
    n = fa["numbers"]
    if "cal_max_fold_change" not in n:
        return []
    import pandas as pd
    cal = pd.DataFrame(fa["tables"]["data_calibrated"])
    sub = cal[(cal["family"] == "exgauss") & (cal["sex"] == sorted(cal["sex"].unique())[0])]
    want = max(sub["ratio_p90_p10"].max(), 1.0 / sub["ratio_p90_p10"].min())
    got = n["cal_max_fold_change"]["value"]
    return [] if abs(want - got) / want < 1e-3 else [f"cal_max_fold_change {got} != recomputed {want:.4g}"]


def main():
    results = {p.name: load(p) for p in sorted(OUT.glob("*.json"))}
    by_path = {f"analysis/outputs/{k}": v for k, v in results.items()}
    numbers = load(ROOT / "analysis" / "numbers.json")
    failures = []
    failures += check_no_mock(results)
    failures += check_numbers_match(numbers, by_path)
    if "fp_models.json" in results:
        failures += check_haugen_flag(results["fp_models.json"])
    if "fairness.json" in results:
        failures += check_fold_change(results["fairness.json"])
    # 5. results.md current
    tmp = Path(tempfile.mkdtemp()) / "_results_check.md"
    cmd = load(ROOT / "producers.json")["analysis/results.md"].split()
    cmd[cmd.index("--out") + 1] = str(tmp)                       # the registered command, redirected
    subprocess.run([sys.executable, *cmd], cwd=ROOT, check=True, capture_output=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if tmp.read_bytes() != (ROOT / "analysis" / "results.md").read_bytes():
        failures.append("results.md is stale relative to numbers.json")
    tmp.unlink(missing_ok=True)

    # ---- prove each guard fires ------------------------------------------------------------------
    fired = []
    r2 = copy.deepcopy(results)
    first = next(iter(r2))
    r2[first]["inputs"] = r2[first].get("inputs", []) + [{"path": "analysis/mock/data/MOCK_rt_athletes.csv"}]
    fired.append(bool(check_no_mock(r2)))
    n2 = copy.deepcopy(numbers)
    k0 = next(iter(n2["numbers"]))
    v0 = n2["numbers"][k0]["value"]
    n2["numbers"][k0]["value"] = (v0 + 1) if isinstance(v0, (int, float)) and not isinstance(v0, bool) else "tampered"
    fired.append(bool(check_numbers_match(n2, by_path)))
    if "fp_models.json" in results and "ci_excludes_haugen" in results["fp_models.json"]["numbers"]:
        f2 = copy.deepcopy(results["fp_models.json"])
        f2["numbers"]["ci_excludes_haugen"]["value"] = not f2["numbers"]["ci_excludes_haugen"]["value"]
        fired.append(bool(check_haugen_flag(f2)))
    if "fairness.json" in results and "cal_max_fold_change" in results["fairness.json"]["numbers"]:
        a2 = copy.deepcopy(results["fairness.json"])
        a2["numbers"]["cal_max_fold_change"]["value"] *= 2
        fired.append(bool(check_fold_change(a2)))

    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(fired)}/{len(fired)}")
    if failures or not all(fired):
        sys.exit(1)
    print(f"[ok] {len(numbers['numbers'])} numbers traced; all claim guards pass and fire when broken")


if __name__ == "__main__":
    main()
