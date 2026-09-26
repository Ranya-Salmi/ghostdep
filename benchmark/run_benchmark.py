"""Run GhostDep's run_checks against benchmark/packages.csv.

Outputs
-------
benchmark/results.csv  – one row per package with verdict + reasons
benchmark/RESULTS.md   – human-readable report

Usage
-----
    python benchmark/run_benchmark.py [--sleep SECONDS]

Options
-------
--sleep  Seconds to wait between packages (default: 1.0)
--csv    Path to input CSV   (default: benchmark/packages.csv)
--out    Path to results CSV (default: benchmark/results.csv)
--md     Path to RESULTS.md  (default: benchmark/RESULTS.md)
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ensure the repo root is on sys.path when running as a script
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Use a benchmark-private cache dir so it never collides with the MCP server
# process that may hold the default cache DB open.
import os as _os
_BENCH_CACHE = str(_REPO_ROOT / ".cache" / "ghostdep-benchmark")
_os.environ.setdefault("GHOSTDEP_CACHE_DIR", _BENCH_CACHE)

# Patch the constant before ghostdep.cache is imported
import ghostdep.constants as _const
_const.CACHE_DIR = _BENCH_CACHE

from ghostdep.checker import run_checks
from ghostdep.verdict import Severity, Verdict

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
DEFAULT_CSV = _HERE / "packages.csv"
DEFAULT_OUT = _HERE / "results.csv"
DEFAULT_MD = _HERE / "RESULTS.md"
DEFAULT_SLEEP = 1.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BenchRow:
    name: str
    ecosystem: str
    category: str
    expected: str
    verdict: str = ""
    reasons: str = ""
    match: str = ""  # "yes", "no", "partial", "error"
    error: str = ""


# ---------------------------------------------------------------------------
# Match logic
# ---------------------------------------------------------------------------

def _matches(expected: str, verdict: str) -> str:
    """Return "yes", "no", or "partial" (for legit_obscure)."""
    if expected == "SAFE_OR_SUSPICIOUS":
        # legit_obscure: SAFE or SUSPICIOUS are both acceptable; BLOCKED is not
        return "yes" if verdict in ("SAFE", "SUSPICIOUS") else "no"
    return "yes" if verdict == expected else "no"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all(
    input_csv: Path = DEFAULT_CSV,
    output_csv: Path = DEFAULT_OUT,
    sleep_s: float = DEFAULT_SLEEP,
) -> list[BenchRow]:
    rows: list[BenchRow] = []

    with input_csv.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        packages = list(reader)

    total = len(packages)
    for i, pkg in enumerate(packages, 1):
        name = pkg["name"]
        ecosystem = pkg["ecosystem"]
        category = pkg["category"]
        expected = pkg["expected"]

        print(f"[{i:3}/{total}] {name} ({category}) ... ", end="", flush=True)

        row = BenchRow(name=name, ecosystem=ecosystem, category=category, expected=expected)
        try:
            verdict: Verdict = run_checks(name, ecosystem)
            row.verdict = verdict.overall.value
            row.reasons = " | ".join(
                f"{f.check}:{f.severity.value}:{f.message[:60]}"
                for f in verdict.findings
            )
            row.match = _matches(expected, row.verdict)
        except Exception as exc:
            row.verdict = "ERROR"
            row.error = type(exc).__name__ + ": " + str(exc)
            row.match = "error"

        print(f"{row.verdict}  [{row.match}]")
        rows.append(row)

        if i < total:
            time.sleep(sleep_s)

    # Write CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["name", "ecosystem", "category", "expected", "verdict", "match", "reasons", "error"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "name": r.name,
                    "ecosystem": r.ecosystem,
                    "category": r.category,
                    "expected": r.expected,
                    "verdict": r.verdict,
                    "match": r.match,
                    "reasons": r.reasons,
                    "error": r.error,
                }
            )

    return rows


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _rate(num: int, den: int) -> str:
    if den == 0:
        return "N/A"
    return f"{num}/{den} ({100*num/den:.0f}%)"


def write_md(rows: list[BenchRow], md_path: Path = DEFAULT_MD) -> None:
    categories = ["popular", "mid_popularity", "typosquat", "hallucinated"]

    # Per-category stats
    stats: dict[str, dict] = {}
    for cat in categories:
        cat_rows = [r for r in rows if r.category == cat]
        yes = sum(1 for r in cat_rows if r.match == "yes")
        no = sum(1 for r in cat_rows if r.match == "no")
        err = sum(1 for r in cat_rows if r.match == "error")
        stats[cat] = {"total": len(cat_rows), "yes": yes, "no": no, "err": err}

    # Detection rate = proportion correct for typosquat + hallucinated
    detect_cats = ["typosquat", "hallucinated"]
    detect_yes = sum(stats[c]["yes"] for c in detect_cats)
    detect_total = sum(stats[c]["total"] for c in detect_cats)

    # False-positive rate = BLOCKED verdicts on popular + mid_popularity
    fp_cats = ["popular", "mid_popularity"]
    fp_rows = [r for r in rows if r.category in fp_cats and r.match == "no"]
    fp_total = sum(stats[c]["total"] for c in fp_cats)

    # Mismatches
    mismatches = [r for r in rows if r.match == "no"]

    lines: list[str] = []
    lines.append("# GhostDep Benchmark Results\n")
    lines.append(f"**Total packages tested:** {len(rows)}\n")

    lines.append("## Summary\n")
    lines.append(
        f"| Metric | Value |\n"
        f"|---|---|\n"
        f"| Detection rate (typosquat + hallucinated) | {_rate(detect_yes, detect_total)} |\n"
        f"| False-positive rate (popular + legit\\_obscure) | {_rate(len(fp_rows), fp_total)} |\n"
    )

    lines.append("\n## Per-Category Results\n")
    lines.append("| Category | Expected | Total | Correct | Wrong | Errors |")
    lines.append("|---|---|---|---|---|---|")
    expected_labels = {
        "popular": "SAFE",
        "mid_popularity": "SAFE or SUSPICIOUS",
        "typosquat": "BLOCKED",
        "hallucinated": "BLOCKED",
    }
    for cat in categories:
        s = stats[cat]
        lines.append(
            f"| {cat} | {expected_labels[cat]} | {s['total']} | {s['yes']} | {s['no']} | {s['err']} |"
        )

    lines.append("\n## Mismatches\n")
    if not mismatches:
        lines.append("_No mismatches — all verdicts matched expectations._\n")
    else:
        lines.append(
            f"**{len(mismatches)} package(s) did not match expected verdict.**\n"
        )
        lines.append("| Package | Category | Expected | Got | Reasons |")
        lines.append("|---|---|---|---|---|")
        for r in mismatches:
            reasons_md = r.reasons.replace("|", "\\|") if r.reasons else r.error
            lines.append(
                f"| `{r.name}` | {r.category} | {r.expected} | {r.verdict} | {reasons_md} |"
            )

    lines.append("\n## All Results\n")
    lines.append("| Package | Category | Expected | Verdict | Match | Reasons |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        reasons_md = (r.reasons or r.error).replace("|", "\\|")
        lines.append(
            f"| `{r.name}` | {r.category} | {r.expected} | {r.verdict} | {r.match} | {reasons_md} |"
        )

    lines.append("\n## Notes\n")
    lines.append(
        "- `mid_popularity` packages (ranks 3000–5000) may legitimately be flagged "
        "SUSPICIOUS by the age or popularity checks; only a BLOCKED verdict counts "
        "as a false positive for that category.\n"
        "- The typosquat check depends on OSA edit-distance against "
        "`ghostdep/data/top_pypi.txt`. Names generated by the benchmark may already "
        "exist on PyPI as legitimate packages — the existence check fires first, which "
        "means the package won't be BLOCKED for typosquatting but may be SAFE or "
        "SUSPICIOUS on its own merits.\n"
        "- API errors (network timeouts, rate-limiting) are recorded under match=error "
        "and counted in the Errors column, not as mismatches.\n"
    )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {md_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run GhostDep benchmark")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP,
                        help="Seconds to sleep between packages (default: 1.0)")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        dest="input_csv", help="Input packages.csv")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        dest="output_csv", help="Output results.csv")
    parser.add_argument("--md", type=Path, default=DEFAULT_MD,
                        dest="md_path", help="Output RESULTS.md")
    args = parser.parse_args()

    rows = run_all(args.input_csv, args.output_csv, args.sleep)
    write_md(rows, args.md_path)
    print(f"Wrote {args.output_csv}")


if __name__ == "__main__":
    main()
