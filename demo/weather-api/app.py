"""Minimal weather-API demo app.

Serves a single endpoint:
    GET /weather  →  {"city": "London", "temp_c": 12, "condition": "cloudy"}

Run with:
    python app.py          # listens on http://localhost:8000
    python app.py --port 9000
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


_WEATHER_DATA = {
    "city": "London",
    "temp_c": 12,
    "condition": "cloudy",
    "humidity_pct": 78,
}


class WeatherHandler(BaseHTTPRequestHandler):
    """Handle GET /weather requests."""

    def log_message(self, fmt, *args):  # type: ignore[override]
        # Suppress the default access log to keep demo output clean
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/weather":
            body = json.dumps(_WEATHER_DATA).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
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
