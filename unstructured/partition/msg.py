import tempfile
from typing import IO, Dict, List, Optional

import msg_parser

from unstructured.documents.elements import Element, ElementMetadata
from unstructured.partition.common import exactly_one
from unstructured.partition.email import convert_to_iso_8601
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text


def partition_msg(
    filename: Optional[str] = None,
    file: Optional[IO] = None,
) -> List[Element]:
    """Partitions a MSFT Outlook .msg file

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    """
    exactly_one(filename=filename, file=file)

    if filename is not None:
        msg_obj = msg_parser.MsOxMessage(filename)
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        msg_obj = msg_parser.MsOxMessage(tmp.name)

    text = msg_obj.body
    if "<html>" in text or "</div>" in text:
        elements = partition_html(text=text)
    else:
        elements = partition_text(text=text)

    metadata = build_msg_metadata(msg_obj)
    metadata.filename = filename
    for element in elements:
        element.metadata = metadata

    return elements


def build_msg_metadata(msg_obj: msg_parser.MsOxMessage) -> ElementMetadata:
    """Creates an ElementMetadata object from the header information in the emai."""
    email_date = getattr(msg_obj, "sent_date", None)
    if email_date is not None:
        email_date = convert_to_iso_8601(email_date)

    sent_from = getattr(msg_obj, "sender", None)
    if sent_from is not None:
        sent_from = [str(sender) for sender in sent_from]

    sent_to = getattr(msg_obj, "recipients", None)
    if sent_to is not None:
        sent_to = [str(recipient) for recipient in sent_to]

    return ElementMetadata(
        sent_to=sent_to,
        sent_from=sent_from,
        subject=getattr(msg_obj, "subject", None),
        date=email_date,
    )


def extract_msg_attachment_info(
    filename: str,
    file: Optional[IO] = None,
    output_dir: Optional[str] = None,
) -> List[Dict[str, str]]:
    exactly_one(filename=filename, file=file)

    if filename is not None:
        msg_obj = msg_parser.MsOxMessage(filename)
    elif file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(file.read())
        tmp.close()
        msg_obj = msg_parser.MsOxMessage(tmp.name)

    list_attachments = []

    for attachment in msg_obj.attachments:
        attachment_info = {}

        attachment_info["filename"] = attachment.AttachLongFilename
        attachment_info["extension"] = attachment.AttachExtension
        attachment_info["file_size"] = attachment.AttachmentSize
        attachment_info["payload"] = attachment.data

        list_attachments.append(attachment_info)

        if output_dir is not None:
            filename = output_dir + "/" + attachment_info["filename"]
            with open(filename, "wb") as f:
                f.write(attachment.data)

    return list_attachments
