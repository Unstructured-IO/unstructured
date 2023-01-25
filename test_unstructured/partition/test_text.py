import os
import pathlib
import pytest

from unstructured.documents.elements import Address, NarrativeText, Title, ListItem
from unstructured.partition.text import partition_text

DIRECTORY = pathlib.Path(__file__).parent.resolve()

EXPECTED_OUTPUT = [
    NarrativeText(text="This is a test document to use for unit tests."),
    Address(text="Doylestown, PA 18901"),
    Title(text="Important points:"),
    ListItem(text="Hamburgers are delicious"),
    ListItem(text="Dogs are the best"),
    ListItem(text="I love fuzzy blankets"),
]


def test_partition_text_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    elements = partition_text(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        text = f.read()
    elements = partition_text(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_text()


def test_partition_text_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "r") as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_text(filename=filename, text=text)
