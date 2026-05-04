"""
Single company, single quarter analysis page.
"""

import streamlit as st
import plotly.graph_objects as go
import sys
import os
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import full_analysis
from utils.stocks import get_current_price
from utils.pdf_export import generate_pdf_report


PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#e8e8f0", size=11),
    margin=dict(l=20, r=20, t=30, b=20),
)

SENTIMENT_COLORS = {
    "POSITIVE": "#00d4aa",
    "NEGATIVE": "#ff4d6d",
    "NEUTRAL": "#f59e0b",
}


def html_safe(value):
    return escape(str(value or ""))


def safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def badge(label: str) -> str:
    label = str(label or "NEUTRAL").upper()
    cls = f"badge-{label.lower()}"
    return f'<span class="sentiment-badge {cls}">{label}</span>'


def confidence_bar(score: float, label: str) -> str:
    score = safe_float(score)
    score = max(0, min(score, 1))

    label = str(label or "NEUTRAL").upper()
    color = SENTIMENT_COLORS.get(label, "#f59e0b")
    pct = int(score * 100)

    return f"""
    <div style="display:flex;align-items:center;gap:8px;margin:2px 0">
        <div style="flex:1;background:#1a1a24;border-radius:3px;height:6px;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:3px;transition:width 0.5s"></div>
        </div>
        <span style="font-size:0.75rem;color:#9999bb;min-width:36px">{pct}%</span>
    </div>"""


def render_single(ticker: str, company: str, year: int, quarter: int, run: bool):
    company_display = html_safe(company)
    ticker_display = html_safe(ticker)

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"## {company_display}")
        st.markdown(
            f'<div style="color:#6b6b8a;font-size:0.8rem;letter-spacing:0.15em">Q{quarter} {year} · 10-Q ANALYSIS</div>',
            unsafe_allow_html=True,
        )

    with col2:
        price_data = get_current_price(ticker)

        if price_data:
            change_pct = safe_float(price_data.get("change_pct"))
            price = safe_float(price_data.get("price"))

            delta_color = "#00d4aa" if change_pct >= 0 else "#ff4d6d"
            delta_sign = "+" if change_pct >= 0 else ""

            st.markdown(
                f"""
                <div class="metric-card" style="text-align:right">
                    <div class="metric-label">{ticker_display} · Live Price</div>
                    <div class="metric-value">${price:,.2f}</div>
                    <div class="metric-sub" style="color:{delta_color}">{delta_sign}{change_pct:.2f}% today</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not run:
        st.markdown(
            """
            <div style="text-align:center;padding:4rem 2rem;color:#6b6b8a">
                <div style="font-size:3rem;margin-bottom:1rem">📊</div>
                <div style="font-family:'Syne',sans-serif;font-size:1.2rem;margin-bottom:0.5rem;color:#e8e8f0">Select a company and run analysis</div>
                <div style="font-size:0.85rem">SentiQ fetches live SEC filings and scores them with a FinBERT + LM ensemble</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    with st.spinner(f"Fetching {ticker} Q{quarter} {year} 10-Q filing..."):
        try:
            result = full_analysis(ticker, company, year, quarter)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return

    overall = result["overall_sentiment"]
    llm = result["llm_summary"]

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    label = str(overall.get("label", "NEUTRAL")).upper()
    conf = safe_float(overall.get("confidence"))
    pos = safe_float(overall.get("positive"))
    neg = safe_float(overall.get("negative"))

    with m1:
        color = SENTIMENT_COLORS.get(label, "#f59e0b")
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Overall Verdict</div>
                <div class="metric-value" style="color:{color}">{label}</div>
                <div class="metric-sub">Ensemble confidence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Confidence</div>
                <div class="metric-value">{conf:.1%}</div>
                <div class="metric-sub">FinBERT + LM ensemble</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Positive Signal</div>
                <div class="metric-value" style="color:#00d4aa">{pos:.1%}</div>
                <div class="metric-sub">of filing language</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Negative Signal</div>
                <div class="metric-value" style="color:#ff4d6d">{neg:.1%}</div>
                <div class="metric-sub">of filing language</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    sections_used = result.get("sections_used", [])
    chunks_used = result.get("chunks_used", 0)
    data_source = result.get("data_source", "Unknown")

    st.markdown('<div class="section-header">SECTIONS ANALYZED</div>', unsafe_allow_html=True)

    if sections_used:
        section_tags = " ".join([
            f'<span class="sentiment-badge badge-neutral" style="margin-right:6px;margin-bottom:6px">{html_safe(section)}</span>'
            for section in sections_used
        ])

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Data Source</div>
                <div style="font-size:0.85rem;color:#e8e8f0;margin-bottom:0.7rem">
                    {html_safe(data_source)} · {safe_float(chunks_used):.0f} chunk(s) analyzed
                </div>
                <div>{section_tags}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-sub">No specific filing sections were identified.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_summary = st.columns([1, 1])

    with col_chart:
        st.markdown('<div class="section-header">SENTIMENT BREAKDOWN</div>', unsafe_allow_html=True)

        fb = overall.get("finbert", {})
        lm = overall.get("lm", {})

        fig = go.Figure()
        categories = ["Positive", "Negative", "Neutral"]

        fig.add_trace(
            go.Bar(
                name="FinBERT",
                x=categories,
                y=[
                    safe_float(fb.get("positive")),
                    safe_float(fb.get("negative")),
                    safe_float(fb.get("neutral")),
                ],
                marker_color=[
                    "rgba(0,212,170,0.8)",
                    "rgba(255,77,109,0.8)",
                    "rgba(245,158,11,0.8)",
                ],
            )
        )

        fig.add_trace(
            go.Bar(
                name="LM Lexicon",
                x=categories,
                y=[
                    safe_float(lm.get("positive")),
                    safe_float(lm.get("negative")),
                    safe_float(lm.get("neutral")),
                ],
                marker_color=[
                    "rgba(0,212,170,0.4)",
                    "rgba(255,77,109,0.4)",
                    "rgba(245,158,11,0.4)",
                ],
            )
        )

        fig.add_trace(
            go.Bar(
                name="Ensemble",
                x=categories,
                y=[
                    safe_float(overall.get("positive")),
                    safe_float(overall.get("negative")),
                    safe_float(overall.get("neutral")),
                ],
                marker_color=["#00d4aa", "#ff4d6d", "#f59e0b"],
                marker_line=dict(color="white", width=1),
            )
        )

        fig.update_layout(
            **PLOTLY_THEME,
            barmode="group",
            bargap=0.2,
            bargroupgap=0.05,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                font=dict(size=10),
                bgcolor="rgba(0,0,0,0)",
            ),
            yaxis=dict(
                tickformat=".0%",
                gridcolor="#2a2a3a",
                range=[0, 1],
                tickfont=dict(size=10),
            ),
            xaxis=dict(gridcolor="#2a2a3a"),
            height=280,
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_summary:
        st.markdown('<div class="section-header">LLM SUMMARY</div>', unsafe_allow_html=True)

        tone = html_safe(llm.get("overallTone", ""))
        takeaway = html_safe(llm.get("analystTakeaway", ""))

        if tone:
            st.markdown(
                f'<div style="font-size:0.9rem;color:#e8e8f0;line-height:1.6;margin-bottom:1rem"><em>{tone}</em></div>',
                unsafe_allow_html=True,
            )

        if takeaway:
            st.markdown(
                f'<div style="font-size:0.82rem;color:#9999bb;line-height:1.7">{takeaway}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    col_risks, col_changes = st.columns([1, 1])

    with col_risks:
        st.markdown('<div class="section-header">KEY RISK SIGNALS</div>', unsafe_allow_html=True)

        risks = llm.get("keyRiskSignals", [])

        for item in risks:
            s = item.get("sentiment", {})
            s_label = str(s.get("label", "NEUTRAL")).upper()
            conf_val = safe_float(s.get("confidence"))
            border_color = SENTIMENT_COLORS.get(s_label, "#f59e0b")

            risk_text = html_safe(item.get("risk", ""))
            detail_text = html_safe(item.get("detail", ""))

            st.markdown(
                f"""
                <div class="risk-item" style="border-left-color:{border_color}">
                    <div style="font-weight:500;margin-bottom:4px">{risk_text}</div>
                    <div style="font-size:0.78rem;color:#9999bb;margin-bottom:6px">{detail_text}</div>
                    {confidence_bar(conf_val, s_label)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_changes:
        st.markdown('<div class="section-header">NOTABLE CHANGES</div>', unsafe_allow_html=True)

        changes = llm.get("notableChanges", [])

        for item in changes:
            direction = str(item.get("direction", "neutral")).upper()
            magnitude = html_safe(item.get("magnitude", ""))
            change_text = html_safe(item.get("change", ""))

            color = SENTIMENT_COLORS.get(direction, "#f59e0b")
            icon = "▲" if direction == "POSITIVE" else "▼" if direction == "NEGATIVE" else "●"

            s = item.get("sentiment", {})
            conf_val = safe_float(s.get("confidence"))

            st.markdown(
                f"""
                <div class="risk-item" style="border-left-color:{color}">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                        <span style="font-weight:500">{change_text}</span>
                        <span style="color:{color};font-size:0.8rem">{icon} {magnitude}</span>
                    </div>
                    {confidence_bar(conf_val, direction)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown('<div class="section-header">EVIDENCE CITATIONS</div>', unsafe_allow_html=True)

    citations = llm.get("evidenceCitations", [])

    for i, item in enumerate(citations, 1):
        s = item.get("sentiment", {})
        s_label = str(s.get("label", "NEUTRAL")).upper()
        conf_val = safe_float(s.get("confidence"))

        evidence_text = html_safe(item.get("text", ""))
        significance = html_safe(item.get("significance", "Evidence"))
        expander_title = significance[:80] + "..."

        with st.expander(f"[{i}] {expander_title}", expanded=False):
            st.markdown(
                f"""
                <div style="padding:0.5rem">
                    <div class="evidence-item">"{evidence_text}"</div>
                    <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
                        <span class="sentiment-badge badge-{s_label.lower()}">{s_label}</span>
                        <span style="font-size:0.78rem;color:#9999bb">Confidence: {conf_val:.0%}</span>
                    </div>
                    {confidence_bar(conf_val, s_label)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown('<div class="section-header">STOCK CONTEXT</div>', unsafe_allow_html=True)

    try:
        from utils.stocks import get_stock_data

        price_df = get_stock_data(ticker, year)

        if price_df is not None and not price_df.empty:
            q_months = {
                1: [1, 2, 3],
                2: [4, 5, 6],
                3: [7, 8, 9],
                4: [10, 11, 12],
            }

            q_data = price_df[price_df["Month"].isin(q_months[quarter])]

            if not q_data.empty:
                fig2 = go.Figure()

                fig2.add_trace(
                    go.Scatter(
                        x=q_data["Date"],
                        y=q_data["Close"],
                        mode="lines+markers",
                        line=dict(color="#7c3aed", width=2),
                        marker=dict(size=6, color="#00e5ff"),
                        fill="tozeroy",
                        fillcolor="rgba(124,58,237,0.08)",
                        name=f"{ticker_display} Close",
                    )
                )

                mid_idx = len(q_data) // 2

                if mid_idx < len(q_data):
                    mid_date = q_data.iloc[mid_idx]["Date"]
                    mid_price = q_data.iloc[mid_idx]["Close"]

                    fig2.add_annotation(
                        x=mid_date,
                        y=mid_price,
                        text=f"  {label} ({conf:.0%})",
                        showarrow=True,
                        arrowhead=2,
                        font=dict(
                            color=SENTIMENT_COLORS.get(label, "#f59e0b"),
                            size=11,
                        ),
                        arrowcolor=SENTIMENT_COLORS.get(label, "#f59e0b"),
                    )

                fig2.update_layout(
                    **PLOTLY_THEME,
                    height=240,
                    xaxis=dict(gridcolor="#2a2a3a", showgrid=True),
                    yaxis=dict(gridcolor="#2a2a3a", tickprefix="$", showgrid=True),
                    showlegend=False,
                )

                st.plotly_chart(fig2, use_container_width=True)

    except Exception:
        st.markdown(
            '<div style="color:#6b6b8a;font-size:0.8rem">Stock data unavailable</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    col_dl, _ = st.columns([1, 3])

    with col_dl:
        try:
            pdf_bytes = generate_pdf_report(result)

            st.download_button(
                label="⬇ Download PDF Report",
                data=pdf_bytes,
                file_name=f"SentiQ_{ticker}_Q{quarter}{year}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        except Exception as e:
            st.caption(f"PDF export unavailable: {e}")