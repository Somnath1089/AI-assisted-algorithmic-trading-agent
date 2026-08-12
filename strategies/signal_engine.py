from dataclasses import dataclass
import pandas as pd

W_TREND = 20
W_PRICE_ACTION = 15
W_VOLUME = 15
W_REGIME = 15
W_SECTOR = 10
W_VWAP = 5
W_RSI = 5
W_FUNDAMENTALS = 10
W_RISK_REWARD = 5

@dataclass
class Signal:
    symbol: str
    side: str
    score: int
    grade: str
    entry: float
    stop_loss: float
    target1: float
    target2: float
    risk_reward: float
    reasons: list[str]
    market_context: str
    sector_context: str
    invalidation: str

def classify(score):
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    return "NO TRADE"

def _trend_score(last, side, higher_tf_aligned):
    reasons = []
    score = 0
    if side == "LONG":
        if last["Close"] > last["EMA20"] > last["SMA50"]:
            score += 15; reasons.append("Price above EMA20 above SMA50 (uptrend structure)")
        elif last["Close"] > last["EMA20"]:
            score += 8; reasons.append("Price above EMA20")
    else:
        if last["Close"] < last["EMA20"] < last["SMA50"]:
            score += 15; reasons.append("Price below EMA20 below SMA50 (downtrend structure)")
        elif last["Close"] < last["EMA20"]:
            score += 8; reasons.append("Price below EMA20")
    if higher_tf_aligned:
        score += 5; reasons.append("Higher-timeframe trend aligned")
    return min(score, W_TREND), reasons

def _price_action_score(last, side):
    bullish_candle = last["Close"] > last["Open"]
    bearish_candle = last["Close"] < last["Open"]
    if side == "LONG":
        if bool(last.get("BREAKOUT", False)) and bullish_candle:
            return 15, ["Confirmed breakout with bullish candle close"]
        if bullish_candle and last["Close"] > last["EMA20"]:
            return 8, ["Bullish price action above EMA20"]
    else:
        if bool(last.get("BREAKDOWN", False)) and bearish_candle:
            return 15, ["Confirmed breakdown with bearish candle close"]
        if bearish_candle and last["Close"] < last["EMA20"]:
            return 8, ["Bearish price action below EMA20"]
    return 0, []

def _volume_score(last):
    ratio = last["VOLUME_RATIO"]
    if ratio >= 1.5:
        return 15, ["Strong volume confirmation"]
    if ratio >= 1.2:
        return 10, ["Volume confirmation"]
    if ratio >= 1.0:
        return 5, ["Average volume"]
    return 0, []

def _regime_score(regime, side):
    if (regime == "BULLISH" and side == "LONG") or (regime == "BEARISH" and side == "SHORT"):
        return 15, False, [f"{regime} market regime supports {side}"]
    if regime == "SIDEWAYS":
        return 7, False, ["Sideways regime - reduced conviction"]
    return 0, True, [f"{regime} regime opposes {side} - counter-trend caution"]

def _sector_score(sector_score_10, sector_reason):
    score = max(0, min(10, sector_score_10))
    reasons = [sector_reason] if score >= 7 else []
    return score, reasons

def _vwap_score(last, side):
    if side == "LONG" and last["Close"] > last["VWAP"]:
        return 5, ["Above VWAP"]
    if side == "SHORT" and last["Close"] < last["VWAP"]:
        return 5, ["Below VWAP"]
    return 0, []

def _rsi_score(last, side):
    rsi = last["RSI14"]
    if side == "LONG" and 50 <= rsi <= 70:
        return 5, ["Healthy RSI for long"]
    if side == "SHORT" and rsi < 50:
        return 5, ["Bearish RSI for short"]
    return 0, []

def _fundamentals_score(fundamental_score_10):
    score = max(0, min(10, fundamental_score_10))
    if score >= 7:
        return score, ["Fundamentals support the setup"]
    if score <= 3:
        return score, ["Fundamental weakness penalty applied"]
    return score, []

def _risk_reward_ok(last, side, target1):
    if side == "LONG":
        resistance = last.get("RESISTANCE", float("nan"))
        if pd.notna(resistance) and resistance > last["Close"] and resistance < target1:
            return False
    else:
        support = last.get("SUPPORT", float("nan"))
        if pd.notna(support) and support < last["Close"] and support > target1:
            return False
    return True

def generate_signal(symbol, df, higher_tf_df, regime,
                     fundamental_score_10, sector_score_10, sector_reason,
                     mode="INTRADAY", min_score=65):
    last = df.iloc[-1]
    candidates = []

    higher_aligned_long = False
    higher_aligned_short = False
    if higher_tf_df is not None and len(higher_tf_df) > 0:
        h_last = higher_tf_df.iloc[-1]
        higher_aligned_long = h_last["Close"] > h_last["EMA20"]
        higher_aligned_short = h_last["Close"] < h_last["EMA20"]

    for side, higher_aligned in (("LONG", higher_aligned_long), ("SHORT", higher_aligned_short)):
        entry = float(last["Close"])
        atr = float(last["ATR14"])
        if atr <= 0:
            continue

        if side == "LONG":
            stop = entry - 1.5 * atr
            risk = entry - stop
            target1 = entry + 1.5 * risk
            target2 = entry + 2.0 * risk
            ref_level = last.get("RESISTANCE", float("nan"))
        else:
            stop = entry + 1.5 * atr
            risk = stop - entry
            target1 = entry - 1.5 * risk
            target2 = entry - 2.0 * risk
            ref_level = last.get("SUPPORT", float("nan"))

        if risk <= 0:
            continue

        if pd.notna(ref_level) and abs(entry - ref_level) > 1.5 * atr:
            continue

        if not _risk_reward_ok(last, side, target1):
            continue

        reasons = []
        total = 0

        s, r = _trend_score(last, side, higher_aligned); total += s; reasons += r
        s, r = _price_action_score(last, side); total += s; reasons += r
        s, r = _volume_score(last); total += s; reasons += r
        s, dampen, r = _regime_score(regime, side); total += s; reasons += r
        s, r = _sector_score(sector_score_10, sector_reason); total += s; reasons += r
        s, r = _vwap_score(last, side); total += s; reasons += r
        s, r = _rsi_score(last, side); total += s; reasons += r
        s, r = _fundamentals_score(fundamental_score_10); total += s; reasons += r
        total += W_RISK_REWARD
        reasons.append("Target 1 achievable at 1.5R without structural obstruction")

        if dampen:
            total *= 0.5

        score = int(round(max(0, min(100, total))))
        grade = classify(score)
        if grade == "NO TRADE" or score < min_score:
            continue

        invalidation = (
            "Close back below EMA20/VWAP invalidates the long setup"
            if side == "LONG" else
            "Close back above EMA20/VWAP invalidates the short setup"
        )

        candidates.append(Signal(
            symbol=symbol, side=side, score=score, grade=grade,
            entry=entry, stop_loss=stop, target1=target1, target2=target2,
            risk_reward=1.5, reasons=reasons,
            market_context=regime, sector_context=sector_reason,
            invalidation=invalidation,
        ))

    if not candidates:
        return None

    return max(candidates, key=lambda s: s.score)
