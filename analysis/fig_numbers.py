"""Numbers shown in the confound figure (analysis/make_figures.py --fig confound), keys 'fig.*'.

fit_* : for each fixed line (the 0.100 s rule; 0.094 s, Fiore et al. 2025; 0.115 s, Brosnan et al. 2017, men), the
        number of championships whose 95% CI of the 1-in-1,000 barrier contains it (men, ex-Gaussian, race-cluster
        bootstrap; systematic.json table h2_per_championship). Kept as registered numbers; no longer drawn.
barrier_below_rule / barrier_above_rule : panel B colours the championships by these.
p1_unflagged_rt_min_s / _max_s : the RT range of the recorded false starts a uniform guard band would no longer flag
        (guardband.json table false_starts); cited in the results.md caption, not drawn (panel C states the count).
Generated here so the figure and any prose cite the same registered numbers. Line positions are literature constants.

Usage: .venv\\Scripts\\python.exe analysis\\fig_numbers.py --systematic analysis/outputs/systematic.json
           --guardband analysis/outputs/guardband.json --out analysis/outputs/fig.json
"""
from __future__ import annotations

import _env  # noqa: F401

import argparse
import json
from pathlib import Path

import pandas as pd

from common import num, write_result

LINES_MS = {"rule_100ms": (100.0, "the 0.100 s rule"),
            "fiore_094ms": (94.0, "0.094 s (Fiore et al. 2025)"),
            "brosnan_115ms": (115.0, "0.115 s (Brosnan et al. 2017, men)")}


def barrier_table(sysj: dict) -> pd.DataFrame:
    ch = pd.DataFrame(sysj["tables"]["h2_per_championship"])
    ch = ch[(ch["sex"] == "M") & ch["eligible"].astype(bool)]
    return ch[["comp_year", "barrier_ms_exgauss", "barrier_exgauss_lo", "barrier_exgauss_hi"]].sort_values(
        ["barrier_ms_exgauss", "comp_year"]).reset_index(drop=True)


def counts(ch: pd.DataFrame) -> dict:
    n = len(ch)
    lo, hi, b = ch["barrier_exgauss_lo"], ch["barrier_exgauss_hi"], ch["barrier_ms_exgauss"]
    out = {}
    fits_any = pd.Series(False, index=ch.index)
    for key, (ms, lab) in LINES_MS.items():
        fit = (lo <= ms) & (ms <= hi)
        fits_any |= fit
        out[f"fit_{key}"] = num(int(fit.sum()), desc=f"confound figure panel B: championships whose 95% CI of the 1-in-1,000 "
                                                     f"barrier (men, ex-Gaussian) contains {lab}", n_champs=n,
                                champs=ch.loc[fit, "comp_year"].tolist(), line_ms=ms)
    out["fit_none"] = num(int((~fits_any).sum()), desc="confound figure panel B: championships whose barrier CI contains "
                                                       "none of the three lines", n_champs=n,
                          champs=ch.loc[~fits_any, "comp_year"].tolist())
    below = b < LINES_MS["rule_100ms"][0]
    out["barrier_below_rule"] = num(int(below.sum()), desc="confound figure panel B: championships whose barrier lies "
                                                           "below 0.100 s (the rule flags more than 1 in 1,000 "
                                                           "legitimate starts there)", n_champs=n,
                                    champs=ch.loc[below, "comp_year"].tolist())
    out["barrier_above_rule"] = num(int((~below).sum()), desc="confound figure panel B: championships whose barrier lies "
                                                              "at or above 0.100 s", n_champs=n,
                                    champs=ch.loc[~below, "comp_year"].tolist())
    return out


def guard_cost(gj: dict) -> dict:
    """Panel C cost annotation: RT range of the recorded false starts a uniform guard band (P1) no longer flags."""
    t = pd.DataFrame(gj["tables"]["false_starts"])
    u = t[t["unflagged_p1"].astype(bool) & t["in_primary_set"].astype(bool)]
    if u.empty:
        return {}
    common = dict(n_unflagged=int(len(u)), unflagged_champs=sorted(u["comp_year"].unique().tolist()))
    return {"p1_unflagged_rt_min_s": num(float(u["rt_s"].min()), unit="s", desc="guard band cost (caption; not drawn): shortest RT among "
                                         "the recorded false starts a uniform guard band (P1) would no longer flag", **common),
            "p1_unflagged_rt_max_s": num(float(u["rt_s"].max()), unit="s", desc="guard band cost (caption; not drawn): longest RT among "
                                         "the recorded false starts a uniform guard band (P1) would no longer flag", **common)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--systematic", required=True)
    ap.add_argument("--guardband", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sysj = json.loads(Path(a.systematic).read_text(encoding="utf-8"))
    gj = json.loads(Path(a.guardband).read_text(encoding="utf-8"))
    numbers = counts(barrier_table(sysj))
    numbers.update(guard_cost(gj))
    p = write_result(a.out, "fig", numbers, [Path(a.systematic), Path(a.guardband)], False,
                     extra={"lines_ms": {k: v[0] for k, v in LINES_MS.items()}})
    for k, v in numbers.items():
        print(f"{k:24s} {v['value']}  {v.get('champs')}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
