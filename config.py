"""
BrandPulse Configuration Module.
Loads environment variables and sets application parameters.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "brandpulse-default-secret-key-2026")
    
    # Database Configuration (ensure instance folder exists and use absolute path)
    INSTANCE_DIR = BASE_DIR / "instance"
    DATABASE_FILE = INSTANCE_DIR / "brandpulse.db"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_FILE.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads Configuration
    UPLOAD_FOLDER = BASE_DIR / "instance" / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {"csv"}

    # Twitter / X API v2 Credentials
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "").strip()
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "").strip()
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()

    # Brand Monitoring Thresholds
    DEFAULT_ALERT_THRESHOLD = float(os.getenv("DEFAULT_ALERT_THRESHOLD", 40.0))

    # Built-in sample dataset location
    SAMPLE_DATA_FILE = BASE_DIR / "data" / "sample_tweets.csv"

    @classmethod
    def has_twitter_credentials(cls) -> bool:
        """Returns True if a valid-looking Twitter Bearer Token or API keys are present."""
        return bool(cls.TWITTER_BEARER_TOKEN and cls.TWITTER_BEARER_TOKEN != "your_bearer_token_here")
