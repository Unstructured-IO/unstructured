"""Chunking module initializer.

Publishes the public aspects of the chunking sub-package interface.
"""

from __future__ import annotations

from unstructured.chunking.base import CHUNK_MAX_CHARS_DEFAULT, CHUNK_MULTI_PAGE_DEFAULT
from unstructured.chunking.dispatch import add_chunking_strategy

__all__ = ["CHUNK_MAX_CHARS_DEFAULT", "CHUNK_MULTI_PAGE_DEFAULT", "add_chunking_strategy"]
