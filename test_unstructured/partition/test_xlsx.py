from test_unstructured.partition.test_constants import EXPECTED_TABLE, EXPECTED_TEXT
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table
from unstructured.partition.json import partition_json
from unstructured.partition.xlsx import partition_xlsx
from unstructured.staging.base import elements_to_json

EXPECTED_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXCEPTED_PAGE_NAME = "Stanley Cups"


def test_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE
    assert elements[0].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[0].metadata.filename == "stanley-cups.xlsx"


def test_partition_xlsx_from_filename_with_emoji(filename="example-docs/emoji.xlsx"):
    elements = partition_xlsx(filename=filename, include_header=False)
    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 1
    assert clean_extra_whitespace(elements[0].text) == "🤠😅"


def test_partition_xlsx_from_filename_with_metadata_filename(
    filename="example-docs/stanley-cups.xlsx",
):
    elements = partition_xlsx(filename=filename, metadata_filename="test", include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_xlsx_from_filename_with_header(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_header=True)
    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2
    assert (
        clean_extra_whitespace(elements[0].text)
        == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT
    )
    assert "<thead>" in elements[0].metadata.text_as_html


def test_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f, include_header=False)

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
        elements = partition_xlsx(file=f, metadata_filename="test", include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.filename == "test"


def test_partition_xlsx_from_file_with_header(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition_xlsx(file=f, include_header=True)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2
    assert (
        clean_extra_whitespace(elements[0].text)
        == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT
    )
    assert "<thead>" in elements[0].metadata.text_as_html


def test_partition_xlsx_filename_exclude_metadata(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_metadata=False, include_header=False)

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
        elements = partition_xlsx(file=f, include_metadata=False, include_header=False)

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


def test_partition_xlsx_with_json(filename="example-docs/stanley-cups.xlsx"):
    elements = partition_xlsx(filename=filename, include_header=False)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert clean_extra_whitespace(elements[0].text) == clean_extra_whitespace(test_elements[0].text)
    assert elements[0].metadata.text_as_html == test_elements[0].metadata.text_as_html
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    assert elements[0].metadata.page_name == test_elements[0].metadata.page_name
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]
