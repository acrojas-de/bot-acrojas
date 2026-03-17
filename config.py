from binance.client import Client
import os

# ======================
# BINANCE CONFIG
# ======================

API_KEY = "TU_API_KEY"
API_SECRET = "TU_API_SECRET"

SYMBOL = "BTCUSDT"

ALL_TIMEFRAMES = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "3m": Client.KLINE_INTERVAL_3MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "30m": Client.KLINE_INTERVAL_30MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
    "4h": Client.KLINE_INTERVAL_4HOUR,
    "1D": Client.KLINE_INTERVAL_1DAY,
    "1W": Client.KLINE_INTERVAL_1WEEK
}

ACTIVE_TIMEFRAMES = ["5m", "15m", "1h", "4h", "1D"]

# ======================
# TELEGRAM CONFIG
# ======================

TELEGRAM_TOKEN = "TU_TELEGRAM_TOKEN"
CHAT_ID = "TU_CHAT_ID"

# ======================
# BOT CONFIG
# ======================

UPDATE_INTERVAL = 60

# ======================
# RISK CONFIG
# ======================

CAPITAL_BASE = 1000.0
MAX_LOSS_ALLOWED = -50.0
MIN_PROFIT_ALERT = 20.0

# -----------------------
# BOT MODE
# -----------------------

BOT_MODE = "TEST_5M"          # TEST_5M o RADAR
TRADE_MODE = "MANUAL_SPOT"    # MANUAL_SPOT o AUTO_LEVERAGE
