from config import settings
from data.market_data import get_ohlcv
from indicators.technical import add_indicators
from indicators.market_regime import market_regime
from strategies.signal_engine import generate_signal
from risk.risk_manager import RiskManager
from execution.broker import PaperBroker

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

def scan():
    # Use NIFTY as the broad-market regime proxy.
    nifty = add_indicators(get_ohlcv("^NSEI", period="3mo", interval="5m"))
    regime = market_regime(nifty)

    risk = RiskManager(
        settings.capital,
        settings.risk_per_trade,
        settings.max_daily_loss,
        settings.max_trades_per_day,
    )

    broker = PaperBroker()

    print("=" * 60)
    print("AI TRADING AGENT")
    print("NIFTY REGIME:", regime)
    print("=" * 60)

    candidates = []

    for symbol in UNIVERSE:
        try:
            df = add_indicators(
                get_ohlcv(symbol, period="3mo", interval="5m")
            )

            signal = generate_signal(
                symbol,
                df,
                regime,
                settings.min_signal_score
            )

            if signal:
                qty = risk.position_size(
                    signal.entry,
                    signal.stop_loss
                )

                candidates.append((signal, qty))

        except Exception as exc:
            print(f"{symbol}: data/strategy error: {exc}")

    candidates.sort(key=lambda x: x[0].score, reverse=True)

    if not candidates:
        print("NO SAFE TRADE TODAY")
        return

    for signal, qty in candidates[:5]:
        print("\n", signal.symbol)
        print("Trade Type:", signal.side)
        print("Score:", signal.score)
        print("Entry:", round(signal.entry, 2))
        print("Stop Loss:", round(signal.stop_loss, 2))
        print("Target 1:", round(signal.target1, 2))
        print("Target 2:", round(signal.target2, 2))
        print("Quantity:", qty)
        print("Reason:", "; ".join(signal.reasons))

        allowed, reason = risk.can_trade()
        if allowed and qty > 0:
            order = broker.place_order(
                signal.symbol,
                signal.side,
                qty
            )
            print("PAPER ORDER:", order)
        else:
            print("ORDER BLOCKED:", reason)

if __name__ == "__main__":
    scan()
