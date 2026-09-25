"""Tests for the GhostDep CLI (cli.py)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ghostdep.cli import main
from ghostdep.verdict import Finding, Severity, Verdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _old_ts() -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")


def _safe_verdict(name: str = "requests", ecosystem: str = "pypi") -> Verdict:
    return Verdict(package=name, ecosystem=ecosystem, overall=Severity.SAFE, findings=[])


def _blocked_verdict(name: str = "reqeusts", ecosystem: str = "pypi") -> Verdict:
    return Verdict(
        package=name,
        ecosystem=ecosystem,
        overall=Severity.BLOCKED,
        findings=[
            Finding(
                check="typosquat",
                message=f"'{name}' closely resembles 'requests'",
                severity=Severity.BLOCKED,
                suggestion="Did you mean 'requests'?",
            )
        ],
    )


def _suspicious_verdict(name: str = "newpkg", ecosystem: str = "pypi") -> Verdict:
    return Verdict(
        package=name,
        ecosystem=ecosystem,
        overall=Severity.SUSPICIOUS,
        findings=[
            Finding(
                check="age",
                message="Package published 3 days ago (threshold: 30)",
                severity=Severity.SUSPICIOUS,
            )
        ],
    )


def _patch_run(verdict: Verdict):
    return patch("ghostdep.cli.run_checks", return_value=verdict)


# ---------------------------------------------------------------------------
# Text format — exit codes
# ---------------------------------------------------------------------------

def test_safe_exit_code_0():
    runner = CliRunner()
    with _patch_run(_safe_verdict()):
        result = runner.invoke(main, ["check", "requests"])
    assert result.exit_code == 0


def test_suspicious_exit_code_1():
    runner = CliRunner()
    with _patch_run(_suspicious_verdict()):
        result = runner.invoke(main, ["check", "newpkg"])
    assert result.exit_code == 1


def test_blocked_exit_code_2():
    runner = CliRunner()
    with _patch_run(_blocked_verdict()):
        result = runner.invoke(main, ["check", "reqeusts"])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Text format — output content
# ---------------------------------------------------------------------------

def test_text_output_contains_verdict():
    runner = CliRunner()
    with _patch_run(_safe_verdict()):
        result = runner.invoke(main, ["check", "requests"])
    assert "SAFE" in result.output
    assert "requests" in result.output


def test_text_output_contains_finding_check_name():
    runner = CliRunner()
    with _patch_run(_blocked_verdict()):
        result = runner.invoke(main, ["check", "reqeusts"])
    assert "typosquat" in result.output


def test_text_output_contains_suggestion():
    runner = CliRunner()
    with _patch_run(_blocked_verdict()):
        result = runner.invoke(main, ["check", "reqeusts"])
    assert "Did you mean" in result.output


def test_text_no_findings_says_no_issues():
    runner = CliRunner()
    with _patch_run(_safe_verdict()):
        result = runner.invoke(main, ["check", "requests"])
    assert "No issues" in result.output


# ---------------------------------------------------------------------------
# SARIF format
# ---------------------------------------------------------------------------

def test_sarif_output_is_valid_json():
    runner = CliRunner()
    with _patch_run(_blocked_verdict()):
        result = runner.invoke(main, ["check", "reqeusts", "--format", "sarif"])
    parsed = json.loads(result.output)
    assert parsed["version"] == "2.1.0"


def test_sarif_output_has_schema():
    runner = CliRunner()
    with _patch_run(_safe_verdict()):
        result = runner.invoke(main, ["check", "requests", "--format", "sarif"])
    parsed = json.loads(result.output)
    assert "$schema" in parsed


def test_sarif_blocked_has_error_level():
    runner = CliRunner()
    with _patch_run(_blocked_verdict()):
        result = runner.invoke(main, ["check", "reqeusts", "--format", "sarif"])
    parsed = json.loads(result.output)
    levels = [r["level"] for r in parsed["runs"][0]["results"]]
    assert "error" in levels


# ---------------------------------------------------------------------------
# --ecosystem option
# ---------------------------------------------------------------------------

def test_ecosystem_npm():
    runner = CliRunner()
    npm_verdict = _safe_verdict(name="express", ecosystem="npm")
    with _patch_run(npm_verdict):
        result = runner.invoke(main, ["check", "express", "--ecosystem", "npm"])
    assert "express" in result.output
    assert "npm" in result.output


# ---------------------------------------------------------------------------
# --offline flag sets env var
# ---------------------------------------------------------------------------

def test_offline_flag_sets_env(monkeypatch):
    """--offline must set GHOSTDEP_OFFLINE=1 before calling run_checks."""
    captured_env = {}

    def fake_run_checks(name, ecosystem):
        import os
        captured_env["val"] = os.environ.get("GHOSTDEP_OFFLINE")
        return _safe_verdict()

    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=fake_run_checks):
        runner.invoke(main, ["check", "requests", "--offline"])
    assert captured_env.get("val") == "1"
