"""Team policy: allow and deny lists in a `.ghostdep.toml` file.

Private or internal packages don't exist on public registries, so GhostDep
would block them. A policy file lets a team allow them explicitly, and deny
packages it never wants installed.

Example `.ghostdep.toml` (searched for in the current directory and its parents,
or set GHOSTDEP_POLICY to a path):

    [policy]
    allow = ["acme-internal-auth", "acme-billing-client"]
    deny  = ["pycrypto"]   # abandoned; use pycryptodome

Names are compared the way pip does (case-insensitive; -, _ and . are equal).
The deny list always wins over the allow list.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ghostdep.verdict import Finding, Severity, Verdict

POLICY_FILENAME = ".ghostdep.toml"
POLICY_ENV = "GHOSTDEP_POLICY"


def normalize(name: str) -> str:
    """PEP 503 name normalisation."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class Policy:
    allow: set[str] = field(default_factory=set)
    deny: set[str] = field(default_factory=set)
    source: Optional[Path] = None

    @property
    def empty(self) -> bool:
        return not self.allow and not self.deny

    def verdict_for(self, name: str, ecosystem: str) -> Optional[Verdict]:
        """Return a policy verdict, or None if the policy says nothing."""
        key = normalize(name)
        where = self.source.name if self.source else "policy"
        if key in self.deny:
            return Verdict.aggregate(name, ecosystem, [Finding(
                check="policy",
                message=f"'{name}' is on the deny list in {where}.",
                severity=Severity.BLOCKED,
            )])
        if key in self.allow:
            return Verdict.aggregate(name, ecosystem, [Finding(
                check="policy",
                message=f"'{name}' is on the allow list in {where}; registry checks skipped.",
                severity=Severity.SAFE,
            )])
        return None


def _parse(path: Path) -> Policy:
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    section = data.get("policy", data)
    allow = {normalize(n) for n in section.get("allow", []) if isinstance(n, str)}
    deny = {normalize(n) for n in section.get("deny", []) if isinstance(n, str)}
    return Policy(allow=allow, deny=deny, source=path)


def find_policy_file(start: Optional[Path] = None) -> Optional[Path]:
    """Locate the policy file: GHOSTDEP_POLICY, else search upward from *start*."""
    env = os.environ.get(POLICY_ENV)
    if env:
        p = Path(env)
        return p if p.is_file() else None
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        candidate = d / POLICY_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_policy(start: Optional[Path] = None) -> Policy:
    """Load the applicable policy, or an empty one if there is none."""
    path = find_policy_file(start)
    return _parse(path) if path else Policy()
