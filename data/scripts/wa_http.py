"""Polite, cached HTTP fetching for the RT data pipeline.

Every network response is written to data/raw/ together with a sidecar
``<file>.meta.json`` (url, final url after redirects, HTTP status, bytes,
sha256, retrieved_at in UTC). A cached file is never re-downloaded unless
``force=True``, so re-running any script is offline and deterministic once the
cache is populated. Requests are throttled (MIN_INTERVAL seconds between
network calls) and every download is also appended to data/raw/manifest.csv.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]          # .../ssac
DATA = ROOT / "data"
RAW = DATA / "raw"
DERIVED = DATA / "derived"
MANIFEST = RAW / "manifest.csv"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "ssac-rt-research/0.1 (academic research; throttled; cached)")
MIN_INTERVAL = 2.5      # seconds between network requests (politeness)

_session: requests.Session | None = None
_last_request = [0.0]


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": UA, "Accept-Language": "en"})
    return _session


def _throttle() -> None:
    wait = MIN_INTERVAL + random.uniform(0, 0.5) - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.time()


def meta_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.name + ".meta.json")


def read_meta(cache_path: Path) -> dict | None:
    mp = meta_path(cache_path)
    if mp.exists():
        return json.loads(mp.read_text(encoding="utf-8"))
    return None


def fetch(url: str, cache_path: Path, gz: bool = False, force: bool = False,
          retries: int = 3, ok_404: bool = True) -> dict:
    """Download ``url`` to ``cache_path`` (gzip-compressed if ``gz``).

    Returns the metadata dict. On HTTP 404 the metadata is still cached (status
    404, no body) so we do not hammer missing resources on re-runs.
    """
    cache_path = Path(cache_path)
    meta = read_meta(cache_path)
    if meta is not None and not force and (cache_path.exists() or meta.get("status") == 404):
        meta["from_cache"] = True
        return meta

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(retries):
        _throttle()
        try:
            r = _get_session().get(url, timeout=60, allow_redirects=True)
        except requests.RequestException as exc:          # network hiccup
            last_err = exc
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            last_err = RuntimeError(f"HTTP {r.status_code}")
            time.sleep(15 * (attempt + 1))
            continue
        break
    else:
        raise RuntimeError(f"failed to fetch {url}: {last_err}")

    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = r.content if r.status_code == 200 else b""
    if r.status_code == 200:
        if gz:
            with gzip.open(cache_path, "wb") as fh:
                fh.write(body)
        else:
            cache_path.write_bytes(body)
    elif r.status_code != 404 or not ok_404:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")

    meta = {
        "url": url,
        "final_url": r.url,
        "status": r.status_code,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest() if body else "",
        "content_type": r.headers.get("Content-Type", ""),
        "retrieved_at": retrieved_at,
        "cache_path": str(cache_path.relative_to(ROOT)).replace("\\", "/"),
        "gzip": gz,
    }
    meta_path(cache_path).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    new = not MANIFEST.exists()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["retrieved_at", "status", "bytes", "sha256",
                                           "url", "final_url", "cache_path"])
        if new:
            w.writeheader()
        w.writerow({k: meta[k] for k in w.fieldnames})
    meta["from_cache"] = False
    return meta


def read_cached_text(cache_path: Path) -> str:
    cache_path = Path(cache_path)
    if cache_path.suffix == ".gz":
        with gzip.open(cache_path, "rb") as fh:
            return fh.read().decode("utf-8")
    return cache_path.read_text(encoding="utf-8")


_NEXT_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def extract_next_data(html: str) -> dict:
    """Return the Next.js ``__NEXT_DATA__`` JSON embedded in a WA page."""
    m = _NEXT_RE.search(html)
    if not m:
        raise ValueError("no __NEXT_DATA__ block found")
    return json.loads(m.group(1))
