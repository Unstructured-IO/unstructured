from typing import List

from unstructured.documents.elements import Element, Section, Table, Text, Title


def chunk_by_title(
    elements: List[Element],
) -> List[Element]:
    """Uses title elements to identify sections within the document for chunking."""
    chunked_elements: List[Element] = []
    sections = _split_elements_by_title_and_table(elements)

    for section in sections:
        if isinstance(section[0], Title):
            text = ""
            metadata = section[0].metadata

            for i, element in enumerate(section):
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

        else:
            chunked_elements.extend(section)

    return chunked_elements


def _split_elements_by_title_and_table(elements: List[Element]) -> List[List[Element]]:
    sections: List[List[Element]] = []
    section: List[Element] = []
    for element in elements:
        if isinstance(element, Table) or not isinstance(element, Text):
            sections.append(section)
            sections.append([element])
            section = []
        elif isinstance(element, Title):
            if len(section) > 0:
                sections.append(section)
            section = [element]
        else:
            section.append(element)

    if len(section) > 0:
        sections.append(section)

    return sections
