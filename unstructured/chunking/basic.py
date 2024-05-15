"""Implementation of baseline chunking.

This is the "plain-vanilla" chunking strategy. All the fundamental chunking behaviors are present in
this strategy and also in all other strategies. Those are:

- Maximally fill each chunk with sequential elements.
- Isolate oversized elements and divide (only) those chunks by text-splitting.
- Overlap when requested.

"Fancier" strategies add higher-level semantic-unit boundaries to be respected. For example, in the
by-title strategy, section boundaries are respected, meaning a chunk never contains text from two
different sections. When a new section is detected the current chunk is closed and a new one
started.
"""

from __future__ import annotations

from typing import Iterable, Optional

from unstructured.chunking.base import ChunkingOptions, PreChunker
from unstructured.documents.elements import Element


def chunk_elements(
    elements: Iterable[Element],
    *,
    include_orig_elements: Optional[bool] = None,
    max_characters: Optional[int] = None,
    new_after_n_chars: Optional[int] = None,
    overlap: Optional[int] = None,
    overlap_all: Optional[bool] = None,
) -> list[Element]:
    """Combine sequential `elements` into chunks, respecting specified text-length limits.

    Produces a sequence of `CompositeElement`, `Table`, and `TableChunk` elements (chunks).

    Parameters
    ----------
    elements
        A list of unstructured elements. Usually the output of a partition function.
    include_orig_elements
        When `True` (default), add elements from pre-chunk to the `.metadata.orig_elements` field
        of the chunk(s) formed from that pre-chunk. Among other things, this allows access to
        original-element metadata that cannot be consolidated and is dropped in the course of
        chunking.
    max_characters
        Hard maximum chunk length. No chunk will exceed this length. A single element that exceeds
        this length will be divided into two or more chunks using text-splitting.
    new_after_n_chars
        A chunk that of this length or greater is not extended to include the next element, even if
        that element would fit without exceeding `max_characters`. A "soft max" length that can be
        used in conjunction with `max_characters` to limit most chunks to a preferred length while
        still allowing larger elements to be included in a single chunk without resorting to
        text-splitting. Defaults to `max_characters` when not specified, which effectively disables
        any soft window. Specifying 0 for this argument causes each element to appear in a chunk by
        itself (although an element with text longer than `max_characters` will be still be split
        into two or more chunks).
    overlap
        Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
        next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
        where an oversized element is divided into multiple chunks by text-splitting.
    overlap_all
        Default: `False`. When `True`, apply overlap between "normal" chunks formed from whole
        elements and not subject to text-splitting. Use this with caution as it produces a certain
        level of "pollution" of otherwise clean semantic chunk boundaries.
    """
    # -- raises ValueError on invalid parameters --
    opts = _BasicChunkingOptions.new(
        include_orig_elements=include_orig_elements,
        max_characters=max_characters,
        new_after_n_chars=new_after_n_chars,
        overlap=overlap,
        overlap_all=overlap_all,
    )

    return _chunk_elements(elements, opts)


def _chunk_elements(elements: Iterable[Element], opts: _BasicChunkingOptions) -> list[Element]:
    """Implementation of actual basic chunking."""
    # -- Note(scanny): it might seem like over-abstraction for this to be a separate function but
    # -- it eases overriding or adding individual chunking options when customizing a stock chunker.
    return [
        chunk
        for pre_chunk in PreChunker.iter_pre_chunks(elements, opts)
        for chunk in pre_chunk.iter_chunks()
    ]


class _BasicChunkingOptions(ChunkingOptions):
    """Options for `basic` chunking."""
