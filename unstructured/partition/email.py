import datetime
import email
import os
import re
import sys
from email.message import Message
from functools import partial
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import IO, Callable, Dict, List, Optional, Tuple, Union

from unstructured.file_utils.encoding import (
    COMMON_ENCODINGS,
    format_encoding_str,
    read_txt_file,
    validate_encoding,
)
from unstructured.partition.common import (
    convert_to_bytes,
    exactly_one,
)

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
    process_metadata,
)
from unstructured.documents.email_elements import (
    MetaData,
    ReceivedInfo,
    Recipient,
    Sender,
    Subject,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_DATETIMETZ_PATTERN_RE
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text

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
            ReceivedInfo(
                name="received_datetimetz",
                text=str(datetimetz),
                datestamp=datetimetz,
            ),
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


def build_email_metadata(
    msg: Message,
    filename: Optional[str],
    metadata_date: Optional[str] = None,
) -> ElementMetadata:
    """Creates an ElementMetadata object from the header information in the email."""
    header_dict = dict(msg.raw_items())
    email_date = header_dict.get("Date")
    if email_date is not None:
        email_date = convert_to_iso_8601(email_date)

    sent_from = header_dict.get("From")
    if sent_from is not None:
        sent_from = [sender.strip() for sender in sent_from.split(",")]

    sent_to = header_dict.get("To")
    if sent_to is not None:
        sent_to = [recipient.strip() for recipient in sent_to.split(",")]

    return ElementMetadata(
        sent_to=sent_to,
        sent_from=sent_from,
        subject=header_dict.get("Subject"),
        date=metadata_date or email_date,
        filename=filename,
    )


def convert_to_iso_8601(time: str) -> Optional[str]:
    """Converts the datetime from the email output to ISO-8601 format."""
    cleaned_time = clean_extra_whitespace(time)
    regex_match = EMAIL_DATETIMETZ_PATTERN_RE.search(cleaned_time)
    if regex_match is None:
        logger.warning(
            f"{time} did not match RFC-2822 format. Unable to extract the time.",
        )
        return None

    start, end = regex_match.span()
    dt_string = cleaned_time[start:end]
    datetime_object = datetime.datetime.strptime(dt_string, "%a, %d %b %Y %H:%M:%S %z")
    return datetime_object.isoformat()


def extract_attachment_info(
    message: Message,
    output_dir: Optional[str] = None,
) -> List[Dict[str, str]]:
    list_attachments = []

    for part in message.walk():
        if "content-disposition" in part:
            cdisp = part["content-disposition"].split(";")
            cdisp = [clean_extra_whitespace(item) for item in cdisp]

            for item in cdisp:
                attachment_info = {}

                if item.lower() == "attachment":
                    continue
                key, value = item.split("=")
                key = clean_extra_whitespace(key.replace('"', ""))
                value = clean_extra_whitespace(value.replace('"', ""))
                attachment_info[clean_extra_whitespace(key)] = clean_extra_whitespace(
                    value,
                )
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


def parse_email(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
) -> Tuple[Optional[str], Message]:
    if filename is not None:
        with open(filename, "rb") as f:
            msg = email.message_from_binary_file(f)
    elif file is not None:
        f_bytes = convert_to_bytes(file)
        msg = email.message_from_bytes(f_bytes)
    else:
        raise ValueError("Either 'filename' or 'file' must be provided.")

    encoding = None
    charsets = msg.get_charsets() or []
    for charset in charsets:
        if charset and charset.strip() and validate_encoding(charset):
            encoding = charset
            break

    formatted_encoding = format_encoding_str(encoding) if encoding else None

    return formatted_encoding, msg


@process_metadata()
@add_metadata_with_filetype(FileType.EML)
def partition_email(
    filename: Optional[str] = None,
    file: Optional[Union[IO[bytes], SpooledTemporaryFile]] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
    encoding: Optional[str] = None,
    include_headers: bool = False,
    max_partition: Optional[int] = 1500,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_date: Optional[str] = None,
    process_attachments: bool = False,
    attachment_partitioner: Optional[Callable] = None,
    min_partition: Optional[int] = 0,
    **kwargs,
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
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied. Only applies if processing the text/plain content.
    metadata_filename
        The filename to use for the metadata.
    metadata_date
        The last modified date for the document.
    process_attachments
        If True, partition_email will process email attachments in addition to
        processing the content of the email itself.
    attachment_partitioner
        The partitioning function to use to process attachments.
    min_partition
        The minimum number of characters to include in a partition. Only applies if
        processing the text/plain content.
    """
    if content_source not in VALID_CONTENT_SOURCES:
        raise ValueError(
            f"{content_source} is not a valid value for content_source. "
            f"Valid content sources are: {VALID_CONTENT_SOURCES}",
        )

    if text is not None and text.strip() == "" and not file and not filename:
        return []

    # Verify that only one of the arguments was provided
    exactly_one(filename=filename, file=file, text=text)
    detected_encoding = "utf-8"
    if filename is not None:
        extracted_encoding, msg = parse_email(filename=filename)
        if extracted_encoding:
            detected_encoding = extracted_encoding
        else:
            detected_encoding, file_text = read_txt_file(
                filename=filename,
                encoding=encoding,
            )
            msg = email.message_from_string(file_text)
    elif file is not None:
        extracted_encoding, msg = parse_email(file=file)
        if extracted_encoding:
            detected_encoding = extracted_encoding
        else:
            detected_encoding, file_text = read_txt_file(file=file, encoding=encoding)
            msg = email.message_from_string(file_text)
    elif text is not None:
        _text: str = str(text)
        msg = email.message_from_string(_text)
    if not encoding:
        encoding = detected_encoding

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
        elements = []

    elif content_source == "text/html":
        # NOTE(robinson) - In the .eml files, the HTML content gets stored in a format that
        # looks like the following, resulting in extraneous "=" characters in the output if
        # you don't clean it up
        # <ul> =
        #    <li>Item 1</li>=
        #    <li>Item 2<li>=
        # </ul>
        list_content = content.split("=\n")
        content = "".join(list_content)
        elements = partition_html(
            text=content,
            include_metadata=False,
            metadata_filename=metadata_filename,
        )
        for element in elements:
            if isinstance(element, Text):
                _replace_mime_encodings = partial(
                    replace_mime_encodings,
                    encoding=encoding,
                )
                try:
                    element.apply(_replace_mime_encodings)
                except (UnicodeDecodeError, UnicodeError):
                    # If decoding fails, try decoding through common encodings
                    common_encodings = []
                    for x in COMMON_ENCODINGS:
                        _x = format_encoding_str(x)
                        if _x != encoding:
                            common_encodings.append(_x)

                    for enc in common_encodings:
                        try:
                            _replace_mime_encodings = partial(
                                replace_mime_encodings,
                                encoding=enc,
                            )
                            element.apply(_replace_mime_encodings)
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue

    elif content_source == "text/plain":
        elements = partition_text(
            text=content,
            encoding=encoding,
            max_partition=max_partition,
            metadata_filename=metadata_filename or filename,
            min_partition=min_partition,
        )

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

    metadata = build_email_metadata(
        msg,
        filename=metadata_filename or filename,
        metadata_date=metadata_date,
    )
    for element in all_elements:
        element.metadata = metadata

    if process_attachments:
        with TemporaryDirectory() as tmpdir:
            extract_attachment_info(msg, tmpdir)
            attached_files = os.listdir(tmpdir)
            for attached_file in attached_files:
                attached_filename = os.path.join(tmpdir, attached_file)
                if attachment_partitioner is None:
                    raise ValueError(
                        "Specify the attachment_partitioner kwarg to process attachments.",
                    )
                attached_elements = attachment_partitioner(filename=attached_filename)
                for element in attached_elements:
                    element.metadata.filename = attached_file
                    element.metadata.file_directory = None
                    element.metadata.attached_to_filename = metadata_filename or filename
                    all_elements.append(element)

    return all_elements
