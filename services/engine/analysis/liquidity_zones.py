from __future__ import annotations

import math
from typing import Any

from analysis.market_structure import (
    TIMEFRAME_SECONDS,
    MarketStructureError,
    _prepare_candles,
    detect_swings,
)
from indicators.technical_indicators import (
    IndicatorError,
    calculate_technical_indicators,
)


class LiquidityZoneError(ValueError):
    """Raised when liquidity-zone input or configuration is invalid."""


def _validate_tolerance(tolerance: Any) -> float:
    if isinstance(tolerance, bool):
        raise LiquidityZoneError("tolerance must be a positive number")

    try:
        value = float(tolerance)
    except (TypeError, ValueError):
        raise LiquidityZoneError("tolerance must be a positive number")

    if not math.isfinite(value) or value <= 0:
        raise LiquidityZoneError("tolerance must be a positive finite number")

    return value

def _validate_atr_multiplier(multiplier: Any) -> float:
    if isinstance(multiplier, bool):
        raise LiquidityZoneError(
            "atr_multiplier must be a positive number"
        )

    try:
        value = float(multiplier)
    except (TypeError, ValueError):
        raise LiquidityZoneError(
            "atr_multiplier must be a positive number"
        )

    if not math.isfinite(value) or value <= 0:
        raise LiquidityZoneError(
            "atr_multiplier must be a positive finite number"
        )

    return value

def _make_clusters(
    swings: list[dict],
    zone_type: str,
    tolerance: float,
) -> list[list[dict]]:
    """
    Group confirmed swings by price.

    Clusters are anchored to their first (lowest-price) member. This prevents
    transitive chaining from creating zones wider than the configured tolerance.
    """
    if not swings:
        return []

    ordered = sorted(
        swings,
        key=lambda swing: (
            float(swing["price"]),
            int(swing["index"]),
        ),
    )

    clusters: list[list[dict]] = []
    current: list[dict] = []
    anchor_price: float | None = None

    for swing in ordered:
        price = float(swing["price"])

        if not current:
            current = [swing]
            anchor_price = price
            continue

        if price - anchor_price <= tolerance:
            current.append(swing)
        else:
            if len(current) >= 2:
                clusters.append(current)

            current = [swing]
            anchor_price = price

    if len(current) >= 2:
        clusters.append(current)

    return clusters


def _zone_id(
    timeframe: str,
    zone_type: str,
    members: list[dict],
) -> str:
    indices = "-".join(
        str(member["index"])
        for member in sorted(members, key=lambda item: item["index"])
    )
    return f"{zone_type}-{timeframe}-{indices}"


def _build_zone(
    members: list[dict],
    zone_type: str,
    timeframe: str,
    tolerance: float,
    candles: list[dict],
) -> dict:
    members = sorted(members, key=lambda item: item["index"])

    prices = [float(member["price"]) for member in members]
    zone_low = min(prices)
    zone_high = max(prices)

    latest_confirmed = max(
        members,
        key=lambda item: (
            int(item["confirmation_index"]),
            int(item["index"]),
        ),
    )

    confirmation_index = int(latest_confirmed["confirmation_index"])
    confirmation_timestamp = latest_confirmed["confirmation_timestamp"]

    # A zone is not actionable until the latest member swing is confirmed.
    sweep = None

    for candle_index in range(confirmation_index + 1, len(candles)):
        candle = candles[candle_index]
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])
        candle_close = float(candle["close"])

        if zone_type == "EQH":
            swept = candle_high > zone_high and candle_close <= zone_high
            sweep_direction = "buy_side_liquidity_sweep"
        else:
            swept = candle_low < zone_low and candle_close >= zone_low
            sweep_direction = "sell_side_liquidity_sweep"

        if swept:
            sweep = {
                "direction": sweep_direction,
                "index": candle_index,
                "timestamp": candle["timestamp"],
                "price": (
                    candle_high if zone_type == "EQH" else candle_low
                ),
                "close": candle_close,
            }
            break

    return {
        "id": _zone_id(timeframe, zone_type, members),
        "type": zone_type,
        "liquidity_side": (
            "buy_side" if zone_type == "EQH" else "sell_side"
        ),
        "timeframe": timeframe,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "midpoint": (zone_low + zone_high) / 2,
        "size": zone_high - zone_low,
        "tolerance": tolerance,
        "member_count": len(members),
        "members": [
            {
                "index": int(member["index"]),
                "timestamp": member["timestamp"],
                "price": float(member["price"]),
                "confirmation_index": int(member["confirmation_index"]),
                "confirmation_timestamp": member["confirmation_timestamp"],
            }
            for member in members
        ],
        "formation_timestamp": members[0]["timestamp"],
        "confirmation_index": confirmation_index,
        "confirmation_timestamp": confirmation_timestamp,
        "status": "swept" if sweep else "unswept",
        "is_swept": sweep is not None,
        "sweep": sweep,
        "sweep_timestamp": sweep["timestamp"] if sweep else None,
        "sweep_index": sweep["index"] if sweep else None,
    }


def detect_liquidity_zones(
    candles: list[dict],
    timeframe: str,
    tolerance: float | None = None,
    left_bars: int = 3,
    right_bars: int = 3,
    tolerance_mode: str = "absolute",
    atr_multiplier: float = 0.10,
) -> dict:
    """
    Detect Equal High (EQH) and Equal Low (EQL) liquidity zones.
    tolerance: Absolute price tolerance; required in absolute mode.
    tolerance_mode: "absolute" or "atr".
    atr_multiplier: ATR multiplier used in ATR mode (default 0.10).

    Args:
        candles: OHLC candles, oldest first or unordered.
        timeframe: Supported timeframe, e.g. M5, M15, H1, H4, D1.
        tolerance: Maximum price distance from the cluster's anchor price.
        left_bars: Number of candles to the left for swing confirmation.
        right_bars: Number of candles to the right for swing confirmation.

    A zone requires at least two confirmed swing highs or lows.
    Sweeps are only evaluated on candles after the zone's confirmation candle.
    """
    if not isinstance(timeframe, str) or timeframe not in TIMEFRAME_SECONDS:
        raise LiquidityZoneError(f"Unsupported timeframe: {timeframe!r}")

    if isinstance(left_bars, bool) or not isinstance(left_bars, int) or left_bars < 1:
        raise LiquidityZoneError("left_bars must be an integer greater than or equal to 1")

    if isinstance(right_bars, bool) or not isinstance(right_bars, int) or right_bars < 1:
        raise LiquidityZoneError("right_bars must be an integer greater than or equal to 1")

    if tolerance_mode not in ("absolute", "atr"):
        raise LiquidityZoneError(
            "tolerance_mode must be 'absolute' or 'atr'"
        )

    atr_value = None
    multiplier = None

    if tolerance_mode == "absolute":
        price_tolerance = _validate_tolerance(tolerance)

    else:
        multiplier = _validate_atr_multiplier(atr_multiplier)
        price_tolerance = None

    try:
        prepared = _prepare_candles(candles)

        if tolerance_mode == "atr":
            # The indicator engine requires tick_volume.
            # Zero is supplied only when the source does not provide it.
            indicator_candles = []

            for candle in prepared:
                indicator_candle = dict(candle)
                indicator_candle.setdefault("tick_volume", 0)
                indicator_candles.append(indicator_candle)

            indicator_result = calculate_technical_indicators(
                candles=indicator_candles,
                symbol="LIQUIDITY",
                timeframe=timeframe,
                exclude_forming_candle=True,
            )

            atr_value = indicator_result["indicators"]["atr_14"]

            # Align structure detection with the last closed candle
            # used by the indicator engine.
            latest_closed_timestamp = int(
                indicator_result["candle_timestamp"]
            )

            prepared = [
                candle
                for candle in prepared
                if int(candle["timestamp"]) <= latest_closed_timestamp
            ]

            if atr_value is not None:
                price_tolerance = atr_value * multiplier

        swing_result = detect_swings(
            prepared,
            timeframe,
            left_bars=left_bars,
            right_bars=right_bars,
        )

    except MarketStructureError:
        raise

    except IndicatorError as exc:
        raise LiquidityZoneError(
            f"ATR calculation failed: {exc}"
        ) from exc

    except (TypeError, ValueError, KeyError) as exc:
        raise LiquidityZoneError(str(exc)) from exc

    # ATR needs sufficient closed-candle history.
    # Do not silently fall back to an absolute tolerance.
    if (
        tolerance_mode == "atr"
        and (
            atr_value is None
            or not math.isfinite(atr_value)
            or atr_value <= 0
        )
    ):
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": len(prepared),
            "tolerance_mode": "atr",
            "tolerance": None,
            "atr": atr_value,
            "atr_period": 14,
            "atr_multiplier": multiplier,
            "reason": "insufficient_atr_history",
            "equal_high_count": 0,
            "equal_low_count": 0,
            "buy_side_zone_count": 0,
            "sell_side_zone_count": 0,
            "swept_zone_count": 0,
            "unswept_zone_count": 0,
            "equal_highs": [],
            "equal_lows": [],
            "zones": [],
        }

    if not prepared or swing_result.get("status") == "insufficient_data":
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": len(prepared),
            "tolerance_mode": tolerance_mode,
            "tolerance": price_tolerance,
            "atr": atr_value,
            "atr_period": 14 if tolerance_mode == "atr" else None,
            "atr_multiplier": multiplier,
            "equal_high_count": 0,
            "equal_low_count": 0,
            "buy_side_zone_count": 0,
            "sell_side_zone_count": 0,
            "swept_zone_count": 0,
            "unswept_zone_count": 0,
            "equal_highs": [],
            "equal_lows": [],
            "zones": [],
        }
    high_clusters = _make_clusters(
        swing_result.get("swing_highs", []),
        "EQH",
        price_tolerance,
    )
    low_clusters = _make_clusters(
        swing_result.get("swing_lows", []),
        "EQL",
        price_tolerance,
    )

    zones = [
        _build_zone(cluster, zone_type, timeframe, price_tolerance, prepared)
        for zone_type, clusters in (
            ("EQH", high_clusters),
            ("EQL", low_clusters),
        )
        for cluster in clusters
    ]

    zones.sort(
        key=lambda zone: (
            zone["confirmation_index"],
            zone["type"],
            zone["zone_low"],
            zone["id"],
        )
    )

    equal_highs = [zone for zone in zones if zone["type"] == "EQH"]
    equal_lows = [zone for zone in zones if zone["type"] == "EQL"]
   
    swept_count = sum(zone["is_swept"] for zone in zones)

    return {
        "status": "completed",
        "timeframe": timeframe,
        "candles_received": len(prepared),
        "left_bars": left_bars,
        "right_bars": right_bars,
        "tolerance": price_tolerance,
        "tolerance_mode": tolerance_mode,
        "atr": atr_value,
        "atr_period": 14 if tolerance_mode == "atr" else None,
        "atr_multiplier": multiplier,
        "equal_high_count": len(equal_highs),
        "equal_low_count": len(equal_lows),
        "buy_side_zone_count": len(equal_highs),
        "sell_side_zone_count": len(equal_lows),
        "swept_zone_count": swept_count,
        "unswept_zone_count": len(zones) - swept_count,
        "equal_highs": equal_highs,
        "equal_lows": equal_lows,
        "zones": zones,
    }