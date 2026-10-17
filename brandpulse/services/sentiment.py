"""
Sentiment Analysis Service using VADER (Valence Aware Dictionary and sEntiment Reasoner).
Computes individual post sentiment scores (pos, neu, neg, compound), classifications,
and aggregate brand monitoring metrics including brand health and alert status.
"""
from typing import List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyzes sentiment of a single text string using VADER.
    
    Standard VADER classification thresholds:
    - Positive: compound score >= 0.05
    - Negative: compound score <= -0.05
    - Neutral: -0.05 < compound score < 0.05
    
    Returns:
        dict: {
            'compound': float,
            'pos': float,
            'neu': float,
            'neg': float,
            'sentiment': 'Positive' | 'Neutral' | 'Negative'
        }
    """
    if not text or not isinstance(text, str):
        return {
            "compound": 0.0,
            "pos": 0.0,
            "neu": 1.0,
            "neg": 0.0,
            "sentiment": "Neutral",
        }

    scores = analyzer.polarity_scores(text)
    compound = round(scores["compound"], 4)
    pos = round(scores["pos"], 4)
    neu = round(scores["neu"], 4)
    neg = round(scores["neg"], 4)

    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return {
        "compound": compound,
        "pos": pos,
        "neu": neu,
        "neg": neg,
        "sentiment": sentiment,
    }


def compute_aggregate_metrics(
    analyzed_posts: List[Dict[str, Any]],
    alert_threshold: float = 40.0
) -> Dict[str, Any]:
    """
    Computes overall summary metrics across a collection of analyzed posts.
    
    Metrics:
    - total_posts: Total count
    - positive_count, neutral_count, negative_count
    - positive_pct, neutral_pct, negative_pct
    - avg_compound: Mean compound sentiment score (-1 to 1)
    - brand_health: 'Healthy' | 'Warning' | 'Critical'
    - alert_triggered: bool (True if negative_pct >= alert_threshold)
    - alert_threshold: float
    """
    total = len(analyzed_posts)
    if total == 0:
        return {
            "total_posts": 0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "positive_pct": 0.0,
            "neutral_pct": 0.0,
            "negative_pct": 0.0,
            "avg_compound": 0.0,
            "brand_health": "Unknown",
            "health_badge_class": "secondary",
            "alert_triggered": False,
            "alert_threshold": alert_threshold,
        }

    pos_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Positive")
    neu_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Neutral")
    neg_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Negative")

    pos_pct = round((pos_count / total) * 100, 1)
    neu_pct = round((neu_count / total) * 100, 1)
    neg_pct = round((neg_count / total) * 100, 1)

    total_compound = sum(p.get("compound", 0.0) for p in analyzed_posts)
    avg_compound = round(total_compound / total, 4)

    # Determine Brand Health based on negative sentiment percentage
    # Healthy: < 20% negative sentiment
    # Warning: 20% - 35% negative sentiment
    # Critical: > 35% negative sentiment
    if neg_pct < 20.0:
        brand_health = "Healthy"
        health_badge_class = "success"
        health_description = "Brand sentiment is overwhelmingly favorable and positive."
    elif 20.0 <= neg_pct <= 35.0:
        brand_health = "Warning"
        health_badge_class = "warning"
        health_description = "Moderate negative feedback detected. Monitor customer issues."
    else:
        brand_health = "Critical"
        health_badge_class = "danger"
        health_description = "High volume of customer dissatisfaction. Immediate PR/support response advised."

    alert_triggered = neg_pct >= alert_threshold

    return {
        "total_posts": total,
        "positive_count": pos_count,
        "neutral_count": neu_count,
        "negative_count": neg_count,
        "positive_pct": pos_pct,
        "neutral_pct": neu_pct,
        "negative_pct": neg_pct,
        "avg_compound": avg_compound,
        "brand_health": brand_health,
        "health_badge_class": health_badge_class,
        "health_description": health_description,
        "alert_triggered": alert_triggered,
        "alert_threshold": alert_threshold,
    }


def compute_time_series_trend(analyzed_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Groups posts chronologically by date or timestamp and computes:
    - dates: list of sorted date strings
    - positive_series: count per date
    - neutral_series: count per date
    - negative_series: count per date
    - avg_compound_series: average compound score per date
    """
    if not analyzed_posts:
        return {
            "dates": [],
            "positive_series": [],
            "neutral_series": [],
            "negative_series": [],
            "avg_compound_series": [],
        }

    # Normalize dates into 'YYYY-MM-DD' or 'YYYY-MM-DD HH:00'
    rows = []
    now_str = datetime.utcnow().strftime("%Y-%m-%d")

    for p in analyzed_posts:
        dt_val = p.get("created_at") or p.get("post_date") or p.get("date")
        date_label = now_str
        if dt_val:
            try:
                if isinstance(dt_val, str):
                    # Try parsing common formats
                    dt_obj = pd.to_datetime(dt_val)
                    date_label = dt_obj.strftime("%b %d")
                elif isinstance(dt_val, (datetime, pd.Timestamp)):
                    date_label = dt_val.strftime("%b %d")
            except Exception:
                date_label = now_str

        rows.append({
            "date": date_label,
            "sentiment": p.get("sentiment", "Neutral"),
            "compound": p.get("compound", 0.0),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {
            "dates": [],
            "positive_series": [],
            "neutral_series": [],
            "negative_series": [],
            "avg_compound_series": [],
        }

    # Group by date maintaining chronological order
    grouped = df.groupby("date", sort=False)

    dates = []
    positive_series = []
    neutral_series = []
    negative_series = []
    avg_compound_series = []

    for date_key, group in grouped:
        dates.append(str(date_key))
        positive_series.append(int((group["sentiment"] == "Positive").sum()))
        neutral_series.append(int((group["sentiment"] == "Neutral").sum()))
        negative_series.append(int((group["sentiment"] == "Negative").sum()))
        avg_compound_series.append(round(float(group["compound"].mean()), 3))

    return {
        "dates": dates,
        "positive_series": positive_series,
        "neutral_series": neutral_series,
        "negative_series": negative_series,
        "avg_compound_series": avg_compound_series,
    }
