"""
Trend analysis page: sentiment across all 4 quarters of a year + stock price overlay.
"""

import streamlit as st
import plotly.graph_objects as go
import sys
import os
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import full_analysis
from utils.stocks import get_stock_data, get_quarterly_returns, correlate_sentiment_price


PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#e8e8f0", size=11),
    margin=dict(l=20, r=20, t=40, b=20),
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


def render_trend(ticker: str, company: str, year: int, run: bool):
    safe_company = html_safe(company)
    safe_ticker = html_safe(ticker)

    st.markdown(f"## {safe_company} — Sentiment Trend")
    st.markdown(
        f'<div style="color:#6b6b8a;font-size:0.8rem;letter-spacing:0.15em">ALL QUARTERS {year} · TREND ANALYSIS</div>',
        unsafe_allow_html=True,
    )

    if not run:
        st.markdown(
            """
            <div style="text-align:center;padding:4rem 2rem;color:#6b6b8a">
                <div style="font-size:3rem;margin-bottom:1rem">📈</div>
                <div style="font-family:'Syne',sans-serif;font-size:1.2rem;margin-bottom:0.5rem;color:#e8e8f0">Track sentiment across all 4 quarters</div>
                <div style="font-size:0.85rem">Compare tone shifts with stock price movement — see if filings predict returns</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    results = {}
    progress = st.progress(0, text="Analyzing Q1...")

    for i, q in enumerate([1, 2, 3, 4]):
        progress.progress(i / 4, text=f"Analyzing Q{q} {year}...")

        try:
            r = full_analysis(ticker, company, year, q)
            results[q] = r
        except Exception as e:
            st.warning(f"Q{q} failed: {e}")

    progress.progress(1.0, text="Complete")
    progress.empty()

    if not results:
        st.error("No data retrieved.")
        return

    quarters = sorted(results.keys())
    q_labels = [f"Q{q}" for q in quarters]

    pos_scores = [
        safe_float(results[q].get("overall_sentiment", {}).get("positive"))
        for q in quarters
    ]
    neg_scores = [
        safe_float(results[q].get("overall_sentiment", {}).get("negative"))
        for q in quarters
    ]
    conf_scores = [
        safe_float(results[q].get("overall_sentiment", {}).get("confidence"))
        for q in quarters
    ]

    drift = 0.0
    drift_pct = 0.0
    drift_direction = "flat"
    drift_color = "#f59e0b"

    if len(pos_scores) >= 2:
        drift = pos_scores[-1] - pos_scores[0]
        drift_pct = drift * 100

        if drift > 0:
            drift_direction = "more positive"
            drift_color = "#00d4aa"
        elif drift < 0:
            drift_direction = "more negative"
            drift_color = "#ff4d6d"
        else:
            drift_direction = "flat"
            drift_color = "#f59e0b"

    st.markdown("---")
    d1, d2, d3 = st.columns(3)

    with d1:
        best_q = quarters[pos_scores.index(max(pos_scores))]
        best_label = str(
            results[best_q].get("overall_sentiment", {}).get("label", "NEUTRAL")
        ).upper()

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Most Positive Quarter</div>
                <div class="metric-value" style="color:#00d4aa">Q{best_q}</div>
                <div class="metric-sub">{best_label} · {max(pos_scores):.1%} positive</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d2:
        worst_q = quarters[neg_scores.index(max(neg_scores))]

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Most Negative Quarter</div>
                <div class="metric-value" style="color:#ff4d6d">Q{worst_q}</div>
                <div class="metric-sub">{max(neg_scores):.1%} negative sentiment</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d3:
        sign = "+" if drift > 0 else ""

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Full Year Drift</div>
                <div class="metric-value" style="color:{drift_color}">{sign}{drift_pct:.1f}pp</div>
                <div class="metric-sub">Tone shifted {drift_direction}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-header">SENTIMENT VS STOCK PRICE</div>',
        unsafe_allow_html=True,
    )

    try:
        price_df = get_stock_data(ticker, year)
        price_returns = get_quarterly_returns(ticker, year)
        has_prices = price_df is not None and not price_df.empty
    except Exception:
        price_df = None
        price_returns = {}
        has_prices = False

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=q_labels,
            y=pos_scores,
            mode="lines+markers+text",
            name="Positive",
            line=dict(color="#00d4aa", width=2.5),
            marker=dict(size=10, color="#00d4aa", line=dict(color="white", width=2)),
            text=[f"{v:.0%}" for v in pos_scores],
            textposition="top center",
            textfont=dict(size=10, color="#00d4aa"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=q_labels,
            y=neg_scores,
            mode="lines+markers+text",
            name="Negative",
            line=dict(color="#ff4d6d", width=2.5, dash="dot"),
            marker=dict(size=10, color="#ff4d6d", line=dict(color="white", width=2)),
            text=[f"{v:.0%}" for v in neg_scores],
            textposition="bottom center",
            textfont=dict(size=10, color="#ff4d6d"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=q_labels,
            y=conf_scores,
            mode="lines+markers",
            name="Confidence",
            line=dict(color="#7c3aed", width=1.5, dash="dash"),
            marker=dict(size=6, color="#7c3aed"),
            opacity=0.7,
        )
    )

    fig.update_layout(
        **PLOTLY_THEME,
        height=350,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10),
        ),
        yaxis=dict(tickformat=".0%", gridcolor="#2a2a3a", range=[0, 1]),
        xaxis=dict(gridcolor="#2a2a3a"),
    )

    st.plotly_chart(fig, use_container_width=True)

    if has_prices and price_df is not None and not price_df.empty:
        st.markdown(
            '<div class="section-header" style="margin-top:1rem">STOCK PRICE</div>',
            unsafe_allow_html=True,
        )

        fig2 = go.Figure()

        fig2.add_trace(
            go.Scatter(
                x=price_df["Date"],
                y=price_df["Close"],
                mode="lines",
                name=f"{safe_ticker} Price",
                line=dict(color="#00e5ff", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,229,255,0.05)",
            )
        )

        fig2.update_layout(
            **PLOTLY_THEME,
            height=250,
            yaxis=dict(tickprefix="$", gridcolor="#2a2a3a"),
            xaxis=dict(gridcolor="#2a2a3a"),
            showlegend=False,
        )

        st.plotly_chart(fig2, use_container_width=True)

    if price_returns:
        sentiment_pairs = [
            (q, safe_float(results[q].get("overall_sentiment", {}).get("positive")))
            for q in quarters
        ]

        corr = correlate_sentiment_price(sentiment_pairs, price_returns)

        if corr.get("correlation") is not None:
            corr_val = safe_float(corr.get("correlation"))
            r_squared = corr_val ** 2
            corr_color = "#00d4aa" if corr_val > 0 else "#ff4d6d"
            interpretation = html_safe(corr.get("interpretation", ""))

            st.markdown(
                '<div class="section-header">SENTIMENT PRICE CORRELATION</div>',
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Pearson Correlation</div>
                        <div class="metric-value" style="color:{corr_color}">{corr_val:+.3f}</div>
                        <div class="metric-sub">{interpretation}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Predictive Power</div>
                        <div class="metric-value">{r_squared * 100:.0f}%</div>
                        <div class="metric-sub">of price return variation explained</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c3:
                if corr_val > 0:
                    direction_text = "Positive sentiment → price up"
                elif corr_val < 0:
                    direction_text = "Positive sentiment → price down"
                else:
                    direction_text = "No clear direction"

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Direction</div>
                        <div class="metric-value" style="font-size:1rem;margin-top:0.3rem">{direction_text}</div>
                        <div class="metric-sub">for {safe_ticker} in {year}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.markdown(
        '<div class="section-header">QUARTER BREAKDOWN</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(quarters))

    for col, q in zip(cols, quarters):
        r = results[q]
        overall = r.get("overall_sentiment", {})

        label = str(overall.get("label", "NEUTRAL")).upper()
        color = SENTIMENT_COLORS.get(label, "#f59e0b")
        confidence = safe_float(overall.get("confidence"))

        tone = html_safe(r.get("llm_summary", {}).get("overallTone", "")[:80])
        price_ret = price_returns.get(q)

        with col:
            ret_html = ""

            if price_ret is not None:
                price_ret = safe_float(price_ret)
                ret_color = "#00d4aa" if price_ret >= 0 else "#ff4d6d"
                ret_sign = "+" if price_ret >= 0 else ""

                ret_html = (
                    f'<div class="metric-sub" style="color:{ret_color}">'
                    f"Stock: {ret_sign}{price_ret:.1f}%</div>"
                )

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Q{q} {year}</div>
                    <div class="metric-value" style="color:{color};font-size:1.2rem">{label}</div>
                    <div class="metric-sub">{confidence:.0%} confidence</div>
                    {ret_html}
                    <div style="font-size:0.72rem;color:#6b6b8a;margin-top:8px;line-height:1.5">{tone}...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )