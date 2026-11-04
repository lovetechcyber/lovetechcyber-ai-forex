
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from analysis.multi_timeframe import (
    _calculate_freshness,
    _aggregate_timeframes,
    analyze_multi_timeframe,
)



class TestMultiTimeframeAnalysis(unittest.TestCase):

    def setUp(self):
        self.now = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

        # Historical closed candles for deterministic tests.
        self.candles = []

        start = 1_700_000_000

        for index in range(220):
            price = 1.1000 + (index * 0.0001)

            self.candles.append({
                "timestamp": start + (index * 300),
                "open": price - 0.00005,
                "high": price + 0.00010,
                "low": price - 0.00010,
                "close": price,
                "tick_volume": 100 + index,
            })

    def bullish_indicator_result(self):
        return {
            "indicators": {
                "ema_20": 1.1200,
                "ema_50": 1.1100,
                "ema_200": 1.1000,
                "macd": 0.0010,
                "macd_signal": 0.0005,
                "macd_histogram": 0.0005,
                "rsi_14": 62,
                "plus_di": 30,
                "minus_di": 15,
                "adx_14": 32,
            }
        }

    def bearish_indicator_result(self):
        return {
            "indicators": {
                "ema_20": 1.1000,
                "ema_50": 1.1100,
                "ema_200": 1.1200,
                "macd": -0.0010,
                "macd_signal": -0.0005,
                "macd_histogram": -0.0005,
                "rsi_14": 35,
                "plus_di": 12,
                "minus_di": 28,
                "adx_14": 30,
            }
        }

    @patch("analysis.multi_timeframe.calculate_technical_indicators")
    def test_bullish_timeframe_analysis(self, mock_indicators):
        mock_indicators.return_value = self.bullish_indicator_result()

        result = analyze_multi_timeframe(
            candles_by_timeframe={"H1": self.candles},
            symbol="EURUSD",
            minimum_candles=50,
            now=self.now,
        )

        h1 = result["timeframes"]["H1"]

        self.assertEqual(h1["status"], "completed")
        self.assertEqual(h1["bias"], "bullish")
        self.assertGreater(h1["directional_score"], 0)

    @patch("analysis.multi_timeframe.calculate_technical_indicators")
    def test_bearish_timeframe_analysis(self, mock_indicators):
        mock_indicators.return_value = self.bearish_indicator_result()

        result = analyze_multi_timeframe(
            candles_by_timeframe={"H1": self.candles},
            symbol="EURUSD",
            minimum_candles=50,
            now=self.now,
        )

        h1 = result["timeframes"]["H1"]

        self.assertEqual(h1["status"], "completed")
        self.assertEqual(h1["bias"], "bearish")
        self.assertLess(h1["directional_score"], 0)

    @patch("analysis.multi_timeframe.calculate_technical_indicators")
    def test_insufficient_data_is_reported(self, mock_indicators):
        result = analyze_multi_timeframe(
            candles_by_timeframe={"M5": self.candles[:20]},
            symbol="EURUSD",
            minimum_candles=50,
            now=self.now,
        )

        self.assertEqual(
            result["timeframes"]["M5"]["status"],
            "insufficient_data",
        )
        self.assertEqual(result["overall"]["bias"], "unavailable")
        mock_indicators.assert_not_called()

    @patch("analysis.multi_timeframe.calculate_technical_indicators")
    def test_forming_candle_is_removed(self, mock_indicators):
        mock_indicators.return_value = self.bullish_indicator_result()

        candles = self.candles.copy()

        # This candle opens at the current analysis time and is forming.
        candles.append({
            "timestamp": self.now.timestamp(),
            "open": 1.1200,
            "high": 1.1210,
            "low": 1.1190,
            "close": 1.1205,
            "tick_volume": 50,
        })

        result = analyze_multi_timeframe(
            candles_by_timeframe={"M5": candles},
            symbol="EURUSD",
            minimum_candles=50,
            now=self.now,
        )

        m5 = result["timeframes"]["M5"]

        self.assertEqual(m5["status"], "completed")
        self.assertEqual(m5["forming_candles_removed"], 1)
        self.assertEqual(m5["closed_candles_used"], len(self.candles))

    @patch("analysis.multi_timeframe.calculate_technical_indicators")
    def test_higher_timeframes_have_greater_weight(self, mock_indicators):
        mock_indicators.return_value = self.bullish_indicator_result()

        result = analyze_multi_timeframe(
            candles_by_timeframe={
                "D1": self.candles,
                "H4": self.candles,
                "H1": self.candles,
                "M5": self.candles,
            },
            symbol="EURUSD",
            minimum_candles=50,
            now=self.now,
        )

        self.assertEqual(result["timeframe_weights"]["D1"], 3)
        self.assertEqual(result["timeframe_weights"]["H4"], 3)
        self.assertEqual(result["timeframe_weights"]["M5"], 1)

    def test_empty_input_returns_insufficient_data(self):
        result = analyze_multi_timeframe(
            candles_by_timeframe={},
            symbol="EURUSD",
            now=self.now,
        )

        self.assertEqual(result["analysis_status"], "insufficient_data")
        self.assertEqual(result["overall"]["bias"], "unavailable")

    def test_invalid_symbol_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_multi_timeframe(
                candles_by_timeframe={},
                symbol=" ",
                now=self.now,
            )
    
    
    def test_fresh_candle_is_classified_correctly(self):
        candle_open = 1_800_000_000
        timeframe = "M5"

        result = _calculate_freshness(
            timeframe=timeframe,
            latest_candle_timestamp=candle_open,
            now_timestamp=candle_open + 5 * 60 + 60,
        )

        self.assertEqual(result["status"], "fresh")
        self.assertEqual(result["latest_candle_age_seconds"], 60)

    def test_stale_candle_is_classified_correctly(self):
        candle_open = 1_800_000_000
        timeframe = "M5"

        result = _calculate_freshness(
            timeframe=timeframe,
            latest_candle_timestamp=candle_open,
            now_timestamp=candle_open + 5 * 60 + 25 * 60,
        )

        self.assertEqual(result["status"], "stale")

    def test_stale_timeframe_is_excluded_from_overall_score(self):
        timeframe_results = {
            "D1": {
                "status": "completed",
                "bias": "bullish",
                "directional_score": 5,
                "freshness": {"status": "fresh"},
            },
            "M5": {
                "status": "completed",
                "bias": "bearish",
                "directional_score": -7,
                "freshness": {"status": "stale"},
            },
        }

        result = _aggregate_timeframes(timeframe_results)

        self.assertEqual(result["bias"], "bullish")
        self.assertEqual(result["available_weight"], 3)
        self.assertEqual(result["bullish_weight"], 3)
        self.assertEqual(result["bearish_weight"], 0)


if __name__ == "__main__":
    unittest.main()
