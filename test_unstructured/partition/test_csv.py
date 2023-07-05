from test_unstructured.partition.test_constants import EXPECTED_TABLE, EXPECTED_TEXT
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.csv import partition_csv

EXPECTED_FILETYPE = "text/csv"


def test_partition_csv_from_filename(filename="example-docs/stanley-cups.csv"):
    elements = partition_csv(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.filename == "stanley-cups.csv"


def test_partition_csv_from_filename_with_metadata_filename(
    filename="example-docs/stanley-cups.csv",
):
    elements = partition_csv(filename=filename, metadata_filename="test")

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_csv_from_file(filename="example-docs/stanley-cups.csv"):
    with open(filename, "rb") as f:
        elements = partition_csv(file=f)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
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
