"""CLI: render main.run_scan() into a standalone HTML dashboard.

    python -m dashboard.generate                  # live yfinance data
    python -m dashboard.generate --demo            # synthetic demo data
    python -m dashboard.generate --output out.html
"""
import argparse

from main import run_scan
from dashboard.render import render_dashboard

LIVE_DATA_NOTE = (
    "This run used live data providers configured in data/market_data.py. "
    "Nothing here is guaranteed to be current if the scan failed partway - "
    "check the console output for per-symbol errors."
)
DEMO_DATA_NOTE = (
    "Synthetic demo data. This run used fabricated OHLCV data (see "
    "dashboard/demo_data.py) to exercise the real signal engine, risk "
    "manager, and order manager end to end. Every score, pattern, and "
    "risk-gate decision was computed by the actual code - only the market "
    "prices feeding it are fake. Run without --demo against a live data "
    "provider for real signals."
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file path")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data instead of live data")
    parser.add_argument("--mode", default="INTRADAY", choices=["INTRADAY", "SWING"])
    args = parser.parse_args()

    if args.demo:
        from dashboard.demo_data import make_demo_provider
        get_ohlcv, get_stock_info = make_demo_provider()
        result = run_scan(mode=args.mode, get_ohlcv=get_ohlcv, get_stock_info=get_stock_info)
        note = DEMO_DATA_NOTE
    else:
        result = run_scan(mode=args.mode)
        note = LIVE_DATA_NOTE

    html = render_dashboard(result, data_note=note)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"Wrote {args.output} ({len(html):,} bytes)")
    print(f"Regime: {result['regime']} | Blocked: {result['blocked_reason']}")
    print(f"Signals: {len(result['orders'])}")

if __name__ == "__main__":
    main()
