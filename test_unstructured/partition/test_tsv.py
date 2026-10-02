"""Test-suite for `unstructured.partition.tsv` module."""

from __future__ import annotations

import gzip
import io
from pathlib import Path
from typing import Any

import pandas as pd
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
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Table
from unstructured.errors import UnprocessableEntityError
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


# -- cell-count limit ----------------------------------------------------------------------------


@pytest.mark.parametrize("from_file", [False, True])
def test_partition_tsv_rejects_a_wide_first_line_before_pandas_reads_it(
    from_file: bool, tmp_path: Path, mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CSV_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    # -- Pandas pads every row out to the first line's 5,000 fields: 25M cells from 15KB --
    file_path = tmp_path / "ragged.tsv"
    file_path.write_text("h" + "\t" * 4999 + "\n" + "a\n" * 5000)
    read_csv_ = mocker.patch.object(pd, "read_csv")

    with pytest.raises(UnprocessableEntityError, match="rows x 5,000 columns"):
        if from_file:
            with open(file_path, "rb") as f:
                partition_tsv(file=f)
        else:
            partition_tsv(str(file_path))

    read_csv_.assert_not_called()


@pytest.mark.parametrize("from_file", [False, True])
def test_partition_tsv_partitions_a_file_at_the_cell_limit(
    from_file: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("CSV_MAX_CELLS", "6")
    file_path = tmp_path / "table.tsv"
    file_path.write_text("a\tb\tc\n1\t2\n")

    if from_file:
        with open(file_path, "rb") as f:
            elements = partition_tsv(file=f)
    else:
        elements = partition_tsv(str(file_path))

    assert [e.text for e in elements] == ["a b c 1 2"]


def test_partition_tsv_reads_a_field_larger_than_the_csv_module_field_limit(tmp_path: Path):
    # -- the `csv` module's default field limit is 128 KiB; Pandas has none --
    file_path = tmp_path / "big-field.tsv"
    file_path.write_text("a\t" + "x" * 200_000 + "\n")

    (table,) = partition_tsv(str(file_path))

    assert table.text == "a " + "x" * 200_000


def test_partition_tsv_decompresses_a_compressed_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    file_path = tmp_path / "table.tsv.gz"
    with gzip.open(file_path, "wb") as f:
        f.write(b"a\tb\n1\t2\n")

    (table,) = partition_tsv(str(file_path))

    assert table.text == "a b 1 2"

    # -- the size check measures the decompressed content --
    monkeypatch.setenv("CSV_MAX_CELLS", "3")
    with pytest.raises(UnprocessableEntityError, match="CSV_MAX_CELLS"):
        partition_tsv(str(file_path))


def test_partition_tsv_reads_a_stream_that_cannot_seek():
    class Pipe(io.RawIOBase):
        def __init__(self, data: bytes):
            self._data = io.BytesIO(data)

        def readable(self) -> bool:
            return True

        def seekable(self) -> bool:
            return False

        def readinto(self, buffer: Any) -> int:
            chunk = self._data.read(len(buffer))
            buffer[: len(chunk)] = chunk
            return len(chunk)

    (table,) = partition_tsv(file=io.BufferedReader(Pipe(b"a\tb\n1\t2\n")))

    assert table.text == "a b 1 2"


def test_partition_tsv_counts_every_implicit_index_column_before_pandas_reads(
    tmp_path: Path, mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    # -- a 1-field header, a 100-field first data row (99 implicit-index columns) and a ragged
    # -- tail: Pandas builds 1,002 rows x 100 columns --
    file_path = tmp_path / "index.tsv"
    file_path.write_text("h\n" + "\t".join(f"v{i}" for i in range(100)) + "\n" + "a\n" * 1000)
    monkeypatch.setenv("CSV_MAX_CELLS", str(1002 * 100 - 1))
    read_csv_ = mocker.patch.object(pd, "read_csv")

    with pytest.raises(UnprocessableEntityError, match="100 columns"):
        partition_tsv(str(file_path), include_header=True)

    read_csv_.assert_not_called()


def test_partition_tsv_with_implicit_index_columns_matches_pandas_within_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CSV_MAX_CELLS", raising=False)
    file_path = tmp_path / "index.tsv"
    file_path.write_text("h\n" + "x\ty\tz\n" + "a\n" * 3)

    (table,) = partition_tsv(str(file_path), include_header=True)

    expected = pd.read_csv(file_path, sep="\t", header=0).to_html(
        index=False, header=True, na_rep=""
    )
    assert table.text == HtmlTable.from_html_text(expected).text
