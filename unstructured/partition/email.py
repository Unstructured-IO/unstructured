import email
import sys
from email.message import Message
from typing import Dict, IO, List, Optional

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from unstructured.cleaners.core import replace_mime_encodings, clean_extra_whitespace
from unstructured.documents.elements import Element, Text
from unstructured.partition.html import partition_html


VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html"]


def extract_attachment_info(
    message: Message, output_dir: Optional[str] = None
) -> List[Dict[str, str]]:
    list_attachments = []
    attachment_info = {}
    for part in message.walk():
        if "content-disposition" in part:
            cdisp = part["content-disposition"].split(";")
            cdisp = [clean_extra_whitespace(item) for item in cdisp]

            for item in cdisp:
                if item.lower() == "attachment":
                    continue
                key, value = item.split("=")
                key = clean_extra_whitespace(key.replace('"', ""))
                value = clean_extra_whitespace(value.replace('"', ""))
                attachment_info[clean_extra_whitespace(key)] = clean_extra_whitespace(value)
            attachment_info["payload"] = part.get_payload(decode=True)
            list_attachments.append(attachment_info)

            for attachment in list_attachments:
                if output_dir:
                    filename = output_dir + "/" + attachment["filename"]
                    with open(filename, "wb") as f:
                        # mypy wants to just us `w` when opening the file but this
                        # causes an error since the payloads are bytes not str
                        f.write(attachment["payload"])  # type: ignore
    return list_attachments


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
