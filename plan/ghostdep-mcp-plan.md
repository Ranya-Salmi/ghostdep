# GhostDep MCP Server — Implementation Plan

> Security guard that stops AI coding agents from installing hallucinated,
> typosquatted, or vulnerable packages.

---

## 0. Amendments (supersede original plan where they conflict)

1. **Vulnerabilities**: Always query OSV with both package name **and** version
   (the version being installed, defaulting to the latest release fetched from
   the registry). Never send a name-only query.
2. **Errors**: Only an HTTP 404 from the registry means "package not found"
   (BLOCKED). Timeouts, 5xx, and rate-limit (429) responses produce a SUSPICIOUS
   finding `"could not verify"` and **must never be cached**.
3. **Typosquatting**: BLOCKED only when the queried name is a near-match **and**
   is itself low-download **or** younger than `MIN_AGE_DAYS`. A near-match that
   is itself popular is SAFE. Edit-distance threshold is **1** for names ≤ 5
   characters, **2** for longer names.
4. **Top lists**: Do not write package name lists from memory. A script
   `scripts/build_top_lists.py` downloads them from real public datasets
   (PyPI Stats + npm download-counts API) and writes `ghostdep/data/top_pypi.txt`
   and `ghostdep/data/top_npm.txt`. The resulting files are committed to the repo.
5. **PyPI age**: Determine the first release date by scanning the `upload_time`
   of every file across every release in the registry JSON, and taking the
   earliest timestamp.

---

## 1. Goals & Non-Goals

**Goals**
- Expose a single MCP tool `check_package(name, ecosystem)` over stdio transport.
- Run five deterministic checks and return a structured verdict.
- Cache every external API call to disk; fall back to bundled fixtures in offline mode.
- Provide a `ghostdep` CLI with human-readable and SARIF output modes.
- Ship a pytest suite covering each check in isolation plus integration paths.

**Non-Goals**
- No LLM calls inside the tool (all logic is rule-based and deterministic).
- No authentication / rate-limiting on the MCP server itself (it runs locally).
- No support for other ecosystems beyond `pypi` and `npm` in this iteration.

---

## 2. Project Structure

```
ghostdep/
├── plan/
│   └── ghostdep-mcp-plan.md          ← this file
├── pyproject.toml                     ← build metadata, deps, scripts entry point
├── README.md
├── ghostdep/                          ← importable package
│   ├── __init__.py
│   ├── server.py                      ← MCP server (stdio transport)
│   ├── cli.py                         ← `ghostdep check` CLI (click)
│   ├── checker.py                     ← orchestrates all checks, returns Verdict
│   ├── verdict.py                     ← Verdict / Finding dataclasses + BLOCKED/SUSPICIOUS/SAFE enum
│   ├── sarif.py                       ← converts Verdict → SARIF 2.1.0 JSON
│   ├── cache.py                       ← disk-cache wrapper (sqlite via diskcache)
│   ├── offline.py                     ← fixture loader for offline mode
│   ├── checks/
│   │   ├── __init__.py
│   │   ├── existence.py               ← Check 1: registry lookup
│   │   ├── age.py                     ← Check 2: first-release date
│   │   ├── popularity.py              ← Check 3: download counts
│   │   ├── typosquat.py               ← Check 4: edit-distance against top list
│   │   └── vulnerabilities.py         ← Check 5: OSV.dev query
│   └── data/
│       ├── top_pypi.txt               ← top-5 000 PyPI package names (static, bundled)
│       └── top_npm.txt                ← top-5 000 npm package names (static, bundled)
├── fixtures/                          ← saved API responses for offline mode / tests
│   ├── pypi/
│   │   └── requests.json
│   └── npm/
│       └── express.json
└── tests/
    ├── conftest.py
    ├── test_existence.py
    ├── test_age.py
    ├── test_popularity.py
    ├── test_typosquat.py
    ├── test_vulnerabilities.py
    ├── test_checker.py                ← end-to-end verdict tests
    ├── test_sarif.py
    └── test_cli.py
```

---

## 3. Dependencies

| Package | Purpose |
|---|---|
| `mcp[cli]` | Official Python MCP SDK (stdio server) |
| `httpx` | Async HTTP for registry / OSV API calls |
| `diskcache` | Disk-backed cache (SQLite) |
| `click` | CLI framework |
| `rapidfuzz` | Fast Levenshtein / edit-distance for typosquatting |
| `pytest` + `pytest-asyncio` | Test runner |
| `pytest-httpx` | Mock httpx calls in tests |

All listed in `pyproject.toml` under `[project.dependencies]`.

---

## 4. Configuration Constants

All thresholds live in `ghostdep/constants.py` as named module-level constants so
they can be tuned without touching logic:

```python
# Age check
MIN_AGE_DAYS = 30             # flag packages first released < 30 days ago

# Popularity check — PyPI
PYPI_MIN_DOWNLOADS_MONTH = 1_000    # monthly downloads via pypistats


# Popularity check — npm
NPM_MIN_DOWNLOADS_WEEK = 500        # weekly downloads via npm download-counts API

# Typosquatting
TYPOSQUAT_MAX_DISTANCE = 2          # max edit distance to flag as near-match
TOP_LIST_SIZE = 5_000               # how many entries to load from top_*.txt

# Caching
CACHE_DIR = "~/.cache/ghostdep"
CACHE_TTL_SECONDS = 3600            # 1 hour

# OSV
OSV_API_URL = "https://api.osv.dev/v1/query"
```

---

## 5. Data Models (`verdict.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class Severity(str, Enum):
    SAFE       = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED    = "BLOCKED"

@dataclass
class Finding:
    check: str          # e.g. "typosquat"
    message: str        # human-readable reason
    severity: Severity
    suggestion: Optional[str] = None   # e.g. "Did you mean 'requests'?"

@dataclass
class Verdict:
    package: str
    ecosystem: str
    overall: Severity
    findings: list[Finding] = field(default_factory=list)
```

Verdict aggregation rule (deterministic, no ties):
- Any BLOCKED finding → overall BLOCKED
- Any SUSPICIOUS finding (no BLOCKED) → overall SUSPICIOUS
- Otherwise → SAFE

---

## 6. Check Specifications

### 6.1 Check 1 — Existence (`checks/existence.py`)

| | PyPI | npm |
|---|---|---|
| URL | `https://pypi.org/pypi/{name}/json` | `https://registry.npmjs.org/{name}` |
| Success | HTTP 200 | HTTP 200 |
| Verdict on 404 | BLOCKED ("Package not found in PyPI/npm") | same |
| Verdict on timeout / 5xx / 429 | SUSPICIOUS ("could not verify — registry unreachable") — **not cached** | same |

If BLOCKED here, subsequent checks are skipped and a "hallucinated package" reason
is included in the findings. If SUSPICIOUS (network error), subsequent checks are
still attempted; each that also fails is labelled "could not verify".

### 6.2 Check 2 — Age (`checks/age.py`)

- **PyPI**: iterate every file object across every release in `releases`,
  collect all `upload_time` values, take the minimum. This is the true
  first-published timestamp regardless of which release is latest.
- **npm**: `time.created` field in registry JSON.
- Flag condition: `(today − first_release) < MIN_AGE_DAYS` → SUSPICIOUS
- Finding message: `"Package published {N} days ago (threshold: {MIN_AGE_DAYS})"`.

### 6.3 Check 3 — Popularity (`checks/popularity.py`)

| | PyPI | npm |
|---|---|---|
| API | `https://pypistats.org/api/packages/{name}/recent` | `https://api.npmjs.org/downloads/point/last-week/{name}` |
| Field | `data.last_month` | `downloads` |
| Threshold | `PYPI_MIN_DOWNLOADS_MONTH` | `NPM_MIN_DOWNLOADS_WEEK` |
| Verdict | SUSPICIOUS if below threshold | SUSPICIOUS if below threshold |

Finding message: `"Only {N} downloads in the last month/week (threshold: {T})"`.
Network errors produce SUSPICIOUS "could not verify" and are **not cached**.

### 6.4 Check 4 — Typosquatting (`checks/typosquat.py`)

Algorithm:
1. Load `ghostdep/data/top_pypi.txt` or `top_npm.txt` into memory (once, cached in
   a module-level set after first import). Files generated by `scripts/build_top_lists.py`.
2. Normalise the queried name: lowercase, replace hyphens/underscores/dots with `""`.
3. Compute threshold: `MAX_DIST = 1` if `len(normalised_name) <= 5`, else `2`.
4. Use `rapidfuzz.distance.Levenshtein.distance` against all top-list entries
   (normalised the same way). Collect matches where `0 < distance <= MAX_DIST`.
5. If any near-match found **and** the queried name is **not** in the top list:
   - If the queried package is popular (downloads ≥ threshold) **and** old (≥ `MIN_AGE_DAYS`) → SAFE.
   - Otherwise → BLOCKED with `Finding.suggestion = f"Did you mean '{closest_match}'?"`.
6. If no near-match found, or the name is in the top list: no finding.

Top-list files are plain text, one package name per line, sorted by download rank.
Generated by running `python scripts/build_top_lists.py` and committed to the repo.

### 6.5 Check 5 — Vulnerabilities (`checks/vulnerabilities.py`)

- Resolve the version to check: the caller passes the version being installed, or
  the checker resolves "latest" from the registry response before calling this check.
- POST to `https://api.osv.dev/v1/query` — **version is always included**:
  ```json
  {
    "version": "<resolved_version>",
    "package": { "name": "<name>", "ecosystem": "PyPI" }
  }
  ```
- If `vulns` array is non-empty:
  - Collect CVE / GHSA IDs from `vulns[*].id` and `vulns[*].aliases`.
  - BLOCKED if any vuln has severity CRITICAL or HIGH (check both
    `vulns[*].database_specific.severity` and `vulns[*].severity[*].score`).
  - SUSPICIOUS otherwise (known vulns but lower severity).
  - Finding message lists the first 3 vuln IDs and total count.
- If `vulns` is empty → no finding.
- Timeouts / 5xx from OSV → SUSPICIOUS "could not verify vulnerabilities" (not cached).

---

## 7. Cache Layer (`cache.py`)

```python
import diskcache, os, functools, hashlib

_cache = diskcache.Cache(os.path.expanduser(CACHE_DIR))

def cached_get(url: str, ttl: int = CACHE_TTL_SECONDS) -> dict:
    key = hashlib.sha256(url.encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    response = httpx.get(url, timeout=10).json()
    _cache.set(key, response, expire=ttl)
    return response
```

POST requests (OSV) are keyed on `sha256(url + body_json)`.

**Offline mode**: set env var `GHOSTDEP_OFFLINE=1`. When set, `cache.py`
raises `OfflineError` instead of making network calls. Tests and the demo
loader in `offline.py` populate the cache from `fixtures/` before calling
checks, so everything works without a network.

---

## 8. MCP Server (`server.py`)

```python
from mcp.server.fastmcp import FastMCP
from ghostdep.checker import run_checks

mcp = FastMCP("ghostdep")

@mcp.tool()
async def check_package(name: str, ecosystem: str) -> dict:
    """
    Check a package for hallucination, typosquatting, age, popularity,
    and known vulnerabilities.

    Args:
        name: Package name, e.g. "requests"
        ecosystem: "pypi" or "npm"

    Returns:
        Verdict dict with overall (SAFE/SUSPICIOUS/BLOCKED), findings list,
        and optional suggestion.
    """
    verdict = await run_checks(name, ecosystem)
    return verdict.to_dict()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`run_checks` in `checker.py` fans out to all five checks concurrently using
`asyncio.gather`, collects `Finding` objects, then computes the aggregate verdict.
Checks 2–5 are skipped if Check 1 returns BLOCKED.

---

## 9. CLI (`cli.py`)

```
Usage: ghostdep check <name> [OPTIONS]

Options:
  --ecosystem [pypi|npm]   default: pypi
  --format    [text|sarif] default: text
  --offline               Set GHOSTDEP_OFFLINE=1 for this run
```

- `--format text`: coloured table printed to stdout (using `click.style`).
- `--format sarif`: SARIF 2.1.0 JSON printed to stdout (pipe to a file if needed).

Entry point registered in `pyproject.toml`:
```toml
[project.scripts]
ghostdep = "ghostdep.cli:main"
```

---

## 10. SARIF Output (`sarif.py`)

Schema: SARIF 2.1.0 (`https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json`)

Mapping:
| SARIF field | GhostDep value |
|---|---|
| `runs[0].tool.driver.name` | `"ghostdep"` |
| `runs[0].tool.driver.version` | package version from `importlib.metadata` |
| `runs[0].results[*].ruleId` | `Finding.check` (e.g. `"typosquat"`) |
| `runs[0].results[*].level` | BLOCKED → `"error"`, SUSPICIOUS → `"warning"`, SAFE → `"note"` |
| `runs[0].results[*].message.text` | `Finding.message` |
| `runs[0].results[*].locations` | synthetic URI `pkg://{ecosystem}/{name}` |

If no findings exist, a single SAFE result is emitted so GitHub code scanning
shows a clean run rather than an empty file.

---

## 11. Test Plan

### Unit tests (each check in isolation)

Each test file mocks `httpx` via `pytest-httpx` and sets `GHOSTDEP_OFFLINE=1`.

| File | What it tests |
|---|---|
| `test_existence.py` | 200 → SAFE; 404 → BLOCKED finding |
| `test_age.py` | old package → SAFE; package < 30 days old → SUSPICIOUS |
| `test_popularity.py` | high downloads → SAFE; low downloads → SUSPICIOUS |
| `test_typosquat.py` | exact match → SAFE; "reqeusts" → BLOCKED + suggestion |
| `test_vulnerabilities.py` | no vulns → SAFE; critical vuln → BLOCKED; low vuln → SUSPICIOUS |

### Integration tests (`test_checker.py`)

Uses fixtures in `fixtures/` to simulate:
- A fully clean well-known package (e.g. `requests` / `express`).
- A hallucinated package name that returns 404.
- A typosquatted name that matches a top-list entry.

### CLI tests (`test_cli.py`)

Uses `click.testing.CliRunner` to invoke `ghostdep check` with offline fixtures
and asserts exit code + output contains expected strings.

### SARIF tests (`test_sarif.py`)

Assert the output is valid SARIF 2.1.0 JSON (key fields present, correct `level`
mapping, valid `$schema` URI).

---

## 12. Implementation Sequence (suggested order)

1. **Scaffold** — `pyproject.toml`, package skeleton, `constants.py`, `verdict.py`
2. **Cache layer** — `cache.py` + `offline.py`, write `fixtures/` for `requests` and `express`
3. **Check 1** — `existence.py` + `test_existence.py`
4. **Check 2** — `age.py` + `test_age.py`
5. **Check 3** — `popularity.py` + `test_popularity.py`
6. **Check 4** — `typosquat.py` + `test_typosquat.py` + bundle `top_pypi.txt` / `top_npm.txt`
7. **Check 5** — `vulnerabilities.py` + `test_vulnerabilities.py`
8. **Checker orchestrator** — `checker.py` + `test_checker.py`
9. **SARIF emitter** — `sarif.py` + `test_sarif.py`
10. **CLI** — `cli.py` + `test_cli.py`
11. **MCP server** — `server.py`, smoke-test with `mcp dev ghostdep/server.py`
12. **README** — quickstart, MCP config snippet for Claude / Cursor / Copilot

---

## 13. MCP Registration Snippet (for README)

To use GhostDep with an AI coding agent, add to the agent's MCP config:

```json
{
  "mcpServers": {
    "ghostdep": {
      "command": "python",
      "args": ["-m", "ghostdep.server"]
    }
  }
}
```

The agent can then call `check_package` before every `pip install` or
`npm install` command it generates.

---

## 14. Open Questions / Future Work

- **Updating top lists**: a `ghostdep update-lists` subcommand could refresh
  `top_pypi.txt` and `top_npm.txt` from live download stats.
- **Additional ecosystems**: `cargo`, `rubygems`, `maven` follow the same pattern;
  OSV.dev already supports them.
- **GitHub Actions integration**: emit SARIF to `$GITHUB_STEP_SUMMARY` and upload
  via `github/codeql-action/upload-sarif`.
- **Severity weighting**: a scoring system instead of the current first-BLOCKED-wins
  rule, for richer risk tiers.
