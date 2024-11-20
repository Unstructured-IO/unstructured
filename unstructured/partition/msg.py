from __future__ import annotations

import os
import re
import tempfile
from typing import IO, Any, Iterator, Optional

from oxmsg import Message
from oxmsg.attachment import Attachment

from unstructured.documents.elements import Element, ElementMetadata
from unstructured.file_utils.model import FileType
from unstructured.logger import logger
from unstructured.partition.common import UnsupportedFileFormatError
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text
from unstructured.utils import is_temp_file_path, lazyproperty


def partition_msg(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    process_attachments: bool = True,
    **kwargs: Any,
) -> list[Element]:
    """Partitions a MSFT Outlook .msg file

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    metadata_filename
        The filename to use for the metadata.
    metadata_last_modified
        The last modified date for the document.
    process_attachments
        If True, partition_email will process email attachments in addition to
        processing the content of the email itself.
    """
    opts = MsgPartitionerOptions(
        file=file,
        file_path=filename,
        metadata_file_path=metadata_filename,
        metadata_last_modified=metadata_last_modified,
        partition_attachments=process_attachments,
        kwargs=kwargs,
    )

    return list(_MsgPartitioner.iter_message_elements(opts))


class MsgPartitionerOptions:
    """Encapsulates partitioning option validation, computation, and application of defaults."""

    def __init__(
        self,
        *,
        file: IO[bytes] | None,
        file_path: str | None,
        metadata_file_path: str | None,
        metadata_last_modified: str | None,
        partition_attachments: bool,
        kwargs: dict[str, Any],
    ):
        self._file = file
        self._file_path = file_path
        self._metadata_file_path = metadata_file_path
        self._metadata_last_modified = metadata_last_modified
        self._partition_attachments = partition_attachments
        self._kwargs = kwargs

    @lazyproperty
    def extra_msg_metadata(self) -> ElementMetadata:
        """ElementMetadata suitable for use on an element formed from message content.

        These are only the metadata fields specific to email messages. The remaining metadata
        fields produced by the delegate partitioner are used as produced.

        None of these metadata fields change based on the element, so we just compute it once.
        """
        msg = self.msg

        sent_from = [s.strip() for s in sender.split(",")] if (sender := msg.sender) else None
        sent_to = [r.email_address for r in msg.recipients] or None
        bcc_recipient = (
            [c.strip() for c in bcc.split(",")] if (bcc := msg.message_headers.get("Bcc")) else None
        )
        cc_recipient = (
            [c.strip() for c in cc.split(",")] if (cc := msg.message_headers.get("Cc")) else None
        )
        if email_message_id := msg.message_headers.get("Message-Id"):
            email_message_id = re.sub(r"^<|>$", "", email_message_id)  # Strip angle brackets

        element_metadata = ElementMetadata(
            bcc_recipient=bcc_recipient,
            cc_recipient=cc_recipient,
            email_message_id=email_message_id,
            sent_from=sent_from,
            sent_to=sent_to,
            subject=msg.subject or None,
        )
        element_metadata.detection_origin = "msg"

        return element_metadata

    @lazyproperty
    def is_encrypted(self) -> bool:
        """True when message is encrypted."""
        # NOTE(robinson) - Per RFC 2015, the content type for emails with PGP encrypted content
        # is multipart/encrypted (ref: https://www.ietf.org/rfc/rfc2015.txt)
        # NOTE(scanny) - pretty sure we're going to want to dig deeper to discover messages that are
        # encrypted with something other than PGP.
        #   - might be able to distinguish based on PID_MESSAGE_CLASS = 'IPM.Note.Signed'
        #   - Content-Type header might include "application/pkcs7-mime" for Microsoft S/MIME
        #     encryption.
        return "encrypted" in self.msg.message_headers.get("Content-Type", "")

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
        email_date = sent_date.isoformat() if (sent_date := self.msg.sent_date) else None
        return self._metadata_last_modified or email_date or self._last_modified

    @lazyproperty
    def msg(self) -> Message:
        """The `oxmsg.Message` object loaded from file or filename."""
        return Message.load(self._msg_file)

    @lazyproperty
    def partition_attachments(self) -> bool:
        """True when message attachments should also be partitioned."""
        return self._partition_attachments

    @lazyproperty
    def partitioning_kwargs(self) -> dict[str, Any]:
        """The "extra" keyword arguments received by `partition_msg()`.

        These are passed along to delegate partitioners which extract keyword args like
        `chunking_strategy` etc. in their decorators to control metadata behaviors, etc.
        """
        return self._kwargs

    @lazyproperty
    def _last_modified(self) -> str | None:
        """The best last-modified date available from source-file, None if not available."""
        if not self._file_path or is_temp_file_path(self._file_path):
            return None

        return get_last_modified_date(self._file_path)

    @lazyproperty
    def _msg_file(self) -> str | IO[bytes]:
        """The source for the bytes of the message, either a file-path or a file-like object."""
        if file_path := self._file_path:
            return file_path

        if file := self._file:
            return file

        raise ValueError("one of `file` or `filename` arguments must be provided")


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
            elements = partition_html(
                text=html_body,
                metadata_filename=self._opts.metadata_file_path,
                metadata_file_type=FileType.MSG,
                metadata_last_modified=self._opts.metadata_last_modified,
                **self._opts.partitioning_kwargs,
            )
        elif msg.body:
            elements = partition_text(
                text=msg.body,
                metadata_filename=self._opts.metadata_file_path,
                metadata_file_type=FileType.MSG,
                metadata_last_modified=self._opts.metadata_last_modified,
                **self._opts.partitioning_kwargs,
            )
        else:
            elements: list[Element] = []

        # -- augment the element metadata with email-specific values --
        email_specific_metadata = self._opts.extra_msg_metadata
        for e in elements:
            e.metadata.update(email_specific_metadata)
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
            try:
                elements = partition(
                    detached_file_path,
                    metadata_filename=self._attachment_file_name,
                    metadata_last_modified=self._attachment_last_modified,
                    **self._opts.partitioning_kwargs,
                )
            except UnsupportedFileFormatError:
                return

            for e in elements:
                e.metadata.attached_to_filename = self._opts.metadata_file_path
                yield e

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
