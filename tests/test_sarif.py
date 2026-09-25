"""Tests for SARIF 2.1.0 output (sarif.py)."""
from __future__ import annotations

import json

import pytest

from ghostdep.sarif import verdict_to_sarif, verdict_to_sarif_str
from ghostdep.verdict import Finding, Severity, Verdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_verdict() -> Verdict:
    return Verdict.aggregate("requests", "pypi", [])


def _blocked_verdict() -> Verdict:
    return Verdict.aggregate(
        "reqeusts",
        "pypi",
        [
            Finding(
                check="typosquat",
                message="'reqeusts' closely resembles 'requests'",
                severity=Severity.BLOCKED,
                suggestion="Did you mean 'requests'?",
            )
        ],
    )


def _suspicious_verdict() -> Verdict:
    return Verdict.aggregate(
        "newpkg",
        "pypi",
        [
            Finding(
                check="age",
                message="Package published 3 days ago (threshold: 30)",
                severity=Severity.SUSPICIOUS,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Schema shape
# ---------------------------------------------------------------------------

def test_sarif_has_schema_key():
    doc = verdict_to_sarif(_safe_verdict())
    assert doc["$schema"] == "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json"


def test_sarif_version_is_2_1_0():
    doc = verdict_to_sarif(_safe_verdict())
    assert doc["version"] == "2.1.0"


def test_sarif_has_runs_list():
    doc = verdict_to_sarif(_safe_verdict())
    assert isinstance(doc["runs"], list)
    assert len(doc["runs"]) == 1


def test_sarif_tool_driver_name():
    doc = verdict_to_sarif(_safe_verdict())
    assert doc["runs"][0]["tool"]["driver"]["name"] == "ghostdep"


def test_sarif_tool_driver_has_version():
    doc = verdict_to_sarif(_safe_verdict())
    assert "version" in doc["runs"][0]["tool"]["driver"]


# ---------------------------------------------------------------------------
# Safe verdict — single "note" result emitted
# ---------------------------------------------------------------------------

def test_safe_verdict_emits_one_result():
    doc = verdict_to_sarif(_safe_verdict())
    results = doc["runs"][0]["results"]
    assert len(results) == 1


def test_safe_verdict_result_level_is_note():
    doc = verdict_to_sarif(_safe_verdict())
    assert doc["runs"][0]["results"][0]["level"] == "note"


def test_safe_verdict_result_rule_id():
    doc = verdict_to_sarif(_safe_verdict())
    assert doc["runs"][0]["results"][0]["ruleId"] == "safe"


# ---------------------------------------------------------------------------
# Severity → SARIF level mapping
# ---------------------------------------------------------------------------

def test_blocked_finding_maps_to_error():
    doc = verdict_to_sarif(_blocked_verdict())
    results = doc["runs"][0]["results"]
    assert results[0]["level"] == "error"


def test_suspicious_finding_maps_to_warning():
    doc = verdict_to_sarif(_suspicious_verdict())
    results = doc["runs"][0]["results"]
    assert results[0]["level"] == "warning"


# ---------------------------------------------------------------------------
# ruleId and message
# ---------------------------------------------------------------------------

def test_rule_id_matches_check_name():
    doc = verdict_to_sarif(_blocked_verdict())
    assert doc["runs"][0]["results"][0]["ruleId"] == "typosquat"


def test_message_text_present():
    doc = verdict_to_sarif(_blocked_verdict())
    msg = doc["runs"][0]["results"][0]["message"]["text"]
    assert "reqeusts" in msg or "requests" in msg


def test_suggestion_appended_to_message():
    doc = verdict_to_sarif(_blocked_verdict())
    msg = doc["runs"][0]["results"][0]["message"]["text"]
    assert "Did you mean" in msg


# ---------------------------------------------------------------------------
# Location URI
# ---------------------------------------------------------------------------

def test_location_uri_scheme():
    doc = verdict_to_sarif(_blocked_verdict())
    uri = (
        doc["runs"][0]["results"][0]["locations"][0]
        ["physicalLocation"]["artifactLocation"]["uri"]
    )
    assert uri == "pkg://pypi/reqeusts"


# ---------------------------------------------------------------------------
# JSON serialisation round-trip
# ---------------------------------------------------------------------------

def test_sarif_str_is_valid_json():
    s = verdict_to_sarif_str(_blocked_verdict())
    parsed = json.loads(s)
    assert parsed["version"] == "2.1.0"


def test_sarif_str_indented():
    s = verdict_to_sarif_str(_blocked_verdict(), indent=2)
    # Indented JSON has newlines
    assert "\n" in s
