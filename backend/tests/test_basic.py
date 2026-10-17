"""
Basic test suite for BrandPulse Backend REST API.
"""
import io
import sys
import os
import pytest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    # Ensure no token for auth error testing
    os.environ["TWITTER_BEARER_TOKEN"] = ""
    return app.test_client()


def test_health_check(client):
    """Verify GET /health returns 200 with status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "BrandPulse API" in data["service"]


def test_analyze_sample(client):
    """Verify POST /api/analyze/sample returns complete analysis JSON payload."""
    resp = client.post("/api/analyze/sample", json={
        "brand": "Tesla",
        "count": 20,
        "threshold": 40.0
    })
    assert resp.status_code == 200
    data = resp.get_json()

    # Verify structured top-level keys
    assert "summary" in data
    assert "alert" in data
    assert "distribution" in data
    assert "daily_trend" in data
    assert "top_keywords" in data
    assert "wordclouds" in data
    assert "posts" in data
    assert "meta" in data

    # Verify summary fields
    assert data["summary"]["total_posts"] > 0
    assert "positive_pct" in data["summary"]
    assert "brand_health" in data["summary"]

    # Verify wordclouds are base64 images
    assert data["wordclouds"]["positive"].startswith("data:image/png;base64,")
    assert data["wordclouds"]["negative"].startswith("data:image/png;base64,")


def test_analyze_csv(client):
    """Verify POST /api/analyze/csv parses uploaded CSV and returns analysis."""
    csv_content = """date,text
2026-10-17,The delivery was super fast and the item works perfectly!
2026-10-17,Terrible experience. The box was completely empty.
2026-10-17,Neutral color and standard packaging.
"""
    file_bytes = io.BytesIO(csv_content.encode("utf-8"))

    resp = client.post(
        "/api/analyze/csv",
        data={
            "file": (file_bytes, "feedback.csv"),
            "brand": "GadgetCo",
            "threshold": "40.0"
        },
        content_type="multipart/form-data"
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["meta"]["brand"] == "GadgetCo"
    assert data["summary"]["total_posts"] == 3
    assert len(data["posts"]) == 3


def test_analyze_live_no_api_key_returns_friendly_json(client):
    """Verify POST /api/analyze/live with missing Bearer token returns 401 JSON without crashing."""
    resp = client.post("/api/analyze/live", json={
        "keyword": "Nike",
        "count": 20
    })
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data
    assert "user_hint" in data
    assert "Twitter Bearer Token is not configured" in data["error"]
