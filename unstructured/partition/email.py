import email
import sys
import re
from email.message import Message
from typing import Dict, IO, List, Optional, Tuple

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from unstructured.cleaners.core import replace_mime_encodings, clean_extra_whitespace
from unstructured.cleaners.extract import (
    extract_ip_address,
    extract_ip_address_name,
    extract_mapi_id,
    extract_datetimetz,
    extract_email_address,
)
from unstructured.documents.email_elements import (
    EmailElement,
    Recipient,
    BodyText,
    Sender,
    Subject,
    ReceivedInfo,
    MetaData,
)
from unstructured.documents.elements import Text
from unstructured.partition.html import partition_html
from unstructured.partition.text import split_by_paragraph, partition_text


VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html", "text/plain"]


def _parse_received_data(data: str) -> List[EmailElement]:

    ip_address_names = extract_ip_address_name(data)
    ip_addresses = extract_ip_address(data)
    mapi_id = extract_mapi_id(data)
    datetimetz = extract_datetimetz(data)

    elements: List[EmailElement] = list()
    if ip_address_names and ip_addresses:
        for name, ip in zip(ip_address_names, ip_addresses):
            elements.append(MetaData(name=name, text=ip))
    if mapi_id:
        elements.append(MetaData(name="mapi_id", text=mapi_id[0]))
    if datetimetz:
        elements.append(MetaData(name="received_datetimetz", text=datetimetz[0]))

    return elements


def _parse_email_address(data: str) -> Tuple[str, str]:
    email_address = extract_email_address(data)

    name = re.split("<[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+>", data.lower())[0].title().strip()

    return name, email_address[0]


def _partition_header(msg: Message) -> List[EmailElement]:
    elements: List[Text] = list()
    for item in msg.raw_items():
        if item[0] == "To":
            text = _parse_email_address(item[1])
            print(text)
            elements.append(Recipient(name=text[0], text=text[1]))
        elif item[0] == "From":
            text = _parse_email_address(item[1])
            print(text)
            elements.append(Sender(name=text[0], text=text[1]))
        elif item[0] == "Subject":
            print(item[1])
            elements.append(Subject(text=item[1]))
        elif item[0] == "Received":
            print(item[1])
            elements.append(ReceivedInfo(_parse_received_data(item[1])))
        else:
            print(item[0], item[1])
            elements.append(MetaData(name=item[0], text=item[1]))

    return elements


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
                        # Note(harrell) mypy wants to just us `w` when opening the file but this
                        # causes an error since the payloads are bytes not str
                        f.write(attachment["payload"])  # type: ignore
    return list_attachments


def partition_email(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
    get_meta_data: bool = False,
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
        elements = BodyText(partition_text(file_content=content))

    if get_meta_data:
        elements += _partition_header(msg)

    return elements
