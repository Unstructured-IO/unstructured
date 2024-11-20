from typing import List, Tuple
from unittest.mock import patch

import nltk

from test_unstructured.nlp.mock_nltk import mock_sent_tokenize, mock_word_tokenize
from unstructured.nlp import tokenize


def test_nltk_packages_download_if_not_present():
    with patch.object(nltk, "find", side_effect=LookupError):
        with patch.object(tokenize, "download_nltk_packages") as mock_download:
            tokenize._download_nltk_packages_if_not_present()

    mock_download.assert_called_once()


def test_nltk_packages_do_not_download_if():
    with patch.object(nltk, "find"), patch.object(nltk, "download") as mock_download:
        tokenize._download_nltk_packages_if_not_present()

    mock_download.assert_not_called()


def mock_pos_tag(tokens: List[str]) -> List[Tuple[str, str]]:
    pos_tags: List[Tuple[str, str]] = []
    for token in tokens:
        if token.lower() == "ask":
            pos_tags.append((token, "VB"))
        else:
            pos_tags.append((token, ""))
    return pos_tags


def test_pos_tag():
    parts_of_speech = tokenize.pos_tag("ITEM 2A. PROPERTIES")
    assert parts_of_speech == [
        ("ITEM", "NNP"),
        ("2A", "CD"),
        (".", "."),
        ("PROPERTIES", "NN"),
    ]


def test_word_tokenize_caches(monkeypatch):
    monkeypatch.setattr(tokenize, "_word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(tokenize, "_pos_tag", mock_pos_tag)
    tokenize.word_tokenize.cache_clear()
    assert tokenize.word_tokenize.cache_info().currsize == 0
    tokenize.word_tokenize("Greetings! I am from outer space.")
    assert tokenize.word_tokenize.cache_info().currsize == 1


def test_sent_tokenize_caches(monkeypatch):
    monkeypatch.setattr(tokenize, "_sent_tokenize", mock_sent_tokenize)
    monkeypatch.setattr(tokenize, "_word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(tokenize, "_pos_tag", mock_pos_tag)
    tokenize.sent_tokenize.cache_clear()
    assert tokenize.sent_tokenize.cache_info().currsize == 0
    tokenize.sent_tokenize("Greetings! I am from outer space.")
    assert tokenize.sent_tokenize.cache_info().currsize == 1


def test_pos_tag_caches(monkeypatch):
    monkeypatch.setattr(tokenize, "_word_tokenize", mock_word_tokenize)
    monkeypatch.setattr(tokenize, "_pos_tag", mock_pos_tag)
    tokenize.pos_tag.cache_clear()
    assert tokenize.pos_tag.cache_info().currsize == 0
    tokenize.pos_tag("Greetings! I am from outer space.")
    assert tokenize.pos_tag.cache_info().currsize == 1


def test_tokenizers_functions_run():
    sentence = "I am a big brown bear. What are you?"
    tokenize.sent_tokenize(sentence)
    tokenize.word_tokenize(sentence)
    tokenize.pos_tag(sentence)
