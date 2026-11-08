from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


TIMEFRAME_SECONDS = {
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H4": 14400,
    "D1": 86400,
}

INDICATOR_PERIODS = {
    "ema": (20, 50, 200),
    "sma": (20, 50, 200),
    "rsi": 14,
    "macd": (12, 26, 9),
    "bollinger": (20, 2),
    "atr": 14,
    "adx": 14,
    "stochastic": (14, 3, 3),
}


class IndicatorError(ValueError):
    """Raised when candle data is invalid or insufficient."""


def _number(value: Any) -> float | None:
    """Convert a value to a finite float."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None

        result = float(value)

        return result if np.isfinite(result) else None

    except (TypeError, ValueError):
        return None


def _wilder_average(
    series: pd.Series,
    period: int,
) -> pd.Series:
    """
    Calculate Wilder's smoothed moving average.

    Uses an initial simple average over the first complete period,
    followed by Wilder's recursive smoothing.
    """
    if period < 1:
        raise ValueError("Wilder period must be greater than zero.")

    values = pd.to_numeric(series, errors="coerce").astype(float)

    result = pd.Series(
        np.nan,
        index=values.index,
        dtype=float,
    )

    valid = values.notna()

    if valid.sum() < period:
        return result

    # Locate the first complete consecutive period.
    rolling_mean = values.rolling(
        window=period,
        min_periods=period,
    ).mean()

    seed_positions = np.flatnonzero(rolling_mean.notna().to_numpy())

    if len(seed_positions) == 0:
        return result

    seed_position = int(seed_positions[0])
    seed_value = float(rolling_mean.iloc[seed_position])

    result.iloc[seed_position] = seed_value

    previous_value = seed_value

    for position in range(seed_position + 1, len(values)):
        current_value = values.iloc[position]

        if pd.isna(current_value):
            previous_value = np.nan
            continue

        if pd.isna(previous_value):
            # Restart only after another complete period.
            start = position - period + 1

            if start < 0:
                continue

            window = values.iloc[start:position + 1]

            if len(window) != period or window.isna().any():
                continue

            previous_value = float(window.mean())
            result.iloc[position] = previous_value
            continue

        previous_value = (
            previous_value * (period - 1) + float(current_value)
        ) / period

        result.iloc[position] = previous_value

    return result


def _cross_event(
    previous_a: float | None,
    current_a: float | None,
    previous_b: float | None,
    current_b: float | None,
) -> str:
    """Detect a crossover between two series."""
    values = (
        previous_a,
        current_a,
        previous_b,
        current_b,
    )

    if any(value is None for value in values):
        return "unavailable"

    if previous_a <= previous_b and current_a > current_b:
        return "bullish_crossover"

    if previous_a >= previous_b and current_a < current_b:
        return "bearish_crossover"

    return "none"


def _level_cross_event(
    previous: float | None,
    current: float | None,
    level: float,
) -> str:
    """Detect a series crossing a fixed threshold."""
    if previous is None or current is None:
        return "unavailable"

    if previous <= level and current > level:
        return "crossed_above"

    if previous >= level and current < level:
        return "crossed_below"

    return "none"


def _prepare_candles(
    candles: list[dict[str, Any]],
    timeframe: str,
    exclude_forming_candle: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(timeframe, str) or timeframe not in TIMEFRAME_SECONDS:
        raise IndicatorError(f"Unsupported timeframe: {timeframe}")

    if not isinstance(candles, list) or not candles:
        raise IndicatorError("No candles were supplied.")

    if any(not isinstance(candle, dict) for candle in candles):
        raise IndicatorError("Every candle must be a dictionary.")

    df = pd.DataFrame(candles)

    required = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    ]

    missing = [
        field for field in required
        if field not in df.columns
    ]

    if missing:
        raise IndicatorError(
            f"Missing candle fields: {', '.join(missing)}"
        )

    original_count = len(df)

    for field in required:
        df[field] = pd.to_numeric(
            df[field],
            errors="coerce",
        )

    if df[required].isna().any().any():
        raise IndicatorError(
            "Candle data contains missing or non-numeric required values."
        )

    if not np.isfinite(
        df[required].to_numpy(dtype=float)
    ).all():
        raise IndicatorError(
            "Candle data contains non-finite values."
        )

    # Unix timestamps must be positive whole seconds.
    if (df["timestamp"] <= 0).any():
        raise IndicatorError(
            "Candle timestamps must be positive."
        )

    if not np.all(
        np.equal(
            df["timestamp"].to_numpy(),
            np.floor(df["timestamp"].to_numpy()),
        )
    ):
        raise IndicatorError(
            "Candle timestamps must be whole Unix seconds."
        )

    # Tick volume should represent a non-negative whole count.
    if (df["tick_volume"] < 0).any():
        raise IndicatorError(
            "Tick volume cannot be negative."
        )

    if not np.all(
        np.equal(
            df["tick_volume"].to_numpy(),
            np.floor(df["tick_volume"].to_numpy()),
        )
    ):
        raise IndicatorError(
            "Tick volume must contain whole numbers."
        )

    ohlc = df[["open", "high", "low", "close"]]

    if (ohlc <= 0).any().any():
        raise IndicatorError(
            "OHLC prices must be greater than zero."
        )

    invalid_ohlc = (
        (df["high"] < ohlc.max(axis=1))
        | (df["low"] > ohlc.min(axis=1))
    )

    if invalid_ohlc.any():
        raise IndicatorError(
            "One or more candles have invalid OHLC values."
        )

    df["timestamp"] = df["timestamp"].astype("int64")
    df["tick_volume"] = df["tick_volume"].astype("int64")

    # Sort chronologically and remove duplicate candle openings.
    df = df.sort_values(
        "timestamp",
        kind="stable",
    )

    duplicate_count = int(
        df.duplicated("timestamp").sum()
    )

    df = df.drop_duplicates(
        subset=["timestamp"],
        keep="last",
    ).reset_index(drop=True)

    if len(df) < 2:
        raise IndicatorError(
            "At least two unique candles are required."
        )

    candle_seconds = TIMEFRAME_SECONDS[timeframe]

    forming_candle_removed = False

    if exclude_forming_candle:
        now_timestamp = int(
            datetime.now(timezone.utc).timestamp()
        )

        last_open_time = int(
            df.iloc[-1]["timestamp"]
        )

        if last_open_time + candle_seconds > now_timestamp:
            df = df.iloc[:-1].reset_index(drop=True)
            forming_candle_removed = True

    if len(df) < 2:
        raise IndicatorError(
            "Not enough closed candles after removing the forming candle."
        )

    # Calculate quality metrics using the candles actually retained.
    timestamp_differences = (
        df["timestamp"].diff().dropna()
    )

    gap_count = int(
        (timestamp_differences > candle_seconds).sum()
    )

    irregular_interval_count = int(
        (
            (timestamp_differences != candle_seconds)
            & (timestamp_differences <= candle_seconds)
        ).sum()
    )

    quality = {
        "received_candles": original_count,
        "unique_candles": len(df),
        "duplicate_candles_removed": duplicate_count,
        "gap_count": gap_count,
        "irregular_interval_count": irregular_interval_count,
        "forming_candle_removed": forming_candle_removed,
        "closed_candles_only": exclude_forming_candle,
    }

    return df, quality


def _calculate_indicators(
    df: pd.DataFrame,
) -> pd.DataFrame:
    result = df.copy()

    close = result["close"]
    high = result["high"]
    low = result["low"]
    volume = result["tick_volume"]

    # ---------------------------------------------------------
    # EMA and SMA
    # ---------------------------------------------------------
    for period in (20, 50, 200):
        result[f"ema_{period}"] = close.ewm(
            span=period,
            adjust=False,
            min_periods=period,
        ).mean()

        result[f"sma_{period}"] = close.rolling(
            window=period,
            min_periods=period,
        ).mean()

    # ---------------------------------------------------------
    # RSI - Wilder smoothing
    # ---------------------------------------------------------
    change = close.diff()

    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    average_gain = _wilder_average(gains, 14)
    average_loss = _wilder_average(losses, 14)

    relative_strength = (
        average_gain
        / average_loss.replace(0, np.nan)
    )

    result["rsi_14"] = (
        100 - (100 / (1 + relative_strength))
    )

    # No losses means RSI 100 when gains exist.
    result.loc[
        (average_loss == 0) & (average_gain > 0),
        "rsi_14",
    ] = 100

    # No gains means RSI 0 when losses exist.
    result.loc[
        (average_gain == 0) & (average_loss > 0),
        "rsi_14",
    ] = 0

    # No gains and no losses means neutral RSI.
    result.loc[
        (average_gain == 0) & (average_loss == 0),
        "rsi_14",
    ] = 50

    # ---------------------------------------------------------
    # MACD
    # ---------------------------------------------------------
    ema_fast = close.ewm(
        span=12,
        adjust=False,
        min_periods=12,
    ).mean()

    ema_slow = close.ewm(
        span=26,
        adjust=False,
        min_periods=26,
    ).mean()

    result["macd"] = ema_fast - ema_slow

    result["macd_signal"] = result["macd"].ewm(
        span=9,
        adjust=False,
        min_periods=9,
    ).mean()

    result["macd_histogram"] = (
        result["macd"] - result["macd_signal"]
    )

    # ---------------------------------------------------------
    # Bollinger Bands
    # ---------------------------------------------------------
    bb_middle = close.rolling(
        window=20,
        min_periods=20,
    ).mean()

    bb_std = close.rolling(
        window=20,
        min_periods=20,
    ).std(ddof=0)

    result["bb_middle"] = bb_middle
    result["bb_upper"] = bb_middle + (2 * bb_std)
    result["bb_lower"] = bb_middle - (2 * bb_std)

    result["bb_bandwidth"] = (
        (result["bb_upper"] - result["bb_lower"])
        / bb_middle.replace(0, np.nan)
    )

    result["bb_percent_b"] = (
        (close - result["bb_lower"])
        / (
            result["bb_upper"] - result["bb_lower"]
        ).replace(0, np.nan)
    )

    # ---------------------------------------------------------
    # ATR - Wilder smoothing
    # ---------------------------------------------------------
    previous_close = close.shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["atr_14"] = _wilder_average(
        true_range,
        14,
    )

    # ---------------------------------------------------------
    # ADX and directional indicators
    # ---------------------------------------------------------
    upward_move = high.diff()
    downward_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (upward_move > downward_move)
            & (upward_move > 0),
            upward_move,
            0.0,
        ),
        index=result.index,
        dtype=float,
    )

    minus_dm = pd.Series(
        np.where(
            (downward_move > upward_move)
            & (downward_move > 0),
            downward_move,
            0.0,
        ),
        index=result.index,
        dtype=float,
    )

    smoothed_atr = _wilder_average(
        true_range,
        14,
    )

    smoothed_plus_dm = _wilder_average(
        plus_dm,
        14,
    )

    smoothed_minus_dm = _wilder_average(
        minus_dm,
        14,
    )

    result["plus_di_14"] = (
        100
        * smoothed_plus_dm
        / smoothed_atr.replace(0, np.nan)
    )

    result["minus_di_14"] = (
        100
        * smoothed_minus_dm
        / smoothed_atr.replace(0, np.nan)
    )

    di_total = (
        result["plus_di_14"]
        + result["minus_di_14"]
    ).replace(0, np.nan)

    dx = (
        100
        * (
            result["plus_di_14"]
            - result["minus_di_14"]
        ).abs()
        / di_total
    )

    result["adx_14"] = _wilder_average(
        dx,
        14,
    )

    # ---------------------------------------------------------
    # Stochastic oscillator
    # ---------------------------------------------------------
    lowest_low = low.rolling(
        window=14,
        min_periods=14,
    ).min()

    highest_high = high.rolling(
        window=14,
        min_periods=14,
    ).max()

    price_range = (
        highest_high - lowest_low
    ).replace(0, np.nan)

    result["stoch_k"] = (
        100 * (close - lowest_low) / price_range
    )

    result["stoch_d"] = result["stoch_k"].rolling(
        window=3,
        min_periods=3,
    ).mean()

    # ---------------------------------------------------------
    # Rolling tick-volume-weighted price
    # ---------------------------------------------------------
    typical_price = (
        high + low + close
    ) / 3

    rolling_volume = volume.rolling(
        window=20,
        min_periods=20,
    ).sum()

    rolling_price_volume = (
        typical_price * volume
    ).rolling(
        window=20,
        min_periods=20,
    ).sum()

    result["rolling_vwap_20"] = (
        rolling_price_volume
        / rolling_volume.replace(0, np.nan)
    )

    # ---------------------------------------------------------
    # Volatility measurements
    # ---------------------------------------------------------
    result["atr_percent"] = (
        result["atr_14"] / close
    ) * 100

    result["atr_percentile_100"] = (
        result["atr_14"].rolling(
            window=100,
            min_periods=30,
        ).rank(pct=True) * 100
    )

    result["bb_bandwidth_percentile_100"] = (
        result["bb_bandwidth"].rolling(
            window=100,
            min_periods=30,
        ).rank(pct=True) * 100
    )

    return result


def _trend_interpretation(
    row: pd.Series,
) -> dict[str, str]:
    close = _number(row["close"])

    ema20 = _number(row["ema_20"])
    ema50 = _number(row["ema_50"])
    ema200 = _number(row["ema_200"])

    if any(
        value is None
        for value in (close, ema20, ema50, ema200)
    ):
        return {
            "ema_alignment": "insufficient_history",
            "price_position": "unavailable",
            "trend": "insufficient_history",
        }

    if ema20 > ema50 > ema200:
        alignment = "bullish"
    elif ema20 < ema50 < ema200:
        alignment = "bearish"
    else:
        alignment = "mixed"

    if close > ema20:
        position = "above_ema20"
    elif close < ema20:
        position = "below_ema20"
    else:
        position = "at_ema20"

    if close > ema50 and ema20 > ema50:
        trend = "bullish_bias"
    elif close < ema50 and ema20 < ema50:
        trend = "bearish_bias"
    else:
        trend = "mixed"

    return {
        "ema_alignment": alignment,
        "price_position": position,
        "trend": trend,
    }


def _state_interpretation(
    row: pd.Series,
) -> dict[str, str]:
    rsi = _number(row["rsi_14"])

    macd = _number(row["macd"])
    macd_signal = _number(row["macd_signal"])
    histogram = _number(row["macd_histogram"])

    adx = _number(row["adx_14"])
    plus_di = _number(row["plus_di_14"])
    minus_di = _number(row["minus_di_14"])

    stoch_k = _number(row["stoch_k"])
    stoch_d = _number(row["stoch_d"])

    if rsi is None:
        rsi_state = "unavailable"
    elif rsi >= 70:
        rsi_state = "overbought"
    elif rsi <= 30:
        rsi_state = "oversold"
    elif rsi > 50:
        rsi_state = "positive_momentum"
    elif rsi < 50:
        rsi_state = "negative_momentum"
    else:
        rsi_state = "neutral"

    if macd is None or macd_signal is None:
        macd_state = "unavailable"
    elif macd > macd_signal:
        macd_state = "bullish"
    elif macd < macd_signal:
        macd_state = "bearish"
    else:
        macd_state = "neutral"

    if histogram is None:
        histogram_state = "unavailable"
    elif histogram > 0:
        histogram_state = "positive"
    elif histogram < 0:
        histogram_state = "negative"
    else:
        histogram_state = "neutral"

    if adx is None:
        trend_strength = "unavailable"
    elif adx >= 25:
        trend_strength = "strong"
    elif adx >= 20:
        trend_strength = "developing"
    else:
        trend_strength = "weak_or_ranging"

    if plus_di is None or minus_di is None:
        directional_bias = "unavailable"
    elif plus_di > minus_di:
        directional_bias = "positive"
    elif minus_di > plus_di:
        directional_bias = "negative"
    else:
        directional_bias = "neutral"

    if stoch_k is None or stoch_d is None:
        stochastic_state = "unavailable"
    elif stoch_k >= 80:
        stochastic_state = "overbought_zone"
    elif stoch_k <= 20:
        stochastic_state = "oversold_zone"
    elif stoch_k > stoch_d:
        stochastic_state = "positive_momentum"
    elif stoch_k < stoch_d:
        stochastic_state = "negative_momentum"
    else:
        stochastic_state = "neutral"

    return {
        "rsi_condition": rsi_state,
        "macd_condition": macd_state,
        "macd_histogram_condition": histogram_state,
        "trend_strength": trend_strength,
        "directional_bias": directional_bias,
        "stochastic_condition": stochastic_state,
    }


def _volatility_interpretation(
    row: pd.Series,
) -> dict[str, str]:
    atr_percentile = _number(
        row["atr_percentile_100"]
    )

    bandwidth_percentile = _number(
        row["bb_bandwidth_percentile_100"]
    )

    if atr_percentile is None:
        atr_state = "insufficient_history"
    elif atr_percentile >= 80:
        atr_state = "very_high"
    elif atr_percentile >= 60:
        atr_state = "high"
    elif atr_percentile <= 20:
        atr_state = "low"
    else:
        atr_state = "normal"

    if bandwidth_percentile is None:
        bb_state = "insufficient_history"
    elif bandwidth_percentile <= 20:
        bb_state = "squeeze"
    elif bandwidth_percentile >= 80:
        bb_state = "wide"
    else:
        bb_state = "normal"

    return {
        "atr_volatility": atr_state,
        "bollinger_volatility": bb_state,
    }


def _event_interpretation(
    previous: pd.Series,
    current: pd.Series,
) -> dict[str, Any]:
    def value(
        row: pd.Series,
        key: str,
    ) -> float | None:
        return _number(row[key])

    events: dict[str, Any] = {}

    # EMA crossovers
    events["ema_20_50"] = _cross_event(
        value(previous, "ema_20"),
        value(current, "ema_20"),
        value(previous, "ema_50"),
        value(current, "ema_50"),
    )

    events["ema_50_200"] = _cross_event(
        value(previous, "ema_50"),
        value(current, "ema_50"),
        value(previous, "ema_200"),
        value(current, "ema_200"),
    )

    # MACD line versus signal line
    events["macd_signal"] = _cross_event(
        value(previous, "macd"),
        value(current, "macd"),
        value(previous, "macd_signal"),
        value(current, "macd_signal"),
    )

    # MACD histogram zero-line crossover
    events["macd_zero_line"] = _level_cross_event(
        value(previous, "macd_histogram"),
        value(current, "macd_histogram"),
        0,
    )

    # RSI threshold crossovers
    rsi_previous = value(previous, "rsi_14")
    rsi_current = value(current, "rsi_14")

    events["rsi_30_level"] = _level_cross_event(
        rsi_previous,
        rsi_current,
        30,
    )

    events["rsi_70_level"] = _level_cross_event(
        rsi_previous,
        rsi_current,
        70,
    )

    events["rsi_50_level"] = _level_cross_event(
        rsi_previous,
        rsi_current,
        50,
    )

    # Stochastic K/D crossover
    events["stochastic"] = _cross_event(
        value(previous, "stoch_k"),
        value(current, "stoch_k"),
        value(previous, "stoch_d"),
        value(current, "stoch_d"),
    )

    # Bollinger Band crossovers:
    # Compare each candle's close with its own corresponding band.
    events["bollinger_upper"] = _cross_event(
        value(previous, "close"),
        value(current, "close"),
        value(previous, "bb_upper"),
        value(current, "bb_upper"),
    )

    events["bollinger_lower"] = _cross_event(
        value(previous, "close"),
        value(current, "close"),
        value(previous, "bb_lower"),
        value(current, "bb_lower"),
    )

    # Bollinger bandwidth
    previous_width = value(
        previous,
        "bb_bandwidth",
    )

    current_width = value(
        current,
        "bb_bandwidth",
    )

    if previous_width is None or current_width is None:
        events["bollinger_bandwidth"] = "unavailable"
    elif current_width > previous_width:
        events["bollinger_bandwidth"] = "expanding"
    elif current_width < previous_width:
        events["bollinger_bandwidth"] = "contracting"
    else:
        events["bollinger_bandwidth"] = "unchanged"

    # ATR change
    previous_atr = value(previous, "atr_14")
    current_atr = value(current, "atr_14")

    if previous_atr is None or current_atr is None:
        events["atr"] = "unavailable"
    elif current_atr > previous_atr:
        events["atr"] = "increasing"
    elif current_atr < previous_atr:
        events["atr"] = "decreasing"
    else:
        events["atr"] = "unchanged"

    return events


def calculate_technical_indicators(
    candles: list[dict[str, Any]],
    symbol: str,
    timeframe: str,
    exclude_forming_candle: bool = True,
) -> dict[str, Any]:
    """
    Calculate technical indicators, interpretations, events and data quality.

    Required candle fields:
        timestamp, open, high, low, close, tick_volume

    Timestamps represent candle opening times in Unix seconds.

    This function calculates indicators only. It does not generate
    trading instructions or execute orders.
    """

    if not isinstance(symbol, str) or not symbol.strip():
        raise IndicatorError(
            "Symbol is required."
        )

    if not isinstance(exclude_forming_candle, bool):
        raise IndicatorError(
            "exclude_forming_candle must be a boolean."
        )

    symbol = symbol.strip().upper()

    df, quality = _prepare_candles(
        candles=candles,
        timeframe=timeframe,
        exclude_forming_candle=exclude_forming_candle,
    )

    calculated = _calculate_indicators(df)

    current = calculated.iloc[-1]
    previous = calculated.iloc[-2]

    indicator_names = [
        "ema_20",
        "ema_50",
        "ema_200",
        "sma_20",
        "sma_50",
        "sma_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "bb_bandwidth",
        "bb_percent_b",
        "atr_14",
        "atr_percent",
        "atr_percentile_100",
        "adx_14",
        "plus_di_14",
        "minus_di_14",
        "stoch_k",
        "stoch_d",
        "rolling_vwap_20",
        "bb_bandwidth_percentile_100",
    ]

    indicators = {
        name: _number(current[name])
        for name in indicator_names
    }

    unavailable_indicators = [
        name
        for name, value in indicators.items()
        if value is None
    ]

    interpretation = {
        **_trend_interpretation(current),
        **_state_interpretation(current),
        **_volatility_interpretation(current),
    }

    events = _event_interpretation(
        previous,
        current,
    )

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candle_timestamp": int(current["timestamp"]),
        "previous_candle_timestamp": int(
            previous["timestamp"]
        ),
        "candles_used": len(calculated),
        "indicators": indicators,
        "interpretation": interpretation,
        "events": events,
        "data_quality": quality,
        "metadata": {
            "candle_policy": (
                "closed_candles_only"
                if exclude_forming_candle
                else "includes_latest_candle"
            ),
            "vwap_note": (
                "Rolling 20-candle tick-volume-weighted price. "
                "It is not centralized FX market VWAP."
            ),
            "crossover_note": (
                "Events compare the latest eligible candle with "
                "the immediately preceding eligible candle."
            ),
            "indicator_readiness": (
                "complete"
                if not unavailable_indicators
                else "partial"
            ),
            "unavailable_indicators": unavailable_indicators,
            "wilder_smoothing": (
                "Initial simple average followed by Wilder recursive smoothing."
            ),
            "limitations": [
                "Tick volume is broker-specific.",
                "Rolling tick-volume-weighted price is not centralized FX VWAP.",
                "Indicator values are analytical inputs, not guaranteed trading signals.",
            ],
        },
    }