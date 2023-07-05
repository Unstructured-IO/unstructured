import os
import pathlib

import msg_parser
import pytest

from unstructured.documents.elements import (
    ElementMetadata,
    ListItem,
    NarrativeText,
    Title,
)
from unstructured.partition.msg import extract_msg_attachment_info, partition_msg
from unstructured.partition.text import partition_text

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

EXPECTED_MSG_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

ATTACH_EXPECTED_OUTPUT = [
    {
        "filename": "fake-attachment.txt",
        "extension": ".txt",
        "file_size": "unknown",
        "payload": b"Hey this is a fake attachment!",
    },
]


def test_partition_msg_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename)
    assert elements == EXPECTED_MSG_OUTPUT
    assert (
        elements[0].metadata.to_dict()
        == ElementMetadata(
            coordinates=None,
            filename=filename,
            date="2022-12-16T17:04:16-05:00",
            page_number=None,
            url=None,
            sent_from=["Matthew Robinson <mrobinson@unstructured.io>"],
            sent_to=["Matthew Robinson (None)"],
            subject="Test Email",
            filetype="application/vnd.ms-outlook",
        ).to_dict()
    )
    for element in elements:
        assert element.metadata.filename == "fake-email.msg"


def test_partition_msg_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


class MockMsOxMessage:
    def __init__(self, filename):
        self.body = "Here is an email with plain text."


def test_partition_msg_from_filename_with_text_content(monkeypatch):
    monkeypatch.setattr(msg_parser, "MsOxMessage", MockMsOxMessage)
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename)
    assert str(elements[0]) == "Here is an email with plain text."
    assert elements[0].metadata.filename == "fake-email.msg"
    assert elements[0].metadata.file_directory == EXAMPLE_DOCS_DIRECTORY


def test_partition_msg_raises_with_missing_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "doesnt-exist.msg")
    with pytest.raises(FileNotFoundError):
        partition_msg(filename=filename)


def test_partition_msg_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f)
    assert elements == EXPECTED_MSG_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_msg_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f, metadata_filename="test")
    assert elements == EXPECTED_MSG_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


def test_extract_attachment_info():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-email-attachment.msg")
    attachment_info = extract_msg_attachment_info(filename)
    assert len(attachment_info) > 0
    assert attachment_info == ATTACH_EXPECTED_OUTPUT


def test_partition_msg_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_msg(filename=filename, file=f)


def test_partition_msg_raises_with_neither():
    with pytest.raises(ValueError):
        partition_msg()


def test_partition_msg_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_msg_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_msg_can_process_attachments(
    tmpdir,
    filename="example-docs/fake-email-attachment.msg",
):
    extract_msg_attachment_info(filename=filename, output_dir=tmpdir.dirname)
    attachment_filename = os.path.join(tmpdir.dirname, ATTACH_EXPECTED_OUTPUT[0]["filename"])
    attachment_elements = partition_text(
        filename=attachment_filename,
        metadata_filename=attachment_filename,
    )
    expected_metadata = attachment_elements[0].metadata
    expected_metadata.file_directory = None
    expected_metadata.attached_to_filename = filename

    elements = partition_msg(
        filename=filename,
        attachment_partitioner=partition_text,
        process_attachments=True,
    )

    assert elements[0].text.startswith("Hello!")

    for element in elements[:-1]:
        assert element.metadata.filename == "fake-email-attachment.msg"
        assert element.metadata.subject == "Fake email with attachment"

    assert elements[-1].text == "Hey this is a fake attachment!"
    assert elements[-1].metadata == expected_metadata


def test_partition_msg_raises_with_no_partitioner(
    filename="example-docs/fake-email-attachment.msg",
):
    with pytest.raises(ValueError):
        partition_msg(filename=filename, process_attachments=True)
