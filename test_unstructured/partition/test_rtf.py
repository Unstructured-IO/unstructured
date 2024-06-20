from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, Title
from unstructured.partition.rtf import partition_rtf


def test_partition_rtf_from_filename():
    filename = example_doc_path("fake-doc.rtf")
    elements = partition_rtf(filename=filename)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    assert elements[-1] == Table(
        text="Column 1 Column 2 Row 1, Cell 1 Row 1, Cell 2 Row 2, Cell 1 Row 2, Cell 2"
    )
    for element in elements:
        assert element.metadata.filename == "fake-doc.rtf"


def test_partition_rtf_from_filename_with_metadata_filename():
    filename = example_doc_path("fake-doc.rtf")
    elements = partition_rtf(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_rtf_from_file():
    filename = example_doc_path("fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f)
    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename is None


def test_partition_rtf_from_file_with_metadata_filename():
    filename = example_doc_path("fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, metadata_filename="test")
    assert elements[0] == Title("My First Heading")
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_rtf_from_filename_exclude_metadata():
    filename = example_doc_path("fake-doc.rtf")
    elements = partition_rtf(filename=filename, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rtf_from_file_exclude_metadata():
    filename = example_doc_path("fake-doc.rtf")
    with open(filename, "rb") as f:
        elements = partition_rtf(file=f, include_metadata=False)
    for i in range(len(elements)):
        assert elements[i].metadata.to_dict() == {}


def test_partition_rtf_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.rtf.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_rtf("example-docs/fake-doc.rtf")

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_rtf_prefers_metadata_last_modified(mocker: MockFixture):
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch("unstructured.partition.rtf.get_last_modified", return_value="2029-07-05T09:24:28")

    elements = partition_rtf(
        "example-docs/fake-doc.rtf", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_rtf_with_json():
    elements = partition_rtf(filename=example_doc_path("fake-doc.rtf"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_rtf(filename="example-docs/fake-doc.rtf"):
    elements = partition_rtf(filename=filename)
    chunk_elements = partition_rtf(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_rtf_element_metadata_has_languages():
    filename = "example-docs/fake-doc.rtf"
    elements = partition_rtf(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_rtf_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.rtf"
    elements = partition_rtf(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
