from alerts.telegram_alerts import send_telegram
from engines.smart_hunt_selector import get_selected_symbol, format_ranking_message

# 🔥 VARIABLE GLOBAL
LAST_RANKING = []

def handle_ranking(context):
    global LAST_RANKING

    client = context["client"]
    watchlist = context["watchlist"]
    default_symbol = context["default_symbol"]
    manual_symbol = context["manual_symbol"]

    _, selector_info = get_selected_symbol(
        client=client,
        watchlist=watchlist,
        default_symbol=default_symbol,
        manual_symbol=manual_symbol,
    )

    # 🔥 GUARDAMOS EL RANKING REAL
    LAST_RANKING = selector_info.get("ranking", [])

    msg = format_ranking_message(selector_info)

    # 🔥 añadimos instrucciones
    msg += "\n\nSelecciona:\n"
    for i, item in enumerate(LAST_RANKING[:5], start=1):
        msg += f"{i} → {item['symbol']}\n"

    send_telegram(msg)