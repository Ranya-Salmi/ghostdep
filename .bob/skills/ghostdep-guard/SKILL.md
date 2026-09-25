---
name: ghostdep-guard
description: >-
  Vet every new dependency with the GhostDep MCP tool before adding or
  installing it; block hallucinated, typosquatted or vulnerable packages and
  choose a verified alternative.
---

---
name: ghostdep-guard
description: Vet every new dependency with the GhostDep MCP tool before adding or installing it; block hallucinated, typosquatted or vulnerable packages and choose a verified alternative.
user-invocable: true
---
Before adding any package to a dependency file (requirements.txt,
pyproject.toml, package.json) or running any install command, follow
these phases in order. Never install a package that has not been checked.

## Phase 1: Collect
List every package you intend to add, with its ecosystem (pypi or npm).

## Phase 2: Verify
Call the ghostdep `check_package` MCP tool for each package.
Record the verdict (SAFE, SUSPICIOUS, BLOCKED) and every reason returned.

## Phase 3: Decide
- SAFE: proceed.
- SUSPICIOUS: do not install. Explain the risk and ask the user to confirm.
- BLOCKED: never install. Identify a well-known alternative that provides
  the same functionality, verify it with check_package, and use it only
  if the verdict is SAFE.

## Phase 4: Report
Append to ghostdep_reports/decisions.md, for each package:
- Package requested, verdict, reasons
- Alternative chosen (if any) and why
Then continue the original task using only SAFE packages.
