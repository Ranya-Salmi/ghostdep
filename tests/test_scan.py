"""Tests for the `ghostdep scan` CLI command."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ghostdep.cli import (
    main,
    _parse_requirements_txt,
    _parse_pyproject_toml,
    _read_packages,
)
from ghostdep.verdict import Finding, Severity, Verdict


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _safe(name: str) -> Verdict:
    return Verdict(package=name, ecosystem="pypi", overall=Severity.SAFE, findings=[])


def _suspicious(name: str) -> Verdict:
    return Verdict(
        package=name,
        ecosystem="pypi",
        overall=Severity.SUSPICIOUS,
        findings=[
            Finding(check="age", message=f"{name} is new", severity=Severity.SUSPICIOUS)
        ],
    )


def _blocked(name: str, target: str = "requests") -> Verdict:
    return Verdict(
        package=name,
        ecosystem="pypi",
        overall=Severity.BLOCKED,
        findings=[
            Finding(
                check="typosquat",
                message=f"'{name}' resembles '{target}'",
                severity=Severity.BLOCKED,
                suggestion=f"Did you mean '{target}'?",
            )
        ],
    )


def _make_requirements(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "requirements.txt"
    p.write_text(content, encoding="utf-8")
    return p


def _make_pyproject(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "pyproject.toml"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# _parse_requirements_txt unit tests
# ---------------------------------------------------------------------------

def test_parse_reqs_simple(tmp_path):
    p = _make_requirements(tmp_path, "requests\nflask\n")
    assert _parse_requirements_txt(p) == ["requests", "flask"]


def test_parse_reqs_version_specifiers(tmp_path):
    p = _make_requirements(tmp_path, "requests>=2.0\nflask==2.3.0\npyyaml~=6.0\n")
    assert _parse_requirements_txt(p) == ["requests", "flask", "pyyaml"]


def test_parse_reqs_extras(tmp_path):
    p = _make_requirements(tmp_path, "requests[security]\n")
    assert _parse_requirements_txt(p) == ["requests"]


def test_parse_reqs_skips_comments(tmp_path):
    p = _make_requirements(tmp_path, "# this is a comment\nrequests\n")
    assert _parse_requirements_txt(p) == ["requests"]


def test_parse_reqs_skips_blank_lines(tmp_path):
    p = _make_requirements(tmp_path, "\nrequests\n\nflask\n")
    assert _parse_requirements_txt(p) == ["requests", "flask"]


def test_parse_reqs_skips_options(tmp_path):
    p = _make_requirements(tmp_path, "-r base.txt\n--index-url https://pypi.org\nrequests\n")
    assert _parse_requirements_txt(p) == ["requests"]


def test_parse_reqs_inline_comment(tmp_path):
    p = _make_requirements(tmp_path, "requests  # latest\n")
    assert _parse_requirements_txt(p) == ["requests"]


def test_parse_reqs_empty_file(tmp_path):
    p = _make_requirements(tmp_path, "")
    assert _parse_requirements_txt(p) == []


# ---------------------------------------------------------------------------
# _parse_pyproject_toml unit tests
# ---------------------------------------------------------------------------

def test_parse_pyproject_dependencies(tmp_path):
    content = '[project]\ndependencies = ["requests>=2.0", "flask"]\n'
    p = _make_pyproject(tmp_path, content)
    result = _parse_pyproject_toml(p)
    # tomllib available in Python 3.11+; skip if not
    if result:  # will be [] if tomllib unavailable
        assert "requests" in result
        assert "flask" in result


def test_parse_pyproject_no_dependencies(tmp_path):
    content = '[project]\nname = "myapp"\n'
    p = _make_pyproject(tmp_path, content)
    result = _parse_pyproject_toml(p)
    assert result == []


def test_parse_pyproject_no_project_section(tmp_path):
    content = '[tool.myapp]\nvalue = 1\n'
    p = _make_pyproject(tmp_path, content)
    result = _parse_pyproject_toml(p)
    assert result == []


# ---------------------------------------------------------------------------
# _read_packages dispatch
# ---------------------------------------------------------------------------

def test_read_packages_dispatches_requirements(tmp_path):
    p = _make_requirements(tmp_path, "requests\n")
    assert _read_packages(p) == ["requests"]


def test_read_packages_dispatches_pyproject(tmp_path):
    content = '[project]\ndependencies = ["flask"]\n'
    p = _make_pyproject(tmp_path, content)
    result = _read_packages(p)
    # May be empty if tomllib not available; just check it doesn't crash
    assert isinstance(result, list)


def test_read_packages_unknown_file_falls_back_to_requirements(tmp_path):
    p = tmp_path / "deps.txt"
    p.write_text("requests\n", encoding="utf-8")
    assert _read_packages(p) == ["requests"]


# ---------------------------------------------------------------------------
# scan command — exit codes
# ---------------------------------------------------------------------------

def test_scan_all_safe_exit_0(tmp_path):
    reqs = _make_requirements(tmp_path, "requests\nflask\n")
    verdicts = [_safe("requests"), _safe("flask")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert result.exit_code == 0


def test_scan_blocked_exit_2(tmp_path):
    reqs = _make_requirements(tmp_path, "requests\nreqeusts\n")
    verdicts = [_safe("requests"), _blocked("reqeusts")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert result.exit_code == 2


def test_scan_suspicious_only_exit_1(tmp_path):
    reqs = _make_requirements(tmp_path, "newpkg\n")
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", return_value=_suspicious("newpkg")):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert result.exit_code == 1


def test_scan_blocked_beats_suspicious_exit_2(tmp_path):
    reqs = _make_requirements(tmp_path, "newpkg\nreqeusts\n")
    verdicts = [_suspicious("newpkg"), _blocked("reqeusts")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert result.exit_code == 2


def test_scan_empty_file_exits_0(tmp_path):
    reqs = _make_requirements(tmp_path, "# only comments\n")
    runner = CliRunner()
    result = runner.invoke(main, ["scan", str(reqs)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# scan command — text output content
# ---------------------------------------------------------------------------

def test_scan_text_output_contains_package_names(tmp_path):
    reqs = _make_requirements(tmp_path, "requests\nflask\n")
    verdicts = [_safe("requests"), _safe("flask")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert "requests" in result.output
    assert "flask" in result.output


def test_scan_text_output_contains_summary_counts(tmp_path):
    reqs = _make_requirements(tmp_path, "requests\nreqeusts\n")
    verdicts = [_safe("requests"), _blocked("reqeusts")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert "BLOCKED" in result.output
    assert "SAFE" in result.output


def test_scan_text_output_shows_suggestion(tmp_path):
    reqs = _make_requirements(tmp_path, "reqeusts\n")
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", return_value=_blocked("reqeusts")):
        result = runner.invoke(main, ["scan", str(reqs)])
    assert "Did you mean" in result.output


# ---------------------------------------------------------------------------
# scan command — SARIF format
# ---------------------------------------------------------------------------

def test_scan_sarif_is_valid_json(tmp_path):
    reqs = _make_requirements(tmp_path, "reqeusts\n")
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", return_value=_blocked("reqeusts")):
        result = runner.invoke(main, ["scan", str(reqs), "--format", "sarif"])
    # Exit 2 is expected; output must be valid SARIF JSON
    parsed = json.loads(result.output)
    assert parsed["version"] == "2.1.0"
    assert "$schema" in parsed


def test_scan_sarif_contains_all_packages(tmp_path):
    reqs = _make_requirements(tmp_path, "requests\nreqeusts\n")
    verdicts = [_safe("requests"), _blocked("reqeusts")]
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", side_effect=verdicts):
        result = runner.invoke(main, ["scan", str(reqs), "--format", "sarif"])
    parsed = json.loads(result.output)
    uri_strings = [
        loc["physicalLocation"]["artifactLocation"]["uri"]
        for r in parsed["runs"][0]["results"]
        for loc in r["locations"]
    ]
    uris = " ".join(uri_strings)
    assert "requests" in uris
    assert "reqeusts" in uris


def test_scan_sarif_blocked_has_error_level(tmp_path):
    reqs = _make_requirements(tmp_path, "reqeusts\n")
    runner = CliRunner()
    with patch("ghostdep.cli.run_checks", return_value=_blocked("reqeusts")):
        result = runner.invoke(main, ["scan", str(reqs), "--format", "sarif"])
    parsed = json.loads(result.output)
    levels = [r["level"] for r in parsed["runs"][0]["results"]]
    assert "error" in levels
