"""Check 5 — Vulnerabilities: query OSV.dev for known CVEs/GHSAs.

Always sends both package name AND version to OSV (name-only queries are
not used).  The version defaults to the latest release resolved from the
registry data.

Network errors produce a SUSPICIOUS "could not verify" finding (not cached).
"""
from __future__ import annotations

from typing import Optional

import httpx

from ghostdep.cache import cached_post
from ghostdep.constants import OSV_API_URL
from ghostdep.verdict import Finding, Severity

# OSV ecosystem names differ from our internal names
_ECOSYSTEM_MAP = {"pypi": "PyPI", "npm": "npm"}

# CVSS severity labels that we treat as BLOCKED
_HIGH_SEVERITY = {"CRITICAL", "HIGH"}


def check_vulnerabilities(
    name: str,
    ecosystem: str,
    version: str,
) -> Optional[Finding]:
    """Return a Finding if vulnerabilities exist, else None.

    Parameters
    ----------
    name:      package name
    ecosystem: "pypi" or "npm"
    version:   the specific version to query (must never be empty)
    """
    osv_ecosystem = _ECOSYSTEM_MAP.get(ecosystem, ecosystem)
    body = {
        "version": version,
        "package": {"name": name, "ecosystem": osv_ecosystem},
    }

    try:
        data = cached_post(OSV_API_URL, body)
    except (httpx.TimeoutException, httpx.HTTPStatusError):
        return Finding(
            check="vulnerabilities",
            message=f"Could not verify vulnerabilities for '{name}' v{version} (network error).",
            severity=Severity.SUSPICIOUS,
        )

    vulns = (data or {}).get("vulns", [])
    if not vulns:
        return None

    ids = []
    for v in vulns:
        ids.append(v.get("id", "?"))
        for alias in v.get("aliases", []):
            ids.append(alias)
    # Deduplicate preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for vid in ids:
        if vid not in seen:
            seen.add(vid)
            unique_ids.append(vid)

    max_severity = _max_severity(vulns)
    display_ids = ", ".join(unique_ids[:3])
    if len(unique_ids) > 3:
        display_ids += f" (+{len(unique_ids) - 3} more)"

    message = (
        f"'{name}' v{version} has {len(vulns)} known vulnerability(ies): {display_ids}."
    )

    if max_severity in _HIGH_SEVERITY:
        return Finding(check="vulnerabilities", message=message, severity=Severity.BLOCKED)
    return Finding(check="vulnerabilities", message=message, severity=Severity.SUSPICIOUS)


def _max_severity(vulns: list[dict]) -> str:
    """Return the highest severity label found across all vulns."""
    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    best = "UNKNOWN"
    for v in vulns:
        # Try database_specific.severity first
        sev = str(v.get("database_specific", {}).get("severity", "")).upper()
        if sev in order and order.index(sev) < order.index(best):
            best = sev
        # Also check severity[*].score (CVSS vector string contains severity word)
        for s in v.get("severity", []):
            score = str(s.get("score", "")).upper()
            for label in order:
                if label in score and order.index(label) < order.index(best):
                    best = label
    return best
