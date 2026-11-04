from analysis.market_structure import (
    TIMEFRAME_SECONDS,
    MarketStructureError,
    _prepare_candles,
    _format_timestamp,
    detect_structure_breaks,
)


def _clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def _empty_result(timeframe, status="insufficient_data"):
    return {
        "status": status,
        "timeframe": timeframe,
        "order_block_count": 0,
        "bullish_count": 0,
        "bearish_count": 0,
        "order_blocks": [],
    }


def detect_order_blocks(
    candles,
    timeframe,
    left_bars=3,
    right_bars=3,
):
    """
    Detect order blocks from confirmed Break of Structure (BOS) events.

    Bullish order block:
        Last bearish candle after the broken swing low and before
        a confirmed bullish BOS.

    Bearish order block:
        Last bullish candle after the broken swing high and before
        a confirmed bearish BOS.

    Mitigation is tracked only after the BOS candle.
    """

    if timeframe not in TIMEFRAME_SECONDS:
        raise MarketStructureError(
            f"Unsupported timeframe: {timeframe}"
        )

    if not candles:
        return _empty_result(timeframe)

    prepared = _prepare_candles(candles)

    if len(prepared) < 3:
        return _empty_result(timeframe)

    structure = detect_structure_breaks(
        candles,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    if structure.get("status") != "completed":
        return _empty_result(
            timeframe,
            status=structure.get("status", "insufficient_data"),
        )

    events = structure.get("events", [])
    order_blocks = []
    used_sources = set()

    for event in events:
        # Only confirmed continuation breaks create order blocks.
        if event.get("classification") != "BOS":
            continue

        direction = event.get("direction")

        if direction not in ("bullish", "bearish"):
            continue

        break_index = event.get("candle_index")
        broken_level = event.get("broken_level") or {}
        swing_index = broken_level.get("swing_index")

        if not isinstance(break_index, int):
            continue

        if not isinstance(swing_index, int):
            continue

        if not (0 <= swing_index < break_index < len(prepared)):
            continue

        # The source candle must be after the broken swing candle
        # and before the BOS candle.
        source_index = None

        for index in range(break_index - 1, swing_index, -1):
            candle = prepared[index]

            if direction == "bullish":
                # Bullish OB: last bearish candle.
                if candle["close"] < candle["open"]:
                    source_index = index
                    break
            else:
                # Bearish OB: last bullish candle.
                if candle["close"] > candle["open"]:
                    source_index = index
                    break

        if source_index is None:
            continue

        source_key = (direction, source_index)

        # Prevent multiple BOS events from creating duplicate
        # order blocks from the same source candle.
        if source_key in used_sources:
            continue

        used_sources.add(source_key)

        source = prepared[source_index]
        zone_low = source["low"]
        zone_high = source["high"]
        zone_size = zone_high - zone_low

        if zone_size <= 0:
            continue

        break_candle = prepared[break_index]
        confirmation_timestamp = event.get(
            "candle_close_timestamp"
        )

        if confirmation_timestamp is None:
            confirmation_timestamp = (
                break_candle["timestamp"]
                + TIMEFRAME_SECONDS[timeframe]
            )

        order_block = {
            "id": (
                f"{timeframe}_{direction}_"
                f"{source['timestamp']}"
            ),
            "type": direction,
            "timeframe": timeframe,
            "source_index": source_index,
            "source_timestamp": source["timestamp"],
            "source_time": _format_timestamp(
                source["timestamp"]
            ),
            "open": source["open"],
            "high": zone_high,
            "low": zone_low,
            "close": source["close"],
            "zone_high": zone_high,
            "zone_low": zone_low,
            "midpoint": (zone_high + zone_low) / 2,
            "zone_size": zone_size,
            "bos_index": break_index,
            "bos_timestamp": break_candle["timestamp"],
            "bos_confirmation_timestamp": confirmation_timestamp,
            "bos_confirmation_time": _format_timestamp(
                confirmation_timestamp
            ),
            "broken_swing_index": swing_index,
            "broken_level": broken_level.get("price"),
            "status": "unmitigated",
            "mitigation_percentage": 0.0,
            "first_mitigation_timestamp": None,
            "first_mitigation_time": None,
            "full_mitigation_timestamp": None,
            "full_mitigation_time": None,
            "is_invalidated": False,
            "invalidation_timestamp": None,
            "invalidation_time": None,
        }

        # Only candles after the BOS candle may mitigate the block.
        for index in range(break_index + 1, len(prepared)):
            candle = prepared[index]

            # Once invalidated, preserve the recorded history.
            if order_block["is_invalidated"]:
                break

            # Check whether the candle's range overlaps the zone.
            overlaps_zone = (
                candle["low"] <= zone_high
                and candle["high"] >= zone_low
            )

            if overlaps_zone:
                if direction == "bullish":
                    penetration = (
                        zone_high - max(candle["low"], zone_low)
                    ) / zone_size * 100
                else:
                    penetration = (
                        min(candle["high"], zone_high) - zone_low
                    ) / zone_size * 100

                penetration = _clamp(penetration)

                # Keep the maximum penetration reached.
                order_block["mitigation_percentage"] = max(
                    order_block["mitigation_percentage"],
                    penetration,
                )

                if order_block["first_mitigation_timestamp"] is None:
                    order_block["first_mitigation_timestamp"] = (
                        candle["timestamp"]
                    )
                    order_block["first_mitigation_time"] = (
                        _format_timestamp(candle["timestamp"])
                    )

                if penetration >= 100:
                    order_block["status"] = "fully_mitigated"

                    if order_block["full_mitigation_timestamp"] is None:
                        order_block["full_mitigation_timestamp"] = (
                            candle["timestamp"]
                        )
                        order_block["full_mitigation_time"] = (
                            _format_timestamp(candle["timestamp"])
                        )

                elif order_block["status"] != "fully_mitigated":
                    order_block["status"] = "partially_mitigated"

            # Invalidation requires a candle close beyond the zone.
            if direction == "bullish":
                invalidated = candle["close"] < zone_low
            else:
                invalidated = candle["close"] > zone_high

            if invalidated:
                order_block["is_invalidated"] = True
                order_block["invalidation_timestamp"] = (
                    candle["timestamp"]
                )
                order_block["invalidation_time"] = (
                    _format_timestamp(candle["timestamp"])
                )

        order_blocks.append(order_block)

    bullish_count = sum(
        block["type"] == "bullish"
        for block in order_blocks
    )

    bearish_count = sum(
        block["type"] == "bearish"
        for block in order_blocks
    )

    return {
        "status": "completed",
        "timeframe": timeframe,
        "candles_received": len(prepared),
        "bos_events_received": sum(
            event.get("classification") == "BOS"
            for event in events
        ),
        "order_block_count": len(order_blocks),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "order_blocks": order_blocks,
    }