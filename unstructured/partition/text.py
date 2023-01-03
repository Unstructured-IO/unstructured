import re
from typing import IO, List, Optional

from unstructured.documents.elements import Element, ListItem, NarrativeText, Title, Text

from unstructured.cleaners.core import clean_bullets
from unstructured.partition.text_type import (
    is_possible_narrative_text,
    is_possible_title,
    is_bulleted_text,
)


def split_by_paragraph(content: str) -> List[str]:
    return re.split(r"\n\n\n|\n\n|\r\n|\r|\n", content)


def partition_text(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    file_content: Optional[List] = None,
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
    file_content: A list of strings. Chunks of texts from the document
            in a list. Typically used by `parition_email`.
    """

    if not any([filename, file, text, file_content]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text and not file_content:
        with open(filename, "r") as f:
            file_text = f.read()

    elif file is not None and not filename and not text and not file_content:
        file_text = file.read()

    elif text is not None and not filename and not file and not file_content:
        file_text: str = str(text)

    elif file_content is not None and not filename and not file and not text:
        pass

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    if not file_content:
        file_content = split_by_paragraph(file_text)

    elements: List[Text] = list()
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
