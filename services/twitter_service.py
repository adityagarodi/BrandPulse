"""
Twitter / Social Media Data Collection Service.
Handles Tweepy v2 API interactions, rate limiting, authentication error handling,
and fallback mechanisms (CSV uploads and built-in sample datasets).
"""
import os
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import tweepy
from config import Config


class TwitterServiceError(Exception):
    """Base exception for Twitter data collection errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, user_hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.user_hint = user_hint or "Consider using the built-in sample data or uploading a CSV."


class TwitterAuthError(TwitterServiceError):
    """Raised when authentication fails (HTTP 401 / Invalid or missing Bearer token)."""
    def __init__(self, message: str = "Invalid or missing Twitter Bearer Token."):
        super().__init__(
            message=message,
            status_code=401,
            user_hint="Check your TWITTER_BEARER_TOKEN in .env or switch to Sample Dataset mode."
        )


class TwitterRateLimitError(TwitterServiceError):
    """Raised when Twitter API rate limits are hit (HTTP 429)."""
    def __init__(self, message: str = "Twitter API rate limit exceeded (HTTP 429)."):
        super().__init__(
            message=message,
            status_code=429,
            user_hint="X/Twitter API free/basic tier allows limited queries per 15-minute window. You can continue analysis instantly using Sample Data or CSV upload."
        )


class TwitterForbiddenError(TwitterServiceError):
    """Raised when access is forbidden or endpoint is restricted (HTTP 403)."""
    def __init__(self, message: str = "Twitter API endpoint forbidden or restricted (HTTP 403)."):
        super().__init__(
            message=message,
            status_code=403,
            user_hint="Your Twitter Developer App project tier may not support recent search v2. Switch to Sample Dataset mode to explore all features."
        )


def get_tweepy_client() -> tweepy.Client:
    """Initializes and returns a Tweepy v2 Client using configured credentials."""
    token = Config.TWITTER_BEARER_TOKEN
    if not token or token == "your_bearer_token_here":
        raise TwitterAuthError("Twitter Bearer Token is not configured.")

    return tweepy.Client(
        bearer_token=token,
        consumer_key=Config.TWITTER_API_KEY if Config.TWITTER_API_KEY else None,
        consumer_secret=Config.TWITTER_API_SECRET if Config.TWITTER_API_SECRET else None,
        access_token=Config.TWITTER_ACCESS_TOKEN if Config.TWITTER_ACCESS_TOKEN else None,
        access_token_secret=Config.TWITTER_ACCESS_TOKEN_SECRET if Config.TWITTER_ACCESS_TOKEN_SECRET else None,
        wait_on_rate_limit=False,
    )


def fetch_tweets_from_api(query_term: str, count: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches recent tweets from Twitter API v2 matching query_term.
    - Excludes retweets (-is:retweet)
    - Enforces English language (lang:en)
    - Clamps count between 10 and 100 per Twitter v2 search specification
    """
    if not query_term or not query_term.strip():
        raise TwitterServiceError("Search brand or keyword cannot be empty.")

    clean_term = query_term.strip()
    # Tweepy v2 max_results must be between 10 and 100
    safe_count = max(10, min(int(count), 100))

    # Construct standard search query
    # E.g. 'Tesla lang:en -is:retweet'
    search_query = f"{clean_term} lang:en -is:retweet"

    try:
        client = get_tweepy_client()
        response = client.search_recent_tweets(
            query=search_query,
            max_results=safe_count,
            tweet_fields=["created_at", "lang", "public_metrics", "author_id"],
        )

        tweets = []
        if response and response.data:
            for item in response.data:
                created_at_str = item.created_at.isoformat() if hasattr(item, "created_at") and item.created_at else datetime.now(timezone.utc).isoformat()
                tweets.append({
                    "id": str(item.id),
                    "text": item.text,
                    "created_at": created_at_str,
                    "source": "Twitter API v2",
                })
        else:
            raise TwitterServiceError(
                f"No recent tweets found for '{clean_term}'. Try a broader keyword.",
                user_hint="Try searching for major brands like Apple, Tesla, or Nike, or check with Sample Data."
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
            user_hint="Network issue or Twitter API service disruption. Use Sample Data to continue."
        )


def load_csv_tweets(file_stream_or_path, max_count: int = 100) -> List[Dict[str, Any]]:
    """
    Parses an uploaded CSV file containing social media posts.
    Accepts CSV with column named 'text', 'tweet', 'content', 'post', or 'message' (case-insensitive).
    Optionally extracts 'created_at', 'date', or 'time'.
    """
    try:
        if isinstance(file_stream_or_path, (str, Path)):
            df = pd.read_csv(file_stream_or_path)
        else:
            # Handle Werkzeug FileStorage or bytes
            file_stream_or_path.seek(0)
            df = pd.read_csv(file_stream_or_path)

        # Standardize column names to lowercase
        col_map = {c: c.strip().lower() for c in df.columns}
        df = df.rename(columns=col_map)

        # Find the text column
        text_col = None
        for candidate in ["text", "tweet", "content", "post", "message", "body", "clean_text", "comment"]:
            if candidate in df.columns:
                text_col = candidate
                break

        if not text_col:
            raise TwitterServiceError(
                "CSV must contain a column named 'text', 'tweet', 'content', or 'message'.",
                user_hint=f"Columns found in uploaded file: {list(df.columns)}"
            )

        # Drop empty text rows
        df = df.dropna(subset=[text_col])
        df = df[df[text_col].astype(str).str.strip().str.len() > 0]

        if df.empty:
            raise TwitterServiceError("The uploaded CSV has no valid text rows.")

        # Limit to max_count
        df = df.head(max_count)

        # Check for date column
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
                "created_at": date_val,
                "source": "CSV Upload",
            })

        return tweets

    except TwitterServiceError:
        raise
    except Exception as e:
        raise TwitterServiceError(f"Error reading CSV file: {str(e)}")


def load_sample_tweets(brand_name: Optional[str] = None, count: int = 50) -> Tuple[List[Dict[str, Any]], str]:
    """
    Loads tweets from the built-in sample dataset (data/sample_tweets.csv).
    If brand_name is given, tries to match brand or keyword; if no match or none given,
    returns a representative sample.
    Returns: (list_of_tweets, detected_or_matched_brand)
    """
    sample_file = Config.SAMPLE_DATA_FILE
    if not sample_file.exists():
        raise TwitterServiceError(f"Sample data file missing at {sample_file}")

    df = pd.read_csv(sample_file)
    safe_count = max(5, min(int(count), 150))

    matched_brand = "Sample Dataset"
    if brand_name and brand_name.strip():
        query = brand_name.strip().lower()
        # Check if brand column matches
        brand_matches = df[df["brand"].str.lower() == query]
        if not brand_matches.empty:
            matched_brand = brand_matches["brand"].iloc[0]
            selected_df = brand_matches
        else:
            # Check text contains keyword
            text_matches = df[df["text"].str.lower().str.contains(query, regex=False)]
            if not text_matches.empty:
                selected_df = text_matches
                matched_brand = brand_name.strip()
            else:
                # Return balanced multi-brand sample
                selected_df = df
                matched_brand = f"{brand_name.strip()} (Sample Demo)"
    else:
        selected_df = df

    # If count requested is larger than available, take all; otherwise sample or take head
    if len(selected_df) > safe_count:
        selected_df = selected_df.head(safe_count)

    tweets = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for idx, row in selected_df.iterrows():
        tweets.append({
            "id": f"sample-{idx + 1}",
            "text": str(row["text"]),
            "created_at": str(row.get("created_at", now_iso)),
            "source": f"Sample Data ({row.get('brand', 'General')})",
        })

    return tweets, matched_brand
