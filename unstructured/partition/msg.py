import os
import tempfile
from typing import IO, Callable, Dict, List, Optional

import msg_parser

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, ElementMetadata, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.partition.email import convert_to_iso_8601
from unstructured.partition.html import partition_html
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text import partition_text


@process_metadata()
@add_metadata_with_filetype(FileType.MSG)
@add_chunking_strategy
def partition_msg(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    max_partition: Optional[int] = 1500,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    process_attachments: bool = False,
    attachment_partitioner: Optional[Callable] = None,
    min_partition: Optional[int] = 0,
    chunking_strategy: Optional[str] = None,
    languages: Optional[List[str]] = ["auto"],
    detect_language_per_element: bool = False,
    **kwargs,
) -> List[Element]:
    """Partitions a MSFT Outlook .msg file

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied. Only applies if processing text/plain content.
    metadata_filename
        The filename to use for the metadata.
    process_attachments
        If True, partition_email will process email attachments in addition to
        processing the content of the email itself.
    attachment_partitioner
        The partitioning function to use to process attachments.
    metadata_last_modified
        The last modified date for the document.
    min_partition
        The minimum number of characters to include in a partition. Only applies if
        processing text/plain content.
    languages
        User defined value for `metadata.languages` if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    """
    exactly_one(filename=filename, file=file)

    if filename is not None:
        msg_obj = msg_parser.MsOxMessage(filename)
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        msg_obj = msg_parser.MsOxMessage(tmp.name)

    # NOTE(robinson) - Per RFC 2015, the content type for emails with PGP encrypted
    # content is multipart/encrypted
    # ref: https://www.ietf.org/rfc/rfc2015.txt
    content_type = msg_obj.header_dict.get("Content-Type", "")
    is_encrypted = "encrypted" in content_type
    text = msg_obj.body
    elements: List[Element] = []
    if is_encrypted:
        logger.warning(
            "Encrypted email detected. Partition function will return an empty list.",
        )
    elif text is None:
        pass
    elif "<html>" in text or "</div>" in text:
        elements = partition_html(
            text=text,
            languages=[""],
            include_metadata=False,  # metadata is overwritten later, so no need to compute it here
            detection_origin="msg",
        )
    else:
        elements = partition_text(
            text=text,
            max_partition=max_partition,
            min_partition=min_partition,
            languages=[""],
            include_metadata=False,  # metadata is overwritten later, so no need to compute it here
            detection_origin="msg",
        )

    metadata = build_msg_metadata(
        msg_obj,
        metadata_filename or filename,
        metadata_last_modified=metadata_last_modified,
    )
    for element in elements:
        element.metadata = metadata

    if process_attachments:
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_msg_attachment_info(msg_obj=msg_obj, output_dir=tmpdir)
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
                    elements.append(element)

    elements = list(
        apply_lang_metadata(
            elements=elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )
    return elements


def build_msg_metadata(
    msg_obj: msg_parser.MsOxMessage,
    filename: Optional[str],
    metadata_last_modified: Optional[str],
    languages: Optional[List[str]] = ["auto"],
) -> ElementMetadata:
    """Creates an ElementMetadata object from the header information in the email."""
    email_date = getattr(msg_obj, "sent_date", None)
    if email_date is not None:
        email_date = convert_to_iso_8601(email_date)

    sent_from = getattr(msg_obj, "sender", None)
    if sent_from is not None:
        sent_from = [str(sender) for sender in sent_from]

    sent_to = getattr(msg_obj, "recipients", None)
    if sent_to is not None:
        sent_to = [str(recipient) for recipient in sent_to]

    element_metadata = ElementMetadata(
        sent_to=sent_to,
        sent_from=sent_from,
        subject=getattr(msg_obj, "subject", None),
        last_modified=metadata_last_modified or email_date,
        filename=filename,
        languages=languages,
    )
    element_metadata.detection_origin = "msg"
    return element_metadata


def extract_msg_attachment_info(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    output_dir: Optional[str] = None,
    msg_obj: Optional[msg_parser.MsOxMessage] = None,
) -> List[Dict[str, str]]:
    """Extracts information from email message attachments and returns a list of dictionaries.
    If 'output_dir' is provided, attachments are also saved to that directory.
    """
    exactly_one(filename=filename, file=file, msg_obj=msg_obj)

    if filename is not None:
        msg_obj = msg_parser.MsOxMessage(filename)
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        msg_obj = msg_parser.MsOxMessage(tmp.name)
    elif msg_obj is not None:
        msg_obj = msg_obj

    list_attachments = []

    for attachment in msg_obj.attachments:
        attachment_info = {}

        attachment_info["filename"] = attachment.AttachLongFilename
        attachment_info["extension"] = attachment.AttachExtension
        attachment_info["file_size"] = attachment.AttachmentSize
        attachment_info["payload"] = attachment.data

        list_attachments.append(attachment_info)

        if output_dir is not None:
            output_filename = output_dir + "/" + attachment_info["filename"]
            with open(output_filename, "wb") as f:
                f.write(attachment.data)

    return list_attachments
