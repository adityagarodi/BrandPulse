"""
Charts & WordCloud Generation Service for BrandPulse Backend.
Generates Base64-encoded Word Clouds and structures visualization payloads.
"""
import io
import base64
from typing import List, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
from wordcloud import WordCloud


def generate_wordcloud_base64(
    texts: List[str],
    sentiment_type: str = "positive",
    width: int = 800,
    height: int = 400,
    background_color: str = "#0f172a"
) -> str:
    """Generates a word cloud image and returns a Base64-encoded PNG data URI."""
    joined_text = " ".join([t for t in texts if t and isinstance(t, str)]).strip()

    if not joined_text or len(joined_text.split()) < 2:
        return _create_placeholder_wordcloud(
            f"No {sentiment_type.capitalize()} Words Found",
            width, height, background_color
        )

    colormap = "Greens" if sentiment_type.lower() == "positive" else "Reds"

    try:
        wc = WordCloud(
            width=width,
            height=height,
            background_color=background_color,
            colormap=colormap,
            max_words=80,
            collocations=False,
            margin=8,
            random_state=42
        ).generate(joined_text)

        img_buffer = io.BytesIO()
        wc.to_image().save(img_buffer, format="PNG")
        img_buffer.seek(0)
        b64_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"

    except Exception as e:
        print(f"[WordCloud] Error generating cloud: {e}")
        return _create_placeholder_wordcloud("Word cloud unavailable", width, height, background_color)


def _create_placeholder_wordcloud(message: str, width: int, height: int, bg_color: str) -> str:
    """Creates a placeholder image when no words are available for that sentiment."""
    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.text(
        0.5, 0.5, message,
        ha="center", va="center",
        fontsize=16, color="#94a3b8",
        family="sans-serif", weight="bold"
    )
    ax.axis("off")

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="PNG", bbox_inches="tight", facecolor=bg_color)
    plt.close(fig)
    img_buffer.seek(0)
    b64_str = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"
