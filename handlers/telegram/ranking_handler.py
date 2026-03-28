from alerts.telegram_alerts import send_telegram
from engines.smart_hunt_selector import get_selected_symbol, format_ranking_message

def handle_ranking(context):
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

    msg = format_ranking_message(selector_info)
    send_telegram(msg)