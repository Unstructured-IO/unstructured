from test_unstructured.partition.test_constants import EXPECTED_TABLE, EXPECTED_TEXT
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.xlsx import partition_xlsx

EXPECTED_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXCEPTED_PAGE_NAME = "Stanley Cups"


def test_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[0].metadata.filename == "stanley-cups.xlsx"


def test_partition_xlsx_from_filename_with_metadata_filename(
    filename="example-docs/stanley-cups.xlsx",
):
    elements = partition_xlsx(filename=filename, metadata_filename="test")

    assert all(isinstance(element, Table) for element in elements)
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[0].metadata.filename is None


def test_partition_xlsx_from_file_with_metadata_filename(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f, metadata_filename="test")

    assert all(isinstance(element, Table) for element in elements)
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_xlsx_filename_exclude_metadata(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_metadata=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.page_number is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_xlsx_from_file_exclude_metadata(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f, include_metadata=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.page_number is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None
