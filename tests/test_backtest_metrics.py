import pandas as pd
from backtest.metrics import compute_metrics

def test_compute_metrics_basic():
    trades = pd.DataFrame([
        {"pnl": 1000, "capital": 101000},
        {"pnl": -500, "capital": 100500},
        {"pnl": 1500, "capital": 102000},
        {"pnl": -500, "capital": 101500},
    ])
    m = compute_metrics(trades, initial_capital=100000)
    assert m["total_trades"] == 4
    assert m["winning_trades"] == 2
    assert m["losing_trades"] == 2
    assert m["win_rate"] == 0.5
    assert m["profit_factor"] == 2.5
    assert m["max_consecutive_losses"] == 1
    assert m["final_capital"] == 101500

def test_compute_metrics_empty():
    m = compute_metrics(pd.DataFrame(), initial_capital=100000)
    assert m["total_trades"] == 0
    assert m["final_capital"] == 100000
