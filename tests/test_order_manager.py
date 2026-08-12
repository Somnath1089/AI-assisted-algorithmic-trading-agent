from datetime import datetime, timezone, timedelta

from risk.risk_manager import RiskManager
from execution.broker import PaperBroker
from execution.order_manager import OrderManager
from strategies.signal_engine import Signal

def make_signal(symbol="TEST.NS", side="LONG", entry=100.0, stop=98.0):
    return Signal(
        symbol=symbol, side=side, score=80, grade="A",
        entry=entry, stop_loss=stop, target1=103.0, target2=104.0,
        risk_reward=1.5, reasons=["test"], market_context="BULLISH",
        sector_context="neutral", invalidation="n/a",
    )

def test_order_passes_all_checks():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    om = OrderManager(PaperBroker(), rm)
    ok, reason, order = om.submit(make_signal(), 50, allow_after_hours=True)
    assert ok
    assert order is not None

def test_duplicate_order_blocked():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    om = OrderManager(PaperBroker(), rm)
    signal = make_signal()
    om.submit(signal, 50, allow_after_hours=True)
    ok, reason, order = om.submit(signal, 50, allow_after_hours=True)
    assert not ok
    assert "duplicate" in reason.lower()

def test_invalid_stop_blocked_for_long():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    om = OrderManager(PaperBroker(), rm)
    signal = make_signal(stop=101.0)
    ok, reason, order = om.submit(signal, 50, allow_after_hours=True)
    assert not ok
    assert "stop-loss" in reason.lower()

def test_market_hours_check_blocks_after_hours():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    om = OrderManager(PaperBroker(), rm)
    after_hours = datetime(2026, 8, 12, 20, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    ok, reason, order = om.submit(make_signal(), 50, allow_after_hours=False, now=after_hours)
    assert not ok
    assert "market-hours" in reason.lower()

def test_max_open_risk_blocked():
    rm = RiskManager(100000, 0.01, 0.02, 3, max_open_risk=0.0005)
    om = OrderManager(PaperBroker(), rm)
    ok, reason, order = om.submit(make_signal(), 50, allow_after_hours=True)
    assert not ok
    assert "open risk" in reason.lower()
