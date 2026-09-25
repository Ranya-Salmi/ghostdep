"""Check 2 — Age: flag packages whose first release was < MIN_AGE_DAYS ago.

PyPI: scan upload_time across every file in every release and take the minimum.
npm : use time.created from the registry JSON.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ghostdep.constants import MIN_AGE_DAYS
from ghostdep.verdict import Finding, Severity


def check_age(name: str, ecosystem: str, registry_data: dict) -> Optional[Finding]:
    """Return a SUSPICIOUS Finding if the package is very new, else None."""
    first_release = _first_release(ecosystem, registry_data)
    if first_release is None:
        return None  # can't determine age — skip

    now = datetime.now(tz=timezone.utc)
    age_days = (now - first_release).days

    if age_days < MIN_AGE_DAYS:
        return Finding(
            check="age",
            message=(
                f"Package '{name}' was first published {age_days} day(s) ago "
                f"(threshold: {MIN_AGE_DAYS} days)."
            ),
            severity=Severity.SUSPICIOUS,
        )
    return None


def _first_release(ecosystem: str, data: dict) -> Optional[datetime]:
    if ecosystem == "pypi":
        return _pypi_first_release(data)
    elif ecosystem == "npm":
        return _npm_first_release(data)
    return None


def _pypi_first_release(data: dict) -> Optional[datetime]:
    """Scan upload_time across every file in every release; return the minimum."""
    releases: dict = data.get("releases", {})
    timestamps: list[datetime] = []
    for files in releases.values():
        for file_info in files:
            ts_str = file_info.get("upload_time")
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    timestamps.append(dt)
                except ValueError:
                    continue
    return min(timestamps) if timestamps else None


def _npm_first_release(data: dict) -> Optional[datetime]:
    created_str = data.get("time", {}).get("created")
    if not created_str:
        return None
    try:
        # npm timestamps are ISO-8601 / RFC-3339
        dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        return None
