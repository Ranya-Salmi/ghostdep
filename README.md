# GhostDep

> **Security guard that stops AI coding agents from installing hallucinated, typosquatted, or vulnerable packages.**

GhostDep checks every package name before it gets installed.  It runs five deterministic checks — existence, age, popularity, typosquatting, and known CVEs — and returns a structured **SAFE / SUSPICIOUS / BLOCKED** verdict.  Results are cached to disk so repeated queries are instant.

---

## Checks

| # | Check | Verdict on failure |
|---|---|---|
| 1 | **Existence** — package found in PyPI / npm registry | BLOCKED (404) or SUSPICIOUS (network error) |
| 2 | **Age** — first release ≥ 30 days ago | SUSPICIOUS |
| 3 | **Popularity** — download count above threshold | SUSPICIOUS |
| 4 | **Typosquatting** — OSA edit-distance against top-5,000 PyPI / top-1,000 npm list | BLOCKED |
| 5 | **Vulnerabilities** — OSV.dev CVE query | BLOCKED (critical/high) or SUSPICIOUS |

---

## Quickstart

```bash
# Install (requires Python ≥ 3.11)
pip install -e ".[dev]"

# Check a single PyPI package
ghostdep check requests

# Check an npm package
ghostdep check express --ecosystem npm

# Get SARIF output (pipe to a file for GitHub code-scanning upload)
ghostdep check requests --format sarif > results.sarif

# Offline mode (uses disk cache / fixtures, no network)
ghostdep check requests --offline
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | SAFE |
| `1` | SUSPICIOUS |
| `2` | BLOCKED |

---

## Scan command

Scan an entire `requirements.txt` or `pyproject.toml` in one go:

```bash
ghostdep scan requirements.txt
ghostdep scan pyproject.toml

# Output as SARIF (pipe to GitHub code-scanning)
ghostdep scan requirements.txt --format sarif > ghostdep.sarif
```

Exit code is `2` if any package is BLOCKED, `1` if any are SUSPICIOUS, `0` if all SAFE.

---

## Report command

Generate a self-contained HTML report from a dependency file:

```bash
ghostdep report requirements.txt --output report.html
```

The HTML file is fully self-contained (inline CSS, no external assets) and can be shared directly.  See [`demo/report-example.html`](demo/report-example.html) for an example.

---

## Safe install command

`ghostdep install` is a drop-in replacement for `pip install` (or `npm install`
with `--ecosystem npm`). It checks every package first:

| Verdict | What happens |
|---|---|
| BLOCKED | Nothing is installed, not even the safe packages in the same command (exit 2) |
| SUSPICIOUS | You are asked to confirm (`--yes` to skip the prompt) |
| SAFE | Runs `pip install` with your exact arguments, version pins included |

```bash
ghostdep install requests "python-dateutil>=2.9"
ghostdep install fastapi-auth-helper-pro      # BLOCKED: nothing installed
ghostdep install requests --dry-run           # check only, print the command
```

## Team policy (allow and deny lists)

Private packages don't exist on public registries, so GhostDep would block them.
Add a `.ghostdep.toml` at the root of your project (GhostDep searches the current
directory and its parents, or set `GHOSTDEP_POLICY` to a path):

```toml
[policy]
allow = ["acme-internal-auth", "acme-billing-client"]  # internal packages
deny  = ["pycrypto"]                                   # never install
```

Allowed packages skip the registry checks; denied packages are always BLOCKED
(deny wins over allow). The policy applies to `check`, `scan`, `report`,
`install` and the MCP server used by IBM Bob.

## Pre-commit hook

Block risky dependencies before they are committed. In your project's
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Ranya-Salmi/ghostdep
    rev: main
    hooks:
      - id: ghostdep-scan
```

The hook runs `ghostdep scan` on any changed `requirements*.txt` or
`pyproject.toml` and fails the commit if a package is BLOCKED or SUSPICIOUS.

## MCP Server (IBM Bob / Claude / Cursor / Copilot)

> Full Bob integration guide (MCP, skill, Dependency Guardian mode, safety settings) and how Bob was used to build GhostDep: [`docs/BOB_SETUP.md`](docs/BOB_SETUP.md)

GhostDep ships an [MCP](https://modelcontextprotocol.io) server that exposes a single tool:

```
check_package(name: str, ecosystem: str) -> dict
```

### IBM Bob configuration

Add via **Bob Settings → MCP → +** (project scope) and paste the following JSON:

```json
{
  "mcpServers": {
    "ghostdep": {
      "command": "C:\\path\\to\\ghostdep\\.venv\\Scripts\\python.exe",
      "args": ["-m", "ghostdep.server"],
      "cwd": "C:\\path\\to\\ghostdep"
    }
  }
}
```

Replace `C:\\path\\to\\ghostdep` with the absolute path to the cloned repository root.

> **Tip — find the right python path:**
> ```powershell
> (Get-Command python).Path   # or: .\.venv\Scripts\python.exe --version
> ```

### Enabling automatic checks in Bob

Registering the MCP server alone does **not** make Bob call `check_package` automatically.  To enable automatic checks, use one of these approaches:

**Option A — Dependency Guardian mode**  
A custom Bob mode that instructs the agent to always verify packages before installing.  To activate: change the mode (top-right corner in Bob) to **Dependency Guardian**.

**Option B — `ghostdep-guard` skill**  
A Bob skill that adds a package-vetting rule to any mode.  To enable: go to Bob Settings → Skills and activate `ghostdep-guard`.

With either option active, Bob will call `check_package` before suggesting any `pip install` or `npm install` command and will refuse to proceed if the verdict is BLOCKED.

---

## CI Gate (GitHub Actions)

Add automatic scanning on every pull request that changes `requirements.txt` or `pyproject.toml`:

```yaml
# .github/workflows/ghostdep.yml  (already included in this repo)
on:
  pull_request:
    paths: ["requirements.txt", "pyproject.toml"]
```

The workflow runs `ghostdep scan --format sarif`, uploads the SARIF to the GitHub Security tab, and fails the job if any package is BLOCKED.  See [`.github/workflows/ghostdep.yml`](.github/workflows/ghostdep.yml) for the full configuration.

---

## Radar (live PyPI monitoring)

Every 30 minutes, a scheduled GitHub Action ([`radar.yml`](.github/workflows/radar.yml))
reads PyPI's feed of newly created packages, checks each name it hasn't seen before
against the 1,000 most-downloaded packages, and records possible lookalikes.

- Live view: the **Radar** section of the [landing page](https://ranya-salmi.github.io/ghostdep/#radar)
- Raw data: [`radar/history.jsonl`](radar/history.jsonl) (one record per sweep) and
  [`radar/log.txt`](radar/log.txt) (human-readable)
- Run a sweep locally: `python scripts/radar_update.py`

Lookalikes are possible impersonations, not proof of malice; each one needs review.

## Benchmark results

| Metric | Result |
|---|---|
| Detection rate (typosquats + hallucinated names) | **30/30 (100%)** |
| False-positive rate (popular + mid-popularity packages) | **0/45 (0%)** |
| Historical attack replay (colourama, python3-dateutil, jeIlyfish) | **3/3 (100%)** |
| Date | 2026-09-26 |

Full methodology and per-package results: [`benchmark/RESULTS.md`](benchmark/RESULTS.md).

---

## Demo

See [`demo/DEMO_SCRIPT.md`](demo/DEMO_SCRIPT.md) for step-by-step instructions.
The demo uses the project in [`demo/weather-api/`](demo/weather-api/), which has a "bad PR" requirements file containing a typo (`reqeusts`) and a hallucinated package (`fastapi-auth-helper-pro`).

---

## Running tests

```bash
pytest
```

All tests run offline (network calls are mocked).

---

## Refreshing the top-package lists

The bundled `ghostdep/data/top_pypi.txt` (top-5,000 PyPI packages) and
`ghostdep/data/top_npm.txt` (top-1,000 npm packages) are checked against for typosquatting.  To regenerate them from live download statistics:

```bash
python scripts/build_top_lists.py
```

Commit the updated files to keep the typosquatting check current.

---

## Project structure

```
ghostdep/
├── ghostdep/
│   ├── server.py          ← MCP server (stdio transport)
│   ├── cli.py             ← `ghostdep check` / `scan` / `report` CLI
│   ├── checker.py         ← orchestrates all checks
│   ├── sarif.py           ← SARIF 2.1.0 emitter
│   ├── report.py          ← HTML report generator
│   ├── verdict.py         ← Verdict / Finding dataclasses
│   ├── cache.py           ← disk cache (SQLite via diskcache)
│   ├── checks/            ← individual check modules
│   └── data/              ← bundled top-package lists
├── benchmark/             ← accuracy benchmark scripts and results
├── demo/                  ← demo project and scripts
├── fixtures/              ← saved API responses for offline mode
├── tests/                 ← pytest suite
└── scripts/               ← helper scripts
```

---

## License

MIT
