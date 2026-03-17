def ema(values, period):

    k = 2 / (period + 1)
    ema_vals = []

    for i, v in enumerate(values):

        if i == 0:
            ema_vals.append(v)

        else:
            ema_vals.append(v * k + ema_vals[-1] * (1 - k))

    return ema_vals


def rsi(values, period=14):

    gains = []
    losses = []

    for i in range(1, len(values)):

        diff = values[i] - values[i - 1]

        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))
