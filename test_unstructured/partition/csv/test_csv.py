from tempfile import SpooledTemporaryFile

import pytest

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_WITH_EMOJI,
    EXPECTED_TEXT,
    EXPECTED_TEXT_WITH_EMOJI,
    EXPECTED_TEXT_XLSX,
)
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.csv import partition_csv
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA

EXPECTED_FILETYPE = "text/csv"


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.csv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.csv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_csv_from_filename(filename, expected_text, expected_table):
    f_path = f"example-docs/{filename}"
    elements = partition_csv(filename=f_path)

    assert clean_extra_whitespace(elements[0].text) == expected_text
    assert elements[0].metadata.text_as_html == expected_table
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize(
    "infer_table_structure",
    [
        True,
        False,
    ],
)
def test_partition_csv_from_filename_infer_table_structure(infer_table_structure):
    f_path = "example-docs/stanley-cups.csv"
    elements = partition_csv(filename=f_path, infer_table_structure=infer_table_structure)

    table_element_has_text_as_html_field = (
        hasattr(elements[0].metadata, "text_as_html")
        and elements[0].metadata.text_as_html is not None
    )
    assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_csv_from_filename_with_metadata_filename(
    filename="example-docs/stanley-cups.csv",
):
    elements = partition_csv(filename=filename, metadata_filename="test")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.csv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.csv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_csv_from_file(filename, expected_text, expected_table):
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


def test_partition_csv_from_file_with_metadata_filename(filename="example-docs/stanley-cups.csv"):
    with open(filename, "rb") as f:
        elements = partition_csv(file=f, metadata_filename="test")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_csv_can_exclude_metadata(filename="example-docs/stanley-cups.csv"):
    elements = partition_csv(filename=filename, include_metadata=False)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.filename is None


def test_partition_csv_metadata_date(mocker, filename="example-docs/stanley-cups.csv"):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = partition_csv(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_csv_custom_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.csv",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_csv(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
        include_header=False,
    )

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_csv_from_file_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.csv",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_csv(file=f, include_header=False)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_csv_from_file_custom_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.csv",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.csv.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_csv(
            file=f, metadata_last_modified=expected_last_modification_date, include_header=False
        )

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_csv_from_file_without_metadata(
    mocker,
    filename="example-docs/stanley-cups.csv",
):
    """Test partition_csv() with file that are not possible to get last modified date"""

    with open(filename, "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_csv(file=sf)

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
    filename = "example-docs/stanley-cups.csv"
    elements = partition_csv(filename=filename, strategy="fast", include_header=True)
    assert (
        clean_extra_whitespace(elements[0].text)
        == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    )
    assert "<thead>" in elements[0].metadata.text_as_html
