def liquidity_levels(klines):
    if len(klines) < 2:
        return None, None

    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    magnet_up = max(highs[:-1])
    magnet_down = min(lows[:-1])

    return round(magnet_up, 2), round(magnet_down, 2)


def liquidity_target(price, magnet_up, magnet_down):
    if magnet_up is None or magnet_down is None:
        return "SIN DATOS"

    dist_up = abs(magnet_up - price)
    dist_down = abs(price - magnet_down)

    if dist_up < dist_down:
        return "ARRIBA"
    elif dist_down < dist_up:
        return "ABAJO"
    return "EQUILIBRIO"


def probable_target(price, radar):
    if radar["5m"] == "SELL" and radar["15m"] == "BUY":
        return round(price * 1.003, 2)

    if radar["5m"] == "BUY" and radar["15m"] == "BUY" and radar["1h"] == "BUY":
        return round(price * 1.006, 2)

    if radar["5m"] == "SELL" and radar["15m"] == "SELL":
        return round(price * 0.994, 2)

    return round(price, 2)
