import csv
import os
from datetime import datetime

TRADE_HISTORY_FILE = "trade_history.csv"
EQUITY_HISTORY_FILE = "equity_history.csv"


def _ensure_file(file_path, headers):
    if not os.path.exists(file_path):
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)


def log_trade(row):
    headers = [
        "timestamp_open",
        "timestamp_close",
        "symbol",
        "side",
        "entry",
        "exit",
        "amount",
        "pnl",
        "pnl_pct",
        "stop",
        "take_profit",
        "reason",
        "balance_before",
        "balance_after",
    ]
    _ensure_file(TRADE_HISTORY_FILE, headers)

    with open(TRADE_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("timestamp_open"),
            row.get("timestamp_close"),
            row.get("symbol"),
            row.get("side"),
            row.get("entry"),
            row.get("exit"),
            row.get("amount"),
            row.get("pnl"),
            row.get("pnl_pct"),
            row.get("stop"),
            row.get("take_profit"),
            row.get("reason"),
            row.get("balance_before"),
            row.get("balance_after"),
        ])


def log_equity(row):
    headers = [
        "timestamp",
        "price",
        "balance",
        "open_trade",
        "equity",
        "floating_pnl",
        "risk_mode",
    ]
    _ensure_file(EQUITY_HISTORY_FILE, headers)

    with open(EQUITY_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("timestamp"),
            row.get("price"),
            row.get("balance"),
            row.get("open_trade"),
            row.get("equity"),
            row.get("floating_pnl"),
            row.get("risk_mode"),
        ])


def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")