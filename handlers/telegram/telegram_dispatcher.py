from handlers.telegram.ranking_handler import handle_ranking
from handlers.telegram.history_handler import handle_history

def dispatch_command(cmd, context):
    if cmd in ["ranking", "/ranking"]:
        handle_ranking(context)
        return True

    if cmd in ["/history", "history"]:
        handle_history(context)
        return True

    return False