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
    assert elements[0].metadata == ElementMetadata(
        filename=filename,
        date="2022-12-16T17:04:16-05:00",
        page_number=None,
        url=None,
        sent_from=["Matthew Robinson <mrobinson@unstructured.io>"],
        sent_to=["Matthew Robinson (None)"],
        subject="Test Email",
    )


class MockMsOxMessage:
    def __init__(self, filename):
        self.body = "Here is an email with plain text."


def test_partition_msg_from_filename_with_text_content(monkeypatch):
    monkeypatch.setattr(msg_parser, "MsOxMessage", MockMsOxMessage)
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename)
    assert str(elements[0]) == "Here is an email with plain text."


def test_partition_msg_raises_with_missing_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "doesnt-exist.msg")
    with pytest.raises(FileNotFoundError):
        partition_msg(filename=filename)


def test_partition_msg_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f)
    assert elements == EXPECTED_MSG_OUTPUT


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
