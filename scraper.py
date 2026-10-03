"""
scraper.py — Cryptocurrency Price Tracker
=========================================
A Selenium-powered Python tool that dynamically scrapes real-time
cryptocurrency prices from CoinMarketCap.

As described in the project specification:
  - Uses Chrome WebDriver (via webdriver_manager) to load JS-rendered pages
  - Collects: coin name, current price, 24h change, market cap
  - Supports headless mode
  - Appends timestamped rows to CSV for historical logging
  - Provides filtering by price or 24h change

Technologies used (per specification):
  • selenium          — browser control & dynamic page scraping
  • webdriver_manager — automatic ChromeDriver setup
  • pandas            — data manipulation and CSV export
  • time              — scraping delays and timestamps
  • datetime          — timestamping each record
"""

import os
import sys
import time
import datetime

import pandas as pd
import requests

# ── Selenium imports (primary technology as per specification) ────────────────
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Force UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Chrome WebDriver Setup
#  Uses webdriver_manager to auto-download the correct ChromeDriver version.
# ═══════════════════════════════════════════════════════════════════════════════

def build_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Create and return a configured Chrome WebDriver instance.

    Args:
        headless: If True, runs Chrome in background without opening a window.
                  If False, opens a visible browser window.

    Returns:
        A configured webdriver.Chrome instance.
    """
    options = Options()

    # ── Headless mode (Feature 5 from specification) ─────────────────────────
    if headless:
        options.add_argument("--headless=new")   # modern headless flag for Chrome

    # ── Browser settings ─────────────────────────────────────────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_argument("--lang=en-US,en;q=0.9")

    # ── webdriver_manager automatically downloads the correct ChromeDriver ────
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CoinMarketCap Selenium Scraper  (PRIMARY — as per specification)
#  "Uses Selenium WebDriver to load and extract data from JS-rendered pages"
# ═══════════════════════════════════════════════════════════════════════════════

CMC_URL = "https://coinmarketcap.com/"


def scrape_coinmarketcap_selenium(
    headless: bool = True,
    top_n: int = 10,
) -> pd.DataFrame | None:
    """
    PRIMARY scraper — uses Selenium + Chrome WebDriver to load coinmarketcap.com
    and extract live cryptocurrency data from the dynamically rendered HTML table.

    Process:
        1. Launch Chrome via webdriver_manager
        2. Navigate to coinmarketcap.com
        3. Wait for JavaScript to render the price table (WebDriverWait)
        4. Use time.sleep() delays for natural page-load behaviour
        5. Extract coin name, price, 24h change, market cap from table rows
        6. Return a pandas DataFrame

    Args:
        headless: Run browser in background (no window) if True.
        top_n: Number of coins to extract.
    Returns:
        DataFrame on success, None on failure.
    """
    driver = None
    try:
        print("[•] Launching Chrome WebDriver (webdriver_manager) ...")
        driver = build_driver(headless=headless)

        # ── Step 1: Navigate to CoinMarketCap ────────────────────────────────
        print(f"[•] Loading {CMC_URL} ...")
        driver.get(CMC_URL)

        # ── Step 2: Allow time for JS to render the page ──────────────────────
        # time module used for scraping delays (per specification)
        print("[•] Waiting for JavaScript to render the price table ...")
        time.sleep(5)

        # Scroll slightly to trigger lazy-loading of table rows
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(2)

        # ── Step 3: Wait for table rows to appear ─────────────────────────────
        wait = WebDriverWait(driver, 30)
        try:
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table tbody tr")
            ))
            time.sleep(2)   # extra buffer for all rows to fully load
        except Exception:
            print("[!] Table did not appear within timeout — CMC may have blocked this session.")
            return None

        # ── Step 4: Extract table rows ────────────────────────────────────────
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        headers = [
            " ".join(header.text.split()).casefold()
            for header in driver.find_elements(By.CSS_SELECTOR, "table thead th")
        ]

        def column_index(label: str, fallback: int) -> int:
            return next(
                (index for index, header in enumerate(headers) if label in header),
                fallback,
            )

        rank_index = column_index("rank", 1)
        name_index = column_index("name", 2)
        price_index = column_index("price", 3)
        change_index = column_index("24h", 5)
        market_cap_index = column_index("market cap", 7)
        print(f"[•] Found {len(rows)} rows in the CoinMarketCap price table")

        if not rows:
            print("[!] No table rows found.")
            return None

        # ── Step 5: Parse each row for coin data ──────────────────────────────
        records = []
        for row in rows[:top_n]:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) <= max(
                    rank_index, name_index, price_index, change_index, market_cap_index
                ):
                    continue

                rank_text = cells[rank_index].text.strip()
                rank = int(rank_text) if rank_text.isdigit() else len(records) + 1

                name_lines = cells[name_index].text.strip().splitlines()
                name = name_lines[0].strip() if name_lines else "N/A"
                symbol = name_lines[1].strip() if len(name_lines) > 1 else "N/A"

                price_text = (
                    cells[price_index].text.strip()
                    .replace("$", "").replace(",", "").strip()
                )
                price = float(price_text) if price_text else 0.0

                change_text = (
                    cells[change_index].text.strip()
                    .replace("%", "")
                    .replace("\u2212", "-")
                    .replace("−", "-")
                    .strip()
                )
                change_24h = float(change_text) if change_text else 0.0

                mcap_raw = (
                    cells[market_cap_index].text.strip()
                    .replace("$", "").replace(",", "").strip()
                )
                market_cap = _parse_shorthand(mcap_raw)

                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                records.append({
                    "rank":           rank,
                    "name":           name,
                    "symbol":         symbol,
                    "price_usd":      price,
                    "change_24h":     change_24h,
                    "market_cap_usd": market_cap,
                    "timestamp":      ts,
                    "source":         "CoinMarketCap (Selenium)",
                })

            except Exception as row_err:
                print(f"  [!] Skipping row {len(records)+1}: {row_err}")
                continue

        if not records:
            print("[!] Selenium scrape returned 0 records — CMC likely blocked the session.")
            return None

        df = pd.DataFrame(records)
        print(f"[✓] CoinMarketCap (Selenium): scraped {len(df)} coins successfully")
        return df

    except Exception as e:
        print(f"[!] Selenium scrape failed: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _parse_shorthand(text: str) -> float:
    """Convert CMC market cap shorthand (e.g. '1.34T', '330B', '74.3M') to float."""
    text = text.upper().strip()
    for suffix, mult in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if text.endswith(suffix):
            try:
                return float(text[:-1]) * mult
            except ValueError:
                return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — CoinMarketCap API fallback
# ═══════════════════════════════════════════════════════════════════════════════

_CMC_INTERNAL_URL = (
    "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing"
    "?start=1&limit={n}&sortBy=market_cap&sortType=desc&convert=USD"
    "&cryptoType=all&tagType=all&audited=false"
)

_CMC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://coinmarketcap.com/",
    "Origin": "https://coinmarketcap.com",
}


def _scrape_coinmarketcap_api_backup(top_n: int = 10) -> pd.DataFrame | None:
    """Fetch CoinMarketCap's listing data when Selenium cannot load the page."""
    try:
        response = requests.get(
            _CMC_INTERNAL_URL.format(n=top_n),
            headers=_CMC_HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        coins = response.json().get("data", {}).get("cryptoCurrencyList", [])
        if not coins:
            return None

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = []
        for index, coin in enumerate(coins, start=1):
            quotes = coin.get("quotes", [{}])
            usd = next(
                (quote for quote in quotes if quote.get("name") == "USD"),
                quotes[0] if quotes else {},
            )
            records.append({
                "rank": coin.get("cmcRank", index),
                "name": coin.get("name", "N/A"),
                "symbol": coin.get("symbol", "N/A"),
                "price_usd": usd.get("price", 0.0) or 0.0,
                "change_24h": usd.get("percentChange24h", 0.0) or 0.0,
                "market_cap_usd": usd.get("marketCap", 0.0) or 0.0,
                "timestamp": timestamp,
                "source": "CoinMarketCap (API backup — Selenium blocked)",
            })
        return pd.DataFrame(records)
    except Exception as error:
        print(f"[!] CoinMarketCap API backup failed: {error}")
        return None


def fetch_crypto_data(
    headless: bool = True,
    top_n: int = 10,
    use_selenium: bool = True,
) -> pd.DataFrame | None:
    """Fetch CoinMarketCap data through Selenium, then its API fallback."""
    if use_selenium:
        data = scrape_coinmarketcap_selenium(headless=headless, top_n=top_n)
        if data is not None and not data.empty:
            return data
        print("[→] Selenium failed; trying the CoinMarketCap API fallback.")
    return _scrape_coinmarketcap_api_backup(top_n=top_n)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — Filtering helpers  (Feature 7 — Optional filtering)
# ═══════════════════════════════════════════════════════════════════════════════

def filter_by_price(
    df: pd.DataFrame,
    min_price: float = 0.0,
    max_price: float = float("inf"),
) -> pd.DataFrame:
    """
    Filter coins by price range.
    Specification: "filtering based on custom conditions like price threshold"
    """
    return df[
        (df["price_usd"] >= min_price) & (df["price_usd"] <= max_price)
    ].reset_index(drop=True)


def filter_top_gainers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Return top N coins by highest 24h gain.
    Specification: "highest 24-hour gainers"
    """
    return (
        df.sort_values("change_24h", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def filter_top_losers(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Return the N coins with the weakest 24-hour performance."""
    return (
        df.sort_values("change_24h", ascending=True)
        .head(top_n)
        .reset_index(drop=True)
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — CSV helpers  (CSV export + historical logging)
# ═══════════════════════════════════════════════════════════════════════════════

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "crypto_data.csv")
CSV_COLUMNS = [
    "rank",
    "name",
    "symbol",
    "price_usd",
    "change_24h",
    "market_cap_usd",
    "timestamp",
    "source",
]


def _clean_csv_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the CSV schema consistent and round values for readability."""
    cleaned = df.reindex(columns=CSV_COLUMNS).copy()
    cleaned["rank"] = pd.to_numeric(cleaned["rank"], errors="coerce").fillna(0).astype(int)

    prices = pd.to_numeric(cleaned["price_usd"], errors="coerce")
    small_prices = prices.abs() < 1
    cleaned["price_usd"] = prices.where(~small_prices, prices.round(8))
    cleaned["price_usd"] = cleaned["price_usd"].where(small_prices, prices.round(2))

    cleaned["change_24h"] = pd.to_numeric(cleaned["change_24h"], errors="coerce").round(2)
    cleaned["market_cap_usd"] = (
        pd.to_numeric(cleaned["market_cap_usd"], errors="coerce")
        .round()
        .astype("Int64")
    )
    cleaned["timestamp"] = cleaned["timestamp"].astype(str)

    def source_label(value) -> str:
        source = str(value).casefold()
        if "api" in source:
            return "CoinMarketCap API"
        if "selenium" in source:
            return "CoinMarketCap Selenium"
        return "CoinMarketCap"

    cleaned["source"] = cleaned["source"].map(source_label)
    return cleaned


def save_to_csv(df: pd.DataFrame, path: str = CSV_PATH) -> str:
    """
    Append DataFrame rows to CSV file.
    Specification: "Appends timestamped data to the CSV file to enable
                    trend tracking over time."
    Creates the file with header on first run; appends on subsequent runs.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_exists = os.path.isfile(path)
    cleaned = _clean_csv_rows(df)
    cleaned.to_csv(
        path,
        mode="a",
        header=not file_exists,
        index=False,
        encoding="utf-8" if file_exists else "utf-8-sig",
    )
    return path


def load_from_csv(path: str = CSV_PATH) -> pd.DataFrame | None:
    """Load complete historical CSV into a DataFrame."""
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)
