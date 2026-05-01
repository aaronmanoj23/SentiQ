import streamlit as st

st.set_page_config(
    page_title="SentiQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --accent: #00e5ff;
    --accent2: #7c3aed;
    --positive: #00d4aa;
    --negative: #ff4d6d;
    --neutral: #f59e0b;
    --text: #e8e8f0;
    --muted: #6b6b8a;
    --font-display: 'Syne', sans-serif;
    --font-mono: 'DM Mono', monospace;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
}

[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * { color: var(--text) !important; }

h1, h2, h3 {
    font-family: var(--font-display) !important;
    color: var(--text) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent2), #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: var(--font-mono) !important;
    font-weight: 500 !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.4) !important;
}

.stSelectbox > div, .stTextInput > div > div {
    background-color: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
}

.metric-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
}
.metric-label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.4rem;
}
.metric-value {
    font-family: var(--font-display);
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
}
.metric-sub {
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.2rem;
}

.sentiment-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.badge-positive { background: rgba(0,212,170,0.15); color: #00d4aa; border: 1px solid rgba(0,212,170,0.3); }
.badge-negative { background: rgba(255,77,109,0.15); color: #ff4d6d; border: 1px solid rgba(255,77,109,0.3); }
.badge-neutral  { background: rgba(245,158,11,0.15);  color: #f59e0b;  border: 1px solid rgba(245,158,11,0.3); }

.section-header {
    font-family: var(--font-display);
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

.risk-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--negative);
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
}

.evidence-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.82rem;
    font-style: italic;
    color: #9999bb;
}

.logo-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}
.company-logo {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    object-fit: contain;
    background: white;
    padding: 2px;
}

.drift-up { color: var(--negative); }
.drift-down { color: var(--positive); }
.drift-flat { color: var(--muted); }

.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.6rem 1.5rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

[data-testid="stExpander"] {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

div[data-testid="stMarkdownContainer"] p {
    color: var(--text) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.875rem !important;
    line-height: 1.7 !important;
}

.stAlert {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

.header-logo {
    font-family: var(--font-display);
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00e5ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.header-sub {
    font-size: 0.8rem;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: -0.5rem;
}

.stPlotlyChart { border-radius: 10px; overflow: hidden; }

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="header-logo">SentiQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">SEC Filing Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio(
        "Mode",
        ["Single Analysis", "Trend Analysis", "Compare Companies"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    TICKERS = {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META",
        "Goldman Sachs": "GS",
        "JPMorgan Chase": "JPM",
        "Morgan Stanley": "MS",
        "Tesla": "TSLA",
        "NVIDIA": "NVDA",
    }

    if mode == "Single Analysis":
        company = st.selectbox("Company", list(TICKERS.keys()))
        ticker = TICKERS[company]
        year = st.selectbox("Year", [2024, 2023, 2022], index=0)
        quarter = st.selectbox("Quarter", [1, 2, 3, 4], index=0)
        run_btn = st.button("Run Analysis", use_container_width=True)

    elif mode == "Trend Analysis":
        company = st.selectbox("Company", list(TICKERS.keys()))
        ticker = TICKERS[company]
        year = st.selectbox("Year", [2024, 2023, 2022], index=0)
        run_btn = st.button("Analyze Trend", use_container_width=True)

    elif mode == "Compare Companies":
        companies_selected = st.multiselect(
            "Select Companies (2–4)",
            list(TICKERS.keys()),
            default=["Apple", "Microsoft", "Google"]
        )
        year = st.selectbox("Year", [2024, 2023, 2022], index=0)
        quarter = st.selectbox("Quarter", [1, 2, 3, 4], index=0)
        run_btn = st.button("Compare", use_container_width=True)

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.7rem;color:#6b6b8a;line-height:1.6">'
        'Data: SEC EDGAR<br>'
        'Models: FinBERT + LM Lexicon<br>'
        'LLM: Claude Sonnet<br>'
        '</div>',
        unsafe_allow_html=True
    )

# ── Main content ─────────────────────────────────────────────────────────────
if mode == "Single Analysis":
    from pages.single import render_single
    render_single(ticker, company, year, quarter, run_btn if 'run_btn' in dir() else False)

elif mode == "Trend Analysis":
    from pages.trend import render_trend
    render_trend(ticker, company, year, run_btn if 'run_btn' in dir() else False)

elif mode == "Compare Companies":
    from pages.compare import render_compare
    tickers_selected = {c: TICKERS[c] for c in companies_selected} if 'companies_selected' in dir() else {}
    render_compare(tickers_selected, year, quarter, run_btn if 'run_btn' in dir() else False)
