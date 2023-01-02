import pytest

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
def test_contains_phone_number(text, expected):
    has_phone_number = text_type.contains_phone_number(text)
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
    ],
)
def test_contains_verb(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "pos_tag", mock_pos_tag)
    has_verb = text_type.contains_verb(text)
    assert has_verb is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Intellectual Property in the United States", True),
        ("Intellectual property helps incentivize innovation.", False),
        ("THIS IS ALL CAPS. BUT IT IS TWO SENTENCES.", False),
    ],
)
def test_contains_exceeds_cap_ratio(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    assert text_type.exceeds_cap_ratio(text, threshold=0.3) is expected


def test_sentence_count(monkeypatch):
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    text = "Hi my name is Matt. I work with Crag."
    assert text_type.sentence_count(text) == 2


def test_item_titles():
    text = "ITEM 1(A). THIS IS A TITLE"
    assert text_type.sentence_count(text, 3) < 2
