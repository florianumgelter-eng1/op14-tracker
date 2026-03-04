#!/usr/bin/env python3
"""
One Piece TCG Booster Box Price Tracker – OP-01 bis OP-15
Fetches price history from PriceCharting.com + recent eBay sold listings.
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
    {"id": "op01", "name": "OP-01 Romance Dawn",             "slug": "one-piece-romance-dawn",              "console": "one-piece-romance-dawn",              "ebay": "One Piece Romance Dawn Booster Box english sealed"},
    {"id": "op02", "name": "OP-02 Paramount War",            "slug": "one-piece-paramount-war",             "console": "one-piece-paramount-war",             "ebay": "One Piece Paramount War Booster Box english sealed"},
    {"id": "op03", "name": "OP-03 Pillars of Strength",      "slug": "one-piece-pillars-of-strength",       "console": "one-piece-pillars-of-strength",       "ebay": "One Piece Pillars of Strength Booster Box english sealed"},
    {"id": "op04", "name": "OP-04 Kingdoms of Intrigue",     "slug": "one-piece-kingdoms-of-intrigue",      "console": "one-piece-kingdoms-of-intrigue",      "ebay": "One Piece Kingdoms of Intrigue Booster Box english sealed"},
    {"id": "op05", "name": "OP-05 Awakening of the New Era", "slug": "one-piece-awakening-of-the-new-era",  "console": "one-piece-awakening-of-the-new-era",  "ebay": "One Piece Awakening New Era Booster Box english sealed"},
    {"id": "op06", "name": "OP-06 Wings of the Captain",     "slug": "one-piece-wings-of-the-captain",      "console": "one-piece-wings-of-the-captain",      "ebay": "One Piece Wings of the Captain Booster Box english sealed"},
    {"id": "op07", "name": "OP-07 500 Years in the Future",  "slug": "one-piece-500-years-in-the-future",   "console": "one-piece-500-years-in-the-future",   "ebay": "One Piece 500 Years in the Future Booster Box english sealed"},
    {"id": "op08", "name": "OP-08 Two Legends",              "slug": "one-piece-two-legends",               "console": "one-piece-two-legends",               "ebay": "One Piece Two Legends Booster Box english sealed"},
    {"id": "op09", "name": "OP-09 Emperors in the New World","slug": "one-piece-emperors-in-the-new-world",  "console": "one-piece-emperors-in-the-new-world", "ebay": "One Piece Emperors in the New World Booster Box english sealed"},
    {"id": "op10", "name": "OP-10 Royal Blood",              "slug": "one-piece-royal-blood",               "console": "one-piece-royal-blood",               "ebay": "One Piece Royal Blood Booster Box english sealed"},
    {"id": "op11", "name": "OP-11 Fist of Divine Speed",     "slug": "one-piece-fist-of-divine-speed",      "console": "one-piece-fist-of-divine-speed",      "ebay": "One Piece Fist of Divine Speed Booster Box english sealed"},
    {"id": "op12", "name": "OP-12 Legacy of the Master",     "slug": "one-piece-legacy-of-the-master",      "console": "one-piece-legacy-of-the-master",      "ebay": "One Piece Legacy of the Master Booster Box english sealed"},
    {"id": "op13", "name": "OP-13 Carrying On His Will",     "slug": "one-piece-carrying-on-his-will",      "console": "one-piece-carrying-on-his-will",      "ebay": "One Piece Carrying On His Will Booster Box english sealed"},
    {"id": "op14", "name": "OP-14 Azure Sea's Seven",        "slug": "one-piece-azure-sea%27s-seven",       "console": "one-piece-azure-sea%27s-seven",       "ebay": "One Piece Azure Sea Seven OP-14 Booster Box english sealed"},
    {"id": "op15", "name": "OP-15 Adventure on Kami's Island","slug": "one-piece-adventure-on-kami%27s-island","console": "one-piece-adventure-on-kami%27s-island","ebay": "One Piece Adventure Kami Island OP-15 Booster Box sealed"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── PriceCharting ──────────────────────────────────────────

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
    match = re.search(r'"used"\s*:\s*(\[\[.*?\]\])', html, re.DOTALL)
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
    existing_ts = {e[0] for e in existing}
    for e in new_data:
        if e[0] not in existing_ts:
            existing.append(e)
    return sorted(existing, key=lambda x: x[0])


# ── eBay Sold Listings ─────────────────────────────────────

def parse_recent_sales(html: str, max_results: int = 5) -> list[dict]:
    """Parse recent individual sales from PriceCharting page."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Recent sales table – rows have: date | (icon) | title | price | (report)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Datum in erster Zelle (Format: YYYY-MM-DD)
            date_text = cells[0].get_text(strip=True)
            if not re.match(r"\d{4}-\d{2}-\d{2}", date_text):
                continue

            # Preis: suche in allen Zellen nach $xx.xx
            price = None
            title = ""
            for cell in cells[1:]:
                text = cell.get_text(strip=True)
                m = re.match(r"^\$?([\d,]+\.\d{2})$", text)
                if m:
                    try:
                        price = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
                elif len(text) > 5 and not text.startswith("$") and "report" not in text.lower() and "subscribe" not in text.lower() and "time warp" not in text.lower():
                    if not title:
                        title = text[:80]

            if price and price > 10:
                results.append({
                    "date": date_text,
                    "price": price,
                    "title": title,
                })

            if len(results) >= max_results:
                break
        if results:
            break

    return results


# ── Card List ─────────────────────────────────────────────

SKIP_KEYWORDS = ("booster box", "booster pack", "starter deck", "display", "case", "bundle", "box set", "promo pack")

def fetch_cards(console_slug: str) -> list[dict]:
    """Fetch all individual cards from a PriceCharting console page sorted by price desc."""
    url = f"https://www.pricecharting.com/console/{console_slug}?sort=price-desc&limit=all"
    html = fetch_page(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "games_table"})
    if not table:
        return []

    cards = []
    for row in table.find_all("tr"):
        # Titel-Zelle
        title_el = row.find("td", class_="title")
        if not title_el:
            continue
        link_el = title_el.find("a")
        if not link_el:
            continue
        name = link_el.get_text(strip=True)

        # Sealed-Produkte überspringen
        if any(kw in name.lower() for kw in SKIP_KEYWORDS):
            continue

        card_url = "https://www.pricecharting.com" + link_el.get("href", "")

        # Ungraded-Preis (erste .price Zelle)
        price_el = row.find("td", class_="price")
        if not price_el:
            continue
        price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")
        try:
            price = float(price_text)
        except ValueError:
            continue

        if price <= 0:
            continue

        # Kartennummer aus Name extrahieren (z.B. "OP01-001")
        num_match = re.search(r'[A-Z]{2}\d{2}-\d{3,4}', name)
        number = num_match.group(0) if num_match else ""

        cards.append({
            "name": name,
            "number": number,
            "price": price,
            "url": card_url,
        })

    # Nochmals nach Preis sortieren (sicher)
    return sorted(cards, key=lambda c: c["price"], reverse=True)


# ── Persistence ────────────────────────────────────────────

def load_existing() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sets": {}, "last_updated": None}


def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Main ───────────────────────────────────────────────────

def run():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] One Piece TCG Price Tracker")
    print("=" * 60)

    data = load_existing()
    now_ms = int(time.time() * 1000)
    one_hour = 3600 * 1000

    for i, s in enumerate(SETS):
        print(f"\n  [{i+1:02d}/15] {s['name']}")

        # ── PriceCharting ──
        url = make_url(s["slug"])
        html = fetch_page(url)

        entry = data["sets"].setdefault(s["id"], {
            "name": s["name"], "url": url,
            "history": [], "snapshots": [],
            "ebay_sold": [], "available": False
        })
        entry["name"] = s["name"]
        entry["url"] = url
        entry["ebay_query"] = s["ebay"]

        if html is None:
            print("    PriceCharting: kein Eintrag")
        else:
            entry["available"] = True
            chart_data = parse_chart_data(html)
            current_price = parse_current_price(html)

            if chart_data:
                entry["history"] = merge_history(entry.get("history", []), chart_data)
                print(f"    PC Datenpunkte: {len(entry['history'])}", end="")

            if current_price:
                print(f"  |  Preis: ${current_price:.2f}", end="")
                recent = [s2 for s2 in entry.get("snapshots", []) if now_ms - s2[0] < one_hour]
                if not recent:
                    entry.setdefault("snapshots", []).append([now_ms, round(current_price * 100)])
            print()

        # ── Recent Sales (aus PriceCharting HTML) ──
        if html:
            recent_sales = parse_recent_sales(html, max_results=5)
            if recent_sales:
                entry["recent_sales"] = recent_sales
                print(f"    Letzte Verkäufe: {len(recent_sales)}  (zuletzt ${recent_sales[0]['price']:.2f} am {recent_sales[0]['date']})")
            else:
                print("    Letzte Verkäufe: keine gefunden")

        time.sleep(1.0)

        # ── Kartenliste ──
        cards = fetch_cards(s["console"])
        if cards:
            entry["cards"] = cards
            print(f"    Karten: {len(cards)} geladen  (teuerste: {cards[0]['name'][:40]} – ${cards[0]['price']:.2f})")
        else:
            print("    Karten: keine gefunden")

        time.sleep(1.5)

    data["last_updated"] = datetime.now().isoformat()
    save(data)
    print(f"\n  Gespeichert: {DATA_FILE}")
    print("=" * 60)
    return data


if __name__ == "__main__":
    run()
