from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.rst import partition_rst


def test_partition_rst_from_filename(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"
    for element in elements:
        assert element.metadata.filename == "README.rst"


def test_partition_rst_from_filename_returns_uns_elements(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    assert isinstance(elements[0], Title)


def test_partition_rst_from_filename_with_metadata_filename(
    filename="example-docs/README.rst",
):
    elements = partition_rst(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_rst_from_file(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f)
    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"
    for element in elements:
        assert element.metadata.filename is None


def test_partition_rst_from_file_with_metadata_filename(
    filename="example-docs/README.rst",
):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f, metadata_filename="test")
    assert elements[0] == Title("Example Docs")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_rst_from_filename_exclude_metadata(
    filename="example-docs/README.rst",
):
    elements = partition_rst(filename=filename, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rst_from_file_exclude_metadata(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition_rst(file=f, include_metadata=False)

    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rst_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.rst.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_rst("example-docs/README.rst")

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_rst_prefers_metadata_last_modified(mocker: MockFixture):
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch("unstructured.partition.rst.get_last_modified", return_value="2029-07-05T09:24:28")

    elements = partition_rst(
        "example-docs/README.rst", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_rst_with_json():
    elements = partition_rst(example_doc_path("README.rst"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_rst(filename="example-docs/README.rst"):
    elements = partition_rst(filename=filename)
    chunk_elements = partition_rst(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_rst_element_metadata_has_languages():
    filename = "example-docs/README.rst"
    elements = partition_rst(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_rst_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.rst"
    elements = partition_rst(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
