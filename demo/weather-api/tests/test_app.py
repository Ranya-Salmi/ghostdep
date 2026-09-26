"""Tests for the demo weather-api app."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

from app import WeatherHandler, _load_dotenv

VALID_KEY = "test-key-123"


@pytest.fixture
def server(monkeypatch):
    """Start the app on a free port with one valid key configured."""
    monkeypatch.setenv("API_KEYS", f"{VALID_KEY}, second-key")
    srv = HTTPServer(("127.0.0.1", 0), WeatherHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url: str, key: str | None = None):
    req = urllib.request.Request(url)
    if key is not None:
        req.add_header("X-Api-Key", key)
    return urllib.request.urlopen(req)


def _status(url: str, key: str | None = None) -> int:
    try:
        with _get(url, key) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


# --- authenticated -----------------------------------------------------------

def test_valid_key_returns_200(server):
    assert _status(f"{server}/weather", VALID_KEY) == 200


def test_valid_key_returns_weather_json(server):
    with _get(f"{server}/weather", VALID_KEY) as resp:
        data = json.loads(resp.read())
    assert {"city", "temp_c", "condition"} <= data.keys()


def test_any_configured_key_is_accepted(server):
    assert _status(f"{server}/weather", "second-key") == 200


# --- unauthenticated ---------------------------------------------------------

def test_missing_key_returns_401(server):
    assert _status(f"{server}/weather") == 401


def test_wrong_key_returns_401(server):
    assert _status(f"{server}/weather", "not-a-real-key") == 401


def test_401_body_explains_error(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(f"{server}/weather", "wrong")
    body = json.loads(exc.value.read())
    assert body["error"] == "unauthorized"


def test_no_keys_configured_fails_closed(server, monkeypatch):
    monkeypatch.setenv("API_KEYS", "")
    assert _status(f"{server}/weather", VALID_KEY) == 401


# --- routing -----------------------------------------------------------------

def test_unknown_path_returns_404(server):
    assert _status(f"{server}/unknown", VALID_KEY) == 404


# --- .env loading ------------------------------------------------------------

def test_dotenv_does_not_override_real_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEYS=from-file\n# comment\n", encoding="utf-8")
    monkeypatch.setenv("API_KEYS", "from-env")
    _load_dotenv(env_file)
    import os
    assert os.environ["API_KEYS"] == "from-env"


def test_dotenv_sets_missing_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('API_KEYS="from-file"\n', encoding="utf-8")
    monkeypatch.delenv("API_KEYS", raising=False)
    _load_dotenv(env_file)
    import os
    assert os.environ["API_KEYS"] == "from-file"
