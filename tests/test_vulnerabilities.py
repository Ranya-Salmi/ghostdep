"""Tests for Check 5 — Vulnerabilities."""
from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from ghostdep.checks.vulnerabilities import check_vulnerabilities
from ghostdep.verdict import Severity


OSV_URL = "https://api.osv.dev/v1/query"


def test_no_vulns_is_safe(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=OSV_URL, json={"vulns": []})
    finding = check_vulnerabilities("requests", "pypi", "2.31.0")
    assert finding is None


def test_critical_vuln_is_blocked(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {
                    "id": "GHSA-xxxx-yyyy-zzzz",
                    "aliases": ["CVE-2023-99999"],
                    "database_specific": {"severity": "CRITICAL"},
                }
            ]
        },
    )
    finding = check_vulnerabilities("badpkg", "pypi", "1.0.0")
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert "GHSA-xxxx-yyyy-zzzz" in finding.message


def test_high_vuln_is_blocked(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {
                    "id": "GHSA-high-0000-0000",
                    "aliases": [],
                    "database_specific": {"severity": "HIGH"},
                }
            ]
        },
    )
    finding = check_vulnerabilities("badpkg", "pypi", "1.0.0")
    assert finding is not None
    assert finding.severity == Severity.BLOCKED


def test_medium_vuln_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {
                    "id": "GHSA-med-0000-0000",
                    "aliases": [],
                    "database_specific": {"severity": "MEDIUM"},
                }
            ]
        },
    )
    finding = check_vulnerabilities("badpkg", "pypi", "1.0.0")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_low_vuln_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {
                    "id": "GHSA-low-0000-0000",
                    "aliases": [],
                    "database_specific": {"severity": "LOW"},
                }
            ]
        },
    )
    finding = check_vulnerabilities("badpkg", "pypi", "1.0.0")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_multiple_vulns_shows_ids(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url=OSV_URL,
        json={
            "vulns": [
                {"id": "GHSA-0001", "aliases": [], "database_specific": {"severity": "HIGH"}},
                {"id": "GHSA-0002", "aliases": [], "database_specific": {"severity": "MEDIUM"}},
                {"id": "GHSA-0003", "aliases": [], "database_specific": {"severity": "LOW"}},
                {"id": "GHSA-0004", "aliases": [], "database_specific": {"severity": "LOW"}},
            ]
        },
    )
    finding = check_vulnerabilities("badpkg", "pypi", "1.0.0")
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert "GHSA-0001" in finding.message
    assert "+1 more" in finding.message  # 4 total, show 3, note 1 extra


def test_timeout_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(
        httpx.TimeoutException("timeout"),
        url=OSV_URL,
    )
    finding = check_vulnerabilities("requests", "pypi", "2.31.0")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_osv_server_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST", url=OSV_URL, status_code=500)
    finding = check_vulnerabilities("requests", "pypi", "2.31.0")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_npm_ecosystem_uses_correct_osv_name(httpx_mock: HTTPXMock):
    """OSV ecosystem name for npm must be 'npm', not 'NPM' or 'Node'."""
    captured = []

    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"vulns": []})

    httpx_mock.add_callback(handler, method="POST", url=OSV_URL)
    check_vulnerabilities("express", "npm", "4.18.2")
    assert captured[0]["package"]["ecosystem"] == "npm"


def test_pypi_ecosystem_uses_correct_osv_name(httpx_mock: HTTPXMock):
    captured = []

    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"vulns": []})

    httpx_mock.add_callback(handler, method="POST", url=OSV_URL)
    check_vulnerabilities("requests", "pypi", "2.31.0")
    assert captured[0]["package"]["ecosystem"] == "PyPI"


def test_version_always_included_in_osv_request(httpx_mock: HTTPXMock):
    """Ensure version is always sent to OSV."""
    captured = []

    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"vulns": []})

    httpx_mock.add_callback(handler, method="POST", url=OSV_URL)
    check_vulnerabilities("requests", "pypi", "2.31.0")
    assert "version" in captured[0]
    assert captured[0]["version"] == "2.31.0"
