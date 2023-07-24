import os
import pathlib

from unstructured.documents.elements import Title
from unstructured.partition.odt import partition_odt

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")


def test_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename)
    assert elements == [Title("Lorem ipsum dolor sit amet.")]
    for element in elements:
        assert element.metadata.filename == "fake.odt"


def test_partition_odt_from_filename_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f)

    assert elements == [Title("Lorem ipsum dolor sit amet.")]


def test_partition_odt_from_file_with_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f, metadata_filename="test")

    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_odt_from_filename_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition_odt(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_odt_from_file_exclude_metadata():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition_odt(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_odt_with_include_path_in_metadata_filename(
    filename="example-docs/fake.odt",
):
    elements = partition_odt(filename=filename, include_path_in_metadata_filename=True)

    assert elements[0].metadata.filename == filename
    assert elements[0].metadata.file_directory is None


def test_partition_odt_with_include_path_in_metadata_filename_and_metadata_filename(
    filename="example-docs/fake.odt",
):
    elements = partition_odt(
        filename=filename,
        include_path_in_metadata_filename=True,
        metadata_filename="TEST",
    )

    assert elements[0].metadata.filename == "example-docs/TEST"
    assert elements[0].metadata.file_directory is None
