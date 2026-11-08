
import unittest

from analysis.liquidity_zones import (
    LiquidityZoneError,
    detect_liquidity_zones,
)
from analysis.market_structure import MarketStructureError


def make_candles(highs, lows, closes=None):
    candles = []

    for index, (high, low) in enumerate(zip(highs, lows)):
        close = closes[index] if closes else (high + low) / 2

        candles.append({
            "timestamp": 1_700_000_000 + index * 300,
            "open": close,
            "high": high,
            "low": low,
            "close": close,
        })

    return candles


def make_atr_candles(count=220):
    """Generate valid, regularly spaced candles for ATR tests."""
    candles = []

    for index in range(count):
        close = 1.1000 + (index * 0.00001)
        spread = 0.0005

        candles.append({
            "timestamp": 1_700_000_000 + index * 300,
            "open": close,
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "tick_volume": 100 + index,
        })

    return candles


class TestLiquidityZones(unittest.TestCase):

    def setUp(self):
        self.equal_high_candles = make_candles(
            highs=[
                9, 10, 9,
                10.04, 9,
                10.02, 9,
                9.5, 9,
            ],
            lows=[
                8, 8.5, 8,
                8.5, 8,
                8.5, 8,
                8.5, 8,
            ],
        )

        self.equal_low_candles = make_candles(
            highs=[
                10, 9, 10,
                9, 10,
                9, 10,
                9, 10,
            ],
            lows=[
                9, 8, 9,
                8.02, 9,
                7.99, 9,
                8.5, 9,
            ],
        )

        self.atr_candles = make_atr_candles()

    def test_detects_equal_highs(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["equal_high_count"], 1)

        zone = result["equal_highs"][0]

        self.assertEqual(zone["type"], "EQH")
        self.assertEqual(zone["liquidity_side"], "buy_side")
        self.assertEqual(zone["member_count"], 3)
        self.assertAlmostEqual(zone["zone_low"], 10.0)
        self.assertAlmostEqual(zone["zone_high"], 10.04)

    def test_detects_equal_lows(self):
        result = detect_liquidity_zones(
            self.equal_low_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["equal_low_count"], 1)

        zone = result["equal_lows"][0]

        self.assertEqual(zone["type"], "EQL")
        self.assertEqual(zone["liquidity_side"], "sell_side")
        self.assertEqual(zone["member_count"], 3)
        self.assertAlmostEqual(zone["zone_low"], 7.99)
        self.assertAlmostEqual(zone["zone_high"], 8.02)

    def test_detects_buy_side_liquidity_sweep(self):
        candles = self.equal_high_candles.copy()

        candles[7]["high"] = 10.20
        candles[7]["close"] = 10.00
        candles[7]["open"] = 9.80

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]

        self.assertTrue(zone["is_swept"])
        self.assertEqual(zone["status"], "swept")
        self.assertEqual(
            zone["sweep"]["direction"],
            "buy_side_liquidity_sweep",
        )
        self.assertEqual(zone["sweep_index"], 7)

    def test_detects_sell_side_liquidity_sweep(self):
        candles = self.equal_low_candles.copy()

        candles[7]["low"] = 7.80
        candles[7]["close"] = 8.20
        candles[7]["open"] = 8.40

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_lows"][0]

        self.assertTrue(zone["is_swept"])
        self.assertEqual(zone["status"], "swept")
        self.assertEqual(
            zone["sweep"]["direction"],
            "sell_side_liquidity_sweep",
        )
        self.assertEqual(zone["sweep_index"], 7)

    def test_zone_remains_unswept_without_reclaim(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]

        self.assertFalse(zone["is_swept"])
        self.assertEqual(zone["status"], "unswept")
        self.assertIsNone(zone["sweep_timestamp"])

    def test_sweep_before_zone_confirmation_is_ignored(self):
        candles = make_candles(
            highs=[
                9, 10, 9,
                10.04, 9,
                10.20, 9,
                10.02, 9,
                9.5,
            ],
            lows=[
                8, 8.5, 8,
                8.5, 8,
                8.5, 8,
                8.5, 8,
                8.5,
            ],
            closes=[
                8.5, 9.5, 8.5,
                9.5, 8.5,
                10.00, 8.5,
                9.5, 8.5,
                9.0,
            ],
        )

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["equal_high_count"], 1)

        zone = result["equal_highs"][0]

        self.assertEqual(zone["confirmation_index"], 8)
        self.assertFalse(zone["is_swept"])
        self.assertEqual(zone["status"], "unswept")

    def test_zone_confirmation_waits_for_latest_member(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]

        self.assertEqual(
            zone["confirmation_index"],
            max(
                member["confirmation_index"]
                for member in zone["members"]
            ),
        )
        self.assertEqual(zone["confirmation_index"], 6)

    def test_tolerance_rejects_unrelated_swing_levels(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.001,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["equal_high_count"], 0)

    def test_empty_candles_return_insufficient_data(self):
        result = detect_liquidity_zones(
            [],
            "M5",
            tolerance=0.05,
        )

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["zones"], [])

    def test_invalid_timeframe_raises_error(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M2",
                tolerance=0.05,
            )

    def test_zero_tolerance_raises_error(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=0,
            )

    def test_negative_tolerance_raises_error(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=-0.01,
            )

    def test_non_finite_tolerance_raises_error(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=float("inf"),
            )

    def test_duplicate_timestamps_are_rejected(self):
        candles = self.equal_high_candles.copy()
        candles[2] = candles[1].copy()

        with self.assertRaises(MarketStructureError):
            detect_liquidity_zones(
                candles,
                "M5",
                tolerance=0.05,
                left_bars=1,
                right_bars=1,
            )

    def test_malformed_candle_is_rejected(self):
        candles = self.equal_high_candles.copy()
        candles[2]["high"] = candles[2]["low"] - 1

        with self.assertRaises(MarketStructureError):
            detect_liquidity_zones(
                candles,
                "M5",
                tolerance=0.05,
                left_bars=1,
                right_bars=1,
            )

    def test_zone_ids_are_deterministic(self):
        first = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        second = detect_liquidity_zones(
            list(reversed(self.equal_high_candles)),
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        first_ids = [zone["id"] for zone in first["zones"]]
        second_ids = [zone["id"] for zone in second["zones"]]

        self.assertEqual(first_ids, second_ids)

    def test_zone_counts_are_consistent(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(
            result["buy_side_zone_count"],
            result["equal_high_count"],
        )
        self.assertEqual(
            result["sell_side_zone_count"],
            result["equal_low_count"],
        )
        self.assertEqual(
            result["swept_zone_count"] + result["unswept_zone_count"],
            len(result["zones"]),
        )

    def test_multiple_price_clusters_are_not_merged(self):
        candles = make_candles(
            highs=[9, 10, 9, 10.04, 9, 10.08, 9],
            lows=[8, 8.5, 8, 8.5, 8, 8.5, 8],
        )

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["equal_high_count"], 1)
        self.assertEqual(result["equal_highs"][0]["member_count"], 2)

    def test_tolerance_excludes_swing_outside_cluster_boundary(self):
        result = detect_liquidity_zones(
            self.equal_high_candles,
            "M5",
            tolerance=0.019,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["equal_high_count"], 0)

    def test_sweep_close_exactly_at_zone_boundary_counts(self):
        candles = self.equal_high_candles.copy()

        candles[7]["high"] = 10.20
        candles[7]["close"] = 10.04
        candles[7]["open"] = 10.00

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]
        self.assertTrue(zone["is_swept"])

    def test_close_above_eqh_boundary_does_not_count_as_reclaim(self):
        candles = self.equal_high_candles.copy()

        candles[7]["high"] = 10.20
        candles[7]["close"] = 10.05
        candles[7]["open"] = 10.00

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]
        self.assertFalse(zone["is_swept"])

    def test_first_sweep_is_preserved_when_multiple_sweeps_occur(self):
        candles = self.equal_high_candles.copy()

        candles[7]["high"] = 10.20
        candles[7]["close"] = 10.00
        candles[7]["open"] = 9.80

        candles[8]["high"] = 10.30
        candles[8]["close"] = 10.00
        candles[8]["open"] = 9.80

        result = detect_liquidity_zones(
            candles,
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        zone = result["equal_highs"][0]

        self.assertTrue(zone["is_swept"])
        self.assertEqual(zone["sweep_index"], 7)
        self.assertEqual(
            zone["sweep_timestamp"],
            candles[7]["timestamp"],
        )

    def test_left_bars_zero_is_rejected(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=0.05,
                left_bars=0,
                right_bars=1,
            )

    def test_right_bars_zero_is_rejected(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=0.05,
                left_bars=1,
                right_bars=0,
            )

    def test_boolean_swing_configuration_is_rejected(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                self.equal_high_candles,
                "M5",
                tolerance=0.05,
                left_bars=True,
                right_bars=1,
            )

    def test_insufficient_swing_data_returns_no_zones(self):
        result = detect_liquidity_zones(
            self.equal_high_candles[:3],
            "M5",
            tolerance=0.05,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["zones"], [])
        self.assertEqual(result["equal_high_count"], 0)
        self.assertEqual(result["equal_low_count"], 0)

    def test_absolute_mode_remains_default(self):
        result = detect_liquidity_zones(
            candles=self.equal_high_candles,
            timeframe="M5",
            tolerance=0.001,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["tolerance_mode"], "absolute")
        self.assertEqual(result["tolerance"], 0.001)
        self.assertIsNone(result["atr"])

    def test_atr_mode_returns_adaptive_tolerance(self):
        result = detect_liquidity_zones(
            candles=self.atr_candles,
            timeframe="M5",
            tolerance_mode="atr",
            atr_multiplier=0.10,
            left_bars=1,
            right_bars=1,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["tolerance_mode"], "atr")
        self.assertIsNotNone(result["atr"])
        self.assertGreater(result["atr"], 0)
        self.assertAlmostEqual(
            result["tolerance"],
            result["atr"] * 0.10,
        )

    def test_invalid_tolerance_mode_is_rejected(self):
        with self.assertRaises(LiquidityZoneError):
            detect_liquidity_zones(
                candles=self.equal_high_candles,
                timeframe="M5",
                tolerance=0.05,
                tolerance_mode="unknown",
            )

    def test_invalid_atr_multiplier_is_rejected(self):
        for multiplier in (
            0,
            -0.1,
            float("inf"),
            float("nan"),
            True,
        ):
            with self.subTest(multiplier=multiplier):
                with self.assertRaises(LiquidityZoneError):
                    detect_liquidity_zones(
                        candles=self.atr_candles,
                        timeframe="M5",
                        tolerance_mode="atr",
                        atr_multiplier=multiplier,
                    )

    def test_atr_mode_does_not_fall_back_to_absolute_tolerance(self):
        short_history = self.atr_candles[:10]

        result = detect_liquidity_zones(
            candles=short_history,
            timeframe="M5",
            tolerance_mode="atr",
            atr_multiplier=0.10,
        )

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(
            result["reason"],
            "insufficient_atr_history",
        )
        self.assertIsNone(result["tolerance"])


if __name__ == "__main__":
    unittest.main()
