from alerts.telegram_alerts import send_telegram
from engines.paper_engine import load_wallet
from datetime import datetime, timedelta


def _parse_timestamp(ts):
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            pass

    return None


def handle_history(context):
    raw_cmd = context.get("raw_cmd", "").strip()
    wallet_live = load_wallet()
    history = wallet_live.get("history", [])

    if not history:
        send_telegram("📭 No hay historial de operaciones")
        return

    parts = raw_cmd.split()

    filtered = history[:]

    # Caso 1: /history 3  -> últimos 3 días
    if len(parts) == 2 and parts[1].isdigit():
        days = int(parts[1])
        cutoff = datetime.now() - timedelta(days=days)

        filtered = []
        for trade in history:
            ts = trade.get("timestamp")
            if not ts:
                continue

            dt = _parse_timestamp(ts)
            if dt and dt >= cutoff:
                filtered.append(trade)

    # Caso 2: /history 2026-03-01 2026-03-28 -> rango exacto
    elif len(parts) == 3:
        try:
            start_date = datetime.strptime(parts[1], "%Y-%m-%d")
            end_date = datetime.strptime(parts[2], "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )

            filtered = []
            for trade in history:
                ts = trade.get("timestamp")
                if not ts:
                    continue

                dt = _parse_timestamp(ts)
                if dt and start_date <= dt <= end_date:
                    filtered.append(trade)

        except Exception:
            send_telegram(
                "❌ Formato inválido.\n\n"
                "Usa:\n"
                "/history\n"
                "/history 3\n"
                "/history 2026-03-01 2026-03-28"
            )
            return

    # Si no hay filtro, muestra últimas 5
    elif len(parts) == 1:
        filtered = history[-5:]

    else:
        send_telegram(
            "❌ Formato inválido.\n\n"
            "Usa:\n"
            "/history\n"
            "/history 3\n"
            "/history 2026-03-01 2026-03-28"
        )
        return

    if not filtered:
        send_telegram("📭 No hay operaciones para ese rango")
        return

    msg = "📜 HISTORIAL\n\n"

    # mostramos las últimas 10 del filtro
    for i, trade_item in enumerate(filtered[-10:], 1):
        ts = trade_item.get("timestamp", "sin fecha")
        msg += (
            f"{i}. {trade_item.get('side', '-')}"
            f" | Entrada: {trade_item.get('entry', 0):.2f}"
            f" | Salida: {trade_item.get('exit', 0):.2f}"
            f" | PnL: {trade_item.get('pnl', 0):.2f}\n"
            f"   Fecha: {ts}\n"
        )

    send_telegram(msg)