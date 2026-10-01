"""Step 4: parse official WA/Seiko results PDFs -> data/derived/rt_pdf_results.csv.

One row per athlete line in each heat of each phase-level 'Official Results'
(RS6) PDF. Extracted per heat: actual START TIME (local), temperature, humidity,
wind, NOTE lines (e.g. 'WA Rule TR16.8 - False start'); per athlete: place, bib,
name, country, lane, result, rule code (TR16.8 = false start, TR22.6 = hurdle,
TR17.3 = lane ...), reaction time and the 'Fn' (false-start) column.

Only Seiko-format PDFs (World Championships) are handled; WA hosts no PDFs for
the Olympic Games. Heats/URLs come straight from the cached WA pages
(build_rt.load_all), and PDFs from the local cache (fetch_docs.py --kind pdf).

Usage: .venv/Scripts/python.exe data/scripts/parse_pdfs.py --out data/derived/rt_pdf_results.csv
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

from build_rt import add_subset_args, load_all, subset
from fetch_docs import local_path

HEAT_RE = re.compile(r"^Heat\s+(\d+)\b")
START_RE = re.compile(
    r"(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})\s+(\d{1,2}:\d{2})\s*START\s*TIME"
    r"(?:\s+(-?\d+)\s*°\s*C)?(?:\s+(\d+)\s*%)?(?:\s+([+-]?\d+\.\d)\s*m/s)?")
ROW_RE = re.compile(
    r"^(?:(?P<place>\d{1,2})\s+)?(?:(?P<bib>\d{3,5})\s+)?(?P<name>\S.*?)\s+"
    r"(?P<country>[A-Z]{3})\s+(?:(?P<dob>(?:\d{1,2}\s+[A-Z][a-z]{2}\s+)?\d{2,4})\s+)?"
    r"(?P<lane>\d{1,2})\s+(?P<result>DQ|DNS|DNF|DSQ|\d{1,2}\.\d{2}|\d:\d{2}\.\d{2})"
    r"(?P<rest>.*)$")
RT_RE = re.compile(r"^-?\d\.\d{3}$")
# rule codes: WA 'TR16.8', 'TR22.6.2[K]', 'TR*' (see NOTE), IAAF-era bare '162.8', '163.2(b)'
RULE_RE = re.compile(r"^(?:(?:TR|R|DR)?\d{2,3}(?:\.\d+)*(?:\([a-z0-9]+\))?(?:\[[A-Z]+\])?|TR\*)$")
# false-start rules: WA TR16.8 (2020-), IAAF 162.8 (2018-19), IAAF 162.7 (2010-17)
FS_RULE_RE = re.compile(r"(?:^|\s)(?:TR|R|DR)?16(?:\.8|2\.8|2\.7)(?:\s|$|\()")
CARD_NOTE_RE = re.compile(r"^[A-Z]\s+BIB\s+\d+")
CARD_NAME_RE = re.compile(r"^([A-Z])\s+(?=[A-Z][a-zà-ÿ])")
FOOT_RE = re.compile(r"(AT-\S+?\.RS\d)\.*v?(\d+)?\s+Issued at (\d{1,2}:\d{2}) on \w+, (\d{1,2} \w+ \d{4})")
HEADER_WORDS = ("PLACE", "RECORDS", "World Record", "Championships Record", "World Leading",
                "Area Record", "TEMPERATURE", "WIND", "RESULT NAME", "ALL-TIME")


def parse_rest(rest: str):
    toks = rest.split()
    rt, rule, fn, other = None, [], [], []
    rt_idx = None
    for i, t in enumerate(toks):
        if RT_RE.match(t):
            rt, rt_idx = float(t), i
    for i, t in enumerate(toks):
        if i == rt_idx:
            continue
        if RULE_RE.match(t):
            rule.append(t)
        elif rt_idx is not None and i > rt_idx:
            fn.append(t)
        else:
            other.append(t)
    return rt, " ".join(rule), " ".join(fn), " ".join(other)


def parse_pdf(path):
    rows, heats = [], {}
    heat = 1
    footer = {}
    in_list = False
    last_heat_key = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1) or ""
            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue
                fm = FOOT_RE.search(line)
                if fm:
                    footer = dict(pdf_doc=fm.group(1), pdf_version=fm.group(2) or "",
                                  pdf_issued=f"{fm.group(4)} {fm.group(3)}")
                    continue
                hm = HEAT_RE.match(line)
                if hm:
                    heat = int(hm.group(1))
                sm = START_RE.search(line)
                if sm:
                    heats[heat] = dict(heat=heat, pdf_date=sm.group(1), pdf_start_time=sm.group(2),
                                       pdf_temp_c=sm.group(3), pdf_humidity=sm.group(4),
                                       pdf_wind=sm.group(5), pdf_heat_note="")
                    last_heat_key = heat
                    in_list = True
                    continue
                if line.startswith(("ALL-TIME", "RESULT NAME")):
                    in_list = False
                    continue
                # NOTE lines: rule explanations and start cards ('Y BIB 1999 (NAME) - ...'
                # = yellow card / warning; 'L BIB ...' = lane mark, TR17.4.3)
                if (line.startswith("NOTE") or CARD_NOTE_RE.match(line)
                        or (line.startswith("WA Rule") and last_heat_key is not None)):
                    note = line.replace("NOTE", "", 1).strip()
                    if last_heat_key in heats:
                        prev = heats[last_heat_key]["pdf_heat_note"]
                        heats[last_heat_key]["pdf_heat_note"] = (prev + " | " + note).strip(" |")
                    continue
                if not in_list or line.startswith(HEADER_WORDS):
                    continue
                m = ROW_RE.match(line)
                if not m:
                    continue
                rt, rule, fn, other = parse_rest(m.group("rest"))
                name = m.group("name")
                cm = CARD_NAME_RE.match(name)       # 'Y Lamont Marcell JACOBS' -> card Y
                card = cm.group(1) if cm else ""
                if cm:
                    name = name[2:]
                rows.append(dict(heat=heat, place=m.group("place"), bib=m.group("bib"),
                                 pdf_card=card, pdf_name=name, pdf_country=m.group("country"),
                                 pdf_lane=int(m.group("lane")), pdf_result=m.group("result"),
                                 pdf_rule=rule, pdf_rt=rt, pdf_fn=fn, pdf_other=other,
                                 pdf_line=line))
    return rows, heats, footer


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    add_subset_args(ap)
    a = ap.parse_args(argv)
    _, races = load_all(**subset(a))
    races = races[races["results_pdf_url"].fillna("").str.startswith("http")]
    out = []
    for url, grp in races.groupby("results_pdf_url"):
        path = local_path(url, "pdf")
        if not path.exists():
            print(f"[missing] {path}")
            continue
        rows, heats, footer = parse_pdf(path)
        by_heat = {int(h): rid for h, rid in zip(grp["heat"], grp["race_id"])}
        base = grp.iloc[0]
        for r in rows:
            h = r["heat"]
            r.update(heats.get(h, {}))
            r.update(footer)
            r.update(race_id=by_heat.get(h), comp=base["comp"], year=base["year"],
                     event=base["event"], sex=base["sex"], round=base["round"], pdf_url=url)
            note = r.get("pdf_heat_note") or ""
            rule = r["pdf_rule"] or ""
            # 'TR*' = rule explained in the heat NOTE (e.g. '... TR16.8 False start - BIB 852 ...')
            fs_seg = next((seg for seg in note.split(" | ") if "false start" in seg.lower()), "")
            names_bib = re.search(r"BIB\s*\d+", fs_seg)
            star_fs = (rule == "TR*" and bool(fs_seg)
                       and ((r["bib"] and f"BIB {r['bib']}" in fs_seg) or not names_bib))
            r["pdf_fs"] = bool(FS_RULE_RE.search(f" {rule} ")) or star_fs
            out.append(r)
        n_json = int(grp["n_athletes"].sum())
        flag = "" if len(rows) == n_json else "  <-- count differs"
        print(f"{path.name:32s} heats={len(heats):2d} rows={len(rows):3d} json={n_json:3d}{flag}")
    df = pd.DataFrame(out)
    front = ["race_id", "comp", "year", "event", "sex", "round", "heat", "pdf_date",
             "pdf_start_time", "pdf_temp_c", "pdf_humidity", "pdf_wind", "place", "bib",
             "pdf_card", "pdf_name", "pdf_country", "pdf_lane", "pdf_result", "pdf_rule", "pdf_fs", "pdf_rt",
             "pdf_fn", "pdf_other", "pdf_heat_note", "pdf_doc", "pdf_version", "pdf_issued",
             "pdf_url", "pdf_line"]
    df = df[[c for c in front if c in df.columns]]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False, encoding="utf-8", lineterminator="\n")
    print(f"{a.out}: {len(df)} rows; unmatched heats: {df['race_id'].isna().sum()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
