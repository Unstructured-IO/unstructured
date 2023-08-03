from test_unstructured.partition.test_constants import EXPECTED_TABLE, EXPECTED_TEXT
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.xlsx import partition_xlsx
from unstructured.utils import dependency_exists

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


def test_partition_xlsx_from_filename_with_emoji(filename="example-docs/emoji.xlsx"):
    # Make sure we have the beautifulsoup4 dependency to use the lxml.html.soupparser
    if dependency_exists("bs4"):
        elements = partition_xlsx(filename=filename)
        assert all(isinstance(element, Table) for element in elements)
        assert len(elements) == 1
        assert clean_extra_whitespace(elements[0].text) == "🤠😅"


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


def test_partition_xlsx_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.xlsx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xlsx(
        filename=filename,
    )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xlsx_with_custom_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.xlsx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xlsx(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_xlsx_from_file_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.xlsx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_xlsx(
            file=f,
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xlsx_from_file_with_custom_metadata_date(
    mocker,
    filename="example-docs/stanley-cups.xlsx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f, metadata_last_modified=expected_last_modification_date)

    assert elements[0].metadata.last_modified == expected_last_modification_date
