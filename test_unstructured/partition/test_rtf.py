import os
import pathlib

from unstructured.documents.elements import Title
from unstructured.partition.rtf import partition_rtf

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_rtf_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")


def test_partition_rtf_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")


def test_partition_rtf_from_filename_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert any(elements[i].metadata.to_dict()) == {}


def test_partition_rtf_from_file_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert any(elements[i].metadata.to_dict()) == {}
