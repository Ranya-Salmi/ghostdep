"""Shared pytest fixtures."""
from __future__ import annotations

import pytest
import ghostdep.cache as cache_mod
import ghostdep.constants as const_mod


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Give every test its own empty cache directory and a fresh cache instance."""
    monkeypatch.setenv("GHOSTDEP_OFFLINE", "0")
    cache_dir = str(tmp_path / "ghostdep_cache")
    # Patch the constant so the lazy initialiser picks up the per-test dir
    monkeypatch.setattr(const_mod, "CACHE_DIR", cache_dir)
    # Close and discard the existing cache instance (if any)
    if cache_mod._cache is not None:
        try:
            cache_mod._cache.close()
        except Exception:
            pass
    cache_mod._cache = None
    yield
    # Teardown: close and discard
    if cache_mod._cache is not None:
        try:
            cache_mod._cache.close()
        except Exception:
            pass
    cache_mod._cache = None
