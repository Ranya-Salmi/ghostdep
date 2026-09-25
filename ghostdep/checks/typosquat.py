"""Check 4 — Typosquatting: detect near-matches against top-package lists.

Algorithm
---------
1. Load top_pypi.txt / top_npm.txt into a module-level list (lazy, once).
2. Normalise the queried name: lowercase, remove hyphens/underscores/dots.
3. Dynamic edit-distance threshold:
      len(normalised) <= 5  →  max_dist = 1
      len(normalised) >  5  →  max_dist = 2
4. Find top-list entries within that distance (distance > 0 only).
5. If any near-match AND the queried name is NOT in the top list:
   - If the package is popular (downloads >= threshold) AND old (>= MIN_AGE_DAYS)
     → SAFE (legitimate but less-known package).
   - Otherwise → BLOCKED with a "Did you mean …?" suggestion.
6. Name in top list or no near-match → no finding.

Popularity/age data come from the checker orchestrator, which passes them in.
"""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from rapidfuzz.distance import OSA

from ghostdep.constants import MIN_AGE_DAYS, NPM_MIN_DOWNLOADS_WEEK, PYPI_MIN_DOWNLOADS_MONTH, TOP_LIST_SIZE
from ghostdep.verdict import Finding, Severity

_DATA_DIR = Path(__file__).parent.parent / "data"


def _normalise(name: str) -> str:
    return name.lower().replace("-", "").replace("_", "").replace(".", "")


@lru_cache(maxsize=2)
def _load_top_list(ecosystem: str) -> list[str]:
    """Load and return the top-package list for the given ecosystem (cached)."""
    filename = "top_pypi.txt" if ecosystem == "pypi" else "top_npm.txt"
    path = _DATA_DIR / filename
    if not path.exists():
        return []
    names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return names[:TOP_LIST_SIZE]


def _max_dist(normalised_name: str) -> int:
    return 1 if len(normalised_name) <= 5 else 2


def check_typosquat(
    name: str,
    ecosystem: str,
    download_count: Optional[int],
    first_release: Optional[datetime],
) -> Optional[Finding]:
    """Return a BLOCKED Finding if the name looks like a typosquat, else None.

    Parameters
    ----------
    name:           package name as queried
    ecosystem:      "pypi" or "npm"
    download_count: recent downloads (None if unknown); used for safe-popular check
    first_release:  datetime of first upload (None if unknown); used for age check
    """
    top_list = _load_top_list(ecosystem)
    if not top_list:
        return None  # list not available — skip check

    normalised = _normalise(name)
    top_normalised = [_normalise(n) for n in top_list]

    # If the package itself is in the top list it's a known popular package
    if normalised in top_normalised:
        return None

    threshold = _max_dist(normalised)
    best_dist = threshold + 1
    best_match: Optional[str] = None

    for orig, norm in zip(top_list, top_normalised):
        dist = OSA.distance(normalised, norm)
        if 0 < dist <= threshold:
            if dist < best_dist:
                best_dist = dist
                best_match = orig

    if best_match is None:
        return None  # no near-match

    # Near-match found — check if this package is itself popular and old
    if _is_popular_and_old(ecosystem, download_count, first_release):
        return None  # legitimate but less-known package

    return Finding(
        check="typosquat",
        message=(
            f"'{name}' closely resembles the popular package '{best_match}' "
            f"(edit distance {best_dist}) but is not itself well-established."
        ),
        severity=Severity.BLOCKED,
        suggestion=f"Did you mean '{best_match}'?",
    )


def _is_popular_and_old(
    ecosystem: str,
    download_count: Optional[int],
    first_release: Optional[datetime],
) -> bool:
    """Return True if the package is both popular AND old enough."""
    # Popularity
    if download_count is None:
        popular = False
    elif ecosystem == "pypi":
        popular = download_count >= PYPI_MIN_DOWNLOADS_MONTH
    else:
        popular = download_count >= NPM_MIN_DOWNLOADS_WEEK

    # Age
    if first_release is None:
        old = False
    else:
        now = datetime.now(tz=timezone.utc)
        if first_release.tzinfo is None:
            first_release = first_release.replace(tzinfo=timezone.utc)
        old = (now - first_release).days >= MIN_AGE_DAYS

    return popular and old
