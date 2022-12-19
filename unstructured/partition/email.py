import email
from typing import Dict, Final, IO, List, Optional

from unstructured.cleaners.core import replace_mime_encodings
from unstructured.documents.elements import Element, Text
from unstructured.partition.html import partition_html


VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html"]


def partition_email(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
) -> List[Element]:
    """Partitions an .eml documents into its constituent elements.
    Parameters
    ----------
     filename
        A string defining the target filename path.
    file
        A file-like object using "r" mode --> open(filename, "r").
    text
        The string representation of the .eml document.
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
        raise ValueError("text/html content not found in email")

    # NOTE(robinson) - In the .eml files, the HTML content gets stored in a format that
    # looks like the following, resulting in extraneous "=" chracters in the output if
    # you don't clean it up
    # <ul> =
    #    <li>Item 1</li>=
    #    <li>Item 2<li>=
    # </ul>
    content = "".join(content.split("=\n"))

    elements = partition_html(text=content)
    for element in elements:
        if isinstance(element, Text):
            element.apply(replace_mime_encodings)

    return elements
