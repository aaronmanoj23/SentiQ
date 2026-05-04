"""
Multi-company comparison page: same quarter, multiple tickers side by side.
"""

import streamlit as st
import plotly.graph_objects as go
import sys
import os
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import full_analysis


PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#e8e8f0", size=11),
    margin=dict(l=20, r=20, t=40, b=20),
)

SENTIMENT_COLORS = {"POSITIVE": "#00d4aa", "NEGATIVE": "#ff4d6d", "NEUTRAL": "#f59e0b"}
COMPANY_COLORS = ["#00e5ff", "#7c3aed", "#f59e0b", "#ff4d6d", "#00d4aa", "#a78bfa"]
COMPANY_FILL_COLORS = [
    "rgba(0,229,255,0.1)",
    "rgba(124,58,237,0.1)",
    "rgba(245,158,11,0.1)",
    "rgba(255,77,109,0.1)",
    "rgba(0,212,170,0.1)",
    "rgba(167,139,250,0.1)",
]


def html_safe(value):
    return escape(str(value or ""))


def safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def render_compare(tickers_dict: dict, year: int, quarter: int, run: bool, uploaded_filings: dict = None):
    uploaded_filings = uploaded_filings or {}

    st.markdown("## Company Comparison")
    st.markdown(
        f'<div style="color:#6b6b8a;font-size:0.8rem;letter-spacing:0.15em">Q{quarter} {year} · SIDE-BY-SIDE ANALYSIS</div>',
        unsafe_allow_html=True,
    )

    total_selections = len(tickers_dict) + len(uploaded_filings)

    if not run or total_selections == 0:
        st.markdown(
            """
            <div style="text-align:center;padding:4rem 2rem;color:#6b6b8a">
                <div style="font-size:3rem;margin-bottom:1rem">🔍</div>
                <div style="font-family:'Syne',sans-serif;font-size:1.2rem;margin-bottom:0.5rem;color:#e8e8f0">Compare sentiment across companies</div>
                <div style="font-size:0.85rem">Select EDGAR companies or uploaded filings — mix and match freely</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if total_selections < 2:
        st.warning("Select at least 2 companies to compare.")
        return

    results = {}

    if tickers_dict:
        progress = st.progress(0, text="Fetching filings...")

        for i, (company, ticker) in enumerate(tickers_dict.items()):
            safe_company = html_safe(company)
            progress.progress(i / len(tickers_dict), text=f"Analyzing {company}...")

            try:
                r = full_analysis(ticker, company, year, quarter)
                results[company] = r
            except Exception as e:
                st.warning(f"{safe_company} failed: {e}")

        progress.progress(1.0, text="Complete")
        progress.empty()

    for key, filing in uploaded_filings.items():
        display_name = f"{filing.get('company', 'Uploaded Filing')} (uploaded)"
        results[display_name] = filing

    if not results:
        st.error("No results.")
        return

    if len(results) > 6:
        st.warning("Showing first 6 companies only.")
        results = dict(list(results.items())[:6])

    st.markdown("---")
    cols = st.columns(len(results))

    for col, (company, result) in zip(cols, results.items()):
        ticker = result.get("ticker", "")
        overall = result.get("overall_sentiment", {})

        label = str(overall.get("label", "NEUTRAL")).upper()
        conf = safe_float(overall.get("confidence"))
        color = SENTIMENT_COLORS.get(label, "#f59e0b")

        safe_ticker = html_safe(ticker)
        logo_url = f"https://logo.clearbit.com/{_get_domain(ticker)}"

        with col:
            st.markdown(
                f"""
                <div class="metric-card" style="text-align:center">
                    <img src="{logo_url}" style="width:40px;height:40px;border-radius:8px;object-fit:contain;background:white;padding:3px;margin-bottom:8px" onerror="this.style.display='none'">
                    <div class="metric-label">{safe_ticker}</div>
                    <div class="metric-value" style="color:{color};font-size:1.3rem">{label}</div>
                    <div class="metric-sub">{conf:.0%} confidence</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">SENTIMENT COMPARISON</div>', unsafe_allow_html=True)

    col_bar, col_radar = st.columns([3, 2])

    with col_bar:
        fig = go.Figure()

        for i, (company, result) in enumerate(results.items()):
            overall = result.get("overall_sentiment", {})
            color = COMPANY_COLORS[i % len(COMPANY_COLORS)]

            fig.add_trace(
                go.Bar(
                    name=html_safe(company),
                    x=["Positive", "Negative", "Neutral"],
                    y=[
                        safe_float(overall.get("positive")),
                        safe_float(overall.get("negative")),
                        safe_float(overall.get("neutral")),
                    ],
                    marker_color=color,
                    marker_line=dict(color="rgba(255,255,255,0.2)", width=1),
                    opacity=0.85,
                )
            )

        fig.update_layout(
            **PLOTLY_THEME,
            barmode="group",
            height=300,
            yaxis=dict(tickformat=".0%", gridcolor="#2a2a3a", range=[0, 1]),
            xaxis=dict(gridcolor="#2a2a3a"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                bgcolor="rgba(0,0,0,0)",
            ),
            bargap=0.2,
            bargroupgap=0.05,
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_radar:
        categories = ["Positive", "Negative", "Neutral", "Confidence"]
        fig2 = go.Figure()

        for i, (company, result) in enumerate(results.items()):
            overall = result.get("overall_sentiment", {})

            values = [
                safe_float(overall.get("positive")),
                safe_float(overall.get("negative")),
                safe_float(overall.get("neutral")),
                safe_float(overall.get("confidence")),
            ]

            values.append(values[0])
            cats = categories + [categories[0]]

            color = COMPANY_COLORS[i % len(COMPANY_COLORS)]
            fill_color = COMPANY_FILL_COLORS[i % len(COMPANY_FILL_COLORS)]

            fig2.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=cats,
                    fill="toself",
                    name=html_safe(company),
                    line=dict(color=color, width=2),
                    fillcolor=fill_color,
                    opacity=0.8,
                )
            )

        fig2.update_layout(
            **PLOTLY_THEME,
            height=300,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickformat=".0%",
                    gridcolor="#2a2a3a",
                    linecolor="#2a2a3a",
                    tickfont=dict(size=8),
                ),
                angularaxis=dict(gridcolor="#2a2a3a", linecolor="#2a2a3a"),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                bgcolor="rgba(0,0,0,0)",
            ),
        )

        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-header">RISK SIGNALS BY COMPANY</div>', unsafe_allow_html=True)

    risk_cols = st.columns(len(results))

    for col, (company, result) in zip(risk_cols, results.items()):
        ticker = result.get("ticker", "")
        overall = result.get("overall_sentiment", {})
        label = str(overall.get("label", "NEUTRAL")).upper()
        color = SENTIMENT_COLORS.get(label, "#f59e0b")

        safe_company = html_safe(company)
        safe_ticker = html_safe(ticker)

        with col:
            st.markdown(
                f'<div style="font-family:\'Syne\',sans-serif;font-weight:700;margin-bottom:0.75rem;color:{color}">{safe_company} ({safe_ticker})</div>',
                unsafe_allow_html=True,
            )

            risks = result.get("llm_summary", {}).get("keyRiskSignals", [])[:3]

            for risk in risks:
                s = risk.get("sentiment", {})
                s_label = str(s.get("label", "NEUTRAL")).upper()
                border = SENTIMENT_COLORS.get(s_label, "#f59e0b")
                conf_val = safe_float(s.get("confidence"))
                risk_text = html_safe(risk.get("risk", ""))

                st.markdown(
                    f"""
                    <div style="background:#1a1a24;border-left:3px solid {border};border-radius:4px;padding:0.6rem 0.8rem;margin-bottom:0.4rem;font-size:0.78rem">
                        <div style="color:#e8e8f0;margin-bottom:3px">{risk_text}</div>
                        <div style="color:{border};font-size:0.7rem">{s_label} · {conf_val:.0%}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.markdown('<div class="section-header">RANKINGS</div>', unsafe_allow_html=True)

    ranked = sorted(
        results.items(),
        key=lambda x: safe_float(x[1].get("overall_sentiment", {}).get("positive")),
        reverse=True,
    )

    rank_data = []

    for rank, (company, result) in enumerate(ranked, 1):
        overall = result.get("overall_sentiment", {})

        label = str(overall.get("label", "NEUTRAL")).upper()
        color = SENTIMENT_COLORS.get(label, "#f59e0b")

        medal = ["🥇", "🥈", "🥉", "4️⃣"][rank - 1] if rank <= 4 else str(rank)

        pos = safe_float(overall.get("positive"))
        neg = safe_float(overall.get("negative"))
        confidence = safe_float(overall.get("confidence"))

        spread = pos - neg
        spread_color = "#00d4aa" if spread > 0 else "#ff4d6d"
        spread_sign = "+" if spread > 0 else ""

        rank_data.append(
            {
                "rank": medal,
                "company": html_safe(company),
                "ticker": html_safe(result.get("ticker", "")),
                "label": label,
                "color": color,
                "positive": pos,
                "negative": neg,
                "confidence": confidence,
                "spread": spread,
                "spread_color": spread_color,
                "spread_sign": spread_sign,
            }
        )

    header_cols = st.columns([0.5, 2, 1, 1, 1, 1, 1])
    headers = ["", "Company", "Verdict", "Positive", "Negative", "Confidence", "Spread"]

    for col, h in zip(header_cols, headers):
        col.markdown(
            f'<div style="font-size:0.7rem;color:#6b6b8a;text-transform:uppercase;letter-spacing:0.1em;padding-bottom:4px;border-bottom:1px solid #2a2a3a">{h}</div>',
            unsafe_allow_html=True,
        )

    for row in rank_data:
        cols = st.columns([0.5, 2, 1, 1, 1, 1, 1])

        cols[0].markdown(
            f'<div style="padding:8px 0;font-size:1.1rem">{row["rank"]}</div>',
            unsafe_allow_html=True,
        )
        cols[1].markdown(
            f'<div style="padding:8px 0;font-weight:500">{row["company"]} <span style="color:#6b6b8a">({row["ticker"]})</span></div>',
            unsafe_allow_html=True,
        )
        cols[2].markdown(
            f'<div style="padding:8px 0;color:{row["color"]};font-weight:500">{row["label"]}</div>',
            unsafe_allow_html=True,
        )
        cols[3].markdown(
            f'<div style="padding:8px 0;color:#00d4aa">{row["positive"]:.1%}</div>',
            unsafe_allow_html=True,
        )
        cols[4].markdown(
            f'<div style="padding:8px 0;color:#ff4d6d">{row["negative"]:.1%}</div>',
            unsafe_allow_html=True,
        )
        cols[5].markdown(
            f'<div style="padding:8px 0">{row["confidence"]:.1%}</div>',
            unsafe_allow_html=True,
        )
        cols[6].markdown(
            f'<div style="padding:8px 0;color:{row["spread_color"]}">{row["spread_sign"]}{row["spread"]:.1%}</div>',
            unsafe_allow_html=True,
        )


def _get_domain(ticker: str) -> str:
    ticker = str(ticker or "").upper()

    domains = {
        "AAPL": "apple.com",
        "MSFT": "microsoft.com",
        "GOOGL": "google.com",
        "AMZN": "amazon.com",
        "META": "meta.com",
        "GS": "goldmansachs.com",
        "JPM": "jpmorganchase.com",
        "MS": "morganstanley.com",
        "TSLA": "tesla.com",
        "NVDA": "nvidia.com",
    }

    return domains.get(ticker, f"{ticker.lower()}.com")