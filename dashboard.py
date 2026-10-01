"""Live Rich terminal dashboard for CoinMarketCap prices."""

import argparse
import sys
import time

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from scraper import fetch_crypto_data, save_to_csv

console = Console()


def _price(value: float) -> str:
    if value >= 1000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:.4f}"
    return f"${value:.6f}"


def _market_cap(value: float) -> str:
    for suffix, threshold in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if value >= threshold:
            return f"${value / threshold:.2f}{suffix}"
    return f"${value:,.0f}"


def build_table(data) -> Table:
    table = Table(
        title="CoinMarketCap — Top Cryptocurrency Prices",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        border_style="green",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Coin", style="bold")
    table.add_column("Symbol", style="yellow")
    table.add_column("Price (USD)", justify="right")
    table.add_column("24h Change", justify="right")
    table.add_column("Market Cap", justify="right")
    for _, coin in data.iterrows():
        change = float(coin["change_24h"])
        color = "green" if change >= 0 else "red"
        table.add_row(
            str(int(coin["rank"])),
            str(coin["name"]),
            str(coin["symbol"]),
            _price(float(coin["price_usd"])),
            Text(f"{change:+.2f}%", style=color),
            _market_cap(float(coin["market_cap_usd"])),
        )
    return table


def run_dashboard(headless: bool, use_selenium: bool, refresh_seconds: int) -> None:
    console.print("[bold green]CoinMarketCap Price Tracker[/]  |  Ctrl+C to exit")
    while True:
        try:
            data = fetch_crypto_data(headless=headless, use_selenium=use_selenium)
            if data is None or data.empty:
                console.print("[red]CoinMarketCap returned no data; retrying shortly.[/]")
                time.sleep(30)
                continue
            save_to_csv(data)
            console.clear()
            console.print(build_table(data))
            console.print(f"\nSource: {data['source'].iloc[0]}  |  Saved to CSV")
            console.print(f"Refreshing in {refresh_seconds} seconds")
            time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            console.print("\nDashboard stopped.")
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Live CoinMarketCap terminal dashboard.")
    parser.add_argument("--no-selenium", action="store_true", help="Use the CMC API fallback directly.")
    parser.add_argument("--visible", action="store_true", help="Show the Chrome window.")
    parser.add_argument("--refresh", type=int, default=300, help="Refresh interval in seconds.")
    args = parser.parse_args()
    run_dashboard(
        headless=not args.visible,
        use_selenium=not args.no_selenium,
        refresh_seconds=max(30, args.refresh),
    )


if __name__ == "__main__":
    main()
