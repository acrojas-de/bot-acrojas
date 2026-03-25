import numpy as np

class ViboraEngine:

    def __init__(self, config):
        self.config = config
        self.max_reentries = 2
        self.reentry_count = 0

    # -------------------------
    # 🧨 DETECTAR ESTAMPIDA
    # -------------------------
    def is_stampede(self, candles):
        ranges = [c['high'] - c['low'] for c in candles[-20:]]
        avg_range = np.mean(ranges[:-1])
        current_range = ranges[-1]

        return current_range > avg_range * 1.8

    # -------------------------
    # 🧹 DETECTAR BARRIDO
    # -------------------------
    def detect_sweep(self, candles):
        last = candles[-1]
        prev_high = max([c['high'] for c in candles[-10:-1]])
        prev_low = min([c['low'] for c in candles[-10:-1]])

        # sweep arriba
        if last['high'] > prev_high and last['close'] < prev_high:
            return "SHORT"

        # sweep abajo
        if last['low'] < prev_low and last['close'] > prev_low:
            return "LONG"

        return None

    # -------------------------
    # 🔁 REENGANCHE
    # -------------------------
    def detect_reengage(self, candles, direction):
        last = candles[-1]

        if direction == "LONG":
            return last['close'] > last['open']

        if direction == "SHORT":
            return last['close'] < last['open']

        return False

    # -------------------------
    # 🎯 DECISIÓN FINAL
    # -------------------------
    def get_vibora_signal(self, candles, bias):
        
        if not self.is_stampede(candles):
            return None

        sweep_direction = self.detect_sweep(candles)

        if sweep_direction is None:
            return None

        # solo si coincide con bias
        if sweep_direction != bias:
            return None

        if self.detect_reengage(candles, sweep_direction):
            return sweep_direction

        return None