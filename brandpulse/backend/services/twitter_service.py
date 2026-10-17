"""
Twitter & Data Collection Service for BrandPulse Backend.
Handles Tweepy v2 API queries, rate limits, CSV uploads, and sample datasets.
"""
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import tweepy

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
SAMPLE_DATA_FILE = BACKEND_DIR / "data" / "sample_tweets.csv"


class TwitterServiceError(Exception):
    """Base exception for Twitter data collection errors."""
    def __init__(self, message: str, status_code: int = 400, user_hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.user_hint = user_hint or "Try switching to Sample Dataset mode or upload a CSV."


class TwitterAuthError(TwitterServiceError):
    def __init__(self, message: str = "Twitter Bearer Token is missing or invalid."):
        super().__init__(
            message=message,
            status_code=401,
            user_hint="Check TWITTER_BEARER_TOKEN in your environment or use Sample Dataset mode."
        )


class TwitterRateLimitError(TwitterServiceError):
    def __init__(self, message: str = "Twitter API rate limit reached (HTTP 429)."):
        super().__init__(
            message=message,
            status_code=429,
            user_hint="X/Twitter API free tier rate limit exceeded. Try again in 15 minutes or test with Sample Data."
        )


class TwitterForbiddenError(TwitterServiceError):
    def __init__(self, message: str = "Twitter API endpoint forbidden (HTTP 403)."):
        super().__init__(
            message=message,
            status_code=403,
            user_hint="Your developer tier does not allow recent search v2. Switch to Sample Dataset mode."
        )


def fetch_tweets_from_api(query_term: str, count: int = 50) -> List[Dict[str, Any]]:
    """Fetches recent tweets using Tweepy v2 search_recent_tweets."""
    token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if not token or token == "your_bearer_token_here":
        raise TwitterAuthError("Twitter Bearer Token is not configured on the backend server.")

    if not query_term or not query_term.strip():
        raise TwitterServiceError("Brand or keyword cannot be empty.", status_code=400)

    clean_term = query_term.strip()
    safe_count = max(10, min(int(count), 100))
    search_query = f"{clean_term} lang:en -is:retweet"

    try:
        client = tweepy.Client(bearer_token=token, wait_on_rate_limit=False)
        response = client.search_recent_tweets(
            query=search_query,
            max_results=safe_count,
            tweet_fields=["created_at", "lang"],
        )

        tweets = []
        if response and response.data:
            for item in response.data:
                created_at_str = item.created_at.isoformat() if hasattr(item, "created_at") and item.created_at else datetime.now(timezone.utc).isoformat()
                tweets.append({
                    "id": str(item.id),
                    "text": item.text,
                    "date": created_at_str,
                    "source": "Twitter API v2",
                })
        else:
            raise TwitterServiceError(
                f"No recent tweets found for '{clean_term}'. Try a broader keyword.",
                status_code=404,
                user_hint="Try searching for major brands like Apple, Tesla, or Nike."
            )

        return tweets

    except tweepy.errors.Unauthorized as e:
        raise TwitterAuthError(f"Twitter Authentication Failed: {str(e)}")
    except tweepy.errors.TooManyRequests as e:
        raise TwitterRateLimitError(f"Twitter Rate Limit Exceeded: {str(e)}")
    except tweepy.errors.Forbidden as e:
        raise TwitterForbiddenError(f"Twitter API Access Forbidden: {str(e)}")
    except TwitterServiceError:
        raise
    except Exception as e:
        raise TwitterServiceError(
            f"Twitter API Communication Error: {str(e)}",
            status_code=502,
            user_hint="Network issue or Twitter service disruption. Please try sample data."
        )


def load_sample_tweets(brand_name: Optional[str] = None, count: int = 50) -> Tuple[List[Dict[str, Any]], str]:
    """Loads tweets from data/sample_tweets.csv."""
    if not SAMPLE_DATA_FILE.exists():
        raise TwitterServiceError(f"Sample data file missing at {SAMPLE_DATA_FILE}", status_code=500)

    df = pd.read_csv(SAMPLE_DATA_FILE)
    safe_count = max(5, min(int(count), 150))

    matched_brand = "Sample Dataset"
    if brand_name and brand_name.strip():
        query = brand_name.strip().lower()
        brand_matches = df[df["brand"].str.lower() == query]
        if not brand_matches.empty:
            matched_brand = brand_matches["brand"].iloc[0]
            selected_df = brand_matches
        else:
            text_matches = df[df["text"].str.lower().str.contains(query, regex=False)]
            if not text_matches.empty:
                selected_df = text_matches
                matched_brand = brand_name.strip()
            else:
                selected_df = df
                matched_brand = f"{brand_name.strip()} (Sample Demo)"
    else:
        selected_df = df

    if len(selected_df) > safe_count:
        selected_df = selected_df.head(safe_count)

    tweets = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for idx, row in selected_df.iterrows():
        tweets.append({
            "id": f"sample-{idx + 1}",
            "text": str(row["text"]),
            "date": str(row.get("created_at", now_iso)),
            "source": f"Sample Data ({row.get('brand', 'General')})",
        })

    return tweets, matched_brand


def load_csv_tweets(file_stream_or_path, max_count: int = 100) -> List[Dict[str, Any]]:
    """Parses uploaded CSV file looking for a 'text' column and optional 'date'."""
    try:
        if isinstance(file_stream_or_path, (str, Path)):
            df = pd.read_csv(file_stream_or_path)
        else:
            file_stream_or_path.seek(0)
            df = pd.read_csv(file_stream_or_path)

        # Standardize column names
        col_map = {c: c.strip().lower() for c in df.columns}
        df = df.rename(columns=col_map)

        text_col = None
        for candidate in ["text", "tweet", "content", "post", "message", "body", "clean_text", "comment"]:
            if candidate in df.columns:
                text_col = candidate
                break

        if not text_col:
            raise TwitterServiceError(
                "CSV must contain a column named 'text', 'tweet', 'content', or 'message'.",
                status_code=400,
                user_hint=f"Columns found in uploaded file: {list(df.columns)}"
            )

        df = df.dropna(subset=[text_col])
        df = df[df[text_col].astype(str).str.strip().str.len() > 0]

        if df.empty:
            raise TwitterServiceError("The uploaded CSV contains no valid text rows.", status_code=400)

        df = df.head(max_count)

        date_col = None
        for candidate in ["created_at", "date", "timestamp", "time", "datetime", "post_date"]:
            if candidate in df.columns:
                date_col = candidate
                break

        now_iso = datetime.now(timezone.utc).isoformat()
        tweets = []
        for idx, row in df.iterrows():
            text_val = str(row[text_col]).strip()
            date_val = str(row[date_col]) if date_col and pd.notna(row[date_col]) else now_iso
            tweets.append({
                "id": f"csv-{idx + 1}",
                "text": text_val,
                "date": date_val,
                "source": "CSV Upload",
            })

        return tweets

    except TwitterServiceError:
        raise
    except Exception as e:
        raise TwitterServiceError(f"Error parsing CSV file: {str(e)}", status_code=400)
