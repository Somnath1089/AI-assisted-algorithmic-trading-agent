from config import settings
from data.market_data import get_ohlcv as default_get_ohlcv, get_stock_info as default_get_stock_info
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

def run_scan(mode="INTRADAY", get_ohlcv=None, get_stock_info=None, broker=None):
    """Run one full scan and return a structured result - no printing here,
    so this can drive the CLI, a dashboard, or a test equally. get_ohlcv /
    get_stock_info / broker are injectable so callers can swap in a live
    provider (Dhan), a fake, or synthetic data without touching this logic."""
    get_ohlcv = get_ohlcv or default_get_ohlcv
    get_stock_info = get_stock_info or default_get_stock_info

    result = {
        "mode": mode,
        "fo_enabled": settings.fo_enabled,
        "regime": None,
        "blocked_reason": None,
        "summary": [],
        "signals": [],
        "orders": [],
        "risk_snapshot": None,
        "errors": [],
    }

    try:
        nifty = add_indicators(get_ohlcv("^NSEI", period="1mo", interval="5m"))
        regime = market_regime(nifty)
    except Exception as exc:
        result["blocked_reason"] = f"NIFTY market data unavailable: {exc}"
        return result

    result["regime"] = regime

    if regime in ("UNCERTAIN", "HIGH VOLATILITY"):
        result["blocked_reason"] = f"Market regime is {regime}; capital preservation takes priority."
        return result

    risk = RiskManager(
        settings.capital,
        settings.risk_per_trade,
        settings.max_daily_loss,
        settings.max_trades_per_day,
        settings.max_open_risk,
    )
    broker = broker or PaperBroker()
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
                result["summary"].append((symbol, signal.decision, f"{signal.score} ({signal.grade})", signal.pattern or "-"))
            else:
                result["summary"].append((symbol, "AVOID", "-", "-"))

        except Exception as exc:
            result["summary"].append((symbol, "AVOID", "error", "-"))
            result["errors"].append((symbol, str(exc)))

    candidates.sort(key=lambda s: s.score, reverse=True)
    result["signals"] = candidates[:5]

    for signal in result["signals"]:
        qty = risk.position_size(signal.entry, signal.stop_loss)
        order_entry = {"signal": signal, "quantity": qty, "allowed": False, "reason": None, "order": None}

        if signal.score < settings.min_signal_score:
            order_entry["reason"] = "WATCHLIST ONLY (below auto-eligibility threshold)"
        else:
            record = tracker.record_signal(signal)
            allowed, reason, order = order_manager.submit(
                signal, qty, allow_after_hours=not settings.enforce_market_hours
            )
            order_entry["allowed"] = allowed
            order_entry["reason"] = reason
            order_entry["order"] = order
            if allowed:
                tracker.record_execution(record, signal.entry)

        result["orders"].append(order_entry)

    result["risk_snapshot"] = {
        "capital": risk.capital,
        "daily_pnl": risk.daily_pnl,
        "trade_count": risk.trade_count,
        "max_trades": risk.max_trades,
        "open_risk": risk.open_risk,
        "max_open_risk_amount": risk.max_open_risk_amount,
    }

    return result

def _exit_plan(signal):
    return (
        f"Book at Target 1 ({round(signal.target1, 2)}); trail remainder to Target 2 "
        f"({round(signal.target2, 2)}). Exit immediately on Stop Loss "
        f"({round(signal.stop_loss, 2)}) or if: {signal.invalidation}"
    )

def _print_report(result):
    print("=" * 70)
    print("AI TRADING ALGORITHM AGENT - NSE CASH EQUITY")
    print(f"Mode: {result['mode']} | F&O Enabled: {result['fo_enabled']}")
    print("NIFTY REGIME:", result["regime"] or "UNKNOWN")
    print("=" * 70)

    for symbol, error in result["errors"]:
        print(f"{symbol}: data/strategy error: {error}")

    if result["blocked_reason"]:
        print("NO SAFE TRADE TODAY")
        print(f"Reason: {result['blocked_reason']}")
        return

    print(f"\n{'SYMBOL':<16}{'DECISION':<10}{'SCORE':<14}{'PATTERN':<24}")
    for symbol, decision, score_label, pattern in result["summary"]:
        print(f"{symbol:<16}{decision:<10}{score_label:<14}{pattern:<24}")

    if not result["signals"]:
        print("\nNO SAFE TRADE TODAY")
        return

    for order_entry in result["orders"]:
        signal = order_entry["signal"]

        print("\nStock Name:", signal.symbol)
        print("Signal:", f"{signal.decision} ({signal.side})")
        print("Trade Type:", signal.side)
        print("Signal Score:", f"{signal.score}/100 ({signal.grade})")
        print("Chart Pattern:", f"{signal.pattern or 'None'} ({signal.pattern_bias})")
        print("Entry Price:", round(signal.entry, 2))
        print("Stop Loss:", round(signal.stop_loss, 2))
        print("Target 1:", round(signal.target1, 2))
        print("Target 2:", round(signal.target2, 2))
        print("Exit Plan:", _exit_plan(signal))
        print("Risk/Reward:", f"1:{signal.risk_reward}")
        print("Position Size:", order_entry["quantity"])
        print("Risk Level:", risk_level(signal.grade))
        print("Reason:", "; ".join(signal.reasons))
        print("Market Context:", signal.market_context)
        print("Sector Context:", signal.sector_context)
        print("Invalidation:", signal.invalidation)
        print("Confidence:", signal.grade)

        if order_entry["allowed"]:
            print("PAPER ORDER:", order_entry["order"])
        elif order_entry["order"] is None and order_entry["reason"] and "WATCHLIST" in order_entry["reason"]:
            print("->", order_entry["reason"])
        else:
            print("ORDER BLOCKED:", order_entry["reason"])

def scan(mode="INTRADAY"):
    result = run_scan(mode=mode)
    _print_report(result)
    return result

if __name__ == "__main__":
    scan()
