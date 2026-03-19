def is_compression(closes, threshold=0.002):
    """
    Detecta si el mercado está comprimido (rango muy pequeño)
    """
    if len(closes) < 10:
        return False

    rango = max(closes[-10:]) - min(closes[-10:])
    return (rango / closes[-1]) < threshold


def is_explosion(last_candle, threshold=0.0015):
    """
    Detecta vela fuerte (explosión)
    """
    open_price = float(last_candle[1])
    close_price = float(last_candle[4])

    body = abs(close_price - open_price)

    return (body / open_price) > threshold


def compression_signal(klines_1h):
    """
    Combina compresión + explosión
    """
    closes = [float(k[4]) for k in klines_1h]

    if is_compression(closes):
        last_candle = klines_1h[-1]

        if is_explosion(last_candle):
            open_price = float(last_candle[1])
            close_price = float(last_candle[4])

            if close_price > open_price:
                return "LONG_BREAKOUT"
            else:
                return "SHORT_BREAKOUT"

    return None