"""
Sentiment Analysis Service for BrandPulse Backend.
Computes VADER polarity scores, classifications, aggregate metrics,
brand health determination, and chronological trend series.
"""
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyzes sentiment of text using VADER lexicon."""
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
    """Computes summary metrics, brand health classification, and alert triggers."""
    total = len(analyzed_posts)
    if total == 0:
        return {
            "summary": {
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
                "health_description": "No data available.",
            },
            "alert": {
                "alert_triggered": False,
                "alert_threshold": alert_threshold,
                "alert_message": "No posts analyzed.",
            },
            "distribution": {
                "labels": ["Positive", "Neutral", "Negative"],
                "counts": [0, 0, 0],
                "percentages": [0.0, 0.0, 0.0]
            }
        }

    pos_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Positive")
    neu_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Neutral")
    neg_count = sum(1 for p in analyzed_posts if p.get("sentiment") == "Negative")

    pos_pct = round((pos_count / total) * 100, 1)
    neu_pct = round((neu_count / total) * 100, 1)
    neg_pct = round((neg_count / total) * 100, 1)

    total_compound = sum(p.get("compound_score", p.get("compound", 0.0)) for p in analyzed_posts)
    avg_compound = round(total_compound / total, 4)

    # Health classification
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
        health_description = "High volume of customer dissatisfaction. Immediate response advised."

    alert_triggered = bool(neg_pct >= alert_threshold)
    alert_message = (
        f"Critical Alert: Negative sentiment ({neg_pct}%) exceeds threshold of {alert_threshold}%!"
        if alert_triggered else
        f"Sentiment is within normal boundaries ({neg_pct}% negative vs {alert_threshold}% threshold)."
    )

    return {
        "summary": {
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
        },
        "alert": {
            "alert_triggered": alert_triggered,
            "alert_threshold": alert_threshold,
            "alert_message": alert_message,
        },
        "distribution": {
            "labels": ["Positive", "Neutral", "Negative"],
            "counts": [pos_count, neu_count, neg_count],
            "percentages": [pos_pct, neu_pct, neg_pct]
        }
    }


def compute_time_series_trend(analyzed_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Groups posts chronologically and computes daily counts and average compound scores."""
    if not analyzed_posts:
        return {
            "dates": [],
            "positive": [],
            "neutral": [],
            "negative": [],
            "avg_compound": [],
        }

    rows = []
    now_str = datetime.utcnow().strftime("%b %d")

    for p in analyzed_posts:
        dt_val = p.get("date") or p.get("created_at") or p.get("post_date")
        date_label = now_str
        if dt_val:
            try:
                dt_obj = pd.to_datetime(dt_val)
                date_label = dt_obj.strftime("%b %d")
            except Exception:
                date_label = now_str

        rows.append({
            "date": date_label,
            "sentiment": p.get("sentiment", "Neutral"),
            "compound": p.get("compound_score", p.get("compound", 0.0)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {
            "dates": [],
            "positive": [],
            "neutral": [],
            "negative": [],
            "avg_compound": [],
        }

    grouped = df.groupby("date", sort=False)

    dates = []
    pos_series = []
    neu_series = []
    neg_series = []
    compound_series = []

    for date_key, group in grouped:
        dates.append(str(date_key))
        pos_series.append(int((group["sentiment"] == "Positive").sum()))
        neu_series.append(int((group["sentiment"] == "Neutral").sum()))
        neg_series.append(int((group["sentiment"] == "Negative").sum()))
        compound_series.append(round(float(group["compound"].mean()), 3))

    return {
        "dates": dates,
        "positive": pos_series,
        "neutral": neu_series,
        "negative": neg_series,
        "avg_compound": compound_series,
    }
