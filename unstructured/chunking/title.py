from typing import List

from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Section,
    Table,
    Text,
    Title,
)


def chunk_by_title(
    elements: List[Element],
    multipage_sections: bool = True,
) -> List[Element]:
    """Uses title elements to identify sections within the document for chunking."""
    chunked_elements: List[Element] = []
    sections = _split_elements_by_title_and_table(elements)

    for section in sections:
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

            chunked_elements.append(Section(text=text, metadata=metadata))

    return chunked_elements


def _split_elements_by_title_and_table(
    elements: List[Element],
    multipage_sections: bool = True,
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

        if isinstance(element, Table) or not isinstance(element, Text):
            sections.append(section)
            sections.append([element])
            section = []
        elif isinstance(element, Title) or not metadata_matches:
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
    keys_to_drop = ["element_id", "type"]
    if include_pages and "page_number" in metadata_dict:
        keys_to_drop.append("page_number")

    for key, value in metadata_dict.items():
        if isinstance(value, list):
            keys_to_drop.append(key)

    for key in keys_to_drop:
        if key in metadata_dict:
            del metadata_dict[key]

    return metadata_dict
