"""Step 5a: OCR the text of every cached Seiko start-waveform image.

For each waveform JPG (data/raw/wa/waveform/<id>/<file>.jpg, from
fetch_docs.py --kind waveform) this writes one JSON file with the raw OCR boxes
to --ocr-dir (default data/raw/wa/waveform_ocr/<id>/<file>.json):

* ``header``: the top 145 px (title, race label, 'Heat : 001', 'Attempt : 002',
  'Ready Time : 1.810 sec', image timestamp);
* ``lanes``: the left 700 px of the nine lane panels (lane label, per-lane RT
  text, bib, name, country), after painting out the magenta 'set' marker line,
  which otherwise cuts through the RT digits and corrupts the OCR.

OCR engine: RapidOCR (PP-OCR models on onnxruntime, CPU), pinned in the
environment as rapidocr_onnxruntime==1.4.4. Existing JSON files are skipped, so
the step is resumable. Parsing/validation happens in build_waveform.py.

Usage: .venv/Scripts/python.exe data/scripts/ocr_waveforms.py [--ocr-dir DIR] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from wa_http import RAW

WF_DIR = RAW / "wa" / "waveform"
OCR_DIR = RAW / "wa" / "waveform_ocr"
HEADER_Y1 = 145            # header band height (px) in the 1800x2700 image
STRIP = (140, 2545, 0, 700)  # y0, y1, x0, x1 of the lane-text strip
BG = np.array([255, 255, 191], dtype=np.uint8)   # panel background (pale yellow)


def magenta_mask(im: np.ndarray) -> np.ndarray:
    r, g, b = (im[..., i].astype(np.int16) for i in range(3))
    core = (r - g > 70) & (b - g > 40) & (r > 120) & (b > 90)
    halo = (r > 230) & (b > 200) & (g < 235) & (b - g > 20)   # pink anti-aliasing
    return core | halo


def paint_out_magenta(im: np.ndarray) -> np.ndarray:
    out = im.copy()
    out[magenta_mask(im)] = BG
    return out


def boxes(result) -> list[dict]:
    out = []
    for box, text, score in (result or []):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        out.append(dict(x0=round(min(xs), 1), x1=round(max(xs), 1), y0=round(min(ys), 1),
                        y1=round(max(ys), 1), text=text, score=round(float(score), 3)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-dir", default=str(OCR_DIR))
    ap.add_argument("--limit", type=int, default=0, help="stop after N new images (0 = all)")
    a = ap.parse_args(argv)
    from rapidocr_onnxruntime import RapidOCR   # imported lazily (slow)
    engine = RapidOCR()
    ocr_dir = Path(a.ocr_dir)
    imgs = sorted(WF_DIR.glob("*/*.jpg"))
    done = 0
    t0 = time.time()
    for img in imgs:
        out = ocr_dir / img.parent.name / (img.stem + ".json")
        if out.exists():
            continue
        im = np.asarray(Image.open(img).convert("RGB"))
        hdr, _ = engine(im[:HEADER_Y1, :])
        y0, y1, x0, x1 = STRIP
        strip = paint_out_magenta(im[y0:y1, x0:x1])
        lanes, _ = engine(strip)
        rec = dict(image=str(img.relative_to(RAW.parent.parent)).replace("\\", "/"),
                   shape=list(im.shape), strip=list(STRIP), header=boxes(hdr),
                   lanes=boxes(lanes), engine="rapidocr_onnxruntime 1.4.4")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        done += 1
        if done % 10 == 0:
            print(f"{done} images OCR'd ({time.time() - t0:.0f} s)", flush=True)
        if a.limit and done >= a.limit:
            break
    print(f"OCR done: {done} new images, {len(imgs)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
