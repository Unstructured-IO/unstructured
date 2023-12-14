"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

import collections
import copy
from typing import Any, DefaultDict, Dict, Iterable, Iterator, List, Optional, Tuple, cast

from typing_extensions import TypeAlias

from unstructured.documents.elements import (
    CompositeElement,
    ConsolidationStrategy,
    Element,
    ElementMetadata,
    RegexMetadata,
    Table,
    TableChunk,
    Title,
)
from unstructured.utils import lazyproperty

PreChunk: TypeAlias = "TablePreChunk | TextPreChunk"

# -- goes between text of each element when element-text is concatenated to form chunk --
TEXT_SEPARATOR = "\n\n"


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

    # -- validation and arg pre-processing ---------------------------

    # -- chunking window must have positive length --
    if max_characters <= 0:
        raise ValueError(f"'max_characters' argument must be > 0, got {max_characters}")

    # -- `combine_text_under_n_chars` defaults to `max_characters` when not specified and is
    # -- capped at max-chars
    if combine_text_under_n_chars is None or combine_text_under_n_chars > max_characters:
        combine_text_under_n_chars = max_characters

    # -- `combine_text_under_n_chars == 0` is valid (suppresses chunk combination)
    # -- but a negative value is not
    if combine_text_under_n_chars < 0:
        raise ValueError(
            f"'combine_text_under_n_chars' argument must be >= 0, got {combine_text_under_n_chars}",
        )

    # -- same with `new_after_n_chars` --
    if new_after_n_chars is None or new_after_n_chars > max_characters:
        new_after_n_chars = max_characters

    if new_after_n_chars < 0:
        raise ValueError(f"'new_after_n_chars' argument must be >= 0, got {new_after_n_chars}")

    # -- `new_after_n_chars` takes precendence on conflict with `combine_text_under_n_chars` --
    if combine_text_under_n_chars > new_after_n_chars:
        combine_text_under_n_chars = new_after_n_chars

    # ----------------------------------------------------------------

    pre_chunks = PreChunkCombiner(
        _split_elements_by_title_and_table(
            elements,
            multipage_sections=multipage_sections,
            new_after_n_chars=new_after_n_chars,
            max_characters=max_characters,
        ),
        max_characters,
        combine_text_under_n_chars,
    ).iter_combined_pre_chunks()

    return [chunk for pre_chunk in pre_chunks for chunk in pre_chunk.iter_chunks(max_characters)]


def _split_elements_by_title_and_table(
    elements: List[Element],
    multipage_sections: bool,
    new_after_n_chars: int,
    max_characters: int,
) -> Iterator[TextPreChunk | TablePreChunk]:
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
    pre_chunk_builder = TextPreChunkBuilder(max_characters)

    prior_element = None

    for element in elements:
        metadata_differs = (
            _metadata_differs(element, prior_element, ignore_page_numbers=multipage_sections)
            if prior_element
            else False
        )

        # -- start new pre_chunk when necessary --
        if (
            # -- Title and Table both start a new pre_chunk --
            isinstance(element, (Title, Table))
            # -- adding this element would exceed hard-maxlen for pre_chunk --
            or pre_chunk_builder.remaining_space < len(str(element))
            # -- pre_chunk already meets or exceeds soft-maxlen --
            or pre_chunk_builder.text_length >= new_after_n_chars
            # -- a semantic boundary is indicated by metadata change since prior element --
            or metadata_differs
        ):
            # -- complete any work-in-progress pre_chunk --
            yield from pre_chunk_builder.flush()

        # -- emit table and checkbox immediately since they are always isolated --
        if isinstance(element, Table):
            yield TablePreChunk(table=element)
        # -- but accumulate text elements for consolidation into a composite chunk --
        else:
            pre_chunk_builder.add_element(element)

        prior_element = element

    # -- flush "tail" pre_chunk, any partially-filled pre_chunk after last element is processed --
    yield from pre_chunk_builder.flush()


def _metadata_differs(
    element: Element,
    preceding_element: Element,
    ignore_page_numbers: bool,
) -> bool:
    """True when metadata differences between two elements indicate a semantic boundary.

    Currently this is only a section change and optionally a page-number change.
    """
    metadata1 = preceding_element.metadata
    metadata2 = element.metadata
    if metadata1.section != metadata2.section:
        return True
    if ignore_page_numbers:
        return False
    return metadata1.page_number != metadata2.page_number


# == PreChunks ===================================================================================


class TablePreChunk:
    """A pre-chunk composed of a single Table element."""

    def __init__(self, table: Table) -> None:
        self._table = table

    def iter_chunks(self, maxlen: int) -> Iterator[Table | TableChunk]:
        """Split this pre-chunk into `Table` or `TableChunk` objects maxlen or smaller."""
        text = self._table.text
        html = self._table.metadata.text_as_html or ""

        # -- only chunk a table when it's too big to swallow whole --
        if len(text) <= maxlen and len(html) <= maxlen:
            yield self._table
            return

        is_continuation = False

        while text or html:
            # -- split off the next maxchars into the next TableChunk --
            text_chunk, text = text[:maxlen], text[maxlen:]
            table_chunk = TableChunk(text=text_chunk, metadata=copy.deepcopy(self._table.metadata))

            # -- Attach maxchars of the html to the chunk. Note no attempt is made to add only the
            # -- HTML elements that *correspond* to the TextChunk.text fragment.
            if html:
                html_chunk, html = html[:maxlen], html[maxlen:]
                table_chunk.metadata.text_as_html = html_chunk

            # -- mark second and later chunks as a continuation --
            if is_continuation:
                table_chunk.metadata.is_continuation = True

            yield table_chunk

            is_continuation = True


class TextPreChunk:
    """A sequence of elements that belong to the same semantic unit within a document.

    The name "section" derives from the idea of a document-section, a heading followed by the
    paragraphs "under" that heading. That structure is not found in all documents and actual section
    content can vary, but that's the concept.

    This object is purposely immutable.
    """

    def __init__(self, elements: Iterable[Element]) -> None:
        self._elements = list(elements)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TextPreChunk):
            return False
        return self._elements == other._elements

    def combine(self, other_pre_chunk: TextPreChunk) -> TextPreChunk:
        """Return new `TextPreChunk` that combines this and `other_pre_chunk`."""
        return TextPreChunk(self._elements + other_pre_chunk._elements)

    def iter_chunks(self, maxlen: int) -> Iterator[CompositeElement]:
        """Split this pre-chunk into one or more `CompositeElement` objects maxlen or smaller."""
        text = self._text
        text_len = len(text)
        start = 0
        remaining = text_len

        while remaining > 0:
            end = min(start + maxlen, text_len)
            yield CompositeElement(text=text[start:end], metadata=self._consolidated_metadata)
            start = end
            remaining = text_len - end

    @lazyproperty
    def text_length(self) -> int:
        """Length of concatenated text of this pre-chunk, including separators."""
        # -- used by pre-chunk-combiner to identify combination candidates --
        return len(self._text)

    @lazyproperty
    def _all_metadata_values(self) -> Dict[str, List[Any]]:
        """Collection of all populated metadata values across elements.

        The resulting dict has one key for each `ElementMetadata` field that had a non-None value in
        at least one of the elements in this pre-chunk. The value of that key is a list of all those
        populated values, in element order, for example:

            {
                "filename": ["sample.docx", "sample.docx"],
                "languages": [["lat"], ["lat", "eng"]]
                ...
            }

        This preprocessing step provides the input for a specified consolidation strategy that will
        resolve the list of values for each field to a single consolidated value.
        """

        def iter_populated_fields(metadata: ElementMetadata) -> Iterator[Tuple[str, Any]]:
            """(field_name, value) pair for each non-None field in single `ElementMetadata`."""
            return (
                (field_name, value)
                for field_name, value in metadata.known_fields.items()
                if value is not None
            )

        field_values: DefaultDict[str, List[Any]] = collections.defaultdict(list)

        # -- collect all non-None field values in a list for each field, in element-order --
        for e in self._elements:
            for field_name, value in iter_populated_fields(e.metadata):
                field_values[field_name].append(value)

        return dict(field_values)

    @lazyproperty
    def _consolidated_metadata(self) -> ElementMetadata:
        """Metadata applicable to this pre-chunk as a single chunk.

        Formed by applying consolidation rules to all metadata fields across the elements of this
        pre-chunk.

        For the sake of consistency, the same rules are applied (for example, for dropping values)
        to a single-element pre-chunk too, even though metadata for such a pre-chunk is already
        "consolidated".
        """
        return ElementMetadata(**self._meta_kwargs)

    @lazyproperty
    def _consolidated_regex_meta(self) -> Dict[str, List[RegexMetadata]]:
        """Consolidate the regex-metadata in `regex_metadata_dicts` into a single dict.

        This consolidated value is suitable for use in the chunk metadata. `start` and `end`
        offsets of each regex match are also adjusted for their new positions.
        """
        chunk_regex_metadata: Dict[str, List[RegexMetadata]] = {}
        running_text_len = 0
        start_offset = 0

        for element in self._elements:
            text_len = len(element.text)
            # -- skip empty elements like `PageBreak("")` --
            if not text_len:
                continue
            # -- account for blank line between "squashed" elements, but not before first element --
            running_text_len += len(TEXT_SEPARATOR) if running_text_len else 0
            start_offset = running_text_len
            running_text_len += text_len

            if not element.metadata.regex_metadata:
                continue

            # -- consolidate any `regex_metadata` matches, adjusting the match start/end offsets --
            element_regex_metadata = copy.deepcopy(element.metadata.regex_metadata)
            for regex_name, matches in element_regex_metadata.items():
                for m in matches:
                    m["start"] += start_offset
                    m["end"] += start_offset
                chunk_matches = chunk_regex_metadata.get(regex_name, [])
                chunk_matches.extend(matches)
                chunk_regex_metadata[regex_name] = chunk_matches

        return chunk_regex_metadata

    @lazyproperty
    def _meta_kwargs(self) -> Dict[str, Any]:
        """The consolidated metadata values as a dict suitable for constructing ElementMetadata.

        This is where consolidation strategies are actually applied. The output is suitable for use
        in constructing an `ElementMetadata` object like `ElementMetadata(**self._meta_kwargs)`.
        """
        CS = ConsolidationStrategy
        field_consolidation_strategies = ConsolidationStrategy.field_consolidation_strategies()

        def iter_kwarg_pairs() -> Iterator[Tuple[str, Any]]:
            """Generate (field-name, value) pairs for each field in consolidated metadata."""
            for field_name, values in self._all_metadata_values.items():
                strategy = field_consolidation_strategies.get(field_name)
                if strategy is CS.FIRST:
                    yield field_name, values[0]
                # -- concatenate lists from each element that had one, in order --
                elif strategy is CS.LIST_CONCATENATE:
                    yield field_name, sum(values, cast(List[Any], []))
                # -- union lists from each element, preserving order of appearance --
                elif strategy is CS.LIST_UNIQUE:
                    # -- Python 3.7+ maintains dict insertion order --
                    ordered_unique_keys = {key: None for val_list in values for key in val_list}
                    yield field_name, list(ordered_unique_keys.keys())
                elif strategy is CS.REGEX:
                    yield field_name, self._consolidated_regex_meta
                elif strategy is CS.DROP:
                    continue
                else:
                    # -- not likely to hit this since we have a test in `text_elements.py` that
                    # -- ensures every ElementMetadata fields has an assigned strategy.
                    raise NotImplementedError(
                        f"metadata field {repr(field_name)} has no defined consolidation strategy"
                    )

        return dict(iter_kwarg_pairs())

    @lazyproperty
    def _text(self) -> str:
        """The concatenated text of all elements in this pre-chunk.

        Each element-text is separated from the next by a blank line ("\n\n").
        """
        return TEXT_SEPARATOR.join(e.text for e in self._elements if e.text)


class TextPreChunkBuilder:
    """An element accumulator suitable for incrementally forming a pre-chunk.

    Provides monitoring properties like `.remaining_space` and `.text_length` a pre-chunker can use
    to determine whether it should add the next element in the element stream.

    `.flush()` is used to build a `TextPreChunk` object from the accumulated elements. This method
    returns an interator that generates zero-or-one `TextPreChunk` object and is used like so:

        yield from builder.flush()

    If no elements have been accumulated, no `TextPreChunk` is generated. Flushing the builder
    clears the elements it contains so it is ready to build the next text-pre-chunk.
    """

    def __init__(self, maxlen: int) -> None:
        self._maxlen = maxlen
        self._separator_len = len(TEXT_SEPARATOR)
        self._elements: List[Element] = []

        # -- these mutable working values probably represent premature optimization but improve
        # -- performance and I expect will be welcome when processing a million elements

        # -- only includes non-empty element text, e.g. PageBreak.text=="" is not included --
        self._text_segments: List[str] = []
        # -- combined length of text-segments, not including separators --
        self._text_len: int = 0

    def add_element(self, element: Element) -> None:
        """Add `element` to this section."""
        self._elements.append(element)
        if element.text:
            self._text_segments.append(element.text)
            self._text_len += len(element.text)

    def flush(self) -> Iterator[TextPreChunk]:
        """Generate zero-or-one `PreChunk` object and clear the accumulator.

        Suitable for use to emit a PreChunk when the maximum size has been reached or a semantic
        boundary has been reached. Also to clear out a terminal pre-chunk at the end of an element
        stream.
        """
        if not self._elements:
            return
        # -- clear builder before yield so we're not sensitive to the timing of how/when this
        # -- iterator is exhausted and can add eleemnts for the next pre-chunk immediately.
        elements = self._elements[:]
        self._elements.clear()
        self._text_segments.clear()
        self._text_len = 0
        yield TextPreChunk(elements)

    @property
    def remaining_space(self) -> int:
        """Maximum text-length of an element that can be added without exceeding maxlen."""
        # -- include length of trailing separator that will go before next element text --
        separators_len = self._separator_len * len(self._text_segments)
        return self._maxlen - self._text_len - separators_len

    @property
    def text_length(self) -> int:
        """Length of the text in this pre-chunk.

        This value represents the chunk-size that would result if this pre-chunk was flushed in its
        current state. In particular, it does not include the length of a trailing separator (since
        that would only appear if an additional element was added).

        Not suitable for judging remaining space, use `.remaining_space` for that value.
        """
        # -- number of text separators present in joined text of elements. This includes only
        # -- separators *between* text segments, not one at the end. Note there are zero separators
        # -- for both 0 and 1 text-segments.
        n = len(self._text_segments)
        separator_count = n - 1 if n else 0
        return self._text_len + (separator_count * self._separator_len)


# == PreChunkCombiner ============================================================================


class PreChunkCombiner:
    """Filters pre-chunk stream to combine small pre-chunks where possible."""

    def __init__(
        self,
        pre_chunks: Iterable[PreChunk],
        maxlen: int,
        combine_text_under_n_chars: int,
    ):
        self._pre_chunks = pre_chunks
        self._maxlen = maxlen
        self._combine_text_under_n_chars = combine_text_under_n_chars

    def iter_combined_pre_chunks(self) -> Iterator[PreChunk]:
        """Generate pre-chunk objects, combining TextPreChunk objects when they'll fit in window."""
        accum = TextPreChunkAccumulator(self._maxlen)

        for pre_chunk in self._pre_chunks:
            # -- start new pre-chunk under these conditions --
            if (
                # -- a table pre-chunk is never combined --
                isinstance(pre_chunk, TablePreChunk)
                # -- don't add another pre-chunk once length has reached combination soft-max --
                or accum.text_length >= self._combine_text_under_n_chars
                # -- combining would exceed hard-max --
                or accum.remaining_space < pre_chunk.text_length
            ):
                yield from accum.flush()

            # -- a table pre-chunk is never combined so don't accumulate --
            if isinstance(pre_chunk, TablePreChunk):
                yield pre_chunk
            else:
                accum.add_pre_chunk(pre_chunk)

        yield from accum.flush()


class TextPreChunkAccumulator:
    """Accumulates, measures, and combines pre-chunk objects.

    Provides monitoring properties `.remaining_space` and `.text_length` suitable for deciding
    whether to add another pre-chunk.

    `.flush()` is used to combine the accumulated pre-chunks into a single `TextPreChunk` object.
    This method returns an interator that generates zero-or-one `TextPreChunk` objects and is used
    like so:

        yield from accum.flush()

    If no pre-chunks have been accumulated, no `TextPreChunk` is generated. Flushing the builder
    clears the pre-chunks it contains so it is ready to accept the next text-pre-chunk.
    """

    def __init__(self, maxlen: int) -> None:
        self._maxlen = maxlen
        self._pre_chunks: List[TextPreChunk] = []

    def add_pre_chunk(self, pre_chunk: TextPreChunk) -> None:
        """Add a pre-chunk to the accumulator for possible combination with next pre-chunk."""
        self._pre_chunks.append(pre_chunk)

    def flush(self) -> Iterator[TextPreChunk]:
        """Generate all accumulated pre-chunks as a single combined pre-chunk."""
        pre_chunks = self._pre_chunks

        # -- nothing to do if no pre-chunks have been accumulated --
        if not pre_chunks:
            return

        # -- otherwise combine all accumulated pre-chunk into one --
        pre_chunk = pre_chunks[0]
        for other_pre_chunk in pre_chunks[1:]:
            pre_chunk = pre_chunk.combine(other_pre_chunk)
        yield pre_chunk

        # -- and reset the accumulator (to empty) --
        pre_chunks.clear()

    @property
    def remaining_space(self) -> int:
        """Maximum size of pre-chunk that can be added without exceeding maxlen."""
        return (
            self._maxlen
            if not self._pre_chunks
            # -- an additional pre-chunk will also incur an additional separator --
            else self._maxlen - self.text_length - len(TEXT_SEPARATOR)
        )

    @property
    def text_length(self) -> int:
        """Size of concatenated text in all pre-chunks in accumulator."""
        n = len(self._pre_chunks)
        return (
            0
            if n == 0
            else sum(s.text_length for s in self._pre_chunks) + len(TEXT_SEPARATOR) * (n - 1)
        )
