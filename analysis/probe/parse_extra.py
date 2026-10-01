"""EXPLORATORY scratch (recent_probe): parse cached WA pages (400m, 400mH, relays) into a CSV of
block-start RTs with lane, date/time and athlete ids. Output: analysis/probe/extra_rt.csv"""
from __future__ import annotations
import gzip, json, re, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data" / "scripts"))
from wa_http import extract_next_data  # noqa: E402
from config import round_code  # noqa: E402
PAGES = ROOT / "analysis" / "probe" / "wa_pages"
EV = {"400-metres": "400m", "400-metres-hurdles": "400mH", "4x100-metres-relay": "4x100m",
      "4x400-metres-relay": "4x400m", "4x400-metres-relay-mixed": "4x400mX"}
SEX = {"men": "M", "women": "W", "mixed": "X"}

def f(x):
    try:
        return float(str(x).replace("+", ""))
    except Exception:
        return None

rows = []
for p in sorted(PAGES.glob("*/*.html.gz")):
    cy = p.parent.name
    meta = json.loads(p.with_name(p.name + ".meta.json").read_text(encoding="utf-8"))
    with gzip.open(p, "rb") as fh:
        d = extract_next_data(fh.read().decode("utf-8"))
    ph = d["props"]["pageProps"].get("eventPhasesByDiscipline")
    if ph is None:
        continue
    disc = ph["discipline"]["nameUrlSlug"]; sexs = ph["sexNameUrlSlug"]
    ev = EV.get(disc); sx = SEX.get(sexs)
    rnd = round_code(ph["phaseName"])
    for u in ph["units"]:
        code = (u.get("unitCode") or "").strip()
        heat = int(code) if code.isdigit() else 1
        sl = {s["competitorId"]: s for s in (u.get("startlist") or [])}
        udt = (u.get("unitDateTime") or ph.get("phaseDateAndTime") or "")
        for r in (u.get("results") or []):
            s = sl.get(r["competitorId"], {})
            mark = (r.get("resultMark") or "").strip()
            rows.append(dict(race_id=f"{cy}-{ev}-{sx}-{rnd}-H{heat}", comp_year=cy, event=ev, sex=sx, round=rnd, heat=heat,
                             date=udt[:10], time_local=udt[11:16], lane=s.get("start"), athlete=r.get("competitorName"),
                             athlete_id=r.get("competitorId_WA"), country=r.get("competitorCountryCode"),
                             rt_raw=r.get("reactionTime"), rt_s=f(r.get("reactionTime")), mark=mark,
                             source_url=meta.get("final_url"), retrieved_at=meta.get("retrieved_at")))
df = pd.DataFrame(rows)
df.to_csv(ROOT / "analysis" / "probe" / "extra_rt.csv", index=False)
print(df.groupby(["comp_year", "event", "sex"]).agg(n=("rt_s", "size"), n_rt=("rt_s", lambda s: s.notna().sum()), med=("rt_s", "median")).to_string())
