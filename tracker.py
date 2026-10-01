"""Interactive command-line tools for the CoinMarketCap price tracker."""

import subprocess
import sys
import time

try:
    from rich.console import Console
    from rich.prompt import Prompt
    RICH = True
    console = Console()
except ImportError:
    RICH = False

from scraper import (
    CSV_PATH,
    fetch_crypto_data,
    filter_by_price,
    filter_top_gainers,
    filter_top_losers,
    load_from_csv,
    save_to_csv,
)


def _print(message: str) -> None:
    if RICH:
        console.print(message)
    else:
        print(message)


def show_data(data, title: str) -> None:
    if data is None or data.empty:
        _print("No data to display.")
        return
    _print(f"\n{title}\n{'=' * len(title)}")
    _print(data.to_string(index=False))


def scrape(settings: dict):
    data = fetch_crypto_data(
        headless=settings["headless"],
        top_n=settings["top_n"],
        use_selenium=settings["use_selenium"],
    )
    if data is None or data.empty:
        _print("CoinMarketCap did not return data.")
        return None
    _print(f"Fetched {len(data)} coins from {data['source'].iloc[0]}.")
    return data


def action_scrape(settings: dict) -> None:
    data = scrape(settings)
    if data is not None:
        show_data(data, "Live cryptocurrency prices")
        _print(f"\nSaved to {save_to_csv(data)}")


def action_auto_refresh(settings: dict) -> None:
    try:
        minutes = int(input("Refresh interval in minutes [5]: ").strip() or "5")
    except ValueError:
        minutes = 5
    interval = max(30, minutes * 60)
    _print("Auto-refresh active. Press Ctrl+C to stop.")
    try:
        while True:
            data = scrape(settings)
            if data is not None:
                show_data(data, "Live cryptocurrency prices")
                _print(f"Saved to {save_to_csv(data)}")
            time.sleep(interval)
    except KeyboardInterrupt:
        _print("Auto-refresh stopped.")


def action_filter_price(settings: dict) -> None:
    data = scrape(settings)
    if data is None:
        return
    try:
        minimum = float(input("Minimum USD price [0]: ").strip() or "0")
        maximum = float(input("Maximum USD price [1000000]: ").strip() or "1000000")
    except ValueError:
        _print("Enter valid numeric prices.")
        return
    filtered = filter_by_price(data, minimum, maximum)
    show_data(filtered, f"Coins from ${minimum:,.2f} to ${maximum:,.2f}")
    if not filtered.empty:
        save_to_csv(filtered)


def action_gainers_losers(settings: dict) -> None:
    data = scrape(settings)
    if data is None:
        return
    show_data(filter_top_gainers(data), "Top 5 24-hour gainers")
    show_data(filter_top_losers(data), "Top 5 24-hour losers")


def action_history() -> None:
    data = load_from_csv()
    if data is None or data.empty:
        _print("No saved history yet.")
        return
    show_data(data.tail(50), f"Latest saved records ({len(data)} total)")
    _print(f"Full history: {CSV_PATH}")


def action_settings(settings: dict) -> None:
    _print(
        f"\n1. Selenium: {'ON' if settings['use_selenium'] else 'OFF'}"
        f"\n2. Headless Chrome: {'ON' if settings['headless'] else 'OFF'}"
        f"\n3. Coin count: {settings['top_n']}"
    )
    choice = input("Change setting (1-3, Enter to cancel): ").strip()
    if choice == "1":
        settings["use_selenium"] = not settings["use_selenium"]
    elif choice == "2":
        settings["headless"] = not settings["headless"]
    elif choice == "3":
        try:
            settings["top_n"] = max(1, min(100, int(input("Number of coins [10]: ") or "10")))
        except ValueError:
            _print("Coin count was not changed.")


def action_dashboard(settings: dict) -> None:
    command = [sys.executable, "dashboard.py", "--refresh", "120"]
    if not settings["use_selenium"]:
        command.append("--no-selenium")
    if not settings["headless"]:
        command.append("--visible")
    subprocess.run(command, check=False)


MENU = (
    ("1", "Scrape now"),
    ("2", "Auto-refresh"),
    ("3", "Filter by price"),
    ("4", "Top gainers and losers"),
    ("5", "View history"),
    ("6", "Settings"),
    ("7", "Live terminal dashboard"),
    ("0", "Exit"),
)


def main() -> None:
    settings = {"use_selenium": True, "headless": True, "top_n": 10}
    while True:
        print("\nCryptocurrency Price Tracker — CoinMarketCap")
        print("=" * 48)
        print(
            f"Selenium: {'ON' if settings['use_selenium'] else 'OFF'} | "
            f"Headless: {'ON' if settings['headless'] else 'OFF'} | "
            f"Top {settings['top_n']} coins"
        )
        for key, label in MENU:
            print(f"  [{key}] {label}")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            action_scrape(settings)
        elif choice == "2":
            action_auto_refresh(settings)
        elif choice == "3":
            action_filter_price(settings)
        elif choice == "4":
            action_gainers_losers(settings)
        elif choice == "5":
            action_history()
        elif choice == "6":
            action_settings(settings)
        elif choice == "7":
            action_dashboard(settings)
        elif choice == "0":
            return
        else:
            _print("Choose one of the listed options.")


if __name__ == "__main__":
    main()
