"""Generate demo/report-example.html from representative (offline) verdicts.

Run from the repo root:
    python scripts/gen_demo_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ghostdep.report import generate_html
from ghostdep.verdict import Finding, Severity, Verdict

verdicts = [
    Verdict(
        package="reqeusts",
        ecosystem="pypi",
        overall=Severity.BLOCKED,
        findings=[
            Finding(
                check="existence",
                message="Package 'reqeusts' was not found on PyPI (HTTP 404).",
                severity=Severity.BLOCKED,
                suggestion=None,
            ),
            Finding(
                check="typosquat",
                message="'reqeusts' closely resembles the popular package 'requests' (edit distance 2) but is not itself well-established.",
                severity=Severity.BLOCKED,
                suggestion="Did you mean 'requests'?",
            ),
        ],
    ),
    Verdict(
        package="fastapi-auth-helper-pro",
        ecosystem="pypi",
        overall=Severity.BLOCKED,
        findings=[
            Finding(
                check="existence",
                message="Package 'fastapi-auth-helper-pro' was not found on PyPI (HTTP 404).",
                severity=Severity.BLOCKED,
                suggestion="Did you mean 'fastapi'?",
            ),
        ],
    ),
    Verdict(
        package="requests",
        ecosystem="pypi",
        overall=Severity.SAFE,
        findings=[],
    ),
    Verdict(
        package="python-dateutil",
        ecosystem="pypi",
        overall=Severity.SAFE,
        findings=[],
    ),
]

out = Path(__file__).parent.parent / "demo" / "report-example.html"
out.parent.mkdir(parents=True, exist_ok=True)
html = generate_html(
    verdicts,
    source_file="demo/weather-api/requirements.txt",
    timestamp="2026-09-26 10:00 UTC",
)
out.write_text(html, encoding="utf-8")
print(f"Written: {out}")
