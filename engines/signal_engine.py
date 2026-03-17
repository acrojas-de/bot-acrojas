from indicators.ema_rsi import ema, rsi
from indicators.trap_detector import trap_detector
from indicators.market_structure import market_structure, market_state
from indicators.liquidity import liquidity_levels, liquidity_target, probable_target


def interpret(radar):

    if radar["5m"] == "SELL" and radar["15m"] == "BUY" and radar["1h"] == "BUY":
        return "🔧 CORRECCIÓN DENTRO DE TENDENCIA"

    if radar["5m"] == "BUY" and radar["15m"] == "BUY" and radar["1h"] == "BUY" and radar["4h"] == "BUY":
        return "🔥 ALINEACIÓN ALCISTA"

    if radar["5m"] == "SELL" and radar["15m"] == "SELL" and radar["1h"] == "SELL":
        return "⚠️ POSIBLE GIRO BAJISTA"

    return "⚖️ MERCADO INDECISO"


def signal_strength(radar):

    buy_count = list(radar.values()).count("BUY")
    sell_count = list(radar.values()).count("SELL")

    if buy_count >= 4:
        return "💪 BUY FUERTE"

    if sell_count >= 4:
        return "💥 SELL FUERTE"

    if buy_count > sell_count:
        return "📈 BUY MODERADO"

    if sell_count > buy_count:
        return "📉 SELL MODERADO"

    return "⚖️ NEUTRAL"


def rebound_probability(radar, rsi_map):

    if (
        radar["5m"] == "SELL"
        and radar["15m"] == "BUY"
        and radar["1h"] == "BUY"
        and rsi_map["5m"] < 30
    ):
        return "ALTO"

    if radar["5m"] == "SELL" and rsi_map["5m"] < 35:
        return "MEDIO"

    return "BAJO"


def build_signal(price, klines_map):

    radar = {}
    rsi_map = {}

    for tf, klines in klines_map.items():

        closes = [float(k[4]) for k in klines]

        ema21 = ema(closes, 21)[-1]
        ema50 = ema(closes, 50)[-1]

        rsi_val = rsi(closes)

        signal = "BUY" if ema21 > ema50 else "SELL"

        radar[tf] = signal
        rsi_map[tf] = round(rsi_val, 1)

    interpretation = interpret(radar)
    strength = signal_strength(radar)
    rebound = rebound_probability(radar, rsi_map)

    trap = trap_detector(klines_map["5m"])

    structure = market_structure(klines_map["1h"])
    state_market = market_state(rsi_map)

    magnet_up, magnet_down = liquidity_levels(klines_map["1h"])

    target = probable_target(price, radar)

    liq_target = liquidity_target(price, magnet_up, magnet_down)

    return {
        "radar": radar,
        "rsi": rsi_map,
        "interpretation": interpretation,
        "strength": strength,
        "rebound": rebound,
        "trap": trap,
        "structure": structure,
        "state_market": state_market,
        "magnet_up": magnet_up,
        "magnet_down": magnet_down,
        "target": target,
        "liq_target": liq_target
    }
