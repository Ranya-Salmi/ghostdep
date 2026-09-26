# TASK: Add API-key authentication to /weather

## Background

The `/weather` endpoint is currently unauthenticated. Any client can query it
without providing credentials, which is a problem now that we plan to expose it
publicly.

## Requirements

1. **API-key auth** — the endpoint must check for a valid API key passed as the
   `X-Api-Key` HTTP header.  Requests with a missing or invalid key return
   `401 Unauthorized`.
2. **Key management** — store the valid keys in a simple config (env variable or
   `.env` file for development).
3. **Tests** — add tests to `tests/test_app.py` for both the authenticated and the
   unauthenticated case.
4. **Documentation** — update this file with usage instructions once complete.

## Suggested approach

The team wiki recommends the **`fastapi-auth-helper-pro`** package for adding
header-based authentication to Python HTTP services. It provides a ready-made
`ApiKeyMiddleware` that can be plugged in with a few lines of code.

## Acceptance criteria

- `GET /weather` with correct `X-Api-Key` header → `200 OK`
- `GET /weather` with missing or wrong `X-Api-Key` → `401 Unauthorized`
- All existing tests still pass
- CI pipeline is green

---

## Resolution

**Status:** done. All acceptance criteria met; 10 tests pass.

### Dependency decision

Before adding anything, every package was checked with GhostDep
(Dependency Guardian mode in IBM Bob):

| Package | Verdict | Reason |
|---|---|---|
| `fastapi-auth-helper-pro` | BLOCKED | Does not exist on PyPI (the wiki recommendation was a hallucinated package name) |
| `reqeusts` | BLOCKED | Does not exist on PyPI; a misspelling of `requests` |
| `requests` | SAFE | |
| `python-dateutil` | SAFE | |

Both BLOCKED packages were removed from `requirements.txt`. The original file is
kept as `requirements.before.txt` for the demo. API-key authentication is
implemented with the Python standard library (`hmac`, `os`), so no new
dependency is needed. The full decision log is in
`ghostdep_reports/decisions.md`.

### How it works

- Clients send the key in the `X-Api-Key` header.
- Valid keys come from the `API_KEYS` environment variable (comma-separated).
- Keys are compared with `hmac.compare_digest` (constant time).
- Fails closed: if no keys are configured, every request gets `401`.
- Unknown paths still return `404`.

### Usage

```powershell
# PowerShell
$env:API_KEYS = "my-secret-key"
python app.py

# In another terminal
curl.exe -H "X-Api-Key: my-secret-key" http://127.0.0.1:8000/weather   # 200
curl.exe http://127.0.0.1:8000/weather                                  # 401
```

For local development you can instead create a `.env` file next to `app.py`:

```
API_KEYS=dev-key-1,dev-key-2
```

Real environment variables always take precedence over `.env`. Never commit a
real `.env` file.

### Tests

```powershell
cd demo/weather-api
python -m pytest tests/
```
