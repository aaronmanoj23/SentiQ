"""
Single company, single quarter analysis page.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import full_analysis
from utils.stocks import get_current_price, get_quarterly_returns
from utils.pdf_export import generate_pdf_report


PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#e8e8f0", size=11),
    margin=dict(l=20, r=20, t=30, b=20),
)

SENTIMENT_COLORS = {"POSITIVE": "#00d4aa", "NEGATIVE": "#ff4d6d", "NEUTRAL": "#f59e0b"}


def badge(label: str) -> str:
    cls = f"badge-{label.lower()}"
    return f'<span class="sentiment-badge {cls}">{label}</span>'


def confidence_bar(score: float, label: str) -> str:
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
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## {company}")
        st.markdown(f'<div style="color:#6b6b8a;font-size:0.8rem;letter-spacing:0.15em">Q{quarter} {year} · 10-Q ANALYSIS</div>', unsafe_allow_html=True)
    with col2:
        price_data = get_current_price(ticker)
        if price_data:
            delta_color = "#00d4aa" if price_data["change_pct"] >= 0 else "#ff4d6d"
            delta_sign = "+" if price_data["change_pct"] >= 0 else ""
            st.markdown(f"""
            <div class="metric-card" style="text-align:right">
                <div class="metric-label">{ticker} · Live Price</div>
                <div class="metric-value">${price_data['price']:,.2f}</div>
                <div class="metric-sub" style="color:{delta_color}">{delta_sign}{price_data['change_pct']:.2f}% today</div>
            </div>""", unsafe_allow_html=True)

    if not run:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:#6b6b8a">
            <div style="font-size:3rem;margin-bottom:1rem">📊</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.2rem;margin-bottom:0.5rem;color:#e8e8f0">Select a company and run analysis</div>
            <div style="font-size:0.85rem">SentiQ fetches live SEC filings and scores them with a FinBERT + LM ensemble</div>
        </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner(f"Fetching {ticker} Q{quarter} {year} 10-Q filing..."):
        try:
            result = full_analysis(ticker, company, year, quarter)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return

    overall = result["overall_sentiment"]
    llm = result["llm_summary"]

    # ── Top metrics row ──────────────────────────────────────────────────────
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    label = overall.get("label", "NEUTRAL")
    conf  = overall.get("confidence", 0)
    pos   = overall.get("positive", 0)
    neg   = overall.get("negative", 0)

    with m1:
        color = SENTIMENT_COLORS.get(label, "#f59e0b")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Overall Verdict</div>
            <div class="metric-value" style="color:{color}">{label}</div>
            <div class="metric-sub">Ensemble confidence</div>
        </div>""", unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Confidence</div>
            <div class="metric-value">{conf:.1%}</div>
            <div class="metric-sub">FinBERT + LM ensemble</div>
        </div>""", unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Positive Signal</div>
            <div class="metric-value" style="color:#00d4aa">{pos:.1%}</div>
            <div class="metric-sub">of filing language</div>
        </div>""", unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Negative Signal</div>
            <div class="metric-value" style="color:#ff4d6d">{neg:.1%}</div>
            <div class="metric-sub">of filing language</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sentiment breakdown chart ────────────────────────────────────────────
    col_chart, col_summary = st.columns([1, 1])

    with col_chart:
        st.markdown('<div class="section-header">SENTIMENT BREAKDOWN</div>', unsafe_allow_html=True)
        
        fb = overall.get("finbert", {})
        lm = overall.get("lm", {})
        
        fig = go.Figure()
        categories = ["Positive", "Negative", "Neutral"]

        fig.add_trace(go.Bar(
            name="FinBERT",
            x=categories,
            y=[fb.get("positive",0), fb.get("negative",0), fb.get("neutral",0)],
            marker_color=["rgba(0,212,170,0.8)", "rgba(255,77,109,0.8)", "rgba(245,158,11,0.8)"],
        ))
        fig.add_trace(go.Bar(
            name="LM Lexicon",
            x=categories,
            y=[lm.get("positive",0), lm.get("negative",0), lm.get("neutral",0)],
            marker_color=["rgba(0,212,170,0.4)", "rgba(255,77,109,0.4)", "rgba(245,158,11,0.4)"],
        ))
        fig.add_trace(go.Bar(
            name="Ensemble",
            x=categories,
            y=[overall.get("positive",0), overall.get("negative",0), overall.get("neutral",0)],
            marker_color=["#00d4aa","#ff4d6d","#f59e0b"],
            marker_line=dict(color="white", width=1),
        ))

        fig.update_layout(
            **PLOTLY_THEME,
            barmode="group",
            bargap=0.2,
            bargroupgap=0.05,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                font=dict(size=10), bgcolor="rgba(0,0,0,0)"
            ),
            yaxis=dict(
                tickformat=".0%", gridcolor="#2a2a3a",
                range=[0, 1], tickfont=dict(size=10)
            ),
            xaxis=dict(gridcolor="#2a2a3a"),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_summary:
        st.markdown('<div class="section-header">LLM SUMMARY</div>', unsafe_allow_html=True)
        tone = llm.get("overallTone", "")
        if tone:
            st.markdown(f'<div style="font-size:0.9rem;color:#e8e8f0;line-height:1.6;margin-bottom:1rem"><em>{tone}</em></div>', unsafe_allow_html=True)
        
        takeaway = llm.get("analystTakeaway", "")
        if takeaway:
            st.markdown(f'<div style="font-size:0.82rem;color:#9999bb;line-height:1.7">{takeaway}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Risk signals + Notable changes ──────────────────────────────────────
    col_risks, col_changes = st.columns([1, 1])

    with col_risks:
        st.markdown('<div class="section-header">KEY RISK SIGNALS</div>', unsafe_allow_html=True)
        risks = llm.get("keyRiskSignals", [])
        for item in risks:
            s = item.get("sentiment", {})
            s_label = s.get("label", "NEUTRAL")
            conf_val = s.get("confidence", 0)
            border_color = SENTIMENT_COLORS.get(s_label, "#f59e0b")
            st.markdown(f"""
            <div class="risk-item" style="border-left-color:{border_color}">
                <div style="font-weight:500;margin-bottom:4px">{item.get('risk','')}</div>
                <div style="font-size:0.78rem;color:#9999bb;margin-bottom:6px">{item.get('detail','')}</div>
                {confidence_bar(conf_val, s_label)}
            </div>""", unsafe_allow_html=True)

    with col_changes:
        st.markdown('<div class="section-header">NOTABLE CHANGES</div>', unsafe_allow_html=True)
        changes = llm.get("notableChanges", [])
        for item in changes:
            direction = item.get("direction", "neutral").upper()
            magnitude = item.get("magnitude", "")
            color = SENTIMENT_COLORS.get(direction, "#f59e0b")
            icon = "▲" if direction == "POSITIVE" else "▼" if direction == "NEGATIVE" else "●"
            s = item.get("sentiment", {})
            conf_val = s.get("confidence", 0)
            st.markdown(f"""
            <div class="risk-item" style="border-left-color:{color}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                    <span style="font-weight:500">{item.get('change','')}</span>
                    <span style="color:{color};font-size:0.8rem">{icon} {magnitude}</span>
                </div>
                {confidence_bar(conf_val, direction)}
            </div>""", unsafe_allow_html=True)

    # ── Evidence citations ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">EVIDENCE CITATIONS</div>', unsafe_allow_html=True)
    citations = llm.get("evidenceCitations", [])

    for i, item in enumerate(citations, 1):
        s = item.get("sentiment", {})
        s_label = s.get("label", "NEUTRAL")
        conf_val = s.get("confidence", 0)
        color = SENTIMENT_COLORS.get(s_label, "#f59e0b")
        
        with st.expander(f"[{i}] {item.get('significance', 'Evidence')[:80]}...", expanded=False):
            st.markdown(f"""
            <div style="padding:0.5rem">
                <div class="evidence-item">"{item.get('text', '')}"</div>
                <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
                    <span class="sentiment-badge badge-{s_label.lower()}">{s_label}</span>
                    <span style="font-size:0.78rem;color:#9999bb">Confidence: {conf_val:.0%}</span>
                </div>
                {confidence_bar(conf_val, s_label)}
            </div>
            """, unsafe_allow_html=True)

    # ── Stock price + correlation ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">STOCK CONTEXT</div>', unsafe_allow_html=True)
    
    try:
        from utils.stocks import get_stock_data
        price_df = get_stock_data(ticker, year)
        if price_df is not None and not price_df.empty:
            q_months = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
            q_data = price_df[price_df["Month"].isin(q_months[quarter])]
            
            if not q_data.empty:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=q_data["Date"], y=q_data["Close"],
                    mode="lines+markers",
                    line=dict(color="#7c3aed", width=2),
                    marker=dict(size=6, color="#00e5ff"),
                    fill="tozeroy",
                    fillcolor="rgba(124,58,237,0.08)",
                    name=f"{ticker} Close"
                ))
                
                # Add sentiment annotation
                mid_idx = len(q_data) // 2
                if mid_idx < len(q_data):
                    mid_date = q_data.iloc[mid_idx]["Date"]
                    mid_price = q_data.iloc[mid_idx]["Close"]
                    fig2.add_annotation(
                        x=mid_date, y=mid_price,
                        text=f"  {label} ({conf:.0%})",
                        showarrow=True, arrowhead=2,
                        font=dict(color=SENTIMENT_COLORS.get(label, "#f59e0b"), size=11),
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
        st.markdown('<div style="color:#6b6b8a;font-size:0.8rem">Stock data unavailable</div>', unsafe_allow_html=True)

    # ── PDF Export ───────────────────────────────────────────────────────────
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
