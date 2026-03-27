from engines.htf_bias_engine import get_htf_bias
from engines.compression_engine import compression_signal
from engines.rebound_engine import rebound_entry
from engines.sniper_entry import sniper_entry
from engines.vibora_engine import ViboraEngine
from engines.risk_manager import risk_status
from engines.signal_engine import build_signal

vibora = ViboraEngine(config=None)


def run_orbita_scan(symbol, klines_map):

    # =========================
    # 1. CONTEXTO MTF
    # =========================
    bias = get_htf_bias(klines_map)

    # =========================
    # 2. ESTRUCTURA
    # =========================
    compression = compression_signal(klines_map)
    rebound = rebound_entry(klines_map)

    # =========================
    # 3. SEÑALES
    # =========================
    sniper = sniper_entry(klines_map)
    vibora_signal = vibora.check(klines_map)

    # =========================
    # 4. RIESGO
    # =========================
    risk = risk_status(klines_map)

    # =========================
    # 5. SCORE (simple v1)
    # =========================
    score = 0

    if bias == "bullish":
        score += 2
    if compression:
        score += 2
    if sniper:
        score += 3
    if vibora_signal:
        score += 2

    # =========================
    # 6. ESTADO
    # =========================
    if score >= 7:
        state = "🟢 Listo"
    elif score >= 4:
        state = "🟡 En órbita"
    else:
        state = "🔴 Frío"

    return {
        "bias": bias,
        "compression": compression,
        "rebound": rebound,
        "sniper": sniper,
        "vibora": vibora_signal,
        "risk": risk,
        "score": score,
        "state": state,
    }