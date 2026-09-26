"""Check 1 — Existence: verify the package exists in the registry.

Returns
-------
- None         if the package exists (200 OK)
- BLOCKED      Finding if the package is not found (404)
- SUSPICIOUS   Finding if the registry is unreachable (timeout / 5xx / 429)
  The SUSPICIOUS finding is NOT cached.
"""
from __future__ import annotations

from typing import Optional

import httpx

from ghostdep.cache import cached_get
from ghostdep.constants import NPM_REGISTRY_URL, PYPI_JSON_URL
from ghostdep.verdict import Finding, Severity

_DISPLAY = {"pypi": "PyPI", "npm": "npm"}


def check_existence(name: str, ecosystem: str) -> tuple[Optional[Finding], Optional[dict]]:
    """Return (finding_or_None, registry_data_or_None).

    registry_data is the parsed JSON on success; None on any error.
    The finding is None on success (package found).
    """
    url = _registry_url(name, ecosystem)

    try:
        data = cached_get(url)
    except (httpx.TimeoutException, httpx.HTTPStatusError):
        return _unreachable(ecosystem), None

    if data is None:
        # cached_get stores None for 404 responses
        return Finding(
            check="existence",
            message=f"Package '{name}' not found in {_DISPLAY.get(ecosystem, ecosystem.upper())} registry.",
            severity=Severity.BLOCKED,
        ), None

    return None, data


def _registry_url(name: str, ecosystem: str) -> str:
    if ecosystem == "pypi":
        return PYPI_JSON_URL.format(name=name)
    elif ecosystem == "npm":
        return NPM_REGISTRY_URL.format(name=name)
    raise ValueError(f"Unsupported ecosystem: {ecosystem!r}")


def _unreachable(ecosystem: str) -> Finding:
    return Finding(
        check="existence",
        message=f"Could not verify package in {_DISPLAY.get(ecosystem, ecosystem.upper())} registry (network error).",
        severity=Severity.SUSPICIOUS,
    )
