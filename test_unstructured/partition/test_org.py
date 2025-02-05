from __future__ import annotations

from pathlib import Path

from pytest_mock import MockFixture

from test_unstructured.unit_utils import (
    assert_round_trips_through_JSON,
    example_doc_path,
    find_text_in_elements,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Title
from unstructured.partition.org import partition_org


def test_partition_org_from_filename():
    elements = partition_org(example_doc_path("README.org"))

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_partition_org_from_file():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f)

    assert elements[0] == Title("Example Docs")


# -- .metadata.filename --------------------------------------------------------------------------


def test_partition_org_from_filename_gets_filename_from_filename_arg():
    elements = partition_org(example_doc_path("README.org"))

    assert len(elements) > 0
    assert all(e.metadata.filename == "README.org" for e in elements)


def test_partition_org_from_file_gets_filename_None():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f)

    assert len(elements) > 0
    assert all(e.metadata.filename is None for e in elements)


def test_partition_org_from_filename_prefers_metadata_filename():
    elements = partition_org(example_doc_path("README.org"), metadata_filename="orig-name.org")

    assert len(elements) > 0
    assert all(element.metadata.filename == "orig-name.org" for element in elements)


def test_partition_org_from_file_prefers_metadata_filename():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f, metadata_filename="orig-name.org")

    assert all(e.metadata.filename == "orig-name.org" for e in elements)


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_org_gets_the_ORG_MIME_type_in_metadata_filetype():
    ORG_MIME_TYPE = "text/org"
    elements = partition_org(example_doc_path("README.org"))
    assert all(e.metadata.filetype == ORG_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{ORG_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_org_from_filename_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.org.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_org(example_doc_path("README.org"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_org_from_file_gets_last_modified_None():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_org_from_filename_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2020-08-04T06:11:47"
    metadata_last_modified = "2024-06-14T16:01:29"
    mocker.patch(
        "unstructured.partition.org.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_org(
        example_doc_path("README.org"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_org_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition_org(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_org_with_json():
    elements = partition_org(example_doc_path("README.org"))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_by_title_on_partition_org():
    file_path = example_doc_path("README.org")
    elements = partition_org(file_path)
    chunk_elements = partition_org(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_org_element_metadata_has_languages():
    elements = partition_org(example_doc_path("README.org"))
    assert elements[0].metadata.languages == ["eng"]


def test_partition_org_respects_detect_language_per_element():
    elements = partition_org(
        example_doc_path("language-docs/eng_spa_mult.org"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


def test_org_wont_include_external_files():
    # Make sure our import file is in place (otherwise the import fails silently and test passes)
    assert Path(example_doc_path("file_we_dont_want_imported")).exists()
    elements = partition_org(example_doc_path("README-w-include.org"))
    # The partition should contain some elements
    assert elements
    # We find something we expect to find from file we partitioned directly
    assert find_text_in_elements("instructions", elements)
    # But we don't find something from the file included within the file we partitioned directly
    assert not find_text_in_elements("wombat", elements)
