
import unittest
from unittest.mock import patch

from analysis.unified_analysis import (
    analyze_market,
    _determine_indicator_bias,
)


class TestUnifiedAnalysis(unittest.TestCase):

    def test_empty_candles_return_insufficient_data(self):
        result = analyze_market(
            candles=[],
            symbol="EURUSD",
            timeframe="M5",
        )

        self.assertEqual(
            result["analysis_status"],
            "insufficient_data",
        )

    def test_symbol_is_normalized(self):
        candles = [
            {
               "timestamp": 1790000000,
               "open": 1.1000,
               "high": 1.1010,
               "low": 1.0990,
               "close": 1.1005,
               "tick_volume": 100,
            },
            {
               "timestamp": 1790000300,
               "open": 1.1005,
               "high": 1.1020,
               "low": 1.1000,
               "close": 1.1015,
               "tick_volume": 120,
            },
        ]

        result = analyze_market(
            candles=candles,
            symbol="eurusd",
            timeframe="M5",
        )

   
    def test_indicator_bias_is_bullish(self):
        indicators = {
            "ema_20": 1.12,
            "ema_50": 1.11,
            "ema_200": 1.10,
            "macd": 0.02,
            "macd_signal": 0.01,
            "rsi_14": 60,
            "plus_di_14": 30,
            "minus_di_14": 15,
        }

        result = _determine_indicator_bias(indicators)

        self.assertEqual(result["direction"], "bullish")
        self.assertGreater(result["score"], 0)

    def test_indicator_bias_is_bearish(self):
        indicators = {
            "ema_20": 1.08,
            "ema_50": 1.09,
            "ema_200": 1.10,
            "macd": -0.02,
            "macd_signal": -0.01,
            "rsi_14": 40,
            "plus_di_14": 10,
            "minus_di_14": 25,
        }

        result = _determine_indicator_bias(indicators)

        self.assertEqual(result["direction"], "bearish")
        self.assertLess(result["score"], 0)

    def test_missing_indicators_produce_neutral_bias(self):
        result = _determine_indicator_bias({})

        self.assertEqual(result["direction"], "neutral")
        self.assertEqual(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
