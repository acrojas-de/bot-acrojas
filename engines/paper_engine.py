import json
import os


WALLET_PATH = "data/paper_wallet.json"
CONTROL_PATH = "data/control.json"


def ensure_data_dir():
    os.makedirs("data", exist_ok=True)


def load_wallet():
    with open(WALLET_PATH, "r", encoding="utf-8") as f:
        wallet = json.load(f)

    # compatibilidad con versiones antiguas
    if "open_trade" not in wallet:
        wallet["open_trade"] = None

    if "secondary_trade" not in wallet:
        wallet["secondary_trade"] = None

    if "balance" not in wallet:
        wallet["balance"] = 0.0

    return wallet   # ✅ AQUÍ


def save_wallet(wallet):
    ensure_data_dir()
    with open(WALLET_PATH, "w", encoding="utf-8") as f:
        json.dump(wallet, f, indent=2)


def load_control():
    with open(CONTROL_PATH, "r", encoding="utf-8") as f:
        control = json.load(f)

    # compatibilidad por si faltan claves
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


def calculate_initial_stop(price, side, stop_loss_pct):
    if side == "LONG":
        return round(price * (1 - stop_loss_pct / 100), 2)
    return round(price * (1 + stop_loss_pct / 100), 2)


def open_long(price):
    wallet = load_wallet()
    control = load_control()

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
    return trade


def open_short(price):
    wallet = load_wallet()
    control = load_control()

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
    return trade


def update_trade(price):
    wallet = load_wallet()
    control = load_control()
    trade = wallet.get("open_trade")

    if trade is None:
        return None

    entry = trade["entry"]
    amount = trade.get("amount", wallet["balance"])
    vibora_mode = trade.get("vibora_mode", False)

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

        return {
            "closed": True,
            "forced": True,
            "pnl": pnl,
            "exit_price": price,
        }

    trailing_enabled = control.get("trailing_stop_enabled", True)
    trailing_stop_pct = control.get("trailing_stop_pct", 0.35)
    break_even_trigger_pct = control.get("break_even_trigger_pct", 0.5)
    stop_loss_pct = control.get("stop_loss_pct", 0.6)

    if vibora_mode:
        trailing_stop_pct = min(trailing_stop_pct, 0.25)

    if trade["side"] == "LONG":
        if "highest_price" not in trade:
            trade["highest_price"] = price

        if price > trade["highest_price"]:
            trade["highest_price"] = price

        base_stop = calculate_initial_stop(entry, "LONG", stop_loss_pct)

        if trade["stop"] < base_stop:
            trade["stop"] = base_stop

        profit_pct = (price - entry) / entry * 100

        if profit_pct >= break_even_trigger_pct and trade["stop"] < entry:
            trade["stop"] = entry

        if trailing_enabled:
            trailing = round(
                trade["highest_price"] * (1 - trailing_stop_pct / 100), 2
            )
            if trailing > trade["stop"]:
                trade["stop"] = trailing

        # trailing extra inteligente
        profit_abs = price - entry
        if profit_abs > 0.3:
            factor = 0.5
            if vibora_mode:
                factor = 0.35

            new_stop = round(price - (profit_abs * factor), 2)
            if new_stop > trade["stop"]:
                trade["stop"] = new_stop

        if price <= trade["stop"]:
            pnl = (price - entry) / entry * amount
            wallet["balance"] += pnl
            wallet["open_trade"] = None
            save_wallet(wallet)

            from alerts.telegram_alerts import send_telegram

            close_reason = "🔒 Trade cerrado por stop inteligente"
            if vibora_mode:
                close_reason = "🐍 VIBORA cerró trade por stop dinámico"

            send_telegram(close_reason)

            return {
                "closed": True,
                "pnl": pnl,
                "exit_price": price,
                "stop_used": trade["stop"],
            }

    elif trade["side"] == "SHORT":
        if "lowest_price" not in trade:
            trade["lowest_price"] = price

        if price < trade["lowest_price"]:
            trade["lowest_price"] = price

        base_stop = calculate_initial_stop(entry, "SHORT", stop_loss_pct)

        if trade["stop"] > base_stop:
            trade["stop"] = base_stop

        profit_pct = (entry - price) / entry * 100

        if profit_pct >= break_even_trigger_pct and trade["stop"] > entry:
            trade["stop"] = entry

        if trailing_enabled:
            trailing = round(
                trade["lowest_price"] * (1 + trailing_stop_pct / 100), 2
            )
            if trailing < trade["stop"]:
                trade["stop"] = trailing

        # trailing extra inteligente para short
        profit_abs = entry - price
        if profit_abs > 0.3:
            factor = 0.5
            if vibora_mode:
                factor = 0.35

            new_stop = round(price + (profit_abs * factor), 2)
            if new_stop < trade["stop"]:
                trade["stop"] = new_stop

        if price >= trade["stop"]:
            pnl = (entry - price) / entry * amount
            wallet["balance"] += pnl
            wallet["open_trade"] = None
            save_wallet(wallet)

            from alerts.telegram_alerts import send_telegram

            close_reason = "🔒 Trade cerrado por stop inteligente"
            if vibora_mode:
                close_reason = "🐍 VIBORA cerró trade por stop dinámico"

            send_telegram(close_reason)

            return {
                "closed": True,
                "pnl": pnl,
                "exit_price": price,
                "stop_used": trade["stop"],
            }

    wallet["open_trade"] = trade
    save_wallet(wallet)

    return {
        "closed": False,
        "current_stop": trade["stop"],
    }

def open_long_secondary(price):
    wallet = load_wallet()
    control = load_control()

    stop_loss_pct = control.get("stop_loss_pct", 0.6)

    trade = {
        "side": "LONG",
        "entry": price,
        "amount": wallet["balance"],
        "stop": calculate_initial_stop(price, "LONG", stop_loss_pct),
        "highest_price": price,
        "status": "open",
    }

    wallet["secondary_trade"] = trade
    save_wallet(wallet)
    return trade


def open_short_secondary(price):
    wallet = load_wallet()
    control = load_control()

    stop_loss_pct = control.get("stop_loss_pct", 0.6)

    trade = {
        "side": "SHORT",
        "entry": price,
        "amount": wallet["balance"],
        "stop": calculate_initial_stop(price, "SHORT", stop_loss_pct),
        "lowest_price": price,
        "status": "open",
    }

    wallet["secondary_trade"] = trade
    save_wallet(wallet)
    return trade
