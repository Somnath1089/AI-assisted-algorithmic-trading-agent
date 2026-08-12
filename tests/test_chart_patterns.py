import numpy as np
import pandas as pd
from indicators.chart_patterns import detect_candlestick_pattern, detect_chart_pattern, read_chart

def _candles(rows):
    data = []
    for r in rows:
        o, c = r["Open"], r["Close"]
        h = r.get("High", max(o, c))
        l = r.get("Low", min(o, c))
        data.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": 1000})
    return pd.DataFrame(data)

def test_bullish_engulfing():
    df = _candles([
        {"Open": 20.0, "Close": 20.2},
        {"Open": 10.0, "Close": 9.0},
        {"Open": 8.5, "Close": 10.5},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "BULLISH_ENGULFING"
    assert bias == "BULLISH"

def test_bearish_engulfing():
    df = _candles([
        {"Open": 20.0, "Close": 19.8},
        {"Open": 9.0, "Close": 10.0},
        {"Open": 10.5, "Close": 8.5},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "BEARISH_ENGULFING"
    assert bias == "BEARISH"

def test_hammer():
    df = _candles([
        {"Open": 20.0, "Close": 20.1},
        {"Open": 15.0, "Close": 14.8},
        {"Open": 10.0, "Close": 10.3, "High": 10.35, "Low": 8.5},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "HAMMER"
    assert bias == "BULLISH"

def test_shooting_star():
    df = _candles([
        {"Open": 20.0, "Close": 20.1},
        {"Open": 15.0, "Close": 15.2},
        {"Open": 10.0, "Close": 9.7, "High": 11.5, "Low": 9.65},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "SHOOTING_STAR"
    assert bias == "BEARISH"

def test_doji():
    df = _candles([
        {"Open": 20.0, "Close": 20.1},
        {"Open": 15.0, "Close": 15.2},
        {"Open": 10.0, "Close": 10.02, "High": 10.5, "Low": 9.5},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "DOJI"
    assert bias == "NEUTRAL"

def test_morning_star():
    df = _candles([
        {"Open": 10.0, "Close": 8.0},
        {"Open": 7.8, "Close": 7.9},
        {"Open": 8.0, "Close": 9.3},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "MORNING_STAR"
    assert bias == "BULLISH"

def test_evening_star():
    df = _candles([
        {"Open": 8.0, "Close": 10.0},
        {"Open": 10.2, "Close": 10.1},
        {"Open": 10.0, "Close": 8.7},
    ])
    pattern, bias = detect_candlestick_pattern(df)
    assert pattern == "EVENING_STAR"
    assert bias == "BEARISH"

def _swing_path(waypoints, seg_len=6):
    prices = []
    for i in range(len(waypoints) - 1):
        seg = np.linspace(waypoints[i], waypoints[i + 1], seg_len, endpoint=True)
        if i > 0:
            seg = seg[1:]
        prices.extend(seg)
    return np.array(prices)

def _swing_df(waypoints):
    closes = _swing_path(waypoints)
    return pd.DataFrame({
        "Open": closes - 0.05,
        "High": closes + 0.1,
        "Low": closes - 0.1,
        "Close": closes,
        "Volume": 1000.0,
    })

def test_double_top_confirmed():
    df = _swing_df([95, 110, 100, 110, 90])
    pattern, bias = detect_chart_pattern(df)
    assert pattern == "DOUBLE_TOP"
    assert bias == "BEARISH"

def test_double_bottom_confirmed():
    df = _swing_df([110, 95, 105, 95, 115])
    pattern, bias = detect_chart_pattern(df)
    assert pattern == "DOUBLE_BOTTOM"
    assert bias == "BULLISH"

def test_head_and_shoulders():
    df = _swing_df([95, 105, 98, 115, 98, 105, 90])
    pattern, bias = detect_chart_pattern(df)
    assert pattern == "HEAD_AND_SHOULDERS"
    assert bias == "BEARISH"

def test_read_chart_no_pattern_is_neutral():
    df = _candles([{"Open": 10.0, "Close": 10.05} for _ in range(5)])
    result = read_chart(df)
    assert result["overall_bias"] == "NEUTRAL"
