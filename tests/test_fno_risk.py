from fno.risk import FnoRiskManager

def test_lots_for_risk():
    rm = FnoRiskManager(capital=1000000, risk_per_trade=0.01)
    # risk_amount = 10000; risk_per_lot = |25000-24900|*65 = 6500 -> 1 lot
    lots = rm.lots_for_risk(entry=25000, stop=24900, lot_size=65)
    assert lots == 1

def test_lots_for_risk_zero_when_stop_equals_entry():
    rm = FnoRiskManager(capital=1000000, risk_per_trade=0.01)
    assert rm.lots_for_risk(entry=25000, stop=25000, lot_size=65) == 0

def test_notional_risk_is_full_price_move_not_margin():
    rm = FnoRiskManager(capital=1000000, risk_per_trade=0.01)
    notional = rm.notional_risk(entry=25000, stop=24900, lot_size=65, lots=1)
    assert notional == 100 * 65 * 1

def test_margin_is_a_fraction_of_notional_contract_value():
    rm = FnoRiskManager(capital=1000000, margin_pct=0.12)
    margin = rm.margin_required(entry=25000, lot_size=65, lots=1)
    contract_value = 25000 * 65 * 1
    assert margin == contract_value * 0.12
    assert margin < contract_value  # the whole point of margin vs notional

def test_margin_cannot_exceed_capital():
    rm = FnoRiskManager(capital=100000, margin_pct=0.12)
    # one NIFTY lot at 25000*65 = 1,625,000 notional -> margin ~195,000 > 100,000 capital
    margin = rm.margin_required(entry=25000, lot_size=65, lots=1)
    assert not rm.can_add_margin(margin)

def test_open_risk_cap_independent_of_margin():
    rm = FnoRiskManager(capital=1000000, max_open_risk=0.02)  # cap = 20000
    notional = rm.notional_risk(entry=25000, stop=24900, lot_size=65, lots=3)  # 100*65*3=19500
    assert rm.can_add_open_risk(notional)
    rm.add_open_risk(notional)
    assert not rm.can_add_open_risk(1000)  # 19500+1000 > 20000

def test_daily_loss_and_consecutive_loss_same_as_cash_equity():
    rm = FnoRiskManager(capital=1000000, max_daily_loss=0.02)
    rm.register_trade(-15000)
    rm.register_trade(-10000)
    ok, reason = rm.can_trade()
    assert not ok
    assert "daily loss" in reason.lower()
