import email
from typing import Dict, Final, IO, List, Optional

from unstructured.cleaners.core import replace_mime_encodings
from unstructured.documents.elements import Element, Text
from unstructured.partition.html import partition_html


VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html", "text/plain"]

def split_by_paragraph(content: str) -> List[str]:
    return re.split(r"\n\n\n|\n\n|\r\n|\r|\n", content)

def partition_text(content: List[str]) -> List[Element]:
    """ Categorizes the body of the an email and
        returns the email elements.
    """
    elements: List[Text] = list()
    for ctext in content:
        if ctext == "":
            break
        if is_possible_narrative_text(ctext):
            elements.append(NarrativeText(text=ctext))
        elif is_possible_title(ctext):
            elements.append(Title(text=ctext))
        elif is_bulleted_text(ctext):
            elements.append(ListItem(text=ctext))
    return elements

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
        elements = partition_html(text=content)
        for element in elements:
            if isinstance(element, Text):
                element.apply(replace_mime_encodings)
    elif content_source == "text/plain":
        elements = partition_text(content)

    return elements
