from alerts.telegram_alerts import send_telegram
from engines.trade_registry import get_all_trades, close_trade


def handle_trades(context):
    trades = get_all_trades()

    if not trades:
        send_telegram("📭 No hay trades abiertos")
        return True

    msg = "📂 TRADES ABIERTOS\n\n"

    for i, t in enumerate(trades, 1):
        msg += (
            f"{i}. {t['symbol']} | {t['side']} | "
            f"Entrada: {t['entry']:.2f}\n"
        )

    msg += "\n👉 Usa /close 1 para cerrar"

    send_telegram(msg)
    return True


def handle_close(context):
    raw_cmd = context.get("raw_cmd", "")
    parts = raw_cmd.split()

    if len(parts) < 2:
        send_telegram("❌ Usa: /close 1")
        return True

    try:
        idx = int(parts[1]) - 1
    except:
        send_telegram("❌ Índice inválido")
        return True

    trades = get_all_trades()

    if idx < 0 or idx >= len(trades):
        send_telegram("❌ Índice fuera de rango")
        return True

    trade = trades[idx]

    close_trade(trade["id"])

    send_telegram(f"❌ Trade cerrado: {trade['symbol']}")
    return True
    
    