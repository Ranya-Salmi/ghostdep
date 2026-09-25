"""Tests for Check 4 — Typosquatting."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from ghostdep.checks.typosquat import check_typosquat, _load_top_list
from ghostdep.constants import MIN_AGE_DAYS, PYPI_MIN_DOWNLOADS_MONTH
from ghostdep.verdict import Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _old() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=MIN_AGE_DAYS + 10)


def _new() -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=5)


def _patch_list(ecosystem: str, names: list[str]):
    """Patch _load_top_list to return a controlled list."""
    return patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: names if eco == ecosystem else [],
    )


# ---------------------------------------------------------------------------
# Basic matching
# ---------------------------------------------------------------------------

def test_exact_match_in_top_list_is_safe():
    """'requests' is in the top list → no finding."""
    with _patch_list("pypi", ["requests", "flask", "django"]):
        finding = check_typosquat("requests", "pypi", 5_000_000, _old())
    assert finding is None


def test_no_near_match_is_safe():
    with _patch_list("pypi", ["requests", "flask"]):
        finding = check_typosquat("completelydifferent", "pypi", 0, _new())
    assert finding is None


def test_typosquat_reqeusts_is_blocked():
    """'reqeusts' is edit-distance 2 from 'requests' → BLOCKED."""
    with _patch_list("pypi", ["requests", "flask"]):
        finding = check_typosquat("reqeusts", "pypi", 0, _new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert "requests" in finding.suggestion


def test_typosquat_short_name_threshold_1():
    """Short name (<=5 chars) uses threshold 1. 'flsk' is distance 1 from 'flask'."""
    with _patch_list("pypi", ["flask"]):
        # 'flsk' drops the 'a' — edit distance 1 from 'flask'
        finding = check_typosquat("flsk", "pypi", 0, _new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


def test_typosquat_short_name_distance_2_is_safe():
    """Short name (<=5 chars) uses threshold 1, so distance-2 is NOT flagged."""
    with _patch_list("pypi", ["flask"]):
        # 'fxsk' is distance 2 from 'flask' (2 substitutions); threshold for 4-char name is 1
        finding = check_typosquat("fxsk", "pypi", 0, _new())
    assert finding is None


def test_typosquat_long_name_threshold_2():
    """Long name (>5 chars): 'reqeusts' (7 chars) → threshold 2 → catches distance-2."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat("reqeusts", "pypi", 0, _new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


# ---------------------------------------------------------------------------
# Popular-and-old exception
# ---------------------------------------------------------------------------

def test_popular_and_old_near_match_is_safe():
    """A near-match that is itself popular AND old → SAFE."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat(
            "reqeusts", "pypi",
            download_count=PYPI_MIN_DOWNLOADS_MONTH + 1,
            first_release=_old(),
        )
    assert finding is None


def test_popular_but_new_near_match_is_blocked():
    """Popular but recently uploaded → still BLOCKED."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat(
            "reqeusts", "pypi",
            download_count=PYPI_MIN_DOWNLOADS_MONTH + 1,
            first_release=_new(),
        )
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


def test_old_but_unpopular_near_match_is_blocked():
    """Old but very few downloads → still BLOCKED."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat(
            "reqeusts", "pypi",
            download_count=10,
            first_release=_old(),
        )
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


def test_unknown_downloads_near_match_is_blocked():
    """No download data available → treated as unpopular → BLOCKED."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat("reqeusts", "pypi", download_count=None, first_release=_new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


# ---------------------------------------------------------------------------
# Suggestion text
# ---------------------------------------------------------------------------

def test_suggestion_contains_real_name():
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat("reqeusts", "pypi", 0, _new())
    assert finding is not None
    assert finding.suggestion is not None
    assert "requests" in finding.suggestion


# ---------------------------------------------------------------------------
# Empty list falls through
# ---------------------------------------------------------------------------

def test_empty_top_list_skips_check():
    with _patch_list("pypi", []):
        finding = check_typosquat("reqeusts", "pypi", 0, _new())
    assert finding is None

# ---------------------------------------------------------------------------
# OSA (optimal string alignment) — adjacent-letter transposition = distance 1
# ---------------------------------------------------------------------------

def test_osa_transposition_flaks_is_blocked():
    """'flaks' is a transposition of 'flask' — OSA distance 1 → BLOCKED."""
    with _patch_list("pypi", ["flask"]):
        finding = check_typosquat("flaks", "pypi", 0, _new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert "flask" in finding.suggestion


def test_osa_transposition_reqeusts_is_blocked():
    """'reqeusts' has adjacent swap 'eu'→'ue' in 'requests'; OSA distance 2 → BLOCKED."""
    with _patch_list("pypi", ["requests"]):
        finding = check_typosquat("reqeusts", "pypi", 0, _new())
    assert finding is not None
    assert finding.severity == Severity.BLOCKED

