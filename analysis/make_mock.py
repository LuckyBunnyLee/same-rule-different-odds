"""Generate SYNTHETIC MOCK inputs with the same schemas as the real data/derived files.

MOCK DATA ONLY - used to build and test the analysis code before real data exist.
Files are written to analysis/mock/data/MOCK_*.csv and every row carries is_mock=1.
The ground truth is saved to analysis/mock/data/MOCK_truth.json so the model code can be
checked for parameter recovery. Nothing produced from these files may enter results.md.

Usage:  .venv\\Scripts\\python.exe analysis\\make_mock.py [--seed N]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

import hazard as hz
from common import MOCK_DATA

TRUTH = {
    "note": "MOCK ground truth - synthetic, not a result",
    "rt_intercept_s": 0.150,
    "sex_W_s": 0.006, "round_SF_s": -0.002, "round_F_s": -0.004, "round_PR_s": 0.003,
    "event_200m_s": 0.003, "event_hurdles_s": 0.004,
    "sd_comp_s": 0.008, "sd_race_s": 0.005, "sd_athlete_s": 0.010,
    "resid_sigma_s": 0.010, "resid_tau_s": 0.010,
    "fp_linear_s_per_s": -0.012,           # -1.2 ms per 100 ms
    "fp_hazard_coef_s_per_unit": -0.0015,  # extra shift per unit subjective hazard (1/s)
    "hazard_phi": 0.25,
    "fp_mean_s": 1.80, "fp_sd_s": 0.22, "fp_lo_s": 1.25, "fp_hi_s": 2.60,
    "fp_measured_share": 0.7, "fp_uncertainty_s": 0.02,
}

COMPS = [("WCH", y) for y in (2009, 2011, 2013, 2015, 2017, 2019, 2022, 2023)] + \
        [("OG", y) for y in (2012, 2016, 2021, 2024)]
EVENTS = {"M": ["100m", "200m", "110mH"], "W": ["100m", "200m", "100mH"]}
HEATS = {"PR": 2, "R1": 6, "SF": 3, "F": 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    T = TRUTH
    MOCK_DATA.mkdir(parents=True, exist_ok=True)

    # population subjective hazard used by the synthetic truth
    pop_pdf = hz.truncnorm_pdf(hz.GRID, T["fp_mean_s"], T["fp_sd_s"], T["fp_lo_s"], T["fp_hi_s"])
    h_pop = hz.hazard_curve(pdf=pop_pdf, phi=T["hazard_phi"])
    h_ref = np.interp(T["fp_mean_s"], hz.GRID, h_pop)

    pools = {(s, e): [f"MOCK ATHLETE {s}{e}-{i:03d}" for i in range(70)]
             for s in EVENTS for e in EVENTS[s]}
    ath_eff = {a: rng.normal(0, T["sd_athlete_s"]) for pool in pools.values() for a in pool}

    rows, races, fps = [], [], []
    for comp, year in COMPS:
        comp_eff = rng.normal(0, T["sd_comp_s"])
        starter_shift = rng.normal(0, 0.08)
        for sex, evs in EVENTS.items():
            for ev in evs:
                pool = pools[(sex, ev)]
                rounds = ["PR", "R1", "SF", "F"] if (ev == "100m" and year >= 2015) else ["R1", "SF", "F"]
                field = list(rng.choice(pool, size=8 * HEATS["R1"], replace=False))
                for rnd in rounds:
                    n_heats = HEATS[rnd]
                    if rnd == "PR":
                        entrants = [f"MOCK PR {sex}{ev}{year}-{i}" for i in range(8 * n_heats)]
                        for a in entrants:
                            ath_eff.setdefault(a, rng.normal(0.004, T["sd_athlete_s"]))
                    elif rnd == "R1":
                        entrants = field
                    elif rnd == "SF":
                        entrants = list(rng.choice(field, size=24, replace=False))
                        field = entrants
                    else:
                        entrants = list(rng.choice(field, size=8, replace=False))
                    for h in range(n_heats):
                        heat_ath = entrants[h * 8:(h + 1) * 8]
                        if rnd in ("R1", "PR") and rng.random() < 0.2:
                            heat_ath = heat_ath[:7]
                        race_id = f"{comp}{year}-{ev}-{sex}-{rnd}-H{h + 1}"
                        fp = float(hz.pdf_sample(hz.GRID, hz.truncnorm_pdf(
                            hz.GRID, T["fp_mean_s"] + starter_shift, T["fp_sd_s"],
                            T["fp_lo_s"], T["fp_hi_s"]), 1, rng)[0])
                        h_fp = float(np.interp(fp, hz.GRID, h_pop))
                        race_eff = rng.normal(0, T["sd_race_s"])
                        fp_eff = (T["fp_linear_s_per_s"] * (fp - T["fp_mean_s"]) +
                                  T["fp_hazard_coef_s_per_unit"] * (h_fp - h_ref))
                        day = 1 + ["PR", "R1", "SF", "F"].index(rnd) + (0 if sex == "M" else 1)
                        races.append({"race_id": race_id, "comp": comp, "year": year, "event": ev,
                                      "sex": sex, "round": rnd, "heat": h + 1,
                                      "date": f"{year}-08-{day:02d}",
                                      "session": f"{comp}{year}-D{day}-{'AM' if rnd in ('PR', 'R1') else 'PM'}",
                                      "n_athletes": len(heat_ath), "is_mock": 1})
                        if rng.random() < T["fp_measured_share"]:
                            fps.append({"race_id": race_id,
                                        "foreperiod_s": round(fp + rng.normal(0, T["fp_uncertainty_s"]), 3),
                                        "uncertainty_s": T["fp_uncertainty_s"],
                                        "qc_flag": "ok" if rng.random() < 0.9 else "low_confidence",
                                        "method": "MOCK", "is_mock": 1})
                        for lane, a in enumerate(heat_ath, start=2):
                            mu = (T["rt_intercept_s"] + (T["sex_W_s"] if sex == "W" else 0) +
                                  T.get(f"round_{rnd}_s", 0.0) +
                                  (T["event_200m_s"] if ev == "200m" else 0) +
                                  (T["event_hurdles_s"] if "H" in ev else 0) +
                                  comp_eff + race_eff + ath_eff[a] + fp_eff)
                            rt = mu + rng.normal(0, T["resid_sigma_s"]) + rng.exponential(T["resid_tau_s"])
                            rt -= T["resid_tau_s"]  # keep the mean near mu
                            status = ""
                            if rng.random() < 0.004:   # anticipatory false start
                                rt = rng.uniform(0.02, 0.099)
                                status = "DQ TR16.8"
                            elif rt < 0.100:
                                status = "DQ TR16.8"
                            rows.append({"race_id": race_id, "comp": comp, "year": year, "event": ev,
                                         "sex": sex, "round": rnd, "heat": h + 1, "lane": lane,
                                         "athlete": a, "rt_s": round(rt, 3), "status": status,
                                         "source_url": "MOCK", "is_mock": 1})
    rt = pd.DataFrame(rows)
    rt.to_csv(MOCK_DATA / "MOCK_rt_athletes.csv", index=False)
    # Fiore-like subset: Worlds only, no names
    fio = rt[rt["comp"] == "WCH"].drop(columns=["athlete", "lane"]).copy()
    fio.to_csv(MOCK_DATA / "MOCK_rt_fiore.csv", index=False)
    pd.DataFrame(races).to_csv(MOCK_DATA / "MOCK_races.csv", index=False)
    pd.DataFrame(fps).to_csv(MOCK_DATA / "MOCK_foreperiods.csv", index=False)
    (MOCK_DATA / "MOCK_truth.json").write_text(json.dumps(TRUTH, indent=2))
    print(f"MOCK data written to {MOCK_DATA}: {len(rt)} RT rows, {len(races)} races, "
          f"{len(fps)} foreperiods")


if __name__ == "__main__":
    main()
