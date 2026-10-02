# pyright: reportPrivateUsage=false

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest
from pytest_mock import MockFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_SEMICOLON_DELIMITER,
    EXPECTED_TABLE_WITH_EMOJI,
    EXPECTED_TABLE_WITH_LINE_DELIMITER,
    EXPECTED_TEXT,
    EXPECTED_TEXT_SEMICOLON_DELIMITER,
    EXPECTED_TEXT_WITH_EMOJI,
    EXPECTED_TEXT_WITH_LINE_DELIMITER,
    EXPECTED_TEXT_XLSX,
)
from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.errors import UnprocessableEntityError
from unstructured.partition import csv as csv_module
from unstructured.partition.csv import (
    _CsvPartitioningContext,
    _first_record_width,
    check_cell_count,
    partition_csv,
    read_delimited_text,
)
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

EXPECTED_FILETYPE = "text/csv"


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.csv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.csv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
        (
            "table-semicolon-delimiter.csv",
            EXPECTED_TEXT_SEMICOLON_DELIMITER,
            EXPECTED_TABLE_SEMICOLON_DELIMITER,
        ),
        (
            "csv-with-line-delimiter.csv",
            EXPECTED_TEXT_WITH_LINE_DELIMITER,
            EXPECTED_TABLE_WITH_LINE_DELIMITER,
        ),
    ],
)
def test_partition_csv_from_filename(filename: str, expected_text: str, expected_table: str):
    f_path = f"example-docs/{filename}"
    elements = partition_csv(filename=f_path)

    assert clean_extra_whitespace(elements[0].text) == expected_text
    assert elements[0].metadata.text_as_html == expected_table
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_csv_from_filename_infer_table_structure(infer_table_structure: bool):
    f_path = "example-docs/stanley-cups.csv"
    elements = partition_csv(filename=f_path, infer_table_structure=infer_table_structure)

    table_element_has_text_as_html_field = (
        hasattr(elements[0].metadata, "text_as_html")
        and elements[0].metadata.text_as_html is not None
    )
    assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_csv_from_filename_with_metadata_filename():
    elements = partition_csv(example_doc_path("stanley-cups.csv"), metadata_filename="test")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_csv_with_encoding():
    elements = partition_csv(example_doc_path("stanley-cups-utf-16.csv"), encoding="utf-16")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.csv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.csv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_csv_from_file(filename: str, expected_text: str, expected_table: str):
    f_path = f"example-docs/{filename}"
    with open(f_path, "rb") as f:
        elements = partition_csv(file=f)
    assert clean_extra_whitespace(elements[0].text) == expected_text
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == expected_table
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.filename is None
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"csv"}


def test_partition_csv_from_file_with_metadata_filename():
    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(file=f, metadata_filename="test")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_csv_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = partition_csv(example_doc_path("stanley-cups.csv"))

    assert elements[0].metadata.last_modified == filesystem_last_modified


def test_partition_csv_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_csv(
        example_doc_path("stanley-cups.csv"), metadata_last_modified=metadata_last_modified
    )

    assert elements[0].metadata.last_modified == metadata_last_modified


def test_partition_csv_from_file_gets_last_modified_None():
    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(file=f)

    assert elements[0].metadata.last_modified is None


def test_partition_csv_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(file=f, metadata_last_modified=metadata_last_modified)

    assert elements[0].metadata.last_modified == metadata_last_modified


# ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["stanley-cups.csv", "stanley-cups-with-emoji.csv"])
def test_partition_csv_with_json(filename: str):
    elements = partition_csv(filename=example_doc_path(filename))
    assert_round_trips_through_JSON(elements)


def test_add_chunking_strategy_to_partition_csv_non_default():
    filename = "example-docs/stanley-cups.csv"

    elements = partition_csv(filename=filename)
    chunk_elements = partition_csv(
        filename,
        chunking_strategy="by_title",
        max_characters=9,
        combine_text_under_n_chars=0,
        include_header=False,
    )
    chunks = chunk_by_title(elements, max_characters=9, combine_text_under_n_chars=0)
    assert chunk_elements != elements
    assert chunk_elements == chunks


# NOTE (jennings) partition_csv returns a single TableElement per sheet,
# so leaving off additional tests for multiple languages like the other partitions
def test_partition_csv_element_metadata_has_languages():
    filename = "example-docs/stanley-cups.csv"
    elements = partition_csv(filename=filename, strategy="fast", include_header=False)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_csv_respects_languages_arg():
    filename = "example-docs/stanley-cups.csv"
    elements = partition_csv(
        filename=filename, strategy="fast", languages=["deu"], include_header=False
    )
    assert elements[0].metadata.languages == ["deu"]


def test_partition_csv_header():
    elements = partition_csv(
        example_doc_path("stanley-cups.csv"), strategy="fast", include_header=True
    )

    table = elements[0]
    assert table.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert table.metadata.text_as_html is not None


# -- cell-count limit ----------------------------------------------------------------------------


def test_partition_csv_rejects_a_wide_first_line_before_pandas_reads_it(
    tmp_path: Path, mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CSV_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    # -- Pandas pads every row out to the first line's 5,000 fields: 25M cells from 15KB --
    file_path = tmp_path / "ragged.csv"
    file_path.write_text("h" + "," * 4999 + "\n" + "a\n" * 5000)
    read_csv_ = mocker.patch.object(pd, "read_csv")

    with pytest.raises(UnprocessableEntityError, match="rows x 5,000 columns"):
        partition_csv(str(file_path))

    read_csv_.assert_not_called()


@pytest.mark.parametrize("from_file", [False, True])
@pytest.mark.parametrize(
    ("content", "n_measured_cells"),
    [
        # -- the context's restricted sniffer gives up on this one, so the delimiter is sniffed
        # -- from the first line without restricting the candidates --
        ("h" + "," * 99 + "\n" + "a\n" * 99, 100 * 100),
        # -- every line ending counts as a row, so the blank line makes this 4 rows (Pandas
        # -- reads 3): the measure is an upper bound --
        ("a;b;c\n1;2\n\n4\n", 3 * 4),
        # -- single-column file; the sniffer finds "a" as the delimiter, giving 2 columns --
        ("a\nb\nc\nd\n", 4 * 2),
        ('"x,\ny",z\n1\n', 2 * 2),  # -- quoted delimiter and newline start no field or row --
        ("a,b\r\nc,d\re,f", 3 * 2),  # -- "\r\n", "\r" and an unterminated last line --
    ],
)
def test_partition_csv_limits_the_cells_the_file_spans(
    content: str,
    n_measured_cells: int,
    from_file: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    file_path = tmp_path / "table.csv"
    file_path.write_bytes(content.encode())

    def partition():
        if from_file:
            with open(file_path, "rb") as f:
                return partition_csv(file=f)
        return partition_csv(str(file_path))

    monkeypatch.setenv("CSV_MAX_CELLS", str(n_measured_cells))
    assert len(partition()) == 1

    monkeypatch.setenv("CSV_MAX_CELLS", str(n_measured_cells - 1))
    with pytest.raises(UnprocessableEntityError, match="CSV_MAX_CELLS"):
        partition()


@pytest.mark.parametrize(
    "first_line",
    [
        " \t\n",  # -- a whitespace-only line is skipped, so the wide line is the first record --
        '"x\n"',  # -- a quoted newline does not end the first record --
        "\x0c",  # -- form-feed is not a line ending, so the commas are on the first line --
        'a"b',  # -- a quote inside a field does not open a quoted field --
        "\ufeff\n",  # -- a byte-order mark is dropped, leaving a blank line that is skipped --
    ],
)
def test_check_cell_count_measures_the_record_pandas_sizes_the_data_frame_by(
    first_line: str, monkeypatch: pytest.MonkeyPatch
):
    # -- Pandas reads 4 rows x 101 columns from each of these --
    file = io.BytesIO((first_line + "," * 100 + "\n" + "a,b\n" * 3).encode())
    monkeypatch.setenv("CSV_MAX_CELLS", "403")

    with pytest.raises(UnprocessableEntityError, match="101 columns"):
        check_cell_count(file, ",", None)


def test_partition_csv_is_not_tricked_into_millions_of_rows_by_a_carriage_return():
    # -- Pandas 2.x's C tokenizer reads this as 262,145 rows --
    elements = partition_csv(file=io.BytesIO(b"a,b\n\r ,c\n"))

    assert elements[0].metadata.text_as_html == (
        "<table><tr><td>a</td><td>b</td></tr><tr><td/><td>c</td></tr></table>"
    )


@pytest.mark.parametrize(("python_engine", "expected_width"), [(True, 11), (False, 1)])
def test_first_record_width_applies_each_pandas_engines_blank_line_rule(
    python_engine: bool, expected_width: int
):
    # -- the Python engine skips a record whose one value is whitespace, even quoted; the C engine
    # -- skips only an unquoted line of spaces and tabs --
    chunks = iter(['"  "\n' + ";" * 10 + "\n"])

    width, _ = _first_record_width(chunks, ";", python_engine, 10**9, Mock())

    assert width == expected_width


def test_partition_csv_sniffs_the_delimiter_from_the_first_non_blank_line():
    # -- the context's sniffer only tries ",;|", so Pandas' delimiter is sniffed here --
    elements = partition_csv(file=io.BytesIO(b"\n\na\tb\tc\n1\t2\t3\n"))

    assert elements[0].metadata.text_as_html == (
        "<table><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>1</td><td>2</td><td>3</td></tr>"
        "</table>"
    )


def test_read_delimited_text_streams_the_file_in_chunks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", 1)
    read_sizes: list[int] = []

    class RecordingBytesIO(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            read_sizes.append(-1 if size is None else size)
            return super().read(size)

    # -- with 1-byte chunks every "\r" is held back to see whether a "\n" follows it --
    dataframe = read_delimited_text(
        RecordingBytesIO(b'a,"x\r\ny"\r\nc,"d\re"\r'), sep=",", header=None, encoding=None
    )

    assert dataframe.values.tolist() == [["a", "x\r\ny"], ["c", "d\ne"]]
    assert set(read_sizes) == {1}


def test_partition_csv_reads_a_file_with_no_usable_delimiter_as_one_column():
    # -- the sniffer picks the quote as the delimiter, which cannot delimit fields --
    elements = partition_csv(file=io.BytesIO(b'"a"\n"b"\n'))

    assert (
        elements[0].metadata.text_as_html == "<table><tr><td>a</td></tr><tr><td>b</td></tr></table>"
    )


# ================================================================================================
# UNIT-TESTS
# ================================================================================================


class Describe_CsvPartitioningContext:
    """Unit-test suite for `unstructured.partition.csv._CsvPartitioningContext`."""

    # -- .load() ------------------------------------------------

    def it_provides_a_validating_alternate_constructor(self):
        ctx = _CsvPartitioningContext.load(
            file_path=example_doc_path("stanley-cups.csv"),
            file=None,
            encoding=None,
            include_header=True,
            infer_table_structure=True,
        )
        assert isinstance(ctx, _CsvPartitioningContext)

    def and_the_validating_constructor_raises_on_an_invalid_context(self):
        with pytest.raises(ValueError, match="either file-path or file-like object must be prov"):
            _CsvPartitioningContext.load(
                file_path=None,
                file=None,
                encoding=None,
                include_header=True,
                infer_table_structure=True,
            )

    # -- .delimiter ---------------------------------------------

    @pytest.mark.parametrize(
        "file_name",
        [
            "stanley-cups.csv",
            # -- Issue #2643: previously raised `_csv.Error: Could not determine delimiter` on
            # -- this file
            "csv-with-long-lines.csv",
        ],
    )
    def it_auto_detects_the_delimiter_for_a_comma_delimited_CSV_file(self, file_name: str):
        ctx = _CsvPartitioningContext(example_doc_path(file_name))
        assert ctx.delimiter == ","

    def and_it_auto_detects_the_delimiter_for_a_semicolon_delimited_CSV_file(self):
        ctx = _CsvPartitioningContext(example_doc_path("semicolon-delimited.csv"))
        assert ctx.delimiter == ";"

    def but_it_returns_None_as_the_delimiter_for_a_single_column_CSV_file(self):
        ctx = _CsvPartitioningContext(example_doc_path("single-column.csv"))
        assert ctx.delimiter is None

    # -- .header ------------------------------------------------

    @pytest.mark.parametrize(("include_header", "expected_value"), [(False, None), (True, 0)])
    def it_identifies_the_header_row_based_on_include_header_arg(
        self, include_header: bool, expected_value: int | None
    ):
        assert _CsvPartitioningContext(include_header=include_header).header == expected_value

    # -- .last_modified -----------------------------------------

    def it_gets_last_modified_from_the_filesystem_when_a_path_is_provided(
        self, get_last_modified_date_: Mock
    ):
        filesystem_last_modified = "2024-08-04T02:23:53"
        get_last_modified_date_.return_value = filesystem_last_modified
        ctx = _CsvPartitioningContext(file_path="a/b/document.csv")

        last_modified = ctx.last_modified

        get_last_modified_date_.assert_called_once_with("a/b/document.csv")
        assert last_modified == filesystem_last_modified

    def and_it_falls_back_to_None_for_the_last_modified_date_when_file_path_is_not_provided(self):
        file = io.BytesIO(b"abcdefg")
        ctx = _CsvPartitioningContext(file=file)

        last_modified = ctx.last_modified

        assert last_modified is None

    # -- .open() ------------------------------------------------

    def it_provides_transparent_access_to_the_source_file_when_it_is_a_file_like_object(self):
        with open(example_doc_path("stanley-cups.csv"), "rb") as f:
            # -- read so file cursor is at end of file --
            f.read()
            ctx = _CsvPartitioningContext(file=f)
            with ctx.open() as file:
                assert file is f
                # -- read cursor is reset to 0 on .open() context entry --
                assert f.tell() == 0
                assert file.read(14) == b"Stanley Cups,,"
                assert f.tell() == 14

            # -- and read cursor is reset to 0 on .open() context exit --
            assert f.tell() == 0

    def it_provides_transparent_access_to_the_source_file_when_it_is_a_file_path(self):
        ctx = _CsvPartitioningContext(example_doc_path("stanley-cups.csv"))
        with ctx.open() as file:
            assert file.read(14) == b"Stanley Cups,,"

    # -- .validate() --------------------------------------------

    def it_raises_when_neither_file_path_nor_file_is_provided(self):
        with pytest.raises(ValueError, match="either file-path or file-like object must be prov"):
            _CsvPartitioningContext()._validate()

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def get_last_modified_date_(self, request: FixtureRequest) -> Mock:
        return function_mock(request, "unstructured.partition.csv.get_last_modified_date")


# -- streaming and boundaries --------------------------------------------------------------------


def test_partition_csv_reads_past_a_long_blank_prefix_in_linear_time(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- no delimiter in the context's sample, so the delimiter is sniffed past the blank lines and
    # -- every blank line is replayed to Pandas' Python engine --
    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", 1024)
    data = b"\n" * 200_000 + b"a\tb\n1\t2\n"

    elements = partition_csv(file=io.BytesIO(data))

    assert elements[0].metadata.text_as_html == (
        "<table><tr><td>a</td><td>b</td></tr><tr><td>1</td><td>2</td></tr></table>"
    )


def test_lone_carriage_return_reader_copies_each_character_a_bounded_number_of_times(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", 1024)
    data = b"\n" * 200_000 + b"a\tb\n1\t2\n"
    reader = csv_module._LoneCarriageReturnReader(io.BytesIO(data), None)

    assert reader.peek_first_non_blank_line() == "a\tb\n"
    lines = list(iter(reader.readline, ""))

    assert len(lines) == 200_002
    assert "".join(lines) == data.decode()
    assert reader._chars_copied <= 3 * len(data)


def test_peek_first_non_blank_line_replays_the_original_chunks():
    chunks = ["\n" * 10, " \t\n", "a,", "b\n", "c,d\n"]

    line, replay = csv_module._peek_first_non_blank_line(iter(chunks))

    assert line == "a,b\n"
    assert all(a is b for a, b in zip(replay, chunks, strict=True))


def test_partition_csv_counts_the_implicit_index_column_of_a_header(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- data rows one field wider than the header: Pandas uses the extra field as the index --
    data = b"a,b\n1,2,3\n4,5,6\n"
    monkeypatch.setenv("CSV_MAX_CELLS", str(3 * 3))
    assert len(partition_csv(file=io.BytesIO(data), include_header=True)) == 1

    monkeypatch.setenv("CSV_MAX_CELLS", str(3 * 3 - 1))
    with pytest.raises(UnprocessableEntityError, match="3 columns"):
        partition_csv(file=io.BytesIO(data), include_header=True)


@pytest.mark.parametrize(
    "data",
    [
        '﻿é,ü\r\nx,"a\r\nb"\r\n',  # -- BOM, multibyte, CRLF inside and outside quotes --
        '日本,語\r1,"2\r3"\r\r\n',  # -- lone "\r" inside and outside quotes --
        '﻿﻿\n"q""uote","é"\n',  # -- repeated BOM, doubled quote --
    ],
)
@pytest.mark.parametrize("chunk_size", [1, 3])
def test_reading_does_not_depend_on_where_chunks_split_the_file(
    data: str, chunk_size: int, monkeypatch: pytest.MonkeyPatch
):
    encoded = data.encode()
    expected_text = csv_module._LoneCarriageReturnReader(io.BytesIO(encoded), None).read()
    expected_frame = read_delimited_text(io.BytesIO(encoded), sep=",", header=None, encoding=None)
    expected_cells = expected_frame.shape[0] * expected_frame.shape[1]

    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", chunk_size)

    assert csv_module._LoneCarriageReturnReader(io.BytesIO(encoded), None).read() == expected_text
    frame = read_delimited_text(io.BytesIO(encoded), sep=",", header=None, encoding=None)
    assert frame.equals(expected_frame)
    monkeypatch.setenv("CSV_MAX_CELLS", str(expected_cells - 1))
    with pytest.raises(UnprocessableEntityError):
        check_cell_count(io.BytesIO(encoded), ",", None)


@pytest.mark.parametrize(
    "data",
    [
        b"h"
        + b"," * 100
        + b"\n"
        + b"a\n" * 100_000,  # -- the first record alone passes the limit --
        b"a,b\n" * 100_000,  # -- the rows pass the limit --
    ],
)
def test_check_cell_count_stops_reading_once_the_limit_is_passed(
    data: bytes, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", 64)
    monkeypatch.setenv("CSV_MAX_CELLS", "50")
    n_bytes_read = 0

    class CountingBytesIO(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            nonlocal n_bytes_read
            chunk = super().read(size)
            n_bytes_read += len(chunk)
            return chunk

    with pytest.raises(UnprocessableEntityError):
        check_cell_count(CountingBytesIO(data), ",", None)

    assert n_bytes_read <= 4 * 64


def test_peek_first_non_blank_line_completes_a_line_across_a_chunk_of_only_a_held_carriage_return(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- with 1-byte chunks the "\r" chunk queues nothing until the "\n" after it arrives --
    monkeypatch.setattr(csv_module, "_CSV_CHUNK_CHARS", 1)
    reader = csv_module._LoneCarriageReturnReader(io.BytesIO(b"a\r\nb\n"), None)

    assert reader.peek_first_non_blank_line() == "a\r\n"
    assert reader.read() == "a\r\nb\n"


def test_partition_csv_counts_index_names_the_python_engine_infers(
    mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    # -- the context's sniffer only tries ",;|", so this tab-delimited file is read by Pandas'
    # -- Python engine. Its second data row is as wide as the first plus the header, so Pandas
    # -- makes the first data row the index names: 3 columns, from a 2-field header --
    data = b"a\tb\nidx\ni\t1\t2\n" + b"j\t3\t4\n" * 10
    pandas_cells = 13 * 3
    monkeypatch.setenv("CSV_MAX_CELLS", str(pandas_cells - 1))
    read_csv_ = mocker.patch.object(pd, "read_csv")

    with pytest.raises(UnprocessableEntityError, match="3 columns"):
        partition_csv(file=io.BytesIO(data), include_header=True)

    read_csv_.assert_not_called()
