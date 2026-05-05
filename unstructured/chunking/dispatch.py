"""Handles dispatch of elements to a chunking-strategy by name.

Also provides the `@add_chunking_strategy` decorator which is the chief current user of "by-name"
chunking dispatch.
"""

from __future__ import annotations

import copy
import dataclasses as dc
import functools
import inspect
from functools import cached_property
from typing import Any, Callable, Iterable, Optional, Protocol

from lxml.etree import ParserError, tostring
from lxml.html import fragment_fromstring
from typing_extensions import ParamSpec

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element, Table, TableChunk
from unstructured.utils import get_call_args_applying_defaults

_P = ParamSpec("_P")


class Chunker(Protocol):
    """Abstract interface for chunking functions."""

    def __call__(
        self, elements: Iterable[Element], *, max_characters: Optional[int]
    ) -> list[Element]:
        """A chunking function must have this signature.

        In particular it must minimally have an `elements` parameter and all chunkers will have a
        `max_characters` parameter (doesn't need to follow `elements` directly). All others can
        vary by chunker.
        """
        ...


def add_chunking_strategy(func: Callable[_P, list[Element]]) -> Callable[_P, list[Element]]:
    """Decorator for chunking text in both pre-processing and post-processing way.

    Chunks the element sequence produced by the partitioner it decorates when a `chunking_strategy`
    argument is present in the partitioner call and it names an available chunking strategy.
    The chunking process could be both pre-process and post-process chunking

    """
    # -- Patch the docstring of the decorated function to add chunking strategy and
    # -- chunking-related argument documentation. This only applies when `chunking_strategy`
    # -- is an explicit argument of the decorated function and "chunking_strategy" is not
    # -- already mentioned in the docstring.
    if func.__doc__ and (
        "chunking_strategy" in func.__code__.co_varnames and "chunking_strategy" not in func.__doc__
    ):
        func.__doc__ += (
            "\nchunking_strategy"
            + "\n\tStrategy used for chunking text into larger or smaller elements."
            + "\n\tDefaults to `None` with optional arg of 'basic' or 'by_title'."
            + "\n\tAdditional Parameters:"
            + "\n\t\tmultipage_sections"
            + "\n\t\t\tIf True, sections can span multiple pages. Defaults to True."
            + "\n\t\tcombine_text_under_n_chars"
            + "\n\t\t\tCombines elements (for example a series of titles) until a section"
            + "\n\t\t\treaches a length of n characters. Only applies to 'by_title' strategy."
            + "\n\t\tnew_after_n_chars"
            + "\n\t\t\tCuts off chunks once they reach a length of n characters; a soft max."
            + "\n\t\tmax_characters"
            + "\n\t\t\tChunks elements text and text_as_html (if present) into chunks"
            + "\n\t\t\tof length n characters, a hard max."
            + "\n\t\trepeat_table_headers"
            + "\n\t\t\tDefault: True. Repeat detected table headers on continuation"
            + "\n\t\t\ttable chunks. Set to False to opt out."
            + "\n\t\tskip_table_chunking"
            + "\n\t\t\tDefault: False. When True, Table elements are passed through"
            + "\n\t\t\tunchanged without being split into TableChunk elements."
        )
    # -- Patch the docstring of the decorated function to add contexual chunking strategy and
    # -- contextual_chunking-related argument documentation.
    # -- This only applies when `contextual_chunking_strategy` is an explicit argument
    # -- of the decorated function and "contextual_chunking_strategy" is not
    # -- already mentioned in the docstring.
    if func.__doc__ and (
        "contextual_chunking_strategy" in func.__code__.co_varnames
        and "contextual_chunking_strategy" not in func.__doc__
    ):
        func.__doc__ += (
            "\ncontextual_chunking_strategy"
            + "\n\tStrategy used to contextualize chunks into chunks with prefixs."
            + "\n\tDefaults to `None`"
            + "\n\tAdditional Parameters:"
            + "\n\t\\service_name"
            + "\n\t\t\tThe service name that describes the provider and its purpose"
            + "\n\t\tauth_env"
            + "\n\t\t\tthe authentication environment var name to get the auth token"
        )

    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> list[Element]:
        """The decorated function is replaced with this one."""

        # -- call the partitioning function to get the elements --
        elements = func(*args, **kwargs)

        # -- look for a chunking-strategy argument --
        call_args = get_call_args_applying_defaults(func, *args, **kwargs)
        chunking_strategy = call_args.pop("chunking_strategy", None)

        # -- no chunking-strategy means no chunking --
        if chunking_strategy is None:
            return elements

        # -- otherwise, chunk away :) --
        # here, chunk() can be both pre-process and post-process chunking
        return chunk(elements, chunking_strategy, **call_args)

    return wrapper


def chunk(elements: Iterable[Element], chunking_strategy: str, **kwargs: Any) -> list[Element]:
    """Dispatch chunking of `elements` to the chunking function if only `chunking_strategy` present
    if both `chunking_strategy` and `contextual_chunking_strategy` args are present and None,
    use the chunketized results and perform contextual chunking function afterwards.

    """
    chunker_spec = _chunker_registry.get(chunking_strategy)

    if chunker_spec is None:
        raise ValueError(f"unrecognized chunking strategy {repr(chunking_strategy)}")
    # extract and remove contextual_chunking_strategy from kwargs if present
    contextual_chunking_strategy = kwargs.pop("contextual_chunking_strategy", None)

    # -- `kwargs` will in general be an omnibus dict of all keyword arguments to the partitioner;
    # -- pick out and use only those supported by this chunker.
    chunking_kwargs = {k: v for k, v in kwargs.items() if k in chunker_spec.kw_arg_names}
    chunks = chunker_spec.chunker(elements, **chunking_kwargs)
    if contextual_chunking_strategy == "v1":
        contextual_chunking_spec = _chunker_registry.get(contextual_chunking_strategy)
        if contextual_chunking_spec is None:
            raise ValueError(
                f"unrecognized contextual chunking strategy {repr(contextual_chunking_strategy)}"
            )
        # prepare kwargs for the contextual chunkin strategy such as service name, auth env etc
        contextual_chunking_kwargs = {
            k: v for k, v in kwargs.items() if k in contextual_chunking_spec.kw_arg_names
        }
        # perform post-chunking using contextual_chunking_strategy
        chunks = contextual_chunking_spec.chunker(chunks, **contextual_chunking_kwargs)

    return chunks


def register_chunking_strategy(name: str, chunker: Chunker) -> None:
    """Make chunker available by using `name` as `chunking_strategy` arg in partitioner call."""
    _chunker_registry[name] = _ChunkerSpec(chunker)


@dc.dataclass(frozen=True)
class _ChunkerSpec:
    """A registry entry for a chunker."""

    chunker: Chunker
    """The "chunk_by_{x}() function that implements this chunking strategy."""

    @cached_property
    def kw_arg_names(self) -> tuple[str, ...]:
        """Keyword arguments supported by this chunker.

        These are all arguments other than the required `elements: list[Element]` first parameter.
        """
        sig = inspect.signature(self.chunker)
        return tuple(key for key in sig.parameters if key != "elements")


_chunker_registry: dict[str, _ChunkerSpec] = {
    "basic": _ChunkerSpec(chunk_elements),
    "by_title": _ChunkerSpec(chunk_by_title),
}


def reconstruct_table_from_chunks(elements: Iterable[Element]) -> list[Table]:
    """Reconstruct original tables from a mixed list of chunked elements.

    Filters `TableChunk` elements, groups them by `table_id`, orders by `chunk_index`, and
    merges each group into a single `Table` with combined text and HTML. Non-`TableChunk`
    elements are ignored. Returns reconstructed tables in reading order (order of first chunk
    appearance).
    """
    # -- filter to only TableChunk instances, preserving input order --
    table_chunks = [e for e in elements if isinstance(e, TableChunk)]
    if not table_chunks:
        return []

    # -- group by table_id, preserving first-seen order --
    groups: dict[str, list[TableChunk]] = {}
    for chunk in table_chunks:
        tid = chunk.metadata.table_id
        if tid is None:
            continue
        if tid not in groups:
            groups[tid] = []
        groups[tid].append(chunk)

    # -- sort each group by chunk_index and merge --
    tables: list[Table] = []

    def _chunk_sort_key(chunk: TableChunk) -> tuple[bool, int]:
        chunk_index = chunk.metadata.chunk_index
        return (chunk_index is None, 0 if chunk_index is None else chunk_index)

    for group in groups.values():
        group.sort(key=_chunk_sort_key)
        tables.append(_merge_table_chunks(group))

    return tables


def _merge_table_chunks(chunks: list[TableChunk]) -> Table:
    """Merge an ordered list of TableChunks from the same table into a single Table."""
    # -- combine text --
    text = " ".join(
        chunk_text for chunk in chunks if (chunk_text := _strip_carried_over_header_text(chunk))
    )

    # -- build metadata from first chunk --
    metadata = copy.deepcopy(chunks[0].metadata)
    metadata.is_continuation = None
    metadata.table_id = None
    metadata.chunk_index = None
    metadata.num_carried_over_header_rows = None

    # -- combine HTML if all chunks have it --
    if all(c.metadata.text_as_html for c in chunks):
        combined = fragment_fromstring("<table></table>")
        canonical_header_row_count, canonical_header_rows = _first_carried_header_rows(chunks)
        if canonical_header_rows:
            thead = fragment_fromstring("<thead></thead>")
            for row in canonical_header_rows:
                thead.append(row)
            combined.append(thead)

        for c in chunks:
            parsed = fragment_fromstring(c.metadata.text_as_html)
            carried_over_header_rows = _num_carried_over_header_rows(c)
            rows = parsed.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr")
            skip_count = carried_over_header_rows
            if c is chunks[0] and canonical_header_row_count:
                skip_count = canonical_header_row_count
            for row in rows[skip_count:]:
                combined.append(row)
        metadata.text_as_html = tostring(combined, encoding=str)
    else:
        metadata.text_as_html = None

    return Table(text=text, metadata=metadata)


def _num_carried_over_header_rows(chunk: TableChunk) -> int:
    """Header rows prepended synthetically to this chunk.

    Reconstruction can be called on user-provided/deserialized chunks, so treat missing values as
    "no carried header rows."
    """
    value = chunk.metadata.num_carried_over_header_rows
    return value or 0


def _first_carried_header_rows(chunks: list[TableChunk]) -> tuple[int, list[Any]]:
    """Header rows from first continuation chunk carrying repeated headers, if any."""
    first_chunk_rows = _top_level_table_rows(chunks[0].metadata.text_as_html)
    if first_chunk_rows is None:
        return 0, []

    for chunk in chunks:
        carried_row_count = _num_carried_over_header_rows(chunk)
        if carried_row_count <= 0:
            continue

        rows = _top_level_table_rows(chunk.metadata.text_as_html)
        if rows is None:
            continue

        if carried_row_count > len(rows):
            continue

        carried_rows = rows[:carried_row_count]
        if not _leading_row_texts_match(first_chunk_rows, carried_rows):
            continue

        return carried_row_count, [copy.deepcopy(row) for row in rows[:carried_row_count]]

    return 0, []


def _top_level_table_rows(text_as_html: str | None) -> list[Any] | None:
    """Top-level rows from a table fragment, preserving section ordering."""
    if not text_as_html:
        return None

    try:
        parsed = fragment_fromstring(text_as_html)
    except (ParserError, ValueError):
        return None

    return parsed.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr")


def _leading_row_texts_match(first_chunk_rows: list[Any], carried_rows: list[Any]) -> bool:
    """True when carried rows match first chunk's leading rows by normalized cell text."""
    if len(first_chunk_rows) < len(carried_rows):
        return False

    for first_row, carried_row in zip(first_chunk_rows, carried_rows):
        if _row_text_signature(first_row) != _row_text_signature(carried_row):
            return False

    return True


def _row_text_signature(row: Any) -> tuple[str, ...]:
    """Normalized cell text tuple for a row."""
    return tuple(" ".join(cell.text_content().split()) for cell in row.iter("td", "th"))


def _strip_carried_over_header_text(chunk: TableChunk) -> str:
    """Strip synthetic carried-over header text from continuation chunk text."""
    carried_row_count = _num_carried_over_header_rows(chunk)
    if carried_row_count == 0:
        return chunk.text

    text_as_html = chunk.metadata.text_as_html
    if not text_as_html:
        return chunk.text

    try:
        parsed = fragment_fromstring(text_as_html)
    except (ParserError, ValueError):
        return chunk.text

    rows = parsed.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr")
    if carried_row_count > len(rows):
        return chunk.text

    carried_header_text = " ".join(
        text
        for row in rows[:carried_row_count]
        for text in (" ".join(cell.text_content().split()) for cell in row.iter("td", "th"))
        if text
    )
    if not carried_header_text:
        return chunk.text

    chunk_text = chunk.text.lstrip()
    if chunk_text == carried_header_text:
        return ""
    if chunk_text.startswith(f"{carried_header_text} "):
        return chunk_text[len(carried_header_text) + 1 :]
    if chunk_text.startswith(carried_header_text):
        return chunk_text[len(carried_header_text) :].lstrip()
    return chunk.text
