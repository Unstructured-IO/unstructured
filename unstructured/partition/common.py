import subprocess
from typing import List, Optional, Union

from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    CheckBox,
    FigureCaption,
    ListItem,
    NarrativeText,
    PageBreak,
    Text,
    Title,
)
from unstructured.nlp.patterns import UNICODE_BULLETS_RE, ENUMERATED_BULLETS_RE


def normalize_layout_element(layout_element) -> Union[Element, List[Element]]:
    """Converts a list of unstructured_inference DocumentLayout objects to a list of
    unstructured Elements."""

    if isinstance(layout_element, PageBreak):
        return PageBreak()

    if not isinstance(layout_element, dict):
        layout_dict = layout_element.to_dict()
    else:
        layout_dict = layout_element

    text = layout_dict.get("text")
    coordinates = layout_dict.get("coordinates")
    element_type = layout_dict.get("type")

    if element_type == "Title":
        return Title(text=text, coordinates=coordinates)
    elif element_type == "Text":
        return NarrativeText(text=text, coordinates=coordinates)
    elif element_type == "Figure":
        return FigureCaption(text=text, coordinates=coordinates)
    elif element_type == "List":
        return layout_list_to_list_items(text, coordinates)
    elif element_type == "Checked":
        return CheckBox(checked=True, coordinates=coordinates)
    elif element_type == "Unchecked":
        return CheckBox(checked=False, coordinates=coordinates)
    elif element_type == "PageBreak":
        return PageBreak()
    else:
        return Text(text=text, coordinates=coordinates)


def layout_list_to_list_items(text: str, coordinates: List[float]) -> List[Element]:
    """Converts a list LayoutElement to a list of ListItem elements."""
    split_items = ENUMERATED_BULLETS_RE.split(text)
    # NOTE(robinson) - this means there wasn't a match for the enumerated bullets
    if len(split_items) == 1:
        split_items = UNICODE_BULLETS_RE.split(text)

    list_items: List[Element] = list()
    for text_segment in split_items:
        if len(text_segment.strip()) > 0:
            list_items.append(ListItem(text=text_segment.strip(), coordinates=coordinates))

    return list_items


def document_to_element_list(document, include_page_breaks: bool = False) -> List[Element]:
    """Converts a DocumentLayout object to a list of unstructured elements."""
    elements: List[Element] = list()
    num_pages = len(document.pages)
    for i, page in enumerate(document.pages):
        for element in page.elements:
            elements.append(element)
        if include_page_breaks and i < num_pages - 1:
            elements.append(PageBreak())

    return elements


def add_element_metadata(
    layout_elements,
    include_page_breaks: bool = False,
    filename: Optional[str] = None,
    url: Optional[str] = None,
) -> List[Element]:
    """Adds document metadata to the document element. Document metadata includes information
    like the filename, source url, and page number."""
    elements: List[Element] = list()
    page_number: int = 1
    for layout_element in layout_elements:
        element = normalize_layout_element(layout_element)
        metadata = ElementMetadata(filename=filename, url=url, page_number=page_number)
        if isinstance(element, list):
            for _element in element:
                _element.metadata = metadata
            elements.extend(element)
        elif isinstance(element, PageBreak):
            page_number += 1
            if include_page_breaks is True:
                elements.append(element)
        else:
            element.metadata = metadata
            elements.append(element)
    return elements


def convert_office_doc(input_filename: str, output_directory: str, target_format: str):
    """Converts a .doc file to a .docx file using the libreoffice CLI."""
    # NOTE(robinson) - In the future can also include win32com client as a fallback for windows
    # users who do not have LibreOffice installed
    # ref: https://stackoverflow.com/questions/38468442/
    #       multiple-doc-to-docx-file-conversion-using-python
    try:
        subprocess.call(
            [
                "soffice",
                "--headless",
                "--convert-to",
                target_format,
                "--outdir",
                output_directory,
                input_filename,
            ]
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            """soffice command was not found. Please install libreoffice
on your system and try again.

- Install instructions: https://www.libreoffice.org/get-help/install-howto/
- Mac: https://formulae.brew.sh/cask/libreoffice
- Debian: https://wiki.debian.org/LibreOffice"""
        )
