class RiskManager:
    def __init__(self, capital, risk_per_trade=0.01,
                 max_daily_loss=0.02, max_trades=3, max_open_risk=0.02):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss_amount = capital * max_daily_loss
        self.max_trades = max_trades
        self.max_open_risk_amount = capital * max_open_risk
        self.daily_pnl = 0.0
        self.trade_count = 0
        self.consecutive_losses = 0
        self.open_risk = 0.0

    def can_trade(self):
        if self.trade_count >= self.max_trades:
            return False, "Maximum daily trades reached"
        if self.daily_pnl <= -self.max_daily_loss_amount:
            return False, "Maximum daily loss reached"
        if self.consecutive_losses >= 2:
            return False, "Two consecutive losses"
        return True, "Risk checks passed"

    def position_size(self, entry, stop):
        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            return 0
        risk_amount = self.capital * self.risk_per_trade
        return max(int(risk_amount / risk_per_share), 0)

    def register_trade(self, pnl):
        self.trade_count += 1
        self.daily_pnl += pnl
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def can_add_open_risk(self, amount):
        return (self.open_risk + amount) <= self.max_open_risk_amount

    def add_open_risk(self, amount):
        self.open_risk += amount

    def release_open_risk(self, amount):
        self.open_risk = max(0.0, self.open_risk - amount)
