def market_regime(df) -> str:
    last = df.iloc[-1]

    norm_atr = df["ATR14"] / df["Close"]
    if len(norm_atr) >= 21:
        recent_mean = norm_atr.iloc[-21:-1].mean()
        if recent_mean > 0 and norm_atr.iloc[-1] > 1.5 * recent_mean:
            return "HIGH VOLATILITY"

    if last["Close"] > last["EMA20"] > last["SMA50"]:
        return "BULLISH"
    if last["Close"] < last["EMA20"] < last["SMA50"]:
        return "BEARISH"

    if last["VOLUME_RATIO"] < 0.8:
        return "UNCERTAIN"

    return "SIDEWAYS"
