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


def strong_bearish_close(candle):
    body = candle["open"] - candle["close"]
    rng = candle["high"] - candle["low"]

    if rng <= 0:
        return False

    return candle["close"] < candle["open"] and (body / rng) >= 0.45


def strong_bullish_close(candle):
    body = candle["close"] - candle["open"]
    rng = candle["high"] - candle["low"]

    if rng <= 0:
        return False

    return candle["close"] > candle["open"] and (body / rng) >= 0.45


def sniper_entry(context, setup_5m, trap, last_candle, bias_4h=None, compression=None):
    near_ema21 = setup_5m.get("near_ema21", False)
    near_ema50 = setup_5m.get("near_ema50", False)
    near_zone = near_ema21 or near_ema50

    if not near_zone:
        return None

    # filtro de bias HTF
    allow_long = bias_4h in (None, "LONG_ONLY", "BULLISH", "UP", "ALCISTA")
    allow_short = bias_4h in (None, "SHORT_ONLY", "BEARISH", "DOWN", "BAJISTA")

    # filtro de compresión: evita entrar si aprieta en contra
    compression_block_long = compression in ("SELL", "SHORT", "BEARISH")
    compression_block_short = compression in ("BUY", "LONG", "BULLISH")

    # SHORT sólido
    if context == "bearish" and allow_short:
        if trap == "POSIBLE BARRIDO ALCISTA":
            return None
        if compression_block_short:
            return None

        if near_ema21:
            if bearish_rejection_candle(last_candle) or strong_bearish_close(last_candle):
                return "short"

        if near_ema50:
            if bearish_rejection_candle(last_candle):
                return "short"

    # LONG sólido
    if context == "bullish" and allow_long:
        if trap == "POSIBLE BARRIDO BAJISTA":
            return None
        if compression_block_long:
            return None

        if near_ema21:
            if bullish_rejection_candle(last_candle) or strong_bullish_close(last_candle):
                return "long"

        if near_ema50:
            if bullish_rejection_candle(last_candle):
                return "long"

    return None