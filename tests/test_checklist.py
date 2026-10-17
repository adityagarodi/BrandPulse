"""
Test Checklist Verification Suite for BrandPulse.
Verifies all 7 checklist requirements specified by the user:
1. Home page loads without errors
2. Sample data analysis opens the dashboard
3. Cards show numbers, donut chart, trend line, keyword bars, and both word clouds appear
4. Table search and filter work
5. CSV download works
6. Uploading custom CSV works
7. Live fetch with no API key shows a friendly message instead of crashing
"""
import io
import pytest
from app import create_app
from models import db, SearchHistory, AnalyzedPost


@pytest.fixture
def app():
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "TWITTER_BEARER_TOKEN": "",  # Ensure empty API key for testing error message
    })

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_1_home_page_loads_without_errors(client):
    """Checklist item 1: Home page loads without errors."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"BrandPulse" in response.data
    assert b"Monitor Social Media Sentiment" in response.data
    assert b"Built-in Sample Data" in response.data
    assert b"Live Twitter API v2" in response.data
    assert b"Upload CSV Dataset" in response.data


def test_2_and_3_sample_data_dashboard_and_visualizations(client):
    """
    Checklist item 2: Sample data analysis opens the dashboard.
    Checklist item 3: Cards show numbers, donut chart, trend line, keyword bars, and both word clouds appear.
    """
    # Run sample analysis for Apple
    post_resp = client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Apple",
        "brand_name": "Apple",
        "count": "30",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    assert post_resp.status_code == 200
    html = post_resp.data.decode("utf-8")

    # Verify Dashboard loaded
    assert "BrandPulse — Dashboard for Apple" in html
    assert "Apple" in html

    # Verify Cards show numbers
    assert "Total Posts" in html
    assert "Positive Sentiment" in html
    assert "Neutral Sentiment" in html
    assert "Negative Sentiment" in html
    assert "Avg Compound Score" in html
    assert "Brand Health" in html

    # Verify charts canvases exist
    assert 'id="sentimentDonutChart"' in html
    assert 'id="sentimentTrendChart"' in html
    assert 'id="topKeywordsChart"' in html

    # Verify both word clouds appear as base64 PNG data URIs
    assert "Positive Sentiment Word Cloud" in html
    assert "Negative Sentiment Word Cloud" in html
    assert 'alt="Positive Word Cloud" class="wordcloud-img' in html
    assert 'alt="Negative Word Cloud" class="wordcloud-img' in html
    assert "data:image/png;base64," in html


def test_4_table_search_and_filter_elements(client):
    """Checklist item 4: Table search and filter structure and data attributes exist."""
    # Seed data
    post_resp = client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Tesla",
        "brand_name": "Tesla",
        "count": "20",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    html = post_resp.data.decode("utf-8")

    # Filter buttons exist
    assert 'data-filter="all"' in html
    assert 'data-filter="positive"' in html
    assert 'data-filter="neutral"' in html
    assert 'data-filter="negative"' in html

    # Search input exists
    assert 'id="postSearchInput"' in html

    # Table contains post rows with sentiment attributes
    assert 'id="postsTableBody"' in html
    assert 'class="post-row"' in html
    assert 'data-sentiment="positive"' in html or 'data-sentiment="negative"' in html


def test_5_csv_download_works(client):
    """Checklist item 5: CSV download works."""
    # Seed data
    client.post("/analyze", data={
        "source_mode": "sample",
        "sample_brand": "Nike",
        "brand_name": "Nike",
        "count": "15",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    # Download CSV
    csv_resp = client.get("/export/1/csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.content_type
    content = csv_resp.data.decode("utf-8-sig")

    # Verify CSV headers & content
    assert "Post ID,Date,Brand,Sentiment,Compound Score" in content
    assert "Nike" in content


def test_6_uploading_custom_csv_works(client):
    """Checklist item 6: Uploading your own CSV works."""
    # Create an in-memory custom CSV
    custom_csv_content = """date,text
2026-10-17,The customer support on this brand is absolutely wonderful and fast!
2026-10-17,Product arrived damaged and broke immediately. Total waste of money.
2026-10-17,Average packaging. The color is slightly different than shown online.
"""
    file_bytes = io.BytesIO(custom_csv_content.encode("utf-8"))

    upload_resp = client.post("/analyze", data={
        "source_mode": "csv",
        "csv_file": (file_bytes, "my_custom_reviews.csv"),
        "brand_name": "Acme Brand",
        "count": "50",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    assert upload_resp.status_code == 200
    html = upload_resp.data.decode("utf-8")

    # Verify custom brand dashboard opened
    assert "BrandPulse — Dashboard for Acme Brand" in html
    assert "Acme Brand" in html
    assert "CSV (my_custom_reviews.csv)" in html
    assert "Total Posts" in html
    assert "data:image/png;base64," in html


def test_7_live_fetch_no_api_key_friendly_message(client):
    """Checklist item 7: Live fetch with no API key shows a friendly message instead of crashing."""
    # Submit a live Twitter fetch without API key
    resp = client.post("/analyze", data={
        "source_mode": "twitter",
        "brand_name": "Microsoft",
        "count": "20",
        "alert_threshold": "40.0"
    }, follow_redirects=True)

    # Must NOT crash (status code 200 after redirect)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Verify friendly warning flash message appears
    assert "Twitter Authentication Error" in html or "Twitter Bearer Token is not configured" in html or "Sample Data (Auth Fallback)" in html
    # Verify fallback executed seamlessly so user still sees the dashboard or search
    assert "Microsoft" in html
