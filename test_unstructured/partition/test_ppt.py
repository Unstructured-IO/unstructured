import os
import pathlib

import pytest

from unstructured.documents.elements import ListItem, NarrativeText, Title
from unstructured.partition.ppt import partition_ppt

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

EXPECTED_PPT_OUTPUT = [
    Title(text="Adding a Bullet Slide"),
    ListItem(text="Find the bullet slide layout"),
    ListItem(text="Use _TextFrame.text for first bullet"),
    ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
    NarrativeText(text="Here is a lot of text!"),
    NarrativeText(text="Here is some text in a text box!"),
]


def test_partition_ppt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition_ppt(filename=filename)
    assert elements == EXPECTED_PPT_OUTPUT


def test_partition_ppt_raises_with_missing_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "doesnt-exist.ppt")
    with pytest.raises(ValueError):
        partition_ppt(filename=filename)


def test_partition_ppt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f:
        elements = partition_ppt(file=f)
    assert elements == EXPECTED_PPT_OUTPUT


def test_partition_ppt_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_ppt(filename=filename, file=f)


def test_partition_ppt_raises_with_neither():
    with pytest.raises(ValueError):
        partition_ppt()
