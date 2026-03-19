from indicators.ema_rsi import ema


def pullback_zone(klines, tolerance_ema21=0.0025, tolerance_ema50=0.004):
    closes = [float(k[4]) for k in klines]

    if len(closes) < 50:
        return {
            "near_ema21": False,
            "near_ema50": False,
            "ema21": None,
            "ema50": None,
            "price": closes[-1] if closes else None,
        }

    price = closes[-1]
    ema21 = ema(closes, 21)[-1]
    ema50 = ema(closes, 50)[-1]

    near_ema21 = abs(price - ema21) / price <= tolerance_ema21
    near_ema50 = abs(price - ema50) / price <= tolerance_ema50

    return {
        "near_ema21": near_ema21,
        "near_ema50": near_ema50,
        "ema21": ema21,
        "ema50": ema50,
        "price": price,
    }