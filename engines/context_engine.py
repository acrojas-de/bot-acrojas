def get_market_context(radar):
    buy_count = list(radar.values()).count("BUY")
    sell_count = list(radar.values()).count("SELL")

    if radar.get("1h") == "SELL" and radar.get("4h") == "SELL":
        return "bearish"

    if radar.get("1h") == "BUY" and radar.get("4h") == "BUY":
        return "bullish"

    if sell_count > buy_count:
        return "bearish"

    if buy_count > sell_count:
        return "bullish"

    return "neutral"