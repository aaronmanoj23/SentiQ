# SentiQ — SEC Filing Sentiment Intelligence

> **Live financial sentiment analysis of SEC 10-Q filings using a FinBERT + Loughran-McDonald ensemble and Claude AI.**

![Python](https://img.shields.io/badge/Python-3.10+-7c3aed?style=flat-square) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32-00e5ff?style=flat-square) ![Claude](https://img.shields.io/badge/Claude-Sonnet-00d4aa?style=flat-square)

---

## What It Does

SentiQ fetches live SEC 10-Q filings from EDGAR and scores corporate language using a dual-model ensemble — identifying whether a company's filing tone is becoming more optimistic or more fearful, and correlating those shifts with actual stock price movement.

| Mode | Description |
|---|---|
| **Single Analysis** | Deep-dive on one company, one quarter — risk signals, notable changes, evidence citations, all sentiment-scored |
| **Trend Analysis** | All 4 quarters of a year — sentiment drift detection + stock price overlay + Pearson correlation |
| **Compare Companies** | Same quarter across 2–4 companies — ranked side-by-side with radar chart |
| **Upload Filing** | Upload any 10-Q PDF or TXT — full analysis + save for comparison |

---

## Setup (Windows)

### Step 1 — Clone the repo

Open Command Prompt and run:

```bash
git clone https://github.com/aaronmanoj23/SentiQ.git
cd SentiQ
```

---

### Step 2 — Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your terminal line.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This takes 2–3 minutes the first time.

---

### Step 4 — Create your .env file

In the SentiQ folder, create a file called `.env` (no extension). Open it with Notepad and paste:

```
ANTHROPIC_API_KEY=get_this_from_aaron
HF_TOKEN=get_this_from_aaron
```

**Get both keys from Aaron directly** — he will send them to you via iMessage or Discord. Do not commit this file to GitHub.

> **ANTHROPIC_API_KEY** — required. Powers Claude Sonnet analysis.
> **HF_TOKEN** — optional but recommended. Enables FinBERT scoring via HuggingFace (free). Without it, SentiQ uses LM lexicon only.

To create the `.env` file correctly in Windows:
1. Open Notepad
2. Paste the two lines above with the real keys Aaron sends you
3. File → Save As → navigate to the SentiQ folder → set "Save as type" to **All Files** → name it `.env` → Save

---

### Step 5 — Run

```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.

---

## Setup (Mac)

### Step 1 — Clone the repo

```bash
git clone https://github.com/aaronmanoj23/SentiQ.git
cd SentiQ
```

### Step 2 — Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Create .env file

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in the keys Aaron sends you:

```
ANTHROPIC_API_KEY=get_this_from_aaron
HF_TOKEN=get_this_from_aaron
```

### Step 5 — Run

```bash
streamlit run app.py
```

---

## Common Errors

**`ModuleNotFoundError: No module named 'anthropic'`**
→ Your venv is not activated. Run `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac) first.

**`streamlit: command not found`**
→ Same issue — activate your venv first.

**`AuthenticationError` or `Invalid API key`**
→ Your `.env` file is missing or the key is wrong. Double-check with Aaron.

**`streamlit run app.py` opens but charts are blank**
→ The analysis is still running. Wait 30–60 seconds and the charts will populate.

**`.env` file saving as `.env.txt`**
→ In Notepad, make sure "Save as type" is set to **All Files**, not "Text Documents".

---

## How to Use

**Single Analysis**
1. Select a company from the dropdown
2. Select year and quarter
3. Click **Run Analysis**
4. Wait ~15 seconds for Claude to fetch and analyze the filing

**Trend Analysis**
1. Select a company and year
2. Click **Analyze Trend**
3. Wait ~2 minutes — it runs all 4 quarters back to back
4. See sentiment drift + stock price overlay

**Compare Companies**
1. Select 2–4 companies (or mix with uploaded filings)
2. Select year and quarter
3. Click **Compare**
4. See side-by-side bar chart, radar chart, and rankings table

**Upload Filing**
1. Click **Upload Filing** in the sidebar
2. Enter company name, ticker, quarter, year
3. Upload a 10-Q PDF or TXT file
4. Click **Analyze Filing**
5. Results are saved to session — go to Compare Companies to use them alongside EDGAR companies

---

## Architecture

```
SEC EDGAR (live 10-Q filing)
        ↓
  fetch_mda_text()          ← requests + EDGAR REST API
        ↓
  Claude Sonnet             ← structured JSON: risks, changes, citations, tone
        ↓
  FinBERT (HuggingFace)     ← transformer-based financial sentiment (60% weight)
  LM Lexicon (built-in)     ← domain-specific word list scoring (40% weight)
        ↓
  Ensemble Score            ← label + confidence per component
        ↓
  yfinance                  ← stock price overlay + quarterly returns
        ↓
  Streamlit UI              ← charts, metrics, PDF export
```

---

## Project Structure

```
sentiq/
├── app.py                  # Streamlit entry point + sidebar + routing
├── pages/
│   ├── single.py           # Single analysis page
│   ├── trend.py            # Trend analysis page
│   ├── compare.py          # Multi-company comparison page
│   └── upload.py           # Upload any 10-Q filing
├── utils/
│   ├── pipeline.py         # Core: EDGAR fetch + Claude + FinBERT + LM ensemble
│   ├── stocks.py           # yfinance integration + correlation math
│   └── pdf_export.py       # ReportLab PDF generation
├── tests/
│   └── test_pipeline.py    # Unit tests (12 passing)
├── .streamlit/
│   └── config.toml         # Theme + server config
├── requirements.txt
└── .env.example            # Copy this to .env and fill in your keys
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit + Plotly |
| LLM | Claude Sonnet (Anthropic) |
| Sentiment | FinBERT (ProsusAI) + Loughran-McDonald Lexicon |
| Filing data | SEC EDGAR REST API |
| Stock data | yfinance |
| PDF parsing | pdfplumber |
| PDF export | ReportLab |

---

## Team

Aaron, Sheldin, Anupama

---

*Data sourced from SEC EDGAR public API. Not financial advice.*
