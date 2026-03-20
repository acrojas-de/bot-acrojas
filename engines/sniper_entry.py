def get_last_candle(klines):
    k = klines[-1]
    return {
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
    }


def bearish_rejection_candle(candle):
    body = abs(candle["close"] - candle["open"])
    upper_wick = candle["high"] - max(candle["open"], candle["close"])

    if body == 0:
        body = 0.0001

    return upper_wick > body * 1.5


def bullish_rejection_candle(candle):
    body = abs(candle["close"] - candle["open"])
    lower_wick = min(candle["open"], candle["close"]) - candle["low"]

    if body == 0:
        body = 0.0001

    return lower_wick > body * 1.5

def sniper_entry(context, setup_5m, trap, last_candle, bias_4h=None, compression=None):
    print("ZZZ ACROJAS NUEVO 777", bias_4h)
    near_zone = setup_5m["near_ema21"] or setup_5m["near_ema50"]

    if not near_zone:
        return None

    if context == "bearish":
        if trap == "POSIBLE BARRIDO ALCISTA":
            return None
        if bearish_rejection_candle(last_candle):
            return "short"

    if context == "bullish":
        if trap == "POSIBLE BARRIDO BAJISTA":
            return None
        if bullish_rejection_candle(last_candle):
            return "long"

    return None