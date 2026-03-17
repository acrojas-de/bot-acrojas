def calculate_drawdown(capital_base, current_balance):
    return round(current_balance - capital_base, 2)


def should_pause_by_loss(capital_base, current_balance, max_loss_allowed):
    loss = capital_base - current_balance
    return loss >= max_loss_allowed


def should_alert_profit(capital_base, current_balance, min_profit_alert):
    profit = current_balance - capital_base
    return profit >= min_profit_alert


def risk_status(capital_base, current_balance, max_loss_allowed, min_profit_alert):
    diff = round(current_balance - capital_base, 2)

    if diff >= min_profit_alert:
        return "PROFIT_ALERT", diff

    if (capital_base - current_balance) >= max_loss_allowed:
        return "LOSS_ALERT", diff

    return "NORMAL", diff


def calculate_stop_price(entry_price, side, stop_loss_pct):
    if side == "LONG":
        return round(entry_price * (1 - stop_loss_pct / 100), 2)
    return round(entry_price * (1 + stop_loss_pct / 100), 2)


def calculate_trailing_stop(current_price, side, trailing_stop_pct):
    if side == "LONG":
        return round(current_price * (1 - trailing_stop_pct / 100), 2)
    return round(current_price * (1 + trailing_stop_pct / 100), 2)


def get_active_stop(trade, current_price, control):
    stop_loss_pct = control.get("stop_loss_pct", 1.2)
    trailing_enabled = control.get("trailing_stop_enabled", True)
    trailing_stop_pct = control.get("trailing_stop_pct", 0.8)

    entry_price = trade["entry"]
    side = trade["side"]

    base_stop = calculate_stop_price(entry_price, side, stop_loss_pct)

    if not trailing_enabled:
        return base_stop

    trailing_stop = calculate_trailing_stop(current_price, side, trailing_stop_pct)

    if side == "LONG":
        return max(base_stop, trailing_stop)
    return min(base_stop, trailing_stop)