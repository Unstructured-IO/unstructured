import os
import pathlib

from unstructured.documents.html import HTMLTitle
from unstructured.partition.epub import partition_epub

DIRECTORY = pathlib.Path(__file__).parent.resolve()


def test_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
    for element in elements:
        assert element.metadata.filename == "winter-sports.epub"


def test_partition_epub_from_filename_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition_epub(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
    for element in elements:
        assert element.metadata.filename is None


def test_partition_epub_from_file_with_metadata_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f, metadata_filename="test")
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_epub_from_filename_exclude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition_epub(filename=filename, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_epub_from_file_exlcude_metadata():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_epub_with_include_element_types(
    filename="example-docs/winter-sports.epub",
):
    element_types = [HTMLTitle]
    elements = partition_epub(
        filename=filename,
        include_metadata=False,
        include_element_types=element_types,
    )

    for element in elements:
        assert type(element) in element_types


def test_partition_epub_with_exclude_element_types(
    filename="example-docs/winter-sports.epub",
):
    element_types = [HTMLTitle]
    elements = partition_epub(
        filename=filename,
        include_metadata=False,
        exclude_element_types=element_types,
    )

    for element in elements:
        assert type(element) not in element_types


def test_partition_epub_from_file_with_include_element_types(
    filename="example-docs/winter-sports.epub",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_epub(
            file=f,
            include_metadata=False,
            include_element_types=element_types,
        )

    for element in elements:
        assert type(element) in element_types


def test_partition_epub_from_file_with_exclude_element_types(
    filename="example-docs/winter-sports.epub",
):
    element_types = [HTMLTitle]
    with open(filename, "rb") as f:
        elements = partition_epub(
            file=f,
            include_metadata=False,
            exclude_element_types=element_types,
        )

    for element in elements:
        assert type(element) not in element_types
