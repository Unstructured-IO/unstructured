"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

from typing import Iterator, List, Optional

from unstructured.chunking.base import (
    BoundaryPredicate,
    ChunkingOptions,
    PreChunk,
    PreChunkBuilder,
    PreChunkCombiner,
    is_in_next_section,
    is_on_next_page,
    is_title,
)
from unstructured.documents.elements import Element


def chunk_by_title(
    elements: List[Element],
    multipage_sections: bool = True,
    combine_text_under_n_chars: Optional[int] = None,
    new_after_n_chars: Optional[int] = None,
    max_characters: int = 500,
) -> List[Element]:
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
    """
    opts = ChunkingOptions.new(
        combine_text_under_n_chars=combine_text_under_n_chars,
        max_characters=max_characters,
        multipage_sections=multipage_sections,
        new_after_n_chars=new_after_n_chars,
    )

    pre_chunks = PreChunkCombiner(
        _split_elements_by_title_and_table(elements, opts), opts=opts
    ).iter_combined_pre_chunks()

    return [chunk for pre_chunk in pre_chunks for chunk in pre_chunk.iter_chunks()]


def _split_elements_by_title_and_table(
    elements: List[Element], opts: ChunkingOptions
) -> Iterator[PreChunk]:
    """Implements "pre-chunker" responsibilities.

    A _section_ can be thought of as a "pre-chunk", generally determining the size and contents of a
    chunk formed by the subsequent "chunker" process. The only exception occurs when a single
    element is too big to fit in the chunk window and the chunker splits it into two or more chunks
    divided mid-text. The pre-chunker never divides an element mid-text.

    The pre-chunker's responsibilities are:

        * **Segregate semantic units.** Identify semantic unit boundaries and segregate elements on
          either side of those boundaries into different pre-chunks. In this case, the primary
          indicator of a semantic boundary is a `Title` element. A page-break (change in
          page-number) is also a semantic boundary when `multipage_sections` is `False`.

        * **Minimize chunk count for each semantic unit.** Group the elements within a semantic unit
          into pre-chunks as big as possible without exceeding the chunk window size.

        * **Minimize chunks that must be split mid-text.** Precompute the text length of each
          pre-chunk and only produce a pre-chunk that exceeds the chunk window size when there is a
          single element with text longer than that window.

    A Table or Checkbox element is placed into a pre-chunk by itself.
    """

    # ========================================================================================

    def iter_boundary_predicates() -> Iterator[BoundaryPredicate]:
        yield is_title
        yield is_in_next_section()
        if not opts.multipage_sections:
            yield is_on_next_page()

    # -- the semantic-boundary detectors to be applied to break pre-chunks --
    boundary_predicates = tuple(iter_boundary_predicates())

    def is_in_new_semantic_unit(element: Element) -> bool:
        """True when `element` begins a new semantic unit such as a section or page."""
        # -- all detectors need to be called to update state and avoid double counting
        # -- boundaries that happen to coincide, like Table and new section on same element.
        # -- Using `any()` would short-circuit on first True.
        semantic_boundaries = [pred(element) for pred in boundary_predicates]
        return any(semantic_boundaries)

    # ----------------------------------------------------------------------------------------
    # -- these bits ^^^ will get migrated to `BasePreChunker` helper methods in the next PR --
    # ========================================================================================

    pre_chunk_builder = PreChunkBuilder(opts)

    for element in elements:
        # -- start new pre_chunk when necessary --
        if is_in_new_semantic_unit(element) or not pre_chunk_builder.will_fit(element):
            yield from pre_chunk_builder.flush()

        # -- add this element to the work-in-progress (WIP) pre-chunk --
        pre_chunk_builder.add_element(element)

    # -- flush "tail" pre_chunk, any partially-filled pre_chunk after last element is processed --
    yield from pre_chunk_builder.flush()
