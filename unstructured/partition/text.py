import re
from typing import IO, Callable, List, Optional

from unstructured.cleaners.core import clean_bullets, group_broken_paragraphs
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Text,
    Title,
)
from unstructured.file_utils.encoding import read_txt_file
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common import exactly_one
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)


def split_by_paragraph(content: str) -> List[str]:
    return re.split(PARAGRAPH_PATTERN, content)


@add_metadata_with_filetype(FileType.TXT)
def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = None,
    paragraph_grouper: Optional[Callable[[str], str]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
) -> List[Element]:
    """Partitions an .txt documents into its constituent elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the .txt document.
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    paragrapher_grouper
        A str -> str function for fixing paragraphs that are interrupted by line breaks
        for formatting purposes.
    include_metadata
        Determines whether or not metadata is included in the output.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)

    if filename is not None:
        encoding, file_text = read_txt_file(filename=filename, encoding=encoding)

    elif file is not None:
        encoding, file_text = read_txt_file(file=file, encoding=encoding)

    elif text is not None:
        file_text = str(text)

    if paragraph_grouper is not None:
        file_text = paragraph_grouper(file_text)
    else:
        file_text = group_broken_paragraphs(file_text)

    file_content = split_by_paragraph(file_text)

    metadata_filename = metadata_filename or filename

    elements: List[Element] = []
    metadata = (
        ElementMetadata(filename=metadata_filename) if include_metadata else ElementMetadata()
    )
    for ctext in file_content:
        ctext = ctext.strip()

        if ctext:
            element = element_from_text(ctext)
            element.metadata = metadata
            elements.append(element)

    return elements


def element_from_text(text: str) -> Element:
    if is_bulleted_text(text):
        return ListItem(text=clean_bullets(text))
    elif is_us_city_state_zip(text):
        return Address(text=text)
    elif is_possible_narrative_text(text):
        return NarrativeText(text=text)
    elif is_possible_title(text):
        return Title(text=text)
    else:
        return Text(text=text)
