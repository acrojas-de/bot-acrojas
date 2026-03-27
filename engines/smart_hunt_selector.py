from engines.compression_engine import compression_signal
from engines.signal_engine import build_signal


def _safe_close(klines, idx=-1):
    return float(klines[idx][4])


def _bias_from_klines(klines):
    if len(klines) < 20:
        return "neutral"

    first = float(klines[0][4])
    last = float(klines[-1][4])

    if last > first:
        return "bullish"
    elif last < first:
        return "bearish"
    return "neutral"


def _trigger_5m(klines_5m):
    if len(klines_5m) < 2:
        return "wait"

    prev_close = _safe_close(klines_5m, -2)
    last_close = _safe_close(klines_5m, -1)

    if last_close > prev_close:
        return "long"
    elif last_close < prev_close:
        return "short"
    return "wait"


def _score_candidate(symbol, klines_map):
    score = 0
    reasons = []

    bias_1d = _bias_from_klines(klines_map["1D"])
    bias_4h = _bias_from_klines(klines_map["4H"])
    trigger_5m = _trigger_5m(klines_map["5m"])

    price = float(klines_map["5m"][-1][4])
    signal = build_signal(price, klines_map)
    compression = compression_signal(klines_map["15m"])

    strength = signal.get("strength", "")
    structure = signal.get("structure", "")
    market_read = signal.get("interpretation", "")

    if bias_1d == bias_4h and bias_1d != "neutral":
        score += 3
        reasons.append(f"HTF aligned: {bias_1d}")

    if bias_1d == "bullish" and trigger_5m == "long":
        score += 3
        reasons.append("1D + 5m long")
    elif bias_1d == "bearish" and trigger_5m == "short":
        score += 3
        reasons.append("1D + 5m short")

    if compression == "alta":
        score += 2
        reasons.append("compression alta")
    elif compression == "media":
        score += 1
        reasons.append("compression media")

    if "FUERTE" in strength:
        score += 2
        reasons.append("fuerza fuerte")
    elif "MODERADA" in strength:
        score += 1
        reasons.append("fuerza moderada")

    if structure.startswith("📈") and bias_1d == "bullish":
        score += 1
        reasons.append("estructura alcista")
    elif structure.startswith("📉") and bias_1d == "bearish":
        score += 1
        reasons.append("estructura bajista")

    if "INDECISO" in market_read:
        score -= 2
        reasons.append("mercado indeciso")

    if structure.startswith("⚖️"):
        score -= 2
        reasons.append("estructura lateral")

    return {
        "symbol": symbol,
        "score": score,
        "bias_1d": bias_1d,
        "bias_4h": bias_4h,
        "trigger_5m": trigger_5m,
        "compression": compression,
        "strength": strength,
        "structure": structure,
        "reading": market_read,
        "reasons": reasons,
    }


def get_selected_symbol(
    client,
    watchlist,
    default_symbol,
    manual_symbol=None,
    klines_limit=120,
    min_score=4,
):
    if manual_symbol:
        clean = manual_symbol.strip().upper()
        if clean:
            return clean, {"mode": "manual", "symbol": clean}

    ranking = []

    for symbol in watchlist:
        try:
            klines_map = {
                "5m": client.get_klines(symbol=symbol, interval="5m", limit=klines_limit),
                "15m": client.get_klines(symbol=symbol, interval="15m", limit=klines_limit),
                "1h": client.get_klines(symbol=symbol, interval="1h", limit=klines_limit),
                "4H": client.get_klines(symbol=symbol, interval="4h", limit=klines_limit),
                "1D": client.get_klines(symbol=symbol, interval="1d", limit=klines_limit),
            }

            candidate = _score_candidate(symbol, klines_map)
            ranking.append(candidate)

        except Exception as e:
            ranking.append(
                {
                    "symbol": symbol,
                    "score": -999,
                    "error": str(e),
                    "reasons": [f"error: {e}"],
                }
            )

    ranking.sort(key=lambda x: x["score"], reverse=True)
    best = ranking[0] if ranking else None

    print("\n📊 SELECTOR RANKING")
    for r in ranking:
        print(
            f"{r['symbol']} | score={r['score']} | "
            f"1D={r.get('bias_1d')} | 4H={r.get('bias_4h')} | "
            f"5m={r.get('trigger_5m')} | comp={r.get('compression')} | "
            f"strength={r.get('strength')} | structure={r.get('structure')} | "
            f"reasons={r.get('reasons')}"
        )

    if not best or best["score"] < min_score:
        return default_symbol, {
            "mode": "fallback",
            "symbol": default_symbol,
            "ranking": ranking,
            "reason": f"ningún activo supera min_score={min_score}",
        }

    return best["symbol"], {
        "mode": "auto",
        "symbol": best["symbol"],
        "ranking": ranking,
        "best": best,
    }
    
def format_ranking_message(selector_info):
    ranking = selector_info.get("ranking", [])
    mode = selector_info.get("mode")
    symbol = selector_info.get("symbol")

    msg = "📊 RANKING WATCHLIST\n\n"

    for i, r in enumerate(ranking[:5], 1):
        msg += f"{i}. {r['symbol']} → {r['score']}\n"
        reasons = r.get("reasons", [])
        for reason in reasons:
            msg += f"   - {reason}\n"
        msg += "\n"

    msg += f"🧠 Modo: {mode}\n"
    msg += f"🎯 Activo actual: {symbol}\n"

    return msg    