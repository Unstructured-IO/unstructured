"""Chunking module initializer.

Publishes the public aspects of the chunking sub-package interface.
"""

from __future__ import annotations

from unstructured.chunking.base import CHUNK_MAX_CHARS_DEFAULT, CHUNK_MULTI_PAGE_DEFAULT
from unstructured.chunking.dispatch import (
    Chunker,
    add_chunking_strategy,
    register_chunking_strategy,
)

__all__ = [
    "CHUNK_MAX_CHARS_DEFAULT",
    "CHUNK_MULTI_PAGE_DEFAULT",
    "add_chunking_strategy",
    # -- these must be published to allow pluggable chunkers in other code-bases --
    "Chunker",
    "register_chunking_strategy",
]
