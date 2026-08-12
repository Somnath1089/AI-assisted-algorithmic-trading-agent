import pytest
import pandas as pd

from data.dhan_data import _parse_candles, get_ohlcv_dhan
import data.dhan_data as dhan_data

def test_parse_candles_builds_expected_frame():
    data = {
        "open": [100.0, 101.0],
        "high": [101.5, 102.0],
        "low": [99.5, 100.5],
        "close": [101.0, 101.8],
        "volume": [1000, 1200],
        "timestamp": [1700000000, 1700000300],
    }
    df = _parse_candles(data)
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(df) == 2
    assert df["Close"].iloc[-1] == 101.8

def test_parse_candles_raises_on_unexpected_schema():
    with pytest.raises(ValueError, match="Unexpected Dhan historical-data response shape"):
        _parse_candles({"o": [1], "h": [2], "l": [0.5], "c": [1.5]})

class _FakeDhanClient:
    def __init__(self, response):
        self._response = response

    def intraday_minute_data(self, *args, **kwargs):
        return self._response

    def historical_daily_data(self, *args, **kwargs):
        return self._response

def test_get_ohlcv_dhan_raises_on_failed_request(monkeypatch):
    monkeypatch.setattr(
        dhan_data, "get_dhan_client",
        lambda client_id, access_token: _FakeDhanClient({"status": "failure", "remarks": "bad token"})
    )
    with pytest.raises(ValueError, match="Dhan historical-data request failed"):
        get_ohlcv_dhan("cid", "token", security_id="2885")

def test_get_ohlcv_dhan_returns_dataframe_on_success(monkeypatch):
    response = {
        "status": "success",
        "data": {
            "open": [100.0], "high": [101.0], "low": [99.0],
            "close": [100.5], "volume": [5000], "timestamp": [1700000000],
        },
    }
    monkeypatch.setattr(
        dhan_data, "get_dhan_client",
        lambda client_id, access_token: _FakeDhanClient(response)
    )
    df = get_ohlcv_dhan("cid", "token", security_id="2885")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

def test_get_ohlcv_dhan_rejects_invalid_interval():
    with pytest.raises(ValueError, match="interval must be one of"):
        get_ohlcv_dhan("cid", "token", security_id="2885", interval=7)
