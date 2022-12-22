import email
import sys
import re
from typing import Dict, IO, List, Optional

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from unstructured.cleaners.core import replace_mime_encodings, clean_bullets
from unstructured.documents.email_elements import EmailElement, BodyText
from unstructured.documents.elements import Text, NarrativeText, ListItem, Title
from unstructured.partition.html import partition_html
from unstructured.partition.text_type import (
    is_possible_narrative_text,
    is_possible_title,
    is_bulleted_text,
)


VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html", "text/plain"]


def split_by_paragraph(content: str) -> List[str]:
    return re.split(r"\n\n\n|\n\n|\r\n|\r|\n", content)


def partition_text(content: List[str]) -> List[EmailElement]:
    """Categorizes the body of the an email and
    returns the email elements.
    """

    elements: List[Text] = list()
    for ctext in content:
        # clean bullet doesn't recognize bullet with whitespace around it
        # may want to fix in clean bullet but don't want to break other dependent code
        ctext = ctext.strip()

        if ctext == "":
            break
        if is_bulleted_text(ctext):
            elements.append(ListItem(text=clean_bullets(ctext)))
        elif is_possible_narrative_text(ctext):
            elements.append(NarrativeText(text=ctext))
        elif is_possible_title(ctext):
            elements.append(Title(text=ctext))
    return BodyText(elements)


def partition_email(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
) -> List[EmailElement]:
    """Partitions an .eml documents into its constituent elements.
    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the .eml document.
    content_source
        default: "text/html"
        other: "text/plain"
    """
    if content_source not in VALID_CONTENT_SOURCES:
        raise ValueError(
            f"{content_source} is not a valid value for content_source. "
            f"Valid content sources are: {VALID_CONTENT_SOURCES}"
        )

    if not any([filename, file, text]):
        raise ValueError("One of filename, file, or text must be specified.")

    if filename is not None and not file and not text:
        with open(filename, "r") as f:
            msg = email.message_from_file(f)

    elif file is not None and not filename and not text:
        file_text = file.read()
        msg = email.message_from_string(file_text)

    elif text is not None and not filename and not file:
        _text: str = str(text)
        msg = email.message_from_string(_text)

    else:
        raise ValueError("Only one of filename, file, or text can be specified.")

    content_map: Dict[str, str] = {
        part.get_content_type(): part.get_payload() for part in msg.walk()
    }

    content = content_map.get(content_source, "")
    if not content:
        raise ValueError(f"{content_source} content not found in email")

    # NOTE(robinson) - In the .eml files, the HTML content gets stored in a format that
    # looks like the following, resulting in extraneous "=" chracters in the output if
    # you don't clean it up
    # <ul> =
    #    <li>Item 1</li>=
    #    <li>Item 2<li>=
    # </ul>
    content = split_by_paragraph(content)

    if content_source == "text/html":
        content = "".join(content)
        elements = partition_html(text=content)

        for element in elements:
            if isinstance(element, Text):
                element.apply(replace_mime_encodings)
    elif content_source == "text/plain":
        elements = partition_text(content)

    return elements
