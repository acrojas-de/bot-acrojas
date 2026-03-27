def format_orbita_scan(symbol, data):

    return (
        f"🟡 ESCANEO ÓRBITA — {symbol}\n\n"

        f"Bias:\n"
        f"• {data['bias']}\n\n"

        f"Estructura:\n"
        f"• Compresión: {'Sí' if data['compression'] else 'No'}\n"
        f"• Rebound: {'Sí' if data['rebound'] else 'No'}\n\n"

        f"Señales:\n"
        f"• Sniper: {'Sí' if data['sniper'] else 'No'}\n"
        f"• Víbora: {'Sí' if data['vibora'] else 'No'}\n\n"

        f"Riesgo:\n"
        f"• {data['risk']}\n\n"

        f"Score: {data['score']}\n\n"

        f"Conclusión:\n"
        f"{data['state']}"
    )