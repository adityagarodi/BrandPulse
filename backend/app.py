"""
BrandPulse — Flask JSON API Backend (Split Deployment).
Pure REST API service designed for hosting on Render with CORS support for Vercel.
"""
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import modular services
from services.preprocessing import (
    ensure_nltk_resources,
    preprocess_tweet,
    extract_top_keywords,
    deep_clean_text
)
from services.sentiment import (
    analyze_sentiment,
    compute_aggregate_metrics,
    compute_time_series_trend
)
from services.charts import generate_wordcloud_base64
from services.twitter_service import (
    fetch_tweets_from_api,
    load_sample_tweets,
    load_csv_tweets,
    TwitterServiceError,
    TwitterAuthError,
    TwitterRateLimitError,
    TwitterForbiddenError
)

# Download NLTK data into ./nltk_data at startup
ensure_nltk_resources()


def create_app() -> Flask:
    """Application factory for BrandPulse JSON API."""
    app = Flask(__name__)

    # Configure CORS
    frontend_env = os.getenv("FRONTEND_URL", "").strip()
    allowed_origins = [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "http://localhost:3000",
    ]

    if frontend_env:
        for url in frontend_env.split(","):
            url = url.strip()
            if url and url not in allowed_origins:
                allowed_origins.append(url)

    # If wildcard is requested, enable all origins
    if "*" in allowed_origins or frontend_env == "*":
        CORS(app, resources={r"/*": {"origins": "*"}})
    else:
        CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

    # --------------------------------------------------------------------------
    # Pipeline Helper: Transforms raw posts into unified analysis payload
    # --------------------------------------------------------------------------
    def run_analysis_pipeline(
        raw_posts: List[Dict[str, Any]],
        brand_name: str,
        source_label: str,
        alert_threshold: float = 40.0
    ) -> Dict[str, Any]:
        """Runs NLTK cleaning, VADER scoring, wordcloud generation, and structures output."""
        analyzed_posts = []
        cleaned_tokens_all = []
        positive_cleaned_texts = []
        negative_cleaned_texts = []

        for p in raw_posts:
            raw_text = p.get("text", "")
            prep = preprocess_tweet(raw_text)
            sent = analyze_sentiment(prep["vader_ready_text"])

            post_record = {
                "id": str(p.get("id", "")),
                "text": raw_text,
                "cleaned_text": prep["clean_text"],
                "sentiment": sent["sentiment"],
                "compound_score": sent["compound"],
                "pos_score": sent["pos"],
                "neu_score": sent["neu"],
                "neg_score": sent["neg"],
                "date": p.get("date") or p.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            analyzed_posts.append(post_record)
            cleaned_tokens_all.append(prep["clean_tokens"])

            if sent["sentiment"] == "Positive" and prep["clean_text"]:
                positive_cleaned_texts.append(prep["clean_text"])
            elif sent["sentiment"] == "Negative" and prep["clean_text"]:
                negative_cleaned_texts.append(prep["clean_text"])

        # Aggregate summary and distribution
        metrics = compute_aggregate_metrics(analyzed_posts, alert_threshold=alert_threshold)

        # Daily Trend line series
        daily_trend = compute_time_series_trend(analyzed_posts)

        # Top 10 Keywords (suppress brand terms for cleaner insights)
        brand_words = brand_name.lower().split()
        top_keywords = extract_top_keywords(cleaned_tokens_all, top_n=10, brand_keywords=brand_words)

        # Base64 Word Clouds
        pos_wordcloud = generate_wordcloud_base64(positive_cleaned_texts, sentiment_type="positive")
        neg_wordcloud = generate_wordcloud_base64(negative_cleaned_texts, sentiment_type="negative")

        return {
            "summary": metrics["summary"],
            "alert": metrics["alert"],
            "distribution": metrics["distribution"],
            "daily_trend": daily_trend,
            "top_keywords": top_keywords,
            "wordclouds": {
                "positive": pos_wordcloud,
                "negative": neg_wordcloud,
            },
            "posts": analyzed_posts,
            "meta": {
                "brand": brand_name,
                "source": source_label,
                "count": len(analyzed_posts),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
        }

    # --------------------------------------------------------------------------
    # API Routes
    # --------------------------------------------------------------------------

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for Render / Uptime monitors."""
        return jsonify({
            "status": "ok",
            "service": "BrandPulse API",
            "time": datetime.now(timezone.utc).isoformat()
        }), 200

    @app.route("/api/analyze/sample", methods=["POST"])
    def analyze_sample():
        """
        Runs sentiment analysis on built-in sample data.
        JSON or Form parameters:
        - brand: string (e.g. 'Apple', 'Tesla', 'Nike')
        - count: integer (default 50)
        - threshold: float (default 40.0)
        """
        try:
            data = request.get_json(silent=True) or request.form.to_dict() or {}
            brand = data.get("brand", "Apple").strip()
            count = int(data.get("count", 50))
            threshold = float(data.get("threshold", 40.0))

            raw_posts, matched_brand = load_sample_tweets(brand, count=count)
            payload = run_analysis_pipeline(
                raw_posts=raw_posts,
                brand_name=matched_brand,
                source_label=f"Sample Dataset ({matched_brand})",
                alert_threshold=threshold
            )
            return jsonify(payload), 200

        except Exception as e:
            return jsonify({"error": f"Failed to analyze sample data: {str(e)}"}), 500

    @app.route("/api/analyze/csv", methods=["POST"])
    def analyze_csv():
        """
        Uploads and analyzes a custom CSV file.
        Multipart form fields:
        - file or csv_file: CSV file upload
        - brand: optional brand name
        - count: integer (default 100)
        - threshold: float (default 40.0)
        """
        try:
            uploaded_file = request.files.get("file") or request.files.get("csv_file")
            if not uploaded_file or not uploaded_file.filename:
                return jsonify({"error": "Please provide a valid CSV file to upload."}), 400

            if not uploaded_file.filename.lower().endswith(".csv"):
                return jsonify({"error": "Uploaded file must be a .csv file."}), 400

            brand = request.form.get("brand", "").strip()
            if not brand:
                brand = uploaded_file.filename.rsplit(".", 1)[0].replace("_", " ").title()

            count = int(request.form.get("count", 100))
            threshold = float(request.form.get("threshold", 40.0))

            raw_posts = load_csv_tweets(uploaded_file, max_count=count)
            payload = run_analysis_pipeline(
                raw_posts=raw_posts,
                brand_name=brand,
                source_label=f"CSV ({uploaded_file.filename})",
                alert_threshold=threshold
            )
            return jsonify(payload), 200

        except TwitterServiceError as e:
            return jsonify({"error": e.message, "user_hint": e.user_hint}), e.status_code
        except Exception as e:
            return jsonify({"error": f"Error parsing CSV file: {str(e)}"}), 500

    @app.route("/api/analyze/live", methods=["POST"])
    def analyze_live():
        """
        Fetches live tweets from X/Twitter API v2 and performs sentiment analysis.
        JSON or Form parameters:
        - keyword: brand name or keyword to query
        - count: integer (10-100, default 50)
        - threshold: float (default 40.0)
        """
        try:
            data = request.get_json(silent=True) or request.form.to_dict() or {}
            keyword = data.get("keyword") or data.get("brand") or ""
            keyword = keyword.strip()

            if not keyword:
                return jsonify({"error": "Keyword or brand name is required for live search."}), 400

            count = int(data.get("count", 50))
            threshold = float(data.get("threshold", 40.0))

            raw_posts = fetch_tweets_from_api(keyword, count=count)
            payload = run_analysis_pipeline(
                raw_posts=raw_posts,
                brand_name=keyword,
                source_label="Twitter API v2",
                alert_threshold=threshold
            )
            return jsonify(payload), 200

        except TwitterAuthError as e:
            return jsonify({
                "error": e.message,
                "user_hint": e.user_hint,
                "error_code": "AUTH_ERROR"
            }), 401
        except TwitterRateLimitError as e:
            return jsonify({
                "error": e.message,
                "user_hint": e.user_hint,
                "error_code": "RATE_LIMIT"
            }), 429
        except TwitterForbiddenError as e:
            return jsonify({
                "error": e.message,
                "user_hint": e.user_hint,
                "error_code": "FORBIDDEN"
            }), 403
        except TwitterServiceError as e:
            return jsonify({
                "error": e.message,
                "user_hint": e.user_hint,
                "error_code": "SERVICE_ERROR"
            }), e.status_code
        except Exception as e:
            return jsonify({
                "error": f"An unexpected error occurred: {str(e)}",
                "user_hint": "Please try sample data or upload a CSV."
            }), 500

    # --------------------------------------------------------------------------
    # Global Error Handlers (Always return JSON, never HTML errors)
    # --------------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


# Application entrypoint
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
