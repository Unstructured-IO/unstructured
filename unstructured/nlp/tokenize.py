from __future__ import annotations

import hashlib
import importlib
import logging
import os
import shutil
import sys
import sysconfig
import tempfile
import urllib.request
from functools import lru_cache
from typing import Final, List, Tuple

import spacy

logger = logging.getLogger(__name__)

CACHE_MAX_SIZE: Final[int] = 128

_SPACY_MODEL_NAME: Final[str] = "en_core_web_sm"
_SPACY_MODEL_VERSION: Final[str] = "3.8.0"
_SPACY_MODEL_URL: Final[str] = (
    f"https://github.com/explosion/spacy-models/releases/download/"
    f"{_SPACY_MODEL_NAME}-{_SPACY_MODEL_VERSION}/"
    f"{_SPACY_MODEL_NAME}-{_SPACY_MODEL_VERSION}-py3-none-any.whl"
)
_SPACY_MODEL_SHA256: Final[str] = "1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85"


_DOWNLOAD_TIMEOUT_SECONDS: Final[int] = 120


def _download_with_timeout(url: str, dest: str) -> None:
    """Download a URL to a local file with a socket-level timeout."""
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as resp:
        with open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)


def _install_spacy_model() -> None:
    """Download and install the pinned spaCy model wheel using the `installer` library."""
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile
    from installer.utils import get_launcher_kind

    with tempfile.TemporaryDirectory() as tmp:
        whl_path = os.path.join(tmp, f"{_SPACY_MODEL_NAME}-{_SPACY_MODEL_VERSION}-py3-none-any.whl")
        logger.info("Downloading spaCy model %s %s …", _SPACY_MODEL_NAME, _SPACY_MODEL_VERSION)
        _download_with_timeout(_SPACY_MODEL_URL, whl_path)

        with open(whl_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        if sha256 != _SPACY_MODEL_SHA256:
            raise RuntimeError(
                f"Hash mismatch for {_SPACY_MODEL_NAME}: "
                f"expected {_SPACY_MODEL_SHA256}, got {sha256}"
            )

        # Install into a staging directory to avoid races with other processes
        staging = os.path.join(tmp, "staging")
        paths = sysconfig.get_paths()
        staged_paths = paths.copy()
        staged_paths["purelib"] = staging
        staged_paths["platlib"] = staging

        destination = SchemeDictionaryDestination(
            staged_paths,
            interpreter=sys.executable,
            script_kind=get_launcher_kind(),
        )
        with WheelFile.open(whl_path) as source:
            install(source=source, destination=destination, additional_metadata={})

        # Move installed packages from staging into real site-packages
        site_packages = paths["purelib"]
        for item in os.listdir(staging):
            src = os.path.join(staging, item)
            dst = os.path.join(site_packages, item)
            if os.path.exists(dst):
                logger.info("Skipping %s, already exists (concurrent install)", item)
                continue
            shutil.move(src, dst)

    logger.info("Installed %s %s", _SPACY_MODEL_NAME, _SPACY_MODEL_VERSION)


def _load_spacy_model() -> spacy.language.Language:
    try:
        return spacy.load(_SPACY_MODEL_NAME)
    except OSError:
        _install_spacy_model()
        importlib.invalidate_caches()
        return spacy.load(_SPACY_MODEL_NAME)


_nlp = _load_spacy_model()


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
