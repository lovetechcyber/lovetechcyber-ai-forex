
import unittest

from analysis.fair_value_gap import (
    detect_fair_value_gaps,
)

from analysis.market_structure import MarketStructureError


def make_candles(
    highs,
    lows,
    closes=None,
    opens=None,
    timeframe_seconds=300,
):
    candles = []

    if closes is None:
        closes = [
            (high + low) / 2
            for high, low in zip(highs, lows)
        ]

    if opens is None:
        opens = closes.copy()

    for index, (high, low, close, open_price) in enumerate(
        zip(highs, lows, closes, opens)
    ):
        candles.append({
            "timestamp": 1700000000 + (
                index * timeframe_seconds
            ),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
        })

    return candles


class FairValueGapTests(unittest.TestCase):

    def test_detects_bullish_fvg(self):

        candles = make_candles(
            highs=[10, 14, 16],
            lows=[8, 11, 12],
            closes=[9, 13, 15],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(result["total_gaps"], 1)

        gap = result["gaps"][0]

        self.assertEqual(
            gap["type"],
            "bullish_fvg",
        )

        self.assertEqual(
            gap["lower_boundary"],
            10,
        )

        self.assertEqual(
            gap["upper_boundary"],
            12,
        )

        self.assertEqual(gap["midpoint"], 11)
        self.assertEqual(gap["gap_size"], 2)

    def test_detects_bearish_fvg(self):

        candles = make_candles(
            highs=[14, 11, 8],
            lows=[12, 9, 6],
            closes=[13, 10, 7],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(result["total_gaps"], 1)

        gap = result["gaps"][0]

        self.assertEqual(
            gap["type"],
            "bearish_fvg",
        )

        self.assertEqual(
            gap["lower_boundary"],
            8,
        )

        self.assertEqual(
            gap["upper_boundary"],
            12,
        )

        self.assertEqual(gap["midpoint"], 10)
        self.assertEqual(gap["gap_size"], 4)

    def test_no_fvg_when_candles_overlap(self):

        candles = make_candles(
            highs=[10, 12, 11],
            lows=[8, 9, 9],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(result["total_gaps"], 0)

    def test_empty_input(self):

        result = detect_fair_value_gaps(
            [],
            "M5",
        )

        self.assertEqual(
            result["status"],
            "insufficient_data",
        )

        self.assertEqual(result["gaps"], [])

    def test_insufficient_candles(self):

        candles = make_candles(
            highs=[10, 12],
            lows=[8, 9],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(
            result["status"],
            "insufficient_data",
        )

    def test_invalid_timeframe(self):

        candles = make_candles(
            highs=[10, 12, 15],
            lows=[8, 9, 11],
        )

        with self.assertRaises(MarketStructureError):
            detect_fair_value_gaps(
                candles,
                "INVALID",
            )

    def test_bullish_fvg_starts_unmitigated(self):

        candles = make_candles(
            highs=[10, 14, 16],
            lows=[8, 11, 12],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "unmitigated",
        )

        self.assertEqual(
            gap["mitigation_percent"],
            0.0,
        )

    def test_bullish_fvg_partial_mitigation(self):

        candles = make_candles(
            highs=[10, 14, 16, 13],
            lows=[8, 11, 12, 11],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "partially_mitigated",
        )

        self.assertEqual(
            gap["mitigation_percent"],
            50.0,
        )

    def test_bullish_fvg_full_mitigation(self):

        candles = make_candles(
            highs=[10, 14, 16, 12],
            lows=[8, 11, 12, 9],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "fully_mitigated",
        )

        self.assertEqual(
            gap["mitigation_percent"],
            100.0,
        )

        self.assertIsNotNone(
            gap["mitigated_timestamp"]
        )

    def test_bearish_fvg_partial_mitigation(self):

        candles = make_candles(
            highs=[14, 11, 8, 9],
            lows=[12, 9, 6, 7],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "partially_mitigated",
        )

        self.assertEqual(
            gap["mitigation_percent"],
            25.0,
        )

    def test_bearish_fvg_full_mitigation(self):

        candles = make_candles(
            highs=[14, 11, 8, 13],
            lows=[12, 9, 6, 11],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "fully_mitigated",
        )

        self.assertEqual(
            gap["mitigation_percent"],
            100.0,
        )

    def test_bullish_fvg_invalidation(self):

        candles = make_candles(
            highs=[10, 14, 16, 11],
            lows=[8, 11, 12, 8],
            closes=[9, 13, 15, 9],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertTrue(gap["is_invalidated"])
        self.assertEqual(
            gap["status"],
            "fully_mitigated",
        )

        self.assertIsNotNone(
            gap["invalidation_timestamp"]
        )

    def test_no_mitigation_on_creation_candle(self):

        candles = make_candles(
           highs=[10, 14, 16],
           lows=[8, 11, 12],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["status"],
            "unmitigated",
        )

    def test_creation_metadata(self):

        candles = make_candles(
            highs=[10, 14, 16],
            lows=[8, 11, 12],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        gap = result["gaps"][0]

        self.assertEqual(
            gap["creation_index"],
            2,
        )

        self.assertEqual(
            gap["first_candle_index"],
            0,
        )

        self.assertEqual(
            gap["middle_candle_index"],
            1,
        )

        self.assertEqual(
            gap["third_candle_index"],
            2,
        )

    def test_multiple_gaps_are_detected(self):

        candles = make_candles(
          highs=[10, 14, 16, 20, 22],
          lows=[8, 11, 12, 14, 21],
        )

        result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(
            result["total_gaps"],
            2,
        )

    def test_gap_id_is_deterministic(self):

        candles = make_candles(
            highs=[10, 14, 16],
            lows=[8, 11, 12],
        )

        first_result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        second_result = detect_fair_value_gaps(
            candles,
            "M5",
        )

        self.assertEqual(
            first_result["gaps"][0]["id"],
            second_result["gaps"][0]["id"],
        )
    
    def test_bullish_mitigation_percentage_never_decreases(self):
        candles = make_candles(
            highs=[10, 14, 16, 11.5, 11.8],
            lows=[8, 11, 12, 10.8, 11.4],
            closes=[9, 13, 15, 11.2, 11.6],
        )

        result = detect_fair_value_gaps(candles, "M5")
        gap = result["gaps"][0]

        self.assertEqual(gap["status"], "partially_mitigated")
        self.assertEqual(gap["mitigation_percent"], 60.0)

    def test_bearish_mitigation_percentage_never_decreases(self):
        candles = make_candles(
            highs=[14, 11, 8, 9.6, 8.8],
            lows=[12, 9, 6, 8.5, 8.2],
            closes=[13, 10, 7, 9.0, 8.5],
        )

        result = detect_fair_value_gaps(candles, "M5")
        gap = result["gaps"][0]

        self.assertEqual(gap["status"], "partially_mitigated")
        self.assertEqual(gap["mitigation_percent"], 40.0)

    def test_first_touch_full_mitigation_records_first_timestamp(self):
        candles = make_candles(
            highs=[10, 14, 16, 11],
            lows=[8, 11, 12, 9],
            closes=[9, 13, 15, 9.5],
        )

        result = detect_fair_value_gaps(candles, "M5")
        gap = result["gaps"][0]

        self.assertEqual(gap["status"], "fully_mitigated")
        self.assertEqual(gap["mitigation_percent"], 100.0)
        self.assertEqual(
            gap["first_mitigation_timestamp"],
            candles[3]["timestamp"],
        )

    def test_first_mitigation_timestamp_is_preserved(self):
        candles = make_candles(
            highs=[10, 14, 16, 11.5, 11],
            lows=[8, 11, 12, 10.8, 9],
            closes=[9, 13, 15, 11.2, 9.5],
        )

        result = detect_fair_value_gaps(candles, "M5")
        gap = result["gaps"][0]

        self.assertEqual(
            gap["first_mitigation_timestamp"],
            candles[3]["timestamp"],
        )
        self.assertEqual(gap["status"], "fully_mitigated")
        self.assertEqual(gap["mitigation_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
