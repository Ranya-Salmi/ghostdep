"""Disk-backed cache for HTTP responses.

Usage
-----
from ghostdep.cache import cached_get, cached_post, OfflineError

Set GHOSTDEP_OFFLINE=1 to disable all network calls.  Checks that handle
network errors gracefully can catch httpx exceptions independently; the cache
layer itself only raises OfflineError when offline mode is active.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import diskcache
import httpx

import ghostdep.constants as _constants

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OfflineError(RuntimeError):
    """Raised when a network call is attempted while GHOSTDEP_OFFLINE=1."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_cache: diskcache.Cache | None = None


def _get_cache() -> diskcache.Cache:
    global _cache
    if _cache is None:
        # Read CACHE_DIR via module reference so monkeypatch works in tests
        path = os.path.expanduser(_constants.CACHE_DIR)
        _cache = diskcache.Cache(path)
    return _cache


def _is_offline() -> bool:
    return os.environ.get("GHOSTDEP_OFFLINE", "").strip() in {"1", "true", "yes"}


def _key(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cached_get(url: str, ttl: int = 0) -> Any:
    """GET *url* and return parsed JSON.  Results are cached to disk.

    Raises OfflineError if GHOSTDEP_OFFLINE=1 and the key is not in cache.
    Raises httpx.HTTPStatusError / httpx.TimeoutException on network errors
    (these are NOT cached so callers can produce "could not verify" findings).
    """
    if ttl <= 0:
        ttl = _constants.CACHE_TTL_SECONDS
    cache = _get_cache()
    key = _key(url)
    if key in cache:
        return cache[key]

    if _is_offline():
        raise OfflineError(f"Offline mode: no cached response for {url}")

    resp = httpx.get(url, timeout=10, follow_redirects=True)

    # 404 -> caller handles; other 4xx/5xx -> do NOT cache
    if resp.status_code == 404:
        # cache the 404 so repeated misses are fast
        cache.set(key, None, expire=ttl)
        return None

    if resp.status_code != 200:
        resp.raise_for_status()  # propagates as HTTPStatusError (not cached)

    data = resp.json()
    cache.set(key, data, expire=ttl)
    return data


def cached_post(url: str, body: dict, ttl: int = 0) -> Any:
    """POST *body* to *url* and return parsed JSON.  Results are cached.

    Network errors (timeout, 5xx) are NOT cached; callers handle them.
    """
    if ttl <= 0:
        ttl = _constants.CACHE_TTL_SECONDS
    body_json = json.dumps(body, sort_keys=True)
    cache = _get_cache()
    key = _key(url + body_json)
    if key in cache:
        return cache[key]

    if _is_offline():
        raise OfflineError(f"Offline mode: no cached response for POST {url}")

    resp = httpx.post(url, json=body, timeout=10)

    if resp.status_code != 200:
        resp.raise_for_status()

    data = resp.json()
    cache.set(key, data, expire=ttl)
    return data


def prime_cache(key_data: str, value: Any) -> None:
    """Manually insert a value into the cache (used by offline.py / fixtures)."""
    _get_cache().set(_key(key_data), value)


def clear_cache() -> None:
    """Evict all entries.  Used in tests."""
    _get_cache().clear()
