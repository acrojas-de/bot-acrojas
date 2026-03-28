print("🔥 SI VES ESTO, EL CÓDIGO ES NUEVO 🔥")

import time
import requests
import config

from engines.paper_engine import load_control

BASE_URL = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"

# =========================
# ANTI-FLOOD / COOLDOWN
# =========================
telegram_blocked_until = 0


def telegram_available():
    return time.time() >= telegram_blocked_until


def set_telegram_cooldown(seconds):
    global telegram_blocked_until
    telegram_blocked_until = time.time() + max(0, int(seconds))


def get_telegram_cooldown_left():
    remaining = int(telegram_blocked_until - time.time())
    return max(0, remaining)


def handle_telegram_rate_limit(response, prefix="Telegram"):
    global telegram_blocked_until

    if response.status_code != 429:
        return False

    try:
        data = response.json()
        retry_after = data.get("parameters", {}).get("retry_after", 60)
    except Exception:
        retry_after = 60

    set_telegram_cooldown(retry_after)
    print(f"🚫 {prefix} bloqueado por flood. Retry after: {retry_after}s")
    return True


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
    return "🟢" if control.get("allow_new_entries", True) else "🔴"


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
        "one_time_keyboard": False,
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
    if not telegram_available():
        wait_left = get_telegram_cooldown_left()
        print(f"⏳ Telegram en cooldown. Mensaje no enviado. Faltan {wait_left}s")
        return False

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": config.CHAT_ID,
        "text": message,
    }

    if keyboard:
        payload["reply_markup"] = get_main_keyboard()

    try:
        response = requests.post(url, json=payload, timeout=10)

        print("Telegram status:", response.status_code)
        print("Telegram response:", response.text)

        if handle_telegram_rate_limit(response, prefix="Telegram"):
            return False

        return response.status_code == 200

    except Exception as e:
        print("Error enviando Telegram:", e)
        return False


def send_telegram_image(image_path, caption=None):
    if not telegram_available():
        wait_left = get_telegram_cooldown_left()
        print(f"⏳ Telegram en cooldown. Imagen no enviada. Faltan {wait_left}s")
        return False

    url = f"{BASE_URL}/sendPhoto"

    try:
        with open(image_path, "rb") as img:
            response = requests.post(
                url,
                data={
                    "chat_id": config.CHAT_ID,
                    "caption": caption or "",
                },
                files={"photo": img},
                timeout=20,
            )

        print("Telegram image status:", response.status_code)
        print("Telegram image response:", response.text)

        if handle_telegram_rate_limit(response, prefix="Telegram imagen"):
            return False

        return response.status_code == 200

    except Exception as e:
        print("Error enviando imagen:", e)
        return False


# =========================
# NORMALIZAR BOTONES
# =========================
def normalize_telegram_command(text):
    text = (text or "").strip().lower()

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
        "🟡 órbita": "/orbita",
        "📡 escanear": "/scan",
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
        response = requests.get(url, params=params, timeout=10)
        print("Telegram getUpdates status:", response.status_code)

        if response.status_code != 200:
            print("Telegram getUpdates response:", response.text)
            return [], last_update_id

        data = response.json()
        print("RAW TELEGRAM DATA:", data)

        commands = []
        new_update_id = last_update_id

        for result in data.get("result", []):
            update_id = result.get("update_id")
            new_update_id = update_id

            message = result.get("message", {})
            text = message.get("text")

            print("📩 TEXT RECIBIDO:", text)

            if text:
                commands.append(text)

        print("📥 COMMANDS FINAL:", commands)
        return commands, new_update_id

    except Exception as e:
        print("Error leyendo comandos Telegram:", e)
        return [], last_update_id