import pytest
from unittest.mock import patch

import unstructured.partition.text_type as text_type

from test_unstructured.nlp.mock_nltk import mock_pos_tag, mock_sent_tokenize, mock_word_tokenize


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "ITEM 5(a).: MARKET FOR REGISTRANT’S COMMON EQUITY, RELATED STOCKHOLDER MATTERS AND "
            "ISSUER PURCHASES OF EQUITY SECURITIES",
            False,
        ),
        (
            "Item 5(a).: Market For Registrant’s Common Equity, Related Stockholder Matters and "
            "Issuer Purchases of Equity Securities",
            False,
        ),
        (
            "There is a market for registrant’s common equity, related stockholder matters and "
            "issuer purchases of equity securities.",
            True,
        ),
    ],
)
def test_headings_are_not_narrative_text(text, expected):
    assert text_type.is_possible_narrative_text(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Ask the teacher for an apple.", True),
        ("Ask Me About Intellectual Property", False),  # Exceeds the cap threshold
        ("7", False),  # Fails because it is numeric
        ("intellectual property", False),  # Fails because it does not contain a verb
        ("", False),  # Fails because it is empty
    ],
)
def test_is_possible_narrative_text(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "pos_tag", mock_pos_tag)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    has_verb = text_type.is_possible_narrative_text(text, cap_threshold=0.3)
    assert has_verb is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Intellectual Property", True),  # Fails because it exceeds the cap threshold
        (
            "Ask the teacher for an apple. You might a gold star.",
            False,
        ),  # Too many sentences
        ("7", False),  # Fails because it is numeric
        ("", False),  # Fails because it is empty
        ("ITEM 1A. RISK FACTORS", True),  # Two "sentences", but both are short
        ("To My Dearest Friends,", False),  # Ends with a comma
    ],
)
def test_is_possible_title(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    has_verb = text_type.is_possible_title(text)
    assert has_verb is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("8675309", True),
        ("+1 867-5309", True),
        ("2158675309", True),
        ("+12158675309", True),
        ("867.5309", True),
        ("1-800-867-5309", True),
        ("1(800)-867-5309", True),
        ("Tel: 1(800)-867-5309", True),
    ],
)
def test_contains_us_phone_number(text, expected):
    has_phone_number = text_type.contains_us_phone_number(text)
    assert has_phone_number is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("• This is a fine point!", True),
        (" • This is a fine point!", True),  # Has an extra space in front of the bullet
        ("‣ This is a fine point!", True),
        ("⁃ This is a fine point!", True),
        ("⁌ This is a fine point!", True),
        ("⁍ This is a fine point!", True),
        ("∙ This is a fine point!", True),
        ("○ This is a fine point!", True),
        ("● This is a fine point!", True),
        ("◘ This is a fine point!", True),
        ("◦  This is a fine point!", True),
        ("☙ This is a fine point!", True),
        ("❥ This is a fine point!", True),
        ("❧ This is a fine point!", True),
        ("⦾ This is a fine point!", True),
        ("⦿ This is a fine point!", True),
        ("  This is a fine point!", True),
        ("* This is a fine point!", True),
        ("- This is a fine point!", True),
        ("This is NOT a fine point!", False),  # No bullet point
        ("I love morse code! ● ● ● --- ● ● ●", False),  # Not at the beginning
    ],
)
def test_is_bulletized_text(text, expected):
    assert text_type.is_bulleted_text(text) is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Ask the teacher for an apple", True),
        ("Intellectual property", False),
        ("THIS MESSAGE WAS APPROVED", True),
    ],
)
def test_contains_verb(text, expected, monkeypatch):
    has_verb = text_type.contains_verb(text)
    assert has_verb is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Intellectual Property in the United States", True),
        ("Intellectual property helps incentivize innovation.", False),
        ("THIS IS ALL CAPS. BUT IT IS TWO SENTENCES.", False),
        ("LOOK AT THIS IT IS CAPS BUT NOT A TITLE.", False),
        ("This Has All Caps. It's Weird But Two Sentences", False),
        ("The Business Report is expected within 6 hours of closing", False),
        ("", False),
    ],
)
def test_contains_exceeds_cap_ratio(text, expected, monkeypatch):
    assert text_type.exceeds_cap_ratio(text) is expected


def test_set_caps_ratio_with_environment_variable(monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("NARRATIVE_TEXT_CAP_THRESHOLD", 0.8)

    text = "All The King's Horses. And All The King's Men."
    with patch.object(text_type, "exceeds_cap_ratio", return_value=False) as mock_exceeds:
        text_type.is_possible_narrative_text(text)

    mock_exceeds.assert_called_once_with(text, threshold=0.8)


def test_sentence_count(monkeypatch):
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    text = "Hi my name is Matt. I work with Crag."
    assert text_type.sentence_count(text) == 2


def test_item_titles():
    text = "ITEM 1(A). THIS IS A TITLE"
    assert text_type.sentence_count(text, 3) < 2


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Doylestown, PA 18901", True),
        ("DOYLESTOWN, PENNSYLVANIA, 18901", True),
        ("DOYLESTOWN, PENNSYLVANIA 18901", True),
        ("Doylestown, Pennsylvania 18901", True),
        ("     Doylestown, Pennsylvania 18901", True),
        ("The Business Report is expected within 6 hours of closing", False),
        ("", False),
    ],
)
def test_is_us_city_state_zip(text, expected):
    assert text_type.is_us_city_state_zip(text) is expected
