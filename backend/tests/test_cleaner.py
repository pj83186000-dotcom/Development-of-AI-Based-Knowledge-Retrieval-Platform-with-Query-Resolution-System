"""Unit tests for text cleaning and normalization module."""

import pytest
from backend.app.ingestion.cleaner import clean_text


def test_clean_text_unicode_normalization():
    # NFKC normalizes ligature 'ﬁ' -> 'fi' and fullwidth letters
    raw = "The ﬁnal conﬁguration for ＡＢＣ."
    cleaned = clean_text(raw)
    assert "final" in cleaned
    assert "configuration" in cleaned
    assert "ABC" in cleaned


def test_clean_text_hyphenation_repair():
    raw = "The micro-\nservice architecture provides containerized deploy-\n  ment."
    cleaned = clean_text(raw)
    assert "microservice" in cleaned
    assert "deployment" in cleaned


def test_clean_text_control_characters():
    # Include non-printable control characters \x00, \x07 (bell), \x1b (escape)
    raw = "Hello\x00 world\x07! This is a \x1btest."
    cleaned = clean_text(raw)
    assert cleaned == "Hello world! This is a test."


def test_clean_text_whitespace_standardization():
    raw = "Line 1 with    multiple    spaces.\n\n\n\n\nLine 2 with \t tabs."
    cleaned = clean_text(raw)
    # Consecutive newlines collapsed to max 2
    assert "\n\n\n" not in cleaned
    assert "Line 1 with multiple spaces.\n\nLine 2 with tabs." == cleaned


def test_clean_text_empty_and_whitespace():
    assert clean_text("") == ""
    assert clean_text("   \n\t  \n  ") == ""

