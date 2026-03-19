from indicators.ema_rsi import ema


def get_htf_bias(klines_4h):
    """
    Analiza la estructura de 4H (High Time Frame)
    Devuelve:
    - LONG_ONLY
    - SHORT_ONLY
    - WAIT
    """

    closes = [float(k[4]) for k in klines_4h]

    if len(closes) < 50:
        return "WAIT"

    ema21 = ema(closes, 21)[-1]
    ema50 = ema(closes, 50)[-1]

    # Estructura básica
    if ema21 > ema50:
        return "LONG_ONLY"

    elif ema21 < ema50:
        return "SHORT_ONLY"

    return "WAIT"