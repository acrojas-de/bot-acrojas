def get_selected_symbol(default_symbol, manual_symbol=None):
    if manual_symbol:
        clean = manual_symbol.strip().upper()
        if clean:
            return clean
    return default_symbol