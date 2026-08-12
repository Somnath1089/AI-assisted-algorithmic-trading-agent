# AI Trading Algorithm Agent

## Purpose
Disciplined, rule-based NSE Intraday/Swing research and paper-trading engine.
Optimizes for capital preservation and high-probability setups, not trade
frequency. Cash equity only by default; F&O stays off unless explicitly
enabled.

## Architecture
```
Data Feed -> Technical Engine -> Fundamental Filter -> Sector Strength
          -> Market Regime -> Signal Engine -> Risk Engine
          -> Order Manager -> Broker Adapter -> Paper Trade Tracker
```

The AI layer explains and ranks validated setups; it never invents a trade
and never bypasses the Order Manager's deterministic checks.

## Trading universe
NIFTY 50 / large-cap, liquid NSE stocks only. Penny stocks, illiquid names,
and stocks with unreliable data are out of scope by design (small, curated
`UNIVERSE` list in `main.py`).

## Technical engine
EMA20, SMA50, VWAP, RSI14, ATR14, volume/average-volume ratio, rolling
support/resistance, breakout/breakdown flags, and a simplified trend-strength
measure (`|EMA20-SMA50| / ATR14`). Intraday signals use 5-minute primary bars
confirmed against a daily higher timeframe; swing mode is intended to run
primary=daily / confirmation=weekly.

## Market regime
NIFTY 50 regime is one of `BULLISH`, `BEARISH`, `SIDEWAYS`, `HIGH VOLATILITY`,
`UNCERTAIN`. `HIGH VOLATILITY` is flagged when ATR/Close expands materially
above its recent average. `UNCERTAIN` and `HIGH VOLATILITY` both short-circuit
the scan to `NO SAFE TRADE TODAY` - capital preservation over forcing trades
into unclear conditions.

## Fundamental filter
`fundamentals/fundamental_filter.py` scores revenue growth, profit growth,
debt/equity, ROE, promoter holding, and a basic valuation sanity check from
`yfinance` ticker info, producing a 0-10 score (baseline 5, +/-1 per signal).
Weak fundamentals penalize the setup score; they don't hard-block an
otherwise strong Intraday setup.

## Sector strength
`fundamentals/sector_strength.py` compares a stock's recent return against a
mapped NSE sector index and scores relative outperformance 0-10. Falls back
to a neutral score when sector data isn't available.

## Signal scoring (100 points)
| Component            | Points |
|-----------------------|--------|
| Technical Trend       | 20     |
| Price Action          | 15     |
| Volume Confirmation   | 15     |
| Market Regime         | 15     |
| Sector Strength       | 10     |
| VWAP                  | 5      |
| RSI                   | 5      |
| Fundamentals          | 10     |
| Risk/Reward           | 5      |

`85-100 = A+`, `75-84 = A`, `65-74 = B (watchlist)`, `<65 = NO TRADE`.
Only setups scoring at/above `MIN_SIGNAL_SCORE` (default 75, i.e. grade A/A+)
are auto-submitted to the paper broker; a `B` grade is surfaced as watchlist
only. A setup whose regime opposes its direction (e.g. a LONG when NIFTY is
BEARISH) has its score halved rather than hard-blocked, so counter-trend
setups need an unusually strong confluence to clear the bar. If Target 1
would be capped by a nearer support/resistance level before reaching 1.5R,
the setup is dropped entirely.

## Risk management
- Max 1-2% risk per trade (`RISK_PER_TRADE`)
- Max 2% daily loss (`MAX_DAILY_LOSS`)
- Max 2% aggregate open risk across live positions (`MAX_OPEN_RISK`)
- Max 3 trades/day (`MAX_TRADES_PER_DAY`)
- Stop after 2 consecutive losses

## Order manager
Every order passes through `execution/order_manager.py`, which enforces, in
order: capital check, position-size check, daily-loss check, max-open-risk
check, duplicate-order check, market-hours check (NSE 09:15-15:30 IST,
Mon-Fri), stop-loss sanity check, and a broker health check. Any failed check
blocks the order - the AI layer has no path around this gate.

## Backtesting
`backtest/engine.py` runs a simple long-only backtest with slippage and
brokerage/tax deductions; `backtest/metrics.py` reports win rate, average
win/loss, profit factor, expectancy, max drawdown, Sharpe/Sortino ratios
(per-trade approximations, not calendar-annualized), and max consecutive
losses.

## Paper trading
`paper_trading/tracker.py` records each signal's expected entry/stop/target1
alongside actual execution, so expected-vs-actual slippage and target/stop
hit rates can be reviewed before considering live trading.

## Install

```
python -m venv .venv
```

Windows:
```
.venv\Scripts\activate
```

macOS/Linux:
```
source .venv/bin/activate
```

```
pip install -r requirements.txt
```

## Configure

Copy `.env.example` to `.env`.

Keep:
```
LIVE_TRADING=false
FO_ENABLED=false
```
until the complete system has been validated.

## Run

```
python main.py
```

## Tests

```
pytest -q
```

## Important production work still required
1. Replace generic Yahoo Finance feed with a reliable real-time licensed/broker feed.
2. Add proper NSE symbol master and corporate-action handling.
3. Validate/replace `yfinance` fundamental fields (`revenueGrowth`, `heldPercentInsiders`,
   etc.) - coverage and accuracy for NSE tickers is inconsistent.
4. Add real sector-index data and expand the sector map beyond the starter universe.
5. Add walk-forward and out-of-sample testing; the current backtester is in-sample only.
6. Add persistent trade database.
7. Add authentication and secrets management.
8. Implement the selected broker's current API contract (health check is currently a stub).
9. Add order reconciliation and kill-switch.
10. Add a proper NSE trading-calendar/holiday check (current market-hours check is
    day-of-week + time-of-day only).
11. Validate current Indian algo-trading/broker/exchange requirements before live deployment.

Historical backtest results do not guarantee future returns.
