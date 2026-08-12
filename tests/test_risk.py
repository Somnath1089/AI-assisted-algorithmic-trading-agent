from risk.risk_manager import RiskManager

def test_position_size():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    qty = rm.position_size(100, 98)
    assert qty == 500

def test_daily_limit():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    rm.register_trade(-500)
    rm.register_trade(-500)
    ok, reason = rm.can_trade()
    assert not ok
    assert "consecutive" in reason.lower()

def test_max_daily_loss():
    rm = RiskManager(100000, 0.01, 0.02, 3)
    rm.register_trade(-1200)
    rm.register_trade(-900)
    ok, reason = rm.can_trade()
    assert not ok
    assert "daily loss" in reason.lower()
