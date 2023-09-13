import sys
from functools import lru_cache
from typing import List, Tuple

if sys.version_info < (3, 8):
    from typing_extensions import Final  # pragma: no cover
else:
    from typing import Final

import nltk
from nltk import Tree
from nltk import pos_tag as _pos_tag
from nltk import sent_tokenize as _sent_tokenize
from nltk import word_tokenize as _word_tokenize
from nltk.chunk import ne_chunk as _ne_chunk

CACHE_MAX_SIZE: Final[int] = 128


def _download_nltk_package_if_not_present(package_name: str, package_category: str):
    """If the required nlt package is not present, download it."""
    try:
        nltk.find(f"{package_category}/{package_name}")
    except LookupError:
        nltk.download(package_name)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def sent_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK sentence tokenizer with LRU caching enabled."""
    _download_nltk_package_if_not_present(package_category="tokenizers", package_name="punkt")
    return _sent_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK word tokenizer with LRU caching enabled."""
    _download_nltk_package_if_not_present(package_category="tokenizers", package_name="punkt")
    return _word_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the NLTK POS tagger with LRU caching enabled."""
    _download_nltk_package_if_not_present(package_category="tokenizers", package_name="punkt")
    _download_nltk_package_if_not_present(
        package_category="taggers",
        package_name="averaged_perceptron_tagger",
    )
    # NOTE(robinson) - Splitting into sentences before tokenizing. The helps with
    # situations like "ITEM 1A. PROPERTIES" where "PROPERTIES" can be mistaken
    # for a verb because it looks like it's in verb form an "ITEM 1A." looks like the subject.
    sentences = _sent_tokenize(text)
    parts_of_speech = []
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech


@lru_cache(maxsize=CACHE_MAX_SIZE)
def ne_chunk(text: str) -> Tree:
    """A wrapper around the NLTK Chunk with LRU caching enabled."""
    # NOTE(klaijan) - we will want to specify the language to download from
    # the corpus in the future when nltk or future library in use supports such language
    _download_nltk_package_if_not_present(
        package_category="chunkers",
        package_name="maxent_ne_chunker",
    )
    _download_nltk_package_if_not_present(
        package_category="corpora",
        package_name="words",
    )
    pos = pos_tag(text)
    # NOTE(klaijan) - binary=True captures everything that is name-entity as NE,
    # and not its specific NE category such as PERSON, ORGANIZATION, LOCATION.
    return _ne_chunk(pos, binary=True)
