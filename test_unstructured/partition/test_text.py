import os
import pathlib

import pytest

from unstructured.cleaners.core import group_broken_paragraphs
from unstructured.documents.elements import Address, ListItem, NarrativeText, Title
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


@pytest.mark.parametrize(
    ("filename", "encoding"),
    [("fake-text.txt", "utf-8"), ("fake-text.txt", None), ("fake-text-utf-16-be.txt", "utf-16-be")],
)
def test_partition_text_from_filename(filename, encoding):
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_text(filename=filename, encoding=encoding)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


@pytest.mark.parametrize(
    ("filename", "encoding", "error"),
    [
        ("fake-text.txt", "utf-16", UnicodeDecodeError),
        ("fake-text-utf-16-be.txt", "utf-16", UnicodeError),
    ],
)
def test_partition_text_from_filename_raises_econding_error(filename, encoding, error):
    with pytest.raises(error):
        filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
        partition_text(filename=filename, encoding=encoding)


def test_partition_text_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_from_bytes_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        text = f.read()
    elements = partition_text(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT


def test_partition_text_from_text_works_with_empty_string():
    assert partition_text(text="") == []


def test_partition_text_raises_with_none_specified():
    with pytest.raises(ValueError):
        partition_text()


def test_partition_text_raises_with_too_many_specified():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        text = f.read()

    with pytest.raises(ValueError):
        partition_text(filename=filename, text=text)


def test_partition_text_captures_everything_even_with_linebreaks():
    text = """
    VERY IMPORTANT MEMO
    DOYLESTOWN, PA 18901
    """
    elements = partition_text(text=text)
    assert elements == [
        Title(text="VERY IMPORTANT MEMO"),
        Address(text="DOYLESTOWN, PA 18901"),
    ]


def test_partition_text_groups_broken_paragraphs():
    text = """The big brown fox
was walking down the lane.

At the end of the lane,
the fox met a bear."""

    elements = partition_text(text=text, paragraph_grouper=group_broken_paragraphs)
    assert elements == [
        NarrativeText(text="The big brown fox was walking down the lane."),
        NarrativeText(text="At the end of the lane, the fox met a bear."),
    ]
