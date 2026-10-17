"""
Text Preprocessing Service for BrandPulse Backend.
Safely manages NLTK data downloads into ./nltk_data, cleans social text,
performs tokenization, stopword removal, lemmatization, and keyword extraction.
"""
import os
import re
import html
from typing import List, Dict, Any, Tuple
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Configure NLTK data directory to ./nltk_data for cloud deployment resilience
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
NLTK_DATA_DIR = os.path.join(BACKEND_DIR, "nltk_data")
os.makedirs(NLTK_DATA_DIR, exist_ok=True)
nltk.data.path.insert(0, NLTK_DATA_DIR)


def ensure_nltk_resources():
    """Auto-downloads required NLTK corpora into the custom nltk_data folder if missing."""
    resources = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
        ("corpora/wordnet", "wordnet"),
        ("corpora/omw-1.4", "omw-1.4"),
        ("sentiment/vader_lexicon.zip", "vader_lexicon"),
    ]
    for resource_path, resource_name in resources:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            try:
                nltk.download(resource_name, download_dir=NLTK_DATA_DIR, quiet=True)
            except Exception as e:
                print(f"[NLTK] Error downloading {resource_name}: {e}")


# Run resource verification on module import
ensure_nltk_resources()

lemmatizer = WordNetLemmatizer()

try:
    NLTK_STOPWORDS = set(stopwords.words("english"))
except Exception:
    NLTK_STOPWORDS = set()

CUSTOM_STOPWORDS = {
    "rt", "amp", "via", "http", "https", "co", "twitter", "tweet", "com",
    "get", "one", "would", "like", "also", "could", "got", "going", "go",
    "much", "even", "really", "still", "well", "see", "us", "u", "ur", "im"
}
ALL_STOPWORDS = NLTK_STOPWORDS.union(CUSTOM_STOPWORDS)


def light_clean_for_vader(text: str) -> str:
    """
    Lightly cleans text while preserving capitalization, punctuation, and emojis.
    VADER relies on casing and punctuation to gauge sentiment intensity.
    """
    if not text or not isinstance(text, str):
        return ""

    cleaned = html.unescape(text)
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", cleaned)
    cleaned = re.sub(r"@[\w_]+", "", cleaned)
    cleaned = re.sub(r"#([\w_]+)", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_hashtags(text: str) -> List[str]:
    """Extracts all hashtags without the '#' symbol in lowercase."""
    if not text or not isinstance(text, str):
        return []
    return [tag.lower() for tag in re.findall(r"#(\w+)", text)]


def deep_clean_text(text: str) -> Tuple[str, List[str]]:
    """
    Deep cleaning for word cloud generation and keyword frequency analysis.
    Steps: lowercasing, entity stripping, non-alpha removal, tokenization,
    stopwords removal, and WordNet lemmatization.
    """
    if not text or not isinstance(text, str):
        return "", []

    text = html.unescape(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@[\w_]+", "", text)
    text = re.sub(r"#([\w_]+)", r"\1", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = text.split()

    cleaned_tokens = []
    for token in tokens:
        token = token.strip()
        if len(token) > 2 and token not in ALL_STOPWORDS:
            lemma = lemmatizer.lemmatize(token)
            cleaned_tokens.append(lemma)

    cleaned_str = " ".join(cleaned_tokens)
    return cleaned_str, cleaned_tokens


def preprocess_tweet(text: str) -> Dict[str, Any]:
    """Preprocesses a single tweet for both VADER and keyword analysis."""
    vader_ready = light_clean_for_vader(text)
    clean_str, clean_tokens = deep_clean_text(text)
    hashtags = extract_hashtags(text)

    return {
        "original_text": text,
        "vader_ready_text": vader_ready,
        "clean_text": clean_str,
        "clean_tokens": clean_tokens,
        "hashtags": hashtags,
    }


def extract_top_keywords(
    clean_texts_or_tokens: List[Any],
    top_n: int = 10,
    brand_keywords: List[str] = None
) -> List[Dict[str, Any]]:
    """Computes top N most frequent keywords across analyzed texts."""
    ignore_set = set(ALL_STOPWORDS)
    if brand_keywords:
        for b in brand_keywords:
            ignore_set.add(b.lower())

    counter = Counter()
    for item in clean_texts_or_tokens:
        if isinstance(item, list):
            words = item
        elif isinstance(item, str):
            words = item.split()
        else:
            continue

        filtered = [w.lower() for w in words if len(w) > 2 and w.lower() not in ignore_set]
        counter.update(filtered)

    top_words = counter.most_common(top_n)
    return [{"word": word, "count": count} for word, count in top_words]
