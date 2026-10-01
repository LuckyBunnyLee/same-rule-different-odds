#!/usr/bin/env python3
"""Render the SSAC27 abstract from its template. Every number comes from analysis/numbers.json.

  .venv\\Scripts\\python.exe paper\\render.py                 # DRAFT render + word count
  .venv\\Scripts\\python.exe paper\\render.py --final         # only once results are final
  .venv\\Scripts\\python.exe paper\\render.py --selftest      # prove every guard fires, then exit

Template syntax (paper/abstract.template.md)
  {{key}}                value of numbers.json["numbers"][key]["value"]
  {{key@lo}} {{key@hi}}  95% CI bounds (ci95[0], ci95[1]); {{key@p}} the p-value; {{key@name}} any
                         other field of the entry (dotted path into nested dicts: @by_meet.WCH2022)
  {{key|t1|t2|fmt}}      transforms applied left to right, then a format spec. Transforms:
                           ms (x1000), pct (x100), neg, abs, champ ('WCH2022' -> '2022 World
                           Championships'), year ('WCH2022' -> '2022'), keys (dict -> 'a, b'),
                           count (len of a list or dict), word (integer 0-10 -> 'zero'..'ten')
                         Format: a Python spec (.2f, .0f, ,d, ,.0f) or sig2 (two significant digits).
                         A float with no format is an error: precision is always chosen explicitly.
  <!-- assert: EXPR -->  pins a qualitative claim in the prose ("excludes", "all", "fastest").
                         EXPR uses [key] / [key@field] tokens and must be True or the render fails.
  <!-- draft-note: T --> a known gap, printed in the DRAFT banner. --final refuses to render while any remain.
  <!-- ... -->           any other comment is an author note, stripped from the render.

Measurement numbers: keys 'measure.*' are expected in analysis/numbers.json. Until they are merged, DRAFT
renders fall back to analysis/measure/numbers.json (flat format; 'X_ci95' becomes X's CI) and
say so. --final never falls back: every key must be in analysis/numbers.json, as the brief requires.

Fails loudly (non-zero exit, every problem listed at once) on: a missing or null key or field, a
transform or format that does not apply, a False assertion, a numeric literal in the template prose
that is not a named design constant (list below), a MOCK or unreadable numbers file, and a word
count of 500 or more (SSAC: fewer than 500 words including the title), or more than 470 words by a
counter that also splits hyphenated words (margin against SSAC's counter). Staleness: every input recorded
by a result JSON behind numbers.json is re-hashed (and every flat source merged by data tag); a changed input
is flagged in DRAFT and refused by --final, unless that one input is named with --accept-stale and a
--stale-reason (e.g. a rerun into scratch showed no rendered number changes); the exception is written into
the output's provenance header.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD_LIMIT = 500          # SSAC: "fewer than 500 words, including the title"
STRICT_LIMIT = 485        # margin: <= 485 by a counter that splits hyphenated words (margin vs SSAC's 500)

# Design constants and citation facts that may appear as literals in the template prose. Each entry
# is (regex over the prose with placeholders removed, name). The regex must match the literal WITH
# its context, so '0.100' is allowed only as '0.100 s'. Anything else containing a digit fails.
ALLOWED_LITERALS = [
    (r"0\.100 s", "false-start threshold (World Athletics TR 16.6)"),
    (r"0\.090", "lower edge of the near-threshold window used by descriptive.py (design)"),
    (r"95%", "confidence level (design)"),
    (r"(?:per|each) 100 ms", "slope unit (design)"),
    (r"per 1,000", "rate unit (design)"),
    (r"10th|90th", "hold percentiles compared in fairness_sim.py (design)"),
    (r"r [=≈] 0\.16", "Haugen et al. 2013 published correlation (literature input, design value)"),
    (r"(?:Haugen et al\.|Haugen, Shalfawi and Tønnessen),? \(?2013\)?", "citation year"),
    (r"Fiore et al\.,? \(?2025\)?", "citation year"),
    (r"Pain (?:&|and) Hibbs,? \(?2007\)?", "citation year"),
    (r"Brosnan et al\.,? \(?2017\)?", "citation year"),
    (r"Milloz et al\.,? \(?2021\)?", "citation year"),
    (r"Han et al\.,? \(?2025\)?", "citation year"),
    (r"Lipps et al\.(?:'s)?,? \(?2011\)?", "citation year"),
    (r"\|r\| ≥ 0\.16", "Haugen et al. 2013 published correlation as a simulation threshold (design value)"),
    (r"0\.001 s", "World Athletics photo-finish timing tolerance (Book C, lit/policy_mechanism.md; literature input)"),
    (r"1-in-1,000", "tail probability defining the barrier, as in Fiore et al. 2025 (design constant)"),
    (r"0\.094 s", "Fiore et al. 2025 re-estimated threshold, men, 1e-3 tail (literature input, lit/review.md)"),
    (r"0\.115 s", "Brosnan et al. 2017 revised threshold for men (women: 119 ms) (literature input, lit/review.md)"),
    (r"Figure [12]", "figure number"),
    (r"(?:60|100|110|200) m\b", "event distance"),
]

COMP_NAMES = {"WCH": "World Championships", "OG": "Olympics", "WIC": "World Indoor Championships"}
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

PH = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
SPEC = re.compile(r"^(?:sig2|,?(?:\.\d+)?[dfg%])$")
ASSERT = re.compile(r"<!--\s*assert:\s*(.+?)\s*-->", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
DRAFT_NOTE = re.compile(r"<!--\s*draft-note:\s*(.+?)\s*-->", re.S)
MEASURE_FALLBACK = "analysis/measure/numbers.json"
USED: set = set()
TOKEN = re.compile(r"\[([A-Za-z_][\w.\-]*(?:@[\w.\-]+)?)\]")


class RenderError(Exception):
    pass


# ------------------------------------------------------------------ number lookup and formatting

def lookup(numbers: dict, ref: str):
    """ref = 'key' or 'key@field'; raises RenderError when absent or null."""
    key, _, field = ref.partition("@")
    USED.add(key)
    if key not in numbers:
        raise RenderError(f"missing key: {key}")
    entry = numbers[key]
    if not isinstance(entry, dict):
        entry = {"value": entry}
    if not field or field == "value":
        val = entry.get("value")
    elif field in ("lo", "hi"):
        ci = entry.get("ci95")
        if not ci or ci[0 if field == "lo" else 1] is None:
            raise RenderError(f"missing 95% CI for {key} (asked for @{field})")
        val = ci[0 if field == "lo" else 1]
    else:
        val = entry
        for part in field.split("."):
            if not isinstance(val, dict) or part not in val:
                raise RenderError(f"missing field @{field} in {key}")
            val = val[part]
    if val is None or (isinstance(val, float) and math.isnan(val)):
        raise RenderError(f"null value for {ref}")
    return val


def apply_transform(val, t: str, ref: str):
    num = isinstance(val, (int, float)) and not isinstance(val, bool)
    if t in ("ms", "pct", "neg", "abs"):
        if not num:
            raise RenderError(f"transform '{t}' needs a number, got {val!r} ({ref})")
        return {"ms": val * 1000, "pct": val * 100, "neg": -val, "abs": abs(val)}[t]
    if t in ("champ", "year"):
        m = re.fullmatch(r"([A-Z]+)(\d{4})", str(val))
        if not m or m.group(1) not in COMP_NAMES:
            raise RenderError(f"transform '{t}' needs a championship code like WCH2022, got {val!r} ({ref})")
        return m.group(2) if t == "year" else f"{m.group(2)} {COMP_NAMES[m.group(1)]}"
    if t == "keys":
        if not isinstance(val, dict):
            raise RenderError(f"transform 'keys' needs a dict ({ref})")
        return ", ".join(val)
    if t == "count":
        if not isinstance(val, (list, dict)):
            raise RenderError(f"transform 'count' needs a list or dict ({ref})")
        return len(val)
    if t == "word":
        if not (num and float(val).is_integer() and 0 <= val <= 10):
            raise RenderError(f"transform 'word' needs an integer 0-10, got {val!r} ({ref})")
        return WORDS[int(val)]
    raise RenderError(f"unknown transform '{t}' ({ref})")


def fmt_number(val, spec: str, ref: str) -> str:
    if spec == "sig2":
        if val == 0:
            return "0"
        d = max(0, 1 - int(math.floor(math.log10(abs(val)))))
        s = f"{round(val, d):.{d}f}"
    else:
        try:
            s = format(val, spec)
        except (ValueError, TypeError) as e:
            raise RenderError(f"format '{spec}' does not apply to {val!r} ({ref}): {e}")
    if re.fullmatch(r"-0(?:\.0*)?", s):          # never print a negative zero
        s = s[1:]
    return s


def render_placeholder(numbers: dict, expr: str) -> str:
    parts = [p.strip() for p in expr.split("|")]
    ref, ops = parts[0], parts[1:]
    val = lookup(numbers, ref)
    spec = None
    for i, op in enumerate(ops):
        if SPEC.match(op):
            if i != len(ops) - 1:
                raise RenderError(f"format spec '{op}' must come last ({expr})")
            spec = op
        else:
            val = apply_transform(val, op, ref)
    if isinstance(val, bool):
        raise RenderError(f"{ref} is a boolean; use it in an assert, not in prose")
    if isinstance(val, str):
        if spec:
            raise RenderError(f"format '{spec}' applied to text {val!r} ({ref})")
        return val
    if isinstance(val, int) and spec is None:
        return str(val)
    if isinstance(val, float) and spec is None:
        raise RenderError(f"{ref} is a float ({val!r}); give an explicit format such as .2f or ,.0f")
    return fmt_number(val, spec, ref)


def eval_assert(numbers: dict, expr: str) -> bool:
    env_vals = {}

    def sub(m):
        name = f"_v{len(env_vals)}"
        env_vals[name] = lookup(numbers, m.group(1))
        return name

    py = TOKEN.sub(sub, expr)
    py = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", py))
    safe = {"abs": abs, "min": min, "max": max, "len": len, "set": set, "list": list, "all": all, "any": any,
            "int": int, "float": float}
    try:
        return bool(eval(py, {"__builtins__": {}}, {**safe, **env_vals}))   # noqa: S307 (own template)
    except RenderError:
        raise
    except Exception as e:                                                  # noqa: BLE001
        raise RenderError(f"assert could not be evaluated: {expr!r} ({e})")


# ------------------------------------------------------------------ template checks

def literal_audit(template: str) -> list[str]:
    """Numeric literals in the prose (placeholders and comments removed) that are not design constants."""
    prose = PH.sub(" ", COMMENT.sub(" ", template))
    for rx, _ in ALLOWED_LITERALS:
        prose = re.sub(rx, " ", prose)
    bad = []
    for m in re.finditer(r"\S*\d\S*", prose):
        ctx = " ".join(prose[max(0, m.start() - 40):m.end() + 30].split())
        bad.append(f"{m.group(0)!r} in ...{ctx}...")
    return bad


def md_to_plain(md: str) -> str:
    """Rendered markdown -> the text a reader sees (for word counts)."""
    t = COMMENT.sub(" ", md)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)           # image links: not words on the page
    t = re.sub(r"(?m)^\s*#+\s*", "", t)                     # heading markers
    t = re.sub(r"\*\*|__|`", "", t)                          # bold / code markers
    t = re.sub(r"(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)", "", t)    # italic markers
    t = re.sub(r"(?m)^\s*\|?\s*:?-{3,}.*$", " ", t)          # table rules
    t = t.replace("|", " ")
    return t


def count_words(text: str) -> tuple[int, int]:
    """(words with a letter or digit, all whitespace-separated tokens incl. lone dashes)."""
    toks = text.split()
    return sum(1 for w in toks if re.search(r"[A-Za-z0-9]", w)), len(toks)


def count_strict(text: str) -> int:
    """Words when hyphens, dashes and slashes also split words (the most aggressive common counter)."""
    return sum(1 for tok in text.split() for w in re.split(r"[-\u2010-\u2015/]", tok)
               if re.search(r"[A-Za-z0-9]", w))


def section_counts(md_body: str) -> list[tuple[str, int]]:
    out, cur, buf = [], "title", []
    for line in md_body.splitlines():
        m = re.match(r"^\s*(#+)\s*(.*)$", line)
        if m and len(m.group(1)) >= 2:
            out.append((cur, count_strict(md_to_plain("\n".join(buf)))))
            cur, buf = m.group(2).strip(), [line]
        elif re.match(r"^\s*\*\*Figure \d", line):
            out.append((cur, count_strict(md_to_plain("\n".join(buf)))))
            cur, buf = "caption: " + re.sub(r"\W+$", "", line.split(".")[0].strip("* ")), [line]
        else:
            buf.append(line)
    out.append((cur, count_strict(md_to_plain("\n".join(buf)))))
    return out


# ------------------------------------------------------------------ main render

def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def load_numbers(path: Path) -> tuple[dict, dict]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RenderError(f"cannot read numbers file {path}: {e}")
    if d.get("mock") or "numbers" not in d:
        raise RenderError(f"{path} is MOCK or has no 'numbers' block")
    return d["numbers"], d


def stale_inputs(meta: dict) -> list[str]:
    """Inputs whose bytes changed after numbers.json was built (each result JSON records path + sha256_12)."""
    out = []
    for src in meta.get("_sources", {}):
        sp = ROOT / src
        if not sp.exists():
            out.append(f"{src}: result file missing")
            continue
        for v in json.loads(sp.read_text(encoding="utf-8")).get("inputs", []):
            p, h = ROOT / v.get("path", ""), v.get("sha256_12")
            if not h or not p.is_file():
                continue
            now = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
            if now != h:
                out.append(f"{v['path']} changed after {src} was computed ({h} -> {now})")
    for src, info in meta.get("_sources", {}).items():       # flat sources merged by data tag
        sp = ROOT / src
        for tag in info.get("data", []):
            m = re.match(r"(.+?)@sha256:([0-9a-f]{12})", tag)
            if m and m.group(1) == sp.name and sp.is_file():
                now = hashlib.sha256(sp.read_bytes()).hexdigest()[:12]
                if now != m.group(2):
                    out.append(f"{src} changed after numbers.json merged it ({m.group(2)} -> {now})")
    return sorted(set(out))


def load_measure_fallback(path: Path, numbers: dict) -> set:
    """DRAFT only: add flat measurement numbers as 'measure.<key>' where analysis/numbers.json lacks them."""
    if not path.exists():
        return set()
    flat = json.loads(path.read_text(encoding="utf-8"))
    added = set()
    for k, v in flat.items():
        if k.startswith("_") or k.endswith("_ci95"):
            continue
        key = f"measure.{k}"
        if key not in numbers:
            entry = {"value": v, "source": MEASURE_FALLBACK}
            if isinstance(flat.get(f"{k}_ci95"), list):
                entry["ci95"] = flat[f"{k}_ci95"]
            numbers[key] = entry
            added.add(key)
    return added


def render(template: str, numbers: dict) -> tuple[str, list[str]]:
    errors = []
    for m in re.finditer(r"<!--\s*(assert|draft-note)\b(.*?)-->", template, re.S):
        if not re.match(r"\s*:", m.group(2)):
            errors.append(f"malformed {m.group(1)} comment (needs '{m.group(1)}:'), so it would be silently "
                          f"ignored: {m.group(0)[:90]!r}")
    for m in ASSERT.finditer(template):
        try:
            if not eval_assert(numbers, m.group(1)):
                vals = {t: lookup(numbers, t) for t in TOKEN.findall(m.group(1))}
                errors.append(f"assert FALSE: {m.group(1)}   values: {vals}")
        except RenderError as e:
            errors.append(str(e))
    errors += [f"typed numeric literal (not a named design constant): {b}" for b in literal_audit(template)]

    def sub(m):
        try:
            return render_placeholder(numbers, m.group(1))
        except RenderError as e:
            errors.append(f"{{{{{m.group(1)}}}}}: {e}")
            return "??"

    # drop comment-only lines entirely, so sentences separated by an assert stay in one paragraph
    stripped = re.sub(r"(?ms)^[ \t]*<!--.*?-->[ \t]*\n", "", template)
    body = PH.sub(sub, COMMENT.sub("", stripped))
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body, errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--numbers", default="analysis/numbers.json")
    ap.add_argument("--template", default="paper/abstract.template.md")
    ap.add_argument("--out", default="paper/abstract.md")
    ap.add_argument("--final", action="store_true", help="drop the DRAFT banner (only once results are final)")
    ap.add_argument("--selftest", action="store_true", help="prove the guards fire, then exit")
    ap.add_argument("--accept-stale", action="append", default=[], metavar="PATH",
                    help="with --final: accept staleness of this one input (repo-relative path); needs --stale-reason")
    ap.add_argument("--stale-reason", default="",
                    help="why the accepted stale input cannot change any rendered number (recorded in the output)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    npath = Path(a.numbers) if Path(a.numbers).is_absolute() else ROOT / a.numbers
    tpath = Path(a.template) if Path(a.template).is_absolute() else ROOT / a.template
    opath = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    try:
        numbers, meta = load_numbers(npath)
    except RenderError as e:
        print(f"RENDER FAILED: {e}", file=sys.stderr)
        return 2
    template = tpath.read_text(encoding="utf-8")
    fallback = set() if a.final else load_measure_fallback(ROOT / MEASURE_FALLBACK, numbers)
    USED.clear()
    body, errors = render(template, numbers)
    notes = [" ".join(n.split()) for n in DRAFT_NOTE.findall(template)]
    used_fallback = sorted(USED & fallback)
    stale = stale_inputs(meta)
    def _norm(t: str) -> str:
        return t.replace("\\", "/")
    accepted = [x for x in stale if any(_norm(x).startswith(_norm(pa) + " ") for pa in a.accept_stale)]
    remaining = [x for x in stale if x not in accepted]
    if a.accept_stale and not (a.final and a.stale_reason.strip()):
        errors.append("--accept-stale needs --final and a non-empty --stale-reason")
    if a.final and notes:
        errors.append(f"--final refused: {len(notes)} draft-note(s) remain in the template: " + " | ".join(notes))
    if a.final and remaining:
        errors.append("--final refused: numbers.json is stale (rerun analysis/run_all.py): " + "; ".join(remaining))

    plain = md_to_plain(body)
    n_words, n_tokens = count_words(plain)
    n_strict = count_strict(plain)
    if max(n_words, n_tokens) >= WORD_LIMIT:
        errors.append(f"word count {n_words} words / {n_tokens} tokens: SSAC requires fewer than {WORD_LIMIT}")
    if n_strict > STRICT_LIMIT:
        errors.append(f"hyphen-splitting word count {n_strict} > {STRICT_LIMIT} (margin rule for SSAC's counter)")
    if errors:
        print(f"RENDER FAILED ({len(errors)} problem(s)); nothing written:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("hyphen-split words by section (for cutting):", file=sys.stderr)
        for name, n in section_counts(body):
            print(f"  {n:4d}  {name}", file=sys.stderr)
        return 2

    sha = hashlib.sha256(npath.read_bytes()).hexdigest()[:12]
    prov = (f"<!-- Generated by paper/render.py from {rel(tpath)} and "
            f"{rel(npath)} (sha256 {sha}); do not edit by hand. "
            f"Data versions: {'; '.join(meta.get('_data_versions', []))} -->\n")
    if a.final and accepted:
        prov += (f"<!-- ACCEPTED STALE INPUT(S) at --final: {'; '.join(accepted)}. Reason given: "
                 f"{a.stale_reason.strip()} -->\n")
    banner = ""
    if not a.final:
        banner = ("> **DRAFT: not for submission.** Numbers are preliminary until "
                  "results are final.\n")
        for n in notes:
            banner += f">\n> - Pending: {n}\n"
        if used_fallback:
            banner += (f">\n> - {len(used_fallback)} measurement number(s) read from {MEASURE_FALLBACK}, not yet "
                       f"merged into analysis/numbers.json: {', '.join(used_fallback)}\n")
        for st in stale:
            banner += f">\n> - STALE: {st}\n"
        banner += "\n"
    opath.write_text(prov + banner + body, encoding="utf-8")

    n_asserts = len(ASSERT.findall(template))
    n_ph = len(PH.findall(COMMENT.sub("", template)))
    print(f"wrote {rel(opath)} ({'FINAL' if a.final else 'DRAFT'}); "
          f"{n_ph} placeholders, {n_asserts} assertions, numbers sha256 {sha}")
    if used_fallback:
        print(f"NOTE: {len(used_fallback)} key(s) from the DRAFT-only fallback {MEASURE_FALLBACK}: "
              + ", ".join(used_fallback))
    for n in notes:
        print(f"DRAFT-NOTE: {n}")
    for st in stale:
        print(f"STALE{' (ACCEPTED: ' + a.stale_reason.strip() + ')' if st in accepted else ''}: {st}")
    print(f"WORD COUNT: {n_strict} words splitting hyphens (limit {STRICT_LIMIT}); {n_words} words / "
          f"{n_tokens} whitespace tokens unsplit (SSAC limit: fewer than {WORD_LIMIT}); title and caption included")
    for name, n in section_counts(body):
        print(f"  {n:4d}  {name}")
    return 0


# ------------------------------------------------------------------ selftest

def selftest() -> int:
    """Each guard must fire on a case built to trip it, and a clean case must pass."""
    nums = {"a.x": {"value": 0.3291, "ci95": [-0.146, 0.805], "p": 0.174},
            "a.flag": {"value": True}, "a.name": {"value": "x", "fastest": "WCH2022"},
            "a.n": {"value": 4, "by_meet": {"WCH2022": 4}}}
    ok_t = ("# T\n{{a.x|.1f}} (95% CI {{a.x@lo|.1f}} to {{a.x@hi|.1f}}) at the {{a.name@fastest|champ}}; "
            "{{a.n|word}} of them per 1,000 below 0.100 s\n<!-- assert: [a.flag] == true and [a.x@hi] < 1.466 -->\n"
            "<!-- assert: list([a.n@by_meet]) == [[a.name@fastest]] -->\n")
    cases = [
        ("clean template renders", ok_t, nums, True),
        ("missing key fails", ok_t.replace("a.x|.1f", "a.nope|.1f"), nums, False),
        ("missing CI field fails", ok_t, {**nums, "a.x": {"value": 0.3}}, False),
        ("false assertion fails", ok_t, {**nums, "a.flag": {"value": False}}, False),
        ("assertion on a moved bound fails", ok_t, {**nums, "a.x": {"value": 0.3, "ci95": [-0.1, 1.6]}}, False),
        ("changed 'fastest' breaks the by-meet assertion", ok_t,
         {**nums, "a.name": {"value": "x", "fastest": "WCH2025"}}, False),
        ("typed measurement fails", ok_t + "RT was 0.136 s.\n", nums, False),
        ("float without explicit format fails", ok_t.replace("{{a.x|.1f}}", "{{a.x}}"), nums, False),
        ("null value fails", ok_t, {**nums, "a.x": {"value": None, "ci95": [-0.1, 0.8]}}, False),
        ("malformed assert fails instead of being ignored", ok_t + "<!-- assert (why): [a.x] > 5 -->\n", nums, False),
    ]
    fails = 0
    for name, t, n, expect_ok in cases:
        body, errs = render(t, n)
        ok = not errs
        good = ok == expect_ok
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'}  {name}" + ("" if ok else f"   -> {errs[0][:110]}"))
    # end to end through main(): a numbers file lacking a key must exit non-zero and write nothing
    with tempfile.TemporaryDirectory() as td:
        tp, np_, op = Path(td) / "t.md", Path(td) / "n.json", Path(td) / "o.md"
        tp.write_text(ok_t, encoding="utf-8")
        np_.write_text(json.dumps({"numbers": {k: v for k, v in nums.items() if k != "a.n"}}), encoding="utf-8")
        rc = main(["--numbers", str(np_), "--template", str(tp), "--out", str(op)])
        good = rc != 0 and not op.exists()
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'}  main() exits non-zero and writes nothing on a missing key (rc={rc})")
        # a draft-note is listed in a DRAFT banner, and blocks --final
        np_.write_text(json.dumps({"numbers": nums}), encoding="utf-8")
        tp.write_text(ok_t + "<!-- draft-note: pending check -->\n", encoding="utf-8")
        rc = main(["--numbers", str(np_), "--template", str(tp), "--out", str(op)])
        good = rc == 0 and "Pending: pending check" in op.read_text(encoding="utf-8")
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'}  DRAFT render lists the draft-note in its banner (rc={rc})")
        op.unlink(missing_ok=True)
        rc = main(["--numbers", str(np_), "--template", str(tp), "--out", str(op), "--final"])
        good = rc != 0 and not op.exists()
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'}  --final refuses while a draft-note remains (rc={rc})")
        # measure.* keys: DRAFT may fall back to analysis/measure/numbers.json, --final may not
        if (ROOT / MEASURE_FALLBACK).exists():
            tp.write_text("# T\n{{measure.real_seiko_n}} starts\n", encoding="utf-8")
            rc_d = main(["--numbers", str(np_), "--template", str(tp), "--out", str(op)])
            op.unlink(missing_ok=True)
            rc_f = main(["--numbers", str(np_), "--template", str(tp), "--out", str(op), "--final"])
            good = rc_d == 0 and rc_f != 0 and not op.exists()
            fails += not good
            print(f"{'ok  ' if good else 'FAIL'}  measure.* fallback works in DRAFT (rc={rc_d}) and is refused by --final (rc={rc_f})")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp, res, npf, tp, op = td / "in.csv", td / "res.json", td / "n.json", td / "t.md", td / "o.md"
        inp.write_text("a\n", encoding="utf-8")
        h = hashlib.sha256(inp.read_bytes()).hexdigest()[:12]
        res.write_text(json.dumps({"inputs": [{"path": str(inp), "sha256_12": h}]}), encoding="utf-8")
        npf.write_text(json.dumps({"numbers": nums, "_sources": {str(res): {"name": "r", "data": []}}}), encoding="utf-8")
        tp.write_text(ok_t, encoding="utf-8")
        rc0 = main(["--numbers", str(npf), "--template", str(tp), "--out", str(op), "--final"])
        op.unlink(missing_ok=True)
        inp.write_text("b\n", encoding="utf-8")                       # input changes after the result was computed
        rc1 = main(["--numbers", str(npf), "--template", str(tp), "--out", str(op), "--final"])
        wrote1 = op.exists()
        rc2 = main(["--numbers", str(npf), "--template", str(tp), "--out", str(op), "--final",
                    "--accept-stale", str(inp), "--stale-reason", "selftest: verified no numeric effect"])
        recorded = op.exists() and "ACCEPTED STALE INPUT" in op.read_text(encoding="utf-8")
        op.unlink(missing_ok=True)
        rc3 = main(["--numbers", str(npf), "--template", str(tp), "--out", str(op), "--final",
                    "--accept-stale", str(inp)])
        good = rc0 == 0 and rc1 != 0 and not wrote1 and rc2 == 0 and recorded and rc3 != 0
        fails += not good
        print(f"{'ok  ' if good else 'FAIL'}  staleness blocks --final (rc={rc1}); named+reasoned override passes and is "
              f"recorded (rc={rc2}, recorded={recorded}); override without reason refused (rc={rc3})")
    print("SELFTEST " + ("PASSED" if fails == 0 else f"FAILED ({fails})"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
