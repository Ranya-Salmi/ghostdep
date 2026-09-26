"""Tests for team allow/deny policies."""
from __future__ import annotations

from ghostdep.policy import Policy, find_policy_file, load_policy, normalize
from ghostdep.verdict import Severity


def _write(tmp_path, text):
    p = tmp_path / ".ghostdep.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_normalize_like_pip():
    assert normalize("Acme_Internal.Auth") == "acme-internal-auth"


def test_no_policy_file_gives_empty_policy(tmp_path, monkeypatch):
    monkeypatch.delenv("GHOSTDEP_POLICY", raising=False)
    policy = load_policy(tmp_path)
    assert policy.empty
    assert policy.verdict_for("anything", "pypi") is None


def test_allow_list_returns_safe(tmp_path, monkeypatch):
    monkeypatch.delenv("GHOSTDEP_POLICY", raising=False)
    _write(tmp_path, '[policy]\nallow = ["acme-internal-auth"]\n')
    v = load_policy(tmp_path).verdict_for("Acme_Internal_Auth", "pypi")
    assert v.overall == Severity.SAFE
    assert v.findings[0].check == "policy"


def test_deny_list_returns_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("GHOSTDEP_POLICY", raising=False)
    _write(tmp_path, '[policy]\ndeny = ["pycrypto"]\n')
    v = load_policy(tmp_path).verdict_for("pycrypto", "pypi")
    assert v.overall == Severity.BLOCKED
    assert "deny list" in v.findings[0].message


def test_deny_wins_over_allow():
    policy = Policy(allow={"x-pkg"}, deny={"x-pkg"})
    assert policy.verdict_for("x_pkg", "pypi").overall == Severity.BLOCKED


def test_policy_found_in_parent_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("GHOSTDEP_POLICY", raising=False)
    _write(tmp_path, '[policy]\nallow = ["a"]\n')
    sub = tmp_path / "service" / "api"
    sub.mkdir(parents=True)
    assert find_policy_file(sub) == tmp_path / ".ghostdep.toml"


def test_env_var_overrides_search(tmp_path, monkeypatch):
    other = tmp_path / "team-policy.toml"
    other.write_text('allow = ["b"]\n', encoding="utf-8")
    monkeypatch.setenv("GHOSTDEP_POLICY", str(other))
    policy = load_policy(tmp_path)
    assert policy.verdict_for("b", "pypi").overall == Severity.SAFE
