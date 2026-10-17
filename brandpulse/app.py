"""
BrandPulse — Sentiment Analysis of Social Media Data for Brand Monitoring.
Main Flask Application.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_file, current_app
)
from werkzeug.utils import secure_filename

from config import Config
from models import db, SearchHistory, AnalyzedPost
from services.preprocessing import (
    preprocess_tweet,
    extract_top_keywords,
    deep_clean_text
)
from services.sentiment import (
    analyze_sentiment,
    compute_aggregate_metrics,
    compute_time_series_trend
)
from services.twitter_service import (
    fetch_tweets_from_api,
    load_csv_tweets,
    load_sample_tweets,
    TwitterServiceError,
    TwitterAuthError,
    TwitterRateLimitError,
    TwitterForbiddenError
)
from services.visualization import (
    generate_wordcloud_base64,
    build_chart_js_payloads
)
from services.export_service import (
    export_posts_to_csv,
    export_analysis_to_pdf
)


def create_app(config_class=Config) -> Flask:
    """Application factory for BrandPulse."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize Database
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        return {
            "has_twitter_credentials": Config.has_twitter_credentials(),
            "default_alert_threshold": Config.DEFAULT_ALERT_THRESHOLD,
            "now_year": datetime.utcnow().year,
        }

    # --------------------------------------------------------------------------
    # Routes
    # --------------------------------------------------------------------------

    @app.route("/")
    def index():
        """Home page with search, CSV upload, and sample dataset selectors."""
        recent_searches = SearchHistory.query.order_by(SearchHistory.created_at.desc()).limit(5).all()
        return render_template(
            "index.html",
            recent_searches=recent_searches
        )

    @app.route("/analyze", methods=["POST"])
    def analyze():
        """
        Processes brand monitoring input from Twitter API, CSV upload, or Sample Data,
        runs NLTK cleaning + VADER sentiment analysis, saves to SQLite, and redirects to dashboard.
        """
        source_mode = request.form.get("source_mode", "sample")
        brand_name = request.form.get("brand_name", "").strip()
        count = int(request.form.get("count", 50))
        alert_threshold = float(request.form.get("alert_threshold", Config.DEFAULT_ALERT_THRESHOLD))

        raw_posts = []
        source_label = "Sample Dataset"

        try:
            # 1. Fetch data based on selected source mode
            if source_mode == "twitter":
                if not brand_name:
                    flash("Please provide a brand name, keyword, or hashtag to search.", "danger")
                    return redirect(url_for("index"))

                try:
                    raw_posts = fetch_tweets_from_api(brand_name, count=count)
                    source_label = "Twitter API v2"
                except TwitterAuthError as e:
                    flash(f"Twitter Authentication Error: {e.message} — {e.user_hint}", "warning")
                    # Graceful fallback to sample data matching the brand
                    raw_posts, matched_brand = load_sample_tweets(brand_name, count=count)
                    brand_name = matched_brand
                    source_label = "Sample Data (Auth Fallback)"
                except TwitterRateLimitError as e:
                    flash(f"Twitter Rate Limit (HTTP 429): {e.message} — {e.user_hint}", "warning")
                    raw_posts, matched_brand = load_sample_tweets(brand_name, count=count)
                    brand_name = matched_brand
                    source_label = "Sample Data (Rate Limit Fallback)"
                except TwitterForbiddenError as e:
                    flash(f"Twitter API Forbidden (HTTP 403): {e.message} — {e.user_hint}", "warning")
                    raw_posts, matched_brand = load_sample_tweets(brand_name, count=count)
                    brand_name = matched_brand
                    source_label = "Sample Data (Endpoint Fallback)"
                except TwitterServiceError as e:
                    flash(f"Twitter API Notice: {e.message} — {e.user_hint}", "info")
                    raw_posts, matched_brand = load_sample_tweets(brand_name, count=count)
                    brand_name = matched_brand
                    source_label = "Sample Data (Fallback)"

            elif source_mode == "csv":
                csv_file = request.files.get("csv_file")
                if not csv_file or not csv_file.filename:
                    flash("Please select a valid CSV file to upload.", "danger")
                    return redirect(url_for("index"))

                if not csv_file.filename.lower().endswith(".csv"):
                    flash("Uploaded file must have a .csv extension.", "danger")
                    return redirect(url_for("index"))

                filename = secure_filename(csv_file.filename)
                saved_path = Path(app.config["UPLOAD_FOLDER"]) / filename
                csv_file.save(saved_path)

                raw_posts = load_csv_tweets(saved_path, max_count=count)
                source_label = f"CSV ({filename})"
                if not brand_name:
                    brand_name = filename.rsplit(".", 1)[0].replace("_", " ").title()

            else:  # 'sample' mode
                preset_brand = request.form.get("sample_brand", brand_name or "Apple")
                raw_posts, matched_brand = load_sample_tweets(preset_brand, count=count)
                brand_name = matched_brand
                source_label = f"Built-in Sample ({preset_brand})"

            if not raw_posts:
                flash("No posts found to analyze.", "warning")
                return redirect(url_for("index"))

            # 2. Text Preprocessing & Sentiment Analysis
            analyzed_records = []
            cleaned_tokens_all = []

            for p in raw_posts:
                raw_text = p.get("text", "")
                prep_result = preprocess_tweet(raw_text)
                sentiment_result = analyze_sentiment(prep_result["vader_ready_text"])

                analyzed_records.append({
                    "external_id": str(p.get("id", "")),
                    "original_text": raw_text,
                    "cleaned_text": prep_result["clean_text"],
                    "clean_tokens": prep_result["clean_tokens"],
                    "sentiment": sentiment_result["sentiment"],
                    "compound_score": sentiment_result["compound"],
                    "pos_score": sentiment_result["pos"],
                    "neu_score": sentiment_result["neu"],
                    "neg_score": sentiment_result["neg"],
                    "post_date": p.get("created_at", ""),
                })
                cleaned_tokens_all.append(prep_result["clean_tokens"])

            # 3. Aggregate Metrics & Top Keywords
            metrics = compute_aggregate_metrics(analyzed_records, alert_threshold=alert_threshold)
            brand_words = brand_name.lower().split()
            top_keywords = extract_top_keywords(cleaned_tokens_all, top_n=10, brand_keywords=brand_words)

            # 4. Save to SQLite Database
            search_history = SearchHistory(
                brand=brand_name,
                search_query=request.form.get("brand_name", brand_name),
                source=source_label,
                post_count=metrics["total_posts"],
                positive_pct=metrics["positive_pct"],
                neutral_pct=metrics["neutral_pct"],
                negative_pct=metrics["negative_pct"],
                avg_compound=metrics["avg_compound"],
                health_status=metrics["brand_health"],
                alert_triggered=metrics["alert_triggered"],
                alert_threshold=alert_threshold,
            )
            search_history.set_top_keywords(top_keywords)
            db.session.add(search_history)
            db.session.flush()  # Generates search_history.id

            for item in analyzed_records:
                post_entry = AnalyzedPost(
                    search_id=search_history.id,
                    external_id=item["external_id"],
                    original_text=item["original_text"],
                    cleaned_text=item["cleaned_text"],
                    sentiment=item["sentiment"],
                    compound_score=item["compound_score"],
                    pos_score=item["pos_score"],
                    neu_score=item["neu_score"],
                    neg_score=item["neg_score"],
                    post_date=item["post_date"],
                )
                db.session.add(post_entry)

            db.session.commit()
            return redirect(url_for("dashboard", search_id=search_history.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Analysis encountered an error: {str(e)}", "danger")
            return redirect(url_for("index"))

    @app.route("/dashboard/<int:search_id>")
    def dashboard(search_id):
        """Interactive sentiment dashboard with summary cards, charts, wordclouds, and posts table."""
        search_record = SearchHistory.query.get_or_404(search_id)
        posts_query = AnalyzedPost.query.filter_by(search_id=search_id).all()
        posts_list = [p.to_dict() for p in posts_query]

        # Aggregate metrics
        metrics = {
            "total_posts": search_record.post_count,
            "positive_pct": search_record.positive_pct,
            "neutral_pct": search_record.neutral_pct,
            "negative_pct": search_record.negative_pct,
            "positive_count": sum(1 for p in posts_list if p["sentiment"] == "Positive"),
            "neutral_count": sum(1 for p in posts_list if p["sentiment"] == "Neutral"),
            "negative_count": sum(1 for p in posts_list if p["sentiment"] == "Negative"),
            "avg_compound": search_record.avg_compound,
            "brand_health": search_record.health_status,
            "alert_triggered": search_record.alert_triggered,
            "alert_threshold": search_record.alert_threshold,
        }

        # Health badge metadata
        if search_record.health_status == "Healthy":
            metrics["health_badge_class"] = "success"
            metrics["health_description"] = "Brand sentiment is overwhelmingly favorable and positive."
        elif search_record.health_status == "Warning":
            metrics["health_badge_class"] = "warning"
            metrics["health_description"] = "Moderate negative feedback detected. Monitor customer issues."
        else:
            metrics["health_badge_class"] = "danger"
            metrics["health_description"] = "High volume of customer dissatisfaction. Immediate response advised."

        # Compute time series trend for Line Chart
        time_series_data = compute_time_series_trend(posts_list)

        # Top keywords from record
        top_keywords = search_record.get_top_keywords()

        # Build Chart.js configurations
        charts = build_chart_js_payloads(metrics, time_series_data, top_keywords)

        # Generate Word Clouds (Positive & Negative)
        pos_texts = [p["cleaned_text"] for p in posts_list if p["sentiment"] == "Positive" and p["cleaned_text"]]
        neg_texts = [p["cleaned_text"] for p in posts_list if p["sentiment"] == "Negative" and p["cleaned_text"]]

        pos_wordcloud = generate_wordcloud_base64(pos_texts, sentiment_type="positive")
        neg_wordcloud = generate_wordcloud_base64(neg_texts, sentiment_type="negative")

        return render_template(
            "dashboard.html",
            search=search_record,
            metrics=metrics,
            charts=charts,
            top_keywords=top_keywords,
            pos_wordcloud=pos_wordcloud,
            neg_wordcloud=neg_wordcloud,
            posts=posts_list
        )

    @app.route("/history")
    def history():
        """Lists all previous brand sentiment analysis runs stored in SQLite."""
        searches = SearchHistory.query.order_by(SearchHistory.created_at.desc()).all()
        return render_template("history.html", searches=searches)

    @app.route("/history/<int:search_id>/delete", methods=["POST"])
    def delete_history(search_id):
        """Deletes a previous search and its associated posts from the database."""
        search = SearchHistory.query.get_or_404(search_id)
        db.session.delete(search)
        db.session.commit()
        flash(f"Analysis for '{search.brand}' deleted.", "info")
        return redirect(url_for("history"))

    @app.route("/compare", methods=["GET", "POST"])
    def compare():
        """Side-by-side brand sentiment comparison view."""
        all_searches = SearchHistory.query.order_by(SearchHistory.created_at.desc()).all()

        search_id_1 = request.args.get("brand1", type=int) or request.form.get("brand1", type=int)
        search_id_2 = request.args.get("brand2", type=int) or request.form.get("brand2", type=int)

        brand1 = None
        brand2 = None
        comparison_verdict = None

        if search_id_1 and search_id_2:
            brand1 = db.session.get(SearchHistory, search_id_1)
            brand2 = db.session.get(SearchHistory, search_id_2)

            if brand1 and brand2:
                # Calculate verdict
                score_diff = brand1.avg_compound - brand2.avg_compound
                if abs(score_diff) < 0.05:
                    winner_text = f"Both {brand1.brand} and {brand2.brand} have comparable sentiment performance."
                    winner_class = "secondary"
                elif score_diff > 0:
                    winner_text = f"🏆 {brand1.brand} leads with higher net sentiment ({brand1.positive_pct}% positive vs {brand2.positive_pct}% for {brand2.brand})."
                    winner_class = "success"
                else:
                    winner_text = f"🏆 {brand2.brand} leads with higher net sentiment ({brand2.positive_pct}% positive vs {brand1.positive_pct}% for {brand1.brand})."
                    winner_class = "success"

                comparison_verdict = {
                    "text": winner_text,
                    "class": winner_class,
                    "score_diff": round(abs(score_diff), 3)
                }

        return render_template(
            "compare.html",
            all_searches=all_searches,
            brand1=brand1,
            brand2=brand2,
            comparison_verdict=comparison_verdict
        )

    @app.route("/export/<int:search_id>/csv")
    def export_csv(search_id):
        """Exports analysis posts to CSV file for download."""
        search_record = SearchHistory.query.get_or_404(search_id)
        posts = [p.to_dict() for p in search_record.posts]
        csv_buffer = export_posts_to_csv(posts, search_record.brand)
        filename = f"BrandPulse_{secure_filename(search_record.brand)}_{search_id}.csv"
        return send_file(
            csv_buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )

    @app.route("/export/<int:search_id>/pdf")
    def export_pdf(search_id):
        """Exports executive sentiment analysis report as PDF."""
        search_record = SearchHistory.query.get_or_404(search_id)
        posts = [p.to_dict() for p in search_record.posts]
        pdf_buffer = export_analysis_to_pdf(search_record.to_dict(), posts)
        filename = f"BrandPulse_{secure_filename(search_record.brand)}_Report_{search_id}.pdf"
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    return app


# Application entrypoint
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
