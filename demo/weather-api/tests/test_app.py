"""Tests for the demo weather-api app."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import HTTPServer

from app import WeatherHandler


def _start_server(port: int = 18765) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), WeatherHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def test_weather_endpoint_returns_200():
    server = _start_server(18765)
    try:
        with urllib.request.urlopen("http://127.0.0.1:18765/weather") as resp:
            assert resp.status == 200
    finally:
        server.shutdown()


def test_weather_endpoint_returns_json():
    server = _start_server(18766)
    try:
        with urllib.request.urlopen("http://127.0.0.1:18766/weather") as resp:
            data = json.loads(resp.read())
        assert "city" in data
        assert "temp_c" in data
        assert "condition" in data
    finally:
        server.shutdown()


def test_unknown_path_returns_404():
    server = _start_server(18767)
    try:
        import urllib.error
        try:
            urllib.request.urlopen("http://127.0.0.1:18767/unknown")
            assert False, "Expected 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
