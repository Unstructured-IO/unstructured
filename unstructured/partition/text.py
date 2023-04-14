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


def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    encoding: Optional[str] = "utf-8",
    paragraph_grouper: Optional[Callable[[str], str]] = None,
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
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)

    if filename is not None:
        with open(filename, encoding=encoding) as f:
            try:
                file_text = f.read()
            except (UnicodeDecodeError, UnicodeError) as error:
                raise error

    elif file is not None:
        file_text = file.read()
        if isinstance(file_text, bytes):
            file_text = file_text.decode(encoding)

    elif text is not None:
        file_text = str(text)

    if paragraph_grouper is not None:
        file_text = paragraph_grouper(file_text)
    else:
        file_text = group_broken_paragraphs(file_text)

    file_content = split_by_paragraph(file_text)

    elements: List[Element] = []
    metadata = ElementMetadata(filename=filename)
    for ctext in file_content:
        ctext = ctext.strip()

        if ctext == "":
            continue
        if is_bulleted_text(ctext):
            elements.append(ListItem(text=clean_bullets(ctext), metadata=metadata))
        elif is_us_city_state_zip(ctext):
            elements.append(Address(text=ctext, metadata=metadata))
        elif is_possible_narrative_text(ctext):
            elements.append(NarrativeText(text=ctext, metadata=metadata))
        elif is_possible_title(ctext):
            elements.append(Title(text=ctext, metadata=metadata))
        else:
            elements.append(Text(text=ctext, metadata=metadata))

    return elements
