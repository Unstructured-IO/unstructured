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
    for element in elements:
        assert element.metadata.filename == "fake-doc.rtf"


def test_partition_rtf_from_filename_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_rtf_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename is None


def test_partition_rtf_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, metadata_filename="test")
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_rtf_from_filename_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    elements = partition_rtf(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rtf_from_file_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}
