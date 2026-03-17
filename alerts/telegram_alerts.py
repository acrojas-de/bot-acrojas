import requests
import config
from engines.paper_engine import load_control

BASE_URL = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"


# =========================
# ESTADO DINÁMICO
# =========================

def get_current_trade_mode():
    control = load_control()
    return control.get("trade_mode", config.TRADE_MODE)


def get_mode_leds():
    trade_mode = get_current_trade_mode()

    if trade_mode == "AUTO_LEVERAGE":
        auto_led = "🟢"
        manual_led = "⚪"
    else:
        auto_led = "⚪"
        manual_led = "🟢"

    return manual_led, auto_led


def get_entries_led():
    control = load_control()

    if control.get("allow_new_entries", True):
        return "🟢"
    return "🔴"


# =========================
# TECLADO PRINCIPAL
# =========================

def get_main_keyboard():
    manual_led, auto_led = get_mode_leds()

    return {
        "keyboard": [
            ["📊 Estado", "🎯 Radar"],
            ["📈 Trade", "💼 Cuenta"],
            ["⏸️ Pausar", "▶️ Reanudar"],
            ["❌ Cerrar", "⚙️ Riesgo"],
            [f"{manual_led} Manual", f"{auto_led} Auto"],
            ["🛠️ Orden manual", "🤖 Modo"],
        ],
        "resize_keyboard": True,
    }


# =========================
# PANEL DE BIENVENIDA
# =========================

def send_welcome_panel():
    manual_led, auto_led = get_mode_leds()
    entries_led = get_entries_led()
    trade_mode = get_current_trade_mode()

    message = (
        "🤖 ACROJAS BTC BOT\n\n"
        "Panel de control activado.\n"
        "Usa los botones para consultar el estado del bot.\n\n"
        "⚙️ ESTADO ACTUAL\n"
        f"{manual_led} MANUAL_SPOT\n"
        f"{auto_led} AUTO_LEVERAGE\n"
        f"{entries_led} ENTRADAS ACTIVAS\n\n"
        f"🛠️ Modo activo: {trade_mode}"
    )

    return send_telegram(message, keyboard=True)


# =========================
# ENVÍO DE MENSAJES
# =========================

def send_telegram(message, keyboard=False):
    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": config.CHAT_ID,
        "text": message,
    }

    if keyboard:
        payload["reply_markup"] = get_main_keyboard()

    try:
        r = requests.post(url, json=payload, timeout=10)

        print("Telegram status:", r.status_code)
        print("Telegram response:", r.text)

        return r.status_code == 200

    except Exception as e:
        print("Error enviando Telegram:", e)
        return False


# =========================
# NORMALIZAR BOTONES
# =========================

def normalize_telegram_command(text):
    mapping = {
        "📊 estado": "/status",
        "🎯 radar": "/radar",
        "📈 trade": "/trade",
        "💼 cuenta": "/wallet",
        "⏸️ pausar": "/pause",
        "▶️ reanudar": "/resume",
        "❌ cerrar": "/close",
        "🤖 modo": "/mode",
        "🟢 manual": "/manual",
        "⚪ manual": "/manual",
        "🟢 auto": "/auto",
        "⚪ auto": "/auto",
        "🛠️ orden manual": "/manual_order",
        "⚙️ riesgo": "/risk",
        "1": "/execute",
        "2": "/modify",
        "3": "/cancel",
    }

    return mapping.get(text, text)


# =========================
# LEER COMANDOS
# =========================

def read_telegram_commands(last_update_id=None):
    url = f"{BASE_URL}/getUpdates"

    params = {"timeout": 1}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        commands = []
        new_update_id = last_update_id

        for result in data.get("result", []):
            new_update_id = result["update_id"]

            if "message" in result and "text" in result["message"]:
                text = result["message"]["text"].strip().lower()
                chat_id = str(result["message"]["chat"]["id"])

                if chat_id == str(config.CHAT_ID):
                    text = normalize_telegram_command(text)
                    commands.append(text)

        return commands, new_update_id

    except Exception as e:
        print("Error leyendo comandos Telegram:", e)
        return [], last_update_id