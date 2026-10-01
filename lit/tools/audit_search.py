"""Literature-audit search (lit/audit_protocol.md section 2).

Runs the protocol's queries against OpenAlex, PubMed, Semantic Scholar and Google Scholar, plus one round of
backward/forward citation chasing from seed studies (OpenAlex), and saves every raw record with the query string,
URL, retrieval time and the hit count each source reports.

Usage (from the repo root):
    .venv\\Scripts\\python.exe lit\\tools\\audit_search.py --out lit\\audit_search [--only openalex,pubmed,s2,gs,chase]

Outputs (one JSON per source, plus a log):
    <out>/openalex.json, pubmed.json, s2.json, gs.json, chase.json, search_log.json

Network results change over time, so a rerun will not reproduce these files byte for byte; the saved files are the
audit's frozen record of what the searches returned on the retrieval date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

UA = {"User-Agent": "ssac-lit-audit/1.0 (research literature audit; contact via repository)"}
YEARS = (1990, 2026)

# ---- protocol concept groups (section 2) ----
G1 = ['"reaction time"', '"reaction times"', '"response time"', '"start reaction"']
G2_OA = ["sprint", "sprints", "sprinter", "sprinters", "sprinting", '"false start"', '"false starts"',
         '"starting block"', '"starting blocks"', '"block start"', "hurdle", "hurdles", "hurdler", "hurdlers"]
G3_OA = ["championship", "championships", "olympic", "olympics", '"World Championships"', '"world indoor"', "IAAF",
         '"World Athletics"']

OA_QUERY = "(" + " OR ".join(G1) + ") AND (" + " OR ".join(G2_OA) + ") AND (" + " OR ".join(G3_OA) + ")"

PM_QUERY = ("(\"reaction time\"[tiab] OR \"reaction times\"[tiab] OR \"response time\"[tiab] OR \"start reaction\"[tiab])"
            " AND (sprint*[tiab] OR \"false start\"[tiab] OR \"false starts\"[tiab] OR \"starting block\"[tiab] OR "
            "\"starting blocks\"[tiab] OR \"block start\"[tiab] OR hurdle*[tiab])"
            " AND (championship*[tiab] OR olympic*[tiab] OR \"world championships\"[tiab] OR \"world indoor\"[tiab] OR "
            "IAAF[tiab] OR \"world athletics\"[tiab])"
            f" AND {YEARS[0]}:{YEARS[1]}[dp]")

S2_QUERY = ("(\"reaction time\" | \"reaction times\" | \"response time\" | \"start reaction\") + "
            "(sprint* | \"false start\" | \"false starts\" | \"starting block\" | \"starting blocks\" | \"block start\" | hurdle*) + "
            "(championship* | olympic* | \"World Championships\" | \"world indoor\" | IAAF | \"World Athletics\")")

GS_QUERY = ('("reaction time" OR "response time") (sprint OR sprinter OR sprinters OR "false start" OR "starting blocks") '
            '(championships OR Olympic OR IAAF OR "World Athletics")')

# Seeds for citation chasing: championship-RT studies in lit/systematic_forensics.md sections 2 and 4 with a DOI,
# plus the review Milloz et al. 2021 (hub, chasing only).
SEEDS = {
    "Haugen2013": "10.1080/02640414.2012.746724",
    "Tonnessen2013": "10.1519/jsc.0b013e31826520c3",
    "Brosnan2017": "10.1080/02640414.2016.1201213",
    "Lipps2011": "10.1371/journal.pone.0026141",
    "MirshamsShahshahani2018": "10.1371/journal.pone.0198633",
    "Fiore2025": "10.1080/00031305.2025.2515869",
    "Han2025": "10.1080/24748668.2025.2579341",
    "Collet1999": "10.2466/pms.1999.88.1.65",
    "Mitasik2020": "10.2478/afepuc-2020-0017",
    "Mitasik2021": "10.2478/afepuc-2021-0017",
    "Mitasik2022": "10.2478/afepuc-2022-0007",
    "Ntolaptsis2021": "10.2478/afepuc-2021-0007",
    "Brown2008": "10.1249/mss.0b013e31816770e1",
    "Pilianidis2012IJPAS": "10.1080/24748668.2012.11868587",
    "Matic2023": "10.31382/eqol.230602",
    "Mukai2020": "10.1109/kst48564.2020.9059442",
    "Zhang2021": "10.1155/2021/6633326",
    "Milloz2021_review": "10.1007/s40279-020-01350-4",
}


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url, params=None, headers=None, tries=6, base_sleep=4.0, timeout=60):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers or UA, timeout=timeout)
        except requests.RequestException as e:  # network hiccup: retry
            last = repr(e)
            time.sleep(base_sleep * (2 ** i))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last = f"HTTP {r.status_code}"
            time.sleep(base_sleep * (2 ** i))
            continue
        return r
    raise RuntimeError(f"giving up on {url}: {last}")


def oa_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idx in inv.items():
        for i in idx:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def oa_record(w):
    src = (w.get("primary_location") or {}).get("source") or {}
    return {
        "openalex_id": w.get("id", "").rsplit("/", 1)[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower() or None,
        "title": w.get("display_name") or w.get("title") or "",
        "year": w.get("publication_year"),
        "venue": src.get("display_name"),
        "type": w.get("type"),
        "language": w.get("language"),
        "oa_status": (w.get("open_access") or {}).get("oa_status"),
        "cited_by_count": w.get("cited_by_count"),
        "abstract": oa_abstract(w.get("abstract_inverted_index")),
        "authors": "; ".join(a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:6]),
    }


OA_SELECT = ("id,doi,display_name,title,publication_year,primary_location,type,language,open_access,cited_by_count,"
             "abstract_inverted_index,authorships,referenced_works")


def openalex_paged(filt, max_records=5000):
    url = "https://api.openalex.org/works"
    cursor, out, count, first_url = "*", [], None, None
    while cursor and len(out) < max_records:
        params = {"filter": filt, "per-page": 200, "cursor": cursor, "select": OA_SELECT}
        r = get(url, params=params)
        first_url = first_url or r.url
        r.raise_for_status()
        js = r.json()
        count = js["meta"]["count"]
        out.extend(js["results"])
        cursor = js["meta"].get("next_cursor")
        if not js["results"]:
            break
    return out, count, first_url


def run_openalex():
    filt = f"title_and_abstract.search:{OA_QUERY},publication_year:{YEARS[0]}-{YEARS[1]}"
    works, count, url = openalex_paged(filt)
    return {"source": "openalex", "query": OA_QUERY, "filter": filt, "url": url, "retrieved": now(),
            "reported_count": count, "records": [oa_record(w) for w in works]}


def run_pubmed():
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    r = get(base + "esearch.fcgi", params={"db": "pubmed", "term": PM_QUERY, "retmax": 5000, "retmode": "json"})
    js = r.json()["esearchresult"]
    ids = js.get("idlist", [])
    recs = []
    for i in range(0, len(ids), 150):
        rr = get(base + "efetch.fcgi", params={"db": "pubmed", "id": ",".join(ids[i:i + 150]), "retmode": "xml"})
        root = ET.fromstring(rr.content)
        for art in root.findall(".//PubmedArticle"):
            pmid = art.findtext(".//PMID")
            title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
            abst = " ".join("".join(a.itertext()) for a in art.findall(".//Abstract/AbstractText"))
            year = art.findtext(".//JournalIssue/PubDate/Year") or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4]
            doi = None
            for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):  # the article's own ids, not its references'
                if aid.get("IdType") == "doi":
                    doi = (aid.text or "").lower()
            recs.append({"pmid": pmid, "doi": doi, "title": title, "year": int(year) if str(year).isdigit() else None,
                         "venue": art.findtext(".//Journal/Title"), "abstract": abst})
        time.sleep(0.4)
    return {"source": "pubmed", "query": PM_QUERY, "url": r.url, "retrieved": now(),
            "reported_count": int(js.get("count", 0)), "records": recs}


def run_s2():
    url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    params = {"query": S2_QUERY, "year": f"{YEARS[0]}-{YEARS[1]}",
              "fields": "title,year,externalIds,abstract,venue,publicationTypes,citationCount,authors"}
    recs, total, token, first_url, err = [], None, None, None, None
    try:
        while True:
            p = dict(params)
            if token:
                p["token"] = token
            r = get(url, params=p, tries=8, base_sleep=5.0)
            first_url = first_url or r.url
            r.raise_for_status()
            js = r.json()
            total = js.get("total", total)
            for d in js.get("data", []) or []:
                ext = d.get("externalIds") or {}
                recs.append({"s2_id": d.get("paperId"), "doi": (ext.get("DOI") or "").lower() or None,
                             "pmid": ext.get("PubMed"), "title": d.get("title") or "", "year": d.get("year"),
                             "venue": d.get("venue"), "type": ",".join(d.get("publicationTypes") or []),
                             "abstract": d.get("abstract") or "",
                             "authors": "; ".join(a.get("name", "") for a in (d.get("authors") or [])[:6])})
            token = js.get("token")
            if not token:
                break
            time.sleep(2)
    except Exception as e:  # recorded, not fatal
        err = repr(e)
    return {"source": "semantic_scholar", "query": S2_QUERY, "url": first_url, "retrieved": now(),
            "reported_count": total, "error": err, "records": recs}


def run_gs(pages=10, delay=9.0):
    from bs4 import BeautifulSoup
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
    recs, count_txt, stopped, urls = [], None, None, []
    for p in range(pages):
        params = {"q": GS_QUERY, "hl": "en", "as_ylo": YEARS[0], "as_yhi": YEARS[1], "start": p * 10}
        try:
            r = requests.get("https://scholar.google.com/scholar", params=params, headers=ua, timeout=60)
        except requests.RequestException as e:
            stopped = f"page {p}: {e!r}"
            break
        urls.append(r.url)
        txt = r.text
        if r.status_code != 200 or "gs_captcha" in txt or "unusual traffic" in txt.lower():
            stopped = f"page {p}: HTTP {r.status_code} or CAPTCHA"
            break
        soup = BeautifulSoup(txt, "lxml")
        if count_txt is None:
            m = re.search(r"About ([\d,]+) results", txt) or re.search(r"([\d,]+) results", txt)
            count_txt = m.group(1) if m else None
        items = soup.select("div.gs_r.gs_or.gs_scl")
        if not items:
            stopped = f"page {p}: no result items"
            break
        for it in items:
            h = it.select_one("h3.gs_rt")
            a = h.select_one("a") if h else None
            meta = it.select_one("div.gs_a")
            snip = it.select_one("div.gs_rs")
            mt = meta.get_text(" ", strip=True) if meta else ""
            ym = re.findall(r"\b(19\d{2}|20[0-2]\d)\b", mt)
            recs.append({"gs_rank": len(recs) + 1, "title": re.sub(r"^\[[A-Z]+\]\s*", "", h.get_text(" ", strip=True)) if h else "",
                         "link": a.get("href") if a else None, "meta": mt, "year": int(ym[-1]) if ym else None,
                         "abstract": snip.get_text(" ", strip=True) if snip else "", "doi": None})
        time.sleep(delay)
    return {"source": "google_scholar", "query": GS_QUERY, "url": urls[0] if urls else None, "retrieved": now(),
            "reported_count": int(count_txt.replace(",", "")) if count_txt else None, "pages_fetched": len(urls),
            "stopped": stopped, "records": recs}


def oa_by_ids(ids):
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        r = get("https://api.openalex.org/works",
                params={"filter": "openalex_id:" + "|".join(chunk), "per-page": 50, "select": OA_SELECT})
        out.extend(r.json()["results"])
    return out


def run_chase():
    seeds_out, records = [], {}
    for key, doi in SEEDS.items():
        try:
            r = get(f"https://api.openalex.org/works/https://doi.org/{doi}", params={"select": OA_SELECT})
            if r.status_code != 200:
                seeds_out.append({"seed": key, "doi": doi, "resolved": False, "status": r.status_code})
                continue
            w = r.json()
        except Exception as e:
            seeds_out.append({"seed": key, "doi": doi, "resolved": False, "error": repr(e)})
            continue
        wid = w["id"].rsplit("/", 1)[-1]
        refs = [x.rsplit("/", 1)[-1] for x in (w.get("referenced_works") or [])]
        back = oa_by_ids(refs) if refs else []
        fwd, fcount, _ = openalex_paged(f"cites:{wid}", max_records=2000)
        for ww, rel in [(x, "backward") for x in back] + [(x, "forward") for x in fwd]:
            rec = oa_record(ww)
            k = rec["openalex_id"]
            if k not in records:
                rec["chase"] = []
                records[k] = rec
            records[k]["chase"].append(f"{rel}:{key}")
        seeds_out.append({"seed": key, "doi": doi, "resolved": True, "openalex_id": wid, "n_backward": len(back),
                          "n_references_listed": len(refs), "n_forward": len(fwd), "forward_reported": fcount})
        time.sleep(0.3)
    return {"source": "citation_chasing", "retrieved": now(), "seeds": seeds_out,
            "reported_count": len(records), "records": list(records.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="openalex,pubmed,s2,gs,chase")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log_p = out / "search_log.json"
    log = json.loads(log_p.read_text(encoding="utf-8")) if log_p.exists() else {}
    runners = {"openalex": run_openalex, "pubmed": run_pubmed, "s2": run_s2, "gs": run_gs, "chase": run_chase}
    for name in a.only.split(","):
        t0 = time.time()
        try:
            res = runners[name]()
        except Exception as e:
            res = {"source": name, "retrieved": now(), "error": repr(e), "records": []}
        (out / f"{name}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        log[name] = {k: v for k, v in res.items() if k != "records"}
        log[name]["n_records_saved"] = len(res.get("records", []))
        log[name]["seconds"] = round(time.time() - t0, 1)
        print(name, log[name].get("reported_count"), log[name]["n_records_saved"], log[name].get("error"),
              log[name].get("stopped"))
        log_p.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
