from datetime import date
import numpy as np
import pandas as pd

from fno.instruments import nifty_futures
from fno.risk import FnoRiskManager
from fno.order_manager import FnoOrderManager
from fno.scan import run_fno_scan
from execution.broker import PaperBroker

def _trend_df(n=300, start_trend=250.0, seed=0):
    rng = np.random.default_rng(seed)
    trend = np.linspace(0, start_trend, n)
    noise = np.cumsum(rng.normal(0, 4.0, n))
    close = 25000 + trend + noise
    high = close + rng.random(n) * 5
    low = close - rng.random(n) * 5
    open_ = close - rng.random(n) * 3
    volume = np.concatenate([
        rng.integers(2000, 3000, n - 5),
        rng.integers(6000, 9000, 5),
    ]).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})

def test_run_fno_scan_produces_result_per_instrument_without_raising():
    df = _trend_df()

    def fake_get_ohlcv(symbol, period="6mo", interval="5m"):
        return df

    inst = nifty_futures(lot_size=65, expiry=date(2099, 12, 31))
    rm = FnoRiskManager(capital=5000000)
    om = FnoOrderManager(PaperBroker(), rm)

    results = run_fno_scan([inst], fake_get_ohlcv, regime="BULLISH",
                            risk_manager=rm, order_manager=om, allow_after_hours=True)

    assert len(results) == 1
    assert results[0]["instrument"] is inst

def test_run_fno_scan_survives_data_error():
    def broken_get_ohlcv(symbol, period="6mo", interval="5m"):
        raise ConnectionError("blocked")

    inst = nifty_futures(lot_size=65, expiry=date(2099, 12, 31))
    rm = FnoRiskManager(capital=5000000)
    om = FnoOrderManager(PaperBroker(), rm)

    results = run_fno_scan([inst], broken_get_ohlcv, regime="BULLISH",
                            risk_manager=rm, order_manager=om)

    assert len(results) == 1
    assert results[0]["signal"] is None
    assert "error" in results[0]["reason"].lower()
