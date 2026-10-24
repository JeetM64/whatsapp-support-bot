from __future__ import annotations

from pathlib import Path

from src.rag.normalize import detect_language, load_lexicon, normalize_text, tokenize

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "kb" / "lexicon.yaml"


def test_lexicon_has_at_least_80_aliases() -> None:
    aliases = load_lexicon(str(LEXICON.resolve()))
    assert len(aliases) >= 80


def test_hinglish_synonyms_normalize_to_canonical_tokens() -> None:
    normalized = normalize_text("kitni fee hai kya paisa", LEXICON)
    assert "fee-quantity" in normalized
    assert "money" in normalized
    assert "question" in normalized
    assert "refund" in normalize_text("paisa wapas", LEXICON)


def test_nfkc_punctuation_emoji_and_repeated_characters() -> None:
    normalized = normalize_text("ＲＳ 999 pleaseeee!!! 💸", LEXICON)
    assert "money" in normalized
    assert "please" in normalized
    assert "!" not in normalized
    assert "💸" not in normalized


def test_devanagari_is_preserved_and_detected() -> None:
    normalized = normalize_text("नहीं प्रमाण पत्र मिलेगा?", LEXICON)
    assert "नहीं" in normalized
    assert "प्रमाण" in normalized
    assert detect_language("मुझे प्रमाणपत्र चाहिए") == "Hindi"


def test_normalized_form_is_for_retrieval_tokens_only() -> None:
    message = "fee kitni hai"
    assert tokenize(message, LEXICON) != message.split()
    assert message == "fee kitni hai"
