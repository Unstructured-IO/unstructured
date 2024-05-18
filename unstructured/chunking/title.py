"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

from typing import Iterable, Iterator, Optional

from unstructured.chunking.base import (
    CHUNK_MULTI_PAGE_DEFAULT,
    BoundaryPredicate,
    ChunkingOptions,
    PreChunkCombiner,
    PreChunker,
    is_on_next_page,
    is_title,
)
from unstructured.documents.elements import Element
from unstructured.utils import lazyproperty


def chunk_by_title(
    elements: Iterable[Element],
    *,
    combine_text_under_n_chars: Optional[int] = None,
    include_orig_elements: Optional[bool] = None,
    max_characters: Optional[int] = None,
    multipage_sections: Optional[bool] = None,
    new_after_n_chars: Optional[int] = None,
    overlap: Optional[int] = None,
    overlap_all: Optional[bool] = None,
) -> list[Element]:
    """Uses title elements to identify sections within the document for chunking.

    Splits off into a new CompositeElement when a title is detected or if metadata changes, which
    happens when page numbers or sections change. Cuts off sections once they have exceeded a
    character length of max_characters.

    Parameters
    ----------
    elements
        A list of unstructured elements. Usually the output of a partition function.
    combine_text_under_n_chars
        Combines elements (for example a series of titles) until a section reaches a length of
        n characters. Defaults to `max_characters` which combines chunks whenever space allows.
        Specifying 0 for this argument suppresses combining of small chunks. Note this value is
        "capped" at the `new_after_n_chars` value since a value higher than that would not change
        this parameter's effect.
    include_orig_elements
        When `True` (default), add elements from pre-chunk to the `.metadata.orig_elements` field
        of the chunk(s) formed from that pre-chunk. Among other things, this allows access to
        original-element metadata that cannot be consolidated and is dropped in the course of
        chunking.
    max_characters
        Chunks elements text and text_as_html (if present) into chunks of length
        n characters (hard max)
    multipage_sections
        If True, sections can span multiple pages. Defaults to True.
    new_after_n_chars
        Cuts off new sections once they reach a length of n characters (soft max). Defaults to
        `max_characters` when not specified, which effectively disables any soft window.
        Specifying 0 for this argument causes each element to appear in a chunk by itself (although
        an element with text longer than `max_characters` will be still be split into two or more
        chunks).
    overlap
        Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
        next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
        where an oversized element is divided into multiple chunks by text-splitting.
    overlap_all
        Default: `False`. When `True`, apply overlap between "normal" chunks formed from whole
        elements and not subject to text-splitting. Use this with caution as it entails a certain
        level of "pollution" of otherwise clean semantic chunk boundaries.
    """
    opts = _ByTitleChunkingOptions.new(
        combine_text_under_n_chars=combine_text_under_n_chars,
        include_orig_elements=include_orig_elements,
        max_characters=max_characters,
        multipage_sections=multipage_sections,
        new_after_n_chars=new_after_n_chars,
        overlap=overlap,
        overlap_all=overlap_all,
    )
    return _chunk_by_title(elements, opts)


def _chunk_by_title(elements: Iterable[Element], opts: _ByTitleChunkingOptions) -> list[Element]:
    """Implementation of actual "by-title" chunking."""
    # -- Note(scanny): it might seem like over-abstraction for this to be a separate function but
    # -- it eases overriding or adding individual chunking options when customizing a stock chunker.
    pre_chunks = PreChunkCombiner(
        PreChunker.iter_pre_chunks(elements, opts), opts=opts
    ).iter_combined_pre_chunks()

    return [chunk for pre_chunk in pre_chunks for chunk in pre_chunk.iter_chunks()]


class _ByTitleChunkingOptions(ChunkingOptions):
    """Adds the by-title-specific chunking options to the base case.

    `by_title`-specific options:

    combine_text_under_n_chars
        A remedy to over-chunking caused by elements mis-identified as Title elements.
        Every Title element would start a new chunk and this setting mitigates that, at the
        expense of sometimes violating legitimate semantic boundaries.
    multipage_sections
        Indicates that page-boundaries should not be respected while chunking, i.e. elements
        appearing on two different pages can appear in the same chunk.
    """

    @lazyproperty
    def boundary_predicates(self) -> tuple[BoundaryPredicate, ...]:
        """The semantic-boundary detectors to be applied to break pre-chunks.

        For the `by_title` strategy these are sections indicated by a title (section-heading), an
        explicit section metadata item (only present for certain document types), and optionally
        page boundaries.
        """

        def iter_boundary_predicates() -> Iterator[BoundaryPredicate]:
            yield is_title
            if not self.multipage_sections:
                yield is_on_next_page()

        return tuple(iter_boundary_predicates())

    @lazyproperty
    def combine_text_under_n_chars(self) -> int:
        """Combine consecutive text pre-chunks if former is smaller than this and both will fit.

        - Does not combine table chunks with text chunks even if they would both fit in the
          chunking window.
        - Does not combine text chunks if together they would exceed the chunking window.
        - Defaults to `max_characters` when not specified.
        - Is reduced to `new_after_n_chars` when it exceeds that value.
        """
        # -- `combine_text_under_n_chars` defaults to `max_characters` when not specified --
        arg_value = self._kwargs.get("combine_text_under_n_chars")
        return self.hard_max if arg_value is None else arg_value

    @lazyproperty
    def multipage_sections(self) -> bool:
        """When False, break pre-chunks on page-boundaries."""
        arg_value = self._kwargs.get("multipage_sections")
        return CHUNK_MULTI_PAGE_DEFAULT if arg_value is None else bool(arg_value)

    def _validate(self) -> None:
        """Raise ValueError if request option-set is invalid."""
        # -- start with base-class validations --
        super()._validate()

        # -- `combine_text_under_n_chars == 0` is valid (suppresses chunk combination)
        # -- but a negative value is not
        if self.combine_text_under_n_chars < 0:
            raise ValueError(
                f"'combine_text_under_n_chars' argument must be >= 0,"
                f" got {self.combine_text_under_n_chars}"
            )

        # -- `combine_text_under_n_chars` > `max_characters` can produce behavior confusing to
        # -- users. The chunking behavior would be no different than when
        # -- `combine_text_under_n_chars == max_characters`, but if `max_characters` is left to
        # -- default (500) then it can look like chunk-combining isn't working.
        if self.combine_text_under_n_chars > self.hard_max:
            raise ValueError(
                f"'combine_text_under_n_chars' argument must not exceed `max_characters`"
                f" value, got {self.combine_text_under_n_chars} > {self.hard_max}"
            )
