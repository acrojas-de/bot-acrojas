def is_compression(closes, threshold=0.002):
    """
    Detecta si el mercado está comprimido (rango pequeño)
    """
    if len(closes) < 10:
        return False

    rango = max(closes[-10:]) - min(closes[-10:])
    return (rango / closes[-1]) < threshold


def is_explosion(last_candle, threshold=0.0015):
    """
    Detecta si la última vela tiene cuerpo fuerte
    """
    open_price = float(last_candle[1])
    close_price = float(last_candle[4])

    body = abs(close_price - open_price)
    return (body / open_price) > threshold


def compression_signal(klines_1h):
    """
    Devuelve nivel de compresión compatible con bot_main:
    - 'alta'
    - 'media'
    - 'baja'
    """
    try:
        if not klines_1h or len(klines_1h) < 10:
            return "baja"

        closes = [float(k[4]) for k in klines_1h]
        last_candle = klines_1h[-1]

        compressed = is_compression(closes)
        explosive = is_explosion(last_candle)

        if compressed and explosive:
            return "alta"
        elif compressed:
            return "media"
        else:
            return "baja"

    except Exception as e:
        print("Error compression_signal:", e)
        return "baja"