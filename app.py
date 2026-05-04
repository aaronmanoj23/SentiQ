import streamlit as st
import requests
import yfinance as yf
import datetime

st.set_page_config(
    page_title="SentiQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

POPULAR_TICKERS = {
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


def normalize_ticker(ticker):
    return ticker.strip().upper()


def get_company_from_sec(query):
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {
            "User-Agent": "SentiQ student project contact@example.com"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        query_clean = query.strip()
        query_upper = query_clean.upper()
        query_lower = query_clean.lower()

        exact_matches = []
        partial_matches = []

        for item in data.values():
            ticker = item["ticker"].upper()
            company = item["title"]
            company_lower = company.lower()

            result = {
                "ticker": ticker,
                "company": company,
                "cik": str(item["cik_str"]).zfill(10),
            }

            if query_upper == ticker:
                exact_matches.append(result)

            elif query_lower == company_lower:
                exact_matches.append(result)

            elif query_lower in company_lower:
                partial_matches.append(result)

        if exact_matches:
            return exact_matches[0]

        if partial_matches:
            return partial_matches[0]

        return None

    except Exception:
        return None


def company_picker(label="Company or Ticker"):
    st.markdown("#### Select or enter company")

    shortcut = st.selectbox(
        "Popular company shortcut",
        ["Custom company or ticker"] + list(POPULAR_TICKERS.keys())
    )

    if shortcut == "Custom company or ticker":
        user_input = st.text_input(
            label,
            placeholder="Example: Walmart, Costco, NVIDIA, AAPL, MSFT"
        )
        query = user_input.strip()
    else:
        query = POPULAR_TICKERS[shortcut]

    company_info = None

    if query:
        company_info = get_company_from_sec(query)

        if company_info:
            st.success(
                f"Selected: {company_info['company']} ({company_info['ticker']})"
            )
            return (
                company_info["ticker"],
                company_info["company"],
                company_info["cik"],
            )
        else:
            st.warning(
                "Company or ticker not found in SEC company list. Please check the spelling."
            )

    return None, None, None


def get_ipo_year_from_yahoo(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        ipo_year = info.get("ipoYear", None)

        if ipo_year:
            return int(ipo_year)

        first_trade = info.get("firstTradeDateEpochUtc", None)

        if first_trade:
            first_trade_date = datetime.datetime.fromtimestamp(first_trade)
            return first_trade_date.year

        return 2000

    except Exception:
        return 2000


def get_year_options_from_ipo(ticker):
    ipo_year = get_ipo_year_from_yahoo(ticker)
    current_year = datetime.datetime.now().year

    if ipo_year > current_year:
        ipo_year = 2000

    return list(range(current_year, ipo_year - 1, -1))


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

.header-logo {
    font-family: var(--font-display);
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00e5ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
}

.header-sub {
    font-size: 0.8rem;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: -0.5rem;
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

.badge-positive {
    background: rgba(0,212,170,0.15);
    color: #00d4aa;
    border: 1px solid rgba(0,212,170,0.3);
}

.badge-negative {
    background: rgba(255,77,109,0.15);
    color: #ff4d6d;
    border: 1px solid rgba(255,77,109,0.3);
}

.badge-neutral {
    background: rgba(245,158,11,0.15);
    color: #f59e0b;
    border: 1px solid rgba(245,158,11,0.3);
}

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

.drift-up { color: var(--negative); }
.drift-down { color: var(--positive); }
.drift-flat { color: var(--muted); }

.stPlotlyChart {
    border-radius: 10px;
    overflow: hidden;
}

#MainMenu, footer {
    visibility: hidden;
}

header {
    visibility: visible;
}
</style>
""", unsafe_allow_html=True)


with st.sidebar:
    st.markdown('<div class="header-logo">SentiQ</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">SEC Filing Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio(
        "Mode",
        [
            "Single Analysis",
            "Trend Analysis",
            "Compare Companies",
            "Upload Filing"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    ticker = None
    company = None
    cik = None
    run_btn = False

    if mode == "Single Analysis":
        ticker, company, cik = company_picker()

        if ticker:
            year_options = get_year_options_from_ipo(ticker)
        else:
            year_options = [2024, 2023, 2022]

        year = st.selectbox("Year", year_options, index=0)
        quarter = st.selectbox("Quarter", [1, 2, 3, 4], index=0)

        run_btn = st.button(
            "Run Analysis",
            use_container_width=True,
            disabled=not ticker
        )

    elif mode == "Trend Analysis":
        ticker, company, cik = company_picker()

        if ticker:
            year_options = get_year_options_from_ipo(ticker)
        else:
            year_options = [2024, 2023, 2022]

        year = st.selectbox("Year", year_options, index=0)

        run_btn = st.button(
            "Analyze Trend",
            use_container_width=True,
            disabled=not ticker
        )

    elif mode == "Compare Companies":
        saved = st.session_state.get("saved_filings", {})

        saved_options = [
            f"📄 {v['company']} (Q{v['quarter']} {v['year']})"
            for v in saved.values()
        ]

        st.markdown("#### Enter companies or tickers to compare")

        ticker_text = st.text_input(
            "Companies or Tickers",
            value="Apple, Microsoft, Google",
            placeholder="Example: Walmart, Costco, Amazon or WMT, COST, AMZN"
        )

        typed_tickers = [
            t.strip()
            for t in ticker_text.split(",")
            if t.strip()
        ]

        uploaded_selected_labels = st.multiselect(
            "Optional uploaded filings",
            saved_options
        )

        current_year = datetime.datetime.now().year
        year_options = list(range(current_year, 1995 - 1, -1))

        year = st.selectbox("Year", year_options, index=0)
        quarter = st.selectbox("Quarter", [1, 2, 3, 4], index=0)

        run_btn = st.button(
            "Compare",
            use_container_width=True,
            disabled=len(typed_tickers) + len(uploaded_selected_labels) < 2
        )

    elif mode == "Upload Filing":
        saved = st.session_state.get("saved_filings", {})

        if saved:
            st.markdown(
                f'<div style="font-size:0.75rem;color:#00d4aa;margin-bottom:0.5rem">✓ {len(saved)} filing(s) saved</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    st.markdown(
        '<div style="font-size:0.7rem;color:#6b6b8a;line-height:1.6">'
        'Data: SEC EDGAR<br>'
        'Models: FinBERT + LM Lexicon<br>'
        'LLM: Claude Sonnet<br>'
        '</div>',
        unsafe_allow_html=True
    )


if mode == "Single Analysis":
    from views.single import render_single

    if ticker:
        render_single(ticker, company, year, quarter, run_btn)
    else:
        st.info("Enter a valid U.S. company name or ticker to begin.")

elif mode == "Trend Analysis":
    from views.trend import render_trend

    if ticker:
        render_trend(ticker, company, year, run_btn)
    else:
        st.info("Enter a valid U.S. company name or ticker to begin.")

elif mode == "Compare Companies":
    from views.compare import render_compare

    saved = st.session_state.get("saved_filings", {})

    tickers_selected = {}
    uploaded_selected = {}

    for t in typed_tickers:
        info = get_company_from_sec(t)

        if info:
            tickers_selected[info["company"]] = info["ticker"]
        else:
            tickers_selected[t] = t

    for selected_label in uploaded_selected_labels:
        for key, filing in saved.items():
            label = f"📄 {filing['company']} (Q{filing['quarter']} {filing['year']})"
            if label == selected_label:
                uploaded_selected[key] = filing
                break

    render_compare(
        tickers_selected,
        year,
        quarter,
        run_btn,
        uploaded_selected
    )

elif mode == "Upload Filing":
    from views.upload import render_upload

    render_upload()