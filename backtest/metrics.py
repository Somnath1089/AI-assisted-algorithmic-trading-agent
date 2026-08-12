import numpy as np
import pandas as pd

def compute_metrics(trades: pd.DataFrame, initial_capital: float) -> dict:
    if trades.empty:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
            "profit_factor": 0.0, "expectancy": 0.0, "max_drawdown": 0.0,
            "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
            "max_consecutive_losses": 0, "final_capital": initial_capital,
        }

    pnl = trades["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    total_trades = len(trades)
    winning_trades = len(wins)
    losing_trades = len(losses)
    win_rate = winning_trades / total_trades

    avg_win = float(wins.mean()) if not wins.empty else 0.0
    avg_loss = float(abs(losses.mean())) if not losses.empty else 0.0

    gross_profit = float(wins.sum())
    gross_loss = float(abs(losses.sum()))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    expectancy = float(pnl.mean())

    equity = trades["capital"]
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_drawdown = float(drawdown.min())

    returns = pnl / initial_capital
    sharpe_ratio = float(returns.mean() / returns.std() * np.sqrt(len(returns))) if returns.std() > 0 else 0.0

    downside = returns[returns < 0]
    downside_std = downside.std()
    sortino_ratio = (
        float(returns.mean() / downside_std * np.sqrt(len(returns)))
        if downside_std and downside_std > 0 else 0.0
    )

    consecutive = 0
    max_consecutive_losses = 0
    for p in pnl:
        if p < 0:
            consecutive += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive)
        else:
            consecutive = 0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else float("inf"),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "max_consecutive_losses": max_consecutive_losses,
        "final_capital": round(float(equity.iloc[-1]), 2),
    }
