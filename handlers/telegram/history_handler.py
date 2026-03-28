from alerts.telegram_alerts import send_telegram
from engines.paper_engine import load_wallet

def handle_history(context):
    wallet_live = load_wallet()
    history = wallet_live.get("history", [])

    if not history:
        send_telegram("📭 No hay historial de operaciones")
        return

    msg = "📜 HISTORIAL\n\n"
    for i, trade_item in enumerate(history[-5:], 1):
        msg += (
            f"{i}. {trade_item.get('side', '-')}"
            f" | Entrada: {trade_item.get('entry', 0):.2f}"
            f" | Salida: {trade_item.get('exit', 0):.2f}"
            f" | PnL: {trade_item.get('pnl', 0):.2f}\n"
        )

    send_telegram(msg)