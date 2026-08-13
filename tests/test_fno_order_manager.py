from datetime import date, datetime, timezone, timedelta

from fno.instruments import nifty_futures
from fno.risk import FnoRiskManager
from fno.order_manager import FnoOrderManager
from execution.broker import PaperBroker
from strategies.signal_engine import Signal

def make_signal(side="LONG", entry=25000.0, stop=24900.0):
    return Signal(
        symbol="NIFTY-FUT-2026-06-25", side=side, score=85, grade="A+",
        entry=entry, stop_loss=stop, target1=25150.0, target2=25200.0,
        risk_reward=1.5, reasons=["test"], market_context="BULLISH",
        sector_context="Index derivative", invalidation="n/a",
    )

def make_manager(capital=5000000, margin_pct=0.12, near_expiry_days=2):
    rm = FnoRiskManager(capital, margin_pct=margin_pct)
    om = FnoOrderManager(PaperBroker(), rm, near_expiry_days=near_expiry_days)
    return om, rm

def test_order_passes_all_checks():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    ok, reason, order = om.submit(inst, make_signal(), lots=1, allow_after_hours=True, today=date(2026, 6, 1))
    assert ok
    assert order["quantity"] == 65

def test_zero_lots_blocked():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    ok, reason, order = om.submit(inst, make_signal(), lots=0, allow_after_hours=True, today=date(2026, 6, 1))
    assert not ok
    assert "lot-size" in reason.lower()

def test_expired_contract_blocked():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    ok, reason, order = om.submit(inst, make_signal(), lots=1, allow_after_hours=True, today=date(2026, 6, 26))
    assert not ok
    assert "expiry" in reason.lower()
    assert "expired" in reason.lower()

def test_near_expiry_blocked():
    om, rm = make_manager(near_expiry_days=2)
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    ok, reason, order = om.submit(inst, make_signal(), lots=1, allow_after_hours=True, today=date(2026, 6, 24))
    assert not ok
    assert "expiry" in reason.lower()
    assert "rollover" in reason.lower()

def test_margin_exceeding_capital_blocked():
    om, rm = make_manager(capital=100000)  # too small for even 1 lot of NIFTY-sized notional
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    ok, reason, order = om.submit(inst, make_signal(), lots=1, allow_after_hours=True, today=date(2026, 6, 1))
    assert not ok
    assert "margin" in reason.lower()

def test_duplicate_order_blocked():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    signal = make_signal()
    om.submit(inst, signal, lots=1, allow_after_hours=True, today=date(2026, 6, 1))
    ok, reason, order = om.submit(inst, signal, lots=1, allow_after_hours=True, today=date(2026, 6, 1))
    assert not ok
    assert "duplicate" in reason.lower()

def test_invalid_stop_blocked():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    signal = make_signal(stop=25100.0)  # above entry for a LONG - invalid
    ok, reason, order = om.submit(inst, signal, lots=1, allow_after_hours=True, today=date(2026, 6, 1))
    assert not ok
    assert "stop-loss" in reason.lower()

def test_market_hours_check_blocks_after_hours():
    om, rm = make_manager()
    inst = nifty_futures(lot_size=65, expiry=date(2026, 6, 25))
    after_hours = datetime(2026, 6, 1, 20, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    ok, reason, order = om.submit(inst, make_signal(), lots=1, allow_after_hours=False, now=after_hours, today=date(2026, 6, 1))
    assert not ok
    assert "market-hours" in reason.lower()
