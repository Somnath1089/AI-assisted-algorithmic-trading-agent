import numpy as np
import pandas as pd

from main import run_scan, UNIVERSE

def _trend_df(n=300, start_trend=30.0, seed=0):
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, start_trend, n)
    noise = np.cumsum(rng.normal(0, 0.4, n))
    close = 100 + trend + noise
    high = close + rng.random(n) * 0.4
    low = close - rng.random(n) * 0.4
    open_ = close - rng.random(n) * 0.3
    volume = np.concatenate([
        rng.integers(2000, 3000, n - 5),
        rng.integers(6000, 9000, 5),
    ]).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})

def _fake_get_ohlcv_factory():
    cache = {}

    def fake_get_ohlcv(symbol, period="6mo", interval="5m"):
        key = (symbol, interval)
        if key not in cache:
            seed = abs(hash(key)) % (2**31)
            trend = 25.0 if symbol == "^NSEI" else 30.0
            cache[key] = _trend_df(start_trend=trend, seed=seed)
        return cache[key]

    return fake_get_ohlcv

def _fake_get_stock_info(symbol):
    return {}

def test_run_scan_returns_structured_result_without_raising():
    result = run_scan(get_ohlcv=_fake_get_ohlcv_factory(), get_stock_info=_fake_get_stock_info)
    assert result["mode"] == "INTRADAY"
    assert result["regime"] in ("BULLISH", "BEARISH", "SIDEWAYS", "UNCERTAIN", "HIGH VOLATILITY")
    assert isinstance(result["summary"], list)
    assert len(result["summary"]) == len(UNIVERSE) or result["blocked_reason"] is not None

def test_run_scan_survives_nifty_fetch_failure():
    def broken_get_ohlcv(symbol, period="6mo", interval="5m"):
        raise ConnectionError("network blocked")

    result = run_scan(get_ohlcv=broken_get_ohlcv, get_stock_info=_fake_get_stock_info)
    assert result["regime"] is None
    assert result["blocked_reason"] is not None
    assert "unavailable" in result["blocked_reason"].lower()

def test_run_scan_survives_per_symbol_failure():
    good_ohlcv = _fake_get_ohlcv_factory()

    def flaky_get_ohlcv(symbol, period="6mo", interval="5m"):
        if symbol == "RELIANCE.NS":
            raise ValueError("simulated per-symbol failure")
        return good_ohlcv(symbol, period, interval)

    result = run_scan(get_ohlcv=flaky_get_ohlcv, get_stock_info=_fake_get_stock_info)
    assert result["blocked_reason"] is None or "RELIANCE.NS" not in dict(result["errors"])
    error_symbols = dict(result["errors"])
    if result["blocked_reason"] is None:
        assert "RELIANCE.NS" in error_symbols
        summary_symbols = {row[0]: row[1] for row in result["summary"]}
        assert summary_symbols["RELIANCE.NS"] == "AVOID"
