"""Literature-audit screening table (lit/audit_protocol.md section 3).

Merges the saved search records (lit/audit_search/*.json) and the repo study list
(lit/audit_search/repo_studies.csv), de-duplicates them (DOI, then normalised title + year +/- 1), applies the
protocol's automatic stage-1 off-topic rule, joins the reviewer's stage-2/3 decisions
(lit/audit_search/screen_decisions.csv) and writes lit/audit_screening.csv (a flow summary is printed, not saved).

Usage (from the repo root):
    .venv\\Scripts\\python.exe lit\\tools\\audit_screen.py --search lit\\audit_search --out lit\\audit_screening.csv

Deterministic: the same inputs give the same bytes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SOURCES = ["openalex", "pubmed", "s2", "gs", "chase"]
OTHER_SPORTS = ["swim", "skating", "canoe", "kayak", "cycling", "speedway", "bmx", "taekwondo", "karate", "judo",
                "fencing", "soccer", "football", "basketball", "volleyball", "tennis", "rugby", "esports", "golf",
                "front crawl", "backstroke", "freestyle"]
ATHLETICS_TERMS = ["sprint", "sprinter", "athletics", "track and field", "track-and-field", "100 m", "100-m", "100m",
                   "200 m", "60 m", "hurdle", "false start", "starting block", "block start", "iaaf", "world athletics"]


TAG_RE = re.compile(r"^(\s*(\[(PDF|HTML|C|CITATION|BOOK|B)\]|…|\.\.\.)\s*)+", re.I)


def clean_title(t: str) -> str:
    """Strip Google Scholar result tags ([PDF], [HTML], [C]...) and leading ellipses."""
    return TAG_RE.sub("", t or "").strip()


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", clean_title(t)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())


def rec_id(doi, title):
    if doi:
        return f"doi:{doi.lower()}"
    nt = norm_title(title)
    return f"t:{nt[:50]}-{hashlib.sha1(nt.encode()).hexdigest()[:6]}"


def load_records(search: Path):
    recs = []
    for s in SOURCES:
        p = search / f"{s}.json"
        if not p.exists():
            continue
        js = json.loads(p.read_text(encoding="utf-8"))
        for r in js.get("records", []):
            r = dict(r)
            r["_source"] = s
            recs.append(r)
    rp = search / "repo_studies.csv"
    if rp.exists():
        with rp.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                recs.append({"doi": (r.get("doi") or "").lower() or None, "title": r["title"],
                             "year": int(r["year"]) if r.get("year") else None, "venue": r.get("venue"),
                             "abstract": "", "_source": "repo", "repo_ref": r.get("repo_ref", "")})
    return recs


def dedupe(recs):
    groups, by_doi, by_title = [], {}, {}
    for r in recs:
        doi = (r.get("doi") or "").lower().strip() or None
        nt = norm_title(r.get("title", ""))
        g = None
        if doi and doi in by_doi:
            g = by_doi[doi]
        elif nt:
            for y in ([r.get("year")] if r.get("year") is None else [r["year"], r["year"] - 1, r["year"] + 1]):
                if (nt, y) in by_title:
                    g = by_title[(nt, y)]
                    break
            if g is None and (nt, None) in by_title:
                g = by_title[(nt, None)]
        if g is None:
            g = {"members": []}
            groups.append(g)
        g["members"].append(r)
        if doi:
            by_doi.setdefault(doi, g)
        if nt:
            by_title.setdefault((nt, r.get("year")), g)
    out = []
    for g in groups:
        m = g["members"]
        doi = next((x["doi"].lower() for x in m if x.get("doi")), None)
        title = next((x["title"] for x in m if x.get("_source") in ("openalex", "pubmed", "chase") and x.get("title")),
                     next((x["title"] for x in m if x.get("title")), ""))
        title = clean_title(title)
        abstract = max((x.get("abstract") or "" for x in m), key=len)
        year = next((x["year"] for x in m if x.get("year")), None)
        venue = next((x.get("venue") for x in m if x.get("venue")), "")
        srcs = sorted({x["_source"] for x in m})
        chase = sorted({c for x in m for c in (x.get("chase") or [])})
        out.append({"record_id": rec_id(doi, title), "title": title.strip(), "year": year, "doi": doi or "",
                    "venue": venue or "", "sources": ";".join(srcs), "n_hits": len(m),
                    "has_abstract": bool(abstract.strip()), "abstract": abstract, "chase": ";".join(chase)})
    return out


def stage1(r):
    text = f"{r['title']} {r['abstract']}".lower()
    if not r["has_abstract"]:
        return "to_stage2"
    return "to_stage2" if any(t in text for t in ATHLETICS_TERMS) else "exclude_auto"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    search = Path(a.search)
    recs = dedupe(load_records(search))
    dec = {}
    dp = search / "screen_decisions.csv"
    if dp.exists():
        with dp.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                dec[r["record_id"].strip()] = r
    rows = []
    for r in sorted(recs, key=lambda x: (x["year"] or 0, x["record_id"])):
        s1 = stage1(r)
        d = dec.get(r["record_id"])
        if d:
            decision, reason, study_id, access, note = (d["decision"], d["reason"], d.get("study_id", ""),
                                                        d.get("access_reached", ""), d.get("note", ""))
        elif s1 == "exclude_auto":
            decision, reason, study_id, access, note = "exclude", "E-OFF-auto", "", "", "stage 1: no athletics term"
        else:
            sport = any(k in r["title"].lower() for k in OTHER_SPORTS)
            decision, reason, study_id, access = "exclude", ("E-SPORT" if sport else "E-OFF"), "", "title/abstract"
            note = ("stage 2 (reviewer): other sport" if sport else
                    "stage 2 (reviewer): not an analysis of official championship sprint RTs "
                    "(cognitive/clinical RT, lab biomechanics or training, non-RT race analysis)")
        rows.append({"record_id": r["record_id"], "year": r["year"] or "", "title": r["title"], "doi": r["doi"],
                     "venue": r["venue"], "sources": r["sources"], "n_hits": r["n_hits"],
                     "has_abstract": int(r["has_abstract"]), "stage1": s1, "decision": decision, "reason": reason,
                     "study_id": study_id, "access_reached": access, "note": note, "chase": r["chase"]})
    missing = sorted(set(dec) - {r["record_id"] for r in rows})
    if missing:
        raise SystemExit(f"screen_decisions.csv has record_ids that match no record: {missing}")
    cols = list(rows[0].keys())
    # text mode with the platform newline, like common.write_result: with core.autocrlf the working copy then has the
    # same bytes as a fresh checkout, so the sha256 recorded by analysis/lit_audit.py is stable
    with open(a.out, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    # flow summary
    log = json.loads((search / "search_log.json").read_text(encoding="utf-8"))
    flow = {"per_source": {k: {"reported_count": v.get("reported_count"), "records_saved": v.get("n_records_saved"),
                               "error": v.get("error"), "stopped": v.get("stopped")} for k, v in log.items()},
            "records_before_dedupe": sum(r["n_hits"] for r in rows), "unique_records": len(rows),
            "stage1_auto_excluded": sum(r["decision"] == "exclude" and r["reason"] == "E-OFF-auto" for r in rows),
            "by_decision_reason": {}}
    for r in rows:
        k = f"{r['decision']}|{r['reason']}"
        flow["by_decision_reason"][k] = flow["by_decision_reason"].get(k, 0) + 1
    flow["by_decision_reason"] = dict(sorted(flow["by_decision_reason"].items()))
    print(json.dumps(flow, indent=1, ensure_ascii=False))  # printed only; analysis/lit_audit.py reports these counts


if __name__ == "__main__":
    main()
