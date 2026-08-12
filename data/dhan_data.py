"""
Live market data via the official `dhanhq` SDK (DhanHQ v2 API).

The request contract here (endpoints, payload field names, response
envelope) was verified against the `dhanhq` package's own source on PyPI,
not guessed. The exact field names *inside* a successful response's `data`
payload (assumed here to be parallel `open`/`high`/`low`/`close`/`volume`
arrays, per DhanHQ's publicly documented historical-data schema) could not
be verified against a live call from this environment - outbound access to
*.dhan.co is blocked here the same way Yahoo Finance was. `_parse_candles`
therefore validates the expected keys explicitly and raises a clear error
naming the keys actually received if the schema doesn't match, instead of
silently mis-mapping data. Verify against a real response before trusting
this in production; adjust the key names in `_parse_candles` if needed.
"""
from datetime import datetime, timedelta

import pandas as pd

try:
    from dhanhq import dhanhq as DhanClient, DhanContext
except ImportError:
    DhanClient = None
    DhanContext = None

INTRADAY_INTERVALS = {1, 5, 15, 25, 60}

def get_dhan_client(client_id, access_token):
    if DhanClient is None:
        raise ImportError(
            "The 'dhanhq' package is required for Dhan integration. "
            "Install it with: pip install dhanhq"
        )
    return DhanClient(DhanContext(client_id, access_token))

def _parse_candles(data: dict) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(
            f"Unexpected Dhan historical-data response shape - missing {sorted(missing)}. "
            f"Keys actually received: {list(data.keys())}. Dhan's response schema may "
            f"differ from what this integration assumes; verify against a live response "
            f"and update data/dhan_data.py._parse_candles before trusting this data."
        )

    df = pd.DataFrame({
        "Open": data["open"],
        "High": data["high"],
        "Low": data["low"],
        "Close": data["close"],
        "Volume": data["volume"],
    })

    if "timestamp" in data:
        df.index = pd.to_datetime(data["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata")

    return df

def get_ohlcv_dhan(client_id, access_token, security_id, exchange_segment="NSE_EQ",
                    instrument_type="EQUITY", interval=5, days=5, daily=False):
    client = get_dhan_client(client_id, access_token)

    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if daily:
        response = client.historical_daily_data(
            security_id, exchange_segment, instrument_type, from_date, to_date
        )
    else:
        if interval not in INTRADAY_INTERVALS:
            raise ValueError(
                f"Dhan intraday interval must be one of {sorted(INTRADAY_INTERVALS)} minutes, got {interval}"
            )
        response = client.intraday_minute_data(
            security_id, exchange_segment, instrument_type, from_date, to_date, interval=interval
        )

    if response.get("status") != "success":
        raise ValueError(f"Dhan historical-data request failed: {response.get('remarks')}")

    df = _parse_candles(response["data"])
    if df.empty:
        raise ValueError(f"No market data returned for security_id={security_id}")

    return df
