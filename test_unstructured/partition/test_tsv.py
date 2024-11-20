"""Test-suite for `unstructured.partition.tsv` module."""

from __future__ import annotations

import pytest
from pytest_mock import MockFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_WITH_EMOJI,
    EXPECTED_TEXT,
    EXPECTED_TEXT_WITH_EMOJI,
    EXPECTED_TEXT_XLSX,
)
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Table
from unstructured.partition.tsv import partition_tsv

EXPECTED_FILETYPE = "text/tsv"


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.tsv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.tsv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_tsv_from_filename(filename: str, expected_text: str, expected_table: str):
    elements = partition_tsv(example_doc_path(filename), include_header=False)

    table = elements[0]
    assert table.text == expected_text
    assert table.metadata.text_as_html == expected_table
    assert table.metadata.filetype == EXPECTED_FILETYPE
    assert all(e.metadata.filename == filename for e in elements)


def test_partition_tsv_from_filename_with_metadata_filename():
    elements = partition_tsv(
        example_doc_path("stanley-cups.tsv"), metadata_filename="test", include_header=False
    )

    assert elements[0].text == EXPECTED_TEXT
    assert all(e.metadata.filename == "test" for e in elements)


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.tsv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.tsv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_tsv_from_file(filename: str, expected_text: str, expected_table: str):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition_tsv(file=f, include_header=False)

    table = elements[0]
    assert isinstance(table, Table)
    assert table.text == expected_text
    assert table.metadata.text_as_html == expected_table
    assert table.metadata.filetype == EXPECTED_FILETYPE
    assert all(e.metadata.filename is None for e in elements)


def test_partition_tsv_from_file_with_metadata_filename():
    with open(example_doc_path("stanley-cups.tsv"), "rb") as f:
        elements = partition_tsv(file=f, metadata_filename="test", include_header=False)

    assert elements[0].text == EXPECTED_TEXT
    assert all(element.metadata.filename == "test" for element in elements)


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_tsv_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    mocker.patch(
        "unstructured.partition.tsv.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_tsv(example_doc_path("stanley-cups.tsv"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_tsv_from_file_gets_last_modified_None():
    with open(example_doc_path("stanley-cups.tsv"), "rb") as f:
        elements = partition_tsv(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_tsv_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.tsv.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_tsv(
        example_doc_path("stanley-cups.tsv"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_tsv_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("stanley-cups.tsv"), "rb") as f:
        elements = partition_tsv(file=f, metadata_last_modified=metadata_last_modified)

    assert elements[0].metadata.last_modified == metadata_last_modified


# ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["stanley-cups.tsv", "stanley-cups-with-emoji.tsv"])
def test_partition_tsv_with_json(filename: str):
    elements = partition_tsv(example_doc_path(filename), include_header=False)
    assert_round_trips_through_JSON(elements)


# NOTE (jennings) partition_tsv returns a single TableElement per sheet,
# so no adding tests for multiple languages like the other partitions
def test_partition_tsv_element_metadata_has_languages():
    filename = "example-docs/stanley-cups-with-emoji.tsv"
    elements = partition_tsv(filename=filename, include_header=False)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_tsv_header():
    elements = partition_tsv(
        example_doc_path("stanley-cups.tsv"), strategy="fast", include_header=True
    )

    table = elements[0]
    assert table.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert table.metadata.text_as_html is not None
    assert "<table>" in table.metadata.text_as_html


def test_partition_tsv_supports_chunking_strategy_while_partitioning():
    elements = partition_tsv(filename=example_doc_path("stanley-cups.tsv"))
    chunks = chunk_by_title(elements, max_characters=9, combine_text_under_n_chars=0)

    chunk_elements = partition_tsv(
        example_doc_path("stanley-cups.tsv"),
        chunking_strategy="by_title",
        max_characters=9,
        combine_text_under_n_chars=0,
        include_header=False,
    )

    # The same chunks are returned if chunking elements or chunking during partitioning.
    assert chunk_elements == chunks
