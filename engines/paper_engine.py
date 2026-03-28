# ============================================================
# PAPER ENGINE - GESTIÓN DE WALLET Y TRADES
# ============================================================

import json
import os


# ============================================================
# 1) CONFIGURACIÓN DE RUTAS
# ============================================================
WALLET_PATH = "data/paper_wallet.json"
CONTROL_PATH = "data/control.json"


# ============================================================
# 2) UTILIDADES BASE (FILESYSTEM)
# ============================================================
def ensure_data_dir():
    os.makedirs("data", exist_ok=True)


# ============================================================
# 3) WALLET (CARGA / GUARDADO)
# ============================================================
def load_wallet():
    with open(WALLET_PATH, "r", encoding="utf-8") as f:
        wallet = json.load(f)

    # compatibilidad
    if "open_trade" not in wallet:
        wallet["open_trade"] = None

    if "secondary_trade" not in wallet:
        wallet["secondary_trade"] = None

    if "balance" not in wallet:
        wallet["balance"] = 0.0

    return wallet


def save_wallet(wallet):
    ensure_data_dir()
    with open(WALLET_PATH, "w", encoding="utf-8") as f:
        json.dump(wallet, f, indent=2)


# ============================================================
# 4) CONTROL (CONFIG DINÁMICA DEL BOT)
# ============================================================
def load_control():
    with open(CONTROL_PATH, "r", encoding="utf-8") as f:
        control = json.load(f)

    if "paper_trading_enabled" not in control:
        control["paper_trading_enabled"] = True

    if "allow_new_entries" not in control:
        control["allow_new_entries"] = True

    if "force_close_trade" not in control:
        control["force_close_trade"] = False

    if "trailing_stop_enabled" not in control:
        control["trailing_stop_enabled"] = True

    if "stop_loss_pct" not in control:
        control["stop_loss_pct"] = 0.6

    if "trailing_stop_pct" not in control:
        control["trailing_stop_pct"] = 0.35

    if "break_even_trigger_pct" not in control:
        control["break_even_trigger_pct"] = 0.5

    return control


def save_control(control):
    ensure_data_dir()
    with open(CONTROL_PATH, "w", encoding="utf-8") as f:
        json.dump(control, f, indent=2)


# ============================================================
# 5) UTILIDADES DE RIESGO
# ============================================================
def calculate_initial_stop(price, side, stop_loss_pct):
    if side == "LONG":
        return round(price * (1 - stop_loss_pct / 100), 2)
    return round(price * (1 + stop_loss_pct / 100), 2)


# ============================================================
# 6) APERTURA DE TRADES PRINCIPALES
# ============================================================
def open_long(price):
    wallet = load_wallet()
    control = load_control()

    print("🚀 open_long ejecutado")
    print("📦 wallet antes:", wallet)

    stop_loss_pct = control.get("stop_loss_pct", 0.6)

    trade = {
        "side": "LONG",
        "entry": price,
        "amount": wallet["balance"],
        "stop": calculate_initial_stop(price, "LONG", stop_loss_pct),
        "highest_price": price,
        "status": "open",
    }

    wallet["open_trade"] = trade
    save_wallet(wallet)

    print("📦 wallet después:", wallet)

    return trade


def open_short(price):
    wallet = load_wallet()
    control = load_control()

    print("🚀 open_short ejecutado")
    print("📦 wallet antes:", wallet)

    stop_loss_pct = control.get("stop_loss_pct", 0.6)

    trade = {
        "side": "SHORT",
        "entry": price,
        "amount": wallet["balance"],
        "stop": calculate_initial_stop(price, "SHORT", stop_loss_pct),
        "lowest_price": price,
        "status": "open",
    }

    wallet["open_trade"] = trade
    save_wallet(wallet)

    print("📦 wallet después:", wallet)

    return trade


# ============================================================
# 7) GESTIÓN DINÁMICA DEL TRADE (TRAILING / CIERRE)
# ============================================================
def update_trade(price):
    wallet = load_wallet()
    control = load_control()
    trade = wallet.get("open_trade")

    if trade is None:
        return None

    entry = trade["entry"]
    amount = trade.get("amount", wallet["balance"])
    vibora_mode = trade.get("vibora_mode", False)

    # ========================================================
    # 7.1) CIERRE FORZADO
    # ========================================================
    if control.get("force_close_trade", False):
        if trade["side"] == "LONG":
            pnl = (price - entry) / entry * amount
        else:
            pnl = (entry - price) / entry * amount

        wallet["balance"] += pnl
        wallet["open_trade"] = None

        control["force_close_trade"] = False
        save_control(control)
        save_wallet(wallet)

        return {"closed": True, "forced": True}

    # (el resto de tu lógica se queda igual 👌)