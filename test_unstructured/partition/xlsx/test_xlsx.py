import sys

import pytest
from pytest_mock import MockerFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT_XLSX,
    EXPECTED_TITLE,
)
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table, Text, Title
from unstructured.partition.xlsx import partition_xlsx

EXPECTED_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXCEPTED_PAGE_NAME = "Stanley Cups"


# ------------------------------------------------------------------------------------------------
# INTEGRATION TESTS
# ------------------------------------------------------------------------------------------------
# These test `partition_xlsx()` as a whole by calling `partition_xlsx()` and inspecting the
# outputs.
# ------------------------------------------------------------------------------------------------


def test_partition_xlsx_from_filename():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[1].metadata.filename == "stanley-cups.xlsx"


def test_partition_xlsx_from_filename_with_emoji():
    elements = partition_xlsx("example-docs/emoji.xlsx", include_header=False)
    assert sum(isinstance(element, Text) for element in elements) == 1
    assert len(elements) == 1
    assert clean_extra_whitespace(elements[0].text) == "🤠😅"


def test_partition_xlsx_from_filename_with_metadata_filename():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", metadata_filename="test", include_header=False
    )

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize(
    "infer_table_structure",
    [
        True,
        False,
    ],
)
def test_partition_xlsx_infer_table_structure(infer_table_structure: bool):
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", infer_table_structure=infer_table_structure
    )
    table_elements = [e for e in elements if isinstance(e, Table)]
    for table_element in table_elements:
        table_element_has_text_as_html_field = (
            hasattr(table_element.metadata, "text_as_html")
            and table_element.metadata.text_as_html is not None
        )
        assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_xlsx_from_filename_with_header():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=True)
    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 2
    assert (
        clean_extra_whitespace(elements[0].text)
        == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    )
    text_as_html = elements[0].metadata.text_as_html
    assert text_as_html is not None
    assert "<thead>" in text_as_html


def test_partition_xlsx_from_file():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[1].metadata.filename is None


def test_partition_xlsx_from_file_with_metadata_filename():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, metadata_filename="test", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.filename == "test"


def test_partition_xlsx_from_file_with_header():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_header=True)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 2
    assert (
        clean_extra_whitespace(elements[0].text)
        == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    )
    text_as_html = elements[0].metadata.text_as_html
    assert text_as_html is not None
    assert "<thead>" in text_as_html


def test_partition_xlsx_filename_exclude_metadata():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", include_metadata=False, include_header=False
    )

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html is None
    assert elements[1].metadata.page_number is None
    assert elements[1].metadata.filetype is None
    assert elements[1].metadata.page_name is None
    assert elements[1].metadata.filename is None


def test_partition_xlsx_from_file_exclude_metadata():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_metadata=False, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[0].metadata.text_as_html is None
    assert elements[0].metadata.page_number is None
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_xlsx_metadata_date(mocker: MockerFixture):
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value="2029-07-05T09:24:28"
    )

    elements = partition_xlsx("example-docs/stanley-cups.xlsx")

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


def test_partition_xlsx_with_custom_metadata_date(mocker: MockerFixture):
    """`metadata_last_modified` is preferred when provided"""
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value="2023-12-18T17:42:17"
    )

    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", metadata_last_modified="2020-07-05T09:24:28"
    )

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_xlsx_from_file_metadata_date(mocker: MockerFixture):
    """File's last-modified date is used when that's the best available source."""
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date_from_file",
        return_value="2029-07-05T09:24:28",
    )

    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f)

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


def test_partition_xlsx_from_file_with_custom_metadata_date(mocker: MockerFixture):
    """`metadata_last_modified` is preferred to file last-modified date when provided"""
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date_from_file",
        return_value="2023-12-18T17:42:17",
    )

    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, metadata_last_modified="2020-07-05T09:24:28")

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_xlsx_with_json():
    elements = partition_xlsx(example_doc_path("stanley-cups.xlsx"), include_header=False)
    assert_round_trips_through_JSON(elements)


def test_partition_xlsx_metadata_language_from_filename():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xlsx_subtables():
    elements = partition_xlsx("example-docs/vodafone.xlsx")
    assert sum(isinstance(element, Table) for element in elements) == 3
    assert len(elements) == 6


def test_partition_xlsx_element_metadata_has_languages():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx")
    assert elements[0].metadata.languages == ["eng"]


def test_partition_eml_respects_detect_language_per_element():
    elements = partition_xlsx(
        "example-docs/language-docs/eng_spa.xlsx", detect_language_per_element=True
    )

    langs = {e.metadata.languages[0] for e in elements if e.metadata.languages}
    assert "eng" in langs
    assert "spa" in langs


def test_partition_xlsx_with_more_than_1k_cells():
    old_recursion_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(1000)
        partition_xlsx("example-docs/more-than-1k-cells.xlsx")
    finally:
        sys.setrecursionlimit(old_recursion_limit)
