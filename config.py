from binance.client import Client
import os

# ======================
# BINANCE CONFIG
# ======================

API_KEY = "tuPPjvoVE67BfyVtLJwGzknRTfhDDd9cM7HPHgpI7f4DD2UOmDDyWv5gj3KgKhZt"
API_SECRET = "1OZKiduwN8qzRLJ4eGeiHcYG9IZei5y1bBlfD221vC0I4zFJWKmGObNUTpmJW1Xf"

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

TELEGRAM_TOKEN = "8400052557:AAEi4rYT9AsN9z0yzQLWbFJbZuetKELv9KY"
CHAT_ID = "5221399837"

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
# NUEVO MODO INTELIGENTE
SMART_MODE = True