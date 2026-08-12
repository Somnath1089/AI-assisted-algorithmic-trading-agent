from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def is_market_hours(now=None):
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

class OrderManager:
    """Every order must pass all deterministic risk checks before it
    reaches the broker. The AI layer never has a path around this gate."""

    def __init__(self, broker, risk_manager):
        self.broker = broker
        self.risk_manager = risk_manager
        self._submitted_today = set()

    def reset_day(self):
        self._submitted_today.clear()

    def submit(self, signal, quantity, allow_after_hours=False, now=None):
        if quantity <= 0:
            return False, "Position-size check failed: quantity must be positive", None

        if signal.entry * quantity > self.risk_manager.capital:
            return False, "Capital check failed: order exceeds available capital", None

        ok, reason = self.risk_manager.can_trade()
        if not ok:
            return False, f"Daily-loss check failed: {reason}", None

        open_risk_amount = abs(signal.entry - signal.stop_loss) * quantity
        if not self.risk_manager.can_add_open_risk(open_risk_amount):
            return False, "Max open risk check failed: exceeds maximum open risk", None

        key = (signal.symbol, signal.side)
        if key in self._submitted_today:
            return False, "Duplicate-order check failed: order already placed for this symbol/side today", None

        if not allow_after_hours and not is_market_hours(now):
            return False, "Market-hours check failed: NSE is closed", None

        if signal.side == "LONG" and signal.stop_loss >= signal.entry:
            return False, "Stop-loss check failed: stop must be below entry for a LONG", None
        if signal.side == "SHORT" and signal.stop_loss <= signal.entry:
            return False, "Stop-loss check failed: stop must be above entry for a SHORT", None

        if not self.broker.health_check():
            return False, "Broker/API health check failed", None

        order = self.broker.place_order(signal.symbol, signal.side, quantity, price=signal.entry)
        self._submitted_today.add(key)
        self.risk_manager.add_open_risk(open_risk_amount)
        return True, "All checks passed", order
