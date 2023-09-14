import inspect
from functools import wraps
from typing import Callable, List

from unstructured.documents.elements import (
    CompositeElement,
    Element,
    ElementMetadata,
    Table,
    Text,
    Title,
)


def chunk_by_title(
    elements: List[Element],
    multipage_sections: bool = True,
    combine_under_n_chars: int = 500,
    new_after_n_chars: int = 1500,
) -> List[Element]:
    """Uses title elements to identify sections within the document for chunking. Splits
    off into a new section when a title is detected or if metadata changes, which happens
    when page numbers or sections change. Cuts off sections once they have exceeded
    a character length of new_after_n_chars.

    Parameters
    ----------
    elements
        A list of unstructured elements. Usually the ouput of a partition functions.
    multipage_sections
        If True, sections can span multiple pages. Defaults to True.
    combine_under_n_chars
        Combines elements (for example a series of titles) until a section reaches
        a length of n characters.
    new_after_n_chars
        Cuts off new sections once they reach a length of n characters
    """
    if (
        combine_under_n_chars is not None
        and new_after_n_chars is not None
        and (
            combine_under_n_chars > new_after_n_chars
            or combine_under_n_chars < 0
            or new_after_n_chars < 0
        )
    ):
        raise ValueError(
            "Invalid values for combine_under_n_chars and/or new_after_n_chars.",
        )

    chunked_elements: List[Element] = []
    sections = _split_elements_by_title_and_table(
        elements,
        multipage_sections=multipage_sections,
        combine_under_n_chars=combine_under_n_chars,
        new_after_n_chars=new_after_n_chars,
    )

    for section in sections:
        if not section:
            continue
        if not isinstance(section[0], Text) or isinstance(section[0], Table):
            chunked_elements.extend(section)

        elif isinstance(section[0], Text):
            text = ""
            metadata = section[0].metadata

            for i, element in enumerate(section):
                if isinstance(element, Text):
                    if text:
                        text += "\n\n"
                    start_char = len(text)
                    text += element.text

                for attr, value in vars(element.metadata).items():
                    if isinstance(value, list):
                        _value = getattr(metadata, attr, [])
                        if _value is None:
                            _value = []

                        if attr == "regex_metadata":
                            for item in value:
                                item["start"] += start_char
                                item["end"] += start_char

                        if i > 0:
                            _value.extend(value)
                            setattr(metadata, attr, _value)

            chunked_elements.append(CompositeElement(text=text, metadata=metadata))

    return chunked_elements


def _split_elements_by_title_and_table(
    elements: List[Element],
    multipage_sections: bool = True,
    combine_under_n_chars: int = 500,
    new_after_n_chars: int = 1500,
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
        new_section = (isinstance(element, Title) and section_length > combine_under_n_chars) or (
            not metadata_matches or section_length > new_after_n_chars
        )

        if isinstance(element, Table) or not isinstance(element, Text):
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
    metadata_dict: dict,
    include_pages: bool = True,
) -> dict:
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


def add_chunking_strategy():
    """Decorator for chuncking text. Uses title elements to identify sections within the document
    for chunking. Splits off a new section when a title is detected or if metadata changes,
    which happens when page numbers or sections change. Cuts off sections once they have exceeded
    a character length of new_after_n_chars."""

    def decorator(func: Callable):
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
                + "\n\t\tcombine_under_n_chars"
                + "\n\t\t\tCombines elements (for example a series of titles) until a section"
                + "\n\t\t\treaches a length of n characters."
                + "\n\t\tnew_after_n_chars"
                + "\n\t\t\tCuts off new sections once they reach a length of n characters"
            )

        @wraps(func)
        def wrapper(*args, **kwargs):
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default
            if params.get("chunking_strategy") == "by_title":
                elements = chunk_by_title(
                    elements,
                    multipage_sections=params.get("multipage_sections", True),
                    combine_under_n_chars=params.get("combine_under_n_chars", 500),
                    new_after_n_chars=params.get("new_after_n_chars", 1500),
                )
            return elements

        return wrapper

    return decorator
