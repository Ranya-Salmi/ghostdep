"""Tests for Check 1 — Existence."""
from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from ghostdep.checks.existence import check_existence
from ghostdep.verdict import Severity


# ---------------------------------------------------------------------------
# PyPI
# ---------------------------------------------------------------------------

def test_pypi_exists(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypi.org/pypi/requests/json",
        json={"info": {"name": "requests", "version": "2.31.0"}, "releases": {}},
    )
    finding, data = check_existence("requests", "pypi")
    assert finding is None
    assert data is not None
    assert data["info"]["name"] == "requests"


def test_pypi_not_found(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypi.org/pypi/fakepkg123xyz/json",
        status_code=404,
    )
    finding, data = check_existence("fakepkg123xyz", "pypi")
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert data is None


def test_pypi_server_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypi.org/pypi/requests/json",
        status_code=503,
    )
    finding, data = check_existence("requests", "pypi")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert data is None


def test_pypi_rate_limit_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypi.org/pypi/requests/json",
        status_code=429,
    )
    finding, data = check_existence("requests", "pypi")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


def test_pypi_timeout_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(
        httpx.TimeoutException("timed out"),
        url="https://pypi.org/pypi/requests/json",
    )
    finding, data = check_existence("requests", "pypi")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert data is None


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

def test_npm_exists(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://registry.npmjs.org/express",
        json={
            "name": "express",
            "dist-tags": {"latest": "4.18.2"},
            "time": {"created": "2010-12-29T19:39:24.173Z"},
        },
    )
    finding, data = check_existence("express", "npm")
    assert finding is None
    assert data["name"] == "express"


def test_npm_not_found(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://registry.npmjs.org/fakepkg123xyz",
        status_code=404,
    )
    finding, data = check_existence("fakepkg123xyz", "npm")
    assert finding is not None
    assert finding.severity == Severity.BLOCKED
    assert data is None


def test_npm_server_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://registry.npmjs.org/express",
        status_code=500,
    )
    finding, data = check_existence("express", "npm")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS


# ---------------------------------------------------------------------------
# Error results must NOT be cached
# ---------------------------------------------------------------------------

def test_server_error_not_cached(httpx_mock: HTTPXMock):
    """A 5xx response must not be stored in cache; second call should re-hit network."""
    httpx_mock.add_response(
        url="https://pypi.org/pypi/requests/json",
        status_code=503,
    )
    httpx_mock.add_response(
        url="https://pypi.org/pypi/requests/json",
        json={"info": {"name": "requests", "version": "2.31.0"}, "releases": {}},
    )
    finding1, _ = check_existence("requests", "pypi")
    assert finding1 is not None and finding1.severity == Severity.SUSPICIOUS

    finding2, data2 = check_existence("requests", "pypi")
    assert finding2 is None
    assert data2 is not None
