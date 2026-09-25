"""Integration tests for the checker orchestrator."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import httpx
from pytest_httpx import HTTPXMock

from ghostdep.checker import run_checks
from ghostdep.verdict import Severity


OSV_URL = "https://api.osv.dev/v1/query"
PYPISTATS_URL = "https://pypistats.org/api/packages/{}/recent"
NPM_DL_URL = "https://api.npmjs.org/downloads/point/last-week/{}"


def _old_ts() -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(days=365)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _pypi_registry(name: str = "requests", version: str = "2.31.0") -> dict:
    return {
        "info": {"name": name, "version": version},
        "releases": {
            version: [{"upload_time": _old_ts(), "filename": f"{name}-{version}.tar.gz"}]
        },
    }


def _npm_registry(name: str = "express", version: str = "4.18.2") -> dict:
    return {
        "name": name,
        "dist-tags": {"latest": version},
        "time": {
            "created": _old_ts() + "Z",
            version: _old_ts() + "Z",
        },
    }


# ---------------------------------------------------------------------------
# Clean well-known package — all checks pass
# ---------------------------------------------------------------------------

def test_clean_pypi_package(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://pypi.org/pypi/requests/json", json=_pypi_registry())
    httpx_mock.add_response(
        url=PYPISTATS_URL.format("requests"),
        json={"data": {"last_month": 250_000_000}},
    )
    httpx_mock.add_response(method="POST", url=OSV_URL, json={"vulns": []})

    verdict = run_checks("requests", "pypi")
    assert verdict.overall == Severity.SAFE
    assert verdict.findings == []


def test_clean_npm_package(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://registry.npmjs.org/express", json=_npm_registry())
    httpx_mock.add_response(
        url=NPM_DL_URL.format("express"),
        json={"downloads": 35_000_000},
    )
    httpx_mock.add_response(method="POST", url=OSV_URL, json={"vulns": []})

    verdict = run_checks("express", "npm")
    assert verdict.overall == Severity.SAFE


# ---------------------------------------------------------------------------
# Hallucinated package — 404 → BLOCKED, no further checks
# ---------------------------------------------------------------------------

def test_hallucinated_package_blocked(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypi.org/pypi/aifakepkg999/json",
        status_code=404,
    )
    verdict = run_checks("aifakepkg999", "pypi")
    assert verdict.overall == Severity.BLOCKED
    checks_run = [f.check for f in verdict.findings]
    assert "existence" in checks_run
    # No other checks should have fired (no extra HTTP calls were made)


# ---------------------------------------------------------------------------
# New package → SUSPICIOUS
# ---------------------------------------------------------------------------

def test_new_package_suspicious(httpx_mock: HTTPXMock):
    new_ts = (datetime.now(tz=timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    reg = {
        "info": {"name": "newpkg", "version": "0.1.0"},
        "releases": {
            "0.1.0": [{"upload_time": new_ts, "filename": "newpkg-0.1.0.tar.gz"}]
        },
    }
    httpx_mock.add_response(url="https://pypi.org/pypi/newpkg/json", json=reg)
    httpx_mock.add_response(
        url=PYPISTATS_URL.format("newpkg"),
        json={"data": {"last_month": 5}},
    )
    httpx_mock.add_response(method="POST", url=OSV_URL, json={"vulns": []})

    verdict = run_checks("newpkg", "pypi")
    assert verdict.overall == Severity.SUSPICIOUS
    check_names = [f.check for f in verdict.findings]
    assert "age" in check_names


# ---------------------------------------------------------------------------
# Typosquatted package → BLOCKED
# ---------------------------------------------------------------------------

def test_typosquat_blocked(httpx_mock: HTTPXMock):
    """'reqeusts' looks like 'requests' and has no downloads → BLOCKED."""
    new_ts = (datetime.now(tz=timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    reg = {
        "info": {"name": "reqeusts", "version": "1.0.0"},
        "releases": {
            "1.0.0": [{"upload_time": new_ts, "filename": "reqeusts-1.0.0.tar.gz"}]
        },
    }
    httpx_mock.add_response(url="https://pypi.org/pypi/reqeusts/json", json=reg)
    httpx_mock.add_response(
        url=PYPISTATS_URL.format("reqeusts"),
        json={"data": {"last_month": 5}},
    )
    httpx_mock.add_response(method="POST", url=OSV_URL, json={"vulns": []})

    # Patch top list so 'requests' is in it
    with patch(
        "ghostdep.checks.typosquat._load_top_list",
        side_effect=lambda eco: ["requests"] if eco == "pypi" else [],
    ):
        verdict = run_checks("reqeusts", "pypi")

    assert verdict.overall == Severity.BLOCKED
    typo_findings = [f for f in verdict.findings if f.check == "typosquat"]
    assert len(typo_findings) == 1
    assert typo_findings[0].suggestion is not None


# ---------------------------------------------------------------------------
# Vuln → BLOCKED
# ---------------------------------------------------------------------------

def test_vulnerable_package_blocked(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://pypi.org/pypi/oldpkg/json", json=_pypi_registry("oldpkg"))
    httpx_mock.add_response(
        url=PYPISTATS_URL.format("oldpkg"),
        json={"data": {"last_month": 5_000_000}},
    )
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {
                    "id": "CVE-2023-99999",
                    "aliases": [],
                    "database_specific": {"severity": "CRITICAL"},
                }
            ]
        },
    )
    verdict = run_checks("oldpkg", "pypi")
    assert verdict.overall == Severity.BLOCKED
    vuln_findings = [f for f in verdict.findings if f.check == "vulnerabilities"]
    assert len(vuln_findings) == 1


# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------

def test_version_passed_explicitly(httpx_mock: HTTPXMock):
    """When a version is passed, it must be sent to OSV, not the latest."""
    captured = []

    def osv_handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"vulns": []})

    httpx_mock.add_response(url="https://pypi.org/pypi/requests/json", json=_pypi_registry())
    httpx_mock.add_response(
        url=PYPISTATS_URL.format("requests"),
        json={"data": {"last_month": 250_000_000}},
    )
    httpx_mock.add_callback(osv_handler, method="POST", url=OSV_URL)

    run_checks("requests", "pypi", version="2.28.0")
    assert captured[0]["version"] == "2.28.0"


# ---------------------------------------------------------------------------
# Verdict aggregation
# ---------------------------------------------------------------------------

def test_verdict_aggregation_blocked_wins():
    from ghostdep.verdict import Finding, Verdict, Severity
    findings = [
        Finding(check="age", message="new", severity=Severity.SUSPICIOUS),
        Finding(check="typosquat", message="typo", severity=Severity.BLOCKED),
    ]
    v = Verdict.aggregate("pkg", "pypi", findings)
    assert v.overall == Severity.BLOCKED


def test_verdict_aggregation_suspicious_if_no_blocked():
    from ghostdep.verdict import Finding, Verdict, Severity
    findings = [
        Finding(check="age", message="new", severity=Severity.SUSPICIOUS),
    ]
    v = Verdict.aggregate("pkg", "pypi", findings)
    assert v.overall == Severity.SUSPICIOUS


def test_verdict_aggregation_safe_if_empty():
    from ghostdep.verdict import Verdict
    v = Verdict.aggregate("pkg", "pypi", [])
    assert v.overall == Severity.SAFE


# ---------------------------------------------------------------------------
# Invalid ecosystem
# ---------------------------------------------------------------------------

def test_invalid_ecosystem_raises():
    with pytest.raises(ValueError, match="Unsupported ecosystem"):
        run_checks("requests", "cargo")
