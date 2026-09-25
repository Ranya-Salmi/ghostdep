
"""Tests for Check 3 — Popularity."""
from __future__ import annotations

import pytest
import httpx
from pytest_httpx import HTTPXMock

from ghostdep.checks.popularity import check_popularity
from ghostdep.constants import NPM_MIN_DOWNLOADS_WEEK, PYPI_MIN_DOWNLOADS_MONTH
from ghostdep.verdict import Severity


# ---------------------------------------------------------------------------
# PyPI
# ---------------------------------------------------------------------------

def test_pypi_popular_package(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypistats.org/api/packages/requests/recent",
        json={"data": {"last_month": 250_000_000}},
    )
    finding, count = check_popularity("requests", "pypi")
    assert finding is None
    assert count == 250_000_000


def test_pypi_low_downloads(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypistats.org/api/packages/obscurepkg/recent",
        json={"data": {"last_month": 50}},
    )
    finding, count = check_popularity("obscurepkg", "pypi")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert count == 50
    assert str(PYPI_MIN_DOWNLOADS_MONTH) in finding.message or "1,000" in finding.message


def test_pypi_exactly_at_threshold_is_safe(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypistats.org/api/packages/pkg/recent",
        json={"data": {"last_month": PYPI_MIN_DOWNLOADS_MONTH}},
    )
    finding, count = check_popularity("pkg", "pypi")
    assert finding is None


def test_pypi_network_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(
        httpx.TimeoutException("timeout"),
        url="https://pypistats.org/api/packages/requests/recent",
    )
    finding, count = check_popularity("requests", "pypi")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert count is None


def test_pypi_404_skips(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://pypistats.org/api/packages/unknownpkg/recent",
        status_code=404,
    )
    finding, count = check_popularity("unknownpkg", "pypi")
    assert finding is None
    assert count is None


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

def test_npm_popular_package(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.npmjs.org/downloads/point/last-week/express",
        json={"downloads": 35_000_000, "package": "express"},
    )
    finding, count = check_popularity("express", "npm")
    assert finding is None
    assert count == 35_000_000


def test_npm_low_downloads(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.npmjs.org/downloads/point/last-week/tinypkg",
        json={"downloads": 10, "package": "tinypkg"},
    )
    finding, count = check_popularity("tinypkg", "npm")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert count == 10


def test_npm_network_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(
        httpx.TimeoutException("timeout"),
        url="https://api.npmjs.org/downloads/point/last-week/express",
    )
    finding, count = check_popularity("express", "npm")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
    assert count is None


def test_npm_server_error_is_suspicious(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.npmjs.org/downloads/point/last-week/express",
        status_code=500,
    )
    finding, count = check_popularity("express", "npm")
    assert finding is not None
    assert finding.severity == Severity.SUSPICIOUS
