"""
SentiQ Core Pipeline
====================
Fetch -> Multi Section RAG -> LLM Summary -> FinBERT -> LM Lexicon -> Ensemble
"""

import os
import json
import re
import requests
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()


LM_NEGATIVE = {
    "abandon","abandonment","abdicate","aberrant","abnormal","abolish","absence",
    "abuse","adverse","adversely","adversity","allegation","allegations","alleged",
    "alleges","ambiguity","ambiguous","anxiety","bankruptcy","catastrophe","caution",
    "cautionary","challenge","challenged","challenging","closure","complaint",
    "complaints","concentration","concern","concerns","conflict","costly","crisis",
    "critical","curtail","decline","declining","default","deficiency","delay",
    "difficult","difficulties","difficulty","diminish","dispute","disruption",
    "downturn","exceed","excessive","exposure","fail","failure","falling","flaw",
    "fraud","harm","hazard","headwind","headwinds","impair","impairment","inadequate",
    "insufficient","litigation","loss","losses","negatively","obstacle","penalty",
    "problem","recession","restructuring","risk","risks","shortage","slowdown",
    "uncertainty","unfavorable","unforeseen","unfunded","unstable","volatile",
    "volatility","vulnerability","weak","weakening","weakness","worsen","worsening",
}

LM_POSITIVE = {
    "achieve","achievement","advantage","beneficial","benefit","capitalize",
    "confidence","confident","consistent","deliver","delivering","diversify",
    "efficient","efficiency","enhance","exceeds","exceptional","expand","expansion",
    "favorable","gain","gains","grow","growth","improve","improvement","increasing",
    "innovative","leading","momentum","opportunity","outperform","positive","profit",
    "profitable","progress","record","resilient","revenue","robust","solid","stable",
    "strength","strong","success","superior","sustainable","value","winning",
}


CIK_MAP = {
    "AAPL": "320193",
    "MSFT": "789019",
    "GOOGL": "1652044",
    "AMZN": "1018724",
    "META": "1326801",
    "GS": "886982",
    "JPM": "19617",
    "MS": "895421",
    "TSLA": "1318605",
    "NVDA": "1045810",
}


def lm_score(text: str) -> dict:
    words = re.findall(r"\b[a-z]+\b", text.lower())

    if not words:
        return {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
            "label": "NEUTRAL",
        }

    pos = sum(1 for w in words if w in LM_POSITIVE)
    neg = sum(1 for w in words if w in LM_NEGATIVE)
    total = pos + neg

    if total == 0:
        return {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
            "label": "NEUTRAL",
        }

    sentiment_word_ratio = total / max(len(words), 1)
    neutral_score = max(0.0, 1 - sentiment_word_ratio)

    pos_score = (pos / total) * (1 - neutral_score)
    neg_score = (neg / total) * (1 - neutral_score)

    if pos_score > neg_score + 0.1:
        label = "POSITIVE"
    elif neg_score > pos_score + 0.1:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    return {
        "positive": round(pos_score, 4),
        "negative": round(neg_score, 4),
        "neutral": round(neutral_score, 4),
        "label": label,
    }


def finbert_score(text: str) -> dict:
    hf_token = os.getenv("HF_TOKEN", "")

    if hf_token:
        try:
            api_url = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
            headers = {"Authorization": f"Bearer {hf_token}"}
            payload = {"inputs": text[:512]}

            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=15,
            )

            if response.status_code == 200:
                results = response.json()
                scores = {}

                if isinstance(results, list) and results:
                    first = results[0]

                    if isinstance(first, list):
                        scores = {
                            item.get("label", "").lower(): item.get("score", 0)
                            for item in first
                        }

                    elif isinstance(first, dict):
                        scores = {
                            first.get("label", "").lower(): first.get("score", 0)
                        }

                if scores:
                    label = max(scores, key=scores.get).upper()

                    return {
                        "positive": scores.get("positive", 0),
                        "negative": scores.get("negative", 0),
                        "neutral": scores.get("neutral", 0),
                        "label": label,
                    }

        except Exception:
            pass

    return lm_score(text)


def ensemble_score(text: str) -> dict:
    fb = finbert_score(text)
    lm = lm_score(text)

    pos = 0.6 * fb.get("positive", 0) + 0.4 * lm.get("positive", 0)
    neg = 0.6 * fb.get("negative", 0) + 0.4 * lm.get("negative", 0)
    neu = 0.6 * fb.get("neutral", 0) + 0.4 * lm.get("neutral", 0)

    total = pos + neg + neu

    if total > 0:
        pos = pos / total
        neg = neg / total
        neu = neu / total

    if pos > neg + 0.05:
        label = "POSITIVE"
    elif neg > pos + 0.05:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    confidence = max(pos, neg, neu)

    return {
        "positive": round(pos, 4),
        "negative": round(neg, 4),
        "neutral": round(neu, 4),
        "label": label,
        "confidence": round(confidence, 4),
        "finbert": fb,
        "lm": lm,
    }


def resolve_company_identifier(query: str) -> dict:
    try:
        if not query:
            return {}

        query_clean = query.strip()
        query_upper = query_clean.upper()
        query_lower = query_clean.lower()

        if query_upper in CIK_MAP:
            return {
                "ticker": query_upper,
                "company": query_upper,
                "cik": CIK_MAP[query_upper].zfill(10),
                "cik_raw": CIK_MAP[query_upper],
            }

        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "SentiQ Research anupamasingh47@gmail.com"}

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return {}

        data = response.json()

        exact_matches = []
        partial_matches = []

        for item in data.values():
            ticker = item["ticker"].upper()
            company = item["title"]
            cik_raw = str(item["cik_str"])

            record = {
                "ticker": ticker,
                "company": company,
                "cik": cik_raw.zfill(10),
                "cik_raw": cik_raw,
            }

            if query_upper == ticker:
                exact_matches.append(record)
            elif query_lower == company.lower():
                exact_matches.append(record)
            elif query_lower in company.lower():
                partial_matches.append(record)

        if exact_matches:
            return exact_matches[0]

        if partial_matches:
            return partial_matches[0]

        return {}

    except Exception:
        return {}


def _get_cik(ticker_or_company: str) -> str:
    resolved = resolve_company_identifier(ticker_or_company)

    if resolved:
        return resolved["cik"]

    cik = CIK_MAP.get(ticker_or_company.upper(), "")
    return cik.zfill(10) if cik else ""


def fetch_10q_text(ticker: str, year: int, quarter: int) -> Optional[dict]:
    try:
        resolved = resolve_company_identifier(ticker)

        if not resolved:
            return None

        actual_ticker = resolved["ticker"]
        cik = resolved["cik"]

        search_url = (
            f"https://efts.sec.gov/LATEST/search-index?"
            f"q=%22{actual_ticker}%22"
            f"&dateRange=custom"
            f"&startdt={year}-01-01"
            f"&enddt={year}-12-31"
            f"&forms=10-Q"
        )

        headers = {"User-Agent": "SentiQ Research anupamasingh47@gmail.com"}
        cik_url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        r = requests.get(cik_url, headers=headers, timeout=15)

        if r.status_code != 200:
            return None

        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])

        q_month_map = {
            1: range(4, 7),
            2: range(7, 10),
            3: range(10, 13),
            4: range(1, 4),
        }

        target_months = q_month_map.get(quarter, range(1, 13))
        target_acc = None

        for form, date, acc in zip(forms, dates, accessions):
            if form != "10-Q":
                continue

            parts = date.split("-")

            if len(parts) != 3:
                continue

            filing_year = int(parts[0])
            filing_month = int(parts[1])

            if filing_year == year and filing_month in target_months:
                target_acc = acc.replace("-", "")
                break

        if not target_acc:
            return None

        index_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{resolved['cik_raw']}/{target_acc}/{target_acc}-index.htm"
        )

        return {
            "accession": target_acc,
            "ticker": actual_ticker,
            "company": resolved["company"],
            "cik": cik,
            "cik_raw": resolved["cik_raw"],
            "index_url": index_url,
            "search_url": search_url,
            "found": True,
        }

    except Exception:
        return None


def fetch_filing_text(ticker: str, year: int, quarter: int) -> str:
    try:
        headers = {"User-Agent": "SentiQ Research anupamasingh47@gmail.com"}

        resolved = resolve_company_identifier(ticker)

        if not resolved:
            return ""

        cik = resolved["cik"]
        cik_raw = str(int(resolved["cik_raw"]))

        subs_url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        r = requests.get(subs_url, headers=headers, timeout=15)

        if r.status_code != 200:
            return ""

        data = r.json()
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accessions = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        q_month_map = {
            1: range(4, 7),
            2: range(7, 10),
            3: range(10, 13),
            4: range(1, 4),
        }

        target_months = q_month_map.get(quarter, range(1, 13))

        for form, date, acc, doc in zip(forms, dates, accessions, primary_docs):
            if form != "10-Q":
                continue

            parts = date.split("-")

            if len(parts) < 3:
                continue

            filing_year = int(parts[0])
            filing_month = int(parts[1])

            if filing_year == year and filing_month in target_months:
                acc_fmt = acc.replace("-", "")

                doc_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_raw}/{acc_fmt}/{doc}"
                )

                dr = requests.get(doc_url, headers=headers, timeout=20)

                if dr.status_code == 200:
                    return _clean_html(dr.text)

                break

        return ""

    except Exception:
        return ""


def fetch_mda_text(ticker: str, year: int, quarter: int) -> str:
    filing_text = fetch_filing_text(ticker, year, quarter)

    if not filing_text:
        return ""

    sections = extract_target_sections(filing_text)

    return sections.get("MD&A", "")[:4000]


def _clean_html(html: str) -> str:
    clean = re.sub(
        r"<script.*?</script>",
        " ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    clean = re.sub(
        r"<style.*?</style>",
        " ",
        clean,
        flags=re.DOTALL | re.IGNORECASE,
    )
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = clean.replace("&nbsp;", " ")
    clean = clean.replace("&amp;", "&")
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def extract_target_sections(filing_text: str) -> dict:
    section_patterns = {
        "MD&A": [
            "management’s discussion and analysis",
            "management's discussion and analysis",
            "management discussion and analysis",
        ],
        "Risk Management": [
            "risk management",
            "overview and structure of risk management",
        ],
        "Market Risk": [
            "market risk management",
            "quantitative and qualitative disclosures about market risk",
            "market risk",
        ],
        "Legal Proceedings": [
            "legal proceedings",
        ],
        "Controls and Procedures": [
            "controls and procedures",
        ],
        "Commitments Contingencies and Guarantees": [
            "commitments, contingencies and guarantees",
            "commitments contingencies and guarantees",
            "commitments and contingencies",
            "contingencies",
            "guarantees",
        ],
        "Regulatory and Other Matters": [
            "regulatory and other matters",
        ],
    }

    lower_text = filing_text.lower()
    starts = []

    for section_name, patterns in section_patterns.items():
        best_pos = None

        for pattern in patterns:
            pos = lower_text.find(pattern.lower())

            if pos != -1:
                if best_pos is None or pos < best_pos:
                    best_pos = pos

        if best_pos is not None:
            starts.append((best_pos, section_name))

    starts.sort(key=lambda x: x[0])
    sections = {}

    for i, (start_pos, section_name) in enumerate(starts):
        if i + 1 < len(starts):
            end_pos = starts[i + 1][0]
        else:
            end_pos = min(len(filing_text), start_pos + 12000)

        section_text = filing_text[start_pos:end_pos].strip()

        if len(section_text) > 200:
            sections[section_name] = section_text[:12000]

    return sections


def chunk_sections(sections: dict, chunk_size: int = 1800, overlap: int = 250) -> list:
    chunks = []

    for section_name, section_text in sections.items():
        text = re.sub(r"\s+", " ", section_text).strip()

        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            if len(chunk_text) > 200:
                chunks.append(
                    {
                        "section": section_name,
                        "text": chunk_text,
                    }
                )

            start += chunk_size - overlap

    return chunks


def retrieve_relevant_chunks(chunks: list, query: str, top_k: int = 6) -> list:
    query_words = set(re.findall(r"\b[a-z]+\b", query.lower()))
    scored_chunks = []

    for chunk in chunks:
        chunk_words = set(re.findall(r"\b[a-z]+\b", chunk["text"].lower()))
        score = len(query_words.intersection(chunk_words))

        section_bonus = 0
        section_lower = chunk["section"].lower()

        if "risk" in section_lower:
            section_bonus += 3
        if "legal" in section_lower:
            section_bonus += 2
        if "management" in section_lower:
            section_bonus += 2
        if "market" in section_lower:
            section_bonus += 2
        if "controls" in section_lower:
            section_bonus += 1
        if "regulatory" in section_lower:
            section_bonus += 2
        if "commitments" in section_lower:
            section_bonus += 2

        total_score = score + section_bonus
        scored_chunks.append((total_score, chunk))

    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    selected = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]

    if not selected:
        return chunks[:top_k]

    return selected


def build_rag_context(filing_text: str) -> dict:
    sections = extract_target_sections(filing_text)

    if not sections:
        return {
            "rag_text": filing_text[:8000],
            "sections_used": ["Fallback Filing Text"],
            "chunks_used": 1,
        }

    chunks = chunk_sections(sections)

    rag_query = """
    financial performance revenue earnings expenses liquidity capital risk risks
    market risk credit risk operational risk cybersecurity risk legal proceedings
    litigation regulatory matters controls procedures commitments contingencies guarantees
    management discussion analysis results operations
    """

    retrieved_chunks = retrieve_relevant_chunks(chunks, rag_query, top_k=6)

    rag_parts = []
    sections_used = []

    for chunk in retrieved_chunks:
        section = chunk["section"]
        sections_used.append(section)

        rag_parts.append(
            f"\n\nSECTION: {section}\n"
            f"{chunk['text']}"
        )

    rag_text = "\n".join(rag_parts)

    return {
        "rag_text": rag_text[:10000],
        "sections_used": sorted(list(set(sections_used))),
        "chunks_used": len(retrieved_chunks),
    }


def _extract_section(html: str, keywords: list) -> str:
    clean = _clean_html(html)

    pattern = "|".join(keywords)
    matches = [m.start() for m in re.finditer(pattern, clean.lower())]

    if not matches:
        return clean[:3000]

    start = matches[0]
    return clean[start:start + 4000].strip()


def run_claude_analysis(text: str, ticker: str, quarter: int, year: int) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return {
            "overallTone": "LLM analysis unavailable because ANTHROPIC_API_KEY is missing.",
            "keyRiskSignals": [],
            "notableChanges": [],
            "evidenceCitations": [],
            "analystTakeaway": "Set ANTHROPIC_API_KEY in your .env file to enable Claude analysis.",
        }

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze this SEC 10-Q filing excerpt for {ticker} (Q{quarter} {year}).

The excerpt was selected using a lightweight RAG retrieval step across multiple 10-Q sections.

Return ONLY valid JSON in this exact format:
{{
  "overallTone": "one sentence describing the overall tone",
  "keyRiskSignals": [
    {{"risk": "risk description", "detail": "specific detail from filing"}}
  ],
  "notableChanges": [
    {{"change": "change description", "direction": "positive|negative|neutral", "magnitude": "percentage or qualitative"}}
  ],
  "evidenceCitations": [
    {{"text": "direct quote from filing", "significance": "why this matters"}}
  ],
  "analystTakeaway": "2 to 3 sentence investor facing summary"
}}

Include 3 to 5 items in each array. Focus on material financial information, risks, legal or regulatory issues, market risk, liquidity, capital, and controls.

Filing text:
{text[:9000]}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except Exception as e:
        return {
            "overallTone": f"LLM analysis unavailable due to error: {str(e)}",
            "keyRiskSignals": [],
            "notableChanges": [],
            "evidenceCitations": [],
            "analystTakeaway": "The filing was fetched and sentiment scoring can still run, but Claude summary failed.",
        }


def full_analysis(ticker: str, company: str, year: int, quarter: int) -> dict:
    resolved = resolve_company_identifier(ticker)

    if resolved:
        ticker = resolved["ticker"]
        company = resolved["company"]

    filing_text = fetch_filing_text(ticker, year, quarter)

    if filing_text:
        rag_result = build_rag_context(filing_text)
        analysis_text = rag_result["rag_text"]
        sections_used = rag_result["sections_used"]
        chunks_used = rag_result["chunks_used"]
        data_source = "SEC Filing"
    else:
        analysis_text = _demo_text(ticker, quarter, year)
        sections_used = ["Demo Text"]
        chunks_used = 1
        data_source = "Demo Text"

    llm_result = run_claude_analysis(
        analysis_text,
        ticker,
        quarter,
        year,
    )

    overall_score = ensemble_score(analysis_text)

    for item in llm_result.get("keyRiskSignals", []):
        item["sentiment"] = ensemble_score(
            item.get("detail", item.get("risk", ""))
        )

    for item in llm_result.get("notableChanges", []):
        item["sentiment"] = ensemble_score(
            item.get("change", "")
        )

    for item in llm_result.get("evidenceCitations", []):
        item["sentiment"] = ensemble_score(
            item.get("text", "")
        )

    return {
        "ticker": ticker,
        "company": company,
        "year": year,
        "quarter": quarter,
        "mda_text": (
            analysis_text[:500] + "..."
            if len(analysis_text) > 500
            else analysis_text
        ),
        "rag_enabled": True,
        "sections_used": sections_used,
        "chunks_used": chunks_used,
        "data_source": data_source,
        "llm_summary": llm_result,
        "overall_sentiment": overall_score,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


def _demo_text(ticker: str, quarter: int, year: int) -> str:
    demos = {
        "AAPL": f"Apple Inc. reported net revenues for Q{quarter} {year} with strong Services growth of 14% year over year. iPhone revenue showed resilience despite macroeconomic headwinds in Greater China, where net sales declined 13%. The company faces ongoing challenges from currency fluctuations, particularly weakness in the Japanese Yen and Chinese RMB. Wearables and Home Accessories revenue decreased 11% due to lower demand. However, gross margin improved to 45.9% from 43.0% in the prior year period, driven by favorable product mix and cost efficiencies. The company maintains a robust balance sheet with $162 billion in cash and marketable securities, providing flexibility for capital returns.",
        "MSFT": f"Microsoft Corporation delivered Q{quarter} {year} results with total revenue growing 17% to $62 billion. Azure and cloud services revenue increased 29%, continuing to demonstrate strong enterprise adoption. LinkedIn revenue grew 10% reflecting resilient labor market demand. Gaming revenue declined 7% following the completion of the Activision Blizzard acquisition impact. Operating income increased 23% with operating margins expanding to 44.6%. The company faces risks from global economic uncertainty, regulatory scrutiny of AI services, and competitive pressure in the cloud infrastructure market.",
        "GOOGL": f"Alphabet Inc. Q{quarter} {year} results showed total revenues of $88.3 billion, representing 15% year over year growth. Google Search and other revenues grew 14%, demonstrating continued advertiser demand. Google Cloud revenues increased 29% to $11.4 billion, approaching profitability. YouTube advertising revenues grew 13% as brand spending recovered. The company faces headwinds from regulatory actions in multiple jurisdictions, antitrust investigations, and ongoing competition from AI powered search alternatives. Operating income grew 28% with margin expansion to 32%.",
        "GS": f"Goldman Sachs Q{quarter} {year} net revenues of $14.2 billion increased 17% year over year. Investment Banking fees grew 26% reflecting recovery in M&A and IPO activity. Global Markets net revenues increased 10% on strong client intermediation. Asset and Wealth Management revenues grew 18% on higher management fees. The firm faces continued uncertainty from elevated interest rates, geopolitical tensions affecting capital markets activity, and regulatory capital requirements. Return on equity improved to 12.1% from 9.4% in the prior year period.",
    }

    return demos.get(
        ticker,
        f"{ticker} reported quarterly results with mixed performance across business segments. Revenue growth remained resilient despite macroeconomic headwinds. The company continues to navigate challenges related to inflation, interest rates, and competitive dynamics.",
    )