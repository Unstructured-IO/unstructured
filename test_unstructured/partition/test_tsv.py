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
from unstructured.chunking.base import TokenCounter
from unstructured.chunking.title import chunk_by_title
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import Table
from unstructured.errors import UnprocessableEntityError
from unstructured.partition.auto import partition
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


# -- `infer_table_structure` ---------------------------------------------------------------------


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_tsv_from_filename_infer_table_structure(infer_table_structure: bool):
    elements = partition_tsv(
        example_doc_path("stanley-cups.tsv"), infer_table_structure=infer_table_structure
    )

    has_text_as_html = elements[0].metadata.text_as_html is not None
    assert has_text_as_html == infer_table_structure


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_tsv_via_partition_respects_infer_table_structure(infer_table_structure: bool):
    elements = partition(
        example_doc_path("stanley-cups.tsv"), infer_table_structure=infer_table_structure
    )

    has_text_as_html = elements[0].metadata.text_as_html is not None
    assert has_text_as_html == infer_table_structure


def test_partition_tsv_with_html_disabled_and_token_overlap():
    pytest.importorskip("tiktoken")
    raw = b"a\t" + b"x" * 10_000 + b"\n"
    chunks = partition_tsv(
        file=io.BytesIO(raw),
        infer_table_structure=False,
        chunking_strategy="basic",
        max_tokens=100,
        tokenizer="cl100k_base",
        overlap=20,
    )

    assert len(chunks) > 1
    assert all(c.metadata.text_as_html is None for c in chunks)
    assert chunks[0].text.startswith("a x")
    assert all(set(c.text).issubset({"a", " ", "x"}) for c in chunks)
    assert "a" in chunks[0].text
    assert sum(c.text.count("x") for c in chunks) >= 10_000


def test_partition_auto_tsv_with_html_disabled_and_token_overlap():
    pytest.importorskip("tiktoken")
    raw = b"a\t" + b"x" * 10_000 + b"\n"
    chunks = partition(
        file=io.BytesIO(raw),
        metadata_filename="table.tsv",
        infer_table_structure=False,
        chunking_strategy="basic",
        max_tokens=100,
        tokenizer="cl100k_base",
        overlap=20,
    )

    assert len(chunks) > 1
    assert all(c.metadata.text_as_html is None for c in chunks)
    assert chunks[0].text.startswith("a x")
    assert all(set(c.text).issubset({"a", " ", "x"}) for c in chunks)
    assert "a" in chunks[0].text
    assert sum(c.text.count("x") for c in chunks) >= 10_000


# -- bounded token-chunking work for text-only tables --------------------------------------------


def _instrument_tokenizer_work(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Record [call-count, measured-characters] of the tokenizer used while chunking."""
    original_count = TokenCounter.count
    work = [0, 0]

    def counting_count(self: TokenCounter, text: str) -> int:
        work[0] += 1
        work[1] += len(text)
        return original_count(self, text)

    monkeypatch.setattr(TokenCounter, "count", counting_count)
    return work


def test_partition_tsv_html_disabled_bounds_token_measurement_work(monkeypatch: pytest.MonkeyPatch):
    """Chunking a separator-dense text-only table performs bounded tokenizer work per chunk."""
    tiktoken = pytest.importorskip("tiktoken")
    row_count = 20_000
    raw = b"a\tb\n" * row_count
    work = _instrument_tokenizer_work(monkeypatch)

    chunks = partition_tsv(
        file=io.BytesIO(raw),
        infer_table_structure=False,
        chunking_strategy="basic",
        max_tokens=100,
        tokenizer="cl100k_base",
        overlap=0,
    )

    # -- the ordered payload survives and every chunk stays within the token budget --
    assert len(chunks) > 1
    assert " ".join(chunk.text for chunk in chunks).split() == ["a", "b"] * row_count
    encode = tiktoken.get_encoding("cl100k_base").encode
    assert all(len(encode(chunk.text)) <= 100 for chunk in chunks)
    # -- tokenizer work stays bounded per chunk instead of growing with the table length --
    assert work[0] <= 30 * len(chunks)
    assert work[1] <= 40 * len(raw)


def test_partition_tsv_html_disabled_bounds_byte_conversion_work():
    """Chunking a text-only table must not convert the unread suffix to bytes per chunk."""
    import cProfile
    import pstats

    pytest.importorskip("tiktoken")
    row_count = 20_000
    raw = b"a\tb\n" * row_count

    profile = cProfile.Profile()
    profile.enable()
    try:
        chunks = partition_tsv(
            file=io.BytesIO(raw),
            infer_table_structure=False,
            chunking_strategy="basic",
            max_tokens=100,
            tokenizer="cl100k_base",
            overlap=0,
        )
    finally:
        profile.disable()

    assert len(chunks) > 1
    encode_entry = next(
        (
            value
            for func_name, value in pstats.Stats(profile).stats.items()
            if func_name[0] == "~" and "method 'encode' of 'str' objects" in func_name[2]
        ),
        None,
    )
    # -- sanity: per-chunk work (element-id hashing) does convert chunk-sized strings -- #
    assert encode_entry is not None
    encode_callers = list(encode_entry[4])
    # -- a per-chunk UTF-8 conversion of the unread suffix is quadratic at a fixed budget, --
    # -- so the chunking splitter itself must not convert strings to bytes at all -- #
    assert not any(caller[0].endswith("unstructured/chunking/base.py") for caller in encode_callers)


# -- shared vocabulary bound across HTML cell splitters -----------------------------------------


def test_partition_tsv_html_cells_share_one_vocabulary_traversal(monkeypatch: pytest.MonkeyPatch):
    """Oversized HTML cells must not each re-traverse the tokenizer vocabulary."""
    tiktoken = pytest.importorskip("tiktoken")
    import unstructured.chunking.base as chunking_base

    original_decode = tiktoken.Encoding.decode_single_token_bytes
    decode_calls = [0]

    def counting_decode_single_token_bytes(self, token: int) -> bytes:
        decode_calls[0] += 1
        return original_decode(self, token)

    monkeypatch.setattr(
        tiktoken.Encoding, "decode_single_token_bytes", counting_decode_single_token_bytes
    )

    def traversal_calls_for(row_count: int) -> int:
        chunking_base._max_token_bytes_for_encoding.cache_clear()
        decode_calls[0] = 0
        raw = (b"id\t" + b"a!" * 200 + b"\n") * row_count
        chunks = partition_tsv(
            file=io.BytesIO(raw),
            chunking_strategy="basic",
            max_tokens=100,
            tokenizer="gpt2",
        )
        assert chunks
        return decode_calls[0]

    few_rows = traversal_calls_for(5)
    many_rows = traversal_calls_for(50)

    assert few_rows > 0
    # -- the bound is per encoding, so adding oversized cells adds no vocabulary work -- #
    assert many_rows == few_rows


@pytest.mark.parametrize("chunking_strategy", ["basic", "by_title"])
@pytest.mark.parametrize("via_partition", [False, True])
def test_partition_tsv_html_disabled_many_short_rows_keeps_ordered_payload(
    chunking_strategy: str, via_partition: bool
):
    """Both entry points and both chunking strategies preserve the payload of a dense table."""
    tiktoken = pytest.importorskip("tiktoken")
    row_count = 2_000
    raw = b"a\tb\n" * row_count
    chunking_kwargs: dict[str, Any] = {
        "infer_table_structure": False,
        "chunking_strategy": chunking_strategy,
        "max_tokens": 100,
        "tokenizer": "cl100k_base",
        "overlap": 0,
    }

    if via_partition:
        chunks = partition(file=io.BytesIO(raw), metadata_filename="table.tsv", **chunking_kwargs)
    else:
        chunks = partition_tsv(file=io.BytesIO(raw), **chunking_kwargs)

    assert len(chunks) > 1
    assert all(chunk.metadata.text_as_html is None for chunk in chunks)
    assert " ".join(chunk.text for chunk in chunks).split() == ["a", "b"] * row_count
    encode = tiktoken.get_encoding("cl100k_base").encode
    assert all(len(encode(chunk.text)) <= 100 for chunk in chunks)


def test_partition_tsv_reads_each_cell_as_written(tmp_path: Path):
    file_path = tmp_path / "cells.tsv"
    file_path.write_text("name\tqty\tstatus\nPen\t12\tN/A\nInk\t\tNULL\n")

    element = partition_tsv(str(file_path), include_header=True)[0]

    assert element.text == "name qty status Pen 12 N/A Ink NULL"
