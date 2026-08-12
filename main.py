from config import settings
from data.market_data import get_ohlcv, get_stock_info
from indicators.technical import add_indicators
from indicators.market_regime import market_regime
from fundamentals.fundamental_filter import fundamental_score
from fundamentals.sector_strength import sector_strength_score, SECTOR_INDEX
from strategies.signal_engine import generate_signal
from risk.risk_manager import RiskManager
from execution.broker import PaperBroker
from execution.order_manager import OrderManager
from paper_trading.tracker import PaperTradeTracker

UNIVERSE = [
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "INFY.NS",
    "TCS.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "AXISBANK.NS",
]

RISK_LEVEL_BY_GRADE = {"A+": "Low", "A": "Moderate", "B": "Elevated"}

def risk_level(grade):
    return RISK_LEVEL_BY_GRADE.get(grade, "High")

def scan(mode="INTRADAY"):
    nifty = add_indicators(get_ohlcv("^NSEI", period="1mo", interval="5m"))
    regime = market_regime(nifty)

    print("=" * 70)
    print("AI TRADING ALGORITHM AGENT - NSE CASH EQUITY")
    print(f"Mode: {mode} | F&O Enabled: {settings.fo_enabled}")
    print("NIFTY REGIME:", regime)
    print("=" * 70)

    if regime in ("UNCERTAIN", "HIGH VOLATILITY"):
        print("NO SAFE TRADE TODAY")
        print(f"Reason: Market regime is {regime}; capital preservation takes priority.")
        return

    risk = RiskManager(
        settings.capital,
        settings.risk_per_trade,
        settings.max_daily_loss,
        settings.max_trades_per_day,
        settings.max_open_risk,
    )
    broker = PaperBroker()
    order_manager = OrderManager(broker, risk)
    tracker = PaperTradeTracker()

    candidates = []

    for symbol in UNIVERSE:
        try:
            primary = add_indicators(get_ohlcv(symbol, period="1mo", interval="5m"))
            confirmation = add_indicators(get_ohlcv(symbol, period="6mo", interval="1d"))

            info = get_stock_info(symbol)
            fscore, freasons = fundamental_score(info)

            sector_symbol = SECTOR_INDEX.get(symbol)
            sector_df = None
            if sector_symbol:
                try:
                    sector_df = add_indicators(get_ohlcv(sector_symbol, period="1mo", interval="1d"))
                except Exception:
                    sector_df = None
            sscore, sreason = sector_strength_score(primary, sector_df)

            signal = generate_signal(
                symbol, primary, confirmation, regime,
                fscore, sscore, sreason, mode=mode,
            )

            if signal:
                candidates.append(signal)

        except Exception as exc:
            print(f"{symbol}: data/strategy error: {exc}")

    candidates.sort(key=lambda s: s.score, reverse=True)

    if not candidates:
        print("NO SAFE TRADE TODAY")
        return

    for signal in candidates[:5]:
        qty = risk.position_size(signal.entry, signal.stop_loss)

        print("\nStock Name:", signal.symbol)
        print("Trade Type:", signal.side)
        print("Signal Score:", f"{signal.score}/100 ({signal.grade})")
        print("Entry Price:", round(signal.entry, 2))
        print("Stop Loss:", round(signal.stop_loss, 2))
        print("Target 1:", round(signal.target1, 2))
        print("Target 2:", round(signal.target2, 2))
        print("Risk/Reward:", f"1:{signal.risk_reward}")
        print("Position Size:", qty)
        print("Risk Level:", risk_level(signal.grade))
        print("Reason:", "; ".join(signal.reasons))
        print("Market Context:", signal.market_context)
        print("Sector Context:", signal.sector_context)
        print("Invalidation:", signal.invalidation)
        print("Confidence:", signal.grade)

        if signal.score < settings.min_signal_score:
            print("-> WATCHLIST ONLY (below auto-eligibility threshold)")
            continue

        record = tracker.record_signal(signal)
        allowed, reason, order = order_manager.submit(
            signal, qty, allow_after_hours=not settings.enforce_market_hours
        )
        if allowed:
            tracker.record_execution(record, signal.entry)
            print("PAPER ORDER:", order)
        else:
            print("ORDER BLOCKED:", reason)

if __name__ == "__main__":
    scan()
