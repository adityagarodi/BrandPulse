"""
Export Service for BrandPulse.
Generates CSV and PDF reports from brand sentiment analysis results.
Uses ReportLab for clean, professional PDF document rendering.
"""
import io
import csv
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)


def export_posts_to_csv(posts: List[Dict[str, Any]], brand_name: str) -> io.BytesIO:
    """
    Exports analyzed posts to a CSV file in memory.
    Returns a BytesIO stream ready for Flask send_file.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Post ID", "Date", "Brand", "Sentiment", "Compound Score",
        "Positive Score", "Neutral Score", "Negative Score",
        "Cleaned Text", "Original Text"
    ])

    for p in posts:
        writer.writerow([
            p.get("id", ""),
            p.get("post_date") or p.get("created_at", ""),
            brand_name,
            p.get("sentiment", ""),
            p.get("compound_score", p.get("compound", 0.0)),
            p.get("pos_score", p.get("pos", 0.0)),
            p.get("neu_score", p.get("neu", 0.0)),
            p.get("neg_score", p.get("neg", 0.0)),
            p.get("cleaned_text", p.get("clean_text", "")),
            p.get("original_text", p.get("text", "")),
        ])

    bytes_output = io.BytesIO()
    bytes_output.write(output.getvalue().encode("utf-8-sig"))  # UTF-8 with BOM for Excel compatibility
    bytes_output.seek(0)
    return bytes_output


def export_analysis_to_pdf(
    search_record: Dict[str, Any],
    posts: List[Dict[str, Any]]
) -> io.BytesIO:
    """
    Generates a professional executive PDF report summarizing brand sentiment metrics,
    health indicators, sentiment breakdown, and sample highlighted posts.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom BrandPulse Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        alignment=1,
        textColor=colors.white
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("BrandPulse — Executive Sentiment Report", title_style))
    brand_name = search_record.get("brand", "Brand Analysis")
    created_at = search_record.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    source = search_record.get("source", "Social Media Feed")
    elements.append(Paragraph(f"Brand Monitored: <b>{brand_name}</b> &nbsp;|&nbsp; Generated: {created_at} &nbsp;|&nbsp; Data Source: {source}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

    # 2. Executive Summary Metrics Table
    elements.append(Paragraph("1. Executive Summary & Brand Health", section_heading))

    health_status = search_record.get("health_status", "Healthy")
    health_color = colors.HexColor("#10b981") if health_status == "Healthy" else (
        colors.HexColor("#f59e0b") if health_status == "Warning" else colors.HexColor("#ef4444")
    )

    alert_txt = "TRIGGERED (High Negative Vol)" if search_record.get("alert_triggered") else "NORMAL (Below Threshold)"
    alert_color = colors.HexColor("#ef4444") if search_record.get("alert_triggered") else colors.HexColor("#10b981")

    summary_data = [
        [
            Paragraph("<b>Total Posts Analyzed:</b>", body_style),
            Paragraph(str(search_record.get("post_count", len(posts))), body_style),
            Paragraph("<b>Brand Health Status:</b>", body_style),
            Paragraph(f"<b>{health_status.upper()}</b>", ParagraphStyle("H", parent=body_style, textColor=health_color, fontName="Helvetica-Bold"))
        ],
        [
            Paragraph("<b>Average Compound Score:</b>", body_style),
            Paragraph(f"{search_record.get('avg_compound', 0.0):+.4f} (-1.0 to +1.0)", body_style),
            Paragraph("<b>Alert Status:</b>", body_style),
            Paragraph(f"<b>{alert_txt}</b>", ParagraphStyle("A", parent=body_style, textColor=alert_color, fontName="Helvetica-Bold"))
        ]
    ]

    t_summary = Table(summary_data, colWidths=[130, 140, 130, 140])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 14))

    # 3. Sentiment Distribution Breakdown Table
    elements.append(Paragraph("2. Sentiment Distribution Breakdown", section_heading))

    pos_pct = search_record.get("positive_pct", 0.0)
    neu_pct = search_record.get("neutral_pct", 0.0)
    neg_pct = search_record.get("negative_pct", 0.0)
    total_count = search_record.get("post_count", len(posts)) or 1

    pos_c = int(round((pos_pct / 100.0) * total_count))
    neu_c = int(round((neu_pct / 100.0) * total_count))
    neg_c = max(0, total_count - pos_c - neu_c)

    dist_data = [
        [
            Paragraph("<b>Sentiment Tier</b>", body_style),
            Paragraph("<b>VADER Compound Criteria</b>", body_style),
            Paragraph("<b>Volume (Posts)</b>", body_style),
            Paragraph("<b>Percentage Share</b>", body_style)
        ],
        [
            Paragraph("<font color='#10b981'><b>Positive</b></font>", body_style),
            Paragraph("Compound Score ≥ +0.05", body_style),
            Paragraph(str(pos_c), body_style),
            Paragraph(f"<b>{pos_pct:.1f}%</b>", body_style)
        ],
        [
            Paragraph("<font color='#f59e0b'><b>Neutral</b></font>", body_style),
            Paragraph("-0.05 < Compound < +0.05", body_style),
            Paragraph(str(neu_c), body_style),
            Paragraph(f"<b>{neu_pct:.1f}%</b>", body_style)
        ],
        [
            Paragraph("<font color='#ef4444'><b>Negative</b></font>", body_style),
            Paragraph("Compound Score ≤ -0.05", body_style),
            Paragraph(str(neg_c), body_style),
            Paragraph(f"<b>{neg_pct:.1f}%</b>", body_style)
        ]
    ]

    t_dist = Table(dist_data, colWidths=[120, 180, 110, 130])
    t_dist.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0fdf4")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fffbeb")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fef2f2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t_dist)
    elements.append(Spacer(1, 16))

    # 4. Recent / Top Highlighted Posts Sample
    elements.append(Paragraph("3. Sample Analyzed Posts", section_heading))

    post_rows = [
        [
            Paragraph("<b>Date</b>", body_style),
            Paragraph("<b>Sentiment</b>", body_style),
            Paragraph("<b>Score</b>", body_style),
            Paragraph("<b>Social Media Post Content</b>", body_style)
        ]
    ]

    # Select up to top 8 posts to fit on 1-2 pages neatly
    sample_posts = posts[:10]
    for p in sample_posts:
        sent = p.get("sentiment", "Neutral")
        score = p.get("compound_score", p.get("compound", 0.0))
        date_str = str(p.get("post_date", p.get("created_at", "")))[:10]
        text_content = str(p.get("original_text", p.get("text", "")))
        if len(text_content) > 130:
            text_content = text_content[:127] + "..."

        sent_color = "#10b981" if sent == "Positive" else ("#f59e0b" if sent == "Neutral" else "#ef4444")

        post_rows.append([
            Paragraph(date_str, body_style),
            Paragraph(f"<font color='{sent_color}'><b>{sent}</b></font>", body_style),
            Paragraph(f"{score:+.2f}", body_style),
            Paragraph(text_content, body_style)
        ])

    t_posts = Table(post_rows, colWidths=[70, 75, 45, 350])
    t_posts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(t_posts)

    # 5. Build Document
    doc.build(elements)
    buffer.seek(0)
    return buffer
