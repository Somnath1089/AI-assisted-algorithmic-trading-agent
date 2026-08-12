import pandas as pd
from indicators.technical import add_indicators

def backtest(df, initial_capital=100000, risk_fraction=0.01):
    data = add_indicators(df)
    capital = initial_capital
    trades = []

    for i in range(50, len(data) - 1):
        row = data.iloc[i]

        long_setup = (
            row["Close"] > row["EMA20"] >
            row["SMA50"] and
            row["Close"] > row["VWAP"] and
            row["VOLUME_RATIO"] >= 1.2 and
            50 <= row["RSI14"] <= 70
        )

        if not long_setup:
            continue

        entry = float(row["Close"])
        stop = entry - 1.5 * float(row["ATR14"])
        risk = entry - stop
        target = entry + 1.5 * risk
        risk_amount = capital * risk_fraction

        result = None
        exit_price = None

        for j in range(i + 1, len(data)):
            candle = data.iloc[j]

            if candle["Low"] <= stop:
                result = -risk_amount
                exit_price = stop
                break

            if candle["High"] >= target:
                result = risk_amount * 1.5
                exit_price = target
                break

        if result is None:
            continue

        capital += result
        trades.append({
            "entry": entry,
            "stop": stop,
            "target": target,
            "exit": exit_price,
            "pnl": result,
            "capital": capital
        })

    return pd.DataFrame(trades), capital
