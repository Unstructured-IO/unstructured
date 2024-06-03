from __future__ import annotations

import copy
import os
import tempfile
from typing import IO, Any, Iterator, Optional

from oxmsg import Message
from oxmsg.attachment import Attachment

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, ElementMetadata, process_metadata
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.logger import logger
from unstructured.partition.common import (
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.html import partition_html
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text import partition_text
from unstructured.utils import is_temp_file_path, lazyproperty


@process_metadata()
@add_metadata_with_filetype(FileType.MSG)
@add_chunking_strategy
def partition_msg(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    date_from_file_object: bool = False,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    process_attachments: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions a MSFT Outlook .msg file

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True and inference
        from message header failed, attempt to infer last_modified metadata from bytes,
        otherwise set it to None.
    metadata_filename
        The filename to use for the metadata.
    metadata_last_modified
        The last modified date for the document.
    process_attachments
        If True, partition_email will process email attachments in addition to
        processing the content of the email itself.
    """
    opts = MsgPartitionerOptions(
        date_from_file_object=date_from_file_object,
        file=file,
        file_path=filename,
        metadata_file_path=metadata_filename,
        metadata_last_modified=metadata_last_modified,
        partition_attachments=process_attachments,
    )

    return list(
        apply_lang_metadata(
            elements=_MsgPartitioner.iter_message_elements(opts),
            languages=kwargs.get("languages", ["auto"]),
            detect_language_per_element=kwargs.get("detect_language_per_element", False),
        )
    )


class MsgPartitionerOptions:
    """Encapsulates partitioning option validation, computation, and application of defaults."""

    def __init__(
        self,
        *,
        date_from_file_object: bool,
        file: IO[bytes] | None,
        file_path: str | None,
        metadata_file_path: str | None,
        metadata_last_modified: str | None,
        partition_attachments: bool,
    ):
        self._date_from_file_object = date_from_file_object
        self._file = file
        self._file_path = file_path
        self._metadata_file_path = metadata_file_path
        self._metadata_last_modified = metadata_last_modified
        self._partition_attachments = partition_attachments

    @lazyproperty
    def is_encrypted(self) -> bool:
        """True when message is encrypted."""
        # NOTE(robinson) - Per RFC 2015, the content type for emails with PGP encrypted content
        # is multipart/encrypted (ref: https://www.ietf.org/rfc/rfc2015.txt)
        if "encrypted" in self.msg.message_headers.get("Content-Type", ""):
            return True
        # -- pretty sure we're going to want to dig deeper to discover messages that are encrypted
        # -- with something other than PGP.
        #    - might be able to distinguish based on PID_MESSAGE_CLASS = 'IPM.Note.Signed'
        #    - Content-Type header might include "application/pkcs7-mime" for Microsoft S/MIME
        #      encryption.
        return False

    @lazyproperty
    def metadata_file_path(self) -> str | None:
        """Best available path for MSG file.

        The value is the caller supplied `metadata_filename` if present, falling back to the
        source file-path if that was provided, otherwise `None`.
        """
        return self._metadata_file_path or self._file_path

    @lazyproperty
    def metadata_last_modified(self) -> str | None:
        """Caller override for `.metadata.last_modified` to be applied to all elements."""
        return self._metadata_last_modified

    @lazyproperty
    def msg(self) -> Message:
        """The `oxmsg.Message` object loaded from file or filename."""
        return Message.load(self._msg_file)

    @property
    def msg_metadata(self) -> ElementMetadata:
        """ElementMetadata suitable for use on an element formed from message content.

        A distinct instance is returned on each reference such that downstream changes to the
        metadata of one element is not also reflected in another element.
        """
        return copy.copy(self._msg_metadata)

    @lazyproperty
    def partition_attachments(self) -> bool:
        """True when message attachments should also be partitioned."""
        return self._partition_attachments

    @lazyproperty
    def partitioning_kwargs(self) -> dict[str, Any]:
        """Partitioning keyword-arguments to be passed along to attachment partitioner."""
        # TODO: no good reason we can't accept and pass along any file-type specific kwargs
        # the caller might want to send along.
        return {}

    @lazyproperty
    def _last_modified(self) -> str | None:
        """The best last-modified date available from source-file, None if not available."""
        if self._file_path:
            return (
                None
                if is_temp_file_path(self._file_path)
                else get_last_modified_date(self._file_path)
            )

        if self._file:
            return (
                get_last_modified_date_from_file(self._file)
                if self._date_from_file_object
                else None
            )

        return None

    @lazyproperty
    def _msg_file(self) -> str | IO[bytes]:
        """The source for the bytes of the message, either a file-path or a file-like object."""
        if file_path := self._file_path:
            return file_path

        if file := self._file:
            return file

        raise ValueError("one of `file` or `filename` arguments must be provided")

    @property
    def _msg_metadata(self) -> ElementMetadata:
        """ElementMetadata "template" for elements of this message.

        None of these metadata fields change based on the element, so compute it once here and then
        just make a separate copy for each element.
        """
        msg = self.msg

        email_date = sent_date.isoformat() if (sent_date := msg.sent_date) else None
        sent_from = [s.strip() for s in sender.split(",")] if (sender := msg.sender) else None
        sent_to = [r.email_address for r in msg.recipients] or None

        element_metadata = ElementMetadata(
            filename=self.metadata_file_path,
            last_modified=self._metadata_last_modified or email_date or self._last_modified,
            sent_from=sent_from,
            sent_to=sent_to,
            subject=msg.subject or None,
        )
        element_metadata.detection_origin = "msg"

        return element_metadata


class _MsgPartitioner:
    """Partitions Outlook email message (MSG) files."""

    def __init__(self, opts: MsgPartitionerOptions):
        self._opts = opts

    @classmethod
    def iter_message_elements(cls, opts: MsgPartitionerOptions) -> Iterator[Element]:
        """Partition MS Outlook email messages (.msg files) into elements."""
        if opts.is_encrypted:
            logger.warning("Encrypted email detected. Partitioner will return an empty list.")
            return

        yield from cls(opts)._iter_message_elements()

    def _iter_message_elements(self) -> Iterator[Element]:
        """Partition MS Outlook email messages (.msg files) into elements."""
        yield from self._iter_message_body_elements()

        if not self._opts.partition_attachments:
            return

        for attachment in self._attachments:
            yield from _AttachmentPartitioner.iter_elements(attachment, self._opts)

    @lazyproperty
    def _attachments(self) -> tuple[Attachment, ...]:
        """The `oxmsg.attachment.Attachment` objects for this message."""
        return tuple(self._opts.msg.attachments)

    def _iter_message_body_elements(self) -> Iterator[Element]:
        """Partition the message body (but not the attachments)."""
        msg = self._opts.msg

        if html_body := msg.html_body:
            elements = partition_html(text=html_body, languages=[""])
        elif msg.body:
            elements = partition_text(text=msg.body, languages=[""])
        else:
            elements: list[Element] = []

        # -- replace the element metadata with email-specific values --
        for e in elements:
            e.metadata = self._opts.msg_metadata
            yield e


class _AttachmentPartitioner:
    """Partitions an attachment to a MSG file."""

    def __init__(self, attachment: Attachment, opts: MsgPartitionerOptions):
        self._attachment = attachment
        self._opts = opts

    @classmethod
    def iter_elements(
        cls, attachment: Attachment, opts: MsgPartitionerOptions
    ) -> Iterator[Element]:
        """Partition an `oxmsg.attachment.Attachment` from an Outlook email message (.msg file)."""
        return cls(attachment, opts)._iter_elements()

    def _iter_elements(self) -> Iterator[Element]:
        """Partition the file in an `oxmsg.attachment.Attachment` into elements."""
        from unstructured.partition.auto import partition

        with tempfile.TemporaryDirectory() as tmp_dir_path:
            # -- save attachment as file in this temporary directory --
            detached_file_path = os.path.join(tmp_dir_path, self._attachment_file_name)
            with open(detached_file_path, "wb") as f:
                f.write(self._file_bytes)

            # -- partition the attachment --
            for element in partition(
                detached_file_path,
                metadata_filename=self._attachment_file_name,
                metadata_last_modified=self._attachment_last_modified,
                **self._opts.partitioning_kwargs,
            ):
                element.metadata.attached_to_filename = self._opts.metadata_file_path
                yield element

    @lazyproperty
    def _attachment_file_name(self) -> str:
        """The original name of the attached file, no path.

        This value is 'unknown' if it is not present in the MSG file (not expected).
        """
        return self._attachment.file_name or "unknown"

    @lazyproperty
    def _attachment_last_modified(self) -> str | None:
        """ISO8601 string timestamp of attachment last-modified date.

        This value generally available on the attachment and will be the most reliable last-modifed
        time. There are fallbacks for when it is not present, ultimately `None` if we have no way
        of telling.
        """
        if last_modified := self._attachment.last_modified:
            return last_modified.isoformat()
        return self._opts.metadata_last_modified

    @lazyproperty
    def _file_bytes(self) -> bytes:
        """The bytes of the attached file."""
        return self._attachment.file_bytes or b""
