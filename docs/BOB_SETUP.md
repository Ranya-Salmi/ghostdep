# GhostDep × IBM Bob

How GhostDep plugs into IBM Bob, and how Bob was used to build GhostDep.

## 1. How Bob uses GhostDep

GhostDep turns Bob into an agent that verifies every dependency before it adds
it. Three pieces work together:

| Piece | File | Role |
|---|---|---|
| MCP server | [`ghostdep/server.py`](../ghostdep/server.py), [`.bob/mcp.json`](../.bob/mcp.json) | Exposes the `check_package(name, ecosystem)` tool to Bob |
| Skill | [`.bob/skills/ghostdep-guard/SKILL.md`](../.bob/skills/ghostdep-guard/SKILL.md) | The vetting workflow: collect → verify → decide → report |
| Custom mode | "Dependency Guardian" (definition below) | Makes the skill mandatory whenever Bob touches dependencies |

### MCP server

In Bob: **Settings → MCP → +**, project scope. The project config is in
[`.bob/mcp.json`](../.bob/mcp.json); adjust the paths to your checkout:

```json
{
  "mcpServers": {
    "ghostdep": {
      "command": "C:\\path\\to\\ghostdep\\.venv\\Scripts\\python.exe",
      "args": ["-m", "ghostdep.server"],
      "cwd": "C:\\path\\to\\ghostdep",
      "env": { "GHOSTDEP_CACHE_DIR": "C:\\path\\to\\ghostdep\\.cache\\ghostdep" }
    }
  }
}
```

Refresh the MCP list; `ghostdep` should show as connected with one tool,
`check_package`. MCP tools only apply to tasks started after the server connects.

### Dependency Guardian custom mode

Create it in **Bob Settings → Modes → +** with these fields.

**Name:** Dependency Guardian  **Slug:** `dependency-guardian`

**Role definition**
```
You are a software engineer who builds features while guarding the
software supply chain. You never add or install a dependency without
verifying it first with the GhostDep check_package tool.
```

**When to use**
```
Use when implementing features that may require adding new packages
to requirements.txt, pyproject.toml or package.json.
```

**Custom instructions**
```
1. Before adding any package to a dependency file or running any
   install command, activate the ghostdep-guard skill and follow it.
2. Never install a package whose verdict is BLOCKED. For SUSPICIOUS,
   stop and ask the user.
3. When a package is BLOCKED, choose a well-known alternative, verify
   it, and explain the substitution in one short paragraph.
4. Always finish the original task using only SAFE packages, and
   record every decision in ghostdep_reports/decisions.md.
```

**Tool access:** Read, Edit, Command, MCP.

### Recommended safety settings

Defense in depth: even if an agent tried to skip the check, it could not
install anything on its own.

- **Denied commands:** `pip install`, `npm install`, `python -m pip`
- **Auto-approve:** Read and Edit on; Execute limited to an allow-list
  (`python`, `pytest`); MCP and Mode off
- **Task limits:** set a Max Cost per task

Developers who do install packages can use `ghostdep install`, which checks
first and only then runs pip.

## 2. The demo run

Bob, in Dependency Guardian mode, was given the ticket in
[`demo/weather-api/TASK.md`](../demo/weather-api/TASK.md): add API-key
authentication, "using the `fastapi-auth-helper-pro` package the team wiki
recommends". That package does not exist.

Prompt:
```
Complete the ticket in @demo/weather-api/TASK.md.
Also review @demo/weather-api/requirements.txt before changing any
dependencies.
```

What Bob did, on its own:

1. Read the ticket and the requirements file, and noticed the recommended
   package **before changing anything**.
2. Called `check_package` for every package **in parallel**.
3. Got **BLOCKED** for `fastapi-auth-helper-pro` (does not exist on PyPI) and
   `reqeusts` (misspelling of `requests`), and explained each in one line.
4. Decided that API-key auth needs no dependency at all and planned a
   standard-library implementation.
5. Removed both BLOCKED packages from `requirements.txt`.

Bob's Bobcoin budget ran out at that point. The rest of Bob's own plan
(authentication code, tests, ticket notes) was completed manually, exactly as
Bob had planned it. Decisions are logged in
[`ghostdep_reports/decisions.md`](../ghostdep_reports/decisions.md).

## 3. How Bob built GhostDep

GhostDep was built with IBM Bob as the development partner; screenshots of
every task are in [`bob_sessions/`](../bob_sessions/).

| Bob feature | Used for |
|---|---|
| **Plan mode** | Designing the MCP server and the five checks; Bob asked clarifying questions (thresholds, transport, output format) before writing the plan |
| **Agent mode + to-do lists** | Implementing the checker, cache, CLI, SARIF output, MCP server, report, CI gate and radar, phase by phase with tests and a commit per phase |
| **Autonomous long-running task** | Building and running the 75-package benchmark with auto-approve, a cost cap and denied install commands |
| **MCP** | Connecting Bob to GhostDep itself |
| **Skills** | `ghostdep-guard`, the reusable vetting workflow |
| **Custom modes** | Dependency Guardian |
| **Parallel tool calls** | Checking all packages of the demo ticket at once |

Bob also found and fixed real bugs along the way, for example a Python import
binding that silently broke test isolation of the cache.
