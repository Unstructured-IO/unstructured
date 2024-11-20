"""Test suite for `unstructured.partition.email` module."""

from __future__ import annotations

import io
import tempfile
from email.message import EmailMessage
from typing import Any

import pytest

from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    CompositeElement,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.email import EmailPartitioningContext, partition_email

EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_partition_email_from_filename_can_partition_an_RFC_822_email():
    assert partition_email(example_doc_path("eml/simple-rfc-822.eml")) == [
        NarrativeText("This is an RFC 822 email message."),
        NarrativeText(
            "An RFC 822 message is characterized by its simple, text-based format, which includes"
            ' a header and a body. The header contains structured fields such as "From", "To",'
            ' "Date", and "Subject", each followed by a colon and the corresponding information.'
            " The body follows the header, separated by a blank line, and contains the main"
            " content of the email."
        ),
        NarrativeText(
            "The structure ensures compatibility and readability across different email systems"
            " and clients, adhering to the standards set by the Internet Engineering Task Force"
            " (IETF)."
        ),
    ]


def test_partition_email_from_file_can_partition_an_email():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        assert partition_email(file=f) == EXPECTED_OUTPUT


def test_partition_email_from_spooled_temp_file_can_partition_an_email():
    with tempfile.SpooledTemporaryFile() as file:
        with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
            file.write(f.read())
        file.seek(0)

        assert partition_email(file=file) == EXPECTED_OUTPUT


def test_partition_email_can_partition_an_HTML_only_email_with_Base64_ISO_8859_1_charset():
    assert partition_email(example_doc_path("eml/mime-html-only.eml")) == [
        NarrativeText("This is a text/html part."),
        NarrativeText(
            "The first emoticon, :) , was proposed by Scott Fahlman in 1982 to indicate just or"
            " sarcasm in text emails."
        ),
        NarrativeText(
            "Gmail was launched by Google in 2004 with 1 GB of free storage, significantly more"
            " than what other services offered at the time."
        ),
    ]


def test_extract_email_from_text_plain_matches_elements_extracted_from_text_html():
    file_path = example_doc_path("eml/fake-email.eml")

    elements_from_text = partition_email(file_path, content_source="text/plain")
    elements_from_html = partition_email(file_path, content_source="text/html")

    assert elements_from_text == EXPECTED_OUTPUT
    assert elements_from_html == EXPECTED_OUTPUT
    assert elements_from_html == elements_from_text


def test_partition_email_round_trips_via_json():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    assert_round_trips_through_JSON(elements)


# -- transfer-encodings --------------------------------------------------------------------------


def test_partition_email_partitions_an_HTML_part_with_Base64_encoded_UTF_8_charset():
    assert partition_email(example_doc_path("eml/fake-email-b64.eml")) == EXPECTED_OUTPUT


def test_partition_email_partitions_a_text_plain_part_with_Base64_encoded_windows_1255_charset():
    elements = partition_email(
        example_doc_path("eml/email-no-utf8-2008-07-16.062410.eml"),
        content_source="text/plain",
    )

    assert len(elements) == 30
    assert elements[1].text.startswith("אני חושב שזה לא יהיה מקצועי והוגן שאני אראה לך היכן")


def test_partition_email_partitions_an_html_part_with_quoted_printable_encoded_ISO_8859_1_charset():
    elements = partition_email(
        example_doc_path("eml/email-no-utf8-2014-03-17.111517.eml"),
        content_source="text/html",
        process_attachments=False,
    )

    assert len(elements) == 1
    assert isinstance(elements[0], Table)
    assert elements[0].text.startswith("Slava Gxyzxyz Hi Slava, The password for your Google")


# -- edge-cases ----------------------------------------------------------------------------------


def test_partition_email_accepts_a_whitespace_only_file():
    """Should produce no elements but should not raise an exception."""
    assert partition_email(example_doc_path("eml/empty.eml")) == []


def test_partition_email_can_partition_an_empty_email():
    assert (
        partition_email(example_doc_path("eml/mime-no-body.eml"), process_attachments=False) == []
    )


def test_partition_email_does_not_break_on_an_encrypted_message():
    assert (
        partition_email(example_doc_path("eml/fake-encrypted.eml"), process_attachments=False) == []
    )


def test_partition_email_finds_content_when_it_is_marked_with_content_disposition_inline():
    elements = partition_email(
        example_doc_path("eml/email-inline-content-disposition.eml"), process_attachments=False
    )

    assert len(elements) == 1
    e = elements[0]
    assert isinstance(e, Text)
    assert e.text == "This is a test of inline"


def test_partition_email_from_filename_malformed_encoding():
    elements = partition_email(filename=example_doc_path("eml/fake-email-malformed-encoding.eml"))
    assert elements == EXPECTED_OUTPUT


# -- error behaviors -----------------------------------------------------------------------------


def test_partition_email_raises_when_no_message_source_is_specified():
    with pytest.raises(ValueError, match="no document specified; either a `filename` or `file`"):
        partition_email()


def test_partition_email_raises_with_invalid_content_type():
    with pytest.raises(ValueError, match="'application/json' is not a valid value for content_s"):
        partition_email(example_doc_path("eml/fake-email.eml"), content_source="application/json")


# -- .metadata -----------------------------------------------------------------------------------


def test_partition_email_augments_message_body_elements_with_email_metadata():
    elements = partition_email(example_doc_path("eml/mime-multi-to-cc-bcc.eml"))

    assert all(
        e.metadata.bcc_recipient == ["John <john@example.com>", "Mary <mary@example.com>"]
        for e in elements
    )
    assert all(
        e.metadata.cc_recipient == ["Tom <tom@example.com>", "Alice <alice@example.com>"]
        for e in elements
    )
    assert all(e.metadata.email_message_id == "2143658709@example.com" for e in elements)
    assert all(e.metadata.sent_from == ["sender@example.com"] for e in elements)
    assert all(
        e.metadata.sent_to == ["Bob <bob@example.com>", "Sue <sue@example.com>"] for e in elements
    )
    assert all(e.metadata.subject == "Example Plain-Text MIME Message" for e in elements)


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_email_from_filename_gets_filename_metadata_from_file_path():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))

    assert all(e.metadata.filename == "fake-email.eml" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("eml") for e in elements)


def test_partition_email_from_file_gets_filename_metadata_None():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f)

    assert all(e.metadata.filename is None for e in elements)
    assert all(e.metadata.file_directory is None for e in elements)


def test_partition_email_from_filename_prefers_metadata_filename():
    elements = partition_email(
        example_doc_path("eml/fake-email.eml"), metadata_filename="a/b/c.eml"
    )

    assert all(e.metadata.filename == "c.eml" for e in elements)
    assert all(e.metadata.file_directory == "a/b" for e in elements)


def test_partition_email_from_file_prefers_metadata_filename():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f, metadata_filename="d/e/f.eml")

    assert all(e.metadata.filename == "f.eml" for e in elements)
    assert all(e.metadata.file_directory == "d/e" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_email_gets_the_EML_MIME_type_in_metadata_filetype_for_message_body_elements():
    EML_MIME_TYPE = "message/rfc822"
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    assert all(e.metadata.filetype == EML_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{EML_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.languages -------------------------------------------------------------------------


def test_partition_email_element_metadata_has_languages():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    assert all(e.metadata.languages == ["eng"] for e in elements)


def test_partition_email_respects_languages_arg():
    elements = partition_email(example_doc_path("eml/fake-email.eml"), languages=["deu"])
    assert all(element.metadata.languages == ["deu"] for element in elements)


def test_partition_eml_respects_detect_language_per_element():
    elements = partition_email(
        example_doc_path("language-docs/eng_spa_mult.eml"),
        detect_language_per_element=True,
    )
    # languages other than English and Spanish are detected by this partitioner,
    # so this test is slightly different from the other partition tests
    langs = {e.metadata.languages[0] for e in elements if e.metadata.languages is not None}

    assert "eng" in langs
    assert "spa" in langs


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_email_from_file_path_gets_last_modified_from_Date_header():
    elements = partition_email(example_doc_path("eml/fake-email.eml"))
    assert all(e.metadata.last_modified == "2022-12-16T22:04:16+00:00" for e in elements)


def test_partition_email_from_file_gets_last_modified_from_Date_header():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f)

    assert all(e.metadata.last_modified == "2022-12-16T22:04:16+00:00" for e in elements)


def test_partition_email_from_file_path_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    elements = partition_email(
        example_doc_path("eml/fake-email.eml"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_email_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition_email(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# -- chunking ------------------------------------------------------------------------------------


def test_partition_email_chunks_when_so_instructed():
    """Note it's actually the delegate partitioners that do the chunking."""
    elements = partition_email(example_doc_path("eml/fake-email.txt"))
    chunks = partition_email(example_doc_path("eml/fake-email.txt"), chunking_strategy="by_title")
    separately_chunked_chunks = chunk_by_title(elements)

    assert all(isinstance(c, (CompositeElement, Table, TableChunk)) for c in chunks)
    assert chunks != elements
    assert chunks == separately_chunked_chunks


def test_partition_email_chunks_attachments_too():
    chunks = partition_email(
        example_doc_path("eml/fake-email-attachment.eml"),
        chunking_strategy="by_title",
        process_attachments=True,
    )

    assert len(chunks) == 2
    assert all(isinstance(c, CompositeElement) for c in chunks)
    attachment_chunk = chunks[-1]
    assert attachment_chunk.text == "Hey this is a fake attachment!"
    assert attachment_chunk.metadata.filename == "fake-attachment.txt"
    assert attachment_chunk.metadata.attached_to_filename == "fake-email-attachment.eml"
    assert all(c.metadata.last_modified == "2022-12-23T18:08:48+00:00" for c in chunks)


# -- attachments ---------------------------------------------------------------------------------


def test_partition_email_also_partitions_attachments_when_so_instructed():
    elements = partition_email(
        example_doc_path("eml/email-equals-attachment-filename.eml"), process_attachments=True
    )

    assert elements == [
        NarrativeText("Below is an example of an odd filename"),
        Title("Odd filename"),
    ]


def test_partition_email_can_process_attachments():
    elements = partition_email(
        example_doc_path("eml/fake-email-attachment.eml"), process_attachments=True
    )

    assert elements == [
        Title("Hello!"),
        NarrativeText("Here's the attachments!"),
        NarrativeText("It includes:"),
        ListItem("Lots of whitespace"),
        ListItem("Little to no content"),
        ListItem("and is a quick read"),
        Text("Best,"),
        Title("Mallori"),
        NarrativeText("Hey this is a fake attachment!"),
    ]
    assert all(e.metadata.last_modified == "2022-12-23T18:08:48+00:00" for e in elements)
    attachment_element = elements[-1]
    assert attachment_element.text == "Hey this is a fake attachment!"
    assert attachment_element.metadata.filename == "fake-attachment.txt"
    assert attachment_element.metadata.attached_to_filename == "fake-email-attachment.eml"


def test_partition_email_silently_skips_attachments_it_cannot_partition():
    elements = partition_email(
        example_doc_path("eml/mime-attach-mp3.eml"), process_attachments=True
    )

    # -- no exception is raised --
    assert elements == [
        # -- the email body is partitioned --
        NarrativeText("This is an email with an MP3 attachment."),
        # -- no elements appear for the attachment --
    ]


# ================================================================================================
# ISOLATED UNIT TESTS
# ================================================================================================


class DescribeEmailPartitionerOptions:
    """Unit-test suite for `unstructured.partition.email.EmailPartitioningContext` objects."""

    # -- .load() ---------------------------------

    def it_provides_a_validating_constructor(self, ctx_args: dict[str, Any]):
        ctx_args["file_path"] = example_doc_path("eml/fake-email.eml")

        ctx = EmailPartitioningContext.load(**ctx_args)

        assert isinstance(ctx, EmailPartitioningContext)

    def but_it_raises_when_no_source_document_was_specified(self, ctx_args: dict[str, Any]):
        with pytest.raises(ValueError, match="no document specified; either a `filename` or `fi"):
            EmailPartitioningContext.load(**ctx_args)

    def and_it_raises_when_a_file_open_for_reading_str_is_used(self, ctx_args: dict[str, Any]):
        ctx_args["file"] = io.StringIO("abcdefg")
        with pytest.raises(ValueError, match="file object must be opened in binary mode"):
            EmailPartitioningContext.load(**ctx_args)

    def and_it_raises_when_an_invalid_content_source_is_specified(self, ctx_args: dict[str, Any]):
        ctx_args["file_path"] = example_doc_path("eml/fake-email.eml")
        ctx_args["content_source"] = "application/json"

        with pytest.raises(ValueError, match="'application/json' is not a valid value for conte"):
            EmailPartitioningContext.load(**ctx_args)

    # -- .bcc_addresses --------------------------

    def it_provides_access_to_the_Bcc_addresses_when_present(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-multi-to-cc-bcc.eml"))
        assert ctx.bcc_addresses == ["John <john@example.com>", "Mary <mary@example.com>"]

    def but_it_returns_None_when_there_are_no_Bcc_addresses(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/simple-rfc-822.eml"))
        assert ctx.bcc_addresses is None

    # -- .body_part ------------------------------

    def it_returns_the_html_body_part_when_there_is_one_by_default(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-different-plain-html.eml"))

        body_part = ctx.body_part

        assert isinstance(body_part, EmailMessage)
        content = body_part.get_content()
        assert isinstance(content, str)
        assert content.startswith("<!DOCTYPE html>")

    def but_it_returns_the_plain_text_body_part_when_there_is_one_when_so_requested(self):
        ctx = EmailPartitioningContext(
            example_doc_path("eml/mime-different-plain-html.eml"), content_source="text/plain"
        )

        body_part = ctx.body_part

        assert isinstance(body_part, EmailMessage)
        content = body_part.get_content()
        assert isinstance(content, str)
        assert content.startswith("This is the text/plain part.")

    def and_it_returns_None_when_the_email_has_no_body(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-no-body.eml"))
        assert ctx.body_part is None

    # -- .cc_addresses ---------------------------

    def it_provides_access_to_the_Cc_addresses_when_present(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-multi-to-cc-bcc.eml"))
        assert ctx.cc_addresses == ["Tom <tom@example.com>", "Alice <alice@example.com>"]

    def but_it_returns_None_when_there_are_no_Cc_addresses(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/simple-rfc-822.eml"))
        assert ctx.cc_addresses is None

    # -- .content_type_preference ----------------

    @pytest.mark.parametrize(
        ("content_source", "expected_value"),
        [
            ("text/html", ("html", "plain")),
            ("text/plain", ("plain", "html")),
        ],
    )
    def it_knows_whether_the_caller_prefers_the_HTML_or_plain_text_body(
        self, content_source: str, expected_value: tuple[str, ...]
    ):
        ctx = EmailPartitioningContext(content_source=content_source)
        assert ctx.content_type_preference == expected_value

    def and_it_defaults_to_preferring_the_HTML_body(self):
        ctx = EmailPartitioningContext()
        assert ctx.content_type_preference == ("html", "plain")

    # -- .from -----------------------------------

    def it_knows_the_From_address_of_the_email(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-simple.eml"))
        assert ctx.from_address == "sender@example.com"

    # -- .message_id -----------------------------

    def it_provides_access_to_the_Message_ID_when_present(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-simple.eml"))
        assert ctx.message_id == "1234567890@example.com"

    def but_it_returns_None_when_there_is_no_Message_ID_header(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/simple-rfc-822.eml"))
        assert ctx.message_id is None

    # -- .metadata_file_path ---------------------

    def it_uses_the_metadata_file_path_arg_value_when_one_was_provided(self):
        ctx = EmailPartitioningContext(metadata_file_path="a/b/c.eml")
        assert ctx.metadata_file_path == "a/b/c.eml"

    def and_it_uses_the_file_path_arg_value_when_metadata_file_path_was_not_provided(self):
        ctx = EmailPartitioningContext(file_path="x/y/z.eml")
        assert ctx.metadata_file_path == "x/y/z.eml"

    def and_it_returns_None_when_neither_file_path_was_provided(self):
        ctx = EmailPartitioningContext()
        assert ctx.metadata_file_path is None

    # -- .metadata_last_modified -----------------

    def it_uses_the_metadata_last_modified_arg_value_when_one_was_provided(self):
        metadata_last_modified = "2023-04-08T12:18:07"
        ctx = EmailPartitioningContext(metadata_last_modified=metadata_last_modified)
        assert ctx.metadata_last_modified == metadata_last_modified

    def and_it_uses_the_msg_Date_header_date_when_metadata_last_modified_was_not_provided(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/simple-rfc-822.eml"))
        assert ctx.metadata_last_modified == "2024-10-01T17:34:56+00:00"

    def and_it_falls_back_to_filesystem_last_modified_when_no_Date_header_is_present(
        self, get_last_modified_date_: Mock
    ):
        """Not an expected case as according to RFC 5322, the Date header is required."""
        filesystem_last_modified = "2024-07-09T14:08:17"
        get_last_modified_date_.return_value = filesystem_last_modified

        ctx = EmailPartitioningContext(example_doc_path("eml/rfc822-no-date.eml"))

        assert ctx.metadata_last_modified == filesystem_last_modified

    def and_it_returns_None_when_no_last_modified_is_available(self):
        with open(example_doc_path("eml/rfc822-no-date.eml"), "rb") as f:
            ctx = EmailPartitioningContext(file=f)
            assert ctx.metadata_last_modified is None

    # -- .msg ------------------------------------

    def it_loads_the_email_message_from_the_filesystem_when_a_path_is_provided(self):
        ctx = EmailPartitioningContext(file_path=example_doc_path("eml/simple-rfc-822.eml"))
        assert isinstance(ctx.msg, EmailMessage)

    def and_it_loads_the_email_message_from_a_file_like_object_when_one_is_provided(self):
        with open(example_doc_path("eml/simple-rfc-822.eml"), "rb") as f:
            ctx = EmailPartitioningContext(file=f)
            assert isinstance(ctx.msg, EmailMessage)

    # -- .partitioning_kwargs --------------------

    def it_passes_along_the_kwargs_it_received_on_construction(self):
        kwargs = {"foo": "bar", "baz": "qux"}
        ctx = EmailPartitioningContext(kwargs=kwargs)

        assert ctx.partitioning_kwargs == kwargs

    # -- .process_attachments --------------------

    @pytest.mark.parametrize("process_attachments", [True, False])
    def it_knows_whether_the_caller_wants_to_also_partition_attachments(
        self, process_attachments: bool
    ):
        ctx = EmailPartitioningContext(process_attachments=process_attachments)
        assert ctx.process_attachments == process_attachments

    def but_by_default_it_ignores_attachments(self):
        ctx = EmailPartitioningContext()
        assert ctx.process_attachments is False

    # -- .subject --------------------------------

    def it_provides_access_to_the_email_Subject_as_a_string(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-word-encoded-subject.eml"))
        assert ctx.subject == "Simple email with ☸☿ Unicode subject"

    def but_it_returns_None_when_there_is_no_Subject_header(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-no-subject.eml"))
        assert ctx.subject is None

    # -- .to_addresses ---------------------------

    def it_provides_access_to_the_To_addresses_when_present(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-multi-to-cc-bcc.eml"))
        assert ctx.to_addresses == ["Bob <bob@example.com>", "Sue <sue@example.com>"]

    def but_it_returns_None_when_there_are_no_To_addresses(self):
        ctx = EmailPartitioningContext(example_doc_path("eml/mime-no-to.eml"))
        assert ctx.to_addresses is None

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def ctx_args(self) -> dict[str, Any]:
        return {
            "file_path": None,
            "file": None,
            "content_source": "text/html",
            "metadata_file_path": None,
            "metadata_last_modified": None,
            "process_attachments": False,
            "kwargs": {},
        }

    @pytest.fixture()
    def get_last_modified_date_(self, request: FixtureRequest) -> Mock:
        return function_mock(request, "unstructured.partition.email.get_last_modified_date")
