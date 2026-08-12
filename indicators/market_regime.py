def market_regime(df) -> str:
    last = df.iloc[-1]

    if last["Close"] > last["EMA20"] > last["SMA50"]:
        return "BULLISH"
    if last["Close"] < last["EMA20"] < last["SMA50"]:
        return "BEARISH"

    # Simple uncertainty guard
    if last["VOLUME_RATIO"] < 0.8:
        return "UNCERTAIN"

    return "SIDEWAYS"
