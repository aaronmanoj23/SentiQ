"""
PDF report generation for SentiQ analysis results.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import io
from datetime import datetime


# Brand colors
C_BG       = HexColor("#0a0a0f")
C_ACCENT   = HexColor("#00e5ff")
C_PURPLE   = HexColor("#7c3aed")
C_POS      = HexColor("#00d4aa")
C_NEG      = HexColor("#ff4d6d")
C_NEUTRAL  = HexColor("#f59e0b")
C_TEXT     = HexColor("#e8e8f0")
C_MUTED    = HexColor("#6b6b8a")
C_SURFACE  = HexColor("#1a1a24")


def sentiment_color(label: str) -> HexColor:
    if label == "POSITIVE":
        return C_POS
    elif label == "NEGATIVE":
        return C_NEG
    return C_NEUTRAL


def generate_pdf_report(result: dict) -> bytes:
    """Generate a PDF report from analysis results."""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "SentiQTitle",
        parent=styles["Heading1"],
        fontSize=28,
        textColor=C_ACCENT,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "SentiQSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=C_MUTED,
        spaceAfter=16,
        fontName="Helvetica",
    )
    section_style = ParagraphStyle(
        "SentiQSection",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=C_ACCENT,
        spaceBefore=16,
        spaceAfter=8,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "SentiQBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#ccccdd"),
        spaceAfter=6,
        fontName="Helvetica",
        leading=14,
    )
    label_style = ParagraphStyle(
        "SentiQLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=C_MUTED,
        fontName="Helvetica",
    )
    
    story = []
    llm = result.get("llm_summary", {})
    overall = result.get("overall_sentiment", {})
    ticker = result.get("ticker", "")
    company = result.get("company", "")
    year = result.get("year", "")
    quarter = result.get("quarter", "")
    
    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("SentiQ", title_style))
    story.append(Paragraph("SEC Filing Sentiment Intelligence", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=C_PURPLE, spaceAfter=16))
    
    # Filing info table
    info_data = [
        ["Company", f"{company} ({ticker})", "Period", f"Q{quarter} {year}"],
        ["Filed", "SEC EDGAR 10-Q", "Generated", datetime.now().strftime("%B %d, %Y")],
    ]
    info_table = Table(info_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("TEXTCOLOR",   (0,0), (0,-1), C_MUTED),
        ("TEXTCOLOR",   (2,0), (2,-1), C_MUTED),
        ("TEXTCOLOR",   (1,0), (1,-1), C_TEXT),
        ("TEXTCOLOR",   (3,0), (3,-1), C_TEXT),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_SURFACE, C_BG]),
        ("PADDING",     (0,0), (-1,-1), 6),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 16))
    
    # ── Overall Sentiment ────────────────────────────────────────────────────
    story.append(Paragraph("OVERALL SENTIMENT", section_style))
    
    label = overall.get("label", "NEUTRAL")
    confidence = overall.get("confidence", 0)
    pos = overall.get("positive", 0)
    neg = overall.get("negative", 0)
    neu = overall.get("neutral", 0)
    
    sent_data = [
        ["Verdict", "Confidence", "Positive", "Negative", "Neutral"],
        [label, f"{confidence:.1%}", f"{pos:.1%}", f"{neg:.1%}", f"{neu:.1%}"],
    ]
    sent_table = Table(sent_data, colWidths=[1.4*inch, 1.4*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    sent_table.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_MUTED),
        ("TEXTCOLOR",     (0,1), (0,1),   sentiment_color(label)),
        ("TEXTCOLOR",     (1,1), (-1,1),  C_TEXT),
        ("FONTNAME",      (0,1), (0,1),   "Helvetica-Bold"),
        ("FONTSIZE",      (0,1), (0,1),   14),
        ("BACKGROUND",    (0,0), (-1,0),  C_SURFACE),
        ("BACKGROUND",    (0,1), (-1,1),  C_BG),
        ("PADDING",       (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#2a2a3a")),
    ]))
    story.append(sent_table)
    story.append(Spacer(1, 8))
    
    # Overall tone
    tone = llm.get("overallTone", "")
    if tone:
        story.append(Paragraph(f"<i>{tone}</i>", body_style))
    
    # ── Analyst Takeaway ─────────────────────────────────────────────────────
    takeaway = llm.get("analystTakeaway", "")
    if takeaway:
        story.append(Paragraph("ANALYST TAKEAWAY", section_style))
        story.append(Paragraph(takeaway, body_style))
    
    # ── Key Risk Signals ─────────────────────────────────────────────────────
    risks = llm.get("keyRiskSignals", [])
    if risks:
        story.append(Paragraph("KEY RISK SIGNALS", section_style))
        for item in risks:
            risk_label = item.get("sentiment", {}).get("label", "NEUTRAL")
            conf = item.get("sentiment", {}).get("confidence", 0)
            risk_data = [
                [Paragraph(item.get("risk", ""), body_style),
                 Paragraph(f'<font color="#{_hex(sentiment_color(risk_label))}">{risk_label} ({conf:.0%})</font>', label_style)]
            ]
            risk_table = Table(risk_data, colWidths=[5.5*inch, 1.5*inch])
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), C_SURFACE),
                ("PADDING",    (0,0), (-1,-1), 8),
                ("LINEAFTER",  (0,0), (0,0),   2, sentiment_color(risk_label)),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("TOPPADDING", (0,0), (-1,-1), 6),
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 4))
    
    # ── Notable Changes ──────────────────────────────────────────────────────
    changes = llm.get("notableChanges", [])
    if changes:
        story.append(Paragraph("NOTABLE CHANGES", section_style))
        for item in changes:
            direction = item.get("direction", "neutral").upper()
            magnitude = item.get("magnitude", "")
            change_text = item.get("change", "")
            c = sentiment_color(direction if direction != "NEUTRAL" else "NEUTRAL")
            story.append(Paragraph(
                f'<font color="#{_hex(c)}">▸</font> {change_text} <font color="#{_hex(C_MUTED)}">— {magnitude}</font>',
                body_style
            ))
    
    # ── Evidence Citations ────────────────────────────────────────────────────
    citations = llm.get("evidenceCitations", [])
    if citations:
        story.append(Paragraph("EVIDENCE CITATIONS", section_style))
        for i, item in enumerate(citations, 1):
            text = item.get("text", "")
            sig = item.get("significance", "")
            s_label = item.get("sentiment", {}).get("label", "NEUTRAL")
            conf = item.get("sentiment", {}).get("confidence", 0)
            
            story.append(Paragraph(
                f'[{i}] <i>"{text}"</i>',
                ParagraphStyle("cite", parent=body_style, textColor=HexColor("#9999bb"), leftIndent=12)
            ))
            if sig:
                story.append(Paragraph(
                    f'<font color="#{_hex(C_MUTED)}">→ {sig}</font> '
                    f'<font color="#{_hex(sentiment_color(s_label))}">{s_label} ({conf:.0%})</font>',
                    ParagraphStyle("sig", parent=label_style, leftIndent=12, spaceAfter=8)
                ))
    
    # ── Ensemble Model Info ──────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#2a2a3a"), spaceAfter=8))
    story.append(Paragraph(
        "Models: FinBERT (ProsusAI) + Loughran-McDonald Lexicon (60/40 ensemble) · LLM: Claude Sonnet · Data: SEC EDGAR",
        ParagraphStyle("footer", parent=label_style, alignment=TA_CENTER, fontSize=7)
    ))
    
    doc.build(story)
    return buffer.getvalue()


def _hex(color: HexColor) -> str:
    """Extract hex string without #."""
    return color.hexval()[1:]
