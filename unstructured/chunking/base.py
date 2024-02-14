"""Chunking objects not specific to a particular chunking strategy."""

from __future__ import annotations

import collections
import copy
from typing import Any, Callable, DefaultDict, Iterable, Iterator, Optional, Sequence, cast

import regex
from typing_extensions import Self, TypeAlias

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

# -- CONSTANTS -----------------------------------

CHUNK_MAX_CHARS_DEFAULT: int = 500
"""Hard-max chunk-length when no explicit value specified in `max_characters` argument."""

CHUNK_MULTI_PAGE_DEFAULT: bool = True
"""When False, respect page-boundaries (no two elements from different page in same chunk).

Only operative for "by_title" chunking strategy.
w"""


# -- TYPES ---------------------------------------

BoundaryPredicate: TypeAlias = Callable[[Element], bool]
"""Detects when element represents crossing a semantic boundary like section or page."""

PreChunk: TypeAlias = "TablePreChunk | TextPreChunk"
"""The kind of object produced by a pre-chunker."""


# ================================================================================================
# CHUNKING OPTIONS
# ================================================================================================


class ChunkingOptions:
    """Specifies parameters of optional chunking behaviors.

    Parameters
    ----------
    max_characters
        Hard-maximum text-length of chunk. A chunk longer than this will be split mid-text and be
        emitted as two or more chunks.
    new_after_n_chars
        Preferred approximate chunk size. A chunk composed of elements totalling this size or
        greater is considered "full" and will not be enlarged by adding another element, even if it
        will fit within the remaining `max_characters` for that chunk. Defaults to `max_characters`
        when not specified, which effectively disables this behavior. Specifying 0 for this
        argument causes each element to appear in a chunk by itself (although an element with text
        longer than `max_characters` will be still be split into two or more chunks).
    multipage_sections
        Indicates that page-boundaries should not be respected while chunking, i.e. elements
        appearing on two different pages can appear in the same chunk.
    combine_text_under_n_chars
        Provides a way to "recombine" small chunks formed by breaking on a semantic boundary. Only
        relevant for a chunking strategy that specifies higher-level semantic boundaries to be
        respected, like "section" or "page". Recursively combines two adjacent pre-chunks when the
        first pre-chunk is smaller than this threshold. "Recursively" here means the resulting
        pre-chunk can be combined with the next pre-chunk if it is still under the length threshold.
        Defaults to `max_characters` which combines chunks whenever space allows. Specifying 0 for
        this argument suppresses combining of small chunks. Note this value is "capped" at the
        `new_after_n_chars` value since a value higher than that would not change this parameter's
        effect.
    overlap
        Specifies the length of a string ("tail") to be drawn from each chunk and prefixed to the
        next chunk as a context-preserving mechanism. By default, this only applies to split-chunks
        where an oversized element is divided into multiple chunks by text-splitting.
    overlap_all
        Default: `False`. When `True`, apply overlap between "normal" chunks formed from whole
        elements and not subject to text-splitting. Use this with caution as it entails a certain
        level of "pollution" of otherwise clean semantic chunk boundaries.
    text_splitting_separators
        A sequence of strings like `("\n", " ")` to be used as target separators during
        text-splitting. Text-splitting only applies to splitting an oversized element into two or
        more chunks. These separators are tried in the specified order until one is found in the
        string to be split. The default separator is `""` which matches between any two characters.
        This separator should not be specified in this sequence because it is always the separator
        of last-resort. Note that because the separator is removed during text-splitting, only
        whitespace character sequences are suitable.
    """

    def __init__(
        self,
        combine_text_under_n_chars: Optional[int] = None,
        max_characters: int = CHUNK_MAX_CHARS_DEFAULT,
        multipage_sections: bool = CHUNK_MULTI_PAGE_DEFAULT,
        new_after_n_chars: Optional[int] = None,
        overlap: int = 0,
        overlap_all: bool = False,
        text_splitting_separators: Sequence[str] = ("\n", " "),
    ):
        self._combine_text_under_n_chars_arg = combine_text_under_n_chars
        self._max_characters = max_characters
        self._multipage_sections = multipage_sections
        self._new_after_n_chars_arg = new_after_n_chars
        self._overlap = overlap
        self._overlap_all = overlap_all
        self._text_splitting_separators = text_splitting_separators

    @classmethod
    def new(
        cls,
        combine_text_under_n_chars: Optional[int] = None,
        max_characters: int = CHUNK_MAX_CHARS_DEFAULT,
        multipage_sections: bool = CHUNK_MULTI_PAGE_DEFAULT,
        new_after_n_chars: Optional[int] = None,
        overlap: int = 0,
        overlap_all: bool = False,
        text_splitting_separators: Sequence[str] = ("\n", " "),
    ) -> Self:
        """Construct validated instance.

        Raises `ValueError` on invalid arguments like overlap > max_chars.
        """
        self = cls(
            combine_text_under_n_chars,
            max_characters,
            multipage_sections,
            new_after_n_chars,
            overlap,
            overlap_all,
            text_splitting_separators,
        )
        self._validate()
        return self

    @lazyproperty
    def combine_text_under_n_chars(self) -> int:
        """Combine consecutive text pre-chunks if former is smaller than this and both will fit.

        - Does not combine table chunks with text chunks even if they would both fit in the
          chunking window.
        - Does not combine text chunks if together they would exceed the chunking window.
        - Defaults to `max_characters` when not specified.
        - Is reduced to `new_after_n_chars` when it exceeds that value.
        """
        max_characters = self._max_characters
        soft_max = self.soft_max
        arg = self._combine_text_under_n_chars_arg

        # -- `combine_text_under_n_chars` defaults to `max_characters` when not specified and is
        # -- capped at max-chars
        combine_text_under_n_chars = max_characters if arg is None or arg > max_characters else arg

        # -- `new_after_n_chars` takes precendence on conflict with `combine_text_under_n_chars` --
        return soft_max if combine_text_under_n_chars > soft_max else combine_text_under_n_chars

    @lazyproperty
    def hard_max(self) -> int:
        """The maximum size for a chunk.

        A pre-chunk will only exceed this size when it contains exactly one element which by itself
        exceeds this size. Such a pre-chunk is subject to mid-text splitting later in the chunking
        process.
        """
        return self._max_characters

    @lazyproperty
    def inter_chunk_overlap(self) -> int:
        """Characters of overlap to add between chunks.

        This applies only to boundaries between chunks formed from whole elements and not to
        text-splitting boundaries that arise from splitting an oversized element.
        """
        return self.overlap if self._overlap_all else 0

    @lazyproperty
    def multipage_sections(self) -> bool:
        """When False, break pre-chunks on page-boundaries."""
        return self._multipage_sections

    @lazyproperty
    def overlap(self) -> int:
        """The number of characters to overlap text when splitting chunks mid-text.

        The actual overlap will not exceed this number of characters but may be less as required to
        respect splitting-character boundaries.
        """
        return self._overlap

    @lazyproperty
    def soft_max(self) -> int:
        """A pre-chunk of this size or greater is considered full.

        ??? Is a value of 0 valid? It would produce the behavior: "put each element into its own
        chunk".
        """
        max_chars = self._max_characters
        new_after_n_chars = self._new_after_n_chars_arg
        return (
            max_chars
            if (new_after_n_chars is None or new_after_n_chars < 0 or new_after_n_chars > max_chars)
            else new_after_n_chars
        )

    @lazyproperty
    def split(self) -> Callable[[str], tuple[str, str]]:
        """A text-splitting function suitable for splitting the text of an oversized pre-chunk.

        The function is pre-configured with the chosen chunking window size and any other applicable
        options specified by the caller as part of this chunking-options instance.
        """
        return _TextSplitter(self)

    @lazyproperty
    def text_separator(self) -> str:
        """The string to insert between elements when concatenating their text for a chunk.

        Right now this is just "\n\n" (a blank line in plain text), but having this here rather
        than as a module-level constant provides a way for us to easily make it user-configurable
        in future if we want to.
        """
        return "\n\n"

    @lazyproperty
    def text_splitting_separators(self) -> tuple[str, ...]:
        """Sequence of text-splitting target strings to be used in order of preference."""
        return tuple(self._text_splitting_separators)

    def _validate(self) -> None:
        """Raise ValueError if requestion option-set is invalid."""
        max_characters = self._max_characters
        # -- chunking window must have positive length --
        if max_characters <= 0:
            raise ValueError(f"'max_characters' argument must be > 0," f" got {max_characters}")

        # -- `combine_text_under_n_chars == 0` is valid (suppresses chunk combination)
        # -- but a negative value is not
        combine_text_under_n_chars = self._combine_text_under_n_chars_arg
        if combine_text_under_n_chars is not None and combine_text_under_n_chars < 0:
            raise ValueError(
                f"'combine_text_under_n_chars' argument must be >= 0,"
                f" got {combine_text_under_n_chars}"
            )

        # -- a negative value for `new_after_n_chars` is assumed to
        # -- be a mistake the caller will want to know about
        new_after_n_chars = self._new_after_n_chars_arg
        if new_after_n_chars is not None and new_after_n_chars < 0:
            raise ValueError(
                f"'new_after_n_chars' argument must be >= 0," f" got {new_after_n_chars}"
            )

        # -- overlap must be less than max-chars or the chunk text will
        # -- never be consumed
        # TODO: consider a heuristic like never overlap more than half,
        # otherwise there could be corner cases leading to an infinite
        # loop (I think).
        if self._overlap >= max_characters:
            raise ValueError(f"'overlap' must be less than max_characters," f" got {self._overlap}")


class _TextSplitter:
    """Provides a text-splitting function configured on construction.

    Text is split on the best-available separator, falling-back from the preferred separator
    through a sequence of alternate separators.

    - The separator is removed by splitting so only whitespace strings are suitable separators.
    - A "blank-line" ("\n\n") is unlikely to occur in an element as it would have been used as an
      element boundary during partitioning.

    This is a *callable* object. Constructing it essentially produces a function:

        split = _TextSplitter(opts)
        fragment, remainder = split(s)

    This allows it to be configured with length-options etc. on construction and used throughout a
    chunking operation on a given element-stream.
    """

    def __init__(self, opts: ChunkingOptions):
        self._opts = opts

    def __call__(self, s: str) -> tuple[str, str]:
        """Return pair of strings split from `s` on the best match of configured patterns.

        The first string is the split, the second is the remainder of the string. The split string
        will never be longer than `maxlen`. The separators are tried in order until a match is
        found. The last separator is "" which matches between any two characters so there will
        always be a split.

        The separator is removed and does not appear in the split or remainder.

        An `s` that is already less than the maximum length is returned unchanged with no remainder.
        This allows this function to be called repeatedly with the remainder until it is consumed
        and returns a remainder of "".
        """
        maxlen = self._opts.hard_max

        if len(s) <= maxlen:
            return s, ""

        for p, sep_len in self._patterns:
            # -- length of separator must be added to include that separator when it happens to be
            # -- located exactly at maxlen. Otherwise the search-from-end regex won't find it.
            fragment, remainder = self._split_from_maxlen(p, sep_len, s)
            if (
                # -- no available split with this separator --
                not fragment
                # -- split did not progress, consuming part of the string --
                or len(remainder) >= len(s)
            ):
                continue
            return fragment.rstrip(), remainder.lstrip()

        # -- the terminal "" pattern is not actually executed via regex since its implementation is
        # -- trivial and provides a hard back-stop here in this method. No separator is used between
        # -- tail and remainder on arb-char split.
        return s[:maxlen].rstrip(), s[maxlen - self._opts.overlap :].lstrip()

    @lazyproperty
    def _patterns(self) -> tuple[tuple[regex.Pattern[str], int], ...]:
        """Sequence of (pattern, len) pairs to match against.

        Patterns appear in order of preference, those following are "fall-back" patterns to be used
        if no match of a prior pattern is found.

        NOTE these regexes search *from the end of the string*, which is what the "(?r)" bit
        specifies. This is much more efficient than starting at the beginning of the string which
        could result in hundreds of matches before the desired one.
        """
        separators = self._opts.text_splitting_separators
        return tuple((regex.compile(f"(?r){sep}"), len(sep)) for sep in separators)

    def _split_from_maxlen(
        self, pattern: regex.Pattern[str], sep_len: int, s: str
    ) -> tuple[str, str]:
        """Return (split, remainder) pair split from `s` on the right-most match before `maxlen`.

        Returns `"", s` if no suitable match was found. Also returns `"", s` if splitting on this
        separator produces a split shorter than the required overlap (which would produce an
        infinite loop).

        `split` will never be longer than `maxlen` and there is no longer split available using
        `pattern`.

        The separator is removed and does not appear in either the split or remainder.
        """
        maxlen, overlap = self._opts.hard_max, self._opts.overlap

        # -- A split not longer than overlap will not progress (infinite loop). On the right side,
        # -- need to extend search range to include a separator located exactly at maxlen.
        match = pattern.search(s, pos=overlap + 1, endpos=maxlen + sep_len)
        if match is None:
            return "", s

        # -- characterize match location
        match_start, match_end = match.span()
        # -- matched separator is replaced by single-space in overlap string --
        separator = " "

        # -- in multi-space situation, fragment may have trailing whitespace because match is from
        # -- right to left
        fragment = s[:match_start].rstrip()
        # -- remainder can have leading space when match is on "\n" followed by spaces --
        raw_remainder = s[match_end:].lstrip()

        if overlap <= len(separator):
            return fragment, raw_remainder

        # -- compute overlap --
        tail_len = overlap - len(separator)
        tail = fragment[-tail_len:].lstrip()
        overlapped_remainder = tail + separator + raw_remainder
        return fragment, overlapped_remainder


# ================================================================================================
# BASE PRE-CHUNKER
# ================================================================================================


class BasePreChunker:
    """Base-class for per-strategy pre-chunkers.

    The pre-chunker's responsibilities are:

    - **Segregate semantic units.** Identify semantic unit boundaries and segregate elements on
      either side of those boundaries into different sections. In this case, the primary indicator
      of a semantic boundary is a `Title` element. A page-break (change in page-number) is also a
      semantic boundary when `multipage_sections` is `False`.

    - **Minimize chunk count for each semantic unit.** Group the elements within a semantic unit
      into sections as big as possible without exceeding the chunk window size.

    - **Minimize chunks that must be split mid-text.** Precompute the text length of each section
      and only produce a section that exceeds the chunk window size when there is a single element
      with text longer than that window.

    A Table element is placed into a section by itself. CheckBox elements are dropped.

    The "by-title" strategy specifies breaking on section boundaries; a `Title` element indicates
    a new "section", hence the "by-title" designation.
    """

    def __init__(self, elements: Iterable[Element], opts: ChunkingOptions):
        self._elements = elements
        self._opts = opts

    @classmethod
    def iter_pre_chunks(
        cls, elements: Iterable[Element], opts: ChunkingOptions
    ) -> Iterator[PreChunk]:
        """Generate pre-chunks from the element-stream provided on construction."""
        return cls(elements, opts)._iter_pre_chunks()

    def _iter_pre_chunks(self) -> Iterator[PreChunk]:
        """Generate pre-chunks from the element-stream provided on construction.

        A *pre-chunk* is the largest sub-sequence of elements that will both fit within the
        chunking window and respects the semantic boundary rules of the chunking strategy. When a
        single element exceeds the chunking window size it is placed in a pre-chunk by itself and
        is subject to mid-text splitting in the second phase of the chunking process.
        """
        pre_chunk_builder = PreChunkBuilder(self._opts)

        for element in self._elements:
            # -- start new pre-chunk when necessary --
            if self._is_in_new_semantic_unit(element) or not pre_chunk_builder.will_fit(element):
                yield from pre_chunk_builder.flush()

            # -- add this element to the work-in-progress (WIP) pre-chunk --
            pre_chunk_builder.add_element(element)

        # -- flush "tail" pre-chunk, any partially-filled pre-chunk after last element is
        # -- processed
        yield from pre_chunk_builder.flush()

    @lazyproperty
    def _boundary_predicates(self) -> tuple[BoundaryPredicate, ...]:
        """The semantic-boundary detectors to be applied to break pre-chunks."""
        return ()

    def _is_in_new_semantic_unit(self, element: Element) -> bool:
        """True when `element` begins a new semantic unit such as a section or page."""
        # -- all detectors need to be called to update state and avoid double counting
        # -- boundaries that happen to coincide, like Table and new section on same element.
        # -- Using `any()` would short-circuit on first True.
        semantic_boundaries = [pred(element) for pred in self._boundary_predicates]
        return any(semantic_boundaries)


# ================================================================================================
# PRE-CHUNK SUB-TYPES
# ================================================================================================


class TablePreChunk:
    """A pre-chunk composed of a single Table element."""

    def __init__(self, table: Table, overlap_prefix: str, opts: ChunkingOptions) -> None:
        self._table = table
        self._overlap_prefix = overlap_prefix
        self._opts = opts

    def iter_chunks(self) -> Iterator[Table | TableChunk]:
        """Split this pre-chunk into `Table` or `TableChunk` objects maxlen or smaller."""
        maxlen = self._opts.hard_max
        text_remainder = self._text
        html_remainder = self._table.metadata.text_as_html or ""

        # -- only chunk a table when it's too big to swallow whole --
        if len(text_remainder) <= maxlen and len(html_remainder) <= maxlen:
            # -- but the overlap-prefix must be added to its text --
            yield Table(text=text_remainder, metadata=copy.deepcopy(self._table.metadata))
            return

        split = self._opts.split
        is_continuation = False

        while text_remainder or html_remainder:
            # -- split off the next chunk-worth of characters into a TableChunk --
            chunk_text, text_remainder = split(text_remainder)
            table_chunk = TableChunk(text=chunk_text, metadata=copy.deepcopy(self._table.metadata))

            # -- Attach maxchars of the html to the chunk. Note no attempt is made to add only the
            # -- HTML elements that *correspond* to the TextChunk.text fragment.
            if html_remainder:
                chunk_html, html_remainder = html_remainder[:maxlen], html_remainder[maxlen:]
                table_chunk.metadata.text_as_html = chunk_html

            # -- mark second and later chunks as a continuation --
            if is_continuation:
                table_chunk.metadata.is_continuation = True

            yield table_chunk

            is_continuation = True

    @lazyproperty
    def overlap_tail(self) -> str:
        """The portion of this chunk's text to be repeated as a prefix in the next chunk.

        This value is the empty-string ("") when either the `.overlap` length option is `0` or
        `.overlap_all` is `False`. When there is a text value, it is stripped of both leading and
        trailing whitespace.
        """
        overlap = self._opts.inter_chunk_overlap
        return self._text[-overlap:].strip() if overlap else ""

    @lazyproperty
    def _text(self) -> str:
        """The text for this chunk, including the overlap-prefix when present."""
        overlap_prefix = self._overlap_prefix
        table_text = self._table.text
        # -- use row-separator between overlap and table-text --
        return overlap_prefix + "\n" + table_text if overlap_prefix else table_text


class TextPreChunk:
    """A sequence of elements that belong to the same semantic unit within a document.

    The name "section" derives from the idea of a document-section, a heading followed by the
    paragraphs "under" that heading. That structure is not found in all documents and actual section
    content can vary, but that's the concept.

    This object is purposely immutable.
    """

    def __init__(
        self, elements: Iterable[Element], overlap_prefix: str, opts: ChunkingOptions
    ) -> None:
        self._elements = list(elements)
        self._overlap_prefix = overlap_prefix
        self._opts = opts

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TextPreChunk):
            return False
        return self._overlap_prefix == other._overlap_prefix and self._elements == other._elements

    def can_combine(self, pre_chunk: TextPreChunk) -> bool:
        """True when `pre_chunk` can be combined with this one without exceeding size limits."""
        if len(self._text) >= self._opts.combine_text_under_n_chars:
            return False
        # -- avoid duplicating length computations by doing a trial-combine which is just as
        # -- efficient and definitely more robust than hoping two different computations of combined
        # -- length continue to get the same answer as the code evolves. Only possible because
        # -- `.combine()` is non-mutating.
        combined_len = len(self.combine(pre_chunk)._text)

        return combined_len <= self._opts.hard_max

    def combine(self, other_pre_chunk: TextPreChunk) -> TextPreChunk:
        """Return new `TextPreChunk` that combines this and `other_pre_chunk`."""
        # -- combined pre-chunk gets the overlap-prefix of the first pre-chunk. The second overlap
        # -- is automatically incorporated at the end of the first chunk, where it originated.
        return TextPreChunk(
            self._elements + other_pre_chunk._elements,
            overlap_prefix=self._overlap_prefix,
            opts=self._opts,
        )

    def iter_chunks(self) -> Iterator[CompositeElement]:
        """Split this pre-chunk into one or more `CompositeElement` objects maxlen or smaller."""
        split = self._opts.split
        metadata = self._consolidated_metadata

        remainder = self._text

        while remainder:
            s, remainder = split(remainder)
            yield CompositeElement(text=s, metadata=metadata)

    @lazyproperty
    def overlap_tail(self) -> str:
        """The portion of this chunk's text to be repeated as a prefix in the next chunk.

        This value is the empty-string ("") when either the `.overlap` length option is `0` or
        `.overlap_all` is `False`. When there is a text value, it is stripped of both leading and
        trailing whitespace.
        """
        overlap = self._opts.inter_chunk_overlap
        return self._text[-overlap:].strip() if overlap else ""

    @lazyproperty
    def _all_metadata_values(self) -> dict[str, list[Any]]:
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

        def iter_populated_fields(metadata: ElementMetadata) -> Iterator[tuple[str, Any]]:
            """(field_name, value) pair for each non-None field in single `ElementMetadata`."""
            return (
                (field_name, value)
                for field_name, value in metadata.known_fields.items()
                if value is not None
            )

        field_values: DefaultDict[str, list[Any]] = collections.defaultdict(list)

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
    def _consolidated_regex_meta(self) -> dict[str, list[RegexMetadata]]:
        """Consolidate the regex-metadata in `regex_metadata_dicts` into a single dict.

        This consolidated value is suitable for use in the chunk metadata. `start` and `end`
        offsets of each regex match are also adjusted for their new positions.
        """
        chunk_regex_metadata: dict[str, list[RegexMetadata]] = {}
        separator_len = len(self._opts.text_separator)
        running_text_len = len(self._overlap_prefix) if self._overlap_prefix else 0
        start_offset = running_text_len

        for element in self._elements:
            text_len = len(element.text)
            # -- skip empty elements like `PageBreak("")` --
            if not text_len:
                continue
            # -- account for blank line between "squashed" elements, but not at start of text --
            running_text_len += separator_len if running_text_len else 0
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

    def _iter_text_segments(self) -> Iterator[str]:
        """Generate overlap text and each element text segment in order.

        Empty text segments are not included.
        """
        if self._overlap_prefix:
            yield self._overlap_prefix
        for e in self._elements:
            if not e.text:
                continue
            yield e.text

    @lazyproperty
    def _meta_kwargs(self) -> dict[str, Any]:
        """The consolidated metadata values as a dict suitable for constructing ElementMetadata.

        This is where consolidation strategies are actually applied. The output is suitable for use
        in constructing an `ElementMetadata` object like `ElementMetadata(**self._meta_kwargs)`.
        """
        CS = ConsolidationStrategy
        field_consolidation_strategies = ConsolidationStrategy.field_consolidation_strategies()

        def iter_kwarg_pairs() -> Iterator[tuple[str, Any]]:
            """Generate (field-name, value) pairs for each field in consolidated metadata."""
            for field_name, values in self._all_metadata_values.items():
                strategy = field_consolidation_strategies.get(field_name)
                if strategy is CS.FIRST:
                    yield field_name, values[0]
                # -- concatenate lists from each element that had one, in order --
                elif strategy is CS.LIST_CONCATENATE:
                    yield field_name, sum(values, cast("list[Any]", []))
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
        text_separator = self._opts.text_separator
        return text_separator.join(self._iter_text_segments())


# ================================================================================================
# PRE-CHUNKING ACCUMULATORS
# ------------------------------------------------------------------------------------------------
# Accumulators encapsulate the work of grouping elements and later pre-chunks to form the larger
# pre-chunk and combined-pre-chunk items central to unstructured chunking.
# ================================================================================================


class PreChunkBuilder:
    """An element accumulator suitable for incrementally forming a pre-chunk.

    Provides the trial method `.will_fit()` a pre-chunker can use to determine whether it should add
    the next element in the element stream.

    `.flush()` is used to build a PreChunk object from the accumulated elements. This method
    returns an iterator that generates zero-or-one `TextPreChunk` or `TablePreChunk` object and is
    used like so:

        yield from builder.flush()

    If no elements have been accumulated, no `PreChunk` instance is generated. Flushing the builder
    clears the elements it contains so it is ready to build the next pre-chunk.
    """

    def __init__(self, opts: ChunkingOptions) -> None:
        self._opts = opts
        self._separator_len = len(opts.text_separator)
        self._elements: list[Element] = []

        # -- overlap is only between pre-chunks so starts empty --
        self._overlap_prefix: str = ""
        # -- only includes non-empty element text, e.g. PageBreak.text=="" is not included --
        self._text_segments: list[str] = []
        # -- combined length of text-segments, not including separators --
        self._text_len: int = 0

    def add_element(self, element: Element) -> None:
        """Add `element` to this section."""
        self._elements.append(element)
        if element.text:
            self._text_segments.append(element.text)
            self._text_len += len(element.text)

    def flush(self) -> Iterator[PreChunk]:
        """Generate zero-or-one `PreChunk` object and clear the accumulator.

        Suitable for use to emit a PreChunk when the maximum size has been reached or a semantic
        boundary has been reached. Also to clear out a terminal pre-chunk at the end of an element
        stream.
        """
        if not self._elements:
            return

        pre_chunk = (
            TablePreChunk(self._elements[0], self._overlap_prefix, self._opts)
            if isinstance(self._elements[0], Table)
            # -- copy list, don't use original or it may change contents as builder proceeds --
            else TextPreChunk(list(self._elements), self._overlap_prefix, self._opts)
        )
        # -- clear builder before yield so we're not sensitive to the timing of how/when this
        # -- iterator is exhausted and can add elements for the next pre-chunk immediately.
        self._reset_state(pre_chunk.overlap_tail)
        yield pre_chunk

    def will_fit(self, element: Element) -> bool:
        """True when `element` can be added to this prechunk without violating its limits.

        There are several limits:
        - A `Table` element will never fit with any other element. It will only fit in an empty
          pre-chunk.
        - No element will fit in a pre-chunk that already contains a `Table` element.
        - A text-element will not fit in a pre-chunk that already exceeds the soft-max
          (aka. new_after_n_chars).
        - A text-element will not fit when together with the elements already present it would
          exceed the hard-max (aka. max_characters).
        """
        # -- an empty pre-chunk will accept any element (including an oversized-element) --
        if len(self._elements) == 0:
            return True
        # -- a `Table` will not fit in a non-empty pre-chunk --
        if isinstance(element, Table):
            return False
        # -- no element will fit in a pre-chunk that already contains a `Table` element --
        if isinstance(self._elements[0], Table):
            return False
        # -- a pre-chunk that already exceeds the soft-max is considered "full" --
        if self._text_length > self._opts.soft_max:
            return False
        # -- don't add an element if it would increase total size beyond the hard-max --
        if self._remaining_space < len(element.text):
            return False
        return True

    @property
    def _remaining_space(self) -> int:
        """Maximum text-length of an element that can be added without exceeding maxlen."""
        # -- include length of trailing separator that will go before next element text --
        separators_len = self._separator_len * len(self._text_segments)
        return self._opts.hard_max - self._text_len - separators_len

    def _reset_state(self, overlap_prefix: str) -> None:
        """Set working-state values back to "empty", ready to accumulate next pre-chunk."""
        self._overlap_prefix = overlap_prefix
        self._elements.clear()
        self._text_segments = [overlap_prefix] if overlap_prefix else []
        self._text_len = len(overlap_prefix)

    @property
    def _text_length(self) -> int:
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


class PreChunkCombiner:
    """Filters pre-chunk stream to combine small pre-chunks where possible."""

    def __init__(self, pre_chunks: Iterable[PreChunk], opts: ChunkingOptions):
        self._pre_chunks = pre_chunks
        self._opts = opts

    def iter_combined_pre_chunks(self) -> Iterator[PreChunk]:
        """Generate pre-chunk objects, combining TextPreChunk objects when they'll fit in window."""
        accum = TextPreChunkAccumulator(self._opts)

        for pre_chunk in self._pre_chunks:
            # -- a table pre-chunk is never combined --
            if isinstance(pre_chunk, TablePreChunk):
                yield from accum.flush()
                yield pre_chunk
                continue

            # -- finish accumulating pre-chunk when it's full --
            if not accum.will_fit(pre_chunk):
                yield from accum.flush()

            accum.add_pre_chunk(pre_chunk)

        yield from accum.flush()


class TextPreChunkAccumulator:
    """Accumulates, measures, and combines text pre-chunks.

    Used for combining pre-chunks for chunking strategies like "by-title" that can potentially
    produce undersized chunks and offer the `combine_text_under_n_chars` option. Note that only
    sequential `TextPreChunk` objects can be combined. A `TablePreChunk` is never combined with
    another pre-chunk.

    Provides `.add_pre_chunk()` allowing a pre-chunk to be added to the chunk and provides
    monitoring properties `.remaining_space` and `.text_length` suitable for deciding whether to add
    another pre-chunk.

    `.flush()` is used to combine the accumulated pre-chunks into a single `TextPreChunk` object.
    This method returns an interator that generates zero-or-one `TextPreChunk` objects and is used
    like so:

        yield from accum.flush()

    If no pre-chunks have been accumulated, no `TextPreChunk` is generated. Flushing the builder
    clears the pre-chunks it contains so it is ready to accept the next text-pre-chunk.
    """

    def __init__(self, opts: ChunkingOptions) -> None:
        self._opts = opts
        self._pre_chunk: Optional[TextPreChunk] = None

    def add_pre_chunk(self, pre_chunk: TextPreChunk) -> None:
        """Add a pre-chunk to the accumulator for possible combination with next pre-chunk."""
        self._pre_chunk = (
            pre_chunk if self._pre_chunk is None else self._pre_chunk.combine(pre_chunk)
        )

    def flush(self) -> Iterator[TextPreChunk]:
        """Generate accumulated pre-chunk as a single combined pre-chunk.

        Does not generate a pre-chunk when none has been accumulated.
        """
        # -- nothing to do if no pre-chunk has been accumulated --
        if not self._pre_chunk:
            return
        # -- otherwise generate the combined pre-chunk --
        yield self._pre_chunk
        # -- and reset the accumulator (to empty) --
        self._pre_chunk = None

    def will_fit(self, pre_chunk: TextPreChunk) -> bool:
        """True when there is room for `pre_chunk` in accumulator.

        An empty accumulator always has room. Otherwise there is only room when `pre_chunk` can be
        combined with any other pre-chunks in the accumulator without exceeding the combination
        limits specified for the chunking run.
        """
        # -- an empty accumulator always has room --
        if self._pre_chunk is None:
            return True

        return self._pre_chunk.can_combine(pre_chunk)


# ================================================================================================
# CHUNK BOUNDARY PREDICATES
# ------------------------------------------------------------------------------------------------
# A *boundary predicate* is a function that takes an element and returns True when the element
# represents the start of a new semantic boundary (such as section or page) to be respected in
# chunking.
#
# Some of the functions below *are* a boundary predicate and others *construct* a boundary
# predicate.
#
# These can be mixed and matched to produce different chunking behaviors like "by_title" or left
# out altogether to produce "by_element" behavior.
#
# The effective lifetime of the function that produce a predicate (rather than directly being one)
# is limited to a single element-stream because these retain state (e.g. current page number) to
# determine when a semantic boundary has been crossed.
# ================================================================================================


def is_in_next_section() -> BoundaryPredicate:
    """Not a predicate itself, calling this returns a predicate that triggers on each new section.

    The lifetime of the returned callable cannot extend beyond a single element-stream because it
    stores current state (current section) that is particular to that element stream.

    A "section" of this type is particular to the EPUB format (so far) and not to be confused with
    a "section" composed of a section-heading (`Title` element) followed by content elements.

    The returned predicate tracks the current section, starting at `None`. Calling with an element
    with a different value for `metadata.section` returns True, indicating the element starts a new
    section boundary, and updates the enclosed section name ready for the next transition.
    """
    current_section: Optional[str] = None
    is_first: bool = True

    def section_changed(element: Element) -> bool:
        nonlocal current_section, is_first

        section = element.metadata.section

        # -- The first element never reports a section break, it starts the first section of the
        # -- document. That section could be named (section is non-None) or anonymous (section is
        # -- None). We don't really have to care.
        if is_first:
            current_section = section
            is_first = False
            return False

        # -- An element with a `None` section is assumed to continue the current section. It never
        # -- updates the current-section because once set, the current-section is "sticky" until
        # -- replaced by another explicit section.
        if section is None:
            return False

        # -- another element with the same section continues that section --
        if section == current_section:
            return False

        current_section = section
        return True

    return section_changed


def is_on_next_page() -> BoundaryPredicate:
    """Not a predicate itself, calling this returns a predicate that triggers on each new page.

    The lifetime of the returned callable cannot extend beyond a single element-stream because it
    stores current state (current page-number) that is particular to that element stream.

    The returned predicate tracks the "current" page-number, starting at 1. An element with a
    greater page number returns True, indicating the element starts a new page boundary, and
    updates the enclosed page-number ready for the next transition.

    An element with `page_number == None` or a page-number lower than the stored value is ignored
    and returns False.
    """
    current_page_number: int = 1
    is_first: bool = True

    def page_number_incremented(element: Element) -> bool:
        nonlocal current_page_number, is_first

        page_number = element.metadata.page_number

        # -- The first element never reports a page break, it starts the first page of the
        # -- document. That page could be numbered (page_number is non-None) or not. If it is not
        # -- numbered we assign it page-number 1.
        if is_first:
            current_page_number = page_number or 1
            is_first = False
            return False

        # -- An element with a `None` page-number is assumed to continue the current page. It never
        # -- updates the current-page-number because once set, the current-page-number is "sticky"
        # -- until replaced by a different explicit page-number.
        if page_number is None:
            return False

        if page_number == current_page_number:
            return False

        # -- it's possible for a page-number to decrease. We don't expect that, but if it happens
        # -- we consider it a page-break.
        current_page_number = page_number
        return True

    return page_number_incremented


def is_title(element: Element) -> bool:
    """True when `element` is a `Title` element, False otherwise."""
    return isinstance(element, Title)
