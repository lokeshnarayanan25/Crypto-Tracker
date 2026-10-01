"""Local web interface for the CoinMarketCap price tracker."""

import csv
import json
import os
import threading
import time
from io import BytesIO, StringIO

from flask import Flask, jsonify, render_template, request, send_file

from scraper import CSV_PATH, fetch_crypto_data, load_from_csv, save_to_csv

app = Flask(__name__)
_state_lock = threading.Lock()
REFRESH_INTERVAL_SECONDS = 10
_last_refresh_started = 0.0


def _saved_snapshot() -> tuple[list[dict], str | None]:
    history = load_from_csv()
    if history is None or history.empty or "timestamp" not in history:
        return [], None

    latest_timestamp = str(history["timestamp"].iloc[-1])
    latest = history[history["timestamp"].astype(str) == latest_timestamp]
    records = json.loads(latest.to_json(orient="records"))
    return records, latest_timestamp


_saved_coins, _saved_timestamp = _saved_snapshot()
_state = {
    "coins": _saved_coins,
    "updated": _saved_timestamp,
    "cached": bool(_saved_coins),
    "loading": False,
    "queued_refresh": False,
    "error": None,
}


def _state_snapshot() -> dict:
    with _state_lock:
        return {**_state, "count": len(_state["coins"])}


def _refresh_worker() -> None:
    try:
        data = fetch_crypto_data(headless=True)
        if data is None or data.empty:
            raise RuntimeError("CoinMarketCap did not return data. Check connectivity and try again.")

        save_to_csv(data)
        coins = json.loads(data.to_json(orient="records"))
        updated = str(data.iloc[-1]["timestamp"])
        with _state_lock:
            _state.update(coins=coins, updated=updated, cached=False, error=None)
    except Exception as error:
        with _state_lock:
            _state["error"] = str(error)
    finally:
        with _state_lock:
            run_queued_refresh = _state["queued_refresh"]
            _state["queued_refresh"] = False
            _state["loading"] = False
        if run_queued_refresh:
            _start_refresh(force=True)


def _start_refresh(force: bool = False) -> tuple[bool, float, bool]:
    global _last_refresh_started
    now = time.monotonic()
    with _state_lock:
        if _state["loading"]:
            if force:
                _state["queued_refresh"] = True
            return False, 0.0, force
        remaining = REFRESH_INTERVAL_SECONDS - (now - _last_refresh_started)
        if remaining > 0 and not force:
            return False, remaining, False
        _last_refresh_started = now
        _state.update(loading=True, error=None)

    threading.Thread(target=_refresh_worker, daemon=True).start()
    return True, 0.0, False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/csv")
def csv_archive():
    return render_template("csv.html")


@app.route("/api/prices")
def api_prices():
    return jsonify(_state_snapshot())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    manual = request.args.get("manual") == "1"
    started, retry_after, queued = _start_refresh(force=manual)
    snapshot = _state_snapshot()
    snapshot.update(
        refresh_started=started,
        retry_after=retry_after,
        queued_refresh=queued or snapshot["queued_refresh"],
    )
    return jsonify(snapshot)


@app.route("/api/history")
def api_history():
    history_data = load_from_csv()
    if history_data is None or history_data.empty:
        return jsonify({"records": [], "count": 0})
    records = history_data.fillna(0).to_dict(orient="records")
    return jsonify({"records": records, "count": len(records)})


@app.route("/api/download")
def api_download():
    if os.path.isfile(CSV_PATH):
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as source:
            rows = csv.reader(source)
            headers = next(rows, None)
            output = StringIO(newline="")
            writer = csv.writer(output)
            if headers is not None:
                writer.writerow(headers)
                timestamp_index = headers.index("timestamp") if "timestamp" in headers else None
                for row in rows:
                    if timestamp_index is not None and timestamp_index < len(row):
                        row[timestamp_index] = "'" + row[timestamp_index]
                    writer.writerow(row)
        download = BytesIO(output.getvalue().encode("utf-8-sig"))
        return send_file(download, as_attachment=True, download_name="crypto_data.csv")
    return jsonify({"error": "No CSV history exists yet."}), 404


if __name__ == "__main__":
    print("Crypto Tracker is running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
