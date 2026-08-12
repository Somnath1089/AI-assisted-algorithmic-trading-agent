# AI Trading Algorithm Agent

## Purpose
Rule-based NSE Intraday/Swing research and paper-trading engine.

## Architecture
Market Data → Technical Engine → Fundamental Filter → Market Regime → Signal Scoring → Risk Engine → Backtester → Paper Trading → Broker Adapter → Monitoring

The AI layer explains and ranks validated setups; deterministic risk controls remain between strategy signals and broker execution.

## Default rules
- Cash equity only
- EMA20
- SMA50
- VWAP
- RSI14
- ATR14
- Volume confirmation
- NIFTY market-regime filter
- 1% risk per trade
- 2% maximum daily loss
- Maximum 3 trades/day
- Stop after 2 consecutive losses
- Minimum signal score 75

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
3. Add realistic brokerage, taxes and slippage to backtests.
4. Add walk-forward and out-of-sample testing.
5. Add persistent trade database.
6. Add authentication and secrets management.
7. Implement the selected broker's current API contract.
8. Add order reconciliation and kill-switch.
9. Add market-hours/calendar checks.
10. Validate current Indian algo-trading/broker/exchange requirements before live deployment.

Historical backtest results do not guarantee future returns.
