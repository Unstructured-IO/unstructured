from __future__ import annotations

from functools import lru_cache
from typing import Final, List, Tuple

import spacy

CACHE_MAX_SIZE: Final[int] = 128

try:
    _nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError(
        "The spacy model 'en_core_web_sm' is required but not installed. "
        "Install it with: python -m spacy download en_core_web_sm"
    )


def _process(text: str) -> spacy.tokens.Doc:
    """Run the spaCy pipeline once. All public functions extract what they need from the Doc."""
    # -- str() handles numpy.str_ from OCR pipelines --
    return _nlp(str(text))


def sent_tokenize(text: str) -> List[str]:
    """A wrapper so that we can cache the result of sentence tokenization as an
    immutable, while returning the expected return type (list)."""
    return list(_tokenize_for_cache(text))


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the spaCy word tokenizer with LRU caching enabled."""
    return [token.text for token in _process(text)]


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the spaCy POS tagger with LRU caching enabled."""
    doc = _process(text)
    return [(token.text, token.tag_) for token in doc]


@lru_cache(maxsize=CACHE_MAX_SIZE)
def _tokenize_for_cache(text: str) -> Tuple[str, ...]:
    """A wrapper around the spaCy sentence tokenizer with LRU caching enabled."""
    return tuple(sent.text for sent in _process(text).sents)
