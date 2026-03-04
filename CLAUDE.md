# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Start the local web server (opens browser automatically at http://localhost:8765)
python server.py

# Run the scraper manually to refresh price data
python scraper.py
```

Windows batch shortcuts:
- `starten.bat` — starts the server
- `update_und_öffnen.bat` — runs the scraper then starts the server
- `auto_update.bat` — scraper only

## Architecture

This is a single-page local web app with no build step and no framework.

### Backend (`server.py`)
- Minimal `HTTPServer` serving static files from the project root
- Two API endpoints:
  - `GET /api/prices` — returns `prices_all.json`
  - `GET /api/update` — triggers `scraper.run()` synchronously and returns the result
- No database; all persistent price data lives in `prices_all.json`

### Scraper (`scraper.py`)
- Fetches booster box price history and individual card prices from **PriceCharting.com** for OP-01 through OP-15
- Also parses recent sold listings from PriceCharting's own sales table
- Merges new data into `prices_all.json` without overwriting historical data points (`merge_history`)
- Data shape per set: `{ name, url, history: [[timestamp_ms, price_cents], ...], snapshots, cards, recent_sales, available }`
- Card shape: `{ name, number, price, grade9, psa10, url, img }`
- Runs daily via GitHub Actions (`.github/workflows/scraper.yml`) at 22:59 UTC, commits updated `prices_all.json`

### Frontend (`index.html`)
Single self-contained HTML file with inline CSS and JS. Key sections:

- **Set sidebar** — lists all 15 sets, clicking loads that set's data
- **Main panel tabs**: Overview (price chart + stats + recent sales) | Cards (sortable table) | Market Overview (mini charts for all sets)
- **Card table** — renders from `prices_all.json → sets[setId].cards`, columns: img, +inv button, rank, name, number, ungraded, PSA9, PSA10
- **Inventory drawer** (right slide-in) — stored in `localStorage` as `op_inventory`
  - Key format: `{setId}__{cardNumber}__{grade}` where grade ∈ `ungraded | psa9 | psa10`
  - Each entry stores: card data + `grade`, `price` (for chosen grade), `qty`, `addedAt` (timestamp)
  - Renders a Chart.js doughnut showing value distribution + clean card list with grade badges
- **Grade picker** — popup shown on "+" click, lets user choose Ungraded / PSA 9 / PSA 10 before adding to inventory
- **Charts** — Chart.js 4.4 with date-fns adapter, time-series line chart for set price history

### Data flow
1. On load: `refreshData()` fetches `prices_all.json`, populates `allSets`
2. Selecting a set calls `renderSet(sd)` which builds the card table and price chart
3. Inventory lives entirely client-side in localStorage; no server involvement
