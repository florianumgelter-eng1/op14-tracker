#!/usr/bin/env python3
"""
One Piece TCG Booster Box Price Tracker – OP-01 bis OP-15
Fetches price history from PriceCharting.com and saves to prices_all.json
"""

import json
import re
import time
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4"])
    import requests
    from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent / "prices_all.json"

SETS = [
    {"id": "op01", "name": "OP-01 Romance Dawn",            "slug": "one-piece-romance-dawn"},
    {"id": "op02", "name": "OP-02 Paramount War",           "slug": "one-piece-paramount-war"},
    {"id": "op03", "name": "OP-03 Pillars of Strength",     "slug": "one-piece-pillars-of-strength"},
    {"id": "op04", "name": "OP-04 Kingdoms of Intrigue",    "slug": "one-piece-kingdoms-of-intrigue"},
    {"id": "op05", "name": "OP-05 Awakening of the New Era","slug": "one-piece-awakening-of-the-new-era"},
    {"id": "op06", "name": "OP-06 Wings of the Captain",    "slug": "one-piece-wings-of-the-captain"},
    {"id": "op07", "name": "OP-07 500 Years in the Future", "slug": "one-piece-500-years-in-the-future"},
    {"id": "op08", "name": "OP-08 Two Legends",             "slug": "one-piece-two-legends"},
    {"id": "op09", "name": "OP-09 Emperors in the New World","slug": "one-piece-emperors-in-the-new-world"},
    {"id": "op10", "name": "OP-10 Royal Blood",             "slug": "one-piece-royal-blood"},
    {"id": "op11", "name": "OP-11 Fist of Divine Speed",    "slug": "one-piece-fist-of-divine-speed"},
    {"id": "op12", "name": "OP-12 Legacy of the Master",    "slug": "one-piece-legacy-of-the-master"},
    {"id": "op13", "name": "OP-13 Carrying On His Will",    "slug": "one-piece-carrying-on-his-will"},
    {"id": "op14", "name": "OP-14 Azure Sea's Seven",       "slug": "one-piece-azure-sea%27s-seven"},
    {"id": "op15", "name": "OP-15 Adventure on Kami's Island", "slug": "one-piece-adventure-on-kami%27s-island"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


def make_url(slug: str) -> str:
    return f"https://www.pricecharting.com/game/{slug}/booster-box"


def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    Fetch error: {e}")
        return None


def parse_chart_data(html: str) -> list:
    pattern = r'"used"\s*:\s*(\[\[.*?\]\])'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return []


def parse_current_price(html: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")
    for selector in ["#used_price .price", ".price-box .used .price", "[id*='used'] .price"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True).replace("$", "").replace(",", "")
            try:
                return float(text)
            except ValueError:
                pass
    match = re.search(r'"usedPrice"\s*:\s*"?\$?([\d,]+\.?\d*)"?', html)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def merge_history(existing: list, new_data: list) -> list:
    existing_ts = {entry[0] for entry in existing}
    for entry in new_data:
        if entry[0] not in existing_ts:
            existing.append(entry)
    return sorted(existing, key=lambda x: x[0])


def load_existing() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sets": {}, "last_updated": None}


def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] One Piece TCG Price Tracker")
    print("=" * 55)

    data = load_existing()
    now_ms = int(time.time() * 1000)
    one_hour = 3600 * 1000

    for i, s in enumerate(SETS):
        print(f"\n  [{i+1:02d}/15] {s['name']}")
        url = make_url(s["slug"])
        html = fetch_page(url)

        if html is None:
            print("    Kein Eintrag auf PriceCharting (noch nicht verfügbar)")
            if s["id"] not in data["sets"]:
                data["sets"][s["id"]] = {
                    "name": s["name"], "url": url,
                    "history": [], "snapshots": [], "available": False
                }
            continue

        chart_data = parse_chart_data(html)
        current_price = parse_current_price(html)

        entry = data["sets"].setdefault(s["id"], {
            "name": s["name"], "url": url,
            "history": [], "snapshots": [], "available": True
        })
        entry["available"] = True
        entry["name"] = s["name"]
        entry["url"] = url

        if chart_data:
            entry["history"] = merge_history(entry.get("history", []), chart_data)
            print(f"    Datenpunkte: {len(entry['history'])}", end="")

        if current_price:
            print(f"  |  Preis: ${current_price:.2f}", end="")
            recent = [s2 for s2 in entry.get("snapshots", []) if now_ms - s2[0] < one_hour]
            if not recent:
                entry.setdefault("snapshots", []).append([now_ms, round(current_price * 100)])
        print()

        # Rate limiting: kurze Pause zwischen Requests
        if i < len(SETS) - 1:
            time.sleep(1.5)

    data["last_updated"] = datetime.now().isoformat()
    save(data)
    print(f"\n  Gespeichert: {DATA_FILE}")
    print("=" * 55)
    return data


if __name__ == "__main__":
    run()
