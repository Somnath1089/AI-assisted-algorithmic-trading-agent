"""Synthetic OHLCV/fundamentals generators for previewing the dashboard
without a live data connection. Not used by main.py's real scan path -
only by `python -m dashboard.generate --demo`."""
import numpy as np
import pandas as pd

def _base_series(n, start_trend, noise_scale=1.0, vol_boost_last=5, rng=None):
    rng = rng or np.random.default_rng()
    trend = np.linspace(0, start_trend, n)
    noise = np.cumsum(rng.normal(0, noise_scale, n))
    close = 100 + trend + noise
    high = close + rng.random(n) * 0.6
    low = close - rng.random(n) * 0.6
    open_ = close - rng.random(n) * 0.4
    volume = np.concatenate([
        rng.integers(2000, 3000, n - vol_boost_last),
        rng.integers(6000, 9000, vol_boost_last),
    ]).astype(float)
    return open_, high, low, close, volume

def _inject_breakout(open_, high, low, close, volume, range_low, range_high, engulf, rng):
    for i in range(-25, -2):
        c = rng.uniform(range_low, range_high)
        close[i] = c
        open_[i] = c - rng.uniform(-0.5, 0.5)
        high[i] = max(open_[i], close[i]) + rng.uniform(0, 0.3)
        low[i] = min(open_[i], close[i]) - rng.uniform(0, 0.3)

    open_[-2], close[-2] = range_high - 1.0, range_high - 2.0
    high[-2] = open_[-2] + 0.2
    low[-2] = close[-2] - 0.2

    open_[-1] = (close[-2] - 0.3) if engulf else (range_high - 1.8)
    close[-1] = range_high + 3.0
    high[-1] = close[-1] + 0.3
    low[-1] = open_[-1] - 0.2
    volume[-1] = 9000.0
    return open_, high, low, close, volume

def _inject_breakdown(open_, high, low, close, volume, range_low, range_high, rng):
    for i in range(-25, -2):
        c = rng.uniform(range_low, range_high)
        close[i] = c
        open_[i] = c - rng.uniform(-0.5, 0.5)
        high[i] = max(open_[i], close[i]) + rng.uniform(0, 0.3)
        low[i] = min(open_[i], close[i]) - rng.uniform(0, 0.3)

    open_[-2], close[-2] = range_low + 1.0, range_low + 2.0
    high[-2] = open_[-2] + 0.2
    low[-2] = close[-2] - 0.2

    open_[-1], close[-1] = close[-2] + 0.3, range_low - 3.0
    high[-1] = open_[-1] + 0.2
    low[-1] = close[-1] - 0.3
    volume[-1] = 9000.0
    return open_, high, low, close, volume

def make_demo_provider(seed=42):
    rng = np.random.default_rng(seed)
    cache = {}

    def get_ohlcv(symbol, period="6mo", interval="5m"):
        key = (symbol, interval)
        if key in cache:
            return cache[key]

        if symbol == "^NSEI":
            o, h, l, c, v = _base_series(300, 25, 0.8, rng=rng)
        elif symbol == "RELIANCE.NS":
            o, h, l, c, v = _base_series(300, 0, 1.0, rng=rng)
            o, h, l, c, v = _inject_breakout(o, h, l, c, v, 95, 100, engulf=False, rng=rng)
        elif symbol == "ICICIBANK.NS":
            o, h, l, c, v = _base_series(300, 5, 1.0, rng=rng)
            o, h, l, c, v = _inject_breakout(o, h, l, c, v, 95, 100, engulf=True, rng=rng)
        elif symbol == "TCS.NS":
            o, h, l, c, v = _base_series(300, -5, 1.0, rng=rng)
            o, h, l, c, v = _inject_breakdown(o, h, l, c, v, 95, 100, rng=rng)
        elif symbol == "ITC.NS":
            o, h, l, c, v = _base_series(300, -4, 1.0, rng=rng)
            o, h, l, c, v = _inject_breakdown(o, h, l, c, v, 95, 100, rng=rng)
        else:
            o, h, l, c, v = _base_series(300, rng.uniform(-8, 8), 1.0, rng=rng)

        cache[key] = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v})
        return cache[key]

    def get_stock_info(symbol):
        good = {
            "RELIANCE.NS": {"revenueGrowth": 0.14, "earningsGrowth": 0.11, "debtToEquity": 45,
                             "returnOnEquity": 0.16, "heldPercentInsiders": 0.5, "trailingPE": 24},
            "ICICIBANK.NS": {"revenueGrowth": 0.18, "earningsGrowth": 0.2, "debtToEquity": 20,
                              "returnOnEquity": 0.19, "heldPercentInsiders": 0.15, "trailingPE": 19},
        }
        return good.get(symbol, {})

    return get_ohlcv, get_stock_info
