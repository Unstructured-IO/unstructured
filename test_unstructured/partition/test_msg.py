"""Test suite for `unstructured.partition.msg` module."""

from __future__ import annotations

import io
from typing import Any

import pytest
from oxmsg import Message

from test_unstructured.unit_utils import (
    FixtureRequest,
    LogCaptureFixture,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
    property_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    ElementMetadata,
    ListItem,
    NarrativeText,
    Text,
)
from unstructured.partition.common import UnsupportedFileFormatError
from unstructured.partition.msg import MsgPartitionerOptions, partition_msg

EXPECTED_MSG_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Text(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_partition_msg_from_filename():
    filename = example_doc_path("fake-email.msg")
    elements = partition_msg(filename=filename)
    parent_id = elements[0].metadata.parent_id

    assert elements == EXPECTED_MSG_OUTPUT
    assert (
        elements[0].metadata.to_dict()
        == ElementMetadata(
            coordinates=None,
            filename=filename,
            last_modified="2023-03-28T17:00:31+00:00",
            page_number=None,
            url=None,
            sent_from=['"Matthew Robinson" <mrobinson@unstructured.io>'],
            sent_to=["mrobinson@unstructured.io"],
            subject="Test Email",
            filetype="application/vnd.ms-outlook",
            parent_id=parent_id,
            languages=["eng"],
        ).to_dict()
    )


def test_partition_msg_from_filename_returns_uns_elements():
    filename = example_doc_path("fake-email.msg")
    elements = partition_msg(filename=filename)
    assert isinstance(elements[0], NarrativeText)


def test_partition_msg_from_filename_with_metadata_filename():
    filename = example_doc_path("fake-email.msg")
    elements = partition_msg(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_msg_from_filename_with_text_content():
    filename = example_doc_path("fake-email.msg")

    elements = partition_msg(filename=filename)

    assert str(elements[0]) == "This is a test email to use for unit tests."
    assert elements[0].metadata.filename == "fake-email.msg"
    assert elements[0].metadata.file_directory == example_doc_path("")


def test_partition_msg_raises_with_missing_file():
    filename = example_doc_path("doesnt-exist.msg")
    with pytest.raises(FileNotFoundError):
        partition_msg(filename=filename)


def test_partition_msg_from_file():
    filename = example_doc_path("fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f)
    assert elements == EXPECTED_MSG_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_msg_from_file_with_metadata_filename():
    filename = example_doc_path("fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f, metadata_filename="test")
    assert elements == EXPECTED_MSG_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_msg_uses_file_path_when_both_are_specified():
    elements = partition_msg(example_doc_path("fake-email.msg"), file=io.BytesIO(b"abcde"))
    assert elements == EXPECTED_MSG_OUTPUT


def test_partition_msg_raises_with_neither():
    with pytest.raises(ValueError):
        partition_msg()


# -- attachments ---------------------------------------------------------------------------------


def test_partition_msg_can_process_attachments():
    elements = partition_msg(
        example_doc_path("fake-email-multiple-attachments.msg"), process_attachments=True
    )

    assert all(e.metadata.filename == "fake-email-multiple-attachments.msg" for e in elements[:5])
    assert all(e.metadata.filename == "unstructured_logo.png" for e in elements[5:7])
    assert all(e.metadata.filename == "dense_doc.pdf" for e in elements[7:343])
    assert all(e.metadata.filename == "Engineering Onboarding.pptx" for e in elements[343:])
    assert [e.text for e in elements[:5]] == [
        "Here are those documents.",
        "--",
        "Mallori Harrell",
        "Unstructured Technologies",
        "Data Scientist",
    ]
    assert [type(e).__name__ for e in elements][:10] == [
        "NarrativeText",
        "Text",
        "Text",
        "Text",
        "Text",
        "Image",
        "Text",
        "Text",
        "Title",
        "Title",
    ]
    assert [type(e).__name__ for e in elements][-10:] == [
        "Title",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
        "ListItem",
    ]


def test_partition_msg_silently_skips_attachments_it_cannot_partition(request: FixtureRequest):
    function_mock(
        request, "unstructured.partition.auto.partition", side_effect=UnsupportedFileFormatError()
    )

    elements = partition_msg(
        example_doc_path("fake-email-multiple-attachments.msg"), process_attachments=True
    )

    # -- no exception is raised --
    assert elements == [
        # -- the email body is partitioned --
        NarrativeText("Here are those documents."),
        Text("--"),
        Text("Mallori Harrell"),
        Text("Unstructured Technologies"),
        Text("Data Scientist"),
        # -- no elements appear for the attachment(s) --
    ]


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_msg_from_filename_gets_filename_metadata_from_file_path():
    elements = partition_msg(example_doc_path("fake-email.msg"))

    assert all(e.metadata.filename == "fake-email.msg" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


def test_partition_msg_from_file_gets_filename_metadata_None():
    with open(example_doc_path("fake-email.msg"), "rb") as f:
        elements = partition_msg(file=f)

    assert all(e.metadata.filename is None for e in elements)
    assert all(e.metadata.file_directory is None for e in elements)


def test_partition_msg_from_filename_prefers_metadata_filename():
    elements = partition_msg(example_doc_path("fake-email.msg"), metadata_filename="a/b/c.msg")

    assert all(e.metadata.filename == "c.msg" for e in elements)
    assert all(e.metadata.file_directory == "a/b" for e in elements)


def test_partition_msg_from_file_prefers_metadata_filename():
    with open(example_doc_path("fake-email.msg"), "rb") as f:
        elements = partition_msg(file=f, metadata_filename="d/e/f.msg")

    assert all(e.metadata.filename == "f.msg" for e in elements)
    assert all(e.metadata.file_directory == "d/e" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_msg_gets_the_MSG_mime_type_in_metadata_filetype():
    MSG_MIME_TYPE = "application/vnd.ms-outlook"
    elements = partition_msg(example_doc_path("fake-email.msg"))
    assert all(e.metadata.filetype == MSG_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{MSG_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_msg_pulls_last_modified_from_message_sent_date():
    elements = partition_msg(example_doc_path("fake-email.msg"))
    assert all(e.metadata.last_modified == "2023-03-28T17:00:31+00:00" for e in elements)


def test_partition_msg_from_file_path_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    elements = partition_msg(
        example_doc_path("fake-email.msg"), metadata_last_modified=metadata_last_modified
    )

    assert elements[0].metadata.last_modified == metadata_last_modified


def test_partition_msg_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("fake-email.msg"), "rb") as f:
        elements = partition_msg(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_msg_with_json():
    elements = partition_msg(example_doc_path("fake-email.msg"))
    assert_round_trips_through_JSON(elements)


def test_partition_msg_with_pgp_encrypted_message(caplog: LogCaptureFixture):
    elements = partition_msg(example_doc_path("fake-encrypted.msg"))

    assert elements == []
    assert "WARNING" in caplog.text
    assert "Encrypted email detected" in caplog.text


def test_add_chunking_strategy_by_title_on_partition_msg():
    filename = example_doc_path("fake-email.msg")

    elements = partition_msg(filename=filename)
    chunk_elements = partition_msg(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


# -- language behaviors --------------------------------------------------------------------------


def test_partition_msg_element_metadata_has_languages():
    filename = "example-docs/fake-email.msg"
    elements = partition_msg(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_msg_respects_languages_arg():
    filename = "example-docs/fake-email.msg"
    elements = partition_msg(filename=filename, languages=["deu"])
    assert all(element.metadata.languages == ["deu"] for element in elements)


def test_partition_msg_raises_TypeError_for_invalid_languages():
    with pytest.raises(TypeError):
        filename = "example-docs/fake-email.msg"
        partition_msg(filename=filename, languages="eng")


# ================================================================================================
# ISOLATED UNIT TESTS
# ================================================================================================
# These test components used by `partition_msg()` in isolation such that all edge cases can be
# exercised.
# ================================================================================================


class DescribeMsgPartitionerOptions:
    """Unit-test suite for `unstructured.partition.msg.MsgPartitionerOptions` objects."""

    # -- .extra_msg_metadata ---------------------

    def it_provides_email_specific_metadata_to_add_to_each_element(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = example_doc_path("fake-email-with-cc-and-bcc.msg")
        opts = MsgPartitionerOptions(**opts_args)

        m = opts.extra_msg_metadata
        assert m.bcc_recipient == ["hello@unstructured.io"]
        assert m.cc_recipient == ["steve@unstructured.io"]
        assert m.email_message_id == "14DDEF33-2BA7-4CDD-A4D8-E7C5873B37F2@gmail.com"
        assert m.sent_from == ['"John" <johnjennings702@gmail.com>']
        assert m.sent_to == [
            "john-ctr@unstructured.io",
            "steve@unstructured.io",
            "hello@unstructured.io",
        ]
        assert m.subject == "Fake email with cc and bcc recipients"

    # -- .is_encrypted ---------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"), [("fake-encrypted.msg", True), ("fake-email.msg", False)]
    )
    def it_knows_when_the_msg_is_encrypted(
        self, file_name: str, expected_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path(file_name)
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.is_encrypted is expected_value

    # -- .metadata_file_path ---------------------

    def it_uses_the_metadata_file_path_arg_when_provided(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = "x/y/z.msg"
        opts_args["metadata_file_path"] = "a/b/c.msg"
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == "a/b/c.msg"

    def and_it_falls_back_to_the_MSG_file_path_arg_when_provided(self, opts_args: dict[str, Any]):
        file_path = example_doc_path("fake-email.msg")
        opts_args["file_path"] = file_path
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == file_path

    def but_it_returns_None_when_neither_path_is_available(self, opts_args: dict[str, Any]):
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_file_path is None

    # -- .metadata_last_modified -----------------

    def it_uses_metadata_last_modified_when_provided_by_the_caller(self, opts_args: dict[str, Any]):
        metadata_last_modified = "2024-03-05T17:02:53"
        opts_args["metadata_last_modified"] = metadata_last_modified
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_last_modified == metadata_last_modified

    def and_it_uses_the_message_Date_header_when_metadata_last_modified_is_not_provided(
        self, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_last_modified == "2023-03-28T17:00:31+00:00"

    @pytest.mark.parametrize("filesystem_last_modified", ["2024-06-03T20:12:53", None])
    def and_it_uses_the_last_modified_date_from_the_source_file_when_the_message_has_no_sent_date(
        self,
        opts_args: dict[str, Any],
        filesystem_last_modified: str | None,
        Message_sent_date_: Mock,
        _last_modified_prop_: Mock,
    ):
        Message_sent_date_.return_value = None
        _last_modified_prop_.return_value = filesystem_last_modified
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_last_modified == filesystem_last_modified

    # -- .msg ------------------------------------

    def it_loads_the_msg_document_from_a_file_path_when_provided(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert isinstance(opts.msg, Message)

    def and_it_loads_the_msg_document_from_a_file_like_object_when_provided(
        self, opts_args: dict[str, Any]
    ):
        with open(example_doc_path("fake-email.msg"), "rb") as f:
            opts_args["file"] = io.BytesIO(f.read())
        opts = MsgPartitionerOptions(**opts_args)

        assert isinstance(opts.msg, Message)

    def but_it_raises_when_neither_is_provided(self, opts_args: dict[str, Any]):
        with pytest.raises(ValueError, match="one of `file` or `filename` arguments must be prov"):
            MsgPartitionerOptions(**opts_args).msg

    # -- .partition_attachments ------------------

    @pytest.mark.parametrize("partition_attachments", [True, False])
    def it_knows_whether_attachments_should_also_be_partitioned(
        self, partition_attachments: bool, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts_args["partition_attachments"] = partition_attachments
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.partition_attachments is partition_attachments

    # -- .partitioning_kwargs --------------------

    def it_provides_access_to_pass_through_kwargs_collected_by_the_partitioner_function(
        self, opts_args: dict[str, Any]
    ):
        opts_args["kwargs"] = {"foo": 42, "bar": "baz"}
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.partitioning_kwargs == {"foo": 42, "bar": "baz"}

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture
    def _last_modified_prop_(self, request: FixtureRequest):
        return property_mock(request, MsgPartitionerOptions, "_last_modified")

    @pytest.fixture
    def Message_sent_date_(self, request: FixtureRequest):
        return property_mock(request, Message, "sent_date")

    @pytest.fixture
    def opts_args(self) -> dict[str, Any]:
        """All default arguments for `MsgPartitionerOptions`.

        Individual argument values can be changed to suit each test. Makes construction of opts more
        compact for testing purposes.
        """
        return {
            "file": None,
            "file_path": None,
            "metadata_file_path": None,
            "metadata_last_modified": None,
            "partition_attachments": False,
            "kwargs": {},
        }
