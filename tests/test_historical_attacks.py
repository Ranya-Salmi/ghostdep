"""Phase 2 — Historical typosquat attacks: simulated replay tests.

These packages were published on PyPI in the past and later removed.
We cannot use the existence check (they are gone), so we test the typosquat
check directly by simulating them as existing packages that are 3 days old with
10 downloads — exactly the profile a live attacker upload would show.

Packages tested:
    colourama    (imitated colorama)
    python3-dateutil (imitated python-dateutil)
    jeIlyfish    (capital I, imitated jellyfish)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from ghostdep.checks.typosquat import check_typosquat
from ghostdep.verdict import Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_release_days_ago(days: int) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=days)


def _patch_list(ecosystem: str, names: list[str]):
    """Patch _load_top_list to return a controlled list."""
    return patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: names if eco == ecosystem else [],
    )


# Simulated profile: exists on PyPI, 3 days old, 10 downloads
_NEW_RELEASE = _first_release_days_ago(3)
_LOW_DOWNLOADS = 10


# ---------------------------------------------------------------------------
# Historical attack: colourama → colorama
# ---------------------------------------------------------------------------

def test_historical_colourama_blocked():
    """colourama (extra 'u') closely resembles colorama → BLOCKED."""
    with _patch_list("pypi", ["colorama"]):
        finding = check_typosquat(
            "colourama", "pypi",
            download_count=_LOW_DOWNLOADS,
            first_release=_NEW_RELEASE,
        )
    assert finding is not None, "Expected BLOCKED finding for colourama"
    assert finding.severity == Severity.BLOCKED
    assert "colorama" in finding.suggestion


# ---------------------------------------------------------------------------
# Historical attack: python3-dateutil → python-dateutil
# ---------------------------------------------------------------------------

def test_historical_python3_dateutil_blocked():
    """python3-dateutil closely resembles python-dateutil → BLOCKED."""
    with _patch_list("pypi", ["python-dateutil"]):
        finding = check_typosquat(
            "python3-dateutil", "pypi",
            download_count=_LOW_DOWNLOADS,
            first_release=_NEW_RELEASE,
        )
    assert finding is not None, "Expected BLOCKED finding for python3-dateutil"
    assert finding.severity == Severity.BLOCKED
    assert "python-dateutil" in finding.suggestion


# ---------------------------------------------------------------------------
# Historical attack: jeIlyfish (capital I) → jellyfish
# ---------------------------------------------------------------------------

def test_historical_jellyfish_lookalike_blocked():
    """jeIlyfish (capital I substituted for l) closely resembles jellyfish → BLOCKED."""
    with _patch_list("pypi", ["jellyfish"]):
        finding = check_typosquat(
            "jeIlyfish", "pypi",
            download_count=_LOW_DOWNLOADS,
            first_release=_NEW_RELEASE,
        )
    assert finding is not None, "Expected BLOCKED finding for jeIlyfish"
    assert finding.severity == Severity.BLOCKED
    assert "jellyfish" in finding.suggestion


# ---------------------------------------------------------------------------
# Sanity: the real packages themselves are NOT flagged
# ---------------------------------------------------------------------------

def test_real_colorama_not_flagged():
    with _patch_list("pypi", ["colorama"]):
        finding = check_typosquat("colorama", "pypi", 5_000_000, _first_release_days_ago(400))
    assert finding is None


def test_real_python_dateutil_not_flagged():
    with _patch_list("pypi", ["python-dateutil"]):
        finding = check_typosquat("python-dateutil", "pypi", 5_000_000, _first_release_days_ago(400))
    assert finding is None


def test_real_jellyfish_not_flagged():
    with _patch_list("pypi", ["jellyfish"]):
        finding = check_typosquat("jellyfish", "pypi", 5_000_000, _first_release_days_ago(400))
    assert finding is None
