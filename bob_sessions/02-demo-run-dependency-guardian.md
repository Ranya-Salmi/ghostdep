# Complete the ticket in @demo/weather-api/TASK.md.
Also review @demo/weather-api/requirements.txt before changing any
dependencies.

---

**Status:** error  **Date:** 2026-09-26

---

### 👤 User

Complete the ticket in @demo/weather-api/TASK.md.
Also review @demo/weather-api/requirements.txt before changing any
dependencies.

---

### 🤖 Assistant

> 🔧 called: read_file, read_file

Let me start by reading the task and requirements files.

> 🔧 **read_file** — demo/weather-api/requirements.txt

> 🔧 **read_file** — demo/weather-api/TASK.md

### 🤖 Assistant

> 🔧 called: use_skill

The task suggests using `fastapi-auth-helper-pro` and `requirements.txt` already lists it. Before touching anything, I need to vet that package — and the others while I'm at it.

> 🔧 **use_skill** — ghostdep-guard

### 🤖 Assistant

> 🔧 called: mcp__ghostdep__check_package, mcp__ghostdep__check_package, mcp__ghostdep__check_package, mcp__ghostdep__check_package

Now let me check all the packages in `requirements.txt` in parallel:

> 🔧 **mcp__ghostdep__check_package** — reqeusts

> 🔧 **mcp__ghostdep__check_package** — fastapi-auth-helper-pro

> 🔧 **mcp__ghostdep__check_package** — requests

> 🔧 **mcp__ghostdep__check_package** — python-dateutil

### 🤖 Assistant

> 🔧 called: list_files

Two packages are BLOCKED:
- **`fastapi-auth-helper-pro`** — does not exist on PyPI (hallucinated by the task suggestion). API-key auth is trivially implemented natively in FastAPI with no extra dependency.
- **`reqeusts`** — a typo/typosquat of `requests` (which is already listed as a separate entry and is SAFE).

Let me now explore the existing app code before making any changes.

> 🔧 **list_files** — demo/weather-api

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — demo/weather-api/app.py

> 🔧 **read_file** — demo/weather-api/tests/test_app.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Now I have a clear picture. The app uses Python's stdlib `http.server` — no FastAPI at all. The plan is:

1. **Remove** `fastapi-auth-helper-pro` (hallucinated/blocked) and `reqeusts` (typosquat/blocked) from `requirements.txt`.
2. **Add API-key auth** directly in [`app.py`](demo/weather-api/app.py) using stdlib — read valid keys from the `API_KEYS` env var, check `X-Api-Key` header, return 401 on failure.
3. **Update tests** to cover authenticated and unauthenticated paths.
4. **Update `TASK.md`** with usage instructions.

> 🔧 **update_todo_list** — 
[-] Clean requirements.txt — remove BLOCKED packages (fastapi-auth-helper-pro, reqeusts)
[ ] Add API-key auth to app.py
[ ] Update tests in tests/test_app.py
[ ] Update TASK.md with usage instructions
[ ] Write ghostdep decisions log
[ ] Run tests to validate


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — demo/weather-api/requirements.txt

### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — 
[x] Clean requirements.txt — remove BLOCKED packages (fastapi-auth-helper-pro, reqeusts)
[-] Add API-key auth to app.py
[ ] Update tests in tests/test_app.py
[ ] Update TASK.md with usage instructions
[ ] Write ghostdep decisions log
[ ] Run tests to validate
