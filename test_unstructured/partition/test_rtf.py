from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, Title
from unstructured.partition.rtf import partition_rtf


def test_partition_rtf_from_filename():
    elements = partition_rtf(example_doc_path("fake-doc.rtf"))

    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")
    assert elements[-1] == Table(
        text="Column 1 Column 2 Row 1, Cell 1 Row 1, Cell 2 Row 2, Cell 1 Row 2, Cell 2"
    )


def test_partition_rtf_from_file():
    with open(example_doc_path("fake-doc.rtf"), "rb") as f:
        elements = partition_rtf(file=f)

    assert len(elements) > 0
    assert elements[0] == Title("My First Heading")


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_rtf_from_filename_gets_filename_from_filename_arg():
    elements = partition_rtf(example_doc_path("fake-doc.rtf"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "fake-doc.rtf" for e in elements)


def test_partition_rtf_from_file_gets_filename_None():
    with open(example_doc_path("fake-doc.rtf"), "rb") as f:
        elements = partition_rtf(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_rtf_from_filename_prefers_metadata_filename():
    elements = partition_rtf(example_doc_path("fake-doc.rtf"), metadata_filename="orig-name.rtf")

    assert len(elements) > 0
    assert all(element.metadata.filename == "orig-name.rtf" for element in elements)


def test_partition_rtf_from_file_prefers_metadata_filename():
    with open(example_doc_path("fake-doc.rtf"), "rb") as f:
        elements = partition_rtf(file=f, metadata_filename="orig-name.rtf")

    assert all(e.metadata.filename == "orig-name.rtf" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_rtf_gets_the_RTF_MIME_type_in_metadata_filetype():
    RTF_MIME_TYPE = "text/rtf"
    elements = partition_rtf(example_doc_path("fake-doc.rtf"))
    assert all(e.metadata.filetype == RTF_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{RTF_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_rtf_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.rtf.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_rtf("example-docs/fake-doc.rtf")

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_rtf_prefers_metadata_last_modified(mocker: MockFixture):
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.rtf.get_last_modified_date", return_value="2029-07-05T09:24:28"
    )

    elements = partition_rtf(
        "example-docs/fake-doc.rtf", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# -- other ---------------------------------------------------------------------------------------


def test_partition_rtf_with_json():
    elements = partition_rtf(filename=example_doc_path("fake-doc.rtf"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_rtf():
    file_path = example_doc_path("fake-doc.rtf")
    elements = partition_rtf(filename=file_path)

    chunk_elements = partition_rtf(file_path, chunking_strategy="by_title")
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
