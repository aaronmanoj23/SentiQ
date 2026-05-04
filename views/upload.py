"""
Upload Analysis page.
Upload any 10-Q PDF or text file -> get full SentiQ analysis -> save to session for comparison.
"""

import streamlit as st
import pdfplumber
import io
import sys
import os
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import run_claude_analysis, ensemble_score
from utils.pdf_export import generate_pdf_report


SENTIMENT_COLORS = {"POSITIVE": "#00d4aa", "NEGATIVE": "#ff4d6d", "NEUTRAL": "#f59e0b"}


def html_safe(value):
    return escape(str(value or ""))


def safe_float(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:30]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"PDF extraction error: {e}")

    return text


def extract_text_from_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def confidence_bar(score: float, label: str) -> str:
    score = safe_float(score)
    score = max(0, min(score, 1))

    label = str(label or "NEUTRAL").upper()
    color = SENTIMENT_COLORS.get(label, "#f59e0b")
    pct = int(score * 100)

    return f"""
    <div style="display:flex;align-items:center;gap:8px;margin:2px 0">
        <div style="flex:1;background:#1a1a24;border-radius:3px;height:6px;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:3px"></div>
        </div>
        <span style="font-size:0.75rem;color:#9999bb;min-width:36px">{pct}%</span>
    </div>"""


def render_upload():
    if "saved_filings" not in st.session_state:
        st.session_state.saved_filings = {}

    st.markdown("## Upload a 10-Q Filing")
    st.markdown(
        '<div style="color:#6b6b8a;font-size:0.8rem;letter-spacing:0.15em">ANY COMPANY · PDF OR TXT · SAVED FOR COMPARISON</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col_upload, col_saved = st.columns([3, 2])

    with col_upload:
        st.markdown('<div class="section-header">UPLOAD FILING</div>', unsafe_allow_html=True)

        company_name = st.text_input(
            "Company Name",
            placeholder="e.g. Nike, Walmart, Disney...",
            help="This is how it'll appear in comparisons",
        )

        ticker_input = st.text_input(
            "Ticker Symbol",
            placeholder="e.g. NKE, WMT, DIS...",
            help="Used for stock price lookup",
        ).upper().strip()

        col_q, col_y = st.columns(2)

        with col_q:
            quarter_input = st.selectbox("Quarter", [1, 2, 3, 4])

        with col_y:
            year_input = st.selectbox("Year", [2024, 2023, 2022, 2021])

        uploaded_file = st.file_uploader(
            "Upload 10-Q (PDF or TXT)",
            type=["pdf", "txt"],
            help="Upload the full 10-Q filing or just the MD&A section",
        )

        analyze_btn = st.button("Analyze Filing", use_container_width=True)

    with col_saved:
        st.markdown('<div class="section-header">SAVED FILINGS</div>', unsafe_allow_html=True)

        if not st.session_state.saved_filings:
            st.markdown(
                '<div style="color:#6b6b8a;font-size:0.85rem;padding:1rem 0">No filings saved yet.<br>Upload and analyze a filing to save it here for comparison.</div>',
                unsafe_allow_html=True,
            )
        else:
            for key, filing in st.session_state.saved_filings.items():
                overall = filing.get("overall_sentiment", {})
                label = str(overall.get("label", "NEUTRAL")).upper()
                color = SENTIMENT_COLORS.get(label, "#f59e0b")
                conf = safe_float(overall.get("confidence"))

                filing_company = html_safe(filing.get("company", ""))
                filing_ticker = html_safe(filing.get("ticker") or "No ticker")
                filing_quarter = filing.get("quarter", "")
                filing_year = filing.get("year", "")

                col_info, col_del = st.columns([4, 1])

                with col_info:
                    st.markdown(
                        f"""
                        <div class="metric-card" style="margin-bottom:0.5rem;padding:0.8rem 1rem">
                            <div style="font-weight:600;font-size:0.9rem">{filing_company}</div>
                            <div style="font-size:0.72rem;color:#6b6b8a">Q{filing_quarter} {filing_year} · {filing_ticker}</div>
                            <div style="color:{color};font-size:0.8rem;margin-top:4px">{label} · {conf:.0%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_del:
                    if st.button("✕", key=f"del_{key}", help="Remove"):
                        del st.session_state.saved_filings[key]
                        st.rerun()

    if analyze_btn:
        if not uploaded_file:
            st.error("Please upload a file.")
            st.stop()

        if not company_name.strip():
            st.error("Please enter a company name.")
            st.stop()

        safe_uploaded_name = html_safe(uploaded_file.name)

        with st.spinner(f"Extracting text from {safe_uploaded_name}..."):
            file_bytes = uploaded_file.read()

            if uploaded_file.name.lower().endswith(".pdf"):
                raw_text = extract_text_from_pdf(file_bytes)
            else:
                raw_text = extract_text_from_txt(file_bytes)

            if not raw_text or len(raw_text) < 200:
                st.error("Could not extract enough text from the file. Try a text file or a different PDF.")
                st.stop()

        with st.spinner("Running Claude + FinBERT + LM analysis..."):
            try:
                analysis_text = raw_text[:9000]

                llm_result = run_claude_analysis(
                    analysis_text,
                    ticker_input or company_name,
                    quarter_input,
                    year_input,
                )

                overall_score = ensemble_score(analysis_text)

                for item in llm_result.get("keyRiskSignals", []):
                    item["sentiment"] = ensemble_score(
                        item.get("detail", item.get("risk", ""))
                    )

                for item in llm_result.get("notableChanges", []):
                    item["sentiment"] = ensemble_score(item.get("change", ""))

                for item in llm_result.get("evidenceCitations", []):
                    item["sentiment"] = ensemble_score(item.get("text", ""))

                result = {
                    "ticker": ticker_input or company_name[:4].upper(),
                    "company": company_name,
                    "year": year_input,
                    "quarter": quarter_input,
                    "llm_summary": llm_result,
                    "overall_sentiment": overall_score,
                    "source": "upload",
                    "filename": uploaded_file.name,
                }

                safe_filename = uploaded_file.name.replace(" ", "_")
                save_key = f"{company_name}_{quarter_input}_{year_input}_{safe_filename}"

                st.session_state.saved_filings[save_key] = result
                st.success(f"✓ Analysis complete — {company_name} saved for comparison")

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

        st.markdown("---")
        _render_results(result)


def _render_results(result: dict):
    overall = result.get("overall_sentiment", {})
    llm = result.get("llm_summary", {})

    label = str(overall.get("label", "NEUTRAL")).upper()
    conf = safe_float(overall.get("confidence"))
    pos = safe_float(overall.get("positive"))
    neg = safe_float(overall.get("negative"))
    color = SENTIMENT_COLORS.get(label, "#f59e0b")

    company = html_safe(result.get("company", ""))
    filename = html_safe(result.get("filename", "uploaded file"))

    st.markdown(f"### {company} — Q{result.get('quarter', '')} {result.get('year', '')}")
    st.markdown(
        f'<div style="color:#6b6b8a;font-size:0.75rem">Source: {filename}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)

    with m1:
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

    col_sum, col_risk = st.columns([1, 1])

    with col_sum:
        st.markdown('<div class="section-header">LLM SUMMARY</div>', unsafe_allow_html=True)

        tone = html_safe(llm.get("overallTone", ""))
        takeaway = html_safe(llm.get("analystTakeaway", ""))

        if tone:
            st.markdown(
                f'<div style="font-size:0.9rem;color:#e8e8f0;line-height:1.6;margin-bottom:0.75rem"><em>{tone}</em></div>',
                unsafe_allow_html=True,
            )

        if takeaway:
            st.markdown(
                f'<div style="font-size:0.82rem;color:#9999bb;line-height:1.7">{takeaway}</div>',
                unsafe_allow_html=True,
            )

    with col_risk:
        st.markdown('<div class="section-header">KEY RISK SIGNALS</div>', unsafe_allow_html=True)

        for item in llm.get("keyRiskSignals", [])[:4]:
            s = item.get("sentiment", {})
            s_label = str(s.get("label", "NEUTRAL")).upper()
            border = SENTIMENT_COLORS.get(s_label, "#f59e0b")
            conf_val = safe_float(s.get("confidence"))
            risk_text = html_safe(item.get("risk", ""))

            st.markdown(
                f"""
                <div class="risk-item" style="border-left-color:{border}">
                    <div style="font-weight:500;margin-bottom:4px;font-size:0.85rem">{risk_text}</div>
                    {confidence_bar(conf_val, s_label)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown('<div class="section-header">NOTABLE CHANGES</div>', unsafe_allow_html=True)

    for item in llm.get("notableChanges", []):
        direction = str(item.get("direction", "neutral")).upper()
        magnitude = html_safe(item.get("magnitude", ""))
        change_text = html_safe(item.get("change", ""))

        color_c = SENTIMENT_COLORS.get(direction, "#f59e0b")
        icon = "▲" if direction == "POSITIVE" else "▼" if direction == "NEGATIVE" else "●"

        s = item.get("sentiment", {})
        conf_val = safe_float(s.get("confidence"))

        st.markdown(
            f"""
            <div class="risk-item" style="border-left-color:{color_c}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                    <span style="font-weight:500;font-size:0.85rem">{change_text}</span>
                    <span style="color:{color_c};font-size:0.8rem">{icon} {magnitude}</span>
                </div>
                {confidence_bar(conf_val, direction)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown('<div class="section-header">EVIDENCE CITATIONS</div>', unsafe_allow_html=True)

    for i, item in enumerate(llm.get("evidenceCitations", []), 1):
        s = item.get("sentiment", {})
        s_label = str(s.get("label", "NEUTRAL")).upper()
        conf_val = safe_float(s.get("confidence"))

        evidence_text = html_safe(item.get("text", ""))
        significance = html_safe(item.get("significance", "Evidence"))

        with st.expander(f"[{i}] {significance[:80]}..."):
            st.markdown(
                f"""
                <div style="padding:0.5rem">
                    <div class="evidence-item">"{evidence_text}"</div>
                    <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
                        <span class="sentiment-badge badge-{s_label.lower()}">{s_label}</span>
                        <span style="font-size:0.78rem;color:#9999bb">Confidence: {conf_val:.0%}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    try:
        pdf_bytes = generate_pdf_report(result)

        safe_ticker = str(result.get("ticker", "UPLOAD")).replace(" ", "_")

        st.download_button(
            label="⬇ Download PDF Report",
            data=pdf_bytes,
            file_name=f"SentiQ_{safe_ticker}_Q{result.get('quarter', '')}{result.get('year', '')}.pdf",
            mime="application/pdf",
        )

    except Exception as e:
        st.caption(f"PDF export unavailable: {e}")