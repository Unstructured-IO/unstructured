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
    property_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    ElementMetadata,
    ListItem,
    NarrativeText,
    Title,
)
from unstructured.partition.msg import MsgPartitionerOptions, partition_msg

EXPECTED_MSG_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
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
    assert all(e.metadata.filename == "fake-email.msg" for e in elements)


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


def test_partition_msg_from_filename_exclude_metadata():
    filename = example_doc_path("fake-email.msg")
    elements = partition_msg(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_msg_from_file_exclude_metadata():
    filename = example_doc_path("fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


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
        "Title",
        "Title",
        "Title",
        "Image",
        "Title",
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


def test_partition_msg_pulls_last_modified_from_message_sent_date():
    elements = partition_msg(example_doc_path("fake-email.msg"))
    assert all(e.metadata.last_modified == "2023-03-28T17:00:31+00:00" for e in elements)


def test_partition_msg_from_file_prefers_metadata_last_modified_when_provided():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("fake-email.msg"), "rb") as f:
        elements = partition_msg(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_msg_custom_metadata_date():
    expected_last_modification_date = "2020-07-05T09:24:28"

    elements = partition_msg(
        example_doc_path("fake-email.msg"), metadata_last_modified=expected_last_modification_date
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


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

    def it_uses_the_user_provided_metadata_file_path_when_provided(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = "x/y/z.msg"
        opts_args["metadata_file_path"] = "a/b/c.msg"
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == "a/b/c.msg"

    @pytest.mark.parametrize("file_path", ["u/v/w.msg", None])
    def and_it_falls_back_to_the_document_file_path_otherwise_including_when_the_file_path_is_None(
        self, file_path: str | None, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = file_path
        opts_args["metadata_file_path"] = None
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == file_path

    # -- .metadata_last_modified -----------------

    @pytest.mark.parametrize("metadata_last_modified", ["2024-03-05T17:02:53", None])
    def it_knows_the_metadata_last_modified_date_provided_by_the_caller(
        self, metadata_last_modified: str | None, opts_args: dict[str, Any]
    ):
        opts_args["metadata_last_modified"] = metadata_last_modified
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.metadata_last_modified == metadata_last_modified

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

    # -- .msg_metadata ---------------------------

    def it_provides_a_unique_metadata_instance_for_each_element(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata is not opts.msg_metadata

    # -- .metadata.filename ----------------------

    def it_uses_the_metadata_file_path_value_for_msg_metadata(
        self, opts_args: dict[str, Any], metadata_file_path_prop_: Mock
    ):
        metadata_file_path_prop_.return_value = "a/b/c.msg"
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata.filename == "c.msg"
        assert opts.msg_metadata.file_directory == "a/b"

    # -- .metadata.last_modified -----------------

    def it_uses_metadata_last_modified_when_provided_by_caller(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts_args["metadata_last_modified"] = "2024-06-03T20:07:31+00:00"
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata.last_modified == "2024-06-03T20:07:31+00:00"

    def and_it_uses_the_sent_date_of_the_email_when_metadata_last_modified_is_not_provided(
        self, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata.last_modified == "2023-03-28T17:00:31+00:00"

    @pytest.mark.parametrize("file_last_modified", ["2024-06-03T20:12:53", None])
    def and_it_uses_the_last_modified_date_from_the_source_file_when_the_message_has_no_sent_date(
        self,
        opts_args: dict[str, Any],
        file_last_modified: str | None,
        Message_sent_date_: Mock,
        _last_modified_prop_: Mock,
    ):
        Message_sent_date_.return_value = None
        _last_modified_prop_.return_value = file_last_modified
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata.last_modified == file_last_modified

    # -- .metadata (email-specific) --------------

    def it_adds_email_specific_fields_to_the_msg_element_metadata(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.msg_metadata.sent_from == ['"Matthew Robinson" <mrobinson@unstructured.io>']
        assert opts.msg_metadata.sent_to == ["mrobinson@unstructured.io"]
        assert opts.msg_metadata.subject == "Test Email"

    # -- .partition_attachments ------------------

    @pytest.mark.parametrize("partition_attachments", [True, False])
    def it_knows_whether_attachments_should_also_be_partitioned(
        self, partition_attachments: bool, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path("fake-email.msg")
        opts_args["partition_attachments"] = partition_attachments
        opts = MsgPartitionerOptions(**opts_args)

        assert opts.partition_attachments is partition_attachments

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture
    def _last_modified_prop_(self, request: FixtureRequest):
        return property_mock(request, MsgPartitionerOptions, "_last_modified")

    @pytest.fixture
    def Message_sent_date_(self, request: FixtureRequest):
        return property_mock(request, Message, "sent_date")

    @pytest.fixture
    def metadata_file_path_prop_(self, request: FixtureRequest):
        return property_mock(request, MsgPartitionerOptions, "metadata_file_path")

    @pytest.fixture
    def opts_args(self) -> dict[str, Any]:
        """All default arguments for `MsgPartitionerOptions`.

        Individual argument values can be changed to suit each test. Makes construction of opts more
        compact for testing purposes.
        """
        return {
            "date_from_file_object": False,
            "file": None,
            "file_path": None,
            "metadata_file_path": None,
            "metadata_last_modified": None,
            "partition_attachments": False,
        }
