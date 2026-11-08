
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any


TIMEFRAME_SECONDS = {
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}


class MarketStructureError(ValueError):
    """Raised when market structure input is invalid."""


def _to_number(value: Any, field: str) -> float:
    """Convert a value to a finite number."""
    if isinstance(value, bool):
        raise MarketStructureError(
            f"Invalid {field}: boolean values are not accepted."
        )

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise MarketStructureError(
            f"Invalid {field}: expected a numeric value."
        ) from None

    if not isfinite(number):
        raise MarketStructureError(
            f"Invalid {field}: value must be finite."
        )

    return number


def _normalize_timestamp(value: Any) -> float:
    """Convert datetime, Unix seconds, or Unix milliseconds to seconds."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    timestamp = _to_number(value, "timestamp")

    if timestamp > 1_000_000_000_000:
        timestamp /= 1000

    if timestamp <= 0:
        raise MarketStructureError(
            "Invalid timestamp: expected a positive Unix timestamp."
        )

    return timestamp


def _prepare_candles(
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Validate and sort candles chronologically.

    Required fields:
        timestamp, open, high, low, close

    Input must contain closed candles only.
    """
    if not isinstance(candles, list):
        raise MarketStructureError("Candles must be supplied as a list.")

    prepared: list[dict[str, Any]] = []

    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise MarketStructureError(
                f"Candle at index {index} must be a dictionary."
            )

        timestamp = _normalize_timestamp(candle.get("timestamp"))

        open_price = _to_number(candle.get("open"), "open")
        high_price = _to_number(candle.get("high"), "high")
        low_price = _to_number(candle.get("low"), "low")
        close_price = _to_number(candle.get("close"), "close")

        if min(
            open_price,
            high_price,
            low_price,
            close_price,
        ) <= 0:
            raise MarketStructureError(
                f"Candle at index {index} contains a non-positive price."
            )

        if high_price < max(open_price, close_price, low_price):
            raise MarketStructureError(
                f"Candle at index {index} has an invalid high."
            )

        if low_price > min(open_price, close_price, high_price):
            raise MarketStructureError(
                f"Candle at index {index} has an invalid low."
            )

        prepared.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
        })

    prepared.sort(key=lambda item: item["timestamp"])

    timestamps = [candle["timestamp"] for candle in prepared]

    if len(timestamps) != len(set(timestamps)):
        raise MarketStructureError(
            "Duplicate candle timestamps are not allowed."
        )

    return prepared


def _format_timestamp(timestamp: float) -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def detect_swings(
    candles: list[dict[str, Any]],
    timeframe: str,
    left_bars: int = 3,
    right_bars: int = 3,
) -> dict[str, Any]:
    """
    Detect confirmed swing highs and swing lows.

    Swing high:
        High is greater than all preceding left bars
        and greater than or equal to all following right bars.

    Swing low:
        Low is lower than all preceding left bars
        and lower than or equal to all following right bars.

    Only confirmed swings are reported.
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise MarketStructureError(
            f"Unsupported timeframe: {timeframe}"
        )

    if (
        isinstance(left_bars, bool)
        or not isinstance(left_bars, int)
        or left_bars < 1
    ):
        raise MarketStructureError(
            "left_bars must be an integer of at least 1."
        )

    if (
        isinstance(right_bars, bool)
        or not isinstance(right_bars, int)
        or right_bars < 1
    ):
        raise MarketStructureError(
            "right_bars must be an integer of at least 1."
        )

    prepared = _prepare_candles(candles)

    required_candles = left_bars + right_bars + 1

    if len(prepared) < required_candles:
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": len(prepared),
            "minimum_candles_required": required_candles,
            "left_bars": left_bars,
            "right_bars": right_bars,
            "swing_highs": [],
            "swing_lows": [],
            "swings": [],
            "message": (
                f"At least {required_candles} candles are required "
                "for swing detection."
            ),
        }

    swing_highs: list[dict[str, Any]] = []
    swing_lows: list[dict[str, Any]] = []

    first_candidate = left_bars
    last_candidate = len(prepared) - right_bars

    for index in range(first_candidate, last_candidate):
        candidate = prepared[index]

        left_window = prepared[index - left_bars:index]
        right_window = prepared[
            index + 1:index + right_bars + 1
        ]

        left_highs = [item["high"] for item in left_window]
        right_highs = [item["high"] for item in right_window]

        left_lows = [item["low"] for item in left_window]
        right_lows = [item["low"] for item in right_window]

        is_swing_high = (
            candidate["high"] > max(left_highs)
            and candidate["high"] >= max(right_highs)
        )

        is_swing_low = (
            candidate["low"] < min(left_lows)
            and candidate["low"] <= min(right_lows)
        )

        confirmation_index = index + right_bars
        confirmation_candle = prepared[confirmation_index]

        confirmation_timestamp = (
            confirmation_candle["timestamp"]
            + TIMEFRAME_SECONDS[timeframe]
        )

        common_metadata = {
            "index": index,
            "timestamp": candidate["timestamp"],
            "time": _format_timestamp(candidate["timestamp"]),
            "confirmation_index": confirmation_index,
            "confirmation_timestamp": confirmation_timestamp,
            "confirmation_time": _format_timestamp(
                confirmation_timestamp
            ),
            "left_bars": left_bars,
            "right_bars": right_bars,
        }

        if is_swing_high:
            swing_highs.append({
                **common_metadata,
                "type": "swing_high",
                "price": candidate["high"],
            })

        if is_swing_low:
            swing_lows.append({
                **common_metadata,
                "type": "swing_low",
                "price": candidate["low"],
            })

    swings = sorted(
        swing_highs + swing_lows,
        key=lambda item: (
            item["timestamp"],
            item["type"],
        ),
    )

    return {
        "status": "completed",
        "timeframe": timeframe,
        "candles_received": len(prepared),
        "left_bars": left_bars,
        "right_bars": right_bars,
        "swing_high_count": len(swing_highs),
        "swing_low_count": len(swing_lows),
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "swings": swings,
        "method": "confirmed_fractal",
        "tie_breaking": "leftmost_equal_high_or_low",
        "lookahead_protection": (
            "A swing is reported only after all right-side "
            "confirmation candles are available."
        ),
    }


def detect_structure_breaks(
    candles: list[dict[str, Any]],
    timeframe: str,
    left_bars: int = 3,
    right_bars: int = 3,
) -> dict[str, Any]:
    """
    Detect Break of Structure (BOS) and Change of Character (CHoCH).

    Rules:
        - Bullish break requires a close above a confirmed swing high.
        - Bearish break requires a close below a confirmed swing low.
        - First break establishes the structural direction.
        - Same-direction break is BOS.
        - Opposite-direction break is CHoCH.
        - Each swing level is consumed at most once.
        - Unconfirmed swings cannot be used.
        - Wick-only breaks do not qualify.
        - Simultaneous breaks of both sides are ambiguous.
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise MarketStructureError(
            f"Unsupported timeframe: {timeframe}"
        )

    prepared = _prepare_candles(candles)

    swing_result = detect_swings(
        prepared,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    if swing_result["status"] == "insufficient_data":
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": len(prepared),
            "minimum_candles_required": (
                swing_result["minimum_candles_required"]
            ),
            "initial_direction": "unknown",
            "current_direction": "unknown",
            "structure_break_count": 0,
            "bos_count": 0,
            "choch_count": 0,
            "initial_break_count": 0,
            "ambiguous_break_count": 0,
            "events": [],
            "swings": swing_result,
            "message": swing_result["message"],
        }

    swing_highs = swing_result["swing_highs"]
    swing_lows = swing_result["swing_lows"]

    broken_high_indices: set[int] = set()
    broken_low_indices: set[int] = set()

    direction: str | None = None
    initial_direction: str | None = None

    events: list[dict[str, Any]] = []

    for candle_index, candle in enumerate(prepared):
        eligible_highs = [
            swing for swing in swing_highs
            if (
                swing["index"] < candle_index
                and swing["confirmation_index"] <= candle_index
                and swing["index"] not in broken_high_indices
            )
        ]

        eligible_lows = [
            swing for swing in swing_lows
            if (
                swing["index"] < candle_index
                and swing["confirmation_index"] <= candle_index
                and swing["index"] not in broken_low_indices
            )
        ]

        latest_high = (
            max(eligible_highs, key=lambda item: item["index"])
            if eligible_highs else None
        )

        latest_low = (
            max(eligible_lows, key=lambda item: item["index"])
            if eligible_lows else None
        )

        bullish_break = (
            latest_high is not None
            and candle["close"] > latest_high["price"]
        )

        bearish_break = (
            latest_low is not None
            and candle["close"] < latest_low["price"]
        )

        if not bullish_break and not bearish_break:
            continue

        candle_close_timestamp = (
            candle["timestamp"] + TIMEFRAME_SECONDS[timeframe]
        )

        if bullish_break and bearish_break:
            broken_high_indices.update(
                swing["index"]
                for swing in eligible_highs
                if candle["close"] > swing["price"]
            )

            broken_low_indices.update(
                swing["index"]
                for swing in eligible_lows
                if candle["close"] < swing["price"]
            )

            events.append({
                "event": "ambiguous_break",
                "direction": "ambiguous",
                "classification": "ambiguous",
                "candle_index": candle_index,
                "candle_timestamp": candle["timestamp"],
                "candle_close_timestamp": candle_close_timestamp,
                "candle_close_time": _format_timestamp(
                    candle_close_timestamp
                ),
                "close": candle["close"],
                "broken_swing_high": latest_high,
                "broken_swing_low": latest_low,
                "previous_direction": direction or "unknown",
                "resulting_direction": direction or "unknown",
                "reason": (
                    "The candle closed beyond both the latest "
                    "eligible swing high and swing low. Direction "
                    "was not changed."
                ),
            })
            continue

        if bullish_break:
            broken_level = latest_high
            break_direction = "bullish"

            broken_high_indices.update(
                swing["index"]
                for swing in eligible_highs
                if candle["close"] > swing["price"]
            )
        else:
            broken_level = latest_low
            break_direction = "bearish"

            broken_low_indices.update(
                swing["index"]
                for swing in eligible_lows
                if candle["close"] < swing["price"]
            )

        previous_direction = direction or "unknown"

        if direction is None:
            classification = "initial_break"
            direction = break_direction

            if initial_direction is None:
                initial_direction = break_direction

        elif direction == break_direction:
            classification = "BOS"

        else:
            classification = "CHoCH"
            direction = break_direction

        events.append({
            "event": classification,
            "direction": break_direction,
            "classification": classification,
            "candle_index": candle_index,
            "candle_timestamp": candle["timestamp"],
            "candle_close_timestamp": candle_close_timestamp,
            "candle_close_time": _format_timestamp(
                candle_close_timestamp
            ),
            "close": candle["close"],
            "broken_level": {
                "type": broken_level["type"],
                "price": broken_level["price"],
                "swing_index": broken_level["index"],
                "swing_timestamp": broken_level["timestamp"],
                "confirmation_index": (
                    broken_level["confirmation_index"]
                ),
                "confirmation_timestamp": (
                    broken_level["confirmation_timestamp"]
                ),
            },
            "previous_direction": previous_direction,
            "resulting_direction": direction,
            "reason": (
                f"{break_direction.capitalize()} candle close "
                f"broke the confirmed {broken_level['type']} "
                f"at {broken_level['price']}."
            ),
        })

    bos_count = sum(
        event["classification"] == "BOS"
        for event in events
    )

    choch_count = sum(
        event["classification"] == "CHoCH"
        for event in events
    )

    initial_break_count = sum(
        event["classification"] == "initial_break"
        for event in events
    )

    ambiguous_count = sum(
        event["classification"] == "ambiguous"
        for event in events
    )

    return {
        "status": "completed",
        "timeframe": timeframe,
        "candles_received": len(prepared),
        "initial_direction": initial_direction or "unknown",
        "current_direction": direction or "unknown",
        "structure_break_count": len(events),
        "bos_count": bos_count,
        "choch_count": choch_count,
        "initial_break_count": initial_break_count,
        "ambiguous_break_count": ambiguous_count,
        "events": events,
        "swings": swing_result,
        "rules": {
            "break_confirmation": "candle_close",
            "swing_confirmation": "confirmed_fractal",
            "swing_tie_breaking": "leftmost_equal_high_or_low",
            "duplicate_breaks": "one_event_per_swing_level",
            "initial_break": (
                "The first directional break establishes structure "
                "and is not classified as CHoCH."
            ),
            "choch_behavior": (
                "A break against the established direction changes "
                "the current structural direction."
            ),
            "ambiguous_break_behavior": (
                "A candle closing beyond both eligible sides is "
                "reported as ambiguous and does not change direction."
            ),
        },
        "limitations": [
            "The engine expects closed candles only.",
            "This is a rule-based structure model, not a complete "
            "discretionary trading interpretation.",
            "The engine does not account for broker trading sessions.",
            "A structural break is not a trade recommendation.",
        ],
    }


def detect_liquidity_sweeps(
    candles: list[dict[str, Any]],
    timeframe: str,
    left_bars: int = 3,
    right_bars: int = 3,
) -> dict[str, Any]:
    """
    Detect confirmed swing-level liquidity sweeps.

    Buy-side liquidity:
        Price trades above a confirmed swing high and closes below it.

    Sell-side liquidity:
        Price trades below a confirmed swing low and closes above it.

    A swing cannot be swept before confirmation.
    Each swing can generate at most one sweep event.
    """

    if timeframe not in TIMEFRAME_SECONDS:
        raise MarketStructureError(
            f"Unsupported timeframe: {timeframe}"
        )

    prepared = _prepare_candles(candles)

    if not prepared:
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": 0,
            "buy_side_sweeps": 0,
            "sell_side_sweeps": 0,
            "total_sweeps": 0,
            "events": [],
            "sweeps": [],
            "message": "No candles supplied.",
        }

    swing_result = detect_swings(
        prepared,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    if swing_result["status"] == "insufficient_data":
        return {
            "status": "insufficient_data",
            "timeframe": timeframe,
            "candles_received": len(prepared),
            "buy_side_sweeps": 0,
            "sell_side_sweeps": 0,
            "total_sweeps": 0,
            "events": [],
            "sweeps": [],
            "swings": swing_result,
            "message": swing_result["message"],
        }

    swings = swing_result["swings"]

    events: list[dict[str, Any]] = []
    consumed_levels: set[tuple[str, int]] = set()

    for candle_index, candle in enumerate(prepared):

        for swing in swings:
            swing_type = swing["type"]
            swing_index = swing["index"]
            confirmation_index = swing["confirmation_index"]
            level = swing["price"]

            level_key = (swing_type, swing_index)

            # Do not use a swing before confirmation.
            if confirmation_index > candle_index:
                continue

            # A swing cannot sweep itself.
            if swing_index >= candle_index:
                continue

            # Each swing level can generate only one event.
            if level_key in consumed_levels:
                continue

            event_type = None
            wick_extreme = None
            rejection_distance = None

            # Buy-side liquidity sweep:
            # Price takes the swing high and closes below it.
            if (
                swing_type == "swing_high"
                and candle["high"] > level
                and candle["close"] < level
            ):
                event_type = "buy_side_liquidity_sweep"
                wick_extreme = candle["high"]
                rejection_distance = candle["high"] - level

            # Sell-side liquidity sweep:
            # Price takes the swing low and closes above it.
            elif (
                swing_type == "swing_low"
                and candle["low"] < level
                and candle["close"] > level
            ):
                event_type = "sell_side_liquidity_sweep"
                wick_extreme = candle["low"]
                rejection_distance = level - candle["low"]

            if event_type is None:
                continue

            if candle["close"] > candle["open"]:
                candle_direction = "bullish"
            elif candle["close"] < candle["open"]:
                candle_direction = "bearish"
            else:
                candle_direction = "neutral"

            event = {
                "type": event_type,
                "timeframe": timeframe,
                "timestamp": candle["timestamp"],
                "time": _format_timestamp(candle["timestamp"]),
                "candle_index": candle_index,
                "level": level,
                "wick_extreme": wick_extreme,
                "rejection_distance": rejection_distance,
                "candle_direction": candle_direction,
                "swing_index": swing_index,
                "swing_timestamp": swing["timestamp"],
                "confirmation_index": confirmation_index,
                "confirmation_timestamp": (
                    swing["confirmation_timestamp"]
                ),
            }

            events.append(event)
            consumed_levels.add(level_key)

    buy_side_count = sum(
        event["type"] == "buy_side_liquidity_sweep"
        for event in events
    )

    sell_side_count = sum(
        event["type"] == "sell_side_liquidity_sweep"
        for event in events
    )

    return {
        "status": "completed",
        "timeframe": timeframe,
        "candles_received": len(prepared),
        "buy_side_sweeps": buy_side_count,
        "sell_side_sweeps": sell_side_count,
        "total_sweeps": len(events),
        "events": events,
        "sweeps": events,
        "method": "confirmed_swing_liquidity_sweep",
        "rules": {
            "buy_side_sweep": (
                "High exceeds a confirmed swing high and close "
                "returns below the level."
            ),
            "sell_side_sweep": (
                "Low falls below a confirmed swing low and close "
                "returns above the level."
            ),
            "confirmation": "confirmation_index <= candle_index",
            "exclude_swing_candle": True,
            "duplicate_protection": "one_event_per_swing_level",
            "wick_only_rejection": True,
        },
        "lookahead_protection": (
            "Only previously confirmed swing levels are eligible."
        ),
    }


