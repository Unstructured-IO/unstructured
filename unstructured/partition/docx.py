from typing import IO, List, Optional

import docx

from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.partition.common import exactly_one
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)

# NOTE(robinson) - documentation on built in styles can be found at the link below
# ref: https://python-docx.readthedocs.io/en/latest/user/
#   styles-understanding.html#paragraph-styles-in-default-template
STYLE_TO_ELEMENT_MAPPING = {
    "Caption": Text,  # TODO(robinson) - add caption element type
    "Heading 1": Title,
    "Heading 2": Title,
    "Heading 3": Title,
    "Heading 4": Title,
    "Heading 5": Title,
    "Heading 6": Title,
    "Heading 7": Title,
    "Heading 8": Title,
    "Heading 9": Title,
    "Intense Quote": Text,  # TODO(robinson) - add quote element type
    "List": ListItem,
    "List 2": ListItem,
    "List 3": ListItem,
    "List Bullet": ListItem,
    "List Bullet 2": ListItem,
    "List Bullet 3": ListItem,
    "List Continue": ListItem,
    "List Continue 2": ListItem,
    "List Continue 3": ListItem,
    "List Number": ListItem,
    "List Number 2": ListItem,
    "List Number 3": ListItem,
    "List Paragraph": ListItem,
    "Macro Text": Text,
    "No Spacing": Text,
    "Quote": Text,  # TODO(robinson) - add quote element type
    "Subtitle": Title,
    "TOCHeading": Title,
    "Title": Title,
}


def partition_docx(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    metadata_filename: Optional[str] = None,
) -> List[Element]:
    """Partitions Microsoft Word Documents in .docx format into its document elements.

    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata. Relevant because partition_doc converts the
        document to .docx before partition. We want the original source filename in the
        metadata.
    """

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file)

    if filename is not None:
        document = docx.Document(filename)
    elif file is not None:
        document = docx.Document(file)

    metadata_filename = metadata_filename or filename
    elements: List[Element] = []
    for paragraph in document.paragraphs:
        element = _paragraph_to_element(paragraph)
        if element is not None:
            element.metadata = ElementMetadata(filename=metadata_filename)
            elements.append(element)

    return elements


def _paragraph_to_element(paragraph: docx.text.paragraph.Paragraph) -> Optional[Text]:
    """Converts a docx Paragraph object into the appropriate unstructured document element.
    If the paragraph style is "Normal" or unknown, we try to predict the element type from the
    raw text."""
    text = paragraph.text
    style_name = paragraph.style.name

    if len(text.strip()) == 0:
        return None

    element_class = STYLE_TO_ELEMENT_MAPPING.get(style_name)

    # NOTE(robinson) - The "Normal" style name will return None since it's in the mapping.
    # Unknown style names will also return None
    if element_class is None:
        return _text_to_element(text)
    else:
        return element_class(text)


def _text_to_element(text: str) -> Optional[Text]:
    """Converts raw text into an unstructured Text element."""
    if is_bulleted_text(text):
        clean_text = clean_bullets(text).strip()
        return ListItem(text=clean_bullets(text)) if clean_text else None

    elif is_us_city_state_zip(text):
        return Address(text=text)

    if len(text) < 2:
        return None
    elif is_possible_narrative_text(text):
        return NarrativeText(text)
    elif is_possible_title(text):
        return Title(text)
    else:
        return Text(text)
