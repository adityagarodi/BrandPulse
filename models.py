"""
Database Models for BrandPulse.
Uses Flask-SQLAlchemy to store brand monitoring search history and individual analyzed posts.
"""
from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class SearchHistory(db.Model):
    """Stores metadata and summary metrics for an executed brand sentiment analysis run."""
    __tablename__ = "search_history"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(120), nullable=False, index=True)
    search_query = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(50), nullable=False, default="Twitter API v2")
    post_count = db.Column(db.Integer, default=0)
    positive_pct = db.Column(db.Float, default=0.0)
    neutral_pct = db.Column(db.Float, default=0.0)
    negative_pct = db.Column(db.Float, default=0.0)
    avg_compound = db.Column(db.Float, default=0.0)
    health_status = db.Column(db.String(20), default="Healthy")
    alert_triggered = db.Column(db.Boolean, default=False)
    alert_threshold = db.Column(db.Float, default=40.0)
    top_keywords_json = db.Column(db.Text, nullable=True)  # JSON-encoded top keywords
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # One-to-many relationship with AnalyzedPost
    posts = db.relationship(
        "AnalyzedPost",
        backref="search",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="AnalyzedPost.id.asc()"
    )

    def get_top_keywords(self):
        """Deserializes top_keywords_json into list of dicts."""
        if not self.top_keywords_json:
            return []
        try:
            return json.loads(self.top_keywords_json)
        except Exception:
            return []

    def set_top_keywords(self, keywords_list):
        """Serializes list of dicts into top_keywords_json."""
        self.top_keywords_json = json.dumps(keywords_list)

    def to_dict(self):
        """Serializes SearchHistory record to dictionary."""
        return {
            "id": self.id,
            "brand": self.brand,
            "query": self.search_query,
            "source": self.source,
            "post_count": self.post_count,
            "positive_pct": self.positive_pct,
            "neutral_pct": self.neutral_pct,
            "negative_pct": self.negative_pct,
            "avg_compound": self.avg_compound,
            "health_status": self.health_status,
            "alert_triggered": self.alert_triggered,
            "alert_threshold": self.alert_threshold,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M UTC") if self.created_at else "",
            "top_keywords": self.get_top_keywords()
        }


class AnalyzedPost(db.Model):
    """Stores individual social media posts analyzed during a brand search."""
    __tablename__ = "analyzed_post"

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey("search_history.id"), nullable=False, index=True)
    external_id = db.Column(db.String(100), nullable=True)
    original_text = db.Column(db.Text, nullable=False)
    cleaned_text = db.Column(db.Text, nullable=True)
    sentiment = db.Column(db.String(20), nullable=False)  # 'Positive', 'Neutral', 'Negative'
    compound_score = db.Column(db.Float, default=0.0)
    pos_score = db.Column(db.Float, default=0.0)
    neu_score = db.Column(db.Float, default=0.0)
    neg_score = db.Column(db.Float, default=0.0)
    post_date = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        """Serializes AnalyzedPost record to dictionary."""
        return {
            "id": self.id,
            "search_id": self.search_id,
            "external_id": self.external_id,
            "original_text": self.original_text,
            "cleaned_text": self.cleaned_text,
            "sentiment": self.sentiment,
            "compound_score": self.compound_score,
            "pos_score": self.pos_score,
            "neu_score": self.neu_score,
            "neg_score": self.neg_score,
            "post_date": self.post_date or "",
        }
