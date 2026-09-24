# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.xlsx` module (XLSM support)."""

from __future__ import annotations

import io
import tempfile

import pytest

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT_XLSX,
    EXPECTED_TITLE,
)
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import Table, Text, Title
from unstructured.partition.xlsx import partition_xlsm

# -- XLSM has a different MIME type than XLSX --
EXPECTED_FILETYPE_XLSM = "application/vnd.ms-excel.sheet.macroEnabled.12"
EXPECTED_PAGE_NAME = "Stanley Cups"


# ------------------------------------------------------------------------------------------------
# INTEGRATION TESTS
# ------------------------------------------------------------------------------------------------
# These test `partition_xlsm()` as a whole by calling `partition_xlsm()` and inspecting the
# outputs. XLSM files have the same structure as XLSX files but with macro support.
# ------------------------------------------------------------------------------------------------


def test_partition_xlsm_from_filename():
    """Test that partition_xlsm can process an XLSM file from filename."""
    elements = partition_xlsm("example-docs/stanley-cups.xlsm", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE_XLSM
    assert elements[1].metadata.page_name == EXPECTED_PAGE_NAME
    assert elements[1].metadata.filename == "stanley-cups.xlsm"


def test_partition_xlsm_from_file():
    """Test that partition_xlsm can process an XLSM file from file object."""
    with open("example-docs/stanley-cups.xlsm", "rb") as f:
        elements = partition_xlsm(file=f, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE_XLSM
    assert elements[1].metadata.page_name == EXPECTED_PAGE_NAME
    assert elements[1].metadata.filename is None


def test_partition_xlsm_from_file_with_metadata_filename():
    """Test that metadata_filename parameter works correctly for XLSM files."""
    with open("example-docs/stanley-cups.xlsm", "rb") as f:
        elements = partition_xlsm(
            file=f, metadata_filename="custom-name.xlsm", include_header=False
        )

    assert elements[0].metadata.filename == "custom-name.xlsm"


def test_partition_xlsm_from_file_like_object_with_name():
    """Test that partition_xlsm works with file-like objects that have a name attribute."""
    with open("example-docs/stanley-cups.xlsm", "rb") as f:
        file = io.BytesIO(f.read())
    file.name = "stanley-cups-downloaded.xlsm"

    elements = partition_xlsm(file=file, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE_XLSM


def test_partition_xlsm_from_SpooledTemporaryFile_with_emoji():
    """Test that partition_xlsm handles emoji characters correctly in XLSM files."""
    with tempfile.SpooledTemporaryFile() as f:
        with open("example-docs/emoji.xlsm", "rb") as g:
            f.write(g.read())

        elements = partition_xlsm(file=f, include_header=False)

    assert sum(isinstance(element, Text) for element in elements) == 1
    assert len(elements) == 1
    assert clean_extra_whitespace(elements[0].text) == "🤠😅"


def test_partition_xlsm_with_multiple_sheets():
    """Test that partition_xlsm correctly processes XLSM files with multiple worksheets."""
    elements = partition_xlsm("example-docs/multi-sheet-test.xlsm", include_header=False)

    # -- Should have elements from both sheets --
    assert len(elements) > 0

    # -- Check that we have tables from multiple sheets --
    page_names = {e.metadata.page_name for e in elements if hasattr(e.metadata, "page_name")}
    assert len(page_names) >= 2  # -- At least 2 different sheet names --


def test_partition_xlsm_with_subtables():
    """Test that partition_xlsm correctly detects subtables in XLSM files."""
    elements = partition_xlsm("example-docs/xlsx-subtable-cases.xlsm", find_subtable=True)

    # -- With subtable detection, we should get separate elements for subtables --
    assert len(elements) > 1


def test_partition_xlsm_without_subtables():
    """Test that partition_xlsm treats entire sheet as one table when find_subtable=False."""
    elements = partition_xlsm("example-docs/xlsx-subtable-cases.xlsm", find_subtable=False)

    # -- Without subtable detection, entire sheet is one table --
    assert len(elements) == 1
    assert isinstance(elements[0], Table)


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_xlsm_infer_table_structure(infer_table_structure: bool):
    """Test that infer_table_structure parameter controls HTML table generation."""
    elements = partition_xlsm(
        "example-docs/stanley-cups.xlsm", infer_table_structure=infer_table_structure
    )
    table_elements = [e for e in elements if isinstance(e, Table)]
    for table_element in table_elements:
        table_element_has_text_as_html_field = (
            hasattr(table_element.metadata, "text_as_html")
            and table_element.metadata.text_as_html is not None
        )
        assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_xlsm_with_header():
    """Test that partition_xlsm includes header when include_header=True."""
    elements = partition_xlsm("example-docs/stanley-cups.xlsm", include_header=True)

    assert len(elements) == 2
    assert all(isinstance(e, Table) for e in elements)
    e = elements[0]
    # -- Header row is included in the text --
    assert e.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert e.metadata.text_as_html is not None


def test_partition_xlsm_from_empty_file():
    """Test that partition_xlsm handles empty XLSM files gracefully."""
    elements = partition_xlsm("example-docs/empty.xlsm")

    # -- Empty file should return empty list or minimal elements --
    assert isinstance(elements, list)


def test_partition_xlsm_metadata_page_numbers():
    """Test that page numbers are correctly assigned to elements from multiple sheets."""
    elements = partition_xlsm("example-docs/multi-sheet-test.xlsm", starting_page_number=5)

    # -- Page numbers should start from the specified starting_page_number --
    page_numbers = [e.metadata.page_number for e in elements if hasattr(e.metadata, "page_number")]
    assert min(page_numbers) >= 5


def test_partition_xlsm_raises_on_no_file_or_path():
    """Test that partition_xlsm raises ValueError when neither file nor filename is provided."""
    with pytest.raises(ValueError, match="Either 'filename' or 'file' argument must be specif"):
        partition_xlsm()


def test_partition_xlsm_serializable_to_json():
    """Test that elements from partition_xlsm can be serialized to JSON."""
    elements = partition_xlsm("example-docs/stanley-cups.xlsm", include_header=False)

    # -- Elements should be serializable to JSON --
    assert_round_trips_through_JSON(elements)


# ------------------------------------------------------------------------------------------------
# FILE TYPE DETECTION TESTS
# ------------------------------------------------------------------------------------------------
# Test that XLSM files are correctly detected by the auto-detection system
# ------------------------------------------------------------------------------------------------


def test_auto_partition_xlsm_from_filename():
    """Test that partition() auto-detects XLSM files and uses partition_xlsm."""
    from unstructured.partition.auto import partition

    elements = partition("example-docs/stanley-cups.xlsm", include_header=False)

    # -- Should successfully partition the file --
    assert len(elements) > 0
    # -- Should use XLSM MIME type --
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE_XLSM


def test_auto_partition_xlsm_from_file():
    """Test that partition() auto-detects XLSM files from file objects."""
    from unstructured.partition.auto import partition

    with open("example-docs/stanley-cups.xlsm", "rb") as f:
        elements = partition(file=f, metadata_filename="test.xlsm", include_header=False)

    # -- Should successfully partition the file --
    assert len(elements) > 0
    # -- Should use XLSM MIME type --
    assert elements[0].metadata.filetype == EXPECTED_FILETYPE_XLSM
