#!/usr/bin/env python3
"""Scan the repository for secrets, tokens, local absolute paths and e-mail addresses (simple regexes).

    python scripts/scan_secrets.py            # exit code 1 if anything matches

Scans every file git would commit (falls back to all files when git is unavailable), text and binary alike.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PATTERNS = {
    "private key block": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key id": rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "OpenAI / Anthropic key": rb"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b",
    "Slack token": rb"\bxox[abposr]-[A-Za-z0-9\-]{10,}\b",
    "Google API key": rb"\bAIza[0-9A-Za-z_\-]{35}\b",
    "Telegram bot token": rb"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b",
    "Discord bot token": rb"\b[MN][A-Za-z\d]{23,25}\.[\w\-]{6}\.[\w\-]{27,}\b",
    "JSON web token": rb"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    "Hugging Face token": rb"\bhf_[A-Za-z0-9]{30,}\b",
    "bearer header": rb"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{16,}",
    "credential assignment": rb"(?i)\b(?:api[_-]?key|secret|passwd|password|access[_-]?token|auth[_-]?token)\b"
                             rb"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
    "Windows user path": rb"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+",
    "POSIX home path": rb"(?<![\w.])/(?:home|Users)/[A-Za-z][\w.\-]+/",
    "e-mail address": rb"[\w.+\-]+@[\w\-]+\.[\w.\-]*[A-Za-z]{2,}",
}
# e-mail addresses that are expected: none of them identifies the authors
EMAIL_OK = re.compile(rb"@(?:users\.noreply\.github\.com|example\.(?:invalid|com|org))$", re.I)


def files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True,
                             text=True, check=True, creationflags=NOWIN).stdout.splitlines()
        return [ROOT / f for f in out if (ROOT / f).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts]


def main() -> int:
    hits = []
    for p in files():
        if p.resolve() == Path(__file__).resolve():
            continue
        data = p.read_bytes()
        for name, rx in PATTERNS.items():
            for m in re.finditer(rx, data):
                tok = m.group(0)
                if name == "e-mail address" and EMAIL_OK.search(tok):
                    continue
                hits.append(f"{p.relative_to(ROOT).as_posix()}: {name}: {tok[:80].decode('utf-8', 'replace')}")
    for h in hits:
        print(h)
    print(f"{len(hits)} match(es) in {len(files())} files")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
