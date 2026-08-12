import pandas as pd
from indicators.technical import add_indicators
from backtest.metrics import compute_metrics

def backtest(df, initial_capital=100000, risk_fraction=0.01,
             slippage_pct=0.0005, brokerage_per_order=20.0, tax_pct=0.001):
    data = add_indicators(df)
    capital = initial_capital
    trades = []

    for i in range(50, len(data) - 1):
        row = data.iloc[i]

        long_setup = (
            row["Close"] > row["EMA20"] > row["SMA50"] and
            row["Close"] > row["VWAP"] and
            row["VOLUME_RATIO"] >= 1.2 and
            50 <= row["RSI14"] <= 70
        )

        if not long_setup:
            continue

        raw_entry = float(row["Close"])
        entry = raw_entry * (1 + slippage_pct)
        stop = entry - 1.5 * float(row["ATR14"])
        risk = entry - stop
        target = entry + 1.5 * risk

        if risk <= 0:
            continue

        risk_amount = capital * risk_fraction
        quantity = max(int(risk_amount / risk), 0)
        if quantity == 0:
            continue

        result = None
        exit_price = None

        for j in range(i + 1, len(data)):
            candle = data.iloc[j]

            if candle["Low"] <= stop:
                exit_price = stop * (1 - slippage_pct)
                result = (exit_price - entry) * quantity
                break

            if candle["High"] >= target:
                exit_price = target * (1 - slippage_pct)
                result = (exit_price - entry) * quantity
                break

        if result is None:
            continue

        costs = 2 * brokerage_per_order + tax_pct * exit_price * quantity
        result -= costs

        capital += result
        trades.append({
            "entry": entry,
            "stop": stop,
            "target": target,
            "exit": exit_price,
            "quantity": quantity,
            "pnl": result,
            "capital": capital,
        })

    trades_df = pd.DataFrame(trades)
    metrics = compute_metrics(trades_df, initial_capital)
    return trades_df, capital, metrics
