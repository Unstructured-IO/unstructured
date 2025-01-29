from __future__ import annotations

import os
from functools import lru_cache
from typing import Final, List, Tuple

import nltk
from nltk import pos_tag as _pos_tag
from nltk import sent_tokenize as _sent_tokenize
from nltk import word_tokenize as _word_tokenize

CACHE_MAX_SIZE: Final[int] = 128


def check_for_nltk_package(package_name: str, package_category: str) -> bool:
    """Checks to see if the specified NLTK package exists on the image."""
    paths: list[str] = []
    for path in nltk.data.path:
        if not path.endswith("nltk_data"):
            path = os.path.join(path, "nltk_data")
        paths.append(path)

    try:
        nltk.find(f"{package_category}/{package_name}", paths=paths)
        return True
    except (LookupError, OSError):
        return False


def download_nltk_packages():
    """If required NLTK packages are not available, download them."""

    tagger_available = check_for_nltk_package(
        package_category="taggers",
        package_name="averaged_perceptron_tagger_eng",
    )
    tokenizer_available = check_for_nltk_package(
        package_category="tokenizers", package_name="punkt_tab"
    )

    if (not tokenizer_available) or (not tagger_available):
        nltk.download("averaged_perceptron_tagger_eng", quiet=True)
        nltk.download("punkt_tab", quiet=True)


# auto download nltk packages if the environment variable is set
if os.getenv("AUTO_DOWNLOAD_NLTK", "True").lower() == "true":
    download_nltk_packages()


@lru_cache(maxsize=CACHE_MAX_SIZE)
def sent_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK sentence tokenizer with LRU caching enabled."""
    return _sent_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK word tokenizer with LRU caching enabled."""
    return _word_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the NLTK POS tagger with LRU caching enabled."""
    # Splitting into sentences before tokenizing.
    sentences = _sent_tokenize(text)
    parts_of_speech: list[tuple[str, str]] = []
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech
