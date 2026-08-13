from datetime import date
import pytest

from fno.instruments import FnoInstrument, days_to_expiry, is_expired, is_near_expiry, nifty_futures

def test_lot_size_must_be_positive():
    with pytest.raises(ValueError, match="lot_size must be a positive integer"):
        FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="FUT", lot_size=0, expiry=date(2026, 1, 29))

def test_lot_size_must_be_verified_not_negative():
    with pytest.raises(ValueError):
        FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="FUT", lot_size=-65, expiry=date(2026, 1, 29))

def test_invalid_instrument_type_rejected():
    with pytest.raises(ValueError, match="instrument_type must be"):
        FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="SWAP", lot_size=65, expiry=date(2026, 1, 29))

def test_option_requires_strike_and_type():
    with pytest.raises(ValueError, match="require a positive strike"):
        FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="OPT", lot_size=65,
                      expiry=date(2026, 1, 29), option_type="CE")

def test_option_requires_valid_option_type():
    with pytest.raises(ValueError, match="option_type must be"):
        FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="OPT", lot_size=65,
                      expiry=date(2026, 1, 29), strike=25000, option_type="CALL")

def test_valid_option_constructs():
    inst = FnoInstrument(symbol="X", underlying="NIFTY", instrument_type="OPT", lot_size=65,
                         expiry=date(2026, 1, 29), strike=25000, option_type="CE")
    assert inst.strike == 25000

def test_days_to_expiry():
    inst = nifty_futures(lot_size=65, expiry=date(2026, 1, 29))
    assert days_to_expiry(inst, date(2026, 1, 27)) == 2
    assert days_to_expiry(inst, date(2026, 1, 29)) == 0
    assert days_to_expiry(inst, date(2026, 1, 30)) == -1

def test_is_expired():
    inst = nifty_futures(lot_size=65, expiry=date(2026, 1, 29))
    assert not is_expired(inst, date(2026, 1, 29))
    assert is_expired(inst, date(2026, 1, 30))

def test_is_near_expiry():
    inst = nifty_futures(lot_size=65, expiry=date(2026, 1, 29))
    assert is_near_expiry(inst, date(2026, 1, 27), threshold_days=2)
    assert not is_near_expiry(inst, date(2026, 1, 20), threshold_days=2)
    assert not is_near_expiry(inst, date(2026, 1, 30), threshold_days=2)
