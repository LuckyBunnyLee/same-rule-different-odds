"""EXPLORATORY scratch (recent_probe): fetch WA results pages for block-start events outside the
repo's RT scope (400m, 400mH, relays) to separate start location from day at WCH2025.

Pages are cached under analysis/probe/wa_pages/ with a .meta.json sidecar (url, final url,
status, sha256, retrieved_at). Does NOT touch data/raw or its manifest. Throttled (>= 3 s)."""
from __future__ import annotations
import gzip, hashlib, json, random, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data" / "scripts"))
from config import COMPETITIONS, comp_key, results_url  # noqa: E402
from wa_http import extract_next_data  # noqa: E402  (pure function)

OUT = ROOT / "analysis" / "probe" / "wa_pages"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) ssac-rt-research/0.1 (academic research; throttled; cached)")
S = requests.Session(); S.headers.update({"User-Agent": UA, "Accept-Language": "en"})
_last = [0.0]

def get(url, path):
    mp = path.with_name(path.name + ".meta.json")
    if mp.exists():
        m = json.loads(mp.read_text(encoding="utf-8"))
        if path.exists() or m.get("status") == 404:
            return m
    path.parent.mkdir(parents=True, exist_ok=True)
    wait = 3.0 + random.uniform(0, 0.5) - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    r = S.get(url, timeout=60, allow_redirects=True)
    body = r.content if r.status_code == 200 else b""
    if body:
        with gzip.open(path, "wb") as fh:
            fh.write(body)
    m = {"url": url, "final_url": r.url, "status": r.status_code, "bytes": len(body),
         "sha256": hashlib.sha256(body).hexdigest() if body else "",
         "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    mp.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return m

def data_of(path):
    with gzip.open(path, "rb") as fh:
        return extract_next_data(fh.read().decode("utf-8"))

EVENTS = [("men", "400-metres"), ("women", "400-metres"),
          ("men", "400-metres-hurdles"), ("women", "400-metres-hurdles"),
          ("men", "4x100-metres-relay"), ("women", "4x100-metres-relay"),
          ("men", "4x400-metres-relay"), ("women", "4x400-metres-relay"),
          ("mixed", "4x400-metres-relay-mixed")]

def main(comps):
    for c in COMPETITIONS:
        if comp_key(c) not in comps:
            continue
        for sex_slug, disc in EVENTS:
            p = OUT / comp_key(c) / f"{sex_slug}-{disc}-final.html.gz"
            m = get(results_url(c, sex_slug, disc, "final"), p)
            if m["status"] != 200:
                print(f"[miss] {comp_key(c)} {sex_slug} {disc}: {m['status']}", flush=True)
                continue
            d = data_of(p)
            phases = d["props"]["pageProps"].get("allEventPhasesByDiscipline") or []
            print(f"[ok] {comp_key(c)} {sex_slug} {disc}: " + ", ".join(ph["phaseNameUrlSlug"] for ph in phases), flush=True)
            for ph in phases:
                slug = ph["phaseNameUrlSlug"]
                if slug == "final":
                    continue
                p2 = OUT / comp_key(c) / f"{sex_slug}-{disc}-{slug}.html.gz"
                m2 = get(results_url(c, sex_slug, disc, slug), p2)
                print(f"     - {slug}: {m2['status']}", flush=True)

if __name__ == "__main__":
    main(sys.argv[1].split(","))
