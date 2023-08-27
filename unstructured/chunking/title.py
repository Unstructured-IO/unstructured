from typing import List

from unstructured.documents.elements import Element, Table, Text, Title


def chunk_by_title(
    elements: List[Element],
) -> List[Element]:
    """Uses title elements to identify sections within the document for chunking."""
    return []


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
