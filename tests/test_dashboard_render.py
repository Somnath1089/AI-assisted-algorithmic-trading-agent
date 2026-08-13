from strategies.signal_engine import Signal
from dashboard.render import render_dashboard

def _make_signal(symbol="TEST.NS", side="LONG", decision="BUY", pattern="", pattern_bias="NEUTRAL"):
    return Signal(
        symbol=symbol, side=side, score=88, grade="A+",
        entry=100.0, stop_loss=98.0, target1=103.0, target2=104.0,
        risk_reward=1.5, reasons=["Price above EMA20 above SMA50 (uptrend structure)"],
        market_context="BULLISH", sector_context="Stock outperforming its sector",
        invalidation="Close back below EMA20/VWAP invalidates the long setup",
        decision=decision, pattern=pattern, pattern_bias=pattern_bias,
    )

def _base_result(orders):
    return {
        "mode": "INTRADAY",
        "fo_enabled": False,
        "regime": "BULLISH",
        "blocked_reason": None,
        "summary": [("TEST.NS", "BUY", "88 (A+)", "-"), ("OTHER.NS", "AVOID", "-", "-")],
        "signals": [o["signal"] for o in orders],
        "orders": orders,
        "risk_snapshot": {
            "capital": 100000.0, "daily_pnl": 0.0, "trade_count": 0,
            "max_trades": 3, "open_risk": 1500.0, "max_open_risk_amount": 2000.0,
        },
        "errors": [],
    }

def test_render_placed_order():
    signal = _make_signal()
    order = {"signal": signal, "quantity": 500, "allowed": True, "reason": "All checks passed",
              "order": {"order_id": "PAPER-1", "quantity": 500, "price": 100.0}}
    html = render_dashboard(_base_result([order]))
    assert "TEST.NS" in html
    assert "PAPER ORDER PLACED" in html
    assert "NSE Signal Desk" in html
    assert "@font-face" in html

def test_render_blocked_order():
    signal = _make_signal()
    order = {"signal": signal, "quantity": 500, "allowed": False,
              "reason": "Max open risk check failed: exceeds maximum open risk", "order": None}
    html = render_dashboard(_base_result([order]))
    assert "ORDER BLOCKED" in html
    assert "Max open risk check failed" in html

def test_render_pattern_confirm_and_conflict_coloring():
    signal = _make_signal(pattern="INVERSE_HEAD_AND_SHOULDERS", pattern_bias="BULLISH")
    signal.reasons = signal.reasons + ["Chart pattern confirms setup: INVERSE_HEAD_AND_SHOULDERS"]
    order = {"signal": signal, "quantity": 500, "allowed": True, "reason": "All checks passed",
              "order": {"order_id": "PAPER-1", "quantity": 500, "price": 100.0}}
    html = render_dashboard(_base_result([order]))
    assert "reason-confirm" in html
    assert "INVERSE HEAD AND SHOULDERS" in html

def test_render_no_safe_trade_today():
    result = {
        "mode": "INTRADAY", "fo_enabled": False, "regime": "UNCERTAIN",
        "blocked_reason": "Market regime is UNCERTAIN; capital preservation takes priority.",
        "summary": [], "signals": [], "orders": [], "risk_snapshot": None, "errors": [],
    }
    html = render_dashboard(result)
    assert "NO SAFE TRADE TODAY" in html
    assert "UNCERTAIN" in html

def test_render_watchlist_only_status():
    signal = _make_signal(decision="SELL", side="SHORT")
    order = {"signal": signal, "quantity": 500, "allowed": False,
              "reason": "WATCHLIST ONLY (below auto-eligibility threshold)", "order": None}
    html = render_dashboard(_base_result([order]))
    assert "WATCHLIST ONLY" in html
