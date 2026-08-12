import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()

    x["EMA20"] = x["Close"].ewm(span=20, adjust=False).mean()
    x["SMA50"] = x["Close"].rolling(50).mean()

    typical = (x["High"] + x["Low"] + x["Close"]) / 3
    vol = x["Volume"].replace(0, np.nan)
    x["VWAP"] = (typical * vol).cumsum() / vol.cumsum()

    delta = x["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))

    tr = pd.concat([
        x["High"] - x["Low"],
        (x["High"] - x["Close"].shift()).abs(),
        (x["Low"] - x["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    x["ATR14"] = tr.ewm(alpha=1/14, adjust=False).mean()

    x["AVG_VOLUME20"] = x["Volume"].rolling(20).mean()
    x["VOLUME_RATIO"] = x["Volume"] / x["AVG_VOLUME20"]

    return x.dropna()
