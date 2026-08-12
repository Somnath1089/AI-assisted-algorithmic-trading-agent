import pandas as pd
from strategies.signal_engine import generate_signal, classify

def _row(**overrides):
    base = dict(
        Open=99.0, Close=100.0, High=101.0, Low=98.0, Volume=1500,
        EMA20=98.0, SMA50=95.0, VWAP=99.0, RSI14=60.0, ATR14=2.0,
        VOLUME_RATIO=1.3, RESISTANCE=float("nan"), SUPPORT=float("nan"),
        BREAKOUT=True, BREAKDOWN=False,
    )
    base.update(overrides)
    return pd.DataFrame([base])

def test_classify_boundaries():
    assert classify(90) == "A+"
    assert classify(80) == "A"
    assert classify(70) == "B"
    assert classify(50) == "NO TRADE"

def test_long_rewarded_only_for_healthy_rsi_not_low_rsi():
    low_rsi_signal = generate_signal(
        "TEST.NS", _row(RSI14=25.0), None, regime="BULLISH",
        fundamental_score_10=8, sector_score_10=8, sector_reason="strong sector",
    )
    healthy_rsi_signal = generate_signal(
        "TEST.NS", _row(RSI14=60.0), None, regime="BULLISH",
        fundamental_score_10=8, sector_score_10=8, sector_reason="strong sector",
    )
    assert healthy_rsi_signal.score > low_rsi_signal.score

def test_opposed_regime_dampens_or_blocks_score():
    df = _row()
    aligned = generate_signal(
        "TEST.NS", df, None, regime="BULLISH",
        fundamental_score_10=8, sector_score_10=8, sector_reason="strong",
    )
    opposed = generate_signal(
        "TEST.NS", df, None, regime="BEARISH",
        fundamental_score_10=8, sector_score_10=8, sector_reason="strong",
    )
    assert aligned is not None
    assert opposed is None or opposed.score < aligned.score

def test_obstructed_target_blocks_long_setup():
    df = _row(RESISTANCE=100.5)
    signal = generate_signal(
        "TEST.NS", df, None, regime="BULLISH",
        fundamental_score_10=8, sector_score_10=8, sector_reason="strong",
    )
    assert signal is None or signal.side != "LONG"
