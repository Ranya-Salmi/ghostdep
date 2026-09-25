"""Check 3 — Popularity: flag packages with very few downloads.

PyPI : pypistats recent API  (last_month)
npm  : npm download-counts API (last-week)

Network errors produce a SUSPICIOUS "could not verify" finding; they are NOT cached.
"""
from __future__ import annotations

from typing import Optional

import httpx

from ghostdep.cache import cached_get
from ghostdep.constants import (
    NPM_DOWNLOADS_URL,
    NPM_MIN_DOWNLOADS_WEEK,
    PYPI_MIN_DOWNLOADS_MONTH,
    PYPISTATS_RECENT_URL,
)
from ghostdep.verdict import Finding, Severity


def check_popularity(name: str, ecosystem: str) -> tuple[Optional[Finding], Optional[int]]:
    """Return (finding_or_None, download_count_or_None).

    download_count is None on network error or when data is unavailable.
    """
    try:
        if ecosystem == "pypi":
            return _check_pypi(name)
        elif ecosystem == "npm":
            return _check_npm(name)
        return None, None
    except (httpx.TimeoutException, httpx.HTTPStatusError):
        return Finding(
            check="popularity",
            message=f"Could not verify download count for '{name}' (network error).",
            severity=Severity.SUSPICIOUS,
        ), None


def _check_pypi(name: str) -> tuple[Optional[Finding], Optional[int]]:
    url = PYPISTATS_RECENT_URL.format(name=name)
    data = cached_get(url)
    if data is None:
        return None, None  # 404 from pypistats — just skip
    count = data.get("data", {}).get("last_month")
    if count is None:
        return None, None
    count = int(count)
    if count < PYPI_MIN_DOWNLOADS_MONTH:
        return Finding(
            check="popularity",
            message=(
                f"'{name}' has only {count:,} PyPI downloads last month "
                f"(threshold: {PYPI_MIN_DOWNLOADS_MONTH:,})."
            ),
            severity=Severity.SUSPICIOUS,
        ), count
    return None, count


def _check_npm(name: str) -> tuple[Optional[Finding], Optional[int]]:
    url = NPM_DOWNLOADS_URL.format(name=name)
    data = cached_get(url)
    if data is None:
        return None, None
    count = data.get("downloads")
    if count is None:
        return None, None
    count = int(count)
    if count < NPM_MIN_DOWNLOADS_WEEK:
        return Finding(
            check="popularity",
            message=(
                f"'{name}' has only {count:,} npm downloads last week "
                f"(threshold: {NPM_MIN_DOWNLOADS_WEEK:,})."
            ),
            severity=Severity.SUSPICIOUS,
        ), count
    return None, count
