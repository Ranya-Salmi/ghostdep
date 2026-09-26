"""SARIF 2.1.0 emitter — converts a Verdict to a SARIF JSON document."""
from __future__ import annotations

import json
from importlib.metadata import version as _pkg_version, PackageNotFoundError
from typing import Any

from ghostdep.verdict import Severity, Verdict


def _tool_version() -> str:
    try:
        return _pkg_version("ghostdep")
    except PackageNotFoundError:
        return "0.0.0"


_LEVEL_MAP = {
    Severity.BLOCKED: "error",
    Severity.SUSPICIOUS: "warning",
    Severity.SAFE: "note",
}


def verdict_to_sarif(verdict: Verdict) -> dict[str, Any]:
    """Convert a Verdict to a SARIF 2.1.0 document (as a plain dict).

    If there are no findings a single SAFE result is emitted so that
    GitHub code-scanning shows a clean run rather than an empty file.
    """
    results: list[dict[str, Any]] = []

    findings = verdict.findings or []
    if not findings:
        # Emit a single clean result so the file is non-empty
        results.append(
            {
                "ruleId": "safe",
                "level": "note",
                "message": {"text": f"No issues found for {verdict.package} ({verdict.ecosystem})."},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f"pkg://{verdict.ecosystem}/{verdict.package}"
                            }
                        }
                    }
                ],
            }
        )
    else:
        for f in findings:
            result: dict[str, Any] = {
                "ruleId": f.check,
                "level": _LEVEL_MAP[f.severity],
                "message": {"text": f.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f"pkg://{verdict.ecosystem}/{verdict.package}"
                            }
                        }
                    }
                ],
            }
            if f.suggestion:
                result["message"]["text"] += f"  Suggestion: {f.suggestion}"
            results.append(result)

    return {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ghostdep",
                        "version": _tool_version(),
                        "informationUri": "https://github.com/ghostdep/ghostdep",
                        "rules": [],
                    }
                },
                "results": results,
            }
        ],
    }


def verdict_to_sarif_str(verdict: Verdict, indent: int = 2) -> str:
    """Return the SARIF document as a formatted JSON string."""
    return json.dumps(verdict_to_sarif(verdict), indent=indent)


def verdicts_to_sarif(verdicts: list[Verdict]) -> dict[str, Any]:
    """Merge multiple Verdicts into a single SARIF document (for `scan`)."""
    all_results: list[dict[str, Any]] = []
    for v in verdicts:
        doc = verdict_to_sarif(v)
        all_results.extend(doc["runs"][0]["results"])

    return {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ghostdep",
                        "version": _tool_version(),
                        "informationUri": "https://github.com/ghostdep/ghostdep",
                        "rules": [],
                    }
                },
                "results": all_results,
            }
        ],
    }


def verdicts_to_sarif_str(verdicts: list[Verdict], indent: int = 2) -> str:
    """Return multi-verdict SARIF document as a formatted JSON string."""
    return json.dumps(verdicts_to_sarif(verdicts), indent=indent)
