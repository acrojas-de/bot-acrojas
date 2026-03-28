from alerts.telegram_alerts import send_telegram

def handle_select(context):
    raw_cmd = context.get("raw_cmd", "")
    watchlist = context.get("watchlist", [])
    
    parts = raw_cmd.split()

    if len(parts) < 2:
        send_telegram("❌ Usa: /select 1 o /select BTCUSDT")
        return None

    arg = parts[1].upper()

    # Caso 1: número del ranking
    if arg.isdigit():
        idx = int(arg) - 1

        if idx < 0 or idx >= len(watchlist):
            send_telegram("❌ Índice fuera de rango")
            return None

        selected_symbol = watchlist[idx]

    # Caso 2: símbolo directo
    else:
        selected_symbol = arg

    send_telegram(f"🎯 Activo seleccionado manualmente: {selected_symbol}")
    return selected_symbol