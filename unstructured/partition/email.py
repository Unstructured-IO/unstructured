"""Provides `partition_email()` function.

Suitable for use with `.eml` files, which can be exported from many email clients.
"""

from __future__ import annotations

import datetime as dt
import email
import email.policy
import email.utils
import io
import os
from email.message import EmailMessage, MIMEPart
from typing import IO, Any, Final, Iterator, cast

from unstructured.documents.elements import Element, ElementMetadata
from unstructured.file_utils.model import FileType
from unstructured.partition.common import UnsupportedFileFormatError
from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.html import partition_html
from unstructured.partition.text import partition_text
from unstructured.utils import lazyproperty

VALID_CONTENT_SOURCES: Final[tuple[str, ...]] = ("text/html", "text/plain")


def partition_email(
    filename: str | None = None,
    *,
    file: IO[bytes] | None = None,
    content_source: str = "text/html",
    metadata_filename: str | None = None,
    metadata_last_modified: str | None = None,
    process_attachments: bool = True,
    **kwargs: Any,
) -> list[Element]:
    """Partitions an .eml file into document elements.

    Args:
        filename: str path of the target file.
        file: A file-like object open for reading bytes (not str) e.g. --> open(filename, "rb").
        content_source: The preferred message body. Many emails contain both a plain-text and an
            HTML version of the message body. By default, the HTML version will be used when
            available. Specifying "text/plain" will cause the plain-text version to be preferred.
            When the preferred version is not available, the other version will be used.
        metadata_filename: The file-path to use for metadata purposes. Useful when the target file
            is specified as a file-like object or when `filename` is a temporary file and the
            original file-path is known or a more meaningful file-path is desired.
        metadata_last_modified: The last-modified timestamp to be applied in metadata. Useful when
            a file-like object (which can have no last-modified date) target is used. The
            last-modified metadata is otherwise drawn from the filesystem when a path is provided.
        process_attachments: When True, also partition any attachments in the message after
            partitioning the message body. All document elements appear in the single returned
            element list. The filename of the attachment, when available, is used as the
            `filename` metadata value for elements arising from the attachment.

    Note that all global keyword arguments such as `unique_element_ids`, `language` and
    `chunking_strategy` can be used and will be passed along to the decorators that implement
    those functions. Further, any keyword arguments applicable to HTML will be passed along to the
    HTML partitioner when processing an HTML message body.
    """
    ctx = EmailPartitioningContext.load(
        file_path=filename,
        file=file,
        content_source=content_source,
        metadata_file_path=metadata_filename,
        metadata_last_modified=metadata_last_modified,
        process_attachments=process_attachments,
        kwargs=kwargs,
    )

    return list(_EmailPartitioner.iter_elements(ctx=ctx))


class EmailPartitioningContext:
    """Encapsulates partitioning option validation, computation, and application of defaults."""

    def __init__(
        self,
        file_path: str | None = None,
        file: IO[bytes] | None = None,
        content_source: str = "text/html",
        metadata_file_path: str | None = None,
        metadata_last_modified: str | None = None,
        process_attachments: bool = False,
        kwargs: dict[str, Any] = {},
    ):
        self._file_path = file_path
        self._file = file
        self._content_source = content_source
        self._metadata_file_path = metadata_file_path
        self._metadata_last_modified = metadata_last_modified
        self._process_attachments = process_attachments
        self._kwargs = kwargs

    @classmethod
    def load(
        cls,
        file_path: str | None,
        file: IO[bytes] | None,
        content_source: str,
        metadata_file_path: str | None,
        metadata_last_modified: str | None,
        process_attachments: bool,
        kwargs: dict[str, Any],
    ) -> EmailPartitioningContext:
        """Construct and validate an instance."""
        return cls(
            file_path=file_path,
            file=file,
            content_source=content_source,
            metadata_file_path=metadata_file_path,
            metadata_last_modified=metadata_last_modified,
            process_attachments=process_attachments,
            kwargs=kwargs,
        )._validate()

    @lazyproperty
    def bcc_addresses(self) -> list[str] | None:
        """The "blind carbon-copy" Bcc: addresses of the message."""
        bccs = self.msg.get_all("Bcc")
        if not bccs:
            return None
        addrs = email.utils.getaddresses(bccs)
        return [email.utils.formataddr(addr) for addr in addrs]

    @lazyproperty
    def body_part(self) -> MIMEPart | None:
        """The message part containing the actual textual email message.

        This is as opposed to attachments or "related" parts like an image that appears in the
        message etc.
        """
        return self.msg.get_body(preferencelist=self.content_type_preference)

    @lazyproperty
    def cc_addresses(self) -> list[str] | None:
        """The "carbon-copy" Cc: addresses of the message."""
        ccs = self.msg.get_all("Cc")
        if not ccs:
            return None
        addrs = email.utils.getaddresses(ccs)
        return [email.utils.formataddr(addr) for addr in addrs]

    @lazyproperty
    def content_type_preference(self) -> tuple[str, ...]:
        """Whether to prefer HTML or plain-text body when message-body has both.

        The default order of preference is `("html", "plain")`. The order can be switched by
        specifying `"text/plain"` as the `content_source` arg value.
        """
        return ("plain", "html") if self._content_source == "text/plain" else ("html", "plain")

    @lazyproperty
    def email_metadata(self) -> ElementMetadata:
        """The email-specific metadata fields for this message.

        Suitable for use with `.metadata.update()` on the base metadata applied to message body
        elements by delegate partitioners for text and HTML.
        """
        return ElementMetadata(
            bcc_recipient=self.bcc_addresses,
            cc_recipient=self.cc_addresses,
            email_message_id=self.message_id,
            sent_from=[self.from_address] if self.from_address else None,
            sent_to=self.to_addresses,
            subject=self.subject,
        )

    @lazyproperty
    def from_address(self) -> str | None:
        """The address of the message sender."""
        froms = self.msg.get_all("From")
        if not froms:
            # -- this should never occur because the From: header is mandatory per RFC 5322 --
            return None
        addrs = email.utils.getaddresses(froms)
        formatted_addrs = [email.utils.formataddr(addr) for addr in addrs]
        return formatted_addrs[0]

    @lazyproperty
    def message_id(self) -> str | None:
        """The value of the Message-ID: header, when present."""
        raw_id = self.msg.get("Message-ID")
        if not raw_id:
            return None
        return raw_id.strip().strip("<>")

    @lazyproperty
    def metadata_file_path(self) -> str | None:
        """The best available file-path information for this email message.

        It's value is computed according to these rules, applied in order:

          - The `metadata_filename` arg value when one was provided to `partition_email()`.
          - The `file_path` value when one was provided.
          - None otherwise.

        This value is used as the `filename` metadata value for elements produced by partitioning
        the email message (but not those from its attachments).
        """
        return self._metadata_file_path or self._file_path or None

    @lazyproperty
    def metadata_last_modified(self) -> str | None:
        """The best available last-modified date for this message, as an ISO8601 string.

        It's value is computed according to these rules, applied in order:

          - The `metadata_last_modified` arg value when one was provided to `partition_email()`.
          - The date-time in the `Sent:` header of the message, when present.
          - The last-modified date recorded on the filesystem for `file_path` when it was provided.
          - None otherwise.

        This value is used as the `last_modified` metadata value for all elements produced by
        partitioning this email message, including any attachments.
        """
        return self._metadata_last_modified or self._sent_date or self._filesystem_last_modified

    @lazyproperty
    def msg(self) -> EmailMessage:
        """The Python stdlib `email.message.EmailMessage` object parsed from the EML file."""
        if self._file_path is not None:
            with open(self._file_path, "rb") as f:
                return cast(
                    EmailMessage, email.message_from_binary_file(f, policy=email.policy.default)
                )

        assert self._file is not None

        file_bytes = self._file.read()

        return cast(EmailMessage, email.message_from_bytes(file_bytes, policy=email.policy.default))

    @lazyproperty
    def partitioning_kwargs(self) -> dict[str, Any]:
        """The "extra" keyword arguments received by `partition_email()`.

        These are passed along to delegate partitioners which extract keyword args like
        `chunking_strategy` etc. in their decorators to control metadata behaviors, etc.
        """
        return self._kwargs

    @lazyproperty
    def process_attachments(self) -> bool:
        """When True, partition attachments in addition to the email message body.

        Any attachment having file-format that cannot be partitioned by unstructured is silently
        skipped.
        """
        return self._process_attachments

    @lazyproperty
    def subject(self) -> str | None:
        """The value of the Subject: header, when present."""
        subject = self.msg.get("Subject")
        if not subject:
            return None
        return subject

    @lazyproperty
    def to_addresses(self) -> list[str] | None:
        """The To: addresses of the message."""
        tos = self.msg.get_all("To")
        if not tos:
            return None
        addrs = email.utils.getaddresses(tos)
        return [email.utils.formataddr(addr) for addr in addrs]

    @lazyproperty
    def _filesystem_last_modified(self) -> str | None:
        """Last-modified retrieved from filesystem when a file-path was provided, None otherwise."""
        return get_last_modified_date(self._file_path) if self._file_path else None

    @lazyproperty
    def _sent_date(self) -> str | None:
        """ISO-8601 str representation of message sent-date, if available."""
        date_str = self.msg.get("Date")
        if not date_str:
            return None
        sent_date = email.utils.parsedate_to_datetime(date_str)
        return sent_date.astimezone(dt.timezone.utc).isoformat(timespec="seconds")

    def _validate(self) -> EmailPartitioningContext:
        """Raise on first invalid option, return self otherwise."""
        if not self._file_path and not self._file:
            raise ValueError(
                "no document specified; either a `filename` or `file` argument must be provided."
            )

        if self._file:
            if not isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
                self._file.read(0), bytes
            ):
                raise ValueError("file object must be opened in binary mode")
            self._file.seek(0)

        if self._content_source not in VALID_CONTENT_SOURCES:
            raise ValueError(
                f"{repr(self._content_source)} is not a valid value for content_source;"
                f" must be one of: {VALID_CONTENT_SOURCES}",
            )

        return self


class _EmailPartitioner:
    """Encapsulates the partitioning logic for email documents."""

    def __init__(self, ctx: EmailPartitioningContext):
        self._ctx = ctx

    @classmethod
    def iter_elements(cls, ctx: EmailPartitioningContext) -> Iterator[Element]:
        """Generate the document elements for the email described by `ctx`."""
        return cls(ctx=ctx)._iter_elements()

    def _iter_elements(self) -> Iterator[Element]:
        """Generate the document elements for the email described in the partitioning context.

        This optionally includes elements generated by partitioning any partitionable attachments
        in the message as well.
        """
        for e in self._iter_email_body_elements():
            e.metadata.update(self._ctx.email_metadata)
            yield e

        if not self._ctx.process_attachments:
            return

        for attachment in self._ctx.msg.iter_attachments():
            yield from _AttachmentPartitioner.iter_elements(attachment, self._ctx)

    def _iter_email_body_elements(self) -> Iterator[Element]:
        """Generate document elements from the email body."""
        body_part = self._ctx.body_part

        # -- it's possible to have no body part; that translates to zero elements --
        if body_part is None:
            return

        content_type = body_part.get_content_type()
        content = body_part.get_content()
        assert isinstance(content, str)

        if content_type == "text/html":
            yield from partition_html(
                text=content,
                metadata_filename=self._ctx.metadata_file_path,
                metadata_file_type=FileType.EML,
                metadata_last_modified=self._ctx.metadata_last_modified,
                **self._ctx.partitioning_kwargs,
            )
        else:
            yield from partition_text(
                text=content,
                metadata_filename=self._ctx.metadata_file_path,
                metadata_file_type=FileType.EML,
                metadata_last_modified=self._ctx.metadata_last_modified,
                **self._ctx.partitioning_kwargs,
            )


class _AttachmentPartitioner:
    """Partitions an attachment to a MSG file."""

    def __init__(self, attachment: EmailMessage, ctx: EmailPartitioningContext):
        self._attachment = attachment
        self._ctx = ctx

    @classmethod
    def iter_elements(
        cls, attachment: EmailMessage, ctx: EmailPartitioningContext
    ) -> Iterator[Element]:
        """Partition an attachment MIME-part from a MIME email message (.eml file)."""
        return cls(attachment, ctx)._iter_elements()

    def _iter_elements(self) -> Iterator[Element]:
        """Partition the byte-stream in the attachment MIME-part into elements.

        Generates zero elements if the attachment is not partitionable.
        """
        # -- `auto.partition()` imports this module, so we need to defer the import to here to
        # -- avoid a circular import.
        from unstructured.partition.auto import partition

        file = io.BytesIO(self._file_bytes)

        # -- partition the attachment --
        try:
            elements = partition(
                file=file,
                metadata_filename=self._attachment_file_name,
                metadata_last_modified=self._ctx.metadata_last_modified,
                **self._ctx.partitioning_kwargs,
            )
        except UnsupportedFileFormatError:
            # -- indicates `auto.partition()` has no partitioner for this file-format;
            # -- silently skip the attachment
            return

        for e in elements:
            e.metadata.attached_to_filename = self._attached_to_filename
            yield e

    @lazyproperty
    def _attached_to_filename(self) -> str | None:
        """The file-name (no path) of the message. `None` if not available."""
        file_path = self._ctx.metadata_file_path
        if file_path is None:
            return None
        return os.path.basename(file_path)

    @lazyproperty
    def _attachment_file_name(self) -> str | None:
        """The original name of the attached file, `None` if not present in the MIME part."""
        return self._attachment.get_filename()

    @lazyproperty
    def _file_bytes(self) -> bytes:
        """The bytes of the attached file."""
        content = self._attachment.get_content()

        if isinstance(content, str):
            return content.encode("utf-8")

        assert isinstance(content, bytes)
        return content
