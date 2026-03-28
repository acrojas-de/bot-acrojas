# ============================================================
# IMPORTS BASE
# - Cliente Binance
# - utilidades de tiempo / errores
# ============================================================
from binance.client import Client
import time
import traceback


# ============================================================
# TELEGRAM
# - envío de mensajes
# - lectura de comandos
# - imágenes
# - normalización de botones/comandos
# ============================================================
from alerts.telegram_alerts import (
    send_telegram,
    read_telegram_commands,
    send_telegram_image,
    normalize_telegram_command,
)


# ============================================================
# CONFIG GLOBAL
# - claves
# - símbolo por defecto
# - timeframes
# - parámetros generales del bot
# ============================================================
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


# ============================================================
# ENGINES DE ANÁLISIS
# - bias
# - compresión
# - rebote
# - riesgo
# - señal
# - contexto
# - pullback
# - sniper
# - selector smart hunt
# ============================================================
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


# ============================================================
# ÓRBITA / MERCADOS
# - lista de activos
# - menús de navegación
# ============================================================
from orbita.config_market import MARKET_ASSETS
from orbita.router import show_orbita_menu, show_asset_menu


# ============================================================
# ESTADO MANUAL / TEST
# - selección manual de símbolo
# - control candle test 5m
# ============================================================
manual_symbol = None
last_test_5m_candle_time = None


# ============================================================
# PAPER ENGINE / CONTROL OPERATIVO
# - abrir/cerrar trades
# - leer y guardar wallet/control
# ============================================================
from engines.paper_engine import (
    open_long,
    open_short,
    update_trade,
    load_wallet,
    load_control,
    save_wallet,
    save_control,
)


# ============================================================
# MTF / LOGS / DASHBOARD
# - motor multi-timeframe
# - logs de trades/equity
# - panel gráfico
# ============================================================
from mtf_engine import MTFEngine
from utils.history_logger import log_trade, log_equity, now_str
from utils.mtf_dashboard import generate_mtf_dashboard


# ============================================================
# BUILD / IDENTIFICACIÓN DE VERSIÓN
# ============================================================
print("🔥 BOT_ACROJAS BUILD NUEVA - TELEGRAM CLEAN MODE 🔥")


# ============================================================
# WATCHLIST BASE
# - activos candidatos para el selector
# ============================================================
WATCHLIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
]


# ============================================================
# INICIALIZACIÓN DE CLIENTES / ENGINES
# ============================================================
client = Client(API_KEY, API_SECRET)
vibora = ViboraEngine(config=None)


# ============================================================
# FUNCIÓN AUXILIAR
# - obtiene símbolo activo desde selector inteligente
# ============================================================
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


# ============================================================
# FUNCIÓN AUXILIAR
# - descarga klines de Binance
# ============================================================
def get_klines(symbol, interval, limit=120):
    return client.get_klines(
        symbol=symbol,
        interval=interval,
        limit=limit,
    )


# ============================================================
# FUNCIÓN AUXILIAR
# - normaliza klines a diccionario OHLC
# ============================================================
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


# ============================================================
# LOG DE ARRANQUE
# - información visible al iniciar bot
# ============================================================
print("🛰️ ACROJAS BOT iniciado")
print("ℹ️ Welcome panel omitido al arranque")
print("⏱️ Timeframes activos:", ", ".join(ACTIVE_TIMEFRAMES))
print("🧠 Modo bot:", BOT_MODE)
print("🛠️ Modo gestión:", TRADE_MODE)


# ============================================================
# CONFIG INICIAL DE CONTROL
# - lee modo de gestión persistido
# ============================================================
control_boot = load_control()
current_trade_mode = control_boot.get("trade_mode", TRADE_MODE)


# ============================================================
# ESTADO GLOBAL DEL LOOP
# - variables persistentes entre iteraciones
# ============================================================
last_state = None
last_update_id = None
last_active_symbol = None
manual_order_state = None
manual_order_data = {}
risk_state = None
risk_data = {}


# ============================================================
# CACHÉ DE MERCADO
# - evita recalcular todo en cada vuelta del loop
# ============================================================
last_market_run = 0
cached_price = None
cached_signal = None
cached_risk_mode = None
cached_capital_diff = None
cached_klines_map = {}

while True:
    try:
        print("🔁 LOOP VIVO")

        # =========================
        # LEER TELEGRAM UNA SOLA VEZ
        # =========================
        print("📩 LEYENDO TELEGRAM...")
        commands, last_update_id = read_telegram_commands(last_update_id)
        print("📬 COMMANDS RAW:", commands)

        # =========================
        # SELECTOR DE ACTIVO
        # =========================
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

        except Exception as e:
            print("ERROR SELECTOR:", e)
            time.sleep(2)
            continue

        # =========================
        # COMANDOS TELEGRAM
        # =========================
        for cmd in commands:
            raw_cmd = cmd
            cmd = normalize_telegram_command(cmd).strip().lower()

            print("CMD RAW:", raw_cmd)
            print("CMD NORMALIZED:", cmd)

            # RANKING
            if cmd in ["ranking", "/ranking"]:
                print("ENTRO EN RANKING")
                try:
                    _, selector_info = get_selected_symbol(
                        client=client,
                        watchlist=WATCHLIST,
                        default_symbol=DEFAULT_SYMBOL,
                        manual_symbol=manual_symbol,
                    )

                    msg = format_ranking_message(selector_info)
                    send_telegram(msg)

                except Exception as e:
                    print("ERROR EN RANKING:", e)

                continue            

            # ÓRBITA MENU
            if cmd in ["/orbita", "orbita"]:
                from orbita.router import show_orbita_menu
                send_telegram(show_orbita_menu())
                continue

            # SELECCIÓN DE ACTIVO
            if cmd.upper() in MARKET_ASSETS:
                manual_symbol = cmd.upper()
                last_active_symbol = manual_symbol
                print("🎯 MANUAL SYMBOL SET:", manual_symbol)

                from orbita.router import show_asset_menu
                send_telegram(show_asset_menu(manual_symbol))
                continue

            # ESCANEAR
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

                except Exception as e:
                    send_telegram(f"❌ Error en escaneo ÓRBITA: {e}")
                continue

            # MODO
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

            # STATUS
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

            # TRADE
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

            # WALLET
            if cmd in ["/wallet", "cuenta"]:
                wallet_live = load_wallet()
                balance_now = wallet_live["balance"]
                trade_live = wallet_live["open_trade"]

                floating_pnl_amount = 0.0

                if trade_live and price is not None:
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

            # ============================================================
            # ORDEN MANUAL - RESPUESTA A PROPUESTA
            #    - Ejecuta o cancela la orden manual sugerida
            # ============================================================
            if manual_order_state == "suggestion":
                if cmd in ["/execute", "1", "ejecutar"]:
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
                    if wallet_live.get("open_trade"):
                        wallet_live["open_trade"]["stop"] = manual_order_data["stop"]
                        wallet_live["open_trade"]["take_profit"] = manual_order_data["tp"]
                        wallet_live["open_trade"]["amount"] = manual_order_data["amount"]
                        wallet_live["open_trade"]["status"] = "open"
                        wallet_live["open_trade"]["timestamp_open"] = now_str()
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

            # CLOSE
            if cmd in ["/close", "c", "cerrar"]:
                wallet_live = load_wallet()
                trade_live = wallet_live.get("open_trade")

                if trade_live:
                    entry = trade_live["entry"]
                    side_close = trade_live["side"]
                    balance = wallet_live["balance"]
                    amount = trade_live.get("amount", balance)

                    if price is None:
                        send_telegram("⏳ Espera un segundo y vuelve a pulsar Cerrar")
                        continue

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

            # PAUSE / RESUME / MODOS
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

        # ============================================================
        # 1) MERCADO / CACHÉ BASE
        #    - Reusa datos cacheados si siguen frescos
        #    - Si toca actualización, recalcula precio, klines y señal
        # ============================================================
        price = cached_price
        signal = cached_signal
        risk_mode = cached_risk_mode
        capital_diff = cached_capital_diff
        klines_map = cached_klines_map

        now = time.time()

        # ============================================================
        # 2) REFRESCO DE MERCADO
        #    - Solo entra si pasó UPDATE_INTERVAL
        #    - O si todavía no hay señal cacheada
        # ============================================================
        if now - last_market_run >= UPDATE_INTERVAL or cached_signal is None:
            ticker = client.get_symbol_ticker(symbol=active_symbol)
            price = float(ticker["price"])

            wallet_live = load_wallet()
            current_balance = wallet_live["balance"]
            trade_live = wallet_live.get("open_trade")

            floating_pnl_amount = 0.0

            # ========================================================
            # 2.1) PnL flotante del trade abierto
            # ========================================================
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

            # ========================================================
            # 2.2) Log de equity
            # ========================================================
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

            # ========================================================
            # 2.3) Descarga de klines por timeframe
            # ========================================================
            klines_map = {}
            for tf in ACTIVE_TIMEFRAMES:
                interval = ALL_TIMEFRAMES[tf]
                klines_map[tf] = get_klines(active_symbol, interval)

            print("🎯 Active symbol:", active_symbol)

            # ========================================================
            # 2.4) Construcción de señal principal
            # ========================================================
            bias_4h = get_htf_bias(klines_map["4h"])
            compression = compression_signal(klines_map["1h"])
            signal = build_signal(price, klines_map)

            # ========================================================
            # 2.5) Estado de riesgo del bot
            # ========================================================
            risk_mode, capital_diff = risk_status(
                CAPITAL_BASE,
                equity_estimate,
                MAX_LOSS_ALLOWED,
                MIN_PROFIT_ALERT,
            )

            # ========================================================
            # 2.6) Guardado en caché
            # ========================================================
            cached_price = price
            cached_signal = signal
            cached_risk_mode = risk_mode
            cached_capital_diff = capital_diff
            cached_klines_map = klines_map
            last_market_run = now

        else:
            # ========================================================
            # 2.7) Reuso de caché
            #    - No recalcula toda la señal, pero refresca lecturas base
            # ========================================================
            bias_4h = get_htf_bias(klines_map["4h"])
            compression = compression_signal(klines_map["1h"])

        # ============================================================
        # 3) DESGLOSE DE LA SEÑAL
        #    - Extrae del dict "signal" las piezas que usa el bot
        # ============================================================
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

        # ============================================================
        # 4) CONTEXTO OPERATIVO
        #    - Contexto general, zona de pullback y última vela 5m
        # ============================================================
        context = get_market_context(radar)
        setup_5m = pullback_zone(klines_map["5m"])
        last_candle_5m = get_last_candle(klines_map["5m"])

        # ============================================================
        # 5) SEÑALES DE ENTRADA TÁCTICAS
        #    - Sniper entry
        #    - Rebound entry
        #    - Fusión en una entry_signal única
        # ============================================================
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

        print("sniper:", sniper, "rebound_signal:", rebound_signal, "entry_signal:", entry_signal)

        # ============================================================
        # 6) MTF ENGINE
        #    - Bias mensual
        #    - Bias semanal
        #    - Trigger intradía
        #    - Decisión MTF final
        # ============================================================
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

        # ============================================================
        # 7) SCORING DE ENTRADA
        #    - Puntuación por MTF, estructura, compresión, sniper,
        #      rebound y entry_signal
        # ============================================================
        score_mtf = 0
        score_structure = 0
        score_compression = 0
        score_sniper = 0
        score_rebound = 0
        score_entry_signal = 0

        if mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_mtf = 2
        elif mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_mtf = 2

        if structure.startswith("📈") and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_structure = 2
        elif structure.startswith("📉") and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_structure = 2

        if compression == "alta":
            score_compression = 2
        elif compression == "media":
            score_compression = 1

        if sniper == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_sniper = 1
        elif sniper == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_sniper = 1

        if rebound_signal == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_rebound = 1
        elif rebound_signal == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_rebound = 1

        if entry_signal == "long" and mtf_decision in ["ENTER_LONG", "SCALP"]:
            score_entry_signal = 1
        elif entry_signal == "short" and mtf_decision in ["ENTER_SHORT", "SCALP"]:
            score_entry_signal = 1

        entry_score = (
            score_mtf
            + score_structure
            + score_compression
            + score_sniper
            + score_rebound
            + score_entry_signal
        )

        print("👉 entry_score:", entry_score)

        # ============================================================
        # 8) DECISIÓN FINAL DE ENTRADA
        #    - Convierte el score + decisión MTF en final_entry
        # ============================================================
        if mtf_decision == "ENTER_LONG" and entry_score >= 4:
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

        # ============================================================
        # 9) COMANDOS DIFERIDOS DEPENDIENTES DE MERCADO
        #    - Aquí encajan RADAR / RIESGO / ORDEN MANUAL
        #    - Porque aquí ya existen price, radar, strength,
        #      structure, mtf_decision, entry_score y final_entry
        # ============================================================

        # ============================================================
        # 9.1) RADAR
        # ============================================================
        if any(normalize_telegram_command(c).strip().lower() in ["/radar", "radar"] for c in commands):
            try:
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

            except Exception as e:
                send_telegram(f"❌ Error en RADAR: {e}")

        # ============================================================
        # 9.2) RIESGO
        # ============================================================
        if any(normalize_telegram_command(c).strip().lower() in ["/risk", "riesgo"] for c in commands):
            try:
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

            except Exception as e:
                send_telegram(f"❌ Error en panel de riesgo: {e}")
            # ============================================================
            # 9.3) ORDEN MANUAL
            #    - Genera propuesta manual usando radar + estado actual
            # ============================================================
            if any(normalize_telegram_command(c).strip().lower() in ["/manual_order", "orden manual"] for c in commands):
                try:
                    wallet_live = load_wallet()

                    if wallet_live.get("open_trade"):
                        send_telegram("ℹ️ Ya hay un trade principal abierto.")
                    else:
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
                            f"Escribe 1 para ejecutar\n"
                            f"Escribe 2 para cancelar"
                        )

                except Exception as e:
                    send_telegram(f"❌ Error en orden manual: {e}")

        # ============================================================
        # 10) FIN DE CICLO
        #    - Pausa mínima antes del siguiente loop
        # ============================================================
        time.sleep(1)

    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
        time.sleep(2)