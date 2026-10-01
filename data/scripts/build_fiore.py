"""Ingest Fiore's thesis RT data (ofiore/Thesis Data/rxntime.csv) -> rt_fiore.csv.

Source columns (Data/README.md in that repo, commit 3cf1db7): Year, Stage (H/S/F),
TotalTime (s, or DNF/DQ/D/DNS/rule code), ReactionTime (s), Gender (M/F),
Batch (integer id per race, 'not meaningful'), Event ('100 Dash', '100 Hurdles',
'110 Hurdles', '200 Dash'). No athlete names, lanes or heat numbers.

Mapping to our race_id: every Fiore batch is compared with each of our races in
the same (year, event, sex, round) by counting matching (result, RT) pairs
(results to 0.01 s, RT to 0.001 s). A batch is mapped when the best race matches
at least max(3, 60% of the batch's rows) pairs and strictly beats the runner-up.
Rows are then matched to athletes within the mapped race on (result, RT).
Only years/events present in rt_athletes.csv can be mapped.

Usage:
  data/scripts/build_fiore.py --fiore data/raw/fiore/rxntime.csv
      --athletes data/derived/rt_athletes.csv --out data/derived/rt_fiore.csv
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

EVENT_MAP = {"100 Dash": "100m", "100 Hurdles": "100mH", "110 Hurdles": "110mH", "200 Dash": "200m"}
SEX_MAP = {"M": "M", "F": "W"}
STAGE_MAP = {"H": "R1", "S": "SF", "F": "F"}
SOURCE = ("https://github.com/ofiore/Thesis/blob/3cf1db7adebb493f3a5c2e957a1b09cf0986a7cd/"
          "Data/rxntime.csv")


def res_key(x) -> str:
    try:
        return f"{float(x):.2f}"
    except (TypeError, ValueError):
        s = str(x).strip().upper()
        return "DQ" if s.startswith("D") and s not in ("DNF", "DNS") else s


def rt_key(x) -> str:
    try:
        return f"{float(x):.3f}"
    except (TypeError, ValueError):
        return ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fiore", required=True)
    ap.add_argument("--athletes", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    f = pd.read_csv(a.fiore, encoding="utf-8-sig", dtype={"TotalTime": str})
    f.insert(0, "fiore_row", range(1, len(f) + 1))      # 1-based data row in the source
    f["comp"] = "WCH"
    f["event"] = f["Event"].map(EVENT_MAP)
    f["sex"] = f["Gender"].map(SEX_MAP)
    f["round_guess"] = f["Stage"].map(STAGE_MAP)
    f["k"] = [res_key(r) + "|" + rt_key(t) for r, t in zip(f["TotalTime"], f["ReactionTime"])]

    ath = pd.read_csv(a.athletes, dtype={"result": str})
    ath["k"] = [res_key(r) + "|" + rt_key(t) for r, t in zip(ath["result"], ath["rt_s"])]
    ath = ath[ath["comp"] == "WCH"]
    races = {rid: Counter(g["k"]) for rid, g in ath.groupby("race_id")}
    meta = ath.drop_duplicates("race_id").set_index("race_id")[["year", "event", "sex", "round"]]

    batch_rows, row_race = [], {}
    for b, g in f.groupby("Batch"):
        yr, ev, sx = int(g["Year"].iloc[0]), g["event"].iloc[0], g["sex"].iloc[0]
        stages = sorted(g["Stage"].unique())
        labelled = {STAGE_MAP[s] for s in stages if s in STAGE_MAP}
        if "R1" in labelled:
            labelled |= {"PR", "R2"}     # 'heats' label may cover prelim/quarter rounds
        cand = meta[(meta["year"] == yr) & (meta["event"] == ev) & (meta["sex"] == sx)]
        kb = Counter(g["k"])
        scores = sorted(((sum((kb & races[rid]).values()), rid) for rid in cand.index), reverse=True)
        best = scores[0] if scores else (0, None)
        second = scores[1][0] if len(scores) > 1 else 0
        need = max(3, int(0.6 * len(g) + 0.999))
        why, mapped = "", None
        if not len(cand):
            why = "no WA races loaded for this year/event"
        elif best[0] >= need and best[0] > second:
            mapped = best[1]
            if meta.at[mapped, "round"] not in labelled:
                why = f"Stage label {'/'.join(stages)} but data match {meta.at[mapped, 'round']}"
            for i in g.index:
                row_race[i] = mapped
        else:
            # source batches that pool two races (e.g. 2022 batches 217/218): assign
            # rows individually when each key occurs in exactly one candidate race
            hits = {}
            for i, k in zip(g.index, g["k"]):
                rs = [rid for rid in cand.index if races[rid].get(k)]
                if len(rs) == 1:
                    hits[i] = rs[0]
            per = Counter(hits.values())
            good = {rid for rid, n in per.items() if n >= 3}
            n_ok = sum(1 for rid in hits.values() if rid in good)
            if good and n_ok >= need:
                for i, rid in hits.items():
                    if rid in good:
                        row_race[i] = rid
                why = (f"batch pools {len(good)} races: " + ", ".join(sorted(good))
                       + " (rows assigned individually)")
            else:
                why = f"best match {best[0]}/{len(g)} (runner-up {second}) below threshold"
        batch_rows.append(dict(Batch=b, batch_race_id=mapped, match_pairs=best[0], batch_n=len(g),
                               runner_up_pairs=second, map_note=why))
    bm = pd.DataFrame(batch_rows)
    out = f.merge(bm, on="Batch", how="left")
    out["race_id"] = [row_race.get(i) for i in f.index]

    # athlete-level match inside the mapped race
    ath_by_race = {rid: g for rid, g in ath.groupby("race_id")}
    athl, lane, used_note, final_rid = [], [], [], []
    used: dict[str, set] = {}
    for _, r in out.iterrows():
        rid = r["race_id"]
        if not isinstance(rid, str):
            athl.append(None); lane.append(None); used_note.append(""); final_rid.append(None)
            continue
        g = ath_by_race[rid]
        hit = g[(g["k"] == r["k"]) & ~g.index.isin(used.get(rid, set()))]
        note = ""
        if not len(hit):
            # row filed under the wrong batch in the source: look in sibling races
            sib = meta[(meta["year"] == r["Year"]) & (meta["event"] == r["event"])
                       & (meta["sex"] == r["sex"])].index
            alt = [x for x in sib if x != rid and races[x].get(r["k"])]
            if len(alt) == 1:
                note = f"source batch maps to {rid}, but this row matches {alt[0]}"
                rid, g = alt[0], ath_by_race[alt[0]]
                hit = g[(g["k"] == r["k"]) & ~g.index.isin(used.get(rid, set()))]
        if len(hit):
            i = hit.index[0]
            used.setdefault(rid, set()).add(i)
            athl.append(g.at[i, "athlete"]); lane.append(g.at[i, "lane"])
            used_note.append(note); final_rid.append(rid)
        else:
            athl.append(None); lane.append(None)
            used_note.append("row not matched to an athlete"); final_rid.append(rid)
    out["race_id"] = final_rid
    out["athlete"] = athl
    out["lane"] = pd.array(lane, dtype="Int64")
    out["row_note"] = used_note
    out["year"] = out["Year"]
    out["source_url"] = SOURCE
    cols = ["fiore_row", "Year", "Stage", "TotalTime", "ReactionTime", "Gender", "Batch", "Event",
            "comp", "year", "event", "sex", "round_guess", "race_id", "athlete", "lane",
            "match_pairs", "batch_n", "runner_up_pairs", "map_note", "row_note", "source_url"]
    out = out[cols].sort_values("fiore_row")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False, encoding="utf-8", lineterminator="\n")
    n_map = out["race_id"].notna().sum()
    print(f"{a.out}: {len(out)} rows, {n_map} mapped to a race_id "
          f"({bm["batch_race_id"].notna().sum()}/{len(bm)} batches whole)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
