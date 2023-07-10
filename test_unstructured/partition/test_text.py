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
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_text(filename=filename_path, encoding=encoding)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == filename


def test_partition_text_from_filename_with_metadata_filename():
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    elements = partition_text(filename=filename_path, encoding="utf-8", metadata_filename="test")
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_filename_default_encoding(filename):
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_text(filename=filename_path)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == filename


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
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        elements = partition_text(file=f, metadata_filename="test")
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename == "test"


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_file_default_encoding(filename):
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(filename_path) as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_bytes_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


@pytest.mark.parametrize(
    "filename",
    ["fake-text-utf-16.txt", "fake-text-utf-16-le.txt", "fake-text-utf-32.txt"],
)
def test_partition_text_from_bytes_file_default_encoding(filename):
    filename_path = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    with open(filename_path, "rb") as f:
        elements = partition_text(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_from_text():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        text = f.read()
    elements = partition_text(text=text)
    assert len(elements) > 0
    assert elements == EXPECTED_OUTPUT
    for element in elements:
        assert element.metadata.filename is None


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
    for element in elements:
        assert element.metadata.filename is None


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
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_extract_regex_metadata():
    text = "SPEAKER 1: It is my turn to speak now!"

    elements = partition_text(text=text, regex_metadata={"speaker": r"SPEAKER \d{1,3}"})
    assert elements[0].metadata.regex_metadata == {
        "speaker": [{"text": "SPEAKER 1", "start": 0, "end": 9}],
    }
    for element in elements:
        assert element.metadata.filename is None


def test_partition_text_splits_long_text(filename="example-docs/norwich-city.txt"):
    elements = partition_text(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("Iwan Roberts")
    assert elements[-1].text.endswith("External links")


def test_partition_text_doesnt_get_page_breaks():
    text = "--------------------"
    elements = partition_text(text=text)
    assert len(elements) == 1
    assert elements[0].text == text
    assert not isinstance(elements[0], ListItem)


@pytest.mark.parametrize(
    ("filename", "encoding"),
    [("fake-text.txt", "utf-8"), ("fake-text.txt", None), ("fake-text-utf-16-be.txt", "utf-16-be")],
)
def test_partition_text_from_filename_exclude_metadata(filename, encoding):
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", filename)
    elements = partition_text(filename=filename, encoding=encoding, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_text_from_file_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-text.txt")
    with open(filename) as f:
        elements = partition_text(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}
