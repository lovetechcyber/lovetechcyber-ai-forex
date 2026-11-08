
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from indicators.technical_indicators import (
    calculate_technical_indicators,
)
from analysis.market_structure import (
    detect_structure_breaks,
)
from analysis.liquidity_zones import (
    detect_liquidity_zones,
)
from analysis.market_structure import (
    detect_liquidity_sweeps,
)
from analysis.fair_value_gap import (
    detect_fair_value_gaps,
)
from analysis.order_blocks import (
    detect_order_blocks,
)


def _latest(items: list[dict]) -> dict | None:
    """Return the most recent event by candle index."""
    if not items:
        return None

    return max(
        items,
        key=lambda item: (
            item.get("candle_index", -1),
            item.get("creation_index", -1),
        ),
    )


def _determine_indicator_bias(indicators: dict) -> dict:
    """
    Determine directional evidence from the existing indicators.

    This is an analytical classification, not a trade signal.
    """
    score = 0
    evidence = []

    ema20 = indicators.get("ema_20")
    ema50 = indicators.get("ema_50")
    ema200 = indicators.get("ema_200")
    macd = indicators.get("macd")
    macd_signal = indicators.get("macd_signal")
    rsi = indicators.get("rsi_14")
    plus_di = indicators.get("plus_di_14")
    minus_di = indicators.get("minus_di_14")

    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            score += 1
            evidence.append("EMA 20 is above EMA 50.")
        elif ema20 < ema50:
            score -= 1
            evidence.append("EMA 20 is below EMA 50.")

    if ema50 is not None and ema200 is not None:
        if ema50 > ema200:
            score += 1
            evidence.append("EMA 50 is above EMA 200.")
        elif ema50 < ema200:
            score -= 1
            evidence.append("EMA 50 is below EMA 200.")

    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 1
            evidence.append("MACD is above its signal line.")
        elif macd < macd_signal:
            score -= 1
            evidence.append("MACD is below its signal line.")

    if rsi is not None:
        if rsi > 50:
            score += 1
            evidence.append("RSI is above 50.")
        elif rsi < 50:
            score -= 1
            evidence.append("RSI is below 50.")

    if plus_di is not None and minus_di is not None:
        if plus_di > minus_di:
            score += 1
            evidence.append("+DI is above -DI.")
        elif minus_di > plus_di:
            score -= 1
            evidence.append("-DI is above +DI.")

    if score >= 2:
        bias = "bullish"
    elif score <= -2:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "direction": bias,
        "score": score,
        "evidence": evidence,
        "interpretation": (
            "Rule-based indicator evidence; not a probability "
            "or trade recommendation."
        ),
    }


def _build_confluences(
    indicator_bias: dict,
    structure: dict,
    sweeps: dict,
    liquidity: dict,
    fair_value_gaps: dict,
    order_blocks: dict,
) -> tuple[list[dict], list[dict]]:
    confluences = []
    conflicts = []

    bias = indicator_bias["direction"]
    structure_direction = structure.get(
        "current_direction",
        "unknown",
    )

    if (
        bias in ("bullish", "bearish")
        and structure_direction == bias
    ):
        confluences.append({
            "type": "indicator_structure_alignment",
            "direction": bias,
            "evidence": (
                "Indicator bias and confirmed market structure "
                "direction agree."
            ),
        })

    elif (
        bias in ("bullish", "bearish")
        and structure_direction in ("bullish", "bearish")
        and structure_direction != bias
    ):
        conflicts.append({
            "type": "indicator_structure_conflict",
            "indicator_bias": bias,
            "structure_direction": structure_direction,
            "evidence": (
                "Indicator direction conflicts with confirmed "
                "market structure."
            ),
        })

    structure_events = structure.get("events", [])
    latest_structure_event = _latest(structure_events)

    if latest_structure_event:
        classification = latest_structure_event.get(
            "classification"
        )

        if classification in ("BOS", "CHoCH"):
            confluences.append({
                "type": "confirmed_structure_event",
                "direction": latest_structure_event.get("direction"),
                "classification": classification,
                "event": latest_structure_event,
            })

    sweep_events = sweeps.get("events", [])

    for event in sweep_events[-5:]:
        confluences.append({
            "type": "liquidity_sweep",
            "direction": (
                "bearish"
                if event.get("event") == "buy_side_liquidity_sweep"
                else "bullish"
                if event.get("event") == "sell_side_liquidity_sweep"
                else "unknown"
            ),
            "event": event,
        })

    for zone in liquidity.get("zones", []):
        if zone.get("is_swept"):
            confluences.append({
                "type": "swept_liquidity_zone",
                "direction": (
                    "bearish"
                    if zone.get("type") == "EQH"
                    else "bullish"
                ),
                "zone": zone,
            })

    for gap in fair_value_gaps.get("gaps", []):
        if gap.get("status") in (
            "unmitigated",
            "partially_mitigated",
        ) and not gap.get("is_invalidated", False):
            confluences.append({
                "type": "active_fair_value_gap",
                "direction": gap.get("direction"),
                "gap": gap,
            })

    for block in order_blocks.get("order_blocks", []):
        if (
            not block.get("is_invalidated", False)
            and block.get("mitigation_status") != "fully_mitigated"
        ):
            confluences.append({
                "type": "active_order_block",
                "direction": block.get("direction"),
                "order_block": block,
            })

    return confluences, conflicts


def analyze_market(
    candles: list[dict[str, Any]],
    symbol: str,
    timeframe: str,
    tolerance_mode: str = "atr",
    tolerance: float | None = None,
    atr_multiplier: float = 0.10,
    left_bars: int = 3,
    right_bars: int = 3,
) -> dict[str, Any]:
    """
    Run the unified single-timeframe market analysis pipeline.

    Only closed candles are passed to the downstream detectors.
    No orders are placed and no trading instructions are generated.
    """

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A valid symbol is required.")

    if not isinstance(timeframe, str) or not timeframe.strip():
        raise ValueError("A valid timeframe is required.")

    symbol = symbol.strip().upper()
    timeframe = timeframe.strip().upper()

    if not candles:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis_status": "insufficient_data",
            "reason": "No candles supplied.",
        }

    # The indicator engine validates and selects the latest
    # eligible closed candle.
    indicator_candles = []

    for candle in candles:
        item = dict(candle)
        item.setdefault("tick_volume", 0)
        indicator_candles.append(item)

    technical = calculate_technical_indicators(
        candles=indicator_candles,
        symbol=symbol,
        timeframe=timeframe,
        exclude_forming_candle=True,
    )

    # Align all detectors to the same closed-candle boundary.
    latest_closed_timestamp = int(
        technical["candle_timestamp"]
    )

    closed_candles = [
        dict(candle)
        for candle in candles
        if int(candle["timestamp"]) <= latest_closed_timestamp
    ]

    # Use the same normalized timestamp order for all modules.
    closed_candles.sort(
        key=lambda candle: int(candle["timestamp"])
    )

    structure = detect_structure_breaks(
        closed_candles,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    sweeps = detect_liquidity_sweeps(
        closed_candles,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    liquidity = detect_liquidity_zones(
        closed_candles,
        timeframe,
        tolerance=tolerance,
        tolerance_mode=tolerance_mode,
        atr_multiplier=atr_multiplier,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    fair_value_gaps = detect_fair_value_gaps(
        closed_candles,
        timeframe,
    )

    order_blocks = detect_order_blocks(
        closed_candles,
        timeframe,
        left_bars=left_bars,
        right_bars=right_bars,
    )

    indicator_bias = _determine_indicator_bias(
        technical["indicators"]
    )

    confluences, conflicts = _build_confluences(
        indicator_bias,
        structure,
        sweeps,
        liquidity,
        fair_value_gaps,
        order_blocks,
    )

    statuses = [
        structure.get("status"),
        sweeps.get("status"),
        liquidity.get("status"),
        fair_value_gaps.get("status"),
        order_blocks.get("status"),
    ]

    if all(status == "completed" for status in statuses):
        analysis_status = "completed"
    elif all(
        status == "insufficient_data"
        for status in statuses
    ):
        analysis_status = "insufficient_data"
    else:
        analysis_status = "partial"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "analysis_type": "unified_market_analysis",
        "analysis_status": analysis_status,
        "analysed_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "market_bias": indicator_bias,

        "market_structure": {
            "status": structure.get("status"),
            "initial_direction": structure.get(
                "initial_direction"
            ),
            "current_direction": structure.get(
                "current_direction"
            ),
            "structure_break_count": structure.get(
                "structure_break_count", 0
            ),
            "bos_count": structure.get("bos_count", 0),
            "choch_count": structure.get("choch_count", 0),
            "events": structure.get("events", []),
            "latest_event": _latest(
                structure.get("events", [])
            ),
        },

        "liquidity": {
            "sweeps": sweeps,
            "zones": liquidity,
        },

        "fair_value_gaps": fair_value_gaps,
        "order_blocks": order_blocks,

        "technical_indicators": technical,

        "confluences": confluences,
        "conflicts": conflicts,

        "risk_factors": [
            "Indicator bias is rule-based evidence, not a probability.",
            "A bullish or bearish bias is not a trade recommendation.",
            "Liquidity sweeps do not guarantee a reversal.",
            "FVG and order-block zones can fail or be invalidated.",
            "Broker tick volume is not centralized FX market volume.",
            "Human review is required before accepting AI analysis.",
        ],

        "metadata": {
            "candles_received": len(candles),
            "closed_candles_used": len(closed_candles),
            "latest_closed_candle_timestamp": (
                latest_closed_timestamp
            ),
            "closed_candles_only": True,
            "tolerance_mode": tolerance_mode,
            "atr_multiplier": (
                atr_multiplier
                if tolerance_mode == "atr"
                else None
            ),
            "human_confirmation_required": True,
            "automated_trade_execution": False,
        },
    }
