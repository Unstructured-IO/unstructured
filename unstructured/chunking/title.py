"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

from typing import Iterator, Optional

from unstructured.chunking.base import (
    CHUNK_MAX_CHARS_DEFAULT,
    CHUNK_MULTI_PAGE_DEFAULT,
    BasePreChunker,
    BoundaryPredicate,
    ChunkingOptions,
    PreChunkCombiner,
    is_in_next_section,
    is_on_next_page,
    is_title,
)
from unstructured.documents.elements import Element
from unstructured.utils import lazyproperty


def chunk_by_title(
    elements: list[Element],
    multipage_sections: bool = CHUNK_MULTI_PAGE_DEFAULT,
    combine_text_under_n_chars: Optional[int] = None,
    new_after_n_chars: Optional[int] = None,
    max_characters: int = CHUNK_MAX_CHARS_DEFAULT,
    overlap: int = 0,
    overlap_all: bool = False,
) -> list[Element]:
    """Uses title elements to identify sections within the document for chunking.

    Splits off into a new CompositeElement when a title is detected or if metadata changes, which
    happens when page numbers or sections change. Cuts off sections once they have exceeded a
    character length of max_characters.

    Parameters
    ----------
    elements
        A list of unstructured elements. Usually the output of a partition function.
    multipage_sections
        If True, sections can span multiple pages. Defaults to True.
    combine_text_under_n_chars
        Combines elements (for example a series of titles) until a section reaches a length of
        n characters. Defaults to `max_characters` which combines chunks whenever space allows.
        Specifying 0 for this argument suppresses combining of small chunks. Note this value is
        "capped" at the `new_after_n_chars` value since a value higher than that would not change
        this parameter's effect.
    new_after_n_chars
        Cuts off new sections once they reach a length of n characters (soft max). Defaults to
        `max_characters` when not specified, which effectively disables any soft window.
        Specifying 0 for this argument causes each element to appear in a chunk by itself (although
        an element with text longer than `max_characters` will be still be split into two or more
        chunks).
    max_characters
        Chunks elements text and text_as_html (if present) into chunks of length
        n characters (hard max)
    overlap
        Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
        next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
        where an oversized element is divided into multiple chunks by text-splitting.
    overlap_all
        Default: `False`. When `True`, apply overlap between "normal" chunks formed from whole
        elements and not subject to text-splitting. Use this with caution as it entails a certain
        level of "pollution" of otherwise clean semantic chunk boundaries.
    """
    opts = ChunkingOptions.new(
        combine_text_under_n_chars=combine_text_under_n_chars,
        max_characters=max_characters,
        multipage_sections=multipage_sections,
        new_after_n_chars=new_after_n_chars,
        overlap=overlap,
        overlap_all=overlap_all,
    )

    pre_chunks = PreChunkCombiner(
        _ByTitlePreChunker.iter_pre_chunks(elements, opts), opts=opts
    ).iter_combined_pre_chunks()

    return [chunk for pre_chunk in pre_chunks for chunk in pre_chunk.iter_chunks()]


class _ByTitlePreChunker(BasePreChunker):
    """Pre-chunker for the "by_title" chunking strategy.

    The "by-title" strategy specifies breaking on section boundaries; a `Title` element indicates a
    new "section", hence the "by-title" designation.
    """

    @lazyproperty
    def _boundary_predicates(self) -> tuple[BoundaryPredicate, ...]:
        """The semantic-boundary detectors to be applied to break pre-chunks."""

        def iter_boundary_predicates() -> Iterator[BoundaryPredicate]:
            yield is_title
            yield is_in_next_section()
            if not self._opts.multipage_sections:
                yield is_on_next_page()

        return tuple(iter_boundary_predicates())
