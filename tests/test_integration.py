"""
End-to-end integration tests for BrandPulse Flask Application.
Tests analysis execution, dashboard rendering, history storage, brand comparison, and export endpoints.
"""
import pytest
from app import create_app
from models import db, SearchHistory, AnalyzedPost


@pytest.fixture
def app():
    """Create test application configured with an in-memory SQLite database."""
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()


def test_home_page_loads(client):
    """Verify home page loads successfully with 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"BrandPulse" in response.data
    assert b"Monitor Social Media Sentiment" in response.data


def test_sample_analysis_flow(client):
    """Test full analysis flow using built-in sample data."""
    # 1. Post to /analyze
    response = client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Apple",
        "brand_name": "Apple",
        "count": "20",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Apple" in response.data
    assert b"VADER Split" in response.data
    assert b"Analyzed Social Posts" in response.data
    assert b"Positive Sentiment Word Cloud" in response.data


def test_history_and_comparison_flow(client):
    """Test recording to history and comparing two brands."""
    # Run Brand 1 (Apple)
    client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Apple",
        "brand_name": "Apple",
        "count": "15",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    # Run Brand 2 (Tesla)
    client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Tesla",
        "brand_name": "Tesla",
        "count": "15",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    # Verify history page
    hist_resp = client.get("/history")
    assert hist_resp.status_code == 200
    assert b"Apple" in hist_resp.data
    assert b"Tesla" in hist_resp.data

    # Verify comparison page
    comp_resp = client.get("/compare?brand1=1&brand2=2")
    assert comp_resp.status_code == 200
    assert b"Comparative Verdict" in comp_resp.data
    assert b"Side-by-Side Metric Benchmark" in comp_resp.data


def test_csv_and_pdf_export_flow(client):
    """Verify CSV and PDF export endpoints return valid attachment streams."""
    # Seed one search
    client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Nike",
        "brand_name": "Nike",
        "count": "10",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    # CSV export
    csv_resp = client.get("/export/1/csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.content_type
    assert b"Post ID,Date,Brand,Sentiment" in csv_resp.data

    # PDF export
    pdf_resp = client.get("/export/1/pdf")
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.content_type
    assert len(pdf_resp.data) > 1000
    assert pdf_resp.data.startswith(b"%PDF")
