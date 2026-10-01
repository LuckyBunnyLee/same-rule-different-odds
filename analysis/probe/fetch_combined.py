"""EXPLORATORY scratch: fetch WA combined-event block-start disciplines (decathlon 100m/400m/110mH,
heptathlon 100mH/200m) into analysis/probe/wa_pages/ and parse them to combined_rt.csv."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_extra_events as f
import pandas as pd
CE = [("men", "decathlon", "100-metres"), ("men", "decathlon", "400-metres"), ("men", "decathlon", "110-metres-hurdles"),
      ("women", "heptathlon", "100-metres-hurdles"), ("women", "heptathlon", "200-metres")]
EV = {"100-metres": "100m", "400-metres": "400m", "110-metres-hurdles": "110mH", "100-metres-hurdles": "100mH", "200-metres": "200m"}
rows = []
for cy in sys.argv[1].split(","):
    c = [x for x in f.COMPETITIONS if f.comp_key(x) == cy][0]
    for sex, ce, disc in CE:
        p = f.OUT / cy / f"{sex}-{ce}-{disc}.html.gz"
        m = f.get(f.results_url(c, sex, ce, disc), p)
        if m["status"] != 200:
            print("miss", cy, ce, disc, m["status"]); continue
        E = f.data_of(p)["props"]["pageProps"].get("eventPhasesByDiscipline") or {}
        for u in (E.get("units") or []):
            sl = {s["competitorId"]: s for s in (u.get("startlist") or [])}
            udt = u.get("unitDateTime") or ""
            for r in (u.get("results") or []):
                s = sl.get(r["competitorId"], {})
                try:
                    rt = float(r.get("reactionTime"))
                except Exception:
                    rt = None
                rows.append(dict(comp_year=cy, ce=ce, event=EV[disc], sex="M" if sex == "men" else "W",
                                 heat=u.get("unitCode"), date=udt[:10], time_local=udt[11:16], lane=s.get("start"),
                                 athlete=r.get("competitorName"), athlete_id=r.get("competitorId_WA"), rt_s=rt,
                                 mark=r.get("resultMark"), source_url=m.get("final_url"), retrieved_at=m.get("retrieved_at")))
        print("ok", cy, ce, disc, flush=True)
df = pd.DataFrame(rows)
out = Path(__file__).resolve().parent / "combined_rt.csv"
if out.exists():
    old = pd.read_csv(out)
    df = pd.concat([old[~old.comp_year.isin(df.comp_year.unique())], df], ignore_index=True)
df.to_csv(out, index=False)
print(df.groupby(["comp_year", "ce", "event", "date"]).agg(n=("rt_s", "size"), med=("rt_s", "median")).to_string())
