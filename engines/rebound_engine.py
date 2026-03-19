def rebound_entry(price, magnet_up, magnet_down, last_candle):
    """
    Devuelve:
    - "long"
    - "short"
    - None
    """

    if not magnet_up or not magnet_down:
        return None

    # Rebote hacia arriba (long)
    if price <= magnet_down:
        return "long"

    # Rebote hacia abajo (short)
    if price >= magnet_up:
        return "short"

    return None