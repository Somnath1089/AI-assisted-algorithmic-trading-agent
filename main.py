from datetime import date

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
from fno.instruments import nifty_futures
from fno.risk import FnoRiskManager
from fno.order_manager import FnoOrderManager
from fno.scan import run_fno_scan

# NIFTYBEES.NS is a real, NSE-listed Nifty 50 index ETF - the way to hold
# NIFTY exposure in cash equity (you can't buy the index itself). This is
# what "activate NIFTY" means on the cash-equity side; the leveraged side
# (NIFTY futures) lives in the F&O leg below.
UNIVERSE = [
    "NIFTYBEES.NS",
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

def build_fno_instruments():
    """Returns (instruments, status_message). status_message is None when
    everything's fine (F&O off, or on and configured); it carries an
    explanation whenever F&O is enabled but can't actually run, so that
    state is visible instead of silently doing nothing."""
    if not settings.fo_enabled:
        return None, None
    if not settings.fno_lot_size or not settings.fno_expiry:
        return None, (
            "F&O enabled but not configured: set FNO_LOT_SIZE and FNO_EXPIRY in "
            ".env, verified against the current NSE F&O circular, to activate it."
        )
    try:
        lot_size = int(settings.fno_lot_size)
        expiry = date.fromisoformat(settings.fno_expiry)
    except ValueError as exc:
        return None, f"F&O enabled but FNO_LOT_SIZE/FNO_EXPIRY are invalid: {exc}"
    return [nifty_futures(lot_size, expiry)], None

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
        "fno_status": None,
        "fno_orders": None,
        "fno_risk_snapshot": None,
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

    fno_instruments, fno_status = build_fno_instruments()
    result["fno_status"] = fno_status
    if fno_instruments:
        fno_risk = FnoRiskManager(
            settings.capital, settings.risk_per_trade, settings.max_daily_loss,
            settings.max_trades_per_day, settings.max_open_risk, settings.fno_margin_pct,
        )
        fno_broker = broker if broker else PaperBroker()
        fno_order_manager = FnoOrderManager(fno_broker, fno_risk)
        result["fno_orders"] = run_fno_scan(
            fno_instruments, get_ohlcv, regime, fno_risk, fno_order_manager,
            mode=mode, allow_after_hours=not settings.enforce_market_hours,
        )
        result["fno_risk_snapshot"] = {
            "capital": fno_risk.capital,
            "daily_pnl": fno_risk.daily_pnl,
            "trade_count": fno_risk.trade_count,
            "max_trades": fno_risk.max_trades,
            "open_risk": fno_risk.open_risk,
            "max_open_risk_amount": fno_risk.max_open_risk_amount,
            "margin_used": fno_risk.margin_used,
        }

    return result

def _exit_plan(signal):
    return (
        f"Book at Target 1 ({round(signal.target1, 2)}); trail remainder to Target 2 "
        f"({round(signal.target2, 2)}). Exit immediately on Stop Loss "
        f"({round(signal.stop_loss, 2)}) or if: {signal.invalidation}"
    )

def _print_signal_block(signal, quantity, allowed, reason, order, label="Stock Name"):
    print(f"\n{label}:", signal.symbol)
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
    print("Position Size:", quantity)
    print("Risk Level:", risk_level(signal.grade))
    print("Reason:", "; ".join(signal.reasons))
    print("Market Context:", signal.market_context)
    print("Sector Context:", signal.sector_context)
    print("Invalidation:", signal.invalidation)
    print("Confidence:", signal.grade)

    if allowed:
        print("PAPER ORDER:", order)
    elif order is None and reason and "WATCHLIST" in reason:
        print("->", reason)
    else:
        print("ORDER BLOCKED:", reason)

def _print_report(result):
    print("=" * 70)
    print("AI TRADING ALGORITHM AGENT - NSE CASH EQUITY + F&O")
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
        print("\nNO SAFE TRADE TODAY (cash equity)")
    else:
        for order_entry in result["orders"]:
            _print_signal_block(
                order_entry["signal"], order_entry["quantity"],
                order_entry["allowed"], order_entry["reason"], order_entry["order"],
            )

    print("\n" + "=" * 70)
    print("F&O")
    print("=" * 70)
    if result["fno_status"]:
        print(result["fno_status"])
    elif result["fno_orders"] is None:
        print("F&O disabled (FO_ENABLED=false)")
    else:
        any_signal = False
        for entry in result["fno_orders"]:
            instrument = entry["instrument"]
            if entry["signal"] is None:
                print(f"\n{instrument.symbol}: {entry['reason']}")
                continue
            any_signal = True
            _print_signal_block(
                entry["signal"], entry["lots"] * instrument.lot_size,
                entry["allowed"], entry["reason"], entry["order"],
                label="Contract",
            )
            print("Lot Size:", instrument.lot_size, "| Lots:", entry["lots"], "| Expiry:", instrument.expiry.isoformat())
        if not any_signal:
            print("NO SAFE TRADE TODAY (F&O)")

def scan(mode="INTRADAY"):
    result = run_scan(mode=mode)
    _print_report(result)
    return result

if __name__ == "__main__":
    scan()
