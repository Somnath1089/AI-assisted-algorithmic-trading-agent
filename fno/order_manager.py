from datetime import date

from execution.order_manager import is_market_hours
from fno.instruments import is_expired, is_near_expiry

class FnoOrderManager:
    """Same "every check must pass or the order does not go" discipline as
    execution.order_manager.OrderManager, extended with the checks F&O
    specifically needs: lot-size conformance, margin (not just notional
    capital), and expiry. The AI layer has no path around this gate either."""

    def __init__(self, broker, risk_manager, near_expiry_days=2):
        self.broker = broker
        self.risk_manager = risk_manager
        self.near_expiry_days = near_expiry_days
        self._submitted_today = set()

    def reset_day(self):
        self._submitted_today.clear()

    def submit(self, instrument, signal, lots, allow_after_hours=False, now=None, today=None):
        today = today or date.today()

        if lots <= 0:
            return False, "Lot-size check failed: lots must be positive", None

        if is_expired(instrument, today):
            return False, f"Expiry check failed: {instrument.symbol} expired on {instrument.expiry.isoformat()}", None
        if is_near_expiry(instrument, today, self.near_expiry_days):
            return False, (
                f"Expiry check failed: {instrument.symbol} expires within "
                f"{self.near_expiry_days} day(s) - elevated rollover risk"
            ), None

        quantity = lots * instrument.lot_size
        margin = self.risk_manager.margin_required(signal.entry, instrument.lot_size, lots)
        if not self.risk_manager.can_add_margin(margin):
            return False, "Margin check failed: exceeds available capital", None

        ok, reason = self.risk_manager.can_trade()
        if not ok:
            return False, f"Daily-loss check failed: {reason}", None

        notional_risk = self.risk_manager.notional_risk(signal.entry, signal.stop_loss, instrument.lot_size, lots)
        if not self.risk_manager.can_add_open_risk(notional_risk):
            return False, "Max open risk check failed: exceeds maximum open risk", None

        key = (instrument.symbol, signal.side)
        if key in self._submitted_today:
            return False, "Duplicate-order check failed: order already placed for this contract/side today", None

        if not allow_after_hours and not is_market_hours(now):
            return False, "Market-hours check failed: NSE is closed", None

        if signal.side == "LONG" and signal.stop_loss >= signal.entry:
            return False, "Stop-loss check failed: stop must be below entry for a LONG", None
        if signal.side == "SHORT" and signal.stop_loss <= signal.entry:
            return False, "Stop-loss check failed: stop must be above entry for a SHORT", None

        if not self.broker.health_check():
            return False, "Broker/API health check failed", None

        order = self.broker.place_order(instrument.symbol, signal.side, quantity, price=signal.entry)
        self._submitted_today.add(key)
        self.risk_manager.add_margin(margin)
        self.risk_manager.add_open_risk(notional_risk)
        return True, "All checks passed", order
