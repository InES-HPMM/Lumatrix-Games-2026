"""Lokale, betriebssystemunabhaengige Browser-Einrichtung."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import urllib.parse

import transport_api


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def start_server(config_store, state, host="127.0.0.1", port=8765):
    html_path = os.path.join(os.path.dirname(__file__), "setup.html")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def send_bytes(self, body, content_type="application/json; charset=utf-8", status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                with open(html_path, "rb") as handle:
                    self.send_bytes(handle.read(), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/config":
                self.send_bytes(_json_bytes(config_store.load()))
                return
            if parsed.path == "/api/status":
                self.send_bytes(_json_bytes(state.status_snapshot()))
                return
            if parsed.path == "/api/locations":
                query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
                try:
                    names = transport_api.fetch_locations(query) if len(query) >= 2 else []
                    self.send_bytes(_json_bytes({"locations": names}))
                except Exception as exc:
                    self.send_bytes(_json_bytes({"error": str(exc)}), status=502)
                return
            self.send_bytes(b"Not found", "text/plain; charset=utf-8", 404)

        def do_POST(self):
            if self.path != "/api/config":
                self.send_bytes(b"Not found", "text/plain; charset=utf-8", 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 16384:
                    raise ValueError("Ungueltige Datenmenge")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                saved = config_store.save(payload)
                state.request_refresh()
                self.send_bytes(_json_bytes({"ok": True, "config": saved}))
            except Exception as exc:
                self.send_bytes(_json_bytes({"ok": False, "error": str(exc)}), status=400)

    server = ThreadingHTTPServer((host, port), Handler)
    return server

