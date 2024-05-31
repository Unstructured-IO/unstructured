from unittest.mock import patch

import pytest

from test_unstructured.nlp.mock_nltk import (
    mock_pos_tag,
    mock_sent_tokenize,
    mock_word_tokenize,
)
from unstructured.partition import text_type


@pytest.mark.parametrize(
    ("text", "expected"),
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
    ("text", "expected"),
    [
        ("Ask the teacher for an apple.", True),
        ("Ask Me About Intellectual Property", False),  # Exceeds the cap threshold
        ("7", False),  # Fails because it is numeric
        ("intellectual property", False),  # Fails because it does not contain a verb
        ("Dal;kdjfal adawels adfjwalsdf. Addad jaja fjawlek", False),
        ("---------------Aske the teacher for an apple----------", False),  # Too many non-alpha
        ("", False),  # Doesn't have english words  # Fails because it is empty
    ],
)
def test_is_possible_narrative_text(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "pos_tag", mock_pos_tag)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_LANGUAGE_CHECKS", "true")
    is_possible_narrative = text_type.is_possible_narrative_text(text, cap_threshold=0.3)
    assert is_possible_narrative is expected


def test_narrative_text_language_checks():
    # NOTE(robinson) - This is true because we don't check english vocab if language checks
    # are set to False
    text = "Dal;kdjfal adawels adfjwalsdf. Addad jaja fjawlek"
    assert text_type.is_possible_narrative_text(text, language_checks=True) is False


def test_text_type_handles_non_english_examples(monkeypatch):
    monkeypatch.setenv("UNSTRUCTURED_LANGUAGE_CHECKS", "true")
    narrative_text = "Я говорю по-русски. Вы тоже?"
    title = "Риски"

    assert text_type.is_possible_narrative_text(narrative_text, languages=["eng"]) is False
    assert text_type.is_possible_narrative_text(narrative_text, languages=[]) is True

    assert text_type.is_possible_narrative_text(title, languages=["eng"]) is False
    assert text_type.is_possible_narrative_text(title, languages=[]) is False

    assert text_type.is_possible_title(title, languages=["eng"]) is False
    assert text_type.is_possible_title(title, languages=[]) is True


def test_text_type_handles_multi_language_examples(monkeypatch):
    monkeypatch.setenv("UNSTRUCTURED_LANGUAGE_CHECKS", "true")
    narrative_text = "Я говорю по-русски. Вы тоже? 不，我不会说俄语。"
    title = "Риски (Riesgos)"

    assert text_type.is_possible_narrative_text(narrative_text, languages=["eng"]) is False
    assert text_type.is_possible_narrative_text(narrative_text, languages=["chi", "rus"]) is True
    assert text_type.is_possible_narrative_text(narrative_text, languages=[]) is True

    assert text_type.is_possible_narrative_text(title, languages=["eng"]) is False
    assert text_type.is_possible_narrative_text(title, languages=["spa", "rus"]) is False
    assert text_type.is_possible_narrative_text(title, languages=[]) is False

    assert text_type.is_possible_title(title, languages=["eng"]) is False
    assert text_type.is_possible_title(title, languages=["spa", "rus"]) is True
    assert text_type.is_possible_title(title, languages=[]) is True


@pytest.mark.parametrize(
    ("text", "expected"),
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
        ("BTAR ADFJA L", False),  # Doesn't have english words
        ("ITEM 1A. RISK FACTORS " * 15, False),  # Title is too long
        ("/--------BREAK-------/", False),  # Contains too many non-alpha characters
        ("1.A.RISKS", True),  # Tests that "RISKS" gets flagged as an english word
        ("1. Unstructured Technologies", True),  # Make sure we're English words :-)
        ("Big/Brown/Sheet", True),
        ("LOOK AT THIS IT IS CAPS BUT NOT A TITLE.", False),
    ],
)
def test_is_possible_title(text, expected, monkeypatch):
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_LANGUAGE_CHECKS", "true")
    assert text_type.is_possible_title(text) is expected


def test_title_language_checks():
    # NOTE(robinson) - This is true because we don't check english vocab if language checks
    # are set to False
    text = "BTAR ADFJA L"
    assert text_type.is_possible_narrative_text(text, language_checks=True) is False


@pytest.mark.parametrize(
    ("text", "expected"),
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
    ("text", "expected"),
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
        ("----------------------------", False),  # Too long
    ],
)
def test_is_bulletized_text(text, expected):
    assert text_type.is_bulleted_text(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
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
    ("text", "expected"),
    [
        ("PARROT BEAK", True),
        ("Parrot Beak", True),
        ("parrot beak", True),
        ("parrot!", True),
        ("?parrot", True),
        ("zombie?parrot", True),
        ("notaWordHa 'parrot'", True),
        ("notaWordHa'parrot'", False),
        ('notaWordHa "parrot,"', True),
        ("daljdf adlfajldj ajadfa", False),
        ("BTAR ADFJA L", False),
        ("Unstructured Technologies", True),
        ("1.A.RISKS", True),  # Test crammed together words get picked up
        ("Big/Brown/Sheep", True),
    ],
)
def test_contains_english_word(text, expected, monkeypatch):
    assert text_type.contains_english_word(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Intellectual Property in the United States", True),
        ("Intellectual property helps incentivize innovation.", False),
        ("THIS IS ALL CAPS. BUT IT IS TWO SENTENCES.", False),
        ("LOOK AT THIS IT IS CAPS BUT NOT A TITLE.", True),
        ("This Has All Caps. It's Weird But Two Sentences", False),
        ("The Business Report is expected within 6 hours of closing", False),
        ("", True),
    ],
)
def test_contains_exceeds_cap_ratio(text, expected, monkeypatch):
    assert text_type.exceeds_cap_ratio(text) is expected


def test_set_caps_ratio_with_environment_variable(monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_NARRATIVE_TEXT_CAP_THRESHOLD", 0.8)

    text = "All The King's Horses. And All The King's Men."
    with patch.object(text_type, "exceeds_cap_ratio", return_value=False) as mock_exceeds:
        text_type.is_possible_narrative_text(text)

    mock_exceeds.assert_called_once_with(text, threshold=0.8)


def test_set_title_non_alpha_threshold_with_environment_variable(monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_TITLE_NON_ALPHA_THRESHOLD", 0.8)

    text = "/--------------- All the king's horses----------------/"
    with patch.object(text_type, "under_non_alpha_ratio", return_value=False) as mock_exceeds:
        text_type.is_possible_title(text)

    mock_exceeds.assert_called_once_with(text, threshold=0.8)


def test_set_narrative_text_non_alpha_threshold_with_environment_variable(monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_NARRATIVE_TEXT_NON_ALPHA_THRESHOLD", 0.8)

    text = "/--------------- All the king's horses----------------/"
    with patch.object(text_type, "under_non_alpha_ratio", return_value=False) as mock_exceeds:
        text_type.is_possible_narrative_text(text)

    mock_exceeds.assert_called_once_with(text, threshold=0.8)


def test_set_title_max_word_length_with_environment_variable(monkeypatch):
    monkeypatch.setattr(text_type, "word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    monkeypatch.setenv("UNSTRUCTURED_TITLE_MAX_WORD_LENGTH", 5)

    text = "Intellectual Property in the United States"
    assert text_type.is_possible_narrative_text(text) is False


def test_sentence_count(monkeypatch):
    monkeypatch.setattr(text_type, "sent_tokenize", mock_sent_tokenize)
    text = "Hi my name is Matt. I work with Crag."
    assert text_type.sentence_count(text) == 2


def test_item_titles():
    text = "ITEM 1(A). THIS IS A TITLE"
    assert text_type.sentence_count(text, 3) < 2


@pytest.mark.parametrize(
    ("text", "expected"),
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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("fake@gmail.com", True),
        ("Fake@gmail.com", False),
        ("fake.gmail.@gmail.com", True),
        ("fake.gmail@.@gmail.com", False),
        ("     fake@gmail.com", True),
        ("fak!/$e@gmail.com", False),
        ("", False),
    ],
)
def test_is_email_address(text, expected):
    assert text_type.is_email_address(text) is expected


def test_under_non_alpha_ratio_zero_divide():
    # Threw an error before changes
    text_type.under_non_alpha_ratio(" ")
