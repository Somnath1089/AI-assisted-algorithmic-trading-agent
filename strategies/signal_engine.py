from dataclasses import dataclass

@dataclass
class Signal:
    symbol: str
    side: str
    score: int
    entry: float
    stop_loss: float
    target1: float
    target2: float
    risk_reward: float
    reasons: list[str]

def score_long(last, regime):
    score = 0
    reasons = []

    if last["Close"] > last["EMA20"]:
        score += 10; reasons.append("Price above EMA20")
    if last["EMA20"] > last["SMA50"]:
        score += 10; reasons.append("EMA20 above SMA50")
    if last["Close"] > last["VWAP"]:
        score += 5; reasons.append("Above VWAP")
    if 50 <= last["RSI14"] <= 70:
        score += 5; reasons.append("Healthy RSI")
    if last["VOLUME_RATIO"] >= 1.2:
        score += 15; reasons.append("Volume confirmation")
    if regime == "BULLISH":
        score += 15; reasons.append("Bullish market regime")
    elif regime == "SIDEWAYS":
        score += 5; reasons.append("Sideways regime")

    return score, reasons

def score_short(last, regime):
    score = 0
    reasons = []

    if last["Close"] < last["EMA20"]:
        score += 10; reasons.append("Price below EMA20")
    if last["EMA20"] < last["SMA50"]:
        score += 10; reasons.append("EMA20 below SMA50")
    if last["Close"] < last["VWAP"]:
        score += 5; reasons.append("Below VWAP")
    if last["RSI14"] < 50:
        score += 5; reasons.append("Bearish RSI")
    if last["VOLUME_RATIO"] >= 1.2:
        score += 15; reasons.append("Selling-volume confirmation")
    if regime == "BEARISH":
        score += 15; reasons.append("Bearish market regime")
    elif regime == "SIDEWAYS":
        score += 5; reasons.append("Sideways regime")

    return score, reasons

def generate_signal(symbol, df, regime, min_score=75):
    last = df.iloc[-1]
    candidates = []

    long_score, long_reasons = score_long(last, regime)
    if long_score >= min_score:
        entry = float(last["Close"])
        sl = entry - 1.5 * float(last["ATR14"])
        risk = entry - sl
        t1 = entry + 1.5 * risk
        t2 = entry + 2.0 * risk
        candidates.append(Signal(
            symbol, "LONG", long_score, entry, sl, t1, t2, 1.5, long_reasons
        ))

    short_score, short_reasons = score_short(last, regime)
    if short_score >= min_score:
        entry = float(last["Close"])
        sl = entry + 1.5 * float(last["ATR14"])
        risk = sl - entry
        t1 = entry - 1.5 * risk
        t2 = entry - 2.0 * risk
        candidates.append(Signal(
            symbol, "SHORT", short_score, entry, sl, t1, t2, 1.5, short_reasons
        ))

    if not candidates:
        return None

    return max(candidates, key=lambda s: s.score)
