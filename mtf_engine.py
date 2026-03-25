class MTFEngine:

    def get_monthly_bias(self, data_1d):
        if len(data_1d) < 2:
            return "neutral"

        first = float(data_1d[0][4])
        last = float(data_1d[-1][4])

        if last > first:
            return "bullish"
        elif last < first:
            return "bearish"
        return "neutral"

    def get_weekly_bias(self, data_4h):
        if len(data_4h) < 2:
            return "neutral"

        first = float(data_4h[0][4])
        last = float(data_4h[-1][4])

        if last > first:
            return "bullish"
        elif last < first:
            return "bearish"
        return "neutral"

    def get_intraday_trigger(self, data_5m, data_1m):
        if len(data_5m) < 2 or len(data_1m) < 2:
            return "wait"

        last_5m = float(data_5m[-1][4])
        prev_5m = float(data_5m[-2][4])

        last_1m = float(data_1m[-1][4])
        prev_1m = float(data_1m[-2][4])

        if last_5m > prev_5m and last_1m > prev_1m:
            return "long"
        elif last_5m < prev_5m and last_1m < prev_1m:
            return "short"

        return "wait"

    def decide(self, monthly_bias, weekly_bias, trigger):
        if trigger == "wait":
            return "NO TRADE"

        if monthly_bias == weekly_bias:
            if trigger == "long" and monthly_bias == "bullish":
                return "ENTER LONG"
            elif trigger == "short" and monthly_bias == "bearish":
                return "ENTER SHORT"

        if trigger in ["long", "short"]:
            return "SCALP"

        return "NO TRADE"