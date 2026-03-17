def market_structure(klines):
    if len(klines) < 6:
        return "SIN DATOS"

    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    last_high = highs[-1]
    prev_high = highs[-5]

    last_low = lows[-1]
    prev_low = lows[-5]

    if last_high > prev_high and last_low > prev_low:
        return "📈 TENDENCIA ALCISTA"

    if last_high < prev_high and last_low < prev_low:
        return "📉 TENDENCIA BAJISTA"

    if last_high > prev_high and last_low < prev_low:
        return "⚠️ POSIBLE GIRO"

    return "⚖️ LATERAL"


def market_state(rsi_map):
    r5 = rsi_map["5m"]
    r15 = rsi_map["15m"]

    if r5 >= 80 or r15 >= 80:
        return "⚠️ SOBRECOMPRADO (corto plazo)"

    if r5 <= 20 or r15 <= 20:
        return "⚠️ SOBREVENTA (corto plazo)"

    if r5 >= 70 or r15 >= 70:
        return "🌡️ MERCADO EXTENDIDO"

    if r5 <= 35:
        return "🧊 DESCARGA DEL MERCADO"

    return "🔥 IMPULSO SANO"
