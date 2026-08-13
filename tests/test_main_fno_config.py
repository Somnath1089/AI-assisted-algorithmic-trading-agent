import main
from config import settings

def test_fno_disabled_by_default_returns_none_status(monkeypatch):
    monkeypatch.setattr(settings, "fo_enabled", False)
    instruments, status = main.build_fno_instruments()
    assert instruments is None
    assert status is None

def test_fno_enabled_without_config_reports_status(monkeypatch):
    monkeypatch.setattr(settings, "fo_enabled", True)
    monkeypatch.setattr(settings, "fno_lot_size", "")
    monkeypatch.setattr(settings, "fno_expiry", "")
    instruments, status = main.build_fno_instruments()
    assert instruments is None
    assert status is not None
    assert "not configured" in status.lower()

def test_fno_enabled_with_invalid_config_reports_status(monkeypatch):
    monkeypatch.setattr(settings, "fo_enabled", True)
    monkeypatch.setattr(settings, "fno_lot_size", "not-a-number")
    monkeypatch.setattr(settings, "fno_expiry", "2026-06-25")
    instruments, status = main.build_fno_instruments()
    assert instruments is None
    assert "invalid" in status.lower()

def test_fno_enabled_with_valid_config_builds_instrument(monkeypatch):
    monkeypatch.setattr(settings, "fo_enabled", True)
    monkeypatch.setattr(settings, "fno_lot_size", "65")
    monkeypatch.setattr(settings, "fno_expiry", "2026-06-25")
    instruments, status = main.build_fno_instruments()
    assert status is None
    assert len(instruments) == 1
    assert instruments[0].lot_size == 65
    assert instruments[0].underlying == "NIFTY"
