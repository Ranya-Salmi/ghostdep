"""Offline fixture loader.

Call ``load_fixtures()`` at the start of a test session (or demo run) to
populate the disk cache from the JSON files under ``fixtures/``.  After that
every check will hit the cache instead of the network, even with
GHOSTDEP_OFFLINE=1.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ghostdep.cache import prime_cache
from ghostdep.constants import (
    NPM_DOWNLOADS_URL,
    NPM_REGISTRY_URL,
    OSV_API_URL,
    PYPI_JSON_URL,
    PYPISTATS_RECENT_URL,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def load_fixtures() -> None:
    """Prime the cache from every fixture file found under fixtures/."""
    for ecosystem_dir in FIXTURES_DIR.iterdir():
        if not ecosystem_dir.is_dir():
            continue
        ecosystem = ecosystem_dir.name  # "pypi" or "npm"
        for fixture_file in ecosystem_dir.glob("*.json"):
            name = fixture_file.stem
            data = _load(fixture_file)
            _prime_for(name, ecosystem, data)


def _prime_for(name: str, ecosystem: str, data: dict) -> None:
    """Insert all relevant cache keys for a single package fixture."""
    if ecosystem == "pypi":
        prime_cache(PYPI_JSON_URL.format(name=name), data.get("registry"))
        if "pypistats" in data:
            prime_cache(PYPISTATS_RECENT_URL.format(name=name), data["pypistats"])
    elif ecosystem == "npm":
        prime_cache(NPM_REGISTRY_URL.format(name=name), data.get("registry"))
        if "downloads" in data:
            prime_cache(NPM_DOWNLOADS_URL.format(name=name), data["downloads"])

    # OSV fixtures are keyed on the POST body
    if "osv" in data:
        for version, osv_resp in data["osv"].items():
            ecosystem_osv = "PyPI" if ecosystem == "pypi" else "npm"
            body = {
                "version": version,
                "package": {"name": name, "ecosystem": ecosystem_osv},
            }
            import json as _json

            body_json = _json.dumps(body, sort_keys=True)
            prime_cache(OSV_API_URL + body_json, osv_resp)
