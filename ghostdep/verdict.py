

"""Data models: Finding, Verdict, Severity."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"


@dataclass
class Finding:
    check: str  # e.g. "typosquat"
    message: str  # human-readable reason
    severity: Severity
    suggestion: Optional[str] = None  # e.g. "Did you mean 'requests'?"

    def to_dict(self) -> dict:
        d = {
            "check": self.check,
            "message": self.message,
            "severity": self.severity.value,
        }
        if self.suggestion is not None:
            d["suggestion"] = self.suggestion
        return d


# Aggregation precedence: BLOCKED > SUSPICIOUS > SAFE
_PRECEDENCE = {Severity.BLOCKED: 2, Severity.SUSPICIOUS: 1, Severity.SAFE: 0}


@dataclass
class Verdict:
    package: str
    ecosystem: str
    overall: Severity
    findings: list[Finding] = field(default_factory=list)

    @classmethod
    def aggregate(cls, package: str, ecosystem: str, findings: list[Finding]) -> "Verdict":
        """Compute the overall severity from a list of findings."""
        overall = Severity.SAFE
        for f in findings:
            if _PRECEDENCE[f.severity] > _PRECEDENCE[overall]:
                overall = f.severity
        return cls(package=package, ecosystem=ecosystem, overall=overall, findings=findings)

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "ecosystem": self.ecosystem,
            "overall": self.overall.value,
            "findings": [f.to_dict() for f in self.findings],
        }
