"""
F&O risk management differs from cash equity in one crucial way that is
worth stating plainly: margin is not your risk. Margin is the capital the
exchange blocks to let you hold a leveraged position; your actual loss on a
stop-out is driven by the full notional price move times lot size times
lots, which is normally many times larger than the margin paid. A risk
manager that only checks "can I afford the margin" and not "how much could
this actually lose me" is not doing risk management - it is doing capital
accounting. This module tracks both separately and caps both.
"""

class FnoRiskManager:
    def __init__(self, capital, risk_per_trade=0.01, max_daily_loss=0.02,
                 max_trades=3, max_open_risk=0.02, margin_pct=0.12):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss_amount = capital * max_daily_loss
        self.max_trades = max_trades
        self.max_open_risk_amount = capital * max_open_risk
        self.margin_pct = margin_pct

        self.daily_pnl = 0.0
        self.trade_count = 0
        self.consecutive_losses = 0
        self.open_risk = 0.0
        self.margin_used = 0.0

    def can_trade(self):
        if self.trade_count >= self.max_trades:
            return False, "Maximum daily trades reached"
        if self.daily_pnl <= -self.max_daily_loss_amount:
            return False, "Maximum daily loss reached"
        if self.consecutive_losses >= 2:
            return False, "Two consecutive losses"
        return True, "Risk checks passed"

    def lots_for_risk(self, entry, stop, lot_size):
        """Number of lots such that a stop-out loses ~risk_per_trade of
        capital - the same discipline as cash equity's position_size(),
        generalized to a per-lot P&L instead of a per-share one."""
        risk_per_lot = abs(entry - stop) * lot_size
        if risk_per_lot <= 0:
            return 0
        risk_amount = self.capital * self.risk_per_trade
        return max(int(risk_amount / risk_per_lot), 0)

    def notional_risk(self, entry, stop, lot_size, lots):
        return abs(entry - stop) * lot_size * lots

    def margin_required(self, entry, lot_size, lots, margin_pct=None):
        contract_value = entry * lot_size * lots
        return contract_value * (self.margin_pct if margin_pct is None else margin_pct)

    def can_add_margin(self, amount):
        return (self.margin_used + amount) <= self.capital

    def add_margin(self, amount):
        self.margin_used += amount

    def release_margin(self, amount):
        self.margin_used = max(0.0, self.margin_used - amount)

    def can_add_open_risk(self, amount):
        return (self.open_risk + amount) <= self.max_open_risk_amount

    def add_open_risk(self, amount):
        self.open_risk += amount

    def release_open_risk(self, amount):
        self.open_risk = max(0.0, self.open_risk - amount)

    def register_trade(self, pnl):
        self.trade_count += 1
        self.daily_pnl += pnl
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0
