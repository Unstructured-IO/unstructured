import re
from typing import IO, List, Optional

from unstructured.documents.elements import Element, ListItem, NarrativeText, Title

from unstructured.cleaners.core import clean_bullets
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.text_type import (
    is_possible_narrative_text,
    is_possible_title,
    is_bulleted_text,
)


def split_by_paragraph(content: str) -> List[str]:
    return re.split(PARAGRAPH_PATTERN, content)


def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
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
    """

    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text:
        with open(filename, "r") as f:
            file_text = f.read()

    elif file is not None and not filename and not text:
        file_text = file.read()

    elif text is not None and not filename and not file:
        file_text = str(text)

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    file_content = split_by_paragraph(file_text)

    elements: List[Element] = list()
    for ctext in file_content:

        ctext = ctext.strip()

        if ctext == "":
            break
        if is_bulleted_text(ctext):
            elements.append(ListItem(text=clean_bullets(ctext)))
        elif is_possible_narrative_text(ctext):
            elements.append(NarrativeText(text=ctext))
        elif is_possible_title(ctext):
            elements.append(Title(text=ctext))
    return elements
