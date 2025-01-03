from __future__ import annotations

import shutil
import os
from functools import lru_cache
from typing import Final, List, Tuple

import nltk
from nltk import pos_tag as _pos_tag
from nltk import sent_tokenize as _sent_tokenize
from nltk import word_tokenize as _word_tokenize

CACHE_MAX_SIZE: Final[int] = 128

# Define the NLTK data path based on the Docker image environment
NLTK_DATA_PATH = os.getenv("NLTK_DATA", "/home/notebook-user/nltk_data")
nltk.data.path.append(NLTK_DATA_PATH)

def copy_nltk_packages():
    local_path = "../../nltk_data"
    if os.path.exists(local_path):
        if not os.path.exists(NLTK_DATA_PATH):
            os.makedirs(NLTK_DATA_PATH)
        for item in os.listdir(local_path):
            s = os.path.join(local_path, item)
            d = os.path.join(NLTK_DATA_PATH, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        print(f"NLTK data copied to {NLTK_DATA_PATH}")
    else:
        print(f"Local NLTK data path does not exist: {local_path}")

def check_for_nltk_package(package_name: str, package_category: str) -> bool:
    """Checks to see if the specified NLTK package exists on the file system."""
    try:
        nltk.find(f"{package_category}/{package_name}")
        return True
    except (LookupError, OSError):
        return False


# Ensure NLTK data exists in the specified path (pre-baked in Docker)
def validate_nltk_assets():
    """Validate that required NLTK packages are preloaded in the image."""
    required_assets = [
        ("punkt_tab", "tokenizers"),
        ("averaged_perceptron_tagger_eng", "taggers"),
    ]
    for package_name, category in required_assets:
        if not check_for_nltk_package(package_name, category):
            raise RuntimeError(
                f"Required NLTK package '{package_name}' is missing. "
                f"Ensure it is baked into the Docker image at '{NLTK_DATA_PATH}'."
            )


# Validate NLTK assets at import time
validate_nltk_assets()


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
    # NOTE: Splitting into sentences before tokenizing helps with situations
    # like "ITEM 1A. PROPERTIES" where tokens can be misinterpreted.
    sentences = _sent_tokenize(text)
    parts_of_speech: list[tuple[str, str]] = []
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech
