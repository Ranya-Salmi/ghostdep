# IBM Bob sessions

Full task histories exported from IBM Bob IDE (Bob → task history → export),
split into one file per task, plus screenshots of each task's summary.

| # | Task | Mode | Date | What Bob did |
|---|---|---|---|---|
| 1 | [Plan and core checks](01-plan-and-core-checks.md) | Plan → Agent | 25–26 Sep | Asked clarifying questions, wrote the implementation plan, then built the scaffold, cache, the five checks and the orchestrator with 61 tests; found and fixed a Python import-binding bug that broke test isolation |
| 2 | [Demo run: Dependency Guardian](02-demo-run-dependency-guardian.md) | Dependency Guardian (custom mode) + GhostDep MCP | 26 Sep | Read the ticket, checked every package through `check_package` in parallel, got BLOCKED for `fastapi-auth-helper-pro` and `reqeusts`, chose a standard-library alternative, removed both packages. Stopped when the Bobcoin budget ran out (status "error") |
| 3 | [SARIF, CLI, MCP server, benchmark, fixes](03-sarif-cli-mcp-benchmark-landing-fixes.md) | Agent | 25–26 Sep | SARIF emitter, CLI, MCP server, first live `check_package` call from Bob, the 75-package benchmark (autonomous, with denied install commands), radar precision fixes, landing page accuracy fixes |
| 4 | [Phases 1–7 and visual redesign](04-phases-1-7-and-visual-redesign.md) | Agent (autonomous) | 26 Sep | Historical-attack replay, `scan` command, CI gate, HTML report, demo project, README accuracy, new-upload scanner, premium report and landing page |

Task 1 also shows status "error" because it was interrupted before Bob marked
it complete; its work was finished and verified (61 tests passing), and
development continued in task 3.

After the budget ran out, the remaining steps of Bob's own plan in task 2 and
later additions were completed manually; see
[`docs/BOB_SETUP.md`](../docs/BOB_SETUP.md).
