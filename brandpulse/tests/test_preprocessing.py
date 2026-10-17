"""
Unit tests for text preprocessing functions in BrandPulse.
"""
import pytest
from services.preprocessing import (
    light_clean_for_vader,
    deep_clean_text,
    extract_hashtags,
    extract_top_keywords,
    preprocess_tweet,
)


def test_light_clean_for_vader():
    """Verify that light cleaning preserves casing and exclamation while removing URLs and mentions."""
    text = "OMG! Loving the new #iPhone from @Apple so much! https://t.co/abc123xyz"
    cleaned = light_clean_for_vader(text)
    
    assert "https://" not in cleaned
    assert "@Apple" not in cleaned
    assert "#" not in cleaned
    assert "iPhone" in cleaned
    assert "OMG!" in cleaned
    assert "Loving" in cleaned


def test_extract_hashtags():
    """Verify extraction of hashtags from tweet text."""
    text = "Excited for #AI and #MachineLearning revolution with #Tech!"
    tags = extract_hashtags(text)
    assert tags == ["ai", "machinelearning", "tech"]


def test_deep_clean_text():
    """Verify deep cleaning removes numbers, punctuation, stopwords and applies lemmatization."""
    text = "The 5 cars were running very quickly down the street!"
    clean_str, clean_tokens = deep_clean_text(text)

    # Numbers and punctuation should be gone
    assert "5" not in clean_str
    assert "!" not in clean_str

    # Stopwords like 'the', 'were', 'very', 'down' removed
    assert "the" not in clean_tokens
    assert "were" not in clean_tokens

    # Words like 'cars' lemmatized to 'car'
    assert "car" in clean_tokens


def test_preprocess_tweet_pipeline():
    """Verify complete dictionary output of preprocess_tweet."""
    sample = "Loving #Nike shoes! Best running gear ever @Nike http://nike.com"
    result = preprocess_tweet(sample)

    assert "original_text" in result
    assert "vader_ready_text" in result
    assert "clean_text" in result
    assert "clean_tokens" in result
    assert "hashtags" in result
    assert result["hashtags"] == ["nike"]
    assert "http" not in result["clean_text"]


def test_extract_top_keywords():
    """Verify top keywords counter and brand keyword suppression."""
    tokens_list = [
        ["camera", "battery", "apple", "screen"],
        ["camera", "display", "apple", "battery"],
        ["camera", "processor", "battery", "fast"],
    ]
    top_kw = extract_top_keywords(tokens_list, top_n=2, brand_keywords=["apple"])
    
    # 'apple' should be suppressed because it is the brand
    words = [item["word"] for item in top_kw]
    assert "apple" not in words
    # 'camera' and 'battery' occur 3 times each
    assert "camera" in words
    assert "battery" in words
    assert top_kw[0]["count"] == 3
