"""Build benchmark/packages.csv from the top_pypi.txt list.

Categories
----------
popular        (30 names, ranks 1-500)     expected: SAFE
mid_popularity (15 names, ranks 3000-5000) expected: SAFE or SUSPICIOUS
typosquat      (15 names, generated)       expected: BLOCKED
hallucinated   (15 invented names)         expected: BLOCKED

Run this script once; it writes benchmark/packages.csv.
Results are fully reproducible via a fixed random seed.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEED = 42
N_POPULAR = 30
N_OBSCURE = 15
N_TYPOSQUAT = 15
N_HALLUCINATED = 15

TOP_PYPI = Path(__file__).parent.parent / "ghostdep" / "data" / "top_pypi.txt"
OUT_CSV = Path(__file__).parent / "packages.csv"


# ---------------------------------------------------------------------------
# Load top list
# ---------------------------------------------------------------------------

def _load_top(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text("utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Typosquat name generators (pure string transforms)
# ---------------------------------------------------------------------------

def _adjacent_swap(name: str, pos: int) -> str:
    """Swap characters at pos and pos+1."""
    if pos >= len(name) - 1:
        return name
    lst = list(name)
    lst[pos], lst[pos + 1] = lst[pos + 1], lst[pos]
    return "".join(lst)


def _delete_one(name: str, pos: int) -> str:
    """Delete the character at pos."""
    if pos >= len(name):
        return name
    return name[:pos] + name[pos + 1:]


def _double_one(name: str, pos: int) -> str:
    """Double the character at pos."""
    if pos >= len(name):
        return name
    return name[:pos] + name[pos] + name[pos:]


def _generate_typosquats(top100: list[str], rng: random.Random) -> list[str]:
    """Generate plausible-looking typosquatted names from top-100 packages.

    Strategy: for each candidate original, try all three transforms at every
    position and keep the ones that are distinct from the original.
    Then sample from the pool.  We always include "reqeusts".
    """
    pool: list[str] = []
    generators = [_adjacent_swap, _delete_one, _double_one]

    for original in top100:
        for gen in generators:
            for pos in range(len(original)):
                candidate = gen(original, pos)
                if candidate != original and len(candidate) >= 3:
                    pool.append(candidate)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in pool:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    # Always include "reqeusts"
    forced = ["reqeusts"]
    # Remove forced names from pool to avoid duplicates in final list
    unique = [c for c in unique if c not in forced]

    # Shuffle remaining and take N_TYPOSQUAT - len(forced)
    rng.shuffle(unique)
    result = forced + unique[: N_TYPOSQUAT - len(forced)]
    return result


# ---------------------------------------------------------------------------
# Hallucinated names (plausible-sounding, do not exist on PyPI)
# ---------------------------------------------------------------------------

HALLUCINATED: list[str] = [
    "fastapi-auth-helper-pro",
    "django-supermodel",
    "pydantic-schema-validator-plus",
    "requests-async-client",
    "numpy-accelerate-gpu",
    "sqlalchemy-smart-orm",
    "flask-restplus-extended",
    "torch-model-utils",
    "pandas-ai-agent",
    "langchain-vector-store-pro",
    "cryptography-fips-adapter",
    "pytest-ai-fixtures",
    "click-rich-formatter",
    "httpx-retry-middleware",
    "celery-task-scheduler-pro",
]

assert len(HALLUCINATED) == N_HALLUCINATED, "Fix HALLUCINATED list length"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(out_path: Path = OUT_CSV) -> None:
    rng = random.Random(SEED)
    top = _load_top(TOP_PYPI)

    # popular: ranks 1-500 (0-indexed 0-499), sample 30
    popular_pool = top[0:500]
    popular_sample = rng.sample(popular_pool, N_POPULAR)

    # mid_popularity: ranks 3000-5000 (0-indexed 2999-4999), sample 15
    obscure_pool = top[2999:5000]
    obscure_sample = rng.sample(obscure_pool, N_OBSCURE)

    # typosquats generated from top-100
    top100 = top[:100]
    typosquat_names = _generate_typosquats(top100, rng)

    rows: list[dict] = []
    for name in popular_sample:
        rows.append({"name": name, "ecosystem": "pypi", "category": "popular", "expected": "SAFE"})
    for name in obscure_sample:
        rows.append({"name": name, "ecosystem": "pypi", "category": "mid_popularity", "expected": "SAFE_OR_SUSPICIOUS"})
    for name in typosquat_names:
        rows.append({"name": name, "ecosystem": "pypi", "category": "typosquat", "expected": "BLOCKED"})
    for name in HALLUCINATED:
        rows.append({"name": name, "ecosystem": "pypi", "category": "hallucinated", "expected": "BLOCKED"})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["name", "ecosystem", "category", "expected"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    for cat in ("popular", "mid_popularity", "typosquat", "hallucinated"):
        count = sum(1 for r in rows if r["category"] == cat)
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    build()
