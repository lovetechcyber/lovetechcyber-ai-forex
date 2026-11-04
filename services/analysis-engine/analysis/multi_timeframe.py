from __future__ import annotations

import re
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from indicators.technical_indicators import (
    IndicatorError,
    calculate_technical_indicators,
)


TIMEFRAME_SECONDS = {
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}

# Higher timeframes have greater influence on overall market direction.
TIMEFRAME_WEIGHTS = {
    "D1": 3,
    "H4": 3,
    "H1": 2,
    "M30": 1,
    "M15": 1,
    "M5": 1,
}

# Maximum expected age of the latest closed candle.
# These are operational thresholds, not broker trading-session rules.
FRESHNESS_THRESHOLDS_SECONDS = {
    "M5": 10 * 60,
    "M15": 30 * 60,
    "M30": 60 * 60,
    "H1": 2 * 60 * 60,
    "H4": 8 * 60 * 60,
    "D1": 36 * 60 * 60,
}

HIGHER_TIMEFRAMES = ("D1", "H4", "H1")
LOWER_TIMEFRAMES = ("M30", "M15", "M5")

SUPPORTED_SYMBOL_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9._-]{2,19}$"
)


class MultiTimeframeError(ValueError):
    """Raised when multi-timeframe analysis cannot be completed."""


def _to_float(value: Any) -> float | None:
    """Safely convert a value to a finite float."""
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if isfinite(number) else None


def _flatten_numeric_values(
    data: Any,
    output: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Extract numeric indicator values from nested dictionaries.

    This allows the engine to work with nested indicator response
    structures without depending on unrelated metadata fields.
    """
    if output is None:
        output = {}

    if isinstance(data, dict):
        for key, value in data.items():
            normalized_key = str(key).lower()

            if isinstance(value, dict):
                _flatten_numeric_values(value, output)
            else:
                number = _to_float(value)

                if number is not None:
                    output[normalized_key] = number

    return output


def _get_value(
    values: dict[str, float],
    *possible_names: str,
) -> float | None:
    """Find an indicator using any supported key name."""
    for name in possible_names:
        value = values.get(name.lower())

        if value is not None:
            return value

    return None


def _normalize_timestamp(value: Any) -> float | None:
    """Convert supported timestamps to Unix seconds."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.timestamp()

    number = _to_float(value)

    if number is None:
        return None

    # Support Unix milliseconds as well as Unix seconds.
    if number > 1_000_000_000_000:
        number /= 1000

    return number


def _calculate_freshness(
    timeframe: str,
    latest_candle_timestamp: float,
    now_timestamp: float,
) -> dict[str, Any]:
    """
    Determine how recently the latest closed candle finished.

    Age is calculated from candle close time, not candle open time.
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise MultiTimeframeError(
            f"Unsupported timeframe: {timeframe}"
        )

    candle_close_time = (
        latest_candle_timestamp + TIMEFRAME_SECONDS[timeframe]
    )

    age_seconds = max(0, now_timestamp - candle_close_time)

    threshold = FRESHNESS_THRESHOLDS_SECONDS[timeframe]

    if age_seconds <= threshold:
        status = "fresh"
    elif age_seconds <= threshold * 2:
        status = "delayed"
    else:
        status = "stale"

    return {
        "status": status,
        "latest_candle_age_seconds": round(age_seconds),
        "latest_candle_age_minutes": round(age_seconds / 60, 2),
        "last_closed_candle_time": datetime.fromtimestamp(
            candle_close_time,
            tz=timezone.utc,
        ).isoformat(),
        "expected_next_candle_time": datetime.fromtimestamp(
            candle_close_time + TIMEFRAME_SECONDS[timeframe],
            tz=timezone.utc,
        ).isoformat(),
        "freshness_threshold_seconds": threshold,
    }


def _get_closed_candles(
    candles: list[dict[str, Any]],
    timeframe: str,
    now_timestamp: float,
) -> tuple[list[dict[str, Any]], int]:
    """
    Keep only candles whose opening time plus timeframe duration
    is at or before the current UTC time.

    Invalid timestamps and forming candles are removed.
    """
    duration = TIMEFRAME_SECONDS[timeframe]

    closed: list[dict[str, Any]] = []
    removed = 0

    for candle in candles:
        if not isinstance(candle, dict):
            removed += 1
            continue

        timestamp = _normalize_timestamp(
            candle.get("timestamp")
        )

        if timestamp is None:
            removed += 1
            continue

        if timestamp + duration <= now_timestamp:
            closed.append(candle)
        else:
            removed += 1

    # Ensure chronological order before calculating indicators.
    closed.sort(
        key=lambda candle: _normalize_timestamp(
            candle.get("timestamp")
        ) or 0
    )

    return closed, removed


def _calculate_timeframe_score(
    indicators: dict[str, float],
) -> dict[str, Any]:
    """
    Score directional evidence for one timeframe.

    This is a transparent rule-based classification, not a
    probability of a profitable trade.
    """
    score = 0
    evidence: list[str] = []
    unavailable: list[str] = []

    ema20 = _get_value(indicators, "ema_20", "ema20")
    ema50 = _get_value(indicators, "ema_50", "ema50")
    ema200 = _get_value(indicators, "ema_200", "ema200")

    close = _get_value(
        indicators,
        "close",
        "latest_close",
        "current_price",
    )

    macd = _get_value(indicators, "macd")

    macd_signal = _get_value(
        indicators,
        "macd_signal",
        "macd_signal_line",
        "signal",
    )

    macd_histogram = _get_value(
        indicators,
        "macd_histogram",
        "macd_hist",
        "histogram",
    )

    rsi = _get_value(
        indicators,
        "rsi_14",
        "rsi14",
        "rsi",
    )

    plus_di = _get_value(
        indicators,
        "plus_di",
        "plus_di_14",
        "plus_di14",
    )

    minus_di = _get_value(
        indicators,
        "minus_di",
        "minus_di_14",
        "minus_di14",
    )

    adx = _get_value(
        indicators,
        "adx_14",
        "adx14",
        "adx",
    )

    # EMA alignment.
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            score += 2
            evidence.append("EMA20 is above EMA50.")
        elif ema20 < ema50:
            score -= 2
            evidence.append("EMA20 is below EMA50.")
        else:
            evidence.append("EMA20 and EMA50 are equal.")
    else:
        unavailable.append("EMA20/EMA50 alignment")

    if ema50 is not None and ema200 is not None:
        if ema50 > ema200:
            score += 1
            evidence.append("EMA50 is above EMA200.")
        elif ema50 < ema200:
            score -= 1
            evidence.append("EMA50 is below EMA200.")
    else:
        unavailable.append("EMA50/EMA200 alignment")

    if close is not None and ema20 is not None:
        if close > ema20:
            score += 1
            evidence.append("Price is above EMA20.")
        elif close < ema20:
            score -= 1
            evidence.append("Price is below EMA20.")
    else:
        unavailable.append("Price versus EMA20")

    # MACD momentum.
    if macd_histogram is not None:
        if macd_histogram > 0:
            score += 1
            evidence.append("MACD histogram is positive.")
        elif macd_histogram < 0:
            score -= 1
            evidence.append("MACD histogram is negative.")

    elif macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 1
            evidence.append("MACD is above its signal line.")
        elif macd < macd_signal:
            score -= 1
            evidence.append("MACD is below its signal line.")
    else:
        unavailable.append("MACD momentum")

    # RSI is momentum evidence, not a standalone reversal signal.
    if rsi is not None:
        if rsi >= 55:
            score += 1
            evidence.append("RSI supports bullish momentum.")
        elif rsi <= 45:
            score -= 1
            evidence.append("RSI supports bearish momentum.")
        else:
            evidence.append("RSI is in its neutral momentum range.")
    else:
        unavailable.append("RSI")

    # Directional movement.
    if plus_di is not None and minus_di is not None:
        if plus_di > minus_di:
            score += 1
            evidence.append("+DI is above -DI.")
        elif minus_di > plus_di:
            score -= 1
            evidence.append("-DI is above +DI.")
    else:
        unavailable.append("Directional movement")

    # ADX measures trend strength, not direction.
    if adx is None:
        strength = "unavailable"
    elif adx >= 25:
        strength = "strong"
    elif adx >= 20:
        strength = "developing"
    else:
        strength = "weak"

    if score >= 3:
        bias = "bullish"
    elif score <= -3:
        bias = "bearish"
    else:
        bias = "neutral"

    # Maximum possible directional score is 7.
    # This is not a statistical probability or win-rate estimate.
    confidence = round(
        min(abs(score) / 7, 1.0) * 100,
        2,
    )

    return {
        "bias": bias,
        "directional_score": score,
        "evidence": evidence,
        "unavailable_indicators": unavailable,
        "trend_strength": strength,
        "adx": adx,
        "rsi": rsi,
        "confidence_score": confidence,
        "confidence_description": (
            "Rule-based evidence strength; not a trade success probability."
        ),
    }


def _analyse_one_timeframe(
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
    now_timestamp: float,
    minimum_candles: int,
) -> dict[str, Any]:
    """Calculate indicators and directional bias for one timeframe."""
    closed_candles, forming_removed = _get_closed_candles(
        candles=candles,
        timeframe=timeframe,
        now_timestamp=now_timestamp,
    )

    if len(closed_candles) < minimum_candles:
        return {
            "timeframe": timeframe,
            "status": "insufficient_data",
            "bias": "unavailable",
            "candles_received": len(candles),
            "closed_candles_used": len(closed_candles),
            "forming_candles_removed": forming_removed,
            "minimum_candles_required": minimum_candles,
            "reason": (
                f"At least {minimum_candles} closed candles are required."
            ),
        }

    try:
        result = calculate_technical_indicators(
            candles=closed_candles,
            symbol=symbol,
            timeframe=timeframe,
            exclude_forming_candle=False,
        )
    except IndicatorError as exc:
        return {
            "timeframe": timeframe,
            "status": "analysis_error",
            "bias": "unavailable",
            "closed_candles_used": len(closed_candles),
            "reason": str(exc),
        }

    if not isinstance(result, dict):
        raise MultiTimeframeError(
            f"Unexpected indicator response for {symbol} {timeframe}."
        )

    indicator_values = _flatten_numeric_values(result)

    latest_candle = closed_candles[-1]

    latest_close = _to_float(
        latest_candle.get("close")
    )

    if latest_close is not None:
        indicator_values["close"] = latest_close

    score_result = _calculate_timeframe_score(
        indicator_values
    )

    latest_timestamp = _normalize_timestamp(
        latest_candle.get("timestamp")
    )

    if latest_timestamp is None:
        return {
            "timeframe": timeframe,
            "status": "invalid_data",
            "bias": "unavailable",
            "reason": "Latest closed candle has an invalid timestamp.",
        }

    freshness = _calculate_freshness(
        timeframe=timeframe,
        latest_candle_timestamp=latest_timestamp,
        now_timestamp=now_timestamp,
    )

    return {
        "timeframe": timeframe,
        "status": "completed",
        "candles_received": len(candles),
        "closed_candles_used": len(closed_candles),
        "forming_candles_removed": forming_removed,
        "latest_closed_candle_timestamp": latest_timestamp,
        "latest_close": latest_close,
        "freshness": freshness,
        **score_result,
        "indicators": indicator_values,
    }


def _aggregate_timeframes(
    timeframe_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Combine timeframe scores using higher-timeframe weighting."""
    weighted_score = 0
    total_available_weight = 0

    bullish_weight = 0
    bearish_weight = 0
    neutral_weight = 0

    for timeframe, weight in TIMEFRAME_WEIGHTS.items():
        result = timeframe_results.get(timeframe, {})

        if result.get("status") != "completed":
            continue

        freshness = result.get("freshness", {})

        # Stale timeframe results must not influence overall direction.
        if freshness.get("status") == "stale":
            continue

        score = result.get("directional_score", 0)
        bias = result.get("bias", "neutral")

        weighted_score += score * weight
        total_available_weight += weight

        if bias == "bullish":
            bullish_weight += weight
        elif bias == "bearish":
            bearish_weight += weight
        else:
            neutral_weight += weight

    if total_available_weight == 0:
        return {
            "status": "insufficient_data",
            "bias": "unavailable",
            "weighted_score": 0,
            "normalized_score": 0,
            "available_weight": 0,
            "bullish_weight": 0,
            "bearish_weight": 0,
            "neutral_weight": 0,
            "conflict_detected": False,
            "directional_agreement": "unavailable",
        }

    maximum_score = 7 * total_available_weight
    normalized_score = weighted_score / maximum_score

    if normalized_score >= 0.25:
        overall_bias = "bullish"
    elif normalized_score <= -0.25:
        overall_bias = "bearish"
    else:
        overall_bias = "neutral"

    conflict_detected = (
        bullish_weight > 0 and bearish_weight > 0
    )

    return {
        "status": "completed",
        "bias": overall_bias,
        "weighted_score": round(weighted_score, 2),
        "normalized_score": round(normalized_score, 4),
        "available_weight": total_available_weight,
        "bullish_weight": bullish_weight,
        "bearish_weight": bearish_weight,
        "neutral_weight": neutral_weight,
        "conflict_detected": conflict_detected,
        "directional_agreement": (
            "mixed" if conflict_detected else overall_bias
        ),
    }


def analyze_multi_timeframe(
    candles_by_timeframe: dict[str, list[dict[str, Any]]],
    symbol: str,
    minimum_candles: int = 50,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Analyse all supported timeframes and calculate market confluence.

    Args:
        candles_by_timeframe:
            Mapping of timeframe names to chronological OHLC candle lists.
        symbol:
            Market instrument, for example EURUSD.
        minimum_candles:
            Minimum closed candles needed before a timeframe is analysed.
        now:
            Optional timezone-aware datetime for deterministic testing.

    Returns:
        Structured multi-timeframe market analysis.

    No orders are placed and no trading instructions are generated.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        raise MultiTimeframeError(
            "A valid market symbol is required."
        )

    symbol = symbol.strip().upper()

    if not SUPPORTED_SYMBOL_PATTERN.fullmatch(symbol):
        raise MultiTimeframeError(
            "Invalid market symbol format."
        )

    if (
        isinstance(minimum_candles, bool)
        or not isinstance(minimum_candles, int)
        or minimum_candles < 2
    ):
        raise MultiTimeframeError(
            "minimum_candles must be an integer of at least 2."
        )

    if not isinstance(candles_by_timeframe, dict):
        raise MultiTimeframeError(
            "candles_by_timeframe must be a dictionary."
        )

    current_time = now or datetime.now(timezone.utc)

    if not isinstance(current_time, datetime):
        raise MultiTimeframeError(
            "The supplied analysis time must be a datetime."
        )

    if current_time.tzinfo is None:
        raise MultiTimeframeError(
            "The supplied analysis time must include a timezone."
        )

    current_time = current_time.astimezone(timezone.utc)
    now_timestamp = current_time.timestamp()

    timeframe_results: dict[str, dict[str, Any]] = {}

    # Analyse all six supported timeframes.
    for timeframe in TIMEFRAME_SECONDS:
        candles = candles_by_timeframe.get(timeframe, [])

        if not isinstance(candles, list):
            timeframe_results[timeframe] = {
                "timeframe": timeframe,
                "status": "invalid_data",
                "bias": "unavailable",
                "reason": "Candles must be supplied as a list.",
            }
            continue

        timeframe_results[timeframe] = _analyse_one_timeframe(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            now_timestamp=now_timestamp,
            minimum_candles=minimum_candles,
        )

    # Aggregate only completed, non-stale timeframe results.
    overall = _aggregate_timeframes(timeframe_results)

    # Higher timeframe directional context.
    higher_biases = [
        timeframe_results[timeframe]["bias"]
        for timeframe in HIGHER_TIMEFRAMES
        if (
            timeframe_results[timeframe].get("status") == "completed"
            and timeframe_results[timeframe]
            .get("freshness", {})
            .get("status") != "stale"
        )
    ]

    # Lower timeframe directional context.
    lower_biases = [
        timeframe_results[timeframe]["bias"]
        for timeframe in LOWER_TIMEFRAMES
        if (
            timeframe_results[timeframe].get("status") == "completed"
            and timeframe_results[timeframe]
            .get("freshness", {})
            .get("status") != "stale"
        )
    ]

    higher_directional = {
        bias
        for bias in higher_biases
        if bias in {"bullish", "bearish"}
    }

    lower_directional = {
        bias
        for bias in lower_biases
        if bias in {"bullish", "bearish"}
    }

    higher_conflict = len(higher_directional) > 1
    lower_conflict = len(lower_directional) > 1

    if higher_conflict:
        market_context = "conflicting_higher_timeframes"
    elif len(higher_directional) == 1:
        market_context = next(iter(higher_directional))
    else:
        market_context = "insufficient_higher_timeframe_direction"

    if (
        len(higher_directional) == 1
        and len(lower_directional) == 1
        and higher_directional != lower_directional
    ):
        entry_context = "lower_timeframe_countertrend"

    elif higher_conflict or lower_conflict:
        entry_context = "mixed_timeframe_conditions"

    elif higher_directional and lower_directional:
        entry_context = "timeframes_aligned"

    else:
        entry_context = "insufficient_alignment"

    # Count timeframe completion and freshness.
    completed_count = sum(
        1
        for result in timeframe_results.values()
        if result.get("status") == "completed"
    )

    fresh_count = sum(
        1
        for result in timeframe_results.values()
        if (
            result.get("status") == "completed"
            and result.get("freshness", {}).get("status") == "fresh"
        )
    )

    delayed_count = sum(
        1
        for result in timeframe_results.values()
        if (
            result.get("status") == "completed"
            and result.get("freshness", {}).get("status") == "delayed"
        )
    )

    stale_count = sum(
        1
        for result in timeframe_results.values()
        if (
            result.get("status") == "completed"
            and result.get("freshness", {}).get("status") == "stale"
        )
    )

    if completed_count == 0:
        analysis_status = "insufficient_data"

    elif (
        completed_count < len(TIMEFRAME_SECONDS)
        or stale_count > 0
        or delayed_count > 0
    ):
        analysis_status = "partial"

    else:
        analysis_status = "completed"

    # The full timeframe mapping is important to API consumers and tests.
    return {
        "symbol": symbol,
        "analysis_type": "multi_timeframe",
        "analysis_status": analysis_status,
        "analysed_at": current_time.isoformat(),
        "overall": overall,
        "market_context": {
            "higher_timeframe_bias": market_context,
            "lower_timeframe_context": entry_context,
            "higher_timeframe_conflict": higher_conflict,
            "lower_timeframe_conflict": lower_conflict,
        },
        "timeframe_weights": TIMEFRAME_WEIGHTS.copy(),
        "timeframes": timeframe_results,
        "data_summary": {
            "timeframes_requested": len(TIMEFRAME_SECONDS),
            "timeframes_completed": completed_count,
            "timeframes_unavailable": (
                len(TIMEFRAME_SECONDS) - completed_count
            ),
            "fresh_timeframes": fresh_count,
            "delayed_timeframes": delayed_count,
            "stale_timeframes": stale_count,
            "closed_candles_only": True,
            "stale_timeframes_excluded_from_overall_score": True,
        },
        "limitations": [
            "Directional scores are rule-based evidence, not probabilities.",
            "A bullish or bearish bias is not a trade recommendation.",
            "Indicator agreement does not guarantee future price movement.",
            "Market structure and liquidity analysis are separate stages.",
            "Freshness thresholds do not account for broker sessions, weekends, or holidays.",
            "Human review is required before accepting an AI-generated analysis.",
        ],
    }