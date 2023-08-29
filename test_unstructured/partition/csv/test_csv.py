from tempfile import SpooledTemporaryFile

import pytest

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_WITH_EMOJI,
    EXPECTED_TEXT,
    EXPECTED_TEXT_WITH_EMOJI,
)
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.csv import partition_csv
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_to_json

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
        elements = partition_csv(file=f)

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
        elements = partition_csv(file=f, metadata_last_modified=expected_last_modification_date)

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


@pytest.mark.parametrize(
    ("filename", "expected_text", "expected_table"),
    [
        ("stanley-cups.csv", EXPECTED_TEXT, EXPECTED_TABLE),
        ("stanley-cups-with-emoji.csv", EXPECTED_TEXT_WITH_EMOJI, EXPECTED_TABLE_WITH_EMOJI),
    ],
)
def test_partition_csv_with_json(filename, expected_text, expected_table):
    f_path = f"example-docs/{filename}"
    elements = partition_csv(filename=f_path)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert clean_extra_whitespace(elements[0].text) == clean_extra_whitespace(test_elements[0].text)
    assert elements[0].metadata.text_as_html == test_elements[0].metadata.text_as_html
    assert elements[0].metadata.filename == test_elements[0].metadata.filename
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
