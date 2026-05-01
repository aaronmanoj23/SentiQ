"""
Stock price data fetching and correlation with sentiment scores.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def get_stock_data(ticker: str, year: int) -> Optional[pd.DataFrame]:
    """Fetch full year stock price data."""
    try:
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end, interval="1mo")
        if df.empty:
            return None
        df = df[["Close", "Volume"]].reset_index()
        df.columns = ["Date", "Close", "Volume"]
        df["Month"] = df["Date"].dt.month
        return df
    except Exception:
        return None


def get_quarterly_returns(ticker: str, year: int) -> dict:
    """Get quarterly price returns for a ticker."""
    df = get_stock_data(ticker, year)
    if df is None:
        return {}
    
    results = {}
    q_months = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
    
    for q, months in q_months.items():
        q_data = df[df["Month"].isin(months)]
        if len(q_data) >= 2:
            start_price = q_data.iloc[0]["Close"]
            end_price = q_data.iloc[-1]["Close"]
            ret = ((end_price - start_price) / start_price) * 100
            results[q] = round(ret, 2)
    
    return results


def get_current_price(ticker: str) -> Optional[dict]:
    """Get current stock price and basic info."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5d")
        
        if hist.empty:
            return None
        
        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change_pct = ((current - prev) / prev) * 100
        
        return {
            "price": round(current, 2),
            "change_pct": round(change_pct, 2),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", None),
            "52w_high": info.get("fiftyTwoWeekHigh", None),
            "52w_low": info.get("fiftyTwoWeekLow", None),
        }
    except Exception:
        return None


def correlate_sentiment_price(sentiment_scores: list, price_returns: dict) -> dict:
    """
    Compute correlation between sentiment scores and price returns.
    sentiment_scores: list of (quarter, score) tuples where score is 0-1 positive sentiment
    price_returns: dict of {quarter: return_pct}
    """
    if not sentiment_scores or not price_returns:
        return {"correlation": None, "note": "Insufficient data"}
    
    paired = []
    for q, score in sentiment_scores:
        if q in price_returns:
            paired.append((score, price_returns[q]))
    
    if len(paired) < 2:
        return {"correlation": None, "note": "Need at least 2 quarters"}
    
    scores = [p[0] for p in paired]
    returns = [p[1] for p in paired]
    
    # Pearson correlation
    n = len(paired)
    mean_s = sum(scores) / n
    mean_r = sum(returns) / n
    
    num = sum((s - mean_s) * (r - mean_r) for s, r in paired)
    den_s = (sum((s - mean_s)**2 for s in scores)) ** 0.5
    den_r = (sum((r - mean_r)**2 for r in returns)) ** 0.5
    
    if den_s == 0 or den_r == 0:
        return {"correlation": 0.0, "note": "No variance"}
    
    corr = num / (den_s * den_r)
    
    interpretation = ""
    if abs(corr) < 0.2:
        interpretation = "Weak correlation"
    elif abs(corr) < 0.5:
        interpretation = "Moderate correlation"
    else:
        interpretation = "Strong correlation"
    
    direction = "positive" if corr > 0 else "negative"
    
    return {
        "correlation": round(corr, 3),
        "interpretation": f"{interpretation} ({direction})",
        "note": f"Sentiment predicts price direction {abs(corr)*100:.0f}% of variance"
    }
