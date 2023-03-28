import os
import pathlib

import pytest

from unstructured.documents.elements import ListItem, NarrativeText, Title
from unstructured.partition.msg import partition_msg

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

EXPECTED_MSG_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_partition_msg_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition_msg(filename=filename)
    assert elements == EXPECTED_MSG_OUTPUT


def test_partition_msg_raises_with_missing_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "doesnt-exist.msg")
    with pytest.raises(FileNotFoundError):
        partition_msg(filename=filename)


def test_partition_msg_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f:
        elements = partition_msg(file=f)
    assert elements == EXPECTED_MSG_OUTPUT


def test_partition_msg_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_msg(filename=filename, file=f)


def test_partition_msg_raises_with_neither():
    with pytest.raises(ValueError):
        partition_msg()
