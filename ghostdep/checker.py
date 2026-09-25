"""Checker orchestrator — runs all five checks and returns a Verdict.

Flow
----
1. Existence check (Check 1): if BLOCKED, skip remaining checks.
2. Resolve latest version from registry data.
3. Run checks 2–5 independently (age, popularity, typosquat, vulnerabilities).
4. Aggregate findings into a Verdict.

The orchestrator is synchronous to keep the logic simple and deterministic.
The MCP server can call it in a thread if needed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ghostdep.checks.age import check_age
from ghostdep.checks.existence import check_existence
from ghostdep.checks.popularity import check_popularity
from ghostdep.checks.typosquat import check_typosquat
from ghostdep.checks.vulnerabilities import check_vulnerabilities
from ghostdep.verdict import Finding, Severity, Verdict


def run_checks(name: str, ecosystem: str, version: Optional[str] = None) -> Verdict:
    """Run all checks and return a Verdict.

    Parameters
    ----------
    name:       package name
    ecosystem:  "pypi" or "npm"
    version:    specific version to install; defaults to latest from registry
    """
    ecosystem = ecosystem.lower().strip()
    if ecosystem not in ("pypi", "npm"):
        raise ValueError(f"Unsupported ecosystem: {ecosystem!r}. Use 'pypi' or 'npm'.")

    findings: list[Finding] = []

    # ------------------------------------------------------------------
    # Check 1 — Existence
    # ------------------------------------------------------------------
    existence_finding, registry_data = check_existence(name, ecosystem)
    if existence_finding is not None:
        findings.append(existence_finding)
        if existence_finding.severity == Severity.BLOCKED:
            # Package doesn't exist — no point running other checks
            return Verdict.aggregate(name, ecosystem, findings)

    # ------------------------------------------------------------------
    # Resolve version
    # ------------------------------------------------------------------
    resolved_version = version or _resolve_latest_version(ecosystem, registry_data)

    # ------------------------------------------------------------------
    # Check 2 — Age (uses registry_data already fetched)
    # ------------------------------------------------------------------
    first_release: Optional[datetime] = None
    if registry_data is not None:
        age_finding = check_age(name, ecosystem, registry_data)
        if age_finding is not None:
            findings.append(age_finding)
        # Extract first_release for use in typosquat check
        from ghostdep.checks.age import _first_release as _fr
        first_release = _fr(ecosystem, registry_data)

    # ------------------------------------------------------------------
    # Check 3 — Popularity
    # ------------------------------------------------------------------
    popularity_finding, download_count = check_popularity(name, ecosystem)
    if popularity_finding is not None:
        findings.append(popularity_finding)

    # ------------------------------------------------------------------
    # Check 4 — Typosquatting
    # ------------------------------------------------------------------
    typosquat_finding = check_typosquat(name, ecosystem, download_count, first_release)
    if typosquat_finding is not None:
        findings.append(typosquat_finding)

    # ------------------------------------------------------------------
    # Check 5 — Vulnerabilities
    # ------------------------------------------------------------------
    if resolved_version:
        vuln_finding = check_vulnerabilities(name, ecosystem, resolved_version)
        if vuln_finding is not None:
            findings.append(vuln_finding)

    return Verdict.aggregate(name, ecosystem, findings)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_latest_version(ecosystem: str, registry_data: Optional[dict]) -> Optional[str]:
    """Extract the latest version string from registry data."""
    if registry_data is None:
        return None
    if ecosystem == "pypi":
        return registry_data.get("info", {}).get("version")
    elif ecosystem == "npm":
        return registry_data.get("dist-tags", {}).get("latest")
    return None
