from __future__ import annotations

import copy
import datetime
import email
import os
import re
from email import policy
from email.headerregistry import AddressHeader
from email.message import EmailMessage
from functools import partial
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import IO, Any, Callable, Final, Optional, Type, cast

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import clean_extra_whitespace, replace_mime_encodings
from unstructured.cleaners.extract import (
    extract_datetimetz,
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
from unstructured.file_utils.encoding import (
    COMMON_ENCODINGS,
    format_encoding_str,
    read_txt_file,
    validate_encoding,
)
from unstructured.file_utils.filetype import add_metadata_with_filetype
from unstructured.file_utils.model import FileType
from unstructured.logger import logger
from unstructured.nlp.patterns import EMAIL_DATETIMETZ_PATTERN_RE
from unstructured.partition.common import (
    convert_to_bytes,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.html import partition_html
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text import partition_text

VALID_CONTENT_SOURCES: Final[list[str]] = ["text/html", "text/plain"]
DETECTION_ORIGIN: str = "email"


def _parse_received_data(data: str) -> list[Element]:
    ip_address_names = extract_ip_address_name(data)
    ip_addresses = extract_ip_address(data)
    mapi_id = extract_mapi_id(data)
    datetimetz = extract_datetimetz(data)

    elements: list[Element] = []
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


def _strip_angle_brackets(data: str) -> str:
    """Remove angle brackets from the beginning and end of the string if they exist.

    Returns:
    str: The string with surrounding angle brackets removed.

    Example:
    >>> _strip_angle_brackets("<example>")
    'example'
    >>> _strip_angle_brackets("<another>test>")
    'another>test'
    >>> _strip_angle_brackets("<<edge>>")
    '<edge>'
    """
    return re.sub(r"^<|>$", "", data)


def partition_email_header(msg: EmailMessage) -> list[Element]:

    def append_address_header_elements(header: AddressHeader, element_type: Type[Element]):
        for addr in header.addresses:
            elements.append(
                element_type(
                    name=addr.display_name or addr.username, text=addr.addr_spec  # type: ignore
                )
            )

    elements: list[Element] = []

    for msg_field, msg_value in msg.items():
        if msg_field in {"To", "Bcc", "Cc"}:
            append_address_header_elements(msg_value, Recipient)
        elif msg_field == "From":
            append_address_header_elements(msg_value, Sender)
        elif msg_field == "Subject":
            elements.append(Subject(text=msg_value))
        elif msg_field == "Received":
            elements += _parse_received_data(msg_value)
        elif msg_field == "Message-ID":
            elements.append(MetaData(name=msg_field, text=_strip_angle_brackets(str(msg_value))))
        else:
            elements.append(MetaData(name=msg_field, text=msg_value))

    return elements


def find_signature(msg: EmailMessage) -> Optional[str]:
    """Extracts the signature from an email message, if it's available."""
    payload: Any = msg.get_payload()
    if not isinstance(payload, list):
        return None

    payload = cast(list[EmailMessage], payload)
    for item in payload:
        if item.get_content_type().endswith("signature"):
            return item.get_payload()

    return None


def build_email_metadata(
    msg: EmailMessage,
    filename: Optional[str],
    metadata_last_modified: Optional[str] = None,
    last_modification_date: Optional[str] = None,
) -> ElementMetadata:
    """Creates an ElementMetadata object from the header information in the email."""
    signature = find_signature(msg)

    header_dict = dict(msg.raw_items())
    email_date = header_dict.get("Date")

    def parse_recipients(header_value: Optional[str]) -> Optional[list[str]]:
        if header_value is not None:
            return [recipient.strip() for recipient in header_value.split(",")]
        return None

    if email_date is not None:
        email_date = convert_to_iso_8601(email_date)

    email_message_id = header_dict.get("Message-ID")
    if email_message_id:
        email_message_id = _strip_angle_brackets(email_message_id)

    element_metadata = ElementMetadata(
        bcc_recipient=parse_recipients(header_dict.get("Bcc")),
        cc_recipient=parse_recipients(header_dict.get("Cc")),
        email_message_id=email_message_id,
        sent_to=parse_recipients(header_dict.get("To")),
        sent_from=parse_recipients(header_dict.get("From")),
        subject=msg.get("Subject"),
        signature=signature,
        last_modified=metadata_last_modified or email_date or last_modification_date,
        filename=filename,
    )
    element_metadata.detection_origin = DETECTION_ORIGIN
    return element_metadata


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
    message: EmailMessage,
    output_dir: Optional[str] = None,
) -> list[dict[str, str]]:
    list_attachments: list[Any] = []

    for part in message.walk():
        if "content-disposition" in part:
            cdisp = part["content-disposition"].split(";")
            cdisp = [clean_extra_whitespace(item) for item in cdisp]

            attachment_info: dict[str, Any] = {}
            for item in cdisp:
                if item.lower() in ("attachment", "inline"):
                    continue
                key, value = item.split("=", 1)
                key = clean_extra_whitespace(key.replace('"', ""))
                value = clean_extra_whitespace(value.replace('"', ""))
                attachment_info[clean_extra_whitespace(key)] = clean_extra_whitespace(
                    value,
                )
            attachment_info["payload"] = part.get_payload(decode=True)
            list_attachments.append(attachment_info)

            for idx, attachment in enumerate(list_attachments):
                if output_dir:
                    if "filename" in attachment:
                        filename = output_dir + "/" + attachment["filename"]
                        with open(filename, "wb") as f:
                            # Note(harrell) mypy wants to just us `w` when opening the file but this
                            # causes an error since the payloads are bytes not str
                            f.write(attachment["payload"])
                    else:
                        with NamedTemporaryFile(
                            mode="wb",
                            dir=output_dir,
                            delete=False,
                        ) as f:
                            list_attachments[idx]["filename"] = os.path.basename(f.name)
                            f.write(attachment["payload"])

    return list_attachments


def has_embedded_image(element: Element):
    PATTERN = re.compile(r"\[image: .+\]")
    return PATTERN.search(element.text)


def find_embedded_image(
    element: NarrativeText | Title, indices: re.Match[str]
) -> tuple[Element, Element]:
    start, end = indices.start(), indices.end()

    image_raw_info = element.text[start:end]
    image_info = clean_extra_whitespace(image_raw_info.split(":")[1])
    element.text = element.text.replace("[image: " + image_info[:-1] + "]", "")
    return Image(text=image_info[:-1], detection_origin="email"), element


def parse_email(
    filename: Optional[str] = None, file: Optional[IO[bytes]] = None
) -> tuple[Optional[str], EmailMessage]:
    if filename is not None:
        with open(filename, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
    elif file is not None:
        f_bytes = convert_to_bytes(file)
        msg = email.message_from_bytes(f_bytes, policy=policy.default)
    else:
        raise ValueError("Either 'filename' or 'file' must be provided.")

    encoding = None
    charsets = msg.get_charsets() or []
    for charset in charsets:
        if charset and charset.strip() and validate_encoding(charset):
            encoding = charset
            break

    formatted_encoding = format_encoding_str(encoding) if encoding else None
    msg = cast(EmailMessage, msg)
    return formatted_encoding, msg


@process_metadata()
@add_metadata_with_filetype(FileType.EML)
@add_chunking_strategy
def partition_email(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    content_source: str = "text/html",
    encoding: Optional[str] = None,
    include_headers: bool = False,
    max_partition: Optional[int] = 1500,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    process_attachments: bool = False,
    attachment_partitioner: Optional[Callable[..., list[Element]]] = None,
    min_partition: Optional[int] = 0,
    chunking_strategy: Optional[str] = None,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    date_from_file_object: bool = False,
    **kwargs: Any,
) -> list[Element]:
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
    metadata_last_modified
        The last modified date for the document.
    process_attachments
        If True, partition_email will process email attachments in addition to
        processing the content of the email itself.
    attachment_partitioner
        The partitioning function to use to process attachments.
    min_partition
        The minimum number of characters to include in a partition. Only applies if
        processing the text/plain content.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True and inference
        from message header failed, attempt to infer last_modified metadata from bytes,
        otherwise set it to None.
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
            msg = email.message_from_string(file_text, policy=policy.default)
    elif file is not None:
        extracted_encoding, msg = parse_email(file=file)
        if extracted_encoding:
            detected_encoding = extracted_encoding
        else:
            detected_encoding, file_text = read_txt_file(file=file, encoding=encoding)
            msg = email.message_from_string(file_text, policy=policy.default)
    elif text is not None:
        _text: str = str(text)
        msg = email.message_from_string(_text, policy=policy.default)
    else:
        return []
    if not encoding:
        encoding = detected_encoding
    msg = cast(EmailMessage, msg)

    is_encrypted = False
    content_map: dict[str, str] = {}
    for part in msg.walk():
        # NOTE(robinson) - content dispostiion is None for the content of the email itself.
        # Other dispositions include "attachment" for attachments
        if part.get_content_disposition() is not None:
            continue
        content_type = part.get_content_type()

        # NOTE(robinson) - Per RFC 2015, the content type for emails with PGP encrypted
        # content is multipart/encrypted
        # ref: https://www.ietf.org/rfc/rfc2015.txt
        if content_type.endswith("encrypted"):
            is_encrypted = True

        # NOTE(andymli) - we can determine if text is base64 encoded via the
        # content-transfer-encoding property of a part
        # https://www.w3.org/Protocols/rfc1341/5_Content-Transfer-Encoding.html
        if (
            part.get_content_maintype() == "text"
            and part.get("content-transfer-encoding", None) == "base64"
        ):
            try:
                content_map[content_type] = part.get_payload(decode=True).decode(encoding)
            except (UnicodeDecodeError, UnicodeError):
                content_map[content_type] = part.get_payload()
        else:
            content_map[content_type] = part.get_payload()

    content = None
    if content_source in content_map:
        content = content_map.get(content_source)
    # NOTE(robinson) - If the chosen content source is not available and there is
    # another valid content source, fall back to the other valid source
    else:
        for _content_source in VALID_CONTENT_SOURCES:
            content = content_map.get(_content_source, "")
            if content:
                logger.warning(
                    f"{content_source} was not found. Falling back to {_content_source}."
                )
                break

    elements: list[Element] = []

    if is_encrypted:
        logger.warning(
            "Encrypted email detected. Partition function will return an empty list.",
        )

    elif not content:
        pass

    elif content_source == "text/html":
        # NOTE(robinson) - In the .eml files, the HTML content gets stored in a format that
        # looks like the following, resulting in extraneous "=" characters in the output if
        # you don't clean it up
        # <ul> =
        #    <li>Item 1</li>=
        #    <li>Item 2<li>=
        # </ul>

        content = content.replace("=\n", "").replace("=\r\n", "")
        elements = partition_html(
            text=content,
            include_metadata=False,
            metadata_filename=metadata_filename,
            languages=[""],
            detection_origin="email",
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
                    common_encodings: list[str] = []
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
            min_partition=min_partition,
            languages=[""],
            include_metadata=False,  # metadata is overwritten later, so no need to compute it here
            detection_origin="email",
        )
    else:
        raise ValueError(
            f"Invalid content source: {content_source}. "
            f"Valid content sources are: {VALID_CONTENT_SOURCES}",
        )

    for idx, element in enumerate(elements):
        indices = has_embedded_image(element)
        if (isinstance(element, (NarrativeText, Title))) and indices:
            image_info, clean_element = find_embedded_image(element, indices)
            elements[idx] = clean_element
            elements.insert(idx + 1, image_info)

    header: list[Element] = []
    if include_headers:
        header = partition_email_header(msg)
    all_elements = header + elements

    last_modification_date = None
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
    elif file is not None:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )

    metadata = build_email_metadata(
        msg,
        filename=metadata_filename or filename,
        metadata_last_modified=metadata_last_modified,
        last_modification_date=last_modification_date,
    )
    for element in all_elements:
        element.metadata = copy.deepcopy(metadata)

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
                attached_elements = attachment_partitioner(
                    filename=attached_filename,
                    metadata_last_modified=metadata_last_modified,
                    max_partition=max_partition,
                    min_partition=min_partition,
                )
                for element in attached_elements:
                    element.metadata.filename = attached_file
                    element.metadata.file_directory = None
                    element.metadata.attached_to_filename = metadata_filename or filename
                    all_elements.append(element)

    elements = list(
        apply_lang_metadata(
            elements=all_elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )

    return elements
