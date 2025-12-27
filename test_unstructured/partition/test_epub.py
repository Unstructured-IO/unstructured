from __future__ import annotations

from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table, Text
from unstructured.partition.epub import partition_epub
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


def test_partition_epub_from_filename():
    elements = partition_epub(example_doc_path("simple.epub"))

    assert len(elements) > 0
    assert isinstance(elements[0], Text)
    assert elements[1].text.startswith("a shared culture")
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"epub"}


def test_partition_epub_from_filename_returns_table_in_elements():
    elements = partition_epub(example_doc_path("winter-sports.epub"))
    assert elements[12] == Table(
        "Contents. List of Illustrations (In certain versions of this etext [in certain\nbrowsers]"
        " clicking on the image will bring up a larger\nversion.) (etext transcriber's note)"
    )


def test_partition_epub_from_file():
    with open(example_doc_path("winter-sports.epub"), "rb") as f:
        elements = partition_epub(file=f)

    assert len(elements) > 0
    assert elements[2].text.startswith("The Project Gutenberg eBook of Winter Sports")


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_epub_from_filename_gets_filename_from_filename_arg():
    elements = partition_epub(example_doc_path("simple.epub"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "simple.epub" for e in elements)


def test_partition_epub_from_file_gets_filename_None():
    with open(example_doc_path("simple.epub"), "rb") as f:
        elements = partition_epub(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_epub_from_filename_prefers_metadata_filename():
    elements = partition_epub(example_doc_path("simple.epub"), metadata_filename="orig-name.epub")

    assert len(elements) > 0
    assert all(element.metadata.filename == "orig-name.epub" for element in elements)


def test_partition_epub_from_file_prefers_metadata_filename():
    with open(example_doc_path("simple.epub"), "rb") as f:
        elements = partition_epub(file=f, metadata_filename="orig-name.epub")

    assert all(e.metadata.filename == "orig-name.epub" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_epub_gets_the_EPUB_MIME_type_in_metadata_filetype():
    EPUB_MIME_TYPE = "application/epub"
    elements = partition_epub(example_doc_path("simple.epub"))
    assert all(e.metadata.filetype == EPUB_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{EPUB_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_epub_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.epub.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_epub(example_doc_path("winter-sports.epub"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_epub_from_file_gets_last_modified_None():
    with open(example_doc_path("simple.epub"), "rb") as f:
        elements = partition_epub(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_epub_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    metadata_last_modified = "2020-03-08T06:10:23"
    mocker.patch(
        "unstructured.partition.epub.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_epub(
        example_doc_path("winter-sports.epub"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_epub_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-03-08T06:10:23"
    with open(example_doc_path("simple.epub"), "rb") as f:
        elements = partition_epub(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified is metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_epub_with_json():
    filename = "example-docs/winter-sports.epub"
    elements = partition_epub(filename=filename)

    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_on_partition_epub():
    file_path = example_doc_path("winter-sports.epub")
    elements = partition_epub(file_path)
    chunk_elements = partition_epub(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_epub_non_default():
    file_path = example_doc_path("winter-sports.epub")
    elements = partition_epub(filename=file_path)
    chunk_elements = partition_epub(
        file_path,
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
