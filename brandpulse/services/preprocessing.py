"""
Text Preprocessing Service using NLTK and Regex.
Performs text sanitization, tokenization, stopword removal, lemmatization,
and keyword extraction for social media brand sentiment analysis.
"""
import re
import html
import unicodedata
from typing import List, Dict, Any, Tuple
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


def download_nltk_resources() -> None:
    """Auto-downloads required NLTK corpora and models if not already present."""
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
                nltk.download(resource_name, quiet=True)
            except Exception as e:
                # Fallback non-quiet download attempt
                print(f"[NLTK] Error downloading {resource_name}: {e}")


# Ensure resources are downloaded on module import
download_nltk_resources()

# Initialize Lemmatizer and Stopwords
lemmatizer = WordNetLemmatizer()

try:
    NLTK_STOPWORDS = set(stopwords.words("english"))
except Exception:
    NLTK_STOPWORDS = set()

# Add domain-specific Twitter / social media noise words
CUSTOM_TWITTER_STOPWORDS = {
    "rt", "amp", "via", "http", "https", "co", "twitter", "tweet", "com",
    "get", "one", "would", "like", "also", "could", "got", "going", "go",
    "much", "even", "really", "still", "well", "see", "us", "u", "ur", "im"
}
ALL_STOPWORDS = NLTK_STOPWORDS.union(CUSTOM_TWITTER_STOPWORDS)


def light_clean_for_vader(text: str) -> str:
    """
    Lightly cleans text while preserving casing, punctuation, and emojis.
    VADER is rule-based and benefits from capitalization (e.g. 'GREAT')
    and exclamation points (e.g. '!') to score intensity.
    """
    if not text or not isinstance(text, str):
        return ""

    # Unescape HTML entities (&amp; -> &, &lt; -> <, etc.)
    cleaned = html.unescape(text)

    # Remove URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", "", cleaned)

    # Remove user mentions (@username)
    cleaned = re.sub(r"@[\w_]+", "", cleaned)

    # Remove hashtag symbol '#' but keep the word
    cleaned = re.sub(r"#([\w_]+)", r"\1", cleaned)

    # Normalize excessive whitespace
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
    Steps:
    1. Lowercase
    2. Remove URLs, mentions, and HTML entities
    3. Keep words from hashtags (strip #)
    4. Remove emojis and non-alphanumeric characters
    5. Tokenization
    6. Stopwords removal
    7. Lemmatization
    Returns:
        tuple: (cleaned_string, list_of_cleaned_tokens)
    """
    if not text or not isinstance(text, str):
        return "", []

    # 1. Unescape HTML
    text = html.unescape(text)

    # 2. Lowercase
    text = text.lower()

    # 3. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # 4. Remove User Mentions
    text = re.sub(r"@[\w_]+", "", text)

    # 5. Remove hashtag symbols but keep word
    text = re.sub(r"#([\w_]+)", r"\1", text)

    # 6. Remove numbers and punctuation (keep only letters and spaces)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    # 7. Normalize extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # 8. Tokenization
    try:
        tokens = word_tokenize(text)
    except Exception:
        tokens = text.split()

    # 9. Stopword removal & Lemmatization
    cleaned_tokens = []
    for token in tokens:
        token = token.strip()
        # Keep words longer than 2 characters and not in stopword set
        if len(token) > 2 and token not in ALL_STOPWORDS:
            lemma = lemmatizer.lemmatize(token)
            cleaned_tokens.append(lemma)

    cleaned_str = " ".join(cleaned_tokens)
    return cleaned_str, cleaned_tokens


def preprocess_tweet(text: str) -> Dict[str, Any]:
    """
    Main preprocessing entrypoint for a single tweet/post.
    Produces both VADER-ready text and deep-cleaned tokens for NLP analytics.
    """
    hashtags = extract_hashtags(text)
    vader_ready = light_clean_for_vader(text)
    clean_str, clean_tokens = deep_clean_text(text)

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
    """
    Computes top N most frequent keywords across analyzed texts.
    Optionally ignores the searched brand name words so insights aren't trivial.
    """
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
