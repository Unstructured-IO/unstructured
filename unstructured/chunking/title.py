"""Implementation of chunking by title.

Main entry point is the `@add_chunking_strategy()` decorator.
"""

from __future__ import annotations

import copy
import functools
import inspect
from typing import Any, Callable, Dict, List, cast

from typing_extensions import ParamSpec

from unstructured.documents.elements import (
    CompositeElement,
    Element,
    ElementMetadata,
    Table,
    TableChunk,
    Text,
    Title,
)


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
    combine_text_under_n_chars: int = 500,
    new_after_n_chars: int = 500,
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
        Combines elements (for example a series of titles) until a section reaches
        a length of n characters.
    new_after_n_chars
        Cuts off new sections once they reach a length of n characters (soft max)
    max_characters
        Chunks elements text and text_as_html (if present) into chunks of length
        n characters (hard max)
    """

    if not (
        max_characters > 0
        and combine_text_under_n_chars >= 0
        and new_after_n_chars >= 0
        and combine_text_under_n_chars <= new_after_n_chars
        and combine_text_under_n_chars <= max_characters
    ):
        raise ValueError(
            "Invalid values for combine_text_under_n_chars, "
            "new_after_n_chars, and/or max_characters.",
        )

    chunked_elements: List[Element] = []
    sections = _split_elements_by_title_and_table(
        elements,
        multipage_sections=multipage_sections,
        combine_text_under_n_chars=combine_text_under_n_chars,
        new_after_n_chars=new_after_n_chars,
        max_characters=max_characters,
    )
    for section in sections:
        if not section:
            continue

        first_element = section[0]

        if not isinstance(first_element, Text):
            chunked_elements.extend(section)
            continue

        elif isinstance(first_element, Table):
            chunked_elements.extend(chunk_table_element(first_element, max_characters))
            continue

        text = ""
        metadata = first_element.metadata
        start_char = 0
        for element_idx, element in enumerate(section):
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
    multipage_sections: bool = True,
    combine_text_under_n_chars: int = 500,
    new_after_n_chars: int = 500,
    max_characters: int = 500,
) -> List[List[Element]]:
    sections: List[List[Element]] = []
    section: List[Element] = []

    for i, element in enumerate(elements):
        metadata_differs = False
        if i > 0:
            last_element = elements[i - 1]
            metadata_differs = _metadata_differs(
                element.metadata,
                last_element.metadata,
                include_pages=not multipage_sections,
            )

        section_length = sum([len(str(element)) for element in section])

        new_section = (
            (section_length + len(str(element)) > max_characters)
            or (isinstance(element, Title) and section_length > combine_text_under_n_chars)
            or (metadata_differs or section_length > new_after_n_chars)
        )
        if not isinstance(element, Text) or isinstance(element, Table):
            sections.append(section)
            sections.append([element])
            section = []
        elif new_section:
            if len(section) > 0:
                sections.append(section)
            section = [element]
        else:
            # if existing section plus new section will go above max, start new section
            section.append(element)

    if len(section) > 0:
        sections.append(section)

    return sections


def _metadata_differs(
    metadata1: ElementMetadata,
    metadata2: ElementMetadata,
    include_pages: bool = True,
) -> bool:
    """True when metadata differences between two elements indicate a semantic boundary.

    Currently this is only a page-number change or a section change.
    """
    if metadata1.section != metadata2.section:
        return True
    if include_pages and metadata1.page_number != metadata2.page_number:
        return True
    return False


_P = ParamSpec("_P")


def add_chunking_strategy() -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """Decorator for chuncking text. Uses title elements to identify sections within the document
    for chunking. Splits off a new section when a title is detected or if metadata changes,
    which happens when page numbers or sections change. Cuts off sections once they have exceeded
    a character length of max_characters."""

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
        if func.__doc__ and (
            "chunking_strategy" in func.__code__.co_varnames
            and "chunking_strategy" not in func.__doc__
        ):
            func.__doc__ += (
                "\nchunking_strategy"
                + "\n\tStrategy used for chunking text into larger or smaller elements."
                + "\n\tDefaluts to `None` withoptional arg of 'by_title'."
                + "\n\tAdditional Parameters:"
                + "\n\t\tmultipage_sections"
                + "\n\t\t\tIf True, sections can span multiple pages. Defaults to True."
                + "\n\t\tcombine_text_under_n_chars"
                + "\n\t\t\tCombines elements (for example a series of titles) until a section"
                + "\n\t\t\treaches a length of n characters."
                + "\n\t\tnew_after_n_chars"
                + "\n\t\t\t Cuts off new sections once they reach a length of n characters"
                + "\n\t\t\t a soft max."
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
