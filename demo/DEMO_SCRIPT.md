# GhostDep Demo Script

This script walks through the full demo in ~5 minutes. Record each step in order.

---

## Prerequisites

- GhostDep installed and registered as an MCP server in Bob
- Bob open with the **Dependency Guardian** custom mode active (or the
  `ghostdep-guard` skill enabled)
- Terminal open at the repo root (`d:/ghostdep`)

---

## Step 1 — Run `ghostdep scan` on the bad requirements file

```bash
ghostdep scan demo/weather-api/requirements.txt
```

Expected output:

```
GhostDep Scan Summary
  Package                             Verdict      Reasons
  ──────────────────────────────────────────────────────────────────────────
  requests                            SAFE
  reqeusts                            BLOCKED      'reqeusts' closely resembles 'requests'
                                         → Did you mean 'requests'?
  fastapi-auth-helper-pro             BLOCKED      existence:BLOCKED (404)
  python-dateutil                     SAFE
  ──────────────────────────────────────────────────────────────────────────
  4 packages checked: 2 SAFE  0 SUSPICIOUS  2 BLOCKED
```

The exit code is **2** (BLOCKED packages found).

---

## Step 2 — Open the HTML report

```bash
ghostdep report demo/weather-api/requirements.txt --output demo/report-example.html
```

Open `demo/report-example.html` in a browser. Point out:

- BLOCKED packages appear at the top with ghost styling (struck-through name).
- The "Use instead" box for `reqeusts` shows the correct spelling `requests`.
- `fastapi-auth-helper-pro` is BLOCKED because it does not exist on PyPI.

---

## Step 3 — Switch Bob to Dependency Guardian mode

In Bob, change the mode (top-right corner) to **Dependency Guardian**, or enable
the `ghostdep-guard` skill.

Open `demo/weather-api/TASK.md` and give Bob this prompt:

> Please complete the task described in TASK.md.

---

## Step 4 — Show Bob being blocked

Bob will read TASK.md, see the recommendation for `fastapi-auth-helper-pro`, and
call `check_package` via the GhostDep MCP tool before installing.

GhostDep returns **BLOCKED**:

```
BLOCKED  fastapi-auth-helper-pro
  · package does not exist on PyPI
```

Bob refuses to install the non-existent package and instead:

1. Notes that `fastapi-auth-helper-pro` does not exist.
2. Chooses a safe, real alternative — for example, implementing the API-key check
   directly with the standard library (`http.server` + `os.environ`), or using
   a well-known package like `starlette` if the project allows third-party deps.
3. Completes the task by implementing the auth check with the chosen approach.
4. All tests pass.

---

## What to highlight in the recording

- The typo `reqeusts` is caught before `pip install` runs — zero damage.
- The hallucinated package `fastapi-auth-helper-pro` is caught the same way.
- Bob adapts autonomously: it does not get stuck, it just picks a real solution.
- The HTML report is a clean, shareable artefact showing exactly what was found.
