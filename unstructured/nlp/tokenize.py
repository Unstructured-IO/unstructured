from __future__ import annotations

import hashlib
import os
import sys
import tarfile
import tempfile
import urllib.request
from functools import lru_cache
from typing import Any, Final, List, Tuple

import nltk
from nltk import pos_tag as _pos_tag
from nltk import sent_tokenize as _sent_tokenize
from nltk import word_tokenize as _word_tokenize

CACHE_MAX_SIZE: Final[int] = 128

NLTK_DATA_URL = "https://utic-public-cf.s3.amazonaws.com/nltk_data.tgz"
NLTK_DATA_SHA256 = "126faf671cd255a062c436b3d0f2d311dfeefcd92ffa43f7c3ab677309404d61"


def _raise_on_nltk_download(*args: Any, **kwargs: Any):
    raise ValueError("NLTK download disabled. See CVE-2024-39705")


nltk.download = _raise_on_nltk_download


# NOTE(robinson) - mimic default dir logic from NLTK
# https://github.com/nltk/nltk/
# 	blob/8c233dc585b91c7a0c58f96a9d99244a379740d5/nltk/downloader.py#L1046
def get_nltk_data_dir() -> str | None:
    """Locates the directory the nltk data will be saved too. The directory
    set by the NLTK environment variable takes highest precedence. Otherwise
    the default is determined by the rules indicated below. Returns None when
    the directory is not writable.

        On Windows, the default download directory is
        ``PYTHONHOME/lib/nltk``, where *PYTHONHOME* is the
        directory containing Python, e.g. ``C:\\Python311``.

        On all other platforms, the default directory is the first of
        the following which exists or which can be created with write
        permission: ``/usr/share/nltk_data``, ``/usr/local/share/nltk_data``,
        ``/usr/lib/nltk_data``, ``/usr/local/lib/nltk_data``, ``~/nltk_data``.
    """
    # Check if we are on GAE where we cannot write into filesystem.
    if "APPENGINE_RUNTIME" in os.environ:
        return

    # Check if we have sufficient permissions to install in a
    # variety of system-wide locations.
    for nltkdir in nltk.data.path:
        if os.path.exists(nltkdir) and nltk.internals.is_writable(nltkdir):
            return nltkdir

    # On Windows, use %APPDATA%
    if sys.platform == "win32" and "APPDATA" in os.environ:
        homedir = os.environ["APPDATA"]

    # Otherwise, install in the user's home directory.
    else:
        homedir = os.path.expanduser("~/")
        if homedir == "~/":
            raise ValueError("Could not find a default download directory")

    # NOTE(robinson) - NLTK appends nltk_data to the homedir. That's already
    # present in the tar file so we don't have to do that here.
    return homedir


def download_nltk_packages():
    nltk_data_dir = get_nltk_data_dir()

    if nltk_data_dir is None:
        raise OSError("NLTK data directory does not exist or is not writable.")

    def sha256_checksum(filename: str, block_size: int = 65536):
        sha256 = hashlib.sha256()
        with open(filename, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256.update(block)
        return sha256.hexdigest()

    with tempfile.NamedTemporaryFile() as tmp_file:
        tgz_file = tmp_file.name
        urllib.request.urlretrieve(NLTK_DATA_URL, tgz_file)

        file_hash = sha256_checksum(tgz_file)
        if file_hash != NLTK_DATA_SHA256:
            os.remove(tgz_file)
            raise ValueError(f"SHA-256 mismatch: expected {NLTK_DATA_SHA256}, got {file_hash}")

        # Extract the contents
        if not os.path.exists(nltk_data_dir):
            os.makedirs(nltk_data_dir)

        with tarfile.open(tgz_file, "r:gz") as tar:
            tar.extractall(path=nltk_data_dir)


def check_for_nltk_package(package_name: str, package_category: str) -> bool:
    """Checks to see if the specified NLTK package exists on the file system"""
    paths: list[str] = []
    for path in nltk.data.path:
        if not path.endswith("nltk_data"):
            path = os.path.join(path, "nltk_data")
        paths.append(path)

    try:
        nltk.find(f"{package_category}/{package_name}", paths=paths)
        return True
    except LookupError:
        return False


def _download_nltk_packages_if_not_present():
    """If required NLTK packages are not available, download them."""

    tagger_available = check_for_nltk_package(
        package_category="taggers",
        package_name="averaged_perceptron_tagger",
    )
    tokenizer_available = check_for_nltk_package(
        package_category="tokenizers", package_name="punkt"
    )

    if not (tokenizer_available and tagger_available):
        download_nltk_packages()


@lru_cache(maxsize=CACHE_MAX_SIZE)
def sent_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK sentence tokenizer with LRU caching enabled."""
    _download_nltk_packages_if_not_present()
    return _sent_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def word_tokenize(text: str) -> List[str]:
    """A wrapper around the NLTK word tokenizer with LRU caching enabled."""
    _download_nltk_packages_if_not_present()
    return _word_tokenize(text)


@lru_cache(maxsize=CACHE_MAX_SIZE)
def pos_tag(text: str) -> List[Tuple[str, str]]:
    """A wrapper around the NLTK POS tagger with LRU caching enabled."""
    _download_nltk_packages_if_not_present()
    # NOTE(robinson) - Splitting into sentences before tokenizing. The helps with
    # situations like "ITEM 1A. PROPERTIES" where "PROPERTIES" can be mistaken
    # for a verb because it looks like it's in verb form an "ITEM 1A." looks like the subject.
    sentences = _sent_tokenize(text)
    parts_of_speech: list[tuple[str, str]] = []
    for sentence in sentences:
        tokens = _word_tokenize(sentence)
        parts_of_speech.extend(_pos_tag(tokens))
    return parts_of_speech
