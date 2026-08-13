from indicators.technical import add_indicators
from strategies.signal_engine import generate_signal

def run_fno_scan(instruments, get_ohlcv, regime, risk_manager, order_manager,
                  mode="INTRADAY", allow_after_hours=False):
    """Same shape and error-resilience as main.run_scan(): one instrument
    failing (bad data, no setup) never takes down the rest of the scan."""
    results = []

    for instrument in instruments:
        try:
            df = add_indicators(get_ohlcv(instrument.symbol, period="1mo", interval="5m"))
            confirmation = add_indicators(get_ohlcv(instrument.symbol, period="6mo", interval="1d"))

            signal = generate_signal(
                instrument.symbol, df, confirmation, regime,
                fundamental_score_10=5, sector_score_10=5,
                sector_reason="Index derivative - fundamentals/sector not applicable",
                mode=mode,
            )

            if not signal:
                results.append({
                    "instrument": instrument, "signal": None, "lots": 0,
                    "allowed": False, "reason": "No valid setup", "order": None,
                })
                continue

            lots = risk_manager.lots_for_risk(signal.entry, signal.stop_loss, instrument.lot_size)
            allowed, reason, order = order_manager.submit(
                instrument, signal, lots, allow_after_hours=allow_after_hours
            )
            results.append({
                "instrument": instrument, "signal": signal, "lots": lots,
                "allowed": allowed, "reason": reason, "order": order,
            })

        except Exception as exc:
            results.append({
                "instrument": instrument, "signal": None, "lots": 0,
                "allowed": False, "reason": f"data/strategy error: {exc}", "order": None,
            })

    return results
