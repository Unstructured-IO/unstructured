import copy
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

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


def chunk_table_element(
    element: Table,
    max_characters: Optional[int] = 500,
) -> List[Union[Table, TableChunk]]:
    text = element.text
    html = getattr(element, "text_as_html", None)

    if len(text) <= max_characters and (  # type: ignore
        html is None or len(html) <= max_characters  # type: ignore
    ):
        return [element]

    chunks: List[Union[Table, TableChunk]] = []
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
    """Uses title elements to identify sections within the document for chunking. Splits
    off into a new section when a title is detected or if metadata changes, which happens
    when page numbers or sections change. Cuts off sections once they have exceeded
    a character length of max_characters.

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
        for element in section:
            if isinstance(element, Text):
                text += "\n\n" if text else ""
                start_char = len(text)
                text += element.text
            for attr, value in vars(element.metadata).items():
                if isinstance(value, list):
                    _value = getattr(metadata, attr, []) or []

                    if attr == "regex_metadata":
                        for item in value:
                            item["start"] += start_char
                            item["end"] += start_char

                    _value.extend(item for item in value if item not in _value)
                    setattr(metadata, attr, _value)

        # Check if text exceeds max_characters
        if len(text) > max_characters:
            # Chunk the text from the end to the beginning
            while len(text) > 0:
                if len(text) <= max_characters:
                    # If the remaining text is shorter than max_characters
                    # create a chunk from the beginning
                    chunk_text = text
                    text = ""
                else:
                    # Otherwise, create a chunk from the end
                    chunk_text = text[-max_characters:]
                    text = text[:-max_characters]

                # Prepend the chunk to the beginning of the list
                chunked_elements.insert(0, CompositeElement(text=chunk_text, metadata=metadata))
        else:
            # If it doesn't exceed, create a single CompositeElement
            chunked_elements.append(CompositeElement(text=text, metadata=metadata))

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
        metadata_matches = True
        if i > 0:
            last_element = elements[i - 1]
            metadata_matches = _metadata_matches(
                element.metadata,
                last_element.metadata,
                include_pages=not multipage_sections,
            )

        section_length = sum([len(str(element)) for element in section])

        new_section = (
            (section_length + len(str(element)) > max_characters)
            or (isinstance(element, Title) and section_length > combine_text_under_n_chars)
            or (not metadata_matches or section_length > new_after_n_chars)
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


def _metadata_matches(
    metadata1: ElementMetadata,
    metadata2: ElementMetadata,
    include_pages: bool = True,
) -> bool:
    metadata_dict1 = metadata1.to_dict()
    metadata_dict1 = _drop_extra_metadata(metadata_dict1, include_pages=include_pages)

    metadata_dict2 = metadata2.to_dict()
    metadata_dict2 = _drop_extra_metadata(metadata_dict2, include_pages=include_pages)

    return metadata_dict1 == metadata_dict2


def _drop_extra_metadata(
    metadata_dict: Dict[str, Any],
    include_pages: bool = True,
) -> Dict[str, Any]:
    keys_to_drop = [
        "element_id",
        "type",
        "coordinates",
        "parent_id",
        "category_depth",
        "detection_class_prob",
    ]
    if not include_pages and "page_number" in metadata_dict:
        keys_to_drop.append("page_number")

    for key, value in metadata_dict.items():
        if isinstance(value, list):
            keys_to_drop.append(key)

    for key in keys_to_drop:
        if key in metadata_dict:
            del metadata_dict[key]

    return metadata_dict


_T = TypeVar("_T")
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
