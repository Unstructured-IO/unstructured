from __future__ import annotations

from functools import lru_cache
from itertools import chain
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


def _sent_tokenize(text: str) -> List[str]:
    # -- spacy requires native str, not numpy.str_ from OCR pipelines --
    return [sent.text for sent in _nlp(str(text)).sents]


def _word_tokenize(text: str) -> List[str]:
    return [token.text for token in _nlp(str(text))]


def _pos_tag(tokens: List[str]) -> List[Tuple[str, str]]:
    doc = _nlp(str(" ".join(tokens)))
    return [(token.text, token.tag_) for token in doc]


def sent_tokenize(text: str) -> List[str]:
    """A wrapper so that we can cache the result of sentence tokenization as an
    immutable, while returning the expected return type (list)."""
    return list(_tokenize_for_cache(text))


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the spaCy word tokenizer with LRU caching enabled."""
    return _word_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the spaCy POS tagger with LRU caching enabled."""
    sentences = _sent_tokenize(text)
    if not sentences:
        return []
    tokenized_sentences = [_word_tokenize(sentence) for sentence in sentences]
    return list(chain.from_iterable(_pos_tag(tokens) for tokens in tokenized_sentences))


@lru_cache(maxsize=CACHE_MAX_SIZE)
def _tokenize_for_cache(text: str) -> Tuple[str, ...]:
    """A wrapper around the spaCy sentence tokenizer with LRU caching enabled."""
    return tuple(_sent_tokenize(text))
