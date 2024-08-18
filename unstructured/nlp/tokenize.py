from __future__ import annotations

import hashlib
import os
import sys
import tarfile
import tempfile
import urllib.request
from functools import lru_cache
from typing import Final, List, Tuple

import nltk
from nltk import pos_tag as _pos_tag
from nltk import sent_tokenize as _sent_tokenize
from nltk import word_tokenize as _word_tokenize

CACHE_MAX_SIZE: Final[int] = 128


def download_nltk_packages():
    _download_nltk_package_if_not_present(package_name="punkt_tab", package_category="tokenizers")
    _download_nltk_package_if_not_present(package_name="averaged_perceptron_tagger_eng", package_category="taggers")


def _download_nltk_package_if_not_present(package_name: str, package_category: str):
    """If the required nlt package is not present, download it."""
    try:
        nltk.find(f"{package_category}/{package_name}")
    except LookupError:
        nltk.download(package_name)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def sent_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK sentence tokenizer with LRU caching enabled."""
    _download_nltk_package_if_not_present(package_category="tokenizers", package_name="punkt_tab")
    return _sent_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK word tokenizer with LRU caching enabled."""
    _download_nltk_package_if_not_present(package_category="tokenizers", package_name="punkt_tab")
    return _word_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the NLTK POS tagger with LRU caching enabled."""
    download_nltk_packages()
    # NOTE(robinson) - Splitting into sentences before tokenizing. The helps with
    # situations like "ITEM 1A. PROPERTIES" where "PROPERTIES" can be mistaken
    # for a verb because it looks like it's in verb form an "ITEM 1A." looks like the subject.
    sentences = _sent_tokenize(text)
    parts_of_speech: list[tuple[str, str]] = []
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech
