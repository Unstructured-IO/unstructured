from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, Text
from unstructured.partition.epub import partition_epub
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


def test_partition_epub_from_filename():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
    for element in elements:
        assert element.metadata.filename == "winter-sports.epub"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"epub"}


def test_partition_epub_from_filename_returns_table_in_elements():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert (
        elements[14].text.replace("\n", " ")
        == Table(
            text="Contents. List of Illustrations "
            "(In certain versions of this etext [in certain browsers] "
            "clicking on the image will bring up a larger version.) "
            "(etext transcriber's note)",
        ).text
    )


def test_partition_epub_from_filename_returns_uns_elements():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert len(elements) > 0
    assert isinstance(elements[0], Text)


def test_partition_epub_from_filename_with_metadata_filename():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename, metadata_filename="test")
    assert len(elements) > 0
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_epub_from_file():
    filename = example_doc_path("winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")
    for element in elements:
        assert element.metadata.filename is None


def test_partition_epub_from_file_with_metadata_filename():
    filename = example_doc_path("winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f, metadata_filename="test")
    assert len(elements) > 0
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_epub_from_filename_exclude_metadata():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_epub_from_file_exlcude_metadata():
    filename = example_doc_path("winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition_epub(file=f, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_epub_pulls_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.epub.get_last_modified", return_value=filesystem_last_modified
    )

    elements = partition_epub("example-docs/winter-sports.epub")

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_epub_prefers_metadata_last_modified(mocker: MockFixture):
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.epub.get_last_modified", return_value="2029-07-05T09:24:28"
    )

    elements = partition_epub(
        "example-docs/winter-sports.epub", metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_epub_with_json():
    filename = "example-docs/winter-sports.epub"
    elements = partition_epub(filename=filename)

    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_epub(
    filename=example_doc_path("winter-sports.epub"),
):
    elements = partition_epub(filename=filename)
    chunk_elements = partition_epub(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_epub_non_default(
    filename=example_doc_path("winter-sports.epub"),
):
    elements = partition_epub(filename=filename)
    chunk_elements = partition_epub(
        filename,
        chunking_strategy="by_title",
        max_characters=5,
        new_after_n_chars=5,
        combine_text_under_n_chars=0,
    )
    chunks = chunk_by_title(
        elements,
        max_characters=5,
        new_after_n_chars=5,
        combine_text_under_n_chars=0,
    )
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_epub_element_metadata_has_languages():
    filename = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_epub_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.epub"
    elements = partition_epub(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
