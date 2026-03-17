def trap_detector(klines):
    if len(klines) < 2:
        return "SIN DATOS"

    prev = klines[-2]
    curr = klines[-1]

    prev_low = float(prev[3])
    prev_high = float(prev[2])

    curr_low = float(curr[3])
    curr_high = float(curr[2])
    curr_close = float(curr[4])

    # barrido bajista: rompe mínimo anterior y cierra por encima
    if curr_low < prev_low and curr_close > prev_low:
        return "POSIBLE BARRIDO BAJISTA"

    # barrido alcista: rompe máximo anterior y cierra por debajo
    if curr_high > prev_high and curr_close < prev_high:
        return "POSIBLE BARRIDO ALCISTA"

    return "SIN TRAMPA CLARA"
