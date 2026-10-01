"""Guards for the measurement pipeline's derived files and README claims.

Run: .venv/Scripts/python.exe -m pytest analysis/measure/tests -q
Paths can be redirected with environment variables (used to prove the guards fire on corrupted copies):
  FP_CSV, VS_CSV, SEIKO_JSON, NUMBERS_JSON, README_MD
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FP = Path(os.environ.get("FP_CSV", ROOT / "data/derived/foreperiods.csv"))
VS = Path(os.environ.get("VS_CSV", ROOT / "data/derived/video_sources.csv"))
SEIKO = Path(os.environ.get("SEIKO_JSON", ROOT / "analysis/measure/results/seiko_validation.json"))
NUMBERS = Path(os.environ.get("NUMBERS_JSON", ROOT / "analysis/measure/numbers.json"))
README = Path(os.environ.get("README_MD", ROOT / "analysis/measure/README.md"))
RACES = ROOT / "data/derived/races.csv"
METHODS = {"audio_auto_v1", "manual_override", "visual_override", "none"}


def test_foreperiods_schema_and_keys():
    fp = pd.read_csv(FP)
    need = {"race_id", "foreperiod_s", "set_onset_s", "gun_s", "method", "uncertainty_s", "qc_flag", "url", "notes"}
    assert need <= set(fp.columns), f"missing columns: {need - set(fp.columns)}"
    assert not fp.duplicated(["race_id", "attempt"]).any(), "duplicate (race_id, attempt) rows"
    races = set(pd.read_csv(RACES).race_id)
    bad = sorted(set(fp.race_id) - races)
    assert not bad, f"race_ids not in races.csv: {bad}"
    assert set(fp.method) <= METHODS, f"unknown methods: {set(fp.method) - METHODS}"


def test_foreperiod_values_plausible():
    fp = pd.read_csv(FP)
    v = fp.dropna(subset=["foreperiod_s"])
    out = v[(v.foreperiod_s < 0.8) | (v.foreperiod_s > 4.0)]
    assert out.empty, f"implausible foreperiods (outside 0.8-4.0 s):\n{out[['race_id', 'attempt', 'foreperiod_s']]}"
    assert (v.uncertainty_s > 0).all(), "every measured foreperiod needs a positive uncertainty"
    assert ((v.gun_s - v.set_onset_s - v.foreperiod_s).abs() < 1e-3).all(), "foreperiod != gun - set onset"
    none = fp[fp.method == "none"]
    assert none.foreperiod_s.isna().all(), "method 'none' rows must not carry a foreperiod"


def test_video_sources_keys():
    vs = pd.read_csv(VS)
    races = set(pd.read_csv(RACES).race_id)
    bad = sorted(set(vs.race_id) - races)
    assert not bad, f"race_ids not in races.csv: {bad}"
    assert vs.url.str.startswith("https://www.youtube.com/watch?v=").all()
    measured = set(pd.read_csv(FP).race_id)
    listed = set(vs[vs.status == "measured"].race_id)
    assert measured <= listed, f"measured races without a source row: {sorted(measured - listed)}"


def test_readme_claim_ready_time_never_matches_onset():
    """README: 'on every compared race Ready Time is shorter than the acoustic onset-to-gun interval and it does
    not match the onset within 40 ms on any race'."""
    s = json.load(open(SEIKO, encoding="utf-8"))
    on = s["manual"]["onset_minus_ready"]
    assert on["within_40ms"] == 0.0, "some race matches the onset within 40 ms: README claim is false"
    assert on["min_s"] > 0.04, "Ready Time is not shorter than the onset foreperiod on every race"


def test_synthetic_numbers_are_labelled():
    n = json.load(open(NUMBERS, encoding="utf-8"))
    for k in n:
        if k.startswith("_"):
            continue
        assert k.startswith("real_") or k.startswith("synthetic_"), f"number key without real_/synthetic_ label: {k}"
    txt = README.read_text(encoding="utf-8")
    i = txt.index("### (a) Synthetic benchmark")
    assert "SIMULATED" in txt[i:i + 200], "synthetic section heading must say SIMULATED"


def test_readme_claim_qcok_slope_near_one():
    """README: 'among automated measurements with qc_flag == ok, the OLS slope of Ready Time on the onset
    foreperiod is close to 1' (and the all-starts slope is lower because of Ready-Time outliers)."""
    s = json.load(open(SEIKO, encoding="utf-8"))
    q = s["automated_all_measured_valid"]["qc_ok_corr_ready_vs_fp_onset"]
    assert q["n"] >= 10, "too few QC-ok starts to support the claim"
    assert 0.8 <= q["ols_ready_on_fp_slope"] <= 1.2, f"QC-ok slope {q['ols_ready_on_fp_slope']} is not close to 1"
    allv = s["final_dataset_valid"]["corr_ready_vs_fp_onset"]
    assert allv["ols_ready_on_fp_slope"] < q["ols_ready_on_fp_slope"], "all-starts slope not lower than QC-ok slope"
