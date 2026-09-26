"""Quality check: verify no external resource requests in HTML output files."""
import re
import sys

files = [
    "docs/index.html",
    "docs/report-example.html",
    "demo/report-example.html",
]

# Patterns that would load external resources at render time
external_patterns = [
    r'<script[^>]+src=["\']https?://',
    r'<img[^>]+src=["\']https?://',
    r'<link[^>]+href=["\']https?://',
    r'url\(https?://',
    r'@import\s+["\']https?://',
]

failures = []
for filepath in files:
    try:
        content = open(filepath, encoding="utf-8").read()
    except FileNotFoundError:
        failures.append(f"MISSING: {filepath}")
        continue
    for pat in external_patterns:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            failures.append(f"EXTERNAL REQUEST in {filepath}: {matches[0]!r}")

if failures:
    for f in failures:
        print(f"FAIL  {f}")
    sys.exit(1)
else:
    print(f"PASS  No external resource requests in {len(files)} HTML files")
