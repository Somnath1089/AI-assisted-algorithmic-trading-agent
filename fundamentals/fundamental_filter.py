def fundamental_score(info: dict) -> tuple[int, list[str]]:
    score = 5
    reasons = []

    revenue_growth = info.get("revenueGrowth")
    if revenue_growth is not None:
        if revenue_growth >= 0.10:
            score += 1; reasons.append("Strong revenue growth")
        elif revenue_growth < 0:
            score -= 1; reasons.append("Declining revenue")

    earnings_growth = info.get("earningsGrowth")
    if earnings_growth is not None:
        if earnings_growth >= 0.10:
            score += 1; reasons.append("Strong profit growth")
        elif earnings_growth < 0:
            score -= 1; reasons.append("Declining profit")

    debt_to_equity = info.get("debtToEquity")
    if debt_to_equity is not None:
        if debt_to_equity < 50:
            score += 1; reasons.append("Low debt")
        elif debt_to_equity > 150:
            score -= 1; reasons.append("High debt load")

    roe = info.get("returnOnEquity")
    if roe is not None:
        if roe >= 0.15:
            score += 1; reasons.append("Healthy ROE")
        elif roe < 0.05:
            score -= 1; reasons.append("Weak ROE")

    promoter_holding = info.get("heldPercentInsiders")
    if promoter_holding is not None:
        if promoter_holding >= 0.5:
            score += 1; reasons.append("High promoter holding")
        elif promoter_holding < 0.2:
            score -= 1; reasons.append("Low promoter holding")

    pe = info.get("trailingPE")
    if pe is not None:
        if pe <= 0 or pe > 100:
            score -= 1; reasons.append("Valuation sanity check failed")
        elif pe <= 40:
            score += 1; reasons.append("Reasonable valuation")

    if not reasons:
        reasons.append("Fundamental data unavailable - neutral score applied")

    score = max(0, min(10, score))
    return score, reasons
