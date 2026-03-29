# =========================
# TRADE FACTORY
# =========================
def new_trade(
    trade_id,
    symbol,
    side,
    entry,
    amount,
    stop,
    take_profit,
    mode="manual",
):
    return {
        "id": trade_id,
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "amount": amount,
        "stop": stop,
        "take_profit": take_profit,
        "mode": mode,
        "status": "open",
    }


# =========================
# REGISTRY (PARKING)
# =========================
open_trades = []
_next_id = 1


# =========================
# CREATE TRADE
# =========================
def create_trade(symbol, side, entry, amount, stop, take_profit, mode="manual"):
    global _next_id

    trade = new_trade(
        trade_id=_next_id,
        symbol=symbol,
        side=side,
        entry=entry,
        amount=amount,
        stop=stop,
        take_profit=take_profit,
        mode=mode,
    )

    open_trades.append(trade)
    _next_id += 1

    return trade


# =========================
# GET OPEN TRADES
# =========================
def get_open_trades():
    return [t for t in open_trades if t["status"] == "open"]


# =========================
# GET TRADE BY ID
# =========================
def get_trade_by_id(trade_id):
    for t in open_trades:
        if t["id"] == trade_id:
            return t
    return None


# =========================
# CLOSE TRADE
# =========================
def close_trade(trade_id, exit_price, pnl):
    trade = get_trade_by_id(trade_id)

    if not trade:
        return None

    trade["status"] = "closed"
    trade["exit"] = exit_price
    trade["pnl"] = pnl

    return trade
    
# =========================
# GET ALL TRADES
# =========================
def get_all_trades():
    return open_trades


# =========================
# CLOSE TRADE
# =========================
def close_trade(trade_id):
    trade = get_trade_by_id(trade_id)

    if not trade:
        return None

    trade["status"] = "closed"
    return trade