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
