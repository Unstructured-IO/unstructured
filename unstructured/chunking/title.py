"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

from functools import cached_property
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


def chunk_by_title(
    elements: Iterable[Element],
    *,
    combine_text_under_n_chars: Optional[int] = None,
    include_orig_elements: Optional[bool] = None,
    max_characters: Optional[int] = None,
    max_tokens: Optional[int] = None,
    multipage_sections: Optional[bool] = None,
    new_after_n_chars: Optional[int] = None,
    new_after_n_tokens: Optional[int] = None,
    overlap: Optional[int] = None,
    overlap_all: Optional[bool] = None,
    tokenizer: Optional[str] = None,
    repeat_table_headers: Optional[bool] = None,
    skip_table_chunking: Optional[bool] = None,
    isolate_table: Optional[bool] = None,
) -> list[Element]:
    """Uses title elements to identify sections within the document for chunking.

    Splits off into a new CompositeElement when a title is detected or if metadata changes, which
    happens when page numbers or sections change. Cuts off sections once they have exceeded a
    character length of max_characters (or token count of max_tokens).

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
        n characters (hard max). Mutually exclusive with `max_tokens`.
    max_tokens
        Chunks elements into chunks of n tokens (hard max). Requires `tokenizer` to be specified.
        Mutually exclusive with `max_characters`.
    multipage_sections
        If True, sections can span multiple pages. Defaults to True.
    new_after_n_chars
        Cuts off new sections once they reach a length of n characters (soft max). Defaults to
        `max_characters` when not specified, which effectively disables any soft window.
        Specifying 0 for this argument causes each element to appear in a chunk by itself (although
        an element with text longer than `max_characters` will be still be split into two or more
        chunks).
    new_after_n_tokens
        Token-based equivalent of `new_after_n_chars`. Cuts off new sections once they reach
        n tokens (soft max). Requires `max_tokens` and `tokenizer` to be specified.
    overlap
        Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
        next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
        where an oversized element is divided into multiple chunks by text-splitting.
    overlap_all
        Default: `False`. When `True`, apply overlap between "normal" chunks formed from whole
        elements and not subject to text-splitting. Use this with caution as it entails a certain
        level of "pollution" of otherwise clean semantic chunk boundaries.
    tokenizer
        The tokenizer to use for token-based chunking. Can be either an encoding name (e.g.,
        "cl100k_base") or a model name (e.g., "gpt-4"). Required when using `max_tokens`.
    repeat_table_headers
        Default: `True`. When `True`, repeated table-header behavior is enabled for chunked table
        continuations. Specify `False` to opt out and preserve legacy table-chunk behavior.
    skip_table_chunking
        Default: `False`. When `True`, `Table` elements are passed through unchanged without
        being split into `TableChunk` elements, regardless of their size.
    isolate_table
        Default: `True`. When `True`, `Table` and `TableChunk` elements are always staged in
        their own pre-chunk and never combined with adjacent non-table elements. Specify
        `False` to allow tables to share pre-chunks with adjacent elements (the pre-#4307
        behavior).
    """
    opts = _ByTitleChunkingOptions.new(
        combine_text_under_n_chars=combine_text_under_n_chars,
        include_orig_elements=include_orig_elements,
        max_characters=max_characters,
        max_tokens=max_tokens,
        multipage_sections=multipage_sections,
        new_after_n_chars=new_after_n_chars,
        new_after_n_tokens=new_after_n_tokens,
        overlap=overlap,
        overlap_all=overlap_all,
        tokenizer=tokenizer,
        repeat_table_headers=repeat_table_headers,
        skip_table_chunking=skip_table_chunking,
        isolate_table=isolate_table,
    )
    return _chunk_by_title(elements, opts)


def iter_chunks_by_title(
    elements: Iterable[Element],
    *,
    combine_text_under_n_chars: Optional[int] = None,
    include_orig_elements: Optional[bool] = None,
    max_characters: Optional[int] = None,
    max_tokens: Optional[int] = None,
    multipage_sections: Optional[bool] = None,
    new_after_n_chars: Optional[int] = None,
    new_after_n_tokens: Optional[int] = None,
    overlap: Optional[int] = None,
    overlap_all: Optional[bool] = None,
    tokenizer: Optional[str] = None,
    repeat_table_headers: Optional[bool] = None,
    skip_table_chunking: Optional[bool] = None,
    isolate_table: Optional[bool] = None,
) -> Iterator[Element]:
    """Lazy `chunk_by_title`: yields each chunk as it is formed instead of returning a list.

    Accepts the same options and produces the same chunks in the same order; see
    `chunk_by_title` for the parameter documentation. Prefer this form when `elements` is
    itself lazy and the chunks are consumed one at a time, e.g. written straight to a file.
    The formed chunks are then never accumulated in a list.

    The bound on elements held at once is looser here than in `iter_chunk_elements()`. This
    strategy recombines undersized pre-chunks, and it cannot know a pre-chunk is finished until
    it has read the following one and found it does not fit, so it holds about two pre-chunks
    rather than one. When the whole document fits in one or two chunking windows that lookahead
    reaches the end of `elements`, meaning the first chunk costs the entire source; this is
    inherent to combining and is not avoided by `combine_text_under_n_chars=0`.

    Whatever that bound, it covers the elements this function holds, not what each chunk carries.
    Under the default `include_orig_elements=True` a chunk retains the elements it was formed
    from in `metadata.orig_elements` -- text elements by reference, a table as a copy -- so their
    `metadata.image_base64` payloads live as long as the chunk does. Streaming alone therefore
    gives little relief when those payloads are the bottleneck; pass
    `include_orig_elements=False` as well.

    Chunking has always been lazy internally; this exposes that pipeline rather than adding
    a second one. Options are still validated eagerly, when this function is called, not
    when the returned iterator is first advanced, so an invalid combination -- or an unknown
    `tokenizer`, when chunking by `max_tokens` -- raises here.
    """
    opts = _ByTitleChunkingOptions.new(
        combine_text_under_n_chars=combine_text_under_n_chars,
        include_orig_elements=include_orig_elements,
        max_characters=max_characters,
        max_tokens=max_tokens,
        multipage_sections=multipage_sections,
        new_after_n_chars=new_after_n_chars,
        new_after_n_tokens=new_after_n_tokens,
        overlap=overlap,
        overlap_all=overlap_all,
        tokenizer=tokenizer,
        repeat_table_headers=repeat_table_headers,
        skip_table_chunking=skip_table_chunking,
        isolate_table=isolate_table,
    )
    return _iter_chunks_by_title(elements, opts)


def _chunk_by_title(elements: Iterable[Element], opts: _ByTitleChunkingOptions) -> list[Element]:
    """Implementation of actual "by-title" chunking."""
    # -- Note(scanny): it might seem like over-abstraction for this to be a separate function but
    # -- it eases overriding or adding individual chunking options when customizing a stock chunker.
    return list(_iter_chunks_by_title(elements, opts))


def _iter_chunks_by_title(
    elements: Iterable[Element], opts: _ByTitleChunkingOptions
) -> Iterator[Element]:
    """Lazy implementation of actual "by-title" chunking, shared with `_chunk_by_title`."""
    pre_chunks = PreChunkCombiner(
        PreChunker.iter_pre_chunks(elements, opts), opts=opts
    ).iter_combined_pre_chunks()

    for pre_chunk in pre_chunks:
        yield from pre_chunk.iter_chunks()
        # -- release the emitted pre-chunk before advancing, as basic chunking does, so the
        # -- elements held at a transition are the combiner's inherent two pre-chunks, not three
        del pre_chunk


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

    @cached_property
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

    @cached_property
    def combine_text_under_n_chars(self) -> int:
        """Combine consecutive text pre-chunks if former is smaller than this and both will fit.

        - Does not combine text chunks if together they would exceed the chunking window.
        - Defaults to `max_characters` when not specified.
        - Is reduced to `new_after_n_chars` when it exceeds that value.
        """
        # -- `combine_text_under_n_chars` defaults to `max_characters` when not specified --
        arg_value = self._kwargs.get("combine_text_under_n_chars")
        return self.hard_max if arg_value is None else arg_value

    @cached_property
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
