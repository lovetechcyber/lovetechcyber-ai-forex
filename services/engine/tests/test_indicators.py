import math
import random
import sys
import unittest

from datetime import datetime, timezone
from pathlib import Path

ENGINE_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_PATH))

from indicators.technical_indicators import (
    IndicatorError,
    calculate_technical_indicators,
    _cross_event,
    _level_cross_event,
)


def generate_candles(count=400):
    random.seed(42)

    now = int(datetime.now(timezone.utc).timestamp())
    start = now - (count * 300)

    candles = []
    price = 1.08000

    for index in range(count):
        # A controlled upward drift with random variation.
        change = 0.00001 + random.uniform(-0.0003, 0.0003)

        open_price = price
        close_price = price + change

        high_price = max(open_price, close_price) + 0.0002
        low_price = min(open_price, close_price) - 0.0002

        candles.append({
            "timestamp": start + (index * 300),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "tick_volume": random.randint(50, 500),
        })

        price = close_price

    return candles


class TechnicalIndicatorTests(unittest.TestCase):

    def test_indicator_calculation(self):
        result = calculate_technical_indicators(
            candles=generate_candles(),
            symbol="EURUSD",
            timeframe="M5",
            exclude_forming_candle=False,
        )

        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["timeframe"], "M5")
        self.assertEqual(result["candles_used"], 400)

        required_indicators = [
            "ema_20",
            "ema_50",
            "ema_200",
            "rsi_14",
            "macd",
            "macd_signal",
            "atr_14",
            "adx_14",
            "stoch_k",
            "stoch_d",
            "bb_bandwidth",
            "atr_percentile_100",
        ]

        for name in required_indicators:
            self.assertIn(name, result["indicators"])

        for name, value in result["indicators"].items():
            if value is not None:
                self.assertTrue(
                    math.isfinite(value),
                    f"{name} returned an invalid value",
                )

    def test_crossover_detection(self):
        self.assertEqual(
            _cross_event(1, 3, 2, 2),
            "bullish_crossover",
        )

        self.assertEqual(
            _cross_event(3, 1, 2, 2),
            "bearish_crossover",
        )

        self.assertEqual(
            _cross_event(1, 1.5, 2, 2),
            "none",
        )

    def test_rsi_level_detection(self):
        self.assertEqual(
            _level_cross_event(25, 32, 30),
            "crossed_above",
        )

        self.assertEqual(
            _level_cross_event(75, 65, 70),
            "crossed_below",
        )

    def test_interpretation_and_events_exist(self):
        result = calculate_technical_indicators(
            candles=generate_candles(),
            symbol="EURUSD",
            timeframe="M5",
            exclude_forming_candle=False,
        )

        self.assertIn(
            "ema_alignment",
            result["interpretation"],
        )

        self.assertIn(
            "trend_strength",
            result["interpretation"],
        )

        self.assertIn(
            "macd_signal",
            result["events"],
        )

        self.assertIn(
            "stochastic",
            result["events"],
        )

        self.assertIn(
            "bollinger_upper",
            result["events"],
        )

    def test_data_quality(self):
        candles = generate_candles()

        # Add a duplicate timestamp.
        candles.append(candles[-1].copy())

        result = calculate_technical_indicators(
            candles=candles,
            symbol="EURUSD",
            timeframe="M5",
            exclude_forming_candle=False,
        )

        self.assertEqual(
            result["data_quality"]["duplicate_candles_removed"],
            1,
        )

    def test_invalid_timeframe(self):
        with self.assertRaises(IndicatorError):
            calculate_technical_indicators(
                candles=generate_candles(),
                symbol="EURUSD",
                timeframe="M1",
                exclude_forming_candle=False,
            )

    def test_invalid_ohlc(self):
        candles = generate_candles()
        candles[10]["high"] = 0.5

        with self.assertRaises(IndicatorError):
            calculate_technical_indicators(
                candles=candles,
                symbol="EURUSD",
                timeframe="M5",
                exclude_forming_candle=False,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)