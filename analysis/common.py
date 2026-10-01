"""Shared paths, loaders, provenance and plotting helpers for the SSAC27 foreperiod analysis.

Design rules:

* Real inputs live in ``data/derived/`` (owned by the RT-data and measurement pipelines).
* Mock inputs live in ``analysis/mock/data/`` and are always named ``MOCK_*.csv``; mock
  outputs go to ``analysis/mock/``. ``write_result`` refuses to write a real-mode result that
  read a mock file, and ``make_numbers.py`` refuses any JSON whose ``mock`` flag is true, so
  mock numbers cannot reach ``analysis/numbers.json`` or ``analysis/results.md``.
* Every compute script writes exactly one JSON to ``--out``. The JSON is deterministic
  (no timestamps, run times, absolute paths or git hashes; floats rounded to 6 significant
  digits) so ``scripts/verify_producers.py`` can re-run the registered command and compare
  bytes. Data versions are recorded as sha256 prefixes and row counts of every input.
  The producing command lives in ``producers.json`` (single source of truth).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
DERIVED = ROOT / "data" / "derived"
OUTPUTS = ANALYSIS / "outputs"
FIGURES = ANALYSIS / "figures"
MOCK_DIR = ANALYSIS / "mock"
MOCK_DATA = MOCK_DIR / "data"
VENV_PY = r".venv\Scripts\python.exe"

RT_FILES = ("rt_athletes.csv", "rt_fiore.csv")
RACES_FILE = "races.csv"
FP_FILE = "foreperiods.csv"

# World Athletics false-start threshold (TR16.6 / formerly Rule 162.6), seconds.
FS_THRESHOLD = 0.100

# ----------------------------------------------------------------------------------
# paths
# ----------------------------------------------------------------------------------

def default_out(name: str, mock: bool) -> Path:
    return (MOCK_DIR / "outputs" / f"{name}.json") if mock else (OUTPUTS / f"{name}.json")


def data_path(name: str, mock: bool) -> Path:
    return (MOCK_DATA / f"MOCK_{name}") if mock else (DERIVED / name)


def is_mock_path(p: Path | str) -> bool:
    p = Path(p).resolve()
    return MOCK_DIR.resolve() in p.parents or p.name.startswith("MOCK_")


# ----------------------------------------------------------------------------------
# provenance
# ----------------------------------------------------------------------------------

def file_version(p: Path) -> dict:
    """Deterministic data version of one input: repo-relative path, sha256 prefix, rows."""
    p = Path(p)
    if not p.exists():
        return {"path": rel(p), "exists": False}
    info = {"path": rel(p), "exists": True,
            "sha256_12": hashlib.sha256(p.read_bytes()).hexdigest()[:12]}
    if p.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
            info["rows"] = int(len(df))
            for vc in ("data_version", "version", "dataset_version"):
                if vc in df.columns and df[vc].notna().any():
                    info["declared_version"] = str(df[vc].dropna().iloc[0])
        except Exception as e:  # provenance must never crash a run
            info["read_error"] = type(e).__name__
    return info


def version_tag(v: dict) -> str:
    if not v.get("exists", False):
        return f"{Path(v['path']).name} (missing)"
    s = f"{Path(v['path']).name}@sha256:{v['sha256_12']}"
    if "rows" in v:
        s += f" ({v['rows']} rows)"
    return s


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return Path(p).name


def write_result(out: Path | str, name: str, numbers: dict, inputs: Iterable[Path], mock: bool,
                 tables: dict | None = None, extra: dict | None = None,
                 seed: int | None = None) -> Path:
    """Write the deterministic result JSON to ``out``.

    ``numbers``: key -> dict(value, ci95, desc, unit, ...) - every quantity that may be quoted.
    ``tables``:  name -> list of records (figure and table sources).
    """
    inputs = [Path(p) for p in inputs]
    if not mock:
        bad = [str(p) for p in inputs if is_mock_path(p)]
        if bad:
            raise RuntimeError(f"Refusing to write a real result that used mock inputs: {bad}")
    payload = {"name": name, "mock": bool(mock), "seed": seed,
               "inputs": [file_version(p) for p in inputs],
               "numbers": _jsonable(numbers)}
    if tables:
        payload["tables"] = {k: _jsonable(_records(v)) for k, v in tables.items()}
    if extra:
        payload["extra"] = _jsonable(extra)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _records(v):
    if isinstance(v, pd.DataFrame):
        return v.to_dict(orient="records")
    return v


def _round(x: float, sig: int = 6):
    if x == 0 or not np.isfinite(x):
        return float(x) if np.isfinite(x) else None
    return float(f"{x:.{sig}g}")


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return _round(float(o))
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if o is pd.NA or o is pd.NaT:
        return None
    return o


def num(value, ci=None, desc: str = "", unit: str = "", **kw) -> dict:
    d = {"value": value, "desc": desc, "unit": unit}
    if ci is not None:
        d["ci95"] = list(ci)
    d.update(kw)
    return d


# ----------------------------------------------------------------------------------
# schema normalisation
# ----------------------------------------------------------------------------------

RACE_ID_RE = re.compile(
    r"^(?P<comp>[A-Za-z]+)(?P<year>\d{4})-(?P<event>\d{2,3}m(?:H)?)-(?P<sex>[MWF])-(?P<round>[A-Za-z0-9]+)-(?P<heat>.+)$")

_EVENT_MAP = {
    "100m": "100m", "100": "100m", "100 dash": "100m", "100 metres": "100m", "100 m": "100m",
    "200m": "200m", "200": "200m", "200 dash": "200m", "200 metres": "200m", "200 m": "200m",
    "100mh": "100mH", "100 hurdles": "100mH", "100m hurdles": "100mH", "100 metres hurdles": "100mH",
    "110mh": "110mH", "110 hurdles": "110mH", "110m hurdles": "110mH", "110 metres hurdles": "110mH",
    "60m": "60m", "60 m": "60m", "60 metres": "60m", "60mh": "60mH", "60m hurdles": "60mH", "60 metres hurdles": "60mH",
}
_SEX_MAP = {"m": "M", "men": "M", "male": "M", "w": "W", "f": "W", "women": "W", "female": "W"}
_ROUND_MAP = {"h": "R1", "heat": "R1", "heats": "R1", "r1": "R1", "round 1": "R1", "1st round": "R1",
              "r2": "R2", "qf": "R2", "quarterfinal": "R2", "quarter-final": "R2", "q": "R2",
              "s": "SF", "sf": "SF", "semi": "SF", "semifinal": "SF", "semi-final": "SF",
              "f": "F", "final": "F", "pr": "PR", "preliminary": "PR", "prelim": "PR",
              "rp": "RP", "repechage": "RP"}
ROUND_ORDER = ["PR", "R1", "RP", "R2", "SF", "F"]
EVENT_ORDER = ["100m", "200m", "100mH", "110mH", "60m", "60mH"]


def _find(df: pd.DataFrame, cands: Iterable[str]) -> str | None:
    low = {str(c).lower().strip(): c for c in df.columns}
    for c in cands:
        if c.lower() in low:
            return low[c.lower()]
    return None


def _norm_event(x) -> str | float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    return _EVENT_MAP.get(s.lower(), s)


def _norm_sex(x):
    if pd.isna(x):
        return np.nan
    return _SEX_MAP.get(str(x).strip().lower(), str(x).strip())


def _norm_round(x):
    if pd.isna(x):
        return np.nan
    return _ROUND_MAP.get(str(x).strip().lower(), str(x).strip().upper())


def parse_race_id(race_id: pd.Series) -> pd.DataFrame:
    parts = race_id.astype(str).str.extract(RACE_ID_RE)
    parts["year"] = pd.to_numeric(parts["year"], errors="coerce")
    parts["sex"] = parts["sex"].map(_norm_sex)
    return parts


def normalize_rt(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Map an athlete-level RT table onto the canonical schema.

    Canonical columns: race_id, comp, year, comp_year, event, event_type, sex, round, heat,
    rt_s, athlete, athlete_key, status, is_dq, is_fs, is_dns, lane, result, source.
    Descriptors are coalesced across candidate columns and, failing that, parsed from
    ``race_id``. Rows without a race_id (e.g. Fiore rows not matched to a WA heat) get a
    synthetic key ``{comp}{year}-{event}-{sex}-{round}-B{batch}`` built from their own heat
    fields, so clustering by race stays correct. RTs recorded in ms are converted to s.
    """
    d = df.copy()
    out = pd.DataFrame(index=d.index)
    rid = _find(d, ["race_id", "raceid"])
    rid_s = d[rid].where(d[rid].notna() & (d[rid].astype(str).str.strip() != ""), np.nan) if rid \
        else pd.Series(np.nan, index=d.index, dtype=object)
    parsed = parse_race_id(rid_s.fillna("").astype(str))

    def coalesce(names, parsed_col=None, fn=None):
        s = pd.Series(np.nan, index=d.index, dtype=object)
        for n in names:
            c = _find(d, [n])
            if c is not None:
                s = s.where(s.notna(), d[c])
        if parsed_col is not None and parsed_col in parsed:
            s = s.where(s.notna(), parsed[parsed_col])
        return s.map(fn, na_action="ignore") if fn else s

    out["comp"] = coalesce(["comp", "competition", "meet", "championship"], "comp")
    out["year"] = pd.to_numeric(coalesce(["year", "season"], "year"), errors="coerce")
    out["event"] = coalesce(["event", "discipline"], "event", _norm_event)
    out["sex"] = coalesce(["sex", "gender"], "sex", _norm_sex)
    out["round"] = coalesce(["round", "round_guess", "stage", "rnd"], "round", _norm_round)
    out["heat"] = coalesce(["heat", "batch", "heat_no", "race_no"], "heat")

    rtc = _find(d, ["rt_s", "rt", "reaction_time_s", "reaction_time", "reactiontime", "react_s",
                    "react", "rt_sec", "reaction"])
    if rtc is None:
        raise ValueError(f"{source}: no reaction-time column among {list(d.columns)}")
    rt = pd.to_numeric(d[rtc], errors="coerce")
    if rt.dropna().median() > 1.0:  # recorded in ms
        rt = rt / 1000.0
    # An RT of exactly 0.000 is a missing-value placeholder (the Fiore et al. file codes DNS rows and DQ rows whose
    # negative RT was dropped that way), not a measured reaction (fixed 2026-09-30; see notes/bugfix_rerun_diff.md).
    rt_placeholder = rt == 0.0
    rt = rt.mask(rt_placeholder)
    out["rt_s"] = rt

    ac = _find(d, ["athlete_id", "athlete", "name", "athlete_name", "competitor"])
    if ac:
        a = d[ac]
        out["athlete"] = a.where(a.notna(), np.nan).map(lambda z: str(z).strip().upper(), na_action="ignore")
    else:
        out["athlete"] = np.nan
    sc = _find(d, ["status", "result_status", "mark_status", "remark", "dq"])
    status = d[sc].fillna("").astype(str) if sc else pd.Series("", index=d.index)
    out["status"] = status
    fs_flag = _find(d, ["is_false_start", "false_start", "is_dq", "dq_flag"])
    is_dq = status.str.contains(r"\bDQ\b|TR16|162\.7|FALSE|\bFS\b", case=False, regex=True, na=False)
    if fs_flag:
        is_dq = is_dq | d[fs_flag].astype(str).str.lower().isin(["1", "true", "yes", "y"])
    out["is_dq"] = is_dq
    tc = _find(d, ["result", "time", "mark", "totaltime", "result_s"])
    result_txt = d[tc].fillna("").astype(str).str.strip().str.upper() if tc else pd.Series("", index=d.index)
    # DNS from the status, or from the result field where a file has no status column (Fiore et al.: TotalTime)
    out["is_dns"] = (status.str.contains(r"\bDNS\b", case=False, regex=True, na=False) | result_txt.eq("DNS"))
    # False start: any measured RT below the threshold (by rule), an explicit label, or a DQ whose RT is the 0.000
    # placeholder (Fiore et al. dropped negative RTs). DQs for other reasons (hurdle/lane rules, annulled results)
    # keep a legal RT: their notes say "(not a false start)", a phrase removed before matching false-start labels
    # (fixed 2026-09-30: the regex 'false.?start' used to match inside it).
    txt = status.copy()
    for extra_c in ("notes", "dq_reason", "reason", "rule", "pdf_rule", "row_note"):
        c2 = _find(d, [extra_c])
        if c2 is not None and c2 != sc:
            txt = txt + " " + d[c2].fillna("").astype(str)
    txt = txt.str.replace(r"\(?\s*\bnot\s+an?\s+false[\s-]?start\b\s*\)?", " ", case=False, regex=True)
    explicit_fs = txt.str.contains(r"TR16\.8|162\.7|false.?start|\bFS\b", case=False, regex=True, na=False)
    out["is_fs"] = explicit_fs | (rt < FS_THRESHOLD) | (rt_placeholder & result_txt.eq("DQ"))
    lc = _find(d, ["lane"])
    out["lane"] = pd.to_numeric(d[lc], errors="coerce") if lc else np.nan
    out["result"] = d[tc] if tc else np.nan
    out["source"] = source

    out["comp"] = out["comp"].fillna("WCH") if source == "rt_fiore" else out["comp"]
    synth = (out["comp"].astype(str) + out["year"].astype("Int64").astype(str) + "-" +
             out["event"].astype(str) + "-" + out["sex"].astype(str) + "-" +
             out["round"].astype(str) + "-B" + out["heat"].astype(str))
    out["race_id"] = rid_s.where(rid_s.notna(), synth).astype(str)
    out["race_id_synthetic"] = rid_s.isna()
    out["comp_year"] = out["comp"].astype(str) + out["year"].astype("Int64").astype(str)
    # Event type for models. World Indoors contribute only 60 m / 60 m hurdles, and those events occur
    # nowhere else, so separate indoor levels would be collinear with the championship effect; indoor
    # races therefore share the flat / hurdles levels and the championship effect absorbs indoor-outdoor
    # differences.
    out["event_type"] = out["event"].map({"100m": "flat", "60m": "flat", "200m": "200m", "100mH": "hurdles",
                                          "110mH": "hurdles", "60mH": "hurdles"})
    out["athlete_key"] = np.where(out["athlete"].notna(),
                                  out["athlete"].astype(str) + "|" + out["sex"].astype(str), None)
    # carry through any extra provenance columns
    for extra in ("source_url", "retrieved", "retrieval_date", "timing_system", "venue", "date",
                  "session", "session_id", "country", "nat", "wind"):
        c = _find(d, [extra])
        if c is not None and extra not in out:
            out[extra] = d[c]
    return out


def load_rt(mock: bool, which: str = "all") -> tuple[pd.DataFrame, list[Path]]:
    """Load the athlete-level RT tables that exist. ``which`` in {all, athletes, fiore}."""
    frames, used = [], []
    names = {"all": RT_FILES, "athletes": ("rt_athletes.csv",), "fiore": ("rt_fiore.csv",)}[which]
    for n in names:
        p = data_path(n, mock)
        if p.exists():
            raw = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
            frames.append(normalize_rt(raw, source=n.replace(".csv", "")))
            used.append(p)
    if not frames:
        return pd.DataFrame(), used
    return pd.concat(frames, ignore_index=True), used


def dedupe_sources(rt: pd.DataFrame) -> pd.DataFrame:
    """Where rt_athletes and rt_fiore both cover a championship x event x sex, keep the named
    (rt_athletes) rows. Matching on this level, not race_id, is robust to heat numbering."""
    if rt.empty or rt["source"].nunique() < 2:
        return rt
    key = rt["comp_year"].astype(str) + "|" + rt["event"].astype(str) + "|" + rt["sex"].astype(str)
    named = set(key[rt["source"] == "rt_athletes"])
    keep = (rt["source"] == "rt_athletes") | (~key.isin(named))
    return rt.loc[keep].reset_index(drop=True)


def attach_races(rt: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
    """Add race-level columns (timing system, date, restart counts...) from races.csv."""
    if races is None or races.empty or rt.empty:
        return rt
    cols = [c for c in ("timing", "date", "sched_start_local", "n_fs", "n_dq", "dq_detail",
                        "waveform_url", "session", "session_id") if c in races.columns]
    r = races[["race_id"] + cols].drop_duplicates("race_id")
    r = r.rename(columns={c: f"race_{c}" for c in cols})
    return rt.merge(r, on="race_id", how="left")


GOOD_QC = {"ok", "good", "pass", "passed", "valid", "1", "true", "clean", "high", "a"}


def load_foreperiods(mock: bool) -> tuple[pd.DataFrame, list[Path]]:
    p = data_path(FP_FILE, mock)
    if not p.exists():
        return pd.DataFrame(), []
    d = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    rid = _find(d, ["race_id"])
    fpc = _find(d, ["foreperiod_s", "foreperiod", "hold_s", "hold_time_s", "fp_s"])
    if rid is None or fpc is None:
        raise ValueError(f"foreperiods.csv lacks race_id/foreperiod_s: {list(d.columns)}")
    out = pd.DataFrame({"race_id": d[rid].astype(str),
                        "foreperiod_s": pd.to_numeric(d[fpc], errors="coerce")})
    uc = _find(d, ["uncertainty_s", "fp_uncertainty_s", "sd_s", "uncertainty"])
    out["uncertainty_s"] = pd.to_numeric(d[uc], errors="coerce") if uc else np.nan
    qc = _find(d, ["qc_flag", "qc", "quality", "flag"])
    out["qc_flag"] = d[qc].astype(str).str.strip() if qc else "ok"
    out["qc_ok"] = out["qc_flag"].str.lower().isin(GOOD_QC)
    for extra in ("start_no", "recall", "n_starts", "method", "source_url", "session", "session_id",
                  "starter", "date"):
        c = _find(d, [extra])
        if c is not None:
            out[extra] = d[c]
    return out, [p]


WAVEFORM_FILE = "rt_waveform.csv"


def load_fp_sources(mock: bool, source: str = "auto") -> tuple[pd.DataFrame, list[Path]]:
    """Race-level foreperiods from the official Seiko start waveforms ('Ready Time', validated
    rows only) and/or broadcast-audio measurements (foreperiods.csv).

    Returns one row per race: race_id, foreperiod_s, fp_source, attempt, restart, qc_ok,
    uncertainty_s. ``source``: auto (Seiko where available, else audio), seiko, audio.
    """
    frames, used = [], []
    wf = data_path(WAVEFORM_FILE, mock)
    if wf.exists() and source in ("auto", "seiko"):
        d = pd.read_csv(wf, encoding="utf-8-sig", low_memory=False)
        ok = d["wf_ok"].astype(str).str.lower().isin(["true", "1", "yes"]) if "wf_ok" in d else True
        s = pd.DataFrame({"race_id": d["race_id"].astype(str),
                          "foreperiod_s": pd.to_numeric(d["wf_ready_time_s"], errors="coerce"),
                          "fp_source": "seiko_waveform",
                          "attempt": pd.to_numeric(d.get("wf_attempt"), errors="coerce"),
                          "qc_ok": ok, "uncertainty_s": 0.004})
        frames.append(s)
        used.append(wf)
    fpp = data_path(FP_FILE, mock)
    if fpp.exists() and source in ("auto", "audio"):
        a, _ = load_foreperiods(mock)
        s = pd.DataFrame({"race_id": a["race_id"], "foreperiod_s": a["foreperiod_s"],
                          "fp_source": "broadcast_audio",
                          "attempt": pd.to_numeric(a.get("start_no", a.get("attempt", pd.Series(np.nan, index=a.index))),
                                                   errors="coerce"),
                          "qc_ok": a["qc_ok"], "uncertainty_s": a["uncertainty_s"]})
        frames.append(s)
        used.append(fpp)
    if not frames:
        return pd.DataFrame(), used
    fp = pd.concat(frames, ignore_index=True)
    fp = fp[fp["qc_ok"].astype(bool) & fp["foreperiod_s"].notna()].copy()
    fp["prio"] = fp["fp_source"].map({"seiko_waveform": 0, "broadcast_audio": 1})
    fp = fp.sort_values(["race_id", "prio"]).drop_duplicates("race_id").drop(columns="prio")
    fp["restart"] = fp["attempt"].fillna(1) >= 2
    return fp.reset_index(drop=True), used


def load_races(mock: bool) -> tuple[pd.DataFrame, list[Path]]:
    p = data_path(RACES_FILE, mock)
    if not p.exists():
        return pd.DataFrame(), []
    d = pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    d.columns = [str(c).strip() for c in d.columns]
    if "race_id" not in d.columns:
        c = _find(d, ["race_id", "raceid"])
        d = d.rename(columns={c: "race_id"})
    d["race_id"] = d["race_id"].astype(str)
    return d, [p]


def session_key(races: pd.DataFrame, race_ids: pd.Series) -> pd.Series:
    """Best available session identifier for each race_id (session > date > comp_year)."""
    parsed = parse_race_id(race_ids)
    base = (parsed["comp"].astype(str) + parsed["year"].astype("Int64").astype(str))
    if races is None or races.empty:
        return base.rename("session")
    r = races.set_index("race_id")
    for c in ("session_id", "session"):
        if c in r.columns:
            s = race_ids.map(r[c])
            return s.fillna(base).astype(str).rename("session")
    if "date" in r.columns:
        s = race_ids.map(r["date"])
        return (base + "-" + s.astype(str)).where(s.notna(), base).rename("session")
    return base.rename("session")


def valid_rt_mask(rt: pd.DataFrame, lo: float = FS_THRESHOLD, hi: float = 0.300) -> pd.Series:
    """Legal, plausibly gun-triggered starts used for location/scale analyses: RT in [lo, hi],
    not a false start, not DNS. DQs for non-start reasons keep their (legal) RT."""
    return (rt["rt_s"].between(lo, hi) & ~rt["is_fs"].fillna(False).astype(bool)
            & ~rt["is_dns"].fillna(False).astype(bool))


# False-start rule eras (IAAF / World Athletics). Dates to be confirmed against lit/.
def rule_era(year) -> str:
    y = int(year)
    if y < 2003:
        return "pre-2003"
    if y < 2010:
        return "2003-2009"
    return "2010+"


# ----------------------------------------------------------------------------------
# statistics helpers
# ----------------------------------------------------------------------------------

def wilson_ci(k: float, n: float, z: float = 1.959964) -> tuple[float, float]:
    if n <= 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def cluster_bootstrap(df: pd.DataFrame, cluster: str, stat, n_boot: int = 1000,
                      seed: int = 1, strata: str | None = None) -> np.ndarray:
    """Resample clusters (races) with replacement; returns array of the statistic."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in df.groupby(cluster, sort=False)}
    keys = np.array(list(groups.keys()), dtype=object)
    out = []
    for _ in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        bs = pd.concat([groups[keys[i]] for i in pick], ignore_index=True)
        out.append(stat(bs))
    return np.asarray(out, dtype=float)


# ----------------------------------------------------------------------------------
# plotting
# ----------------------------------------------------------------------------------

# Reference categorical palette (dataviz skill, light mode), fixed order.
PAL = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
       "magenta": "#e87ba4", "green": "#008300", "violet": "#4a3aa7", "red": "#e34948"}
SERIES = [PAL[k] for k in ("blue", "orange", "aqua", "yellow", "magenta", "green", "violet", "red")]
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SEX_COLOR = {"M": PAL["blue"], "W": PAL["orange"]}
SEX_LABEL = {"M": "Men", "W": "Women"}


def set_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 300, "savefig.bbox": "tight",
        "font.family": ["Arial", "Segoe UI", "DejaVu Sans"], "font.size": 9,
        "axes.titlesize": 10, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "legend.frameon": False,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2,
        "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 1.6, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "figure.facecolor": "white", "axes.facecolor": "white", "pdf.fonttype": 42,
    })


def save_fig(fig, out: Path | str, mock: bool):
    """Save a PNG to ``out`` (and a PDF next to it) with deterministic metadata."""
    out = Path(out)
    if mock:
        fig.text(0.5, 0.5, "MOCK DATA - NOT A RESULT", ha="center", va="center", rotation=25,
                 fontsize=28, color="#e34948", alpha=0.25, weight="bold")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, metadata={"Software": None})
    fig.savefig(out.with_suffix(".pdf"), metadata={"Creator": None, "Producer": None,
                                                   "CreationDate": None})
    import matplotlib.pyplot as plt
    plt.close(fig)
    return out


def add_common_args(ap, name: str | None = None):
    ap.add_argument("--mock", action="store_true",
                    help="run on analysis/mock/data/MOCK_*.csv; default outputs go to analysis/mock/")
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--out", default=None,
                    help="output JSON path (default analysis/outputs/<name>.json, or analysis/mock/outputs/)")
    return ap


def resolve_out(args, name: str) -> Path:
    return Path(args.out) if args.out else default_out(name, args.mock)
