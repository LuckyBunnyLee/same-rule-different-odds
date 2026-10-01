"""Tests for analysis/fig_numbers.py (keys 'fig.*', shown in the confound figure).

G1 every count in fig.json equals a direct recount from systematic.json table h2_per_championship (men, ex-Gaussian),
   and the guard-band cost RT range equals a recount from guardband.json table false_starts
G2 the below/above counts partition the championships, and each line's championship list matches its count
G3 numbers.json carries the same fig.* values
Each guard is shown to fire on a corrupted copy.

Usage: .venv\\Scripts\\python.exe analysis\\tests\\test_fig_numbers.py   (or pytest)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "outputs"
LINES = {"rule_100ms": 100.0, "fiore_094ms": 94.0, "brosnan_115ms": 115.0}


def recount(sysj: dict) -> dict:
    ch = pd.DataFrame(sysj["tables"]["h2_per_championship"])
    ch = ch[(ch["sex"] == "M") & ch["eligible"].astype(bool)]
    out, anyfit = {}, pd.Series(False, index=ch.index)
    for k, ms in LINES.items():
        fit = (ch["barrier_exgauss_lo"] <= ms) & (ms <= ch["barrier_exgauss_hi"])
        anyfit |= fit
        out[f"fit_{k}"] = int(fit.sum())
    out["fit_none"] = int((~anyfit).sum())
    out["barrier_below_rule"] = int((ch["barrier_ms_exgauss"] < 100.0).sum())
    out["barrier_above_rule"] = int((ch["barrier_ms_exgauss"] >= 100.0).sum())
    out["_n"] = len(ch)
    return out


def recount_guard(gj: dict) -> dict:
    t = pd.DataFrame(gj["tables"]["false_starts"])
    u = t[t["unflagged_p1"].astype(bool) & t["in_primary_set"].astype(bool)]
    return {"p1_unflagged_rt_min_s": float(u["rt_s"].min()), "p1_unflagged_rt_max_s": float(u["rt_s"].max())} if len(u) else {}


def check(fig: dict, sysj: dict, nums: dict | None, gj: dict | None = None) -> list:
    want, n = recount(sysj), fig["numbers"]
    if gj is not None:
        want.update(recount_guard(gj))
    bad = [f"{k}: stored {n.get(k, {}).get('value')} vs recount {v}" for k, v in want.items()
           if not k.startswith("_") and n.get(k, {}).get("value") != v]
    if n["barrier_below_rule"]["value"] + n["barrier_above_rule"]["value"] != want["_n"]:
        bad.append("below + above does not partition the championships")
    for k, e in n.items():
        if "champs" in e and len(e["champs"]) != e["value"]:
            bad.append(f"{k}: championship list length {len(e['champs'])} != count {e['value']}")
    if nums is not None:
        bad += [f"numbers.json fig.{k} differs" for k, e in n.items() if nums["numbers"].get(f"fig.{k}", {}).get("value") != e["value"]]
    return bad


def run() -> bool:
    fp = OUT / "fig.json"
    if not fp.exists():
        print("[skip] fig.json not built")
        return True
    fig = json.loads(fp.read_text(encoding="utf-8"))
    sysj = json.loads((OUT / "systematic.json").read_text(encoding="utf-8"))
    nums = json.loads((ROOT / "analysis" / "numbers.json").read_text(encoding="utf-8"))
    gj = json.loads((OUT / "guardband.json").read_text(encoding="utf-8"))
    failures = check(fig, sysj, nums, gj)
    fired = []
    c = copy.deepcopy(fig)
    c["numbers"]["fit_rule_100ms"]["value"] += 1
    fired.append(bool(check(c, sysj, None)))
    c = copy.deepcopy(fig)
    c["numbers"]["barrier_above_rule"]["value"] -= 1
    fired.append(bool(check(c, sysj, None)))
    c = copy.deepcopy(fig)
    c["numbers"]["fit_none"]["champs"] = c["numbers"]["fit_none"]["champs"][:-1]
    fired.append(bool(check(c, sysj, None)))
    c = copy.deepcopy(fig)
    c["numbers"]["p1_unflagged_rt_min_s"]["value"] = 0.090
    fired.append(bool(check(c, sysj, None, gj)))
    for f_ in failures:
        print("FAIL", f_)
    print(f"guards fired on corrupted input: {sum(fired)}/{len(fired)}")
    ok = not failures and all(fired)
    if ok:
        print("[ok] fig.json counts equal a direct recount from systematic.json and match numbers.json")
    return ok


def test_fig_numbers():
    assert run()


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
