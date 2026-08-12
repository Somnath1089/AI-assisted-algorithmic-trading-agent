SECTOR_INDEX = {
    "RELIANCE.NS": "^CNXENERGY",
    "HDFCBANK.NS": "^NSEBANK",
    "ICICIBANK.NS": "^NSEBANK",
    "SBIN.NS": "^NSEBANK",
    "AXISBANK.NS": "^NSEBANK",
    "INFY.NS": "^CNXIT",
    "TCS.NS": "^CNXIT",
    "ITC.NS": "^CNXFMCG",
    "LT.NS": "^CNXINFRA",
    "BHARTIARTL.NS": "^NSEI",
}

def sector_strength_score(stock_df, sector_df, lookback: int = 6) -> tuple[int, str]:
    if sector_df is None or len(sector_df) < lookback or len(stock_df) < lookback:
        return 5, "Sector data unavailable - neutral score applied"

    stock_return = stock_df["Close"].iloc[-1] / stock_df["Close"].iloc[-lookback] - 1
    sector_return = sector_df["Close"].iloc[-1] / sector_df["Close"].iloc[-lookback] - 1
    relative = stock_return - sector_return

    if relative > 0.02:
        return 9, "Stock outperforming its sector"
    if relative > 0.0:
        return 7, "Stock slightly outperforming its sector"
    if relative > -0.02:
        return 4, "Stock in line with its sector"
    return 2, "Stock underperforming its sector"
