"""
Visualization Service for BrandPulse.
Generates Word Clouds (Positive & Negative) encoded as Base64 PNGs,
and formats data structures for Chart.js interactive dashboards.
"""
import io
import base64
from typing import List, Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend safe for web servers
import matplotlib.pyplot as plt
from wordcloud import WordCloud


def generate_wordcloud_base64(
    texts: List[str],
    sentiment_type: str = "positive",
    width: int = 800,
    height: int = 400,
    background_color: str = "#0f172a"  # Slate 900 dark theme
) -> Optional[str]:
    """
    Generates a word cloud image from a list of cleaned text strings
    and returns it as a Base64 encoded PNG data URI.
    
    Color themes:
    - positive: vibrant emerald/cyan/green ('viridis' or 'summer')
    - negative: fiery rose/crimson/orange ('plasma' or 'autumn')
    """
    joined_text = " ".join([t for t in texts if t and isinstance(t, str)]).strip()

    # If not enough words to form a cloud, generate a friendly informative canvas
    if not joined_text or len(joined_text.split()) < 2:
        return _create_placeholder_wordcloud(
            f"No {sentiment_type.capitalize()} Words Found",
            width, height, background_color
        )

    # Choose tailored colormap based on sentiment
    if sentiment_type.lower() == "positive":
        colormap = "Greens"
    elif sentiment_type.lower() == "negative":
        colormap = "Reds"
    else:
        colormap = "coolwarm"

    try:
        wc = WordCloud(
            width=width,
            height=height,
            background_color=background_color,
            colormap=colormap,
            max_words=80,
            collocations=False,
            contour_width=0,
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
        return _create_placeholder_wordcloud(f"Word cloud unavailable", width, height, background_color)


def _create_placeholder_wordcloud(message: str, width: int, height: int, bg_color: str) -> str:
    """Creates a sleek placeholder image when no words are available for that sentiment."""
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


def build_chart_js_payloads(
    metrics: Dict[str, Any],
    time_series_data: Dict[str, Any],
    top_keywords: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Constructs clean, JSON-serializable configurations for Chart.js:
    1. Sentiment Donut/Pie Chart
    2. Sentiment Over Time Line Chart
    3. Top Keywords/Hashtags Bar Chart
    """
    # 1. Donut Chart
    donut_chart = {
        "labels": ["Positive", "Neutral", "Negative"],
        "datasets": [{
            "data": [
                metrics.get("positive_count", 0),
                metrics.get("neutral_count", 0),
                metrics.get("negative_count", 0)
            ],
            "backgroundColor": ["#10B981", "#F59E0B", "#EF4444"],
            "hoverBackgroundColor": ["#059669", "#D97706", "#DC2626"],
            "borderWidth": 2,
            "borderColor": "#1e293b",
        }]
    }

    # 2. Line Chart (Trend Over Time)
    dates = time_series_data.get("dates", [])
    pos_series = time_series_data.get("positive_series", [])
    neu_series = time_series_data.get("neutral_series", [])
    neg_series = time_series_data.get("negative_series", [])
    compound_series = time_series_data.get("avg_compound_series", [])

    line_chart = {
        "labels": dates,
        "datasets": [
            {
                "label": "Positive",
                "data": pos_series,
                "borderColor": "#10B981",
                "backgroundColor": "rgba(16, 185, 129, 0.15)",
                "tension": 0.35,
                "fill": True,
                "pointRadius": 4,
            },
            {
                "label": "Neutral",
                "data": neu_series,
                "borderColor": "#F59E0B",
                "backgroundColor": "rgba(245, 158, 11, 0.1)",
                "tension": 0.35,
                "fill": False,
                "pointRadius": 4,
            },
            {
                "label": "Negative",
                "data": neg_series,
                "borderColor": "#EF4444",
                "backgroundColor": "rgba(239, 68, 68, 0.15)",
                "tension": 0.35,
                "fill": True,
                "pointRadius": 4,
            }
        ]
    }

    # 3. Bar Chart (Top Keywords)
    kw_labels = [k["word"] for k in top_keywords]
    kw_counts = [k["count"] for k in top_keywords]

    bar_chart = {
        "labels": kw_labels,
        "datasets": [{
            "label": "Occurrences",
            "data": kw_counts,
            "backgroundColor": "#6366F1",
            "hoverBackgroundColor": "#4F46E5",
            "borderRadius": 6,
            "borderWidth": 0,
        }]
    }

    return {
        "donut_chart": donut_chart,
        "line_chart": line_chart,
        "bar_chart": bar_chart,
    }
