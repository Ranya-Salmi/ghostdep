"""Minimal weather-API demo app.

Serves a single endpoint, protected by an API key:
    GET /weather   (header: X-Api-Key: <key>)
        ->  {"city": "London", "temp_c": 12, "condition": "cloudy", ...}

Valid keys are read from the API_KEYS environment variable (comma-separated).
For local development they can also be placed in a .env file next to this
script:  API_KEYS=dev-key-1,dev-key-2

Run with:
    set API_KEYS=my-secret-key      (PowerShell: $env:API_KEYS="my-secret-key")
    python app.py                   # listens on http://localhost:8000
    python app.py --port 9000

Implemented with the Python standard library only. The ticket suggested the
package `fastapi-auth-helper-pro`, but GhostDep reported it BLOCKED (it does not
exist on PyPI), so no third-party dependency is used.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

API_KEY_HEADER = "X-Api-Key"
API_KEYS_ENV = "API_KEYS"
_ENV_FILE = Path(__file__).with_name(".env")

_WEATHER_DATA = {
    "city": "London",
    "temp_c": 12,
    "condition": "cloudy",
    "humidity_pct": 78,
}


def _load_dotenv(path: Path = _ENV_FILE) -> None:
    """Load KEY=VALUE lines from a .env file without overriding real env vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_valid_keys() -> list[str]:
    """Return the configured API keys (read at request time)."""
    raw = os.environ.get(API_KEYS_ENV, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def is_authorized(provided: str | None) -> bool:
    """Check a provided key against the configured keys.

    Fails closed: if no keys are configured, every request is rejected.
    Uses hmac.compare_digest to avoid timing attacks.
    """
    if not provided:
        return False
    return any(
        hmac.compare_digest(provided.encode(), key.encode())
        for key in get_valid_keys()
    )


class WeatherHandler(BaseHTTPRequestHandler):
    """Handle GET /weather requests."""

    def log_message(self, fmt, *args):  # type: ignore[override]
        # Suppress the default access log to keep demo output clean
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/weather":
            self.send_response(404)
            self.end_headers()
            return

        if not is_authorized(self.headers.get(API_KEY_HEADER)):
            self._send_json(
                401,
                {"error": "unauthorized",
                 "detail": f"Missing or invalid {API_KEY_HEADER} header."},
            )
            return

        self._send_json(200, _WEATHER_DATA)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    _load_dotenv()
    if not get_valid_keys():
        print(f"Warning: {API_KEYS_ENV} is not set; every request will get 401.")
    server = HTTPServer((host, port), WeatherHandler)
    print(f"Serving at http://{host}:{port}/weather  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weather API demo server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(args.host, args.port)
