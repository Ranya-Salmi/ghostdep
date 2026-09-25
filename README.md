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
| 4 | **Typosquatting** — OSA edit-distance against top-5 000 list | BLOCKED |
| 5 | **Vulnerabilities** — OSV.dev CVE query | BLOCKED (critical/high) or SUSPICIOUS |

---

## Quickstart

```bash
# Install (requires Python ≥ 3.11)
pip install -e ".[dev]"

# Check a PyPI package
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

## MCP Server (IBM Bob / Claude / Cursor / Copilot)

GhostDep ships an [MCP](https://modelcontextprotocol.io) server that exposes a single tool:

```
check_package(name: str, ecosystem: str) -> dict
```

### IBM Bob configuration

Add the following to your Bob MCP settings file
(`%APPDATA%\Bob\mcp_settings.json` on Windows):

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

Once registered, Bob will automatically call `check_package` before suggesting any `pip install` or `npm install` command.

---

## Running tests

```bash
pytest
```

All tests run offline (network calls are mocked via `pytest-httpx`).

---

## Refreshing the top-package lists

The bundled `ghostdep/data/top_pypi.txt` and `ghostdep/data/top_npm.txt` files
contain the top-5 000 packages by download count.  To regenerate them from live
download statistics:

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
│   ├── cli.py             ← `ghostdep check` CLI
│   ├── checker.py         ← orchestrates all checks
│   ├── sarif.py           ← SARIF 2.1.0 emitter
│   ├── verdict.py         ← Verdict / Finding dataclasses
│   ├── cache.py           ← disk cache (SQLite via diskcache)
│   ├── checks/            ← individual check modules
│   └── data/              ← bundled top-package lists
├── fixtures/              ← saved API responses for offline mode
├── tests/                 ← pytest suite
└── scripts/               ← build_top_lists.py helper
```

---

## License

MIT
