# pyright: reportPrivateUsage=false

from __future__ import annotations

import io
from tempfile import SpooledTemporaryFile

import pytest
from pytest_mock import MockFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_SEMICOLON_DELIMITER,
    EXPECTED_TABLE_WITH_EMOJI,
    EXPECTED_TEXT,
    EXPECTED_TEXT_SEMICOLON_DELIMITER,
    EXPECTED_TEXT_WITH_EMOJI,
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
from unstructured.partition.csv import _CsvPartitioningContext, partition_csv
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


def test_partition_csv_can_exclude_metadata():
    elements = partition_csv(example_doc_path("stanley-cups.csv"), include_metadata=False)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.filename is None


def test_partition_csv_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_csv(example_doc_path("stanley-cups.csv"))

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_csv_custom_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_csv(
        example_doc_path("stanley-cups.csv"),
        metadata_last_modified=expected_last_modification_date,
        include_header=False,
    )

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_csv_from_file_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(file=f, include_header=False)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified is None


def test_partition_csv_from_file_explicit_get_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(file=f, include_header=False, date_from_file_object=True)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_csv_from_file_custom_metadata_date(mocker: MockFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition_csv(
            file=f,
            metadata_last_modified=expected_last_modification_date,
            include_header=False,
            date_from_file_object=True,
        )

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_csv_from_file_without_metadata(mocker: MockFixture):
    """Test partition_csv() with file that are not possible to get last modified date"""

    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_csv(file=sf, date_from_file_object=True)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified is None


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
    assert clean_extra_whitespace(table.text) == (
        "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    )
    assert table.metadata.text_as_html is not None
    assert "<thead>" in table.metadata.text_as_html


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
            metadata_file_path=None,
            metadata_last_modified=None,
            include_header=True,
            infer_table_structure=True,
            date_from_file_object=False,
        )
        assert isinstance(ctx, _CsvPartitioningContext)

    def and_the_validating_constructor_raises_on_an_invalid_context(self):
        with pytest.raises(ValueError, match="either file-path or file-like object must be prov"):
            _CsvPartitioningContext.load(
                file_path=None,
                file=None,
                encoding=None,
                metadata_file_path=None,
                metadata_last_modified=None,
                include_header=True,
                infer_table_structure=True,
                date_from_file_object=False,
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

    # -- .last_modified --------------------------

    def it_gets_the_last_modified_date_of_the_document_from_the_caller_when_provided(self):
        ctx = _CsvPartitioningContext(metadata_last_modified="2024-08-04T13:12:35")
        assert ctx.last_modified == "2024-08-04T13:12:35"

    def and_it_falls_back_to_the_last_modified_date_of_the_file_when_a_path_is_provided(
        self, get_last_modified_date_: Mock
    ):
        get_last_modified_date_.return_value = "2024-08-04T02:23:53"
        ctx = _CsvPartitioningContext(file_path="a/b/document.csv")

        last_modified = ctx.last_modified

        get_last_modified_date_.assert_called_once_with("a/b/document.csv")
        assert last_modified == "2024-08-04T02:23:53"

    def and_it_falls_back_to_last_modified_date_of_file_when_a_file_like_object_is_provided(
        self, get_last_modified_date_from_file_: Mock
    ):
        get_last_modified_date_from_file_.return_value = "2024-08-04T13:17:47"
        file = io.BytesIO(b"abcdefg")
        ctx = _CsvPartitioningContext(file=file, date_from_file_object=True)

        last_modified = ctx.last_modified

        get_last_modified_date_from_file_.assert_called_once_with(file)
        assert last_modified == "2024-08-04T13:17:47"

    def but_it_falls_back_to_None_for_the_last_modified_date_when_date_from_file_object_is_False(
        self, get_last_modified_date_from_file_: Mock
    ):
        get_last_modified_date_from_file_.return_value = "2024-08-04T13:18:57"
        file = io.BytesIO(b"abcdefg")
        ctx = _CsvPartitioningContext(file=file, date_from_file_object=False)

        last_modified = ctx.last_modified

        get_last_modified_date_from_file_.assert_not_called()
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

    @pytest.fixture()
    def get_last_modified_date_from_file_(self, request: FixtureRequest):
        return function_mock(request, "unstructured.partition.csv.get_last_modified_date_from_file")
