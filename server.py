#!/usr/bin/env python3
"""
Lokaler Webserver für den One Piece TCG Preistracker.
Startet auf http://localhost:8765
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import scraper

ROOT = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Stille Logs

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        mime = {
            ".html": "text/html; charset=utf-8",
            ".json": "application/json",
            ".js":   "application/javascript",
            ".css":  "text/css",
        }.get(path.suffix, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/update":
            print("  Scraper läuft (alle 15 Sets)...")
            try:
                data = scraper.run()
                self.send_json({"ok": True, "data": data})
            except Exception as e:
                print(f"  Fehler: {e}")
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/prices":
            if scraper.DATA_FILE.exists():
                data = json.loads(scraper.DATA_FILE.read_text(encoding="utf-8"))
                self.send_json({"ok": True, "data": data})
            else:
                self.send_json({"ok": False, "error": "Keine Daten"}, 404)
            return

        if path in ("/", "/index.html"):
            self.send_file(ROOT / "index.html")
            return

        file = ROOT / path.lstrip("/")
        if file.exists() and file.is_file():
            self.send_file(file)
        else:
            self.send_response(404)
            self.end_headers()


def open_browser(port):
    import time
    time.sleep(1)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    PORT = 8765
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"\n  One Piece TCG Preistracker läuft auf http://localhost:{PORT}")
    print("  STRG+C zum Beenden\n")
    threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server gestoppt.")
