from fundamentals.fundamental_filter import fundamental_score

def test_strong_fundamentals_score_high():
    info = {
        "revenueGrowth": 0.20, "earningsGrowth": 0.25,
        "debtToEquity": 30, "returnOnEquity": 0.22,
        "heldPercentInsiders": 0.6, "trailingPE": 25,
    }
    score, reasons = fundamental_score(info)
    assert score >= 8
    assert reasons

def test_weak_fundamentals_score_low():
    info = {
        "revenueGrowth": -0.05, "earningsGrowth": -0.10,
        "debtToEquity": 220, "returnOnEquity": 0.02,
        "heldPercentInsiders": 0.10, "trailingPE": 150,
    }
    score, reasons = fundamental_score(info)
    assert score <= 2

def test_missing_fundamentals_neutral():
    score, reasons = fundamental_score({})
    assert score == 5
    assert "unavailable" in reasons[0].lower()
