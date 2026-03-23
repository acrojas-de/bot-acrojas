from binance.client import Client

from alerts.telegram_alerts import (
    send_welcome_panel,
    send_telegram,
    read_telegram_commands,
)

from engines.htf_bias_engine import get_htf_bias
from engines.compression_engine import compression_signal
from engines.rebound_engine import rebound_entry
from utils.history_logger import log_trade, log_equity, now_str

import time

print("🔥 BOT_ACROJAS BUILD NUEVA - sniper fix OK 🔥")

WATCHLIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
]

from config import (
    API_KEY,
    API_SECRET,
    SYMBOL,
    ALL_TIMEFRAMES,
    ACTIVE_TIMEFRAMES,
    UPDATE_INTERVAL,
    BOT_MODE,
    TRADE_MODE,
)
from config import CAPITAL_BASE, MAX_LOSS_ALLOWED, MIN_PROFIT_ALERT
from engines.risk_manager import risk_status
from engines.signal_engine import build_signal
from engines.context_engine import get_market_context
from engines.pullback_engine import pullback_zone
from engines.sniper_entry import get_last_candle, sniper_entry
from engines.paper_engine import (
    open_long,
    open_short,
    open_long_secondary,
    open_short_secondary,
    update_trade,
    load_wallet,
    load_control,
    save_wallet,
    save_control,
)

client = Client(API_KEY, API_SECRET)


def get_klines(interval, limit=120):
    return client.get_klines(
        symbol=SYMBOL,
        interval=interval,
        limit=limit,
    )


def analyze_symbol(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval="15m", limit=50)
        closes = [float(k[4]) for k in klines]

        if len(closes) < 20:
            return None

        last = closes[-1]
        avg = sum(closes[-20:]) / 20

        if last > avg:
            return "BUY"
        else:
            return "SELL"

    except Exception:
        return None


def get_account_balances():
    account = client.get_account()
    balances = {}

    for b in account["balances"]:
        free_amt = float(b["free"])
        locked_amt = float(b["locked"])
        total_amt = free_amt + locked_amt

        if total_amt > 0:
            balances[b["asset"]] = {
                "free": free_amt,
                "locked": locked_amt,
                "total": total_amt,
            }

    return balances


def get_asset_usdt_value(asset, amount):
    if amount <= 0:
        return 0.0

    if asset == "USDT":
        return amount

    if asset == "USDC":
        return amount

    if asset == "BUSD":
        return amount

    if asset == "EUR":
        try:
            ticker = client.get_symbol_ticker(symbol="EURUSDT")
            return amount * float(ticker["price"])
        except Exception:
            return amount

    try:
        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
        return amount * float(ticker["price"])
    except Exception:
        pass

    try:
        ticker = client.get_symbol_ticker(symbol=f"USDT{asset}")
        price = float(ticker["price"])
        if price > 0:
            return amount / price
    except Exception:
        pass

    return 0.0


def get_real_balance(asset="USDT"):
    balances = get_account_balances()
    if asset in balances:
        return balances[asset]["free"]
    return 0.0


def get_balance():
    wallet = load_wallet()
    return wallet["balance"]


def simulate_entry(asset):
    try:
        symbol = f"{asset}USDT"

        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker["price"])

        balances = get_account_balances()

        usdt_available = 0

        if "USDT" in balances:
            usdt_available += float(balances["USDT"]["free"])

        if "USDC" in balances:
            usdt_available += float(balances["USDC"]["free"])

        if usdt_available <= 0:
            return "❌ No tienes saldo disponible"

        capital = usdt_available * 0.2
        quantity = capital / price
        stop_price = price * 0.98

        return (
            f"🚀 ENTRADA SIMULADA\n\n"
            f"Activo: {symbol}\n"
            f"Precio entrada: {price:.2f}\n"
            f"Capital usado: {capital:.2f} USDT\n"
            f"Cantidad: {quantity:.6f}\n"
            f"Stop: {stop_price:.2f}\n"
            f"Modo: TEST (no ejecutado)"
        )

    except Exception as e:
        return f"❌ Error entrada: {e}"


print("🛰️ ACROJAS BTC BOT iniciado")

send_welcome_panel()

print("⏱️ Timeframes activos:", ", ".join(ACTIVE_TIMEFRAMES))
print("🧠 Modo bot:", BOT_MODE)
print("🛠️ Modo gestión:", TRADE_MODE)

current_trade_mode = TRADE_MODE

last_state = None
last_update_id = None
manual_order_state = None
manual_order_data = {}
risk_state = None
risk_data = {}

last_market_run = 0
cached_price = None
cached_signal = None
cached_risk_mode = None
cached_capital_diff = None
cached_klines_map = {}

while True:
    try:
        # =========================
        # TELEGRAM: revisión rápida
        # =========================
        commands, last_update_id = read_telegram_commands(last_update_id)

        if not commands:
            commands = []

        # =========================
        # MERCADO: solo refresca cada UPDATE_INTERVAL
        # =========================
        price = cached_price
        signal = cached_signal
        risk_mode = cached_risk_mode
        capital_diff = cached_capital_diff
        klines_map = cached_klines_map

        now = time.time()
        if now - last_market_run >= UPDATE_INTERVAL or cached_signal is None:
            ticker = client.get_symbol_ticker(symbol=SYMBOL)
            price = float(ticker["price"])

            wallet_live = load_wallet()
            current_balance = wallet_live["balance"]
            trade_live = wallet_live.get("open_trade")

            floating_pnl_amount = 0.0

            if trade_live:
                live_entry = trade_live["entry"]
                live_side = trade_live["side"]
                live_amount = trade_live.get("amount", current_balance)

                if live_side == "LONG":
                    live_pnl_pct = (price - live_entry) / live_entry * 100
                else:
                    live_pnl_pct = (live_entry - price) / live_entry * 100

                floating_pnl_amount = live_amount * (live_pnl_pct / 100)

            equity_estimate = current_balance + floating_pnl_amount

            log_equity({
                "timestamp": now_str(),
                "price": price,
                "balance": current_balance,
                "open_trade": "YES" if trade_live else "NO",
                "equity": equity_estimate,
                "floating_pnl": floating_pnl_amount,
                "risk_mode": risk_mode if 'risk_mode' in locals() else None,
            })

            klines_map = {}
            for tf in ACTIVE_TIMEFRAMES:
                interval = ALL_TIMEFRAMES[tf]
                klines_map[tf] = get_klines(interval)

            bias_4h = get_htf_bias(klines_map["4h"])
            compression = compression_signal(klines_map["1h"])

            signal = build_signal(price, klines_map)

            risk_mode, capital_diff = risk_status(
                CAPITAL_BASE,
                equity_estimate,
                MAX_LOSS_ALLOWED,
                MIN_PROFIT_ALERT,
            )

            cached_price = price
            cached_signal = signal
            cached_risk_mode = risk_mode
            cached_capital_diff = capital_diff
            cached_klines_map = klines_map
            last_market_run = now

        radar = signal["radar"]
        rsi_map = signal["rsi"]
        ema_map = signal.get("ema_map", {})
        interpretation = signal["interpretation"]
        strength = signal["strength"]
        rebound_probable = signal["rebound"]
        trap = signal["trap"]
        structure = signal["structure"]
        state_market = signal["state_market"]
        magnet_up = signal["magnet_up"]
        magnet_down = signal["magnet_down"]
        target = signal["target"]
        liq_target = signal["liq_target"]

        context = get_market_context(radar)
        setup_5m = pullback_zone(klines_map["5m"])
        last_candle_5m = get_last_candle(klines_map["5m"])

        sniper = sniper_entry(
            context=context,
            setup_5m=setup_5m,
            trap=trap,
            last_candle=last_candle_5m,
            bias_4h=bias_4h,
            compression=compression,
        )

        rebound_signal = rebound_entry(
            price=price,
            magnet_up=magnet_up,
            magnet_down=magnet_down,
            last_candle=last_candle_5m,
        )

        entry_signal = None

        if (
            sniper in ("long", "short")
            and rebound_signal in ("long", "short")
            and sniper != rebound_signal
        ):
            entry_signal = None
        elif sniper == "long":
            entry_signal = "long"
        elif sniper == "short":
            entry_signal = "short"
        elif rebound_signal == "long":
            entry_signal = "long"
        elif rebound_signal == "short":
            entry_signal = "short"

        print(
            "sniper:",
            sniper,
            "rebound_signal:",
            rebound_signal,
            "entry_signal:",
            entry_signal,
        )

        # =========================
        # TELEGRAM COMMANDS
        # =========================
        for cmd in commands:
            cmd = cmd.lower().strip()
            cmd = (
                cmd.replace("🟢", "")
                .replace("⚪", "")
                .replace("🔧", "")
                .replace("⚙️", "")
                .replace("❌", "")
                .replace("📊", "")
                .replace("🎯", "")
                .replace("📈", "")
                .replace("💼", "")
                .replace("⏸️", "")
                .replace("▶️", "")
                .replace("🤖", "")
                .strip()
            )

            if cmd in ["/history", "history", "historial"]:
                try:
                    import csv

                    with open("trade_history.csv", "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        trades = list(reader)

                    if not trades:
                        send_telegram("📭 No hay historial todavía")
                        continue

                    lines = ["📊 HISTORIAL DE TRADES\n"]

                    for t in trades[-10:]:
                        side = t.get("side", "")
                        entry = float(t.get("entry", 0) or 0)
                        exit_price = float(t.get("exit", 0) or 0)
                        pnl = float(t.get("pnl", 0) or 0)

                        lines.append(
                            f"{side} | Entry: {entry:.2f} → Exit: {exit_price:.2f} | PnL: {pnl:.2f}"
                        )

                    send_telegram("\n".join(lines))
                    continue

                except FileNotFoundError:
                    send_telegram("📭 Aún no existe trade_history.csv")
                    continue
                except Exception as e:
                    send_telegram(f"❌ Error leyendo historial: {e}")
                    continue

            if cmd in ["/risk", "riesgo"]:
                risk_state = "menu"
                risk_data = {}

                send_telegram(
                    "⚙️ GESTIÓN DE RIESGO\n\n"
                    "1 → Cambiar Stop Loss %\n"
                    "2 → Cambiar Trailing Stop %\n"
                    "3 → Cambiar Break Even %\n"
                    "4 → Activar / Desactivar Trailing\n"
                    "5 → Cancelar"
                )
                continue

            if risk_state is not None:
                if cmd.startswith("/") and cmd != "/risk":
                    risk_state = None
                    risk_data = {}

                elif cmd == "cancelar" or cmd == "5":
                    send_telegram("❌ Gestión de riesgo cancelada")
                    risk_state = None
                    risk_data = {}
                    continue

                elif risk_state == "menu":
                    if cmd == "1":
                        risk_state = "stop_loss"
                        send_telegram("Escribe el nuevo Stop Loss %\nEjemplo: 0.6")
                        continue

                    elif cmd == "2":
                        risk_state = "trailing_stop"
                        send_telegram("Escribe el nuevo Trailing Stop %\nEjemplo: 0.35")
                        continue

                    elif cmd == "3":
                        risk_state = "break_even"
                        send_telegram("Escribe el nuevo Break Even %\nEjemplo: 0.5")
                        continue

                    elif cmd == "4":
                        control_tmp = load_control()
                        current = control_tmp.get("trailing_stop_enabled", True)
                        control_tmp["trailing_stop_enabled"] = not current
                        save_control(control_tmp)

                        estado = (
                            "ACTIVADO"
                            if control_tmp["trailing_stop_enabled"]
                            else "DESACTIVADO"
                        )
                        send_telegram(f"⚙️ Trailing Stop {estado}")

                        risk_state = None
                        risk_data = {}
                        continue

                    else:
                        send_telegram("❌ Opción inválida")
                        continue

                elif risk_state == "stop_loss":
                    try:
                        value = float(cmd)
                        control_tmp = load_control()
                        control_tmp["stop_loss_pct"] = value
                        save_control(control_tmp)

                        send_telegram(f"✅ Stop Loss actualizado a {value}%")
                        risk_state = None
                        risk_data = {}
                    except ValueError:
                        send_telegram("❌ Valor inválido. Ejemplo correcto: 0.6")
                    continue

                elif risk_state == "trailing_stop":
                    try:
                        value = float(cmd)
                        control_tmp = load_control()
                        control_tmp["trailing_stop_pct"] = value
                        save_control(control_tmp)

                        send_telegram(f"✅ Trailing Stop actualizado a {value}%")
                        risk_state = None
                        risk_data = {}
                    except ValueError:
                        send_telegram("❌ Valor inválido. Ejemplo correcto: 0.35")
                    continue

                elif risk_state == "break_even":
                    try:
                        value = float(cmd)
                        control_tmp = load_control()
                        control_tmp["break_even_trigger_pct"] = value
                        save_control(control_tmp)

                        send_telegram(f"✅ Break Even actualizado a {value}%")
                        risk_state = None
                        risk_data = {}
                    except ValueError:
                        send_telegram("❌ Valor inválido. Ejemplo correcto: 0.5")
                    continue

            if cmd in ["/manual_order", "orden manual"]:
                wallet_live = load_wallet()

                if wallet_live.get("open_trade"):
                    send_telegram("ℹ️ Ya hay un trade principal abierto.")
                    continue

                balance = wallet_live["balance"]

                buy_count = sum(1 for tf in radar if "BUY" in radar[tf])
                sell_count = sum(1 for tf in radar if "SELL" in radar[tf])

                score = 50

                if "BUY" in strength:
                    score += 10
                if "SELL" in strength:
                    score -= 10
                if structure.startswith("📈"):
                    score += 10
                if structure.startswith("📉"):
                    score -= 10

                score += (buy_count - sell_count) * 4
                score = max(0, min(100, score))

                if score >= 60:
                    recommendation = "C"
                elif score <= 40:
                    recommendation = "V"
                else:
                    recommendation = "Z"

                control_tmp = load_control()
                stop_pct = control_tmp.get("stop_loss_pct", 0.6)

                risk_pct = 1
                risk_amount = balance * (risk_pct / 100)
                position = round(risk_amount / (stop_pct / 100), 2)

                if recommendation == "C":
                    stop = price * (1 - stop_pct / 100)
                    tp = price * (1 + (stop_pct * 2) / 100)
                elif recommendation == "V":
                    stop = price * (1 + stop_pct / 100)
                    tp = price * (1 - (stop_pct * 2) / 100)
                else:
                    stop = price * (1 - stop_pct / 100)
                    tp = price * (1 + stop_pct / 100)

                manual_order_state = "suggestion"
                manual_order_data = {
                    "price": price,
                    "amount": position,
                    "stop": stop,
                    "tp": tp,
                    "side": recommendation,
                }

                send_telegram(
                    f"🧠 RADAR MANUAL ENTRY\n\n"
                    f"Activo: {SYMBOL}\n"
                    f"Precio: {price:.2f}\n\n"
                    f"Recomendación: {recommendation}\n"
                    f"Score radar: {score}/100\n\n"
                    f"Importe sugerido: {position:.2f} USDT\n"
                    f"Stop sugerido: {stop:.2f}\n"
                    f"Take Profit sugerido: {tp:.2f}\n\n"
                    f"1 → Ejecutar\n"
                    f"2 → Cancelar"
                )
                continue

            if manual_order_state == "suggestion":
                if cmd in ["/execute", "1"]:
                    entry_price = manual_order_data["price"]
                    side_manual = manual_order_data["side"]

                    if side_manual == "C":
                        trade_opened = open_long(entry_price)
                    elif side_manual == "V":
                        trade_opened = open_short(entry_price)
                    else:
                        send_telegram("⏸️ Radar recomienda esperar")
                        manual_order_state = None
                        manual_order_data = {}
                        continue

                    wallet_live = load_wallet()
                    wallet_live["open_trade"]["stop"] = manual_order_data["stop"]
                    wallet_live["open_trade"]["take_profit"] = manual_order_data["tp"]
                    wallet_live["open_trade"]["amount"] = manual_order_data["amount"]
                    wallet_live["open_trade"]["status"] = "open"
                    save_wallet(wallet_live)

                    send_telegram(
                        f"✅ ORDEN MANUAL ABIERTA\n\n"
                        f"Activo: {SYMBOL}\n"
                        f"Entrada: {entry_price:.2f}\n"
                        f"Dirección: {side_manual}\n"
                        f"Importe: {manual_order_data['amount']:.2f}\n"
                        f"Stop Loss: {manual_order_data['stop']:.2f}\n"
                        f"Take Profit: {manual_order_data['tp']:.2f}"
                    )

                    manual_order_state = None
                    manual_order_data = {}
                    continue

                elif cmd in ["/cancel", "2", "cancelar"]:
                    send_telegram("❌ Orden manual cancelada")
                    manual_order_state = None
                    manual_order_data = {}
                    continue

            if cmd in ["/status", "s", "estado"]:
                wallet_live = load_wallet()
                trade_live = wallet_live["open_trade"]

                if trade_live:
                    status_msg = (
                        f"📊 STATUS BOT\n"
                        f"Modo bot: {BOT_MODE}\n"
                        f"Modo gestión: {current_trade_mode}\n"
                        f"Trade: ABIERTO\n"
                        f"Side: {trade_live['side']}\n"
                        f"Entrada: {trade_live['entry']:.2f}\n"
                        f"Stop: {trade_live['stop']:.2f}\n"
                        f"Balance: {wallet_live['balance']:.2f}"
                    )
                else:
                    status_msg = (
                        f"📊 STATUS BOT\n"
                        f"Modo bot: {BOT_MODE}\n"
                        f"Modo gestión: {current_trade_mode}\n"
                        f"Trade: SIN OPERACIÓN ABIERTA\n"
                        f"Balance: {wallet_live['balance']:.2f}"
                    )

                send_telegram(status_msg)
                continue

            if cmd in ["/radar", "radar"]:
                radar_msg = (
                    f"🎯 RADAR BTC\n"
                    f"BTC: {price:.2f}\n\n"
                    + "\n".join([f"{tf} → {radar[tf]} | RSI {rsi_map[tf]}" for tf in radar])
                    + f"\n\n📊 Lectura: {interpretation}"
                    + f"\n⚡ Fuerza: {strength}"
                    + f"\n🔁 Rebote probable: {rebound_probable}"
                    + f"\n🪤 Trap: {trap}"
                    + f"\n🧠 Contexto: {context}"
                    + f"\n🎯 Pullback EMA21: {'SÍ' if setup_5m['near_ema21'] else 'NO'}"
                    + f"\n🎯 Pullback EMA50: {'SÍ' if setup_5m['near_ema50'] else 'NO'}"
                    + f"\n🎯 Sniper: {sniper if sniper else 'esperando'}"
                    + f"\n🎯 Rebound señal: {rebound_signal if rebound_signal else 'esperando'}"
                    + f"\n🎯 Entrada final: {entry_signal if entry_signal else 'esperando'}"
                    + f"\n🎯 Objetivo: {target}"
                    + f"\n📈 Estructura: {structure}"
                    + f"\n🌡️ Estado mercado: {state_market}"
                    + f"\n🧲 Magneto arriba: {magnet_up}"
                    + f"\n🧲 Magneto abajo: {magnet_down}"
                    + f"\n🎯 Liquidez: {liq_target}"
                )
                send_telegram(radar_msg)
                continue

            if cmd in ["/trade", "trade"]:
                wallet_live = load_wallet()
                trade_live = wallet_live["open_trade"]

                if trade_live:
                    live_entry = trade_live["entry"]
                    live_side = trade_live["side"]
                    live_stop = trade_live["stop"]
                    live_tp = trade_live.get("take_profit")
                    live_amount = trade_live.get("amount")

                    if live_side == "LONG":
                        live_pnl_pct = (price - live_entry) / live_entry * 100
                    else:
                        live_pnl_pct = (live_entry - price) / live_entry * 100

                    trade_msg = (
                        f"📈 ESTADO TRADE\n"
                        f"Trade: ABIERTO\n"
                        f"Side: {live_side}\n"
                        f"Entrada: {live_entry:.2f}\n"
                        f"Precio actual: {price:.2f}\n"
                        f"PnL %: {live_pnl_pct:.3f}\n"
                        + (f"Importe: {live_amount:.2f}\n" if live_amount is not None else "")
                        + f"Stop: {live_stop:.2f}\n"
                        + (f"Take Profit: {live_tp:.2f}\n" if live_tp is not None else "")
                        + f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}\n"
                        + f"Modo gestión: {current_trade_mode}"
                    )
                else:
                    trade_msg = (
                        f"📈 ESTADO TRADE\n"
                        f"Trade: SIN OPERACIÓN ABIERTA\n"
                        f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}\n"
                        f"🛠️ Modo gestión: {current_trade_mode}\n"
                    )

                send_telegram(trade_msg)
                continue

            if cmd in ["/wallet", "cuenta"]:
                wallet_live = load_wallet()
                balance_now = wallet_live["balance"]
                trade_live = wallet_live["open_trade"]

                floating_pnl_amount = 0.0

                if trade_live:
                    live_entry = trade_live["entry"]
                    live_side = trade_live["side"]

                    if live_side == "LONG":
                        live_pnl_pct = (price - live_entry) / live_entry * 100
                    else:
                        live_pnl_pct = (live_entry - price) / live_entry * 100

                    live_amount = trade_live.get("amount", balance_now)
                    floating_pnl_amount = live_amount * (live_pnl_pct / 100)

                equity_estimate = balance_now + floating_pnl_amount
                diff_vs_base = equity_estimate - CAPITAL_BASE

                wallet_msg = (
                    f"💼 ESTADO CUENTA\n"
                    f"Balance realizado: {balance_now:.2f}\n"
                    f"PnL flotante: {floating_pnl_amount:.2f}\n"
                    f"Equity estimada: {equity_estimate:.2f}\n"
                    f"Diferencia vs base: {diff_vs_base:.2f}"
                )

                send_telegram(wallet_msg)
                continue

            if cmd in ["/close", "c", "cerrar"]:
                wallet_live = load_wallet()
                trade_live = wallet_live.get("open_trade")

                if trade_live:
                    entry = trade_live["entry"]
                    side_close = trade_live["side"]
                    balance = wallet_live["balance"]
                    amount = trade_live.get("amount", balance)

                    if side_close == "LONG":
                        pnl = (price - entry) / entry * amount
                    else:
                        pnl = (entry - price) / entry * amount

                    wallet_live["balance"] += pnl
                    wallet_live["open_trade"] = None
                    save_wallet(wallet_live)

                    control_tmp = load_control()
                    control_tmp["allow_new_entries"] = False
                    save_control(control_tmp)

                    send_telegram(
                        f"✅ Trade cerrado manualmente desde Telegram\n"
                        f"Side: {side_close}\n"
                        f"Salida: {price:.2f}\n"
                        f"PnL realizado: {pnl:.2f}\n"
                        f"Nuevo balance: {wallet_live['balance']:.2f}\n"
                        f"⏸️ Nuevas entradas pausadas"
                    )
                else:
                    send_telegram("ℹ️ No hay trade abierto")
                continue

            if cmd in ["/pause", "p", "pausar"]:
                control_tmp = load_control()
                control_tmp["allow_new_entries"] = False
                save_control(control_tmp)
                send_telegram("⏸️ Bot en modo observación (no abrirá nuevos trades)")
                continue

            if cmd in ["/resume", "r", "reanudar"]:
                control_tmp = load_control()
                control_tmp["allow_new_entries"] = True
                save_control(control_tmp)
                send_telegram("▶️ Bot reactivado (puede abrir trades)")
                continue

            if cmd in ["/manual", "m", "manual", "manual_spot"]:
                current_trade_mode = "MANUAL_SPOT"
                send_telegram(f"🛠️ Modo cambiado a {current_trade_mode}")
                continue

            if cmd in ["/auto", "a", "auto", "auto_leverage"]:
                current_trade_mode = "AUTO_LEVERAGE"
                send_telegram(f"🤖 Modo cambiado a {current_trade_mode}")
                continue

        # ========================================
        # 🧠 PAPER TRADING ENGINE
        # ========================================
        wallet = load_wallet()
        control = load_control()
        trade = wallet["open_trade"]

        if trade:
            entry = trade["entry"]
            side = trade["side"]
            stop = trade["stop"]

            if side == "LONG":
                pnl_pct = (price - entry) / entry * 100
            else:
                pnl_pct = (entry - price) / entry * 100

            print("\n📊 TRADE STATUS")
            print("------------------")
            print("Modo gestión:", current_trade_mode)
            print("Side:", side)
            print("Entrada:", round(entry, 2))
            print("Precio actual:", round(price, 2))
            print("PnL %:", round(pnl_pct, 3))
            print("Stop actual:", round(stop, 2))
            print("Estado:", trade.get("status", "open"))

            result = update_trade(price)
            if result and result.get("closed"):
                wallet_after = load_wallet()

                balance_after = wallet_after["balance"]
                balance_before = balance_after - result["pnl"]

                amount_used = trade.get("amount", balance_before)

                if trade["side"] == "LONG":
                    pnl_pct = ((result["exit_price"] - trade["entry"]) / trade["entry"]) * 100
                else:
                    pnl_pct = ((trade["entry"] - result["exit_price"]) / trade["entry"]) * 100

                log_trade({
                    "timestamp_open": trade.get("timestamp_open"),
                    "timestamp_close": now_str(),
                    "symbol": SYMBOL,
                    "side": trade["side"],
                    "entry": trade["entry"],
                    "exit": result["exit_price"],
                    "amount": amount_used,
                    "pnl": result["pnl"],
                    "pnl_pct": pnl_pct,
                    "stop": trade.get("stop"),
                    "take_profit": trade.get("take_profit"),
                    "reason": result.get("reason", "close"),
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                })

                print("Trade cerrado:", result)

                close_msg = (
                    f"✅ PAPER TRADE CERRADO\n"
                    f"Modo gestión: {current_trade_mode}\n"
                    f"Side: {side}\n"
                    f"Salida: {result['exit_price']:.2f}\n"
                    f"PnL: {result['pnl']:.2f}\n"
                    f"Nuevo balance: {wallet_after['balance']:.2f}"
                )

                send_telegram(close_msg)

        elif (
            manual_order_state is None
            and control["paper_trading_enabled"]
            and control["allow_new_entries"]
            and current_trade_mode == "AUTO_LEVERAGE"
        ):
            if BOT_MODE == "TEST_5M":
                last_5m = klines_map["5m"][-2]
                open_price = float(last_5m[1])
                close_price = float(last_5m[4])

                if close_price > open_price:
                    trade = open_long(price)

                    if trade is not None:
                        wallet_live = load_wallet()
                        if wallet_live.get("open_trade"):
                            wallet_live["open_trade"]["timestamp_open"] = now_str()
                            save_wallet(wallet_live)

                        print("🧪 TEST MODE LONG:", trade)

                        send_telegram(
                            f"🧪 TEST LONG\n"
                            f"Modo gestión: {current_trade_mode}\n"
                            f"Entrada: {trade['entry']:.2f}\n"
                            f"Stop: {trade['stop']:.2f}\n"
                            f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                        )

                elif close_price < open_price:
                    trade = open_short(price)

                    if trade is not None:
                        wallet_live = load_wallet()
                        if wallet_live.get("open_trade"):
                            wallet_live["open_trade"]["timestamp_open"] = now_str()
                            save_wallet(wallet_live)

                        print("🧪 TEST MODE SHORT:", trade)

                        send_telegram(
                            f"🧪 TEST SHORT\n"
                            f"Modo gestión: {current_trade_mode}\n"
                            f"Entrada: {trade['entry']:.2f}\n"
                            f"Stop: {trade['stop']:.2f}\n"
                            f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                        )

            else:
                if entry_signal == "long":
                    trade = open_long(price)

                    if trade is not None:
                        wallet_live = load_wallet()
                        if wallet_live.get("open_trade"):
                            wallet_live["open_trade"]["timestamp_open"] = now_str()
                            save_wallet(wallet_live)

                        entry_msg = (
                            f"🚨 PAPER LONG ABIERTO\n"
                            f"Modo gestión: {current_trade_mode}\n"
                            f"Contexto: {context}\n"
                            f"Setup: sniper={sniper} | rebound={rebound_signal}\n"
                            f"Entrada: {trade['entry']:.2f}\n"
                            f"Stop: {trade['stop']:.2f}\n"
                            f"Balance simulado: {wallet['balance']:.2f}\n"
                            f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                        )

                        send_telegram(entry_msg)

                elif entry_signal == "short":
                    trade = open_short(price)

                    if trade is not None:
                        wallet_live = load_wallet()
                        if wallet_live.get("open_trade"):
                            wallet_live["open_trade"]["timestamp_open"] = now_str()
                            save_wallet(wallet_live)

                        entry_msg = (
                            f"🚨 PAPER SHORT ABIERTO\n"
                            f"Modo gestión: {current_trade_mode}\n"
                            f"Contexto: {context}\n"
                            f"Setup: sniper={sniper} | rebound={rebound_signal}\n"
                            f"Entrada: {trade['entry']:.2f}\n"
                            f"Stop: {trade['stop']:.2f}\n"
                            f"Balance simulado: {wallet['balance']:.2f}\n"
                            f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                        )

                        send_telegram(entry_msg)

        # ========================================
        # 🧲 LIQUIDITY ALERTS
        # ========================================
        magnet_alert = None

        if magnet_up > 0:
            dist_up = (magnet_up - price) / price * 100
            if 0 <= dist_up <= 0.3:
                magnet_alert = f"🧲 Precio cerca del magneto superior ({magnet_up:.2f})"

        if magnet_down > 0:
            dist_down = (price - magnet_down) / price * 100
            if 0 <= dist_down <= 0.3:
                magnet_alert = f"🧲 Precio cerca del magneto inferior ({magnet_down:.2f})"

        if magnet_alert:
            send_telegram(
                f"⚡ ALERTA LIQUIDEZ\n"
                f"{magnet_alert}\n"
                f"Precio actual: {price:.2f}"
            )

        # ========================================
        # 📊 RADAR EN CONSOLA
        # ========================================
        if now - last_market_run < UPDATE_INTERVAL:
            print("\nBTC RADAR")
            print("------------------")
            print("BIAS 4H:", bias_4h)
            print("COMPRESSION:", compression)

            for tf in radar:
                print(f"{tf} → {radar[tf]} | RSI {rsi_map[tf]}")

            print("LECTURA:", interpretation)
            print("FUERZA SEÑAL:", strength)
            print("REBOTE PROBABLE:", rebound_probable)
            print("TRAP DETECTOR:", trap)
            print("OBJETIVO:", target)
            print("ESTRUCTURA:", structure)
            print("ESTADO MERCADO:", state_market)
            print("MAGNETO ARRIBA:", magnet_up)
            print("MAGNETO ABAJO:", magnet_down)
            print("OBJETIVO LIQUIDEZ:", liq_target)
            print("RIESGO BOT:", risk_mode)
            print("DIFERENCIA CAPITAL:", capital_diff)

        state = (
            tuple(radar.values()),
            strength,
            rebound_probable,
            trap,
            target,
            structure,
            state_market,
            magnet_up,
            magnet_down,
            liq_target,
            risk_mode,
            round(capital_diff, 2),
        )

        if state != last_state and (
            strength in ["💪 BUY FUERTE", "💥 SELL FUERTE"]
            or risk_mode in ["DANGER", "LOSS_ALERT", "PROFIT_ALERT"]
        ):
            message = f"⚡ ACROJAS BTC BOT\n\nBTC: {price:.2f}\n\n"

            wallet_live = load_wallet()
            live_trade = wallet_live["open_trade"]

            recommendation = "Esperando señal"
            live_pnl_pct = 0.0

            if live_trade:
                live_entry = live_trade["entry"]
                live_side = live_trade["side"]
                live_stop = live_trade["stop"]

                if live_side == "LONG":
                    live_pnl_pct = (price - live_entry) / live_entry * 100
                else:
                    live_pnl_pct = (live_entry - price) / live_entry * 100

                if live_side == "LONG":
                    if live_pnl_pct < 0 and structure.startswith("📉"):
                        recommendation = "❌ Conviene cerrar manualmente"
                    elif (
                        structure.startswith("📈")
                        and "BUY" in strength
                        and live_pnl_pct >= 0
                    ):
                        recommendation = "✅ Conviene mantener"
                    elif live_pnl_pct > 0 and (
                        "INDECISO" in interpretation or "SELL" in strength
                    ):
                        recommendation = "⚠️ Conviene vigilar / asegurar"
                    else:
                        recommendation = "⚠️ Conviene vigilar"

                elif live_side == "SHORT":
                    if live_pnl_pct < 0 and structure.startswith("📈"):
                        recommendation = "❌ Conviene cerrar manualmente"
                    elif (
                        structure.startswith("📉")
                        and "SELL" in strength
                        and live_pnl_pct >= 0
                    ):
                        recommendation = "✅ Conviene mantener"
                    elif live_pnl_pct > 0 and (
                        "INDECISO" in interpretation or "BUY" in strength
                    ):
                        recommendation = "⚠️ Conviene vigilar / asegurar"
                    else:
                        recommendation = "⚠️ Conviene vigilar"

            message += f"\n🤖 RECOMENDACIÓN BOT:\n{recommendation}\n"

            balance_now = wallet_live["balance"]

            floating_pnl_amount = 0.0
            if live_trade:
                live_amount = live_trade.get("amount", balance_now)
                floating_pnl_amount = live_amount * (live_pnl_pct / 100)

            equity_estimate = balance_now + floating_pnl_amount
            diff_vs_base = equity_estimate - CAPITAL_BASE

            if diff_vs_base > 0:
                account_state = "🟢 EN BENEFICIO"
            elif diff_vs_base < 0:
                account_state = "🔴 EN ROJO"
            else:
                account_state = "⚪ EN EQUILIBRIO"

            for tf in radar:
                message += f"{tf} → {radar[tf]} | RSI {rsi_map[tf]}\n"

            message += f"\n📊 LECTURA:\n{interpretation}\n"
            message += f"\n⚡ FUERZA:\n{strength}\n"
            message += f"\n🔁 Rebote probable: {rebound_probable}\n"
            message += f"🪤 Trap detector: {trap}\n"
            message += f"🎯 Objetivo probable: {target}\n"
            message += f"📊 Estructura mercado: {structure}\n"
            message += f"🌡️ Estado mercado: {state_market}\n"
            message += f"🧲 Magneto arriba: {magnet_up}\n"
            message += f"🧲 Magneto abajo: {magnet_down}\n"
            message += f"🎯 Objetivo liquidez: {liq_target}\n"
            message += f"🛡️ Riesgo bot: {risk_mode}\n"
            message += f"💰 Diferencia capital: {capital_diff}\n"
            message += f"\n🛠️ Modo gestión: {current_trade_mode}\n"

            if live_trade:
                message += (
                    f"\n📊 ESTADO TRADE:\n"
                    f"Trade: ABIERTO\n"
                    f"Side: {live_side}\n"
                    f"Entrada: {live_entry:.2f}\n"
                    f"Precio actual: {price:.2f}\n"
                    f"PnL %: {live_pnl_pct:.3f}\n"
                    f"Stop actual: {live_stop:.2f}\n"
                    f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}\n"
                )
            else:
                message += (
                    f"\n🧭 ESCENARIO ACTUAL:\n"
                    f"Sin operación abierta\n"
                    f"Objetivo probable: {target}\n"
                    f"Liquidez: {liq_target}\n"
                    f"Bias 4H: {bias_4h}\n"
                    f"Compresión: {compression}\n"
                )

            message += (
                f"\n💼 ESTADO CUENTA:\n"
                f"Balance realizado: {balance_now:.2f}\n"
                f"PnL flotante: {floating_pnl_amount:.2f}\n"
                f"Equity estimada: {equity_estimate:.2f}\n"
                f"Diferencia vs base: {diff_vs_base:.2f}\n"
                f"Estado cuenta: {account_state}\n"
            )

            sent = send_telegram(message)

            if sent:
                print("\n📡 Radar enviado a Telegram")
            else:
                print("\n❌ No se pudo enviar a Telegram")

            last_state = state

        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
