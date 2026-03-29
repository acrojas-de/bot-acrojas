from handlers.telegram.ranking_handler import handle_ranking 
from handlers.telegram.history_handler import handle_history
from handlers.telegram.select_handler import handle_select
from handlers.telegram.trade_handler import handle_trades, handle_close


def dispatch_command(cmd, context):
    if cmd in ["ranking", "/ranking"]:
        handle_ranking(context)
        return True

    if cmd in ["/history", "history"]:
        handle_history(context)
        return True

    if cmd in ["/select", "select"]:
        result = handle_select(context)
        return ("select", result)

    if cmd in ["/trades", "trades"]:
        return handle_trades(context)

    if cmd in ["/close", "close"]:
        return handle_close(context)
        
    return False