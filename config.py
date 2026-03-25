import os
from binance.client import Client


# ======================
# BINANCE CONFIG
# ======================
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

if not API_KEY or not API_SECRET:
    raise Exception("Faltan claves de Binance en variables de entorno")


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

ACTIVE_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"]

# ======================
# TELEGRAM CONFIG
# ======================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise Exception("Faltan datos de Telegram en variables de entorno")


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