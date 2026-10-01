# Cryptocurrency Price Tracker

A Selenium-powered Python tool that loads CoinMarketCap in Google Chrome and extracts current cryptocurrency market data from its JavaScript-rendered page.

## Features

- Scrapes the top 10 cryptocurrencies from CoinMarketCap.
- Collects rank, coin name, symbol, USD price, 24-hour change, and market capitalization.
- Supports headless Chrome or a visible browser window.
- Appends timestamped results to `data/crypto_data.csv` for historical analysis.
- Optionally filters displayed results by USD price range or highest 24-hour gainers.
- Exports CSV data for use in analysis and dashboard tools.
- Provides a Flask web dashboard with live refresh, charts, history, and CSV download.
- Includes a Rich terminal dashboard and an interactive CLI menu.

## Requirements

- Python 3.10 or later
- Google Chrome
- Packages listed in `requirements.txt`

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

`webdriver-manager` downloads and manages the matching ChromeDriver.
Flask serves the local web dashboard, `rich` powers the terminal dashboard, and `requests` is used for the CoinMarketCap API fallback.

## Run

Start the local website:

```bash
python app.py
```

With the server running, open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in your browser. Keep the terminal running while you use the website. The page shows the latest saved CSV snapshot, refreshes CoinMarketCap every 10 seconds, and lets you filter by price or view top gainers.

Visit `/history` to browse saved snapshots and view price trends. Visit `/csv` to search and browse archived CSV rows in the website, or use **Download CSV** there to save the complete file locally. `/api/prices` and `/api/history` provide JSON data; `/api/download` downloads the CSV.

Run a scrape from the command line and save the top 10 coins using headless Chrome:

```bash
python tracker.py
```

The interactive menu also provides auto-refresh, price filtering, gainers and losers, saved history, settings, and the Rich terminal dashboard.

Run the terminal dashboard directly:

```bash
python dashboard.py --refresh 60
```

Show the Chrome window while scraping:

```bash
python tracker.py --visible
```

Display coins in a USD price range:

```bash
python tracker.py --price-range 100 1000
```

Display the top five 24-hour gainers, or choose a count:

```bash
python tracker.py --top-gainers
python tracker.py --top-gainers 3
```

Each run appends the unfiltered top-10 snapshot to `data/crypto_data.csv`. Filters affect the terminal display, not the historical log.

## CSV Fields

`rank`, `name`, `symbol`, `price_usd`, `change_24h`, `market_cap_usd`, `timestamp`, and `source`.

The timestamped CSV supports historical comparisons, trend analysis, and integration with external dashboard or visualization tools.

## Data Source

All live market data is collected from [CoinMarketCap](https://coinmarketcap.com/). Selenium with Chrome WebDriver is the primary source; CoinMarketCap's own listing API is used as a fallback if the browser cannot load the page. No other provider is used.
