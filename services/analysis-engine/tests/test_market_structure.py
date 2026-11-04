
import unittest

from analysis.market_structure import (
    MarketStructureError,
    detect_swings,
    detect_structure_breaks,
    detect_liquidity_sweeps,
)


def make_candles(highs, lows, closes=None, timeframe_seconds=300):
    """Build valid chronological OHLC candles for tests."""
    candles = []

    if closes is None:
        closes = [
            (high + low) / 2
            for high, low in zip(highs, lows)
        ]

    for index, (high, low, close) in enumerate(
        zip(highs, lows, closes)
    ):
        candles.append(
            {
                "timestamp": 1_700_000_000 + (
                    index * timeframe_seconds
                ),
                "open": close,
                "high": high,
                "low": low,
                "close": close,
            }
        )

    return candles


class TestSwingDetection(unittest.TestCase):

    def test_detects_swing_high(self):
        candles = make_candles(
            highs=[10, 12, 16, 13, 11],
            lows=[8, 9, 10, 9, 8],
        )

        result = detect_swings(
            candles, "M5", left_bars=1, right_bars=1
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(result["swing_high_count"], 1)

        swing = next(
            item for item in result["swing_highs"]
            if item["index"] == 2
        )

        self.assertEqual(swing["price"], 16)

    def test_detects_swing_low(self):
        candles = make_candles(
            highs=[12, 13, 14, 13, 12],
            lows=[10, 8, 5, 9, 10],
        )

        result = detect_swings(
            candles, "M5", left_bars=1, right_bars=1
        )

        self.assertEqual(result["status"], "completed")

        swing = next(
            item for item in result["swing_lows"]
            if item["index"] == 2
        )

        self.assertEqual(swing["price"], 5)

    def test_swing_has_confirmation_metadata(self):
        candles = make_candles(
            highs=[10, 15, 12, 11],
            lows=[8, 9, 10, 8],
        )

        result = detect_swings(
            candles, "M5", left_bars=1, right_bars=1
        )

        swing = next(
            item for item in result["swing_highs"]
            if item["index"] == 1
        )

        self.assertEqual(swing["confirmation_index"], 2)
        self.assertEqual(
            swing["confirmation_timestamp"],
            candles[2]["timestamp"] + 300,
        )
        self.assertIn("confirmation_time", swing)

    def test_insufficient_swing_data(self):
        candles = make_candles(
            highs=[10, 12],
            lows=[8, 9],
        )

        result = detect_swings(
            candles, "M5", left_bars=2, right_bars=2
        )

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["swings"], [])

    def test_duplicate_timestamps_are_rejected(self):
        candles = make_candles(
            highs=[10, 12, 11],
            lows=[8, 9, 7],
        )

        candles[1]["timestamp"] = candles[0]["timestamp"]

        with self.assertRaises(MarketStructureError):
            detect_swings(
                candles, "M5", left_bars=1, right_bars=1
            )

    def test_invalid_ohlc_is_rejected(self):
        candles = make_candles(
            highs=[10, 12, 11],
            lows=[8, 9, 7],
        )

        candles[1]["high"] = 5

        with self.assertRaises(MarketStructureError):
            detect_swings(
                candles, "M5", left_bars=1, right_bars=1
            )

    def test_invalid_timeframe_is_rejected(self):
        candles = make_candles(
            highs=[10, 12, 11],
            lows=[8, 9, 7],
        )

        with self.assertRaises(MarketStructureError):
            detect_swings(
                candles, "M1", left_bars=1, right_bars=1
            )


class TestStructureBreakDetection(unittest.TestCase):

    def test_first_bullish_break_is_initial_break(self):
        candles = make_candles(
            highs=[11, 15, 12, 16, 14, 17],
            lows=[9, 10, 8, 10, 9, 11],
            closes=[10, 12, 11, 16, 13, 16.5],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(result["initial_break_count"], 1)

        first_event = result["events"][0]

        self.assertEqual(
            first_event["classification"], "initial_break"
        )
        self.assertEqual(first_event["direction"], "bullish")
        self.assertEqual(result["current_direction"], "bullish")

    def test_bullish_bos(self):
        candles = make_candles(
            highs=[11, 15, 12, 16, 18, 14, 20],
            lows=[9, 10, 8, 10, 12, 9, 13],
            closes=[10, 12, 11, 16, 15, 13, 19],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        classifications = [
            event["classification"]
            for event in result["events"]
        ]

        self.assertIn("initial_break", classifications)
        self.assertIn("BOS", classifications)
        self.assertEqual(result["current_direction"], "bullish")

    def test_bearish_bos(self):
        candles = make_candles(
            highs=[20, 18, 19, 17, 16, 18, 15],
            lows=[15, 12, 14, 11, 10, 12, 8],
            closes=[18, 17, 16, 12, 11, 13, 9],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        classifications = [
            event["classification"]
            for event in result["events"]
        ]

        self.assertIn("initial_break", classifications)
        self.assertIn("BOS", classifications)
        self.assertEqual(result["current_direction"], "bearish")

    def test_bearish_choch_after_bullish_structure(self):
        candles = make_candles(
            highs=[11, 15, 12, 16, 14, 13, 12, 11, 10],
            lows=[9, 10, 8, 10, 12, 9, 7, 8, 6],
            closes=[10, 12, 11, 16, 13, 10, 9, 9, 6.5],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        classifications = [
            event["classification"]
            for event in result["events"]
        ]

        self.assertIn("initial_break", classifications)
        self.assertIn("CHoCH", classifications)

        choch_event = next(
            event for event in result["events"]
            if event["classification"] == "CHoCH"
        )

        self.assertEqual(choch_event["direction"], "bearish")
        self.assertEqual(
            choch_event["previous_direction"], "bullish"
        )
        self.assertEqual(
            choch_event["resulting_direction"], "bearish"
        )
        self.assertEqual(result["current_direction"], "bearish")

    def test_wick_only_break_does_not_count(self):
        candles = make_candles(
            highs=[11, 15, 12, 17, 13],
            lows=[9, 10, 8, 10, 9],
            closes=[10, 12, 11, 14, 12],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        self.assertEqual(result["structure_break_count"], 0)
        self.assertEqual(result["current_direction"], "unknown")

    def test_no_break_before_swing_confirmation(self):
        candles = make_candles(
            highs=[11, 15, 12, 16, 14],
            lows=[9, 10, 8, 10, 9],
            closes=[10, 12, 11, 16, 13],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        for event in result["events"]:
            if "broken_level" in event:
                self.assertLess(
                    event["broken_level"]["confirmation_index"],
                    event["candle_index"],
                )

    def test_broken_level_does_not_generate_duplicate_events(self):
        candles = make_candles(
            highs=[11, 15, 12, 16, 14, 14, 14],
            lows=[9, 10, 8, 10, 9, 9, 9],
            closes=[10, 12, 11, 16, 14, 14, 14],
        )

        result = detect_structure_breaks(
            candles, "M5", left_bars=1, right_bars=1
        )

        broken_levels = [
            event["broken_level"]["swing_index"]
            for event in result["events"]
            if "broken_level" in event
        ]

        self.assertEqual(
            len(broken_levels),
            len(set(broken_levels)),
        )

    def test_empty_input_returns_insufficient_data(self):
        result = detect_structure_breaks(
            [], "M5", left_bars=1, right_bars=1
        )

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["events"], [])

    def test_invalid_input_is_rejected(self):
        invalid_candles = [
            {
                "timestamp": 1_700_000_000,
                "open": 1.1000,
                "high": 1.0900,
                "low": 1.0800,
                "close": 1.0950,
            }
        ]

        with self.assertRaises(MarketStructureError):
            detect_structure_breaks(
                invalid_candles,
                "M5",
                left_bars=1,
                right_bars=1,
            )

    def test_invalid_timeframe_is_rejected(self):
        candles = make_candles(
            highs=[10, 12, 11],
            lows=[8, 9, 7],
        )

        with self.assertRaises(MarketStructureError):
            detect_structure_breaks(
                candles, "M1", left_bars=1, right_bars=1
            )


class TestLiquiditySweepDetection(unittest.TestCase):

    def test_bullish_side_liquidity_sweep(self):
        highs = [10, 11, 12, 11, 10, 13, 14]
        lows = [9, 10, 11, 10, 9, 10, 10]
        closes = [9.5, 10.5, 11.5, 10.5, 9.5, 12, 11]

        candles = make_candles(highs, lows, closes)

        result = detect_liquidity_sweeps(
            candles,
            "M5",
            left_bars=1,
            right_bars=1,
        )

        self.assertGreaterEqual(result["buy_side_sweeps"], 1)

        event = next(
            event for event in result["events"]
            if event["type"] == "buy_side_liquidity_sweep"
        )

        self.assertEqual(event["level"], 12)
        self.assertEqual(event["wick_extreme"], 14)

    def test_bearish_side_liquidity_sweep(self):
        highs = [13, 12, 11, 12, 13, 10, 12]
        lows = [12, 11, 10, 11, 12, 9, 8]
        closes = [12.5, 11.5, 10.5, 11.5, 12.5, 9.5, 11]

        candles = make_candles(highs, lows, closes)

        result = detect_liquidity_sweeps(
            candles,
            "M5",
            left_bars=1,
            right_bars=1,
        )

        self.assertGreaterEqual(result["sell_side_sweeps"], 1)

        event = next(
            event for event in result["events"]
            if event["type"] == "sell_side_liquidity_sweep"
        )

        self.assertEqual(event["level"], 10)
        self.assertEqual(event["wick_extreme"], 8)

    def test_wick_without_reclaim_is_not_sweep(self):
        highs = [10, 11, 12, 11, 10, 13, 14]
        lows = [9, 10, 11, 10, 9, 10, 12]
        closes = [9.5, 10.5, 11.5, 10.5, 9.5, 12, 13]

        candles = make_candles(highs, lows, closes)

        result = detect_liquidity_sweeps(
            candles,
            "M5",
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["total_sweeps"], 0)

    def test_no_sweep_without_wick_breach(self):
        highs = [10, 11, 12, 11, 10, 11, 11]
        lows = [9, 10, 11, 10, 9, 10, 10]
        closes = [9.5, 10.5, 11.5, 10.5, 9.5, 10.5, 10.5]

        candles = make_candles(highs, lows, closes)

        result = detect_liquidity_sweeps(
            candles,
            "M5",
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["total_sweeps"], 0)

    def test_empty_input(self):
        result = detect_liquidity_sweeps(
            [],
            "M5",
        )

        self.assertEqual(
            result["status"],
            "insufficient_data",
        )
        self.assertEqual(result["events"], [])

    def test_invalid_timeframe(self):
        with self.assertRaises(MarketStructureError):
            detect_liquidity_sweeps(
                [],
                "INVALID",
            )


if __name__ == "__main__":
    unittest.main()
