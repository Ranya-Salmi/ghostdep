"""Tests for Check 2 — Age."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ghostdep.checks.age import check_age
from ghostdep.constants import MIN_AGE_DAYS
from ghostdep.verdict import Severity


def _days_ago(n: int) -> str:
    """Return an ISO-8601 UTC timestamp string N days in the past."""
    dt = datetime.now(tz=timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# PyPI
# ---------------------------------------------------------------------------

def test_pypi_old_package_is_safe():
    registry = {
        "releases": {
            "1.0.0": [{"upload_time": _days_ago(365), "filename": "pkg-1.0.0.tar.gz"}],
            "2.0.0": [{"upload_time": _days_ago(10), "filename": "pkg-2.0.0.tar.gz"}],
        }
    }
    finding = check_age("mypkg", "pypi", registry)
    assert finding is None  # oldest file is 365 days ago → safe


def test_pypi_new_package_is_suspicious():
    registry = {
        "releases": {
            "0.1.0": [{"upload_time": _days_ago(5), "filename": "pkg-0.1.0.tar.gz"}],
        }
    }
    finding = check_age("newpkg", "pypi", registry)
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert "5" in finding.message  # age in days mentioned


def test_pypi_exactly_at_threshold_is_safe():
    """A package first published exactly MIN_AGE_DAYS ago is NOT flagged."""
    registry = {
        "releases": {
            "1.0.0": [{"upload_time": _days_ago(MIN_AGE_DAYS), "filename": "a.tar.gz"}],
        }
    }
    finding = check_age("pkg", "pypi", registry)
    assert finding is None


def test_pypi_one_day_short_is_suspicious():
    registry = {
        "releases": {
            "1.0.0": [{"upload_time": _days_ago(MIN_AGE_DAYS - 1), "filename": "a.tar.gz"}],
        }
    }
    finding = check_age("pkg", "pypi", registry)
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_pypi_uses_earliest_upload_time():
    """The check must use the minimum upload_time, not the latest."""
    old = _days_ago(500)
    new = _days_ago(2)
    registry = {
        "releases": {
            "0.1.0": [{"upload_time": old, "filename": "a.tar.gz"}],
            "0.2.0": [{"upload_time": new, "filename": "b.tar.gz"}],
        }
    }
    finding = check_age("pkg", "pypi", registry)
    assert finding is None  # earliest is 500 days ago


def test_pypi_empty_releases_skips():
    finding = check_age("pkg", "pypi", {"releases": {}})
    assert finding is None


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

def test_npm_old_package_is_safe():
    registry = {
        "time": {"created": _days_ago(365) + "Z"}
    }
    # npm created timestamps usually end with Z
    finding = check_age("express", "npm", registry)
    assert finding is None


def test_npm_new_package_is_suspicious():
    registry = {
        "time": {"created": _days_ago(3) + "Z"}
    }
    finding = check_age("newpkg", "npm", registry)
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_npm_missing_created_skips():
    finding = check_age("pkg", "npm", {"time": {}})
    assert finding is None
