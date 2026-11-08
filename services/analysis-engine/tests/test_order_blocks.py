import unittest
from unittest.mock import patch

from analysis.market_structure import MarketStructureError
from analysis.order_blocks import detect_order_blocks


BASE_TIMESTAMP = 1_700_000_000


def make_candles(rows, timeframe_seconds=300):
    """
    Each row is:
        (open, high, low, close)
    """
    candles = []

    for index, row in enumerate(rows):
        open_price, high, low, close = row

        candles.append({
            "timestamp": (
                BASE_TIMESTAMP + index * timeframe_seconds
            ),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
        })

    return candles


def make_bos_event(
    direction="bullish",
    break_index=4,
    swing_index=1,
    classification="BOS",
    broken_level=10,
):
    return {
        "event": classification,
        "classification": classification,
        "direction": direction,
        "candle_index": break_index,
        "candle_timestamp": (
            BASE_TIMESTAMP + break_index * 300
        ),
        "candle_close_timestamp": (
            BASE_TIMESTAMP + (break_index + 1) * 300
        ),
        "broken_level": {
            "type": (
                "swing_high"
                if direction == "bullish"
                else "swing_low"
            ),
            "price": broken_level,
            "swing_index": swing_index,
            "confirmation_index": swing_index + 1,
        },
    }


class TestOrderBlockDetection(unittest.TestCase):

    def setUp(self):
        self.candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (13, 14, 10.5, 12),
            (12, 13, 9.5, 11),
        ])

    def run_with_events(self, events, candles=None):
        if candles is None:
            candles = self.candles

        with patch(
            "analysis.order_blocks.detect_structure_breaks"
        ) as mocked:
            mocked.return_value = {
                "status": "completed",
                "events": events,
            }

            return detect_order_blocks(
                candles,
                "M5",
                left_bars=1,
                right_bars=1,
            )

    def test_detects_bullish_order_block(self):
        result = self.run_with_events([
            make_bos_event("bullish", 4, 1)
        ])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["order_block_count"], 1)
        self.assertEqual(result["bullish_count"], 1)

        block = result["order_blocks"][0]

        self.assertEqual(block["type"], "bullish")
        self.assertEqual(block["source_index"], 2)
        self.assertEqual(block["zone_high"], 11)
        self.assertEqual(block["zone_low"], 8)

    def test_detects_bearish_order_block(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (9, 11, 8, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 10, 7, 8),
        ])

        result = self.run_with_events(
            [make_bos_event("bearish", 4, 1)],
            candles,
        )

        self.assertEqual(result["bearish_count"], 1)

        block = result["order_blocks"][0]

        self.assertEqual(block["type"], "bearish")
        self.assertEqual(block["source_index"], 3)

    def test_ignores_initial_break(self):
        result = self.run_with_events([
            make_bos_event(
                "bullish",
                4,
                1,
                classification="initial_break",
            )
        ])

        self.assertEqual(result["order_block_count"], 0)

    def test_ignores_choch(self):
        result = self.run_with_events([
            make_bos_event(
                "bearish",
                4,
                1,
                classification="CHoCH",
            )
        ])

        self.assertEqual(result["order_block_count"], 0)

    def test_ignores_ambiguous_event(self):
        result = self.run_with_events([
            make_bos_event(
                "bullish",
                4,
                1,
                classification="ambiguous",
            )
        ])

        self.assertEqual(result["order_block_count"], 0)

    def test_ignores_non_bos_events(self):
        result = self.run_with_events([
            make_bos_event(
                "bullish",
                4,
                1,
                classification="initial_break",
            ),
            make_bos_event(
                "bearish",
                4,
                1,
                classification="CHoCH",
            ),
        ])

        self.assertEqual(result["order_block_count"], 0)

    def test_does_not_count_pre_bos_mitigation(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 10, 8, 8.5),
            (11, 14, 10, 13),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertEqual(block["status"], "unmitigated")
        self.assertEqual(block["mitigation_percentage"], 0)
        self.assertIsNone(block["first_mitigation_timestamp"])

    def test_tracks_partial_bullish_mitigation(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (12, 12.5, 9.5, 10),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertEqual(block["status"], "partially_mitigated")
        self.assertAlmostEqual(
            block["mitigation_percentage"],
            50,
        )
        self.assertEqual(
            block["first_mitigation_timestamp"],
            candles[5]["timestamp"],
        )

    def test_tracks_full_bullish_mitigation(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (9, 10, 7.5, 9),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertEqual(block["status"], "fully_mitigated")
        self.assertEqual(block["mitigation_percentage"], 100)
        self.assertEqual(
            block["full_mitigation_timestamp"],
            candles[5]["timestamp"],
        )

    def test_mitigation_percentage_never_decreases(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (12, 12.5, 9, 10),
            (12, 12.5, 10.5, 11),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertAlmostEqual(
          block["mitigation_percentage"],
          200 / 3,
        )

    def test_records_first_mitigation_only_once(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (12, 12.5, 9.5, 10),
            (12, 12.5, 8.5, 9),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertEqual(
            block["first_mitigation_timestamp"],
            candles[5]["timestamp"],
        )

    def test_detects_bullish_invalidation(self):
        candles = make_candles([
            (10, 11, 9, 10),
            (10, 12, 9, 11),
            (10, 11, 8, 9),
            (9, 11, 8.5, 10),
            (11, 14, 10, 13),
            (8.5, 9, 7, 7.5),
        ])

        result = self.run_with_events(
            [make_bos_event("bullish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertTrue(block["is_invalidated"])
        self.assertEqual(
            block["invalidation_timestamp"],
            candles[5]["timestamp"],
        )

    def test_detects_bearish_invalidation(self):
        candles = make_candles([
          (10, 11, 9, 10),
          (10, 12, 9, 11),
          (9, 11, 8, 10),
          (10, 12, 9, 11),
          (10, 11, 8, 9),
          (11, 13, 10, 12.5),
        ])

        result = self.run_with_events(
            [make_bos_event("bearish", 4, 1)],
            candles,
        )

        block = result["order_blocks"][0]

        self.assertTrue(block["is_invalidated"])

    def test_does_not_create_duplicate_source_blocks(self):
        result = self.run_with_events([
            make_bos_event("bullish", 4, 1),
            make_bos_event("bullish", 5, 1),
        ])

        self.assertEqual(result["order_block_count"], 1)

    def test_returns_empty_when_no_bos_events(self):
        result = self.run_with_events([])

        self.assertEqual(result["order_block_count"], 0)
        self.assertEqual(result["bullish_count"], 0)
        self.assertEqual(result["bearish_count"], 0)

    def test_rejects_unsupported_timeframe(self):
        with self.assertRaises(MarketStructureError):
            detect_order_blocks(self.candles, "M2")

    def test_returns_insufficient_data_for_empty_input(self):
        result = detect_order_blocks([], "M5")

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["order_block_count"], 0)


if __name__ == "__main__":
    unittest.main()