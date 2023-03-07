import email
import re
import sys
from email.message import Message
from typing import IO, Dict, List, Optional, Tuple, Union

from unstructured.partition.common import exactly_one

if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from unstructured.cleaners.core import clean_extra_whitespace, replace_mime_encodings
from unstructured.cleaners.extract import (
    extract_datetimetz,
    extract_email_address,
    extract_ip_address,
    extract_ip_address_name,
    extract_mapi_id,
)
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Image,
    NarrativeText,
    Text,
    Title,
)
from unstructured.documents.email_elements import (
    MetaData,
    ReceivedInfo,
    Recipient,
    Sender,
    Subject,
)
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text, split_by_paragraph

VALID_CONTENT_SOURCES: Final[List[str]] = ["text/html", "text/plain"]


def _parse_received_data(data: str) -> List[Element]:
    ip_address_names = extract_ip_address_name(data)
    ip_addresses = extract_ip_address(data)
    mapi_id = extract_mapi_id(data)
    datetimetz = extract_datetimetz(data)

    elements: List[Element] = []
    if ip_address_names and ip_addresses:
        for name, ip in zip(ip_address_names, ip_addresses):
            elements.append(ReceivedInfo(name=name, text=ip))
    if mapi_id:
        elements.append(ReceivedInfo(name="mapi_id", text=mapi_id[0]))
    if datetimetz:
        elements.append(
            ReceivedInfo(name="received_datetimetz", text=str(datetimetz), datestamp=datetimetz),
        )
    return elements


def _parse_email_address(data: str) -> Tuple[str, str]:
    email_address = extract_email_address(data)

    PATTERN = "<[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+>"  # noqa: W605 Note(harrell)
    name = re.split(PATTERN, data.lower())[0].title().strip()

    return name, email_address[0]


def partition_email_header(msg: Message) -> List[Element]:
    elements: List[Element] = []
    for item in msg.raw_items():
        if item[0] == "To":
            text = _parse_email_address(item[1])
            elements.append(Recipient(name=text[0], text=text[1]))
        elif item[0] == "From":
            text = _parse_email_address(item[1])
            elements.append(Sender(name=text[0], text=text[1]))
        elif item[0] == "Subject":
            elements.append(Subject(text=item[1]))
        elif item[0] == "Received":
            elements += _parse_received_data(item[1])
        else:
            elements.append(MetaData(name=item[0], text=item[1]))

    return elements


def extract_attachment_info(
    message: Message,
    output_dir: Optional[str] = None,
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


def has_embedded_image(element):
    PATTERN = re.compile("\[image: .+\]")  # noqa: W605 NOTE(harrell)
    return PATTERN.search(element.text)


def find_embedded_image(
    element: Union[NarrativeText, Title],
    indices: re.Match,
) -> Tuple[Element, Element]:
    start, end = indices.start(), indices.end()

    image_raw_info = element.text[start:end]
    image_info = clean_extra_whitespace(image_raw_info.split(":")[1])
    element.text = element.text.replace("[image: " + image_info[:-1] + "]", "")

    return Image(text=image_info[:-1]), element


def partition_email(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
    encoding: Optional[str] = None,
    include_headers: bool = False,
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
    encoding
        The encoding method used to decode the text input. If None, utf-8 will be used.
    """
    if not encoding:
        encoding = "utf-8"

    if content_source not in VALID_CONTENT_SOURCES:
        raise ValueError(
            f"{content_source} is not a valid value for content_source. "
            f"Valid content sources are: {VALID_CONTENT_SOURCES}",
        )

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)

    if filename is not None:
        with open(filename) as f:
            msg = email.message_from_file(f)

    elif file is not None:
        file_content = file.read()
        if isinstance(file_content, bytes):
            file_text = file_content.decode(encoding)
        else:
            file_text = file_content

        msg = email.message_from_string(file_text)

    elif text is not None:
        _text: str = str(text)
        msg = email.message_from_string(_text)

    content_map: Dict[str, str] = {}
    for part in msg.walk():
        # NOTE(robinson) - content dispostiion is None for the content of the email itself.
        # Other dispositions include "attachment" for attachments
        if part.get_content_disposition() is not None:
            continue
        content_type = part.get_content_type()
        content_map[content_type] = part.get_payload()

    content = content_map.get(content_source, "")
    if not content:
        raise ValueError(f"{content_source} content not found in email")

    if content_source == "text/html":
        # NOTE(robinson) - In the .eml files, the HTML content gets stored in a format that
        # looks like the following, resulting in extraneous "=" characters in the output if
        # you don't clean it up
        # <ul> =
        #    <li>Item 1</li>=
        #    <li>Item 2<li>=
        # </ul>
        list_content = content.split("=\n")
        content = "".join(list_content)
        elements = partition_html(text=content, include_metadata=False)
        for element in elements:
            if isinstance(element, Text):
                element.apply(replace_mime_encodings)
    elif content_source == "text/plain":
        list_content = split_by_paragraph(content)
        elements = partition_text(text=content)

    for idx, element in enumerate(elements):
        indices = has_embedded_image(element)
        if (isinstance(element, (NarrativeText, Title))) and indices:
            image_info, clean_element = find_embedded_image(element, indices)
            elements[idx] = clean_element
            elements.insert(idx + 1, image_info)

    header: List[Element] = []
    if include_headers:
        header = partition_email_header(msg)
    all_elements = header + elements

    for element in all_elements:
        element.metadata = ElementMetadata(filename=filename)
    return all_elements
