from .orbita_engine import run_orbita_scan
from .formatter_scan import format_orbita_scan


def run_scan(symbol, klines_map):
    data = run_orbita_scan(symbol, klines_map)
    return format_orbita_scan(symbol, data)


def show_asset_menu(symbol):
    return (
        f"🟡 ÓRBITA — {symbol}\n\n"
        "Selecciona acción:\n"
        "📡 Escanear\n"
        "👁 Vigilar\n"
        "🤖 Ejecutar Bot\n"
        "📊 Radar\n"
        "⚠️ Alertas"
    )
    
def show_orbita_menu():
    return (
        "🟡 ÓRBITA — MERCADO\n\n"
        "Selecciona un activo:\n"
        "BTCUSDT\n"
        "ETHUSDT\n"
        "SOLUSDT\n"
        "XRPUSDT\n"
        "BNBUSDT"
    )    