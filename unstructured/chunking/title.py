"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

import copy
import functools
import inspect
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, cast

from typing_extensions import ParamSpec, TypeAlias

from unstructured.documents.elements import (
    CompositeElement,
    Element,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.utils import lazyproperty

_Section: TypeAlias = "_NonTextSection | _TableSection | _TextSection"

# -- goes between text of each element when element-text is concatenated to form chunk --
TEXT_SEPARATOR = "\n\n"


def chunk_table_element(element: Table, max_characters: int = 500) -> List[Table | TableChunk]:
    text = element.text
    html = getattr(element, "text_as_html", None)

    if len(text) <= max_characters and (  # type: ignore
        html is None or len(html) <= max_characters  # type: ignore
    ):
        return [element]

    chunks: List[Table | TableChunk] = []
    metadata = copy.copy(element.metadata)
    is_continuation = False

    while text or html:
        text_chunk, text = text[:max_characters], text[max_characters:]
        table_chunk = TableChunk(text=text_chunk, metadata=copy.copy(metadata))

        if html:
            html_chunk, html = html[:max_characters], html[max_characters:]
            table_chunk.metadata.text_as_html = html_chunk

        if is_continuation:
            table_chunk.metadata.is_continuation = True

        chunks.append(table_chunk)
        is_continuation = True

    return chunks


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
        A list of unstructured elements. Usually the output of a partition functions.
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

    chunked_elements: List[Element] = []

    sections = _SectionCombiner(
        _split_elements_by_title_and_table(
            elements,
            multipage_sections=multipage_sections,
            new_after_n_chars=new_after_n_chars,
            max_characters=max_characters,
        ),
        max_characters,
        combine_text_under_n_chars,
    ).iter_combined_sections()

    for section in sections:
        if isinstance(section, _NonTextSection):
            chunked_elements.append(section.element)
            continue

        elif isinstance(section, _TableSection):
            chunked_elements.extend(chunk_table_element(section.table, max_characters))
            continue

        text = ""
        metadata = section.elements[0].metadata
        start_char = 0

        for element_idx, element in enumerate(section.elements):
            # -- concatenate all element text in section into `text` --
            if isinstance(element, Text):
                # -- add a blank line between "squashed" elements --
                text += "\n\n" if text else ""
                start_char = len(text)
                text += element.text

            # -- "chunk" metadata should include union of list-items in all its elements --
            for attr, value in vars(element.metadata).items():
                if isinstance(value, list):
                    value = cast(List[Any], value)
                    # -- get existing (list) value from chunk_metadata --
                    _value = getattr(metadata, attr, []) or []
                    _value.extend(item for item in value if item not in _value)
                    setattr(metadata, attr, _value)

            # -- consolidate any `regex_metadata` matches, adjusting the match start/end offsets --
            element_regex_metadata = element.metadata.regex_metadata
            # -- skip the first element because it is "alredy consolidated" and otherwise this would
            # -- duplicate it.
            if element_regex_metadata and element_idx > 0:
                if metadata.regex_metadata is None:
                    metadata.regex_metadata = {}
                chunk_regex_metadata = metadata.regex_metadata
                for regex_name, matches in element_regex_metadata.items():
                    for m in matches:
                        m["start"] += start_char
                        m["end"] += start_char
                    chunk_matches = chunk_regex_metadata.get(regex_name, [])
                    chunk_matches.extend(matches)
                    chunk_regex_metadata[regex_name] = chunk_matches

        # -- split chunk into CompositeElements objects maxlen or smaller --
        text_len = len(text)
        start = 0
        remaining = text_len

        while remaining > 0:
            end = min(start + max_characters, text_len)
            chunked_elements.append(CompositeElement(text=text[start:end], metadata=metadata))
            start = end
            remaining = text_len - end

    return chunked_elements


def _split_elements_by_title_and_table(
    elements: List[Element],
    multipage_sections: bool,
    new_after_n_chars: int,
    max_characters: int,
) -> Iterator[_TextSection | _TableSection | _NonTextSection]:
    """Implements "sectioner" responsibilities.

    A _section_ can be thought of as a "pre-chunk", generally determining the size and contents of a
    chunk formed by the subsequent "chunker" process. The only exception occurs when a single
    element is too big to fit in the chunk window and the chunker splits it into two or more chunks
    divided mid-text. The sectioner never divides an element mid-text.

    The sectioner's responsibilities are:

        * **Segregate semantic units.** Identify semantic unit boundaries and segregate elements on
          either side of those boundaries into different sections. In this case, the primary
          indicator of a semantic boundary is a `Title` element. A page-break (change in
          page-number) is also a semantic boundary when `multipage_sections` is `False`.

        * **Minimize chunk count for each semantic unit.** Group the elements within a semantic unit
          into sections as big as possible without exceeding the chunk window size.

        * **Minimize chunks that must be split mid-text.** Precompute the text length of each
          section and only produce a section that exceeds the chunk window size when there is a
          single element with text longer than that window.
    """
    section_builder = _TextSectionBuilder(max_characters)

    prior_element = None

    for element in elements:
        metadata_differs = (
            _metadata_differs(element, prior_element, ignore_page_numbers=multipage_sections)
            if prior_element
            else False
        )

        # -- start new section when necessary --
        if (
            # -- Title, Table, and non-Text element (CheckBox) all start a new section --
            isinstance(element, (Title, Table))
            or not isinstance(element, Text)
            # -- adding this element would exceed hard-maxlen for section --
            or section_builder.remaining_space < len(str(element))
            # -- section already meets or exceeds soft-maxlen --
            or section_builder.text_length >= new_after_n_chars
            # -- a semantic boundary is indicated by metadata change since prior element --
            or metadata_differs
        ):
            # -- complete any work-in-progress section --
            yield from section_builder.flush()

        # -- emit table and checkbox immediately since they are always isolated --
        if isinstance(element, Table):
            yield _TableSection(table=element)
        elif not isinstance(element, Text):
            yield _NonTextSection(element)
        # -- but accumulate text elements for consolidation into a composite chunk --
        else:
            section_builder.add_element(element)

        prior_element = element

    # -- flush "tail" section, any partially-filled section after last element is processed --
    yield from section_builder.flush()


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


_P = ParamSpec("_P")


def add_chunking_strategy() -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """Decorator for chunking text.

    Uses title elements to identify sections within the document for chunking. Splits off a new
    section when a title is detected or if metadata changes, which happens when page numbers or
    sections change. Cuts off sections once they have exceeded a character length of
    max_characters.
    """

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        if func.__doc__ and (
            "chunking_strategy" in func.__code__.co_varnames
            and "chunking_strategy" not in func.__doc__
        ):
            func.__doc__ += (
                "\nchunking_strategy"
                + "\n\tStrategy used for chunking text into larger or smaller elements."
                + "\n\tDefaults to `None` with optional arg of 'by_title'."
                + "\n\tAdditional Parameters:"
                + "\n\t\tmultipage_sections"
                + "\n\t\t\tIf True, sections can span multiple pages. Defaults to True."
                + "\n\t\tcombine_text_under_n_chars"
                + "\n\t\t\tCombines elements (for example a series of titles) until a section"
                + "\n\t\t\treaches a length of n characters."
                + "\n\t\tnew_after_n_chars"
                + "\n\t\t\tCuts off new sections once they reach a length of n characters"
                + "\n\t\t\ta soft max."
                + "\n\t\tmax_characters"
                + "\n\t\t\tChunks elements text and text_as_html (if present) into chunks"
                + "\n\t\t\tof length n characters, a hard max."
            )

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params: Dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default
            if params.get("chunking_strategy") == "by_title":
                elements = chunk_by_title(
                    elements,
                    multipage_sections=params.get("multipage_sections", True),
                    combine_text_under_n_chars=params.get("combine_text_under_n_chars", 500),
                    new_after_n_chars=params.get("new_after_n_chars", 500),
                    max_characters=params.get("max_characters", 500),
                )
            return elements

        return wrapper

    return decorator


# == Sections ====================================================================================


class _NonTextSection:
    """A section composed of a single `Element` that does not subclass `Text`.

    Currently, only `CheckBox` fits that description
    """

    def __init__(self, element: Element) -> None:
        self._element = element

    @property
    def element(self) -> Element:
        """The non-text element of this section (currently only CheckBox is non-text)."""
        return self._element


class _TableSection:
    """A section composed of a single Table element."""

    def __init__(self, table: Table) -> None:
        self._table = table

    @property
    def table(self) -> Table:
        """The `Table` element of this section."""
        return self._table


class _TextSection:
    """A sequence of elements that belong to the same semantic unit within a document.

    The name "section" derives from the idea of a document-section, a heading followed by the
    paragraphs "under" that heading. That structure is not found in all documents and actual section
    content can vary, but that's the concept.

    This object is purposely immutable.
    """

    def __init__(self, elements: Iterable[Element]) -> None:
        self._elements = list(elements)

    def combine(self, other_section: _TextSection) -> _TextSection:
        """Return new `_TextSection` that combines this and `other_section`."""
        return _TextSection(self._elements + other_section._elements)

    @property
    def elements(self) -> List[Element]:
        """The elements of this text-section."""
        return self._elements

    @lazyproperty
    def text_length(self) -> int:
        """Length of concatenated text of this section, including separators."""
        return len(self._text)

    @lazyproperty
    def _text(self) -> str:
        """The concatenated text of all elements in this section.

        Each element-text is separated from the next by a blank line ("\n\n").
        """
        return TEXT_SEPARATOR.join(e.text for e in self._elements if isinstance(e, Text) and e.text)


class _TextSectionBuilder:
    """An element accumulator suitable for incrementally forming a section.

    Provides monitoring properties like `.remaining_space` and `.text_length` a sectioner can use
    to determine whether it should add the next element in the element stream.

    `.flush()` is used to build a `TextSection` object from the accumulated elements. This method
    returns an interator that generates zero-or-one `TextSection` object and is used like so:

        yield from builder.flush()

    If no elements have been accumulated, no `TextSection` is generated. Flushing the builder clears
    the elements it contains so it is ready to build the next text-section.
    """

    def __init__(self, maxlen: int) -> None:
        self._maxlen = maxlen
        self._separator_len = len(TEXT_SEPARATOR)
        self._elements: List[Element] = []

        # == these working values probably represent premature optimization but improve performance
        # -- and I expect will be welcome when processing a million elements

        # -- only includes non-empty element text, e.g. PageBreak.text=="" is not included --
        self._text_segments: List[str] = []
        # -- combined length of text-segments, not including separators --
        self._text_len: int = 0

    def add_element(self, element: Element) -> None:
        """Add `element` to this section."""
        self._elements.append(element)
        if isinstance(element, Text) and element.text:
            self._text_segments.append(element.text)
            self._text_len += len(element.text)

    def flush(self) -> Iterator[_TextSection]:
        """Generate zero-or-one `Section` object and clear the accumulator.

        Suitable for use to emit a Section when the maximum size has been reached or a semantic
        boundary has been reached. Also to clear out a terminal section at the end of an element
        stream.
        """
        if not self._elements:
            return
        # -- clear builder before yield so we're not sensitive to the timing of how/when this
        # -- iterator is exhausted and can add eleemnts for the next section immediately.
        elements = self._elements[:]
        self._elements.clear()
        self._text_segments.clear()
        self._text_len = 0
        yield _TextSection(elements)

    @property
    def remaining_space(self) -> int:
        """Maximum text-length of an element that can be added without exceeding maxlen."""
        # -- include length of trailing separator that will go before next element text --
        separators_len = self._separator_len * len(self._text_segments)
        return self._maxlen - self._text_len - separators_len

    @property
    def text_length(self) -> int:
        """Length of the text in this section.

        This value represents the chunk-size that would result if this section was flushed in its
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


# == SectionCombiner =============================================================================


class _SectionCombiner:
    """Filters section stream to combine small sections where possible."""

    def __init__(
        self,
        sections: Iterable[_Section],
        maxlen: int,
        combine_text_under_n_chars: int,
    ):
        self._sections = sections
        self._maxlen = maxlen
        self._combine_text_under_n_chars = combine_text_under_n_chars

    def iter_combined_sections(self) -> Iterator[_Section]:
        """Generate section objects, combining TextSection objects when they will fit in window."""
        accum = _TextSectionAccumulator(self._maxlen)

        for section in self._sections:
            # -- start new section under these conditions --
            if (
                # -- a table or checkbox section is never combined --
                isinstance(section, (_TableSection, _NonTextSection))
                # -- don't add another section once length has reached combination soft-max --
                or accum.text_length >= self._combine_text_under_n_chars
                # -- combining would exceed hard-max --
                or accum.remaining_space < section.text_length
            ):
                yield from accum.flush()

            # -- a table or checkbox section is never combined so don't accumulate --
            if isinstance(section, (_TableSection, _NonTextSection)):
                yield section
            else:
                accum.add_section(section)

        yield from accum.flush()


class _TextSectionAccumulator:
    """Accumulates, measures, and combines section objects.

    Provides monitoring properties `.remaining_space` and `.text_length` suitable for deciding
    whether to add another section.

    `.flush()` is used to combine the accumulated sections into a single `TextSection` object. This
    method returns an interator that generates zero-or-one `TextSection` objects and is used like
    so:

        yield from accum.flush()

    If no sections have been accumulated, no `TextSection` is generated. Flushing the builder clears
    the sections it contains so it is ready to accept the next text-section.
    """

    def __init__(self, maxlen: int) -> None:
        self._maxlen = maxlen
        self._sections: List[_TextSection] = []

    def add_section(self, section: _TextSection) -> None:
        """Add a section to the accumulator for possible combination with next section."""
        self._sections.append(section)

    def flush(self) -> Iterator[_TextSection]:
        """Generate all accumulated sections as a single combined section."""
        sections = self._sections

        # -- nothing to do if no sections have been accumulated --
        if not sections:
            return

        # -- otherwise combine all accumulated section into one --
        section = sections[0]
        for other_section in sections[1:]:
            section = section.combine(other_section)
        yield section

        # -- and reset the accumulator (to empty) --
        sections.clear()

    @property
    def remaining_space(self) -> int:
        """Maximum size of section that can be added without exceeding maxlen."""
        return (
            self._maxlen
            if not self._sections
            # -- an additional section will also incur an additional separator --
            else self._maxlen - self.text_length - len(TEXT_SEPARATOR)
        )

    @property
    def text_length(self) -> int:
        """Size of concatenated text in all sections in accumulator."""
        n = len(self._sections)
        return (
            0
            if n == 0
            else sum(s.text_length for s in self._sections) + len(TEXT_SEPARATOR) * (n - 1)
        )
