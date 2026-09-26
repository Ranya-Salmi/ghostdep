"""Tests for `ghostdep install` and policy-aware CLI commands."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from ghostdep.cli import _name_from_spec, main
from ghostdep.verdict import Finding, Severity, Verdict


def _v(name, sev, msg="", suggestion=None):
    findings = [] if sev == Severity.SAFE else [Finding("t", msg, sev, suggestion)]
    return Verdict.aggregate(name, "pypi", findings)


def test_name_from_spec():
    assert _name_from_spec("requests[socks]>=2.31") == "requests"
    assert _name_from_spec("python-dateutil==2.9.0") == "python-dateutil"
    assert _name_from_spec("@scope/pkg@1.2.0") == "@scope/pkg"


def test_blocked_package_installs_nothing():
    with patch("ghostdep.cli.run_checks",
               return_value=_v("reqeusts", Severity.BLOCKED, "typosquat",
                               "Did you mean 'requests'?")), \
         patch("ghostdep.cli.subprocess.call") as call:
        result = CliRunner().invoke(main, ["install", "reqeusts"])
    assert result.exit_code == 2
    assert "Nothing was installed" in result.output
    assert "Did you mean 'requests'?" in result.output
    call.assert_not_called()


def test_one_blocked_package_stops_the_whole_install():
    verdicts = [_v("requests", Severity.SAFE), _v("fake-pkg", Severity.BLOCKED, "404")]
    with patch("ghostdep.cli.run_checks", side_effect=verdicts), \
         patch("ghostdep.cli.subprocess.call") as call:
        result = CliRunner().invoke(main, ["install", "requests", "fake-pkg"])
    assert result.exit_code == 2
    call.assert_not_called()


def test_safe_packages_run_pip_with_original_specs():
    with patch("ghostdep.cli.run_checks", return_value=_v("requests", Severity.SAFE)), \
         patch("ghostdep.cli.subprocess.call", return_value=0) as call:
        result = CliRunner().invoke(main, ["install", "requests>=2.31"])
    assert result.exit_code == 0
    cmd = call.call_args[0][0]
    assert cmd[1:4] == ["-m", "pip", "install"] and cmd[-1] == "requests>=2.31"


def test_suspicious_declined_installs_nothing():
    with patch("ghostdep.cli.run_checks",
               return_value=_v("newpkg", Severity.SUSPICIOUS, "3 days old")), \
         patch("ghostdep.cli.subprocess.call") as call:
        result = CliRunner().invoke(main, ["install", "newpkg"], input="n\n")
    assert result.exit_code == 1
    call.assert_not_called()


def test_suspicious_with_yes_installs():
    with patch("ghostdep.cli.run_checks",
               return_value=_v("newpkg", Severity.SUSPICIOUS, "3 days old")), \
         patch("ghostdep.cli.subprocess.call", return_value=0) as call:
        result = CliRunner().invoke(main, ["install", "newpkg", "--yes"])
    assert result.exit_code == 0
    call.assert_called_once()


def test_dry_run_prints_command_only():
    with patch("ghostdep.cli.run_checks", return_value=_v("requests", Severity.SAFE)), \
         patch("ghostdep.cli.subprocess.call") as call:
        result = CliRunner().invoke(main, ["install", "requests", "--dry-run"])
    assert result.exit_code == 0
    assert "Would run" in result.output
    call.assert_not_called()


def test_npm_uses_npm_install():
    with patch("ghostdep.cli.run_checks", return_value=_v("express", Severity.SAFE)), \
         patch("ghostdep.cli.subprocess.call", return_value=0) as call:
        CliRunner().invoke(main, ["install", "express", "--ecosystem", "npm"])
    assert call.call_args[0][0][:2] == ["npm", "install"]


def test_policy_allow_skips_registry_checks(tmp_path, monkeypatch):
    policy = tmp_path / "p.toml"
    policy.write_text('[policy]\nallow = ["acme-internal-auth"]\n', encoding="utf-8")
    monkeypatch.setenv("GHOSTDEP_POLICY", str(policy))
    with patch("ghostdep.cli.run_checks") as rc:
        result = CliRunner().invoke(main, ["check", "acme-internal-auth"])
    assert result.exit_code == 0
    rc.assert_not_called()


def test_policy_deny_blocks_scan(tmp_path, monkeypatch):
    policy = tmp_path / "p.toml"
    policy.write_text('[policy]\ndeny = ["pycrypto"]\n', encoding="utf-8")
    monkeypatch.setenv("GHOSTDEP_POLICY", str(policy))
    req = tmp_path / "requirements.txt"
    req.write_text("pycrypto\n", encoding="utf-8")
    with patch("ghostdep.cli.run_checks") as rc:
        result = CliRunner().invoke(main, ["scan", str(req)])
    assert result.exit_code == 2
    rc.assert_not_called()


def test_scan_accepts_multiple_files_and_dedupes(tmp_path):
    a = tmp_path / "requirements.txt"
    a.write_text("requests\n", encoding="utf-8")
    b = tmp_path / "requirements-dev.txt"
    b.write_text("Requests\npytest\n", encoding="utf-8")
    with patch("ghostdep.cli.run_checks",
               side_effect=lambda n, e: _v(n, Severity.SAFE)) as rc:
        result = CliRunner().invoke(main, ["scan", str(a), str(b)])
    assert result.exit_code == 0
    assert rc.call_count == 2
