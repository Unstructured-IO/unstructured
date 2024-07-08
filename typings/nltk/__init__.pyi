from __future__ import annotations

from nltk import data, internals
from nltk.data import find
from nltk.downloader import download
from nltk.tag import pos_tag
from nltk.tokenize import sent_tokenize, word_tokenize

__all__ = [
    "data",
    "download",
    "find",
    "internals",
    "pos_tag",
    "sent_tokenize",
    "word_tokenize",
]
