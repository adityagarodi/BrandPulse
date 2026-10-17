"""
Unit tests for VADER sentiment analysis and aggregate metrics in BrandPulse.
"""
import pytest
from services.sentiment import analyze_sentiment, compute_aggregate_metrics


def test_positive_sentiment():
    """Verify strongly positive text yields Positive sentiment and compound >= 0.05."""
    text = "Absolutely fantastic product! Exceeded all expectations, great quality!"
    result = analyze_sentiment(text)

    assert result["sentiment"] == "Positive"
    assert result["compound"] >= 0.05
    assert result["pos"] > 0


def test_negative_sentiment():
    """Verify strongly negative text yields Negative sentiment and compound <= -0.05."""
    text = "Horrible experience. Broken on arrival, complete waste of money and awful support."
    result = analyze_sentiment(text)

    assert result["sentiment"] == "Negative"
    assert result["compound"] <= -0.05
    assert result["neg"] > 0


def test_neutral_sentiment():
    """Verify factual/neutral text yields Neutral sentiment."""
    text = "The package arrived at 3:00 PM on Tuesday."
    result = analyze_sentiment(text)

    assert result["sentiment"] == "Neutral"
    assert -0.05 < result["compound"] < 0.05


def test_aggregate_metrics_calculation():
    """Verify correct percentage calculation, brand health classification, and alert triggering."""
    posts = [
        {"sentiment": "Positive", "compound": 0.8},
        {"sentiment": "Positive", "compound": 0.6},
        {"sentiment": "Neutral", "compound": 0.0},
        {"sentiment": "Negative", "compound": -0.7},
    ]

    metrics = compute_aggregate_metrics(posts, alert_threshold=40.0)

    assert metrics["total_posts"] == 4
    assert metrics["positive_count"] == 2
    assert metrics["neutral_count"] == 1
    assert metrics["negative_count"] == 1
    assert metrics["positive_pct"] == 50.0
    assert metrics["neutral_pct"] == 25.0
    assert metrics["negative_pct"] == 25.0
    assert metrics["brand_health"] == "Warning"  # 25% is in Warning range (20-35%)
    assert metrics["alert_triggered"] is False   # 25% < 40% threshold


def test_alert_triggered_when_exceeding_threshold():
    """Verify alert triggers when negative sentiment exceeds configured threshold."""
    posts = [
        {"sentiment": "Negative", "compound": -0.8},
        {"sentiment": "Negative", "compound": -0.6},
        {"sentiment": "Negative", "compound": -0.5},
        {"sentiment": "Positive", "compound": 0.5},
    ]

    # Negative is 75%, threshold is 40%
    metrics = compute_aggregate_metrics(posts, alert_threshold=40.0)

    assert metrics["negative_pct"] == 75.0
    assert metrics["brand_health"] == "Critical"
    assert metrics["alert_triggered"] is True
