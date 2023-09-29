import copy
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar

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
    max_characters: Optional[int] = 1500,
) -> List[TableChunk]:
    chunks = []

    element_char_len = len(element.text)

    html_table = element.text_as_html if hasattr(element, "text_as_html") else None
    if html_table:
        element_char_len = len(html_table)
    if element_char_len <= max_characters:
        chunks.append(element)
    else:
        text = element.text
        text_as_html = element.text_as_html if hasattr(element, "text_as_html") else None
        i = 0
        metadata = element.metadata
        while text or text_as_html:
            text_chunk = text[:max_characters]
            table_chunk = TableChunk(
                text=text_chunk,
                metadata=copy.copy(metadata),
            )
            if text_as_html:
                text_as_html_chunk = text_as_html[:max_characters]
                table_chunk.metadata.text_as_html = text_as_html_chunk
                # Remove the processed chunk from text_as_html
                text_as_html = text_as_html[max_characters:]
            if i > 0:
                table_chunk.metadata.is_continuation = True

            chunks.append(table_chunk)
            i += 1

            # Remove the processed chunk from text
            text = text[max_characters:]

            # Ensure that text and text_as_html are not empty before continuing
            if not text and not text_as_html:
                break
    return chunks


def chunk_by_title(
    elements: List[Element],
    multipage_sections: bool = True,
    combine_text_under_n_chars: int = 500,
    max_characters: int = 1500,
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
    max_characters
        Cuts off new sections once they reach a length of n characters
    """
    if (
        combine_text_under_n_chars is not None
        and max_characters is not None
        and (
            combine_text_under_n_chars > max_characters
            or combine_text_under_n_chars < 0
            or max_characters < 0
        )
    ):
        raise ValueError(
            "Invalid values for combine_text_under_n_chars and/or max_characters.",
        )

    chunked_elements: List[Element] = []
    sections = _split_elements_by_title_and_table(
        elements,
        multipage_sections=multipage_sections,
        combine_text_under_n_chars=combine_text_under_n_chars,
        max_characters=max_characters,
    )
    for section in sections:
        if not section:
            continue
        if not isinstance(section[0], Text):
            chunked_elements.extend(section)

        elif isinstance(section[0], Text):
            if isinstance(section[0], Table):
                chunked_elements.extend(chunk_table_element(section[0], max_characters))

            else:
                text = ""
                metadata = section[0].metadata

                for i, element in enumerate(section):
                    if isinstance(element, Text):
                        text += "\n\n" if text else ""
                        start_char = len(text)
                        text += element.text

                    for attr, value in vars(element.metadata).items():
                        if not isinstance(value, list):
                            continue

                        _value = getattr(metadata, attr, [])
                        if _value is None:
                            _value = []

                        if attr == "regex_metadata":
                            for item in value:
                                item["start"] += start_char
                                item["end"] += start_char

                        if i > 0:
                            # NOTE(newelh): Previously, _value was extended with value.
                            # This caused a memory error if the content was a list of strings
                            # with a large number of elements -- doubling the list size each time.
                            # This now instead ensures that the _value list is unique and updated.
                            for item in value:
                                if item not in _value:
                                    _value.append(item)

                            setattr(metadata, attr, _value)

                chunked_elements.append(CompositeElement(text=text, metadata=metadata))

    return chunked_elements


def _split_elements_by_title_and_table(
    elements: List[Element],
    multipage_sections: bool = True,
    combine_text_under_n_chars: int = 500,
    max_characters: int = 1500,
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
        new_section = (isinstance(element, Title) and section_length > combine_text_under_n_chars) or (
            not metadata_matches or section_length > max_characters
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
    keys_to_drop = ["element_id", "type", "coordinates", "parent_id", "category_depth"]
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
                + "\n\t\tmax_characters"
                + "\n\t\t\tCuts off new sections once they reach a length of n characters"
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
                    max_characters=params.get("max_characters", 1500),
                )
            return elements

        return wrapper

    return decorator
