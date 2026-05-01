"""
SentiQ Test Suite
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pipeline import lm_score, ensemble_score, _demo_text
from utils.stocks import correlate_sentiment_price


# ── LM Lexicon tests ─────────────────────────────────────────────────────────

def test_lm_score_negative_text():
    text = "The company faces significant risks and uncertainty. Losses increased due to adverse market conditions and declining revenue."
    result = lm_score(text)
    assert result["label"] == "NEGATIVE"
    assert result["negative"] > result["positive"]
    assert 0 <= result["confidence"] <= 1 if "confidence" in result else True


def test_lm_score_positive_text():
    text = "Strong revenue growth and exceptional profit margins. The company achieved record earnings with consistent performance."
    result = lm_score(text)
    assert result["label"] == "POSITIVE"
    assert result["positive"] > result["negative"]


def test_lm_score_returns_required_keys():
    result = lm_score("Revenue grew significantly this quarter.")
    assert "positive" in result
    assert "negative" in result
    assert "neutral" in result
    assert "label" in result
    assert result["label"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")


def test_lm_score_empty_text():
    result = lm_score("")
    assert result["label"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")


# ── Ensemble tests ────────────────────────────────────────────────────────────

def test_ensemble_score_structure():
    result = ensemble_score("Strong growth driven by exceptional performance.")
    assert "positive" in result
    assert "negative" in result
    assert "neutral" in result
    assert "label" in result
    assert "confidence" in result
    assert "finbert" in result
    assert "lm" in result


def test_ensemble_confidence_range():
    result = ensemble_score("The firm faces headwinds and declining margins.")
    assert 0.0 <= result["confidence"] <= 1.0


def test_ensemble_label_valid():
    result = ensemble_score("Volatile market conditions created uncertainty and risk.")
    assert result["label"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")


# ── Correlation tests ─────────────────────────────────────────────────────────

def test_correlation_positive():
    sentiment_pairs = [(1, 0.7), (2, 0.6), (3, 0.8), (4, 0.75)]
    price_returns = {1: 5.0, 2: 3.0, 3: 8.0, 4: 6.0}
    result = correlate_sentiment_price(sentiment_pairs, price_returns)
    assert "correlation" in result
    if result["correlation"] is not None:
        assert -1 <= result["correlation"] <= 1


def test_correlation_insufficient_data():
    result = correlate_sentiment_price([(1, 0.7)], {1: 5.0})
    assert result["correlation"] is None


def test_correlation_empty():
    result = correlate_sentiment_price([], {})
    assert result["correlation"] is None


# ── Demo text tests ───────────────────────────────────────────────────────────

def test_demo_text_known_ticker():
    text = _demo_text("AAPL", 1, 2024)
    assert len(text) > 100
    assert "Apple" in text or "AAPL" in text or "revenue" in text.lower()


def test_demo_text_unknown_ticker():
    text = _demo_text("XYZ", 1, 2024)
    assert len(text) > 50


if __name__ == "__main__":
    tests = [
        test_lm_score_negative_text,
        test_lm_score_positive_text,
        test_lm_score_returns_required_keys,
        test_lm_score_empty_text,
        test_ensemble_score_structure,
        test_ensemble_confidence_range,
        test_ensemble_label_valid,
        test_correlation_positive,
        test_correlation_insufficient_data,
        test_correlation_empty,
        test_demo_text_known_ticker,
        test_demo_text_unknown_ticker,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{passed}/{len(tests)} tests passed")
