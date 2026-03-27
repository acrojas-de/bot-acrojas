from binance.client import Client
import time
import traceback

from alerts.telegram_alerts import (
    send_telegram,
    read_telegram_commands,
    send_telegram_image,
    normalize_telegram_command,
)

from config import (
    API_KEY,
    API_SECRET,
    SYMBOL,
    DEFAULT_SYMBOL,
    ALL_TIMEFRAMES,
    ACTIVE_TIMEFRAMES,
    UPDATE_INTERVAL,
    BOT_MODE,
    TRADE_MODE,
    CAPITAL_BASE,
    MAX_LOSS_ALLOWED,
    MIN_PROFIT_ALERT,
)

from engines.htf_bias_engine import get_htf_bias
from engines.compression_engine import compression_signal
from engines.rebound_engine import rebound_entry
from engines.risk_manager import risk_status
from engines.signal_engine import build_signal
from engines.context_engine import get_market_context
from engines.pullback_engine import pullback_zone
from engines.sniper_entry import get_last_candle, sniper_entry
from engines.vibora_engine import ViboraEngine
from engines.smart_hunt_selector import get_selected_symbol, format_ranking_message
from orbita.config_market import MARKET_ASSETS
from orbita.router import show_orbita_menu, show_asset_menu



manual_symbol = None
last_test_5m_candle_time = None

from engines.paper_engine import (
    open_long,
    open_short,
    update_trade,
    load_wallet,
    load_control,
    save_wallet,
    save_control,
)

from mtf_engine import MTFEngine
from utils.history_logger import log_trade, log_equity, now_str
from utils.mtf_dashboard import generate_mtf_dashboard

print("🔥 BOT_ACROJAS BUILD NUEVA - TELEGRAM CLEAN MODE 🔥")

WATCHLIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
]

client = Client(API_KEY, API_SECRET)
vibora = ViboraEngine(config=None)

def get_active_symbol(current_symbol, manual_symbol):
    selected_symbol, selector_info = get_selected_symbol(
        client=client,
        watchlist=WATCHLIST,
        default_symbol=current_symbol,
        manual_symbol=manual_symbol,
        klines_limit=120,
        min_score=4,
    )

    print("🧠 Selector mode:", selector_info.get("mode"))
    print("🎯 Selected symbol:", selected_symbol)

    best = selector_info.get("best")
    if best:
        print(
            f"🏆 Best: {best['symbol']} | score={best['score']} | "
            f"1D={best['bias_1d']} | 4H={best['bias_4h']} | 5m={best['trigger_5m']}"
        )

    return selected_symbol


def get_klines(symbol, interval, limit=120):
    return client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )


def normalize_klines(raw_klines):
    candles = []
    for k in raw_klines:
        candles.append(
            {
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
            }
        )
    return candles


print("🛰️ ACROJAS BOT iniciado")
print("ℹ️ Welcome panel omitido al arranque")
print("⏱️ Timeframes activos:", ", ".join(ACTIVE_TIMEFRAMES))
print("🧠 Modo bot:", BOT_MODE)
print("🛠️ Modo gestión:", TRADE_MODE)

control_boot = load_control()
current_trade_mode = control_boot.get("trade_mode", TRADE_MODE)

last_state = None
last_update_id = None
last_active_symbol = None

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
        symbol, selector_info = get_selected_symbol(
            client=client,
            watchlist=WATCHLIST,
            default_symbol=DEFAULT_SYMBOL,
            manual_symbol=manual_symbol,
        )

        print(f"\n🧠 SELECTOR MODE: {selector_info['mode']}")
        print(f"🎯 SYMBOL: {symbol}")

        print("📝 manual_symbol actual:", manual_symbol)
        active_symbol = symbol

        if active_symbol != last_active_symbol:
            cached_price = None
            cached_signal = None
            cached_risk_mode = None
            cached_capital_diff = None
            cached_klines_map = {}
            last_market_run = 0
            last_active_symbol = active_symbol
            print("🔄 Cambio de símbolo:", active_symbol)

        commands, last_update_id = read_telegram_commands(last_update_id)
        
        for cmd in commands:
            cmd = normalize_telegram_command(cmd)

            if cmd == "ranking":
                _, selector_info = get_selected_symbol(
                    client=client,
                    watchlist=WATCHLIST,
                    default_symbol=DEFAULT_SYMBOL,
                    manual_symbol=manual_symbol,
                )

                msg = format_ranking_message(selector_info)
                send_telegram(msg)
                continue        
        
        if not commands:
            commands = []

        price = cached_price
        signal = cached_signal
        risk_mode = cached_risk_mode
        capital_diff = cached_capital_diff
        klines_map = cached_klines_map

        now = time.time()

        if now - last_market_run >= UPDATE_INTERVAL or cached_signal is None:
            ticker = client.get_symbol_ticker(symbol=active_symbol)
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

            log_equity(
                {
                    "timestamp": now_str(),
                    "price": price,
                    "balance": current_balance,
                    "open_trade": "YES" if trade_live else "NO",
                    "equity": equity_estimate,
                    "floating_pnl": floating_pnl_amount,
                    "risk_mode": risk_mode,
                }
            )

            klines_map = {}
            
            for tf in ACTIVE_TIMEFRAMES:
                interval = ALL_TIMEFRAMES[tf]
                klines_map[tf] = get_klines(active_symbol, interval)

            print("🎯 Active symbol:", active_symbol)

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

        else:
            bias_4h = get_htf_bias(klines_map["4h"])
            compression = compression_signal(klines_map["1h"])

        radar = signal["radar"]
        rsi_map = signal["rsi"]
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

        mtf_engine = MTFEngine()

        monthly_bias = mtf_engine.get_monthly_bias(klines_map["1D"])
        weekly_bias = mtf_engine.get_weekly_bias(klines_map["4h"])
        intraday_trigger = mtf_engine.get_intraday_trigger(
            klines_map["5m"],
            klines_map["1m"],
        )

        mtf_decision = mtf_engine.decide(
            monthly_bias,
            weekly_bias,
            intraday_trigger,
        )

        print("\n---- ENTRY DEBUG ----")
        print("mtf_decision:", mtf_decision)
        print("structure:", structure)
        print("compression:", compression)
        print("sniper:", sniper)
        print("rebound_signal:", rebound_signal)
        print("entry_signal:", entry_signal)

        score_mtf = 0
        score_structure = 0
        score_compression = 0
        score_sniper = 0
        score_rebound = 0
        score_entry_signal = 0

        # 🔹 MTF
        if mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_mtf = 2
        elif mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_mtf = 2

        # 🔹 ESTRUCTURA
        if structure.startswith("📈") and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_structure = 2
        elif structure.startswith("📉") and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_structure = 2

        # 🔹 COMPRESIÓN
        if compression == "alta":
            score_compression = 2
        elif compression == "media":
            score_compression = 1

        # 🔹 SNIPER
        if sniper == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_sniper = 1
        elif sniper == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_sniper = 1

        # 🔹 REBOUND
        if rebound_signal == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_rebound = 1
        elif rebound_signal == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_rebound = 1

        # 🔹 ENTRY SIGNAL
        if entry_signal == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_entry_signal = 1
        elif entry_signal == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_entry_signal = 1

        # 🔥 SCORE TOTAL
        entry_score = (
            score_mtf +
            score_structure +
            score_compression +
            score_sniper +
            score_rebound +
            score_entry_signal
        )

        print("score_mtf:", score_mtf)
        print("score_structure:", score_structure)
        print("score_compression:", score_compression)
        print("score_sniper:", score_sniper)
        print("score_rebound:", score_rebound)
        print("score_entry_signal:", score_entry_signal)
        print("👉 entry_score:", entry_score)

        # 🎯 DECISIÓN FINAL
      
        if mtf_decision == "ENTER_LONG" and entry_score >= 6:
            final_entry = "long"
        elif mtf_decision == "ENTER_SHORT" and entry_score >= 6:
            final_entry = "short"
        elif mtf_decision == "SCALP" and entry_score >= 6:
            if entry_signal == "long" or sniper == "long":
                final_entry = "long"
            elif entry_signal == "short" or sniper == "short":
                final_entry = "short"
            else:
                final_entry = None
        else:
            final_entry = None

        print("🎯 final_entry:", final_entry)
        print("----------------------\n")

        if final_entry is None:
            print(
                "🚫 Trade bloqueado | score:",
                entry_score,
                "| compression:",
                compression,
                "| strength:",
                strength,
            )

        candles_5m = normalize_klines(klines_map["5m"])

        vibora_bias = None
        if mtf_decision == "ENTER_LONG":
            vibora_bias = "LONG"
        elif mtf_decision == "ENTER_SHORT":
            vibora_bias = "SHORT"

        vibora_signal = None
        if vibora_bias is not None:
            vibora_signal = vibora.get_vibora_signal(candles_5m, vibora_bias)

        if vibora_signal == "LONG":
            final_entry = "long"
        elif vibora_signal == "SHORT":
            final_entry = "short"

        print("entry_score:", entry_score)
        print("mtf_decision:", mtf_decision)
        print("vibora_bias:", vibora_bias)
        print("vibora_signal:", vibora_signal)
        print("final_entry:", final_entry)
        
        # =========================
        # TELEGRAM COMMANDS
        # =========================
        for cmd in commands:
            print("📩 CMD RAW:", cmd)
            cmd = normalize_telegram_command(cmd)
            print("📩 CMD NORMALIZADO:", cmd)

            # =========================
            # ÓRBITA MENU
            # =========================
            if cmd in ["/orbita", "orbita"]:
                from orbita.router import show_orbita_menu
                send_telegram(show_orbita_menu())
                continue

            # =========================
            # SELECCIÓN DE ACTIVO (ÓRBITA)
            # =========================
            if cmd.upper() in MARKET_ASSETS:
                symbol = cmd.upper()
                last_active_symbol = symbol
                send_telegram(show_asset_menu(symbol))
                continue

            # =========================
            # ESCANEAR (ÓRBITA)
            # =========================
            if cmd in ["📡 escanear", "escanear", "/scan"]:
                try:
                    if not last_active_symbol:
                        send_telegram("⚠️ Selecciona primero un activo en ÓRBITA")
                        continue

                    klines_map_orbita = {}

                    for tf in ACTIVE_TIMEFRAMES:
                        interval = ALL_TIMEFRAMES[tf]
                        raw = get_klines(last_active_symbol, interval)
                        klines_map_orbita[tf] = normalize_klines(raw)

                    from orbita.router import run_scan
                    result = run_scan(last_active_symbol, klines_map_orbita)

                    send_telegram(result)
                    continue

                except Exception as e:
                    send_telegram(f"❌ Error en escaneo ÓRBITA: {e}")
                    continue

            # =========================
            # MODO
            # =========================
            if cmd in ["/mode", "modo"]:
                control_tmp = load_control()
                allow_entries = control_tmp.get("allow_new_entries", True)

                mode_msg = (
                    f"🤖 MODO ACTUAL\n"
                    f"Activo: {active_symbol}\n"
                    f"Modo gestión: {current_trade_mode}\n"
                    f"Nuevas entradas: {'ACTIVAS' if allow_entries else 'PAUSADAS'}\n"
                    f"Paper trading: {'ACTIVO' if control_tmp.get('paper_trading_enabled', False) else 'INACTIVO'}"
                )

                send_telegram(mode_msg)
                continue

            # =========================
            # HISTORY
            # =========================
            if cmd in ["/history", "history", "historial"]:
                try:
                    import csv

                    with open("trade_history.csv", "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        trades = list(reader)

                    if not trades:
                        send_telegram("📭 No hay historial todavía")
                        continue

                    lines = [f"📊 HISTORIAL DE TRADES {active_symbol}\n"]

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

            # =========================
            # RISK
            # =========================
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

                elif cmd in ["cancelar", "5"]:
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

            # =========================
            # MANUAL ORDER
            # =========================
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
                    f"Activo: {active_symbol}\n"
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
                        open_long(entry_price)
                    elif side_manual == "V":
                        open_short(entry_price)
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
                        f"Activo: {active_symbol}\n"
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

            # =========================
            # STATUS
            # =========================
            if cmd in ["/status", "s", "estado"]:
                wallet_live = load_wallet()
                trade_live = wallet_live["open_trade"]

                if trade_live:
                    status_msg = (
                        f"📊 STATUS BOT\n"
                        f"Activo: {active_symbol}\n"
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
                        f"Activo: {active_symbol}\n"
                        f"Modo bot: {BOT_MODE}\n"
                        f"Modo gestión: {current_trade_mode}\n"
                        f"Trade: SIN OPERACIÓN ABIERTA\n"
                        f"Balance: {wallet_live['balance']:.2f}"
                    )

                send_telegram(status_msg)
                continue

            # =========================
            # RADAR
            # =========================
            if cmd in ["/radar", "radar"]:
                panel_path = generate_mtf_dashboard(
                    price,
                    entry_score,
                    mtf_decision,
                    monthly_bias,
                    weekly_bias,
                    intraday_trigger,
                )

                radar_caption = (
                    f"🎯 {active_symbol}\n"
                    f"Precio: {price:.2f}\n"
                    f"Score: {entry_score}/8\n"
                    f"Compresión: {compression}\n"
                    f"Fuerza: {strength}\n"
                    f"Estructura: {structure}\n"
                    f"Trigger: {intraday_trigger}\n"
                    f"Decisión: {mtf_decision}\n"
                    f"Entrada final: {final_entry if final_entry else 'esperando'}"
                )

                send_telegram_image(panel_path, caption=radar_caption)
                continue

            # =========================
            # TRADE
            # =========================
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
                        f"Activo: {active_symbol}\n"
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
                        f"Activo: {active_symbol}\n"
                        f"Trade: SIN OPERACIÓN ABIERTA\n"
                        f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}\n"
                        f"🛠️ Modo gestión: {current_trade_mode}\n"
                    )

                send_telegram(trade_msg)
                continue

            # =========================
            # WALLET
            # =========================
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
                    f"Activo: {active_symbol}\n"
                    f"Balance realizado: {balance_now:.2f}\n"
                    f"PnL flotante: {floating_pnl_amount:.2f}\n"
                    f"Equity estimada: {equity_estimate:.2f}\n"
                    f"Diferencia vs base: {diff_vs_base:.2f}"
                )

                send_telegram(wallet_msg)
                continue

            # =========================
            # CLOSE
            # =========================
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
                        f"Activo: {active_symbol}\n"
                        f"Side: {side_close}\n"
                        f"Salida: {price:.2f}\n"
                        f"PnL realizado: {pnl:.2f}\n"
                        f"Nuevo balance: {wallet_live['balance']:.2f}\n"
                        f"⏸️ Nuevas entradas pausadas"
                    )
                else:
                    send_telegram("ℹ️ No hay trade abierto")
                continue

            # =========================
            # PAUSE / RESUME / MODES
            # =========================
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
                control_tmp = load_control()
                control_tmp["trade_mode"] = current_trade_mode
                save_control(control_tmp)
                send_telegram(f"🛠️ Modo cambiado a {current_trade_mode}")
                continue

            if cmd in ["/auto", "a", "auto", "auto_leverage"]:
                current_trade_mode = "AUTO_LEVERAGE"
                control_tmp = load_control()
                control_tmp["trade_mode"] = current_trade_mode
                save_control(control_tmp)
                send_telegram(f"🤖 Modo cambiado a {current_trade_mode}")
                continue

            # =========================
            # PAPER TRADING ENGINE
            # =========================
            is_vibora_trade = vibora_signal in ("LONG", "SHORT")

            wallet = load_wallet()
            control = load_control()
            trade = wallet.get("open_trade")

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
                print("Activo:", active_symbol)
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
                    pnl_pct = (
                        (result["exit_price"] - trade["entry"]) / trade["entry"]
                    ) * 100
                else:
                    pnl_pct = (
                        (trade["entry"] - result["exit_price"]) / trade["entry"]
                    ) * 100

                log_trade(
                    {
                        "timestamp_open": trade.get("timestamp_open"),
                        "timestamp_close": now_str(),
                        "symbol": active_symbol,
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
                    }
                )

                print("Trade cerrado:", result)

                close_msg = (
                    f"✅ PAPER TRADE CERRADO\n"
                    f"Activo: {active_symbol}\n"
                    f"Modo gestión: {current_trade_mode}\n"
                    f"Side: {trade['side']}\n"
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
                    candle_open_time = last_5m[0]
                    open_price = float(last_5m[1])
                    close_price = float(last_5m[4])

                    if candle_open_time != last_test_5m_candle_time:
                        last_test_5m_candle_time = candle_open_time

                        if close_price > open_price:
                            trade = open_long(price)

                            if trade is not None:
                                wallet_live = load_wallet()
                                if wallet_live.get("open_trade"):
                                    wallet_live["open_trade"]["timestamp_open"] = now_str()
                                    wallet_live["open_trade"]["vibora_mode"] = is_vibora_trade
                                    save_wallet(wallet_live)

                                print("🧪 TEST MODE LONG:", trade)

                                send_telegram(
                                    f"🧪 TEST LONG\n"
                                    f"Activo: {active_symbol}\n"
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
                                    wallet_live["open_trade"]["vibora_mode"] = is_vibora_trade
                                    save_wallet(wallet_live)

                                print("🧪 TEST MODE SHORT:", trade)

                                send_telegram(
                                    f"🧪 TEST SHORT\n"
                                    f"Activo: {active_symbol}\n"
                                    f"Modo gestión: {current_trade_mode}\n"
                                    f"Entrada: {trade['entry']:.2f}\n"
                                    f"Stop: {trade['stop']:.2f}\n"
                                    f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                                )

                else:
                    if final_entry == "long":
                        trade = open_long(price)

                        if trade is not None:
                            wallet_live = load_wallet()
                            if wallet_live.get("open_trade"):
                                wallet_live["open_trade"]["timestamp_open"] = now_str()
                                wallet_live["open_trade"]["vibora_mode"] = is_vibora_trade
                                save_wallet(wallet_live)

                            entry_msg = (
                                f"🚨 PAPER LONG ABIERTO\n"
                                f"Activo: {active_symbol}\n"
                                f"Modo gestión: {current_trade_mode}\n"
                                f"Contexto: {context}\n"
                                f"Setup: sniper={sniper} | rebound={rebound_signal}\n"
                                f"Entrada: {trade['entry']:.2f}\n"
                                f"Stop: {trade['stop']:.2f}\n"
                                f"Balance simulado: {wallet['balance']:.2f}\n"
                                f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                            )

                            send_telegram(entry_msg)

                    elif final_entry == "short":
                        trade = open_short(price)

                        if trade is not None:
                            wallet_live = load_wallet()
                            if wallet_live.get("open_trade"):
                                wallet_live["open_trade"]["timestamp_open"] = now_str()
                                wallet_live["open_trade"]["vibora_mode"] = is_vibora_trade
                                save_wallet(wallet_live)

                            entry_msg = (
                                f"🚨 PAPER SHORT ABIERTO\n"
                                f"Activo: {active_symbol}\n"
                                f"Modo gestión: {current_trade_mode}\n"
                                f"Contexto: {context}\n"
                                f"Setup: sniper={sniper} | rebound={rebound_signal}\n"
                                f"Entrada: {trade['entry']:.2f}\n"
                                f"Stop: {trade['stop']:.2f}\n"
                                f"Balance simulado: {wallet['balance']:.2f}\n"
                                f"Cierre automático: {'SÍ' if current_trade_mode == 'AUTO_LEVERAGE' else 'NO'}"
                            )

                            send_telegram(entry_msg)

            # =========================
            # ALERTAS AUTOMÁTICAS DESACTIVADAS
            # =========================
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
                print("ALERTA LIQUIDEZ:", magnet_alert)

            print(f"\n{active_symbol} RADAR")
            print("------------------")
            print("BIAS 4H:", bias_4h)
            print("COMPRESSION:", compression or "desconocido")

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
            print("\n🌍 MTF ENGINE:")
            print("------------------")
            print("Bias mensual:", monthly_bias)
            print("Bias semanal:", weekly_bias)
            print("Trigger:", intraday_trigger)
            print("Decisión:", mtf_decision)

            state = (
                active_symbol,
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
                round(capital_diff, 2) if capital_diff is not None else None,
            )

            last_state = state

            time.sleep(1)    


    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
        time.sleep(2)