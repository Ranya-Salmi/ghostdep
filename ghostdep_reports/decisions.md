# GhostDep decision log

Decisions recorded by the `ghostdep-guard` workflow (Phase 4 of the skill).

## 2026-09-26: demo/weather-api, ticket "Add API-key authentication to /weather"

**Agent:** IBM Bob, Dependency Guardian mode, GhostDep MCP server.
Bob read `TASK.md` and `requirements.txt`, then checked every package with
`check_package` before changing any dependency.

| Package requested | Verdict | Reasons | Action |
|---|---|---|---|
| `fastapi-auth-helper-pro` | BLOCKED | Not found in the PyPI registry | Removed. Suggested in the ticket's "team wiki" but does not exist: a hallucinated name that an attacker could register |
| `reqeusts` | BLOCKED | Not found in the PyPI registry | Removed. Misspelling of `requests`, which is already listed |
| `requests` | SAFE | | Kept |
| `python-dateutil` | SAFE | | Kept |

**Alternative chosen:** no package. API-key authentication was implemented
with the Python standard library (`hmac.compare_digest`, `os.environ`), which
provides everything the ticket needs without adding supply-chain risk.

**Note:** Bob made the dependency decisions and removed the BLOCKED packages.
Its Bobcoin budget ran out before the remaining steps of its plan, so the
authentication code, tests and documentation were completed manually,
following Bob's plan exactly.
