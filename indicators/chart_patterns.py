import numpy as np
import pandas as pd

def find_swing_points(df: pd.DataFrame, order: int = 3):
    highs = df["High"].values
    lows = df["Low"].values
    n = len(df)
    swing_high = np.zeros(n, dtype=bool)
    swing_low = np.zeros(n, dtype=bool)

    for i in range(order, n - order):
        left_h = highs[i - order:i]
        right_h = highs[i + 1:i + order + 1]
        if highs[i] > left_h.max() and highs[i] > right_h.max():
            swing_high[i] = True

        left_l = lows[i - order:i]
        right_l = lows[i + 1:i + order + 1]
        if lows[i] < left_l.min() and lows[i] < right_l.min():
            swing_low[i] = True

    return swing_high, swing_low

def detect_candlestick_pattern(df: pd.DataFrame):
    if len(df) < 3:
        return None, "NEUTRAL"

    c2, c1, c0 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

    body0 = abs(c0["Close"] - c0["Open"])
    range0 = c0["High"] - c0["Low"]
    upper_wick0 = c0["High"] - max(c0["Close"], c0["Open"])
    lower_wick0 = min(c0["Close"], c0["Open"]) - c0["Low"]

    if range0 > 0 and body0 / range0 < 0.1:
        return "DOJI", "NEUTRAL"

    if (c1["Close"] < c1["Open"] and c0["Close"] > c0["Open"]
            and c0["Close"] >= c1["Open"] and c0["Open"] <= c1["Close"]):
        return "BULLISH_ENGULFING", "BULLISH"

    if (c1["Close"] > c1["Open"] and c0["Close"] < c0["Open"]
            and c0["Open"] >= c1["Close"] and c0["Close"] <= c1["Open"]):
        return "BEARISH_ENGULFING", "BEARISH"

    if body0 > 0 and lower_wick0 >= 2 * body0 and upper_wick0 <= 0.3 * body0:
        return "HAMMER", "BULLISH"

    if body0 > 0 and upper_wick0 >= 2 * body0 and lower_wick0 <= 0.3 * body0:
        return "SHOOTING_STAR", "BEARISH"

    if (c2["Close"] < c2["Open"]
            and abs(c1["Close"] - c1["Open"]) < abs(c2["Close"] - c2["Open"]) * 0.5
            and c0["Close"] > c0["Open"]
            and c0["Close"] > (c2["Open"] + c2["Close"]) / 2):
        return "MORNING_STAR", "BULLISH"

    if (c2["Close"] > c2["Open"]
            and abs(c1["Close"] - c1["Open"]) < abs(c2["Close"] - c2["Open"]) * 0.5
            and c0["Close"] < c0["Open"]
            and c0["Close"] < (c2["Open"] + c2["Close"]) / 2):
        return "EVENING_STAR", "BEARISH"

    return None, "NEUTRAL"

def detect_chart_pattern(df: pd.DataFrame, order: int = 3, lookback: int = 60, tolerance: float = 0.015):
    window = df.iloc[-lookback:] if len(df) > lookback else df
    swing_high, swing_low = find_swing_points(window, order=order)
    highs_idx = np.where(swing_high)[0]
    lows_idx = np.where(swing_low)[0]
    high_vals = window["High"].values
    low_vals = window["Low"].values
    last_close = window["Close"].iloc[-1]

    # Three-point patterns are checked first: a head-and-shoulders' neckline
    # troughs are expected to be roughly equal, which would otherwise also
    # satisfy the generic two-point double-top/bottom check below.
    if len(highs_idx) >= 3:
        i1, i2, i3 = highs_idx[-3], highs_idx[-2], highs_idx[-1]
        h1, h2, h3 = high_vals[i1], high_vals[i2], high_vals[i3]
        if h2 > h1 and h2 > h3 and abs(h1 - h3) / h1 < tolerance * 2:
            return "HEAD_AND_SHOULDERS", "BEARISH"

    if len(lows_idx) >= 3:
        i1, i2, i3 = lows_idx[-3], lows_idx[-2], lows_idx[-1]
        l1, l2, l3 = low_vals[i1], low_vals[i2], low_vals[i3]
        if l2 < l1 and l2 < l3 and abs(l1 - l3) / l1 < tolerance * 2:
            return "INVERSE_HEAD_AND_SHOULDERS", "BULLISH"

    if len(highs_idx) >= 2:
        i1, i2 = highs_idx[-2], highs_idx[-1]
        h1, h2 = high_vals[i1], high_vals[i2]
        if abs(h1 - h2) / h1 < tolerance:
            between_lows = [low_vals[i] for i in lows_idx if i1 < i < i2]
            if between_lows:
                neckline = min(between_lows)
                if last_close < neckline:
                    return "DOUBLE_TOP", "BEARISH"
                return "DOUBLE_TOP_FORMING", "BEARISH"

    if len(lows_idx) >= 2:
        i1, i2 = lows_idx[-2], lows_idx[-1]
        l1, l2 = low_vals[i1], low_vals[i2]
        if abs(l1 - l2) / l1 < tolerance:
            between_highs = [high_vals[i] for i in highs_idx if i1 < i < i2]
            if between_highs:
                neckline = max(between_highs)
                if last_close > neckline:
                    return "DOUBLE_BOTTOM", "BULLISH"
                return "DOUBLE_BOTTOM_FORMING", "BULLISH"

    return None, "NEUTRAL"

def read_chart(primary_df: pd.DataFrame, higher_tf_df: pd.DataFrame = None) -> dict:
    candle_pattern, candle_bias = detect_candlestick_pattern(primary_df)

    structural_df = higher_tf_df if higher_tf_df is not None and len(higher_tf_df) >= 20 else primary_df
    chart_pattern, chart_bias = detect_chart_pattern(structural_df)

    if chart_pattern and candle_pattern:
        overall_bias = chart_bias if chart_bias == candle_bias else "NEUTRAL"
    elif chart_pattern:
        overall_bias = chart_bias
    elif candle_pattern:
        overall_bias = candle_bias
    else:
        overall_bias = "NEUTRAL"

    return {
        "candle_pattern": candle_pattern,
        "candle_bias": candle_bias,
        "chart_pattern": chart_pattern,
        "chart_bias": chart_bias,
        "overall_bias": overall_bias,
    }
