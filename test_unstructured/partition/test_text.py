import os
import pathlib
import pytest

from unstructured.documents.elements import NarrativeText, Title, ListItem
from unstructured.partition.text import partition_text

DIRECTORY = pathlib.Path(__file__).parent.resolve()

EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

def test_partition_email_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    elements = partition_text(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        text = f.read()
    elements = partition_text(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT

def test_partition_email_from_list():
    content = ["This is a test email to use for unit tests.", 
            "Important points:",
            "   - Roses are red",
            "   - Violets are blue"]
    elements = partition_text(file_content=content)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_email_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_text()


def test_partition_email_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_text(filename=filename, text=text)