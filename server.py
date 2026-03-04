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

# ── Async scraper state ─────────────────────────────────────
_scrape_lock = threading.Lock()
_scrape_state = {
    "running": False,
    "progress": 0,      # 0–100
    "current": "",
    "done": False,
    "error": None,
}

def _run_scraper_async():
    global _scrape_state
    total = len(scraper.SETS)
    original_run = scraper.run

    # Patch: intercept per-set progress via a wrapper
    completed = [0]

    def _patched_run():
        import time
        from datetime import datetime
        data = scraper.load_existing()
        now_ms = int(time.time() * 1000)
        one_hour = 3600 * 1000

        for i, s in enumerate(scraper.SETS):
            with _scrape_lock:
                _scrape_state["current"] = s["name"]
                _scrape_state["progress"] = int((i / total) * 95)

            url = scraper.make_url(s["slug"])
            html = scraper.fetch_page(url)
            entry = data["sets"].setdefault(s["id"], {
                "name": s["name"], "url": url,
                "history": [], "snapshots": [],
                "ebay_sold": [], "available": False
            })
            entry["name"] = s["name"]
            entry["url"] = url
            entry["ebay_query"] = s["ebay"]

            if html:
                entry["available"] = True
                box_img = scraper.parse_box_image(html)
                if box_img:
                    entry["box_img"] = box_img
                chart_data = scraper.parse_chart_data(html)
                current_price = scraper.parse_current_price(html)
                if chart_data:
                    entry["history"] = scraper.merge_history(entry.get("history", []), chart_data)
                if current_price:
                    recent = [s2 for s2 in entry.get("snapshots", []) if now_ms - s2[0] < one_hour]
                    if not recent:
                        entry.setdefault("snapshots", []).append([now_ms, round(current_price * 100)])
                recent_sales = scraper.parse_recent_sales(html, max_results=5)
                if recent_sales:
                    entry["recent_sales"] = recent_sales
            else:
                print(f"    {s['name']}: kein Eintrag")

            time.sleep(1.0)
            cards = scraper.fetch_cards(s["console"])
            if cards:
                entry["cards"] = cards
            time.sleep(1.5)

        data["last_updated"] = datetime.now().isoformat()
        scraper.save(data)
        return data

    try:
        result = _patched_run()
        with _scrape_lock:
            _scrape_state["running"] = False
            _scrape_state["done"] = True
            _scrape_state["progress"] = 100
            _scrape_state["current"] = "Fertig"
    except Exception as e:
        with _scrape_lock:
            _scrape_state["running"] = False
            _scrape_state["done"] = True
            _scrape_state["error"] = str(e)
        print(f"  Scraper Fehler: {e}")


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

        # Legacy blocking endpoint (kept for compatibility)
        if path == "/api/update":
            print("  Scraper läuft (alle 15 Sets)...")
            try:
                data = scraper.run()
                self.send_json({"ok": True, "data": data})
            except Exception as e:
                print(f"  Fehler: {e}")
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        # Async scraper: start
        if path == "/api/scrape/start":
            with _scrape_lock:
                if _scrape_state["running"]:
                    self.send_json({"ok": False, "error": "Läuft bereits"})
                    return
                _scrape_state.update({"running": True, "done": False, "error": None, "progress": 0, "current": "Starte…"})
            threading.Thread(target=_run_scraper_async, daemon=True).start()
            self.send_json({"ok": True})
            return

        # Async scraper: status
        if path == "/api/scrape/status":
            with _scrape_lock:
                state = dict(_scrape_state)
            # If done, also return the fresh data
            if state["done"] and not state["error"] and scraper.DATA_FILE.exists():
                state["data"] = json.loads(scraper.DATA_FILE.read_text(encoding="utf-8"))
            self.send_json(state)
            return

        # Async scraper: cancel
        if path == "/api/scrape/cancel":
            with _scrape_lock:
                _scrape_state["running"] = False
                _scrape_state["done"] = True
                _scrape_state["error"] = "Abgebrochen"
            self.send_json({"ok": True})
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
