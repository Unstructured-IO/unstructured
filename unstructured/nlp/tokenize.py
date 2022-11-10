from functools import lru_cache
from typing import List, Tuple
import sys

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from nltk import (
    pos_tag as _pos_tag,
    sent_tokenize as _sent_tokenize,
    word_tokenize as _word_tokenize,
)

CACHE_MAX_SIZE: Final[int] = 128


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
    # NOTE(robinson) - Splitting into sentences before tokenizing. The helps with
    # situations like "ITEM 1A. PROPERTIES" where "PROPERTIES" can be mistaken
    # for a verb because it looks like it's in verb form an "ITEM 1A." looks like the subject.
    sentences = _sent_tokenize(text)
    parts_of_speech = list()
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech
