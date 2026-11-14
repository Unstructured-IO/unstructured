# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.xlsx` module."""

from __future__ import annotations

import io
import logging
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

import networkx as nx
import numpy as np
import openpyxl
import pandas as pd
import pandas.testing as pdt
import pytest
from pandas.io.excel._openpyxl import OpenpyxlReader
from pytest_mock import MockerFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT_XLSX,
    EXPECTED_TITLE,
)
from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import ListItem, Table, Text, Title
from unstructured.errors import UnprocessableEntityError
from unstructured.partition.xlsx import (
    _ConnectedComponent,
    _ConnectedComponents,
    _iter_worksheet_shapes,
    _RowCompactingOpenpyxlReader,
    _SubtableParser,
    _XlsxPartitionerOptions,
    partition_xlsx,
)

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


def test_partition_xlsx_from_SpooledTemporaryFile_with_emoji():
    with tempfile.SpooledTemporaryFile() as f:
        with open("example-docs/emoji.xlsx", "rb") as g:
            f.write(g.read())

        elements = partition_xlsx(file=f, include_header=False)

    assert sum(isinstance(element, Text) for element in elements) == 1
    assert len(elements) == 1
    assert clean_extra_whitespace(elements[0].text) == "🤠😅"


def test_partition_xlsx_raises_on_no_file_or_path_provided():
    with pytest.raises(ValueError, match="Either 'filename' or 'file' argument must be specif"):
        partition_xlsx()


def test_partition_xlsx_from_filename_with_metadata_filename():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", metadata_filename="test", include_header=False
    )

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("infer_table_structure", [True, False])
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

    assert len(elements) == 2
    assert all(isinstance(e, Table) for e in elements)
    e = elements[0]
    assert e.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert e.metadata.text_as_html is not None


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


def test_partition_xlsx_from_file_like_object_with_name():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        file = io.BytesIO(f.read())
    file.name = "stanley-cups-downloaded-from-network.xlsx"

    elements = partition_xlsx(file=file, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME


def test_partition_xlsx_from_file_with_metadata_filename():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, metadata_filename="test", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.filename == "test"


def test_partition_xlsx_from_file_with_header():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_header=True)

    assert len(elements) == 2
    assert all(isinstance(e, Table) for e in elements)
    e = elements[0]
    assert e.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert e.metadata.text_as_html is not None


def test_partition_xlsx_password_protected_raises_exception():
    with pytest.raises(UnprocessableEntityError):
        partition_xlsx(filename="example-docs/password_protected.xlsx")


def test_partition_xlsx_reads_xls_whose_workbook_stream_ends_in_padding():
    # -- written by `xlwt`; msoffcrypto's encryption check raises `struct.error` on the few bytes
    # -- of padding at the end of its Workbook stream (nolze/msoffcrypto-tool#83) --
    elements = partition_xlsx(example_doc_path("xlwt-padded-workbook.xls"))

    assert [(type(e).__name__, e.text) for e in elements] == [
        ("Table", "Fruit Count Apple 3 Pear 7")
    ]
    assert elements[0].metadata.page_name == "Fruit"


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_xlsx_from_file_path_gets_last_modified_from_filesystem(mocker: MockerFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xlsx(example_doc_path("stanley-cups.xlsx"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_xlsx_from_file_gets_last_modified_None():
    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        elements = partition_xlsx(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_xlsx_from_file_path_prefers_metadata_last_modified(mocker: MockerFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xlsx(
        example_doc_path("stanley-cups.xlsx"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_xlsx_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        elements = partition_xlsx(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_xlsx_with_json():
    elements = partition_xlsx(example_doc_path("stanley-cups.xlsx"), include_header=False)
    assert_round_trips_through_JSON(elements)


def test_partition_xlsx_metadata_language_from_filename():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xlsx_subtables():
    assert partition_xlsx("example-docs/xlsx-subtable-cases.xlsx") == [
        Table("a b c d e"),
        ListItem("f"),
        Title("a"),
        Table("b c d e"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Table("a b c d"),
        ListItem("2. e"),
        Table("a b c d"),
        Title("e"),
        Title("f"),
        Title("a"),
        Table("b c d e"),
        Title("f"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Title("g"),
        Title("a"),
        Table("b c d e"),
        Title("f"),
        Title("g"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Title("g"),
        Title("h"),
        Table("a b c"),
        Title("a"),
        Table("b c d"),
        Table("a b c"),
        Title("d"),
        Title("e"),
    ]


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


def test_partition_xlsx_generated_dense_table_preserves_text_and_html(tmp_path: Path):
    xlsx_path = _write_generated_xlsx(
        tmp_path,
        [
            ["Team", "Location", "Stanley Cups"],
            ["Blues", "STL", 1],
            ["Flyers", "PHI", 2],
        ],
    )

    elements = partition_xlsx(str(xlsx_path))

    assert elements == [Table("Team Location Stanley Cups Blues STL 1 Flyers PHI 2")]
    assert elements[0].metadata.text_as_html == (
        "<table>"
        "<tr><td>Team</td><td>Location</td><td>Stanley Cups</td></tr>"
        "<tr><td>Blues</td><td>STL</td><td>1</td></tr>"
        "<tr><td>Flyers</td><td>PHI</td><td>2</td></tr>"
        "</table>"
    )
    assert elements[0].metadata.page_name == "Sheet1"
    assert elements[0].metadata.page_number == 1


def test_partition_xlsx_generated_sparse_far_edge_cells_preserves_text_and_html(tmp_path: Path):
    rows = [[None for _ in range(10)] for _ in range(8)]
    rows[0][0] = "Far Edge Title"
    rows[6][8] = "Key"
    rows[6][9] = "Value"
    rows[7][8] = "answer"
    rows[7][9] = 42
    xlsx_path = _write_generated_xlsx(tmp_path, rows)

    elements = partition_xlsx(str(xlsx_path))

    assert elements == [Title("Far Edge Title"), Table("Key Value answer 42")]
    assert elements[1].metadata.text_as_html == (
        "<table><tr><td>Key</td><td>Value</td></tr><tr><td>answer</td><td>42</td></tr></table>"
    )


def test_partition_xlsx_generated_separated_blocks_and_single_cell_rows(tmp_path: Path):
    xlsx_path = _write_generated_xlsx(
        tmp_path,
        [
            ["North Report", None, None, None, None, None],
            ["Region", "Revenue", None, None, None, None],
            ["North", 100, None, None, None, None],
            [None, "Reviewed", None, None, None, None],
            [None, None, None, None, None, None],
            [None, None, None, "South Report", None, None],
            [None, None, None, "Region", "Revenue", None],
            [None, None, None, "EU", 200, None],
            [None, None, None, None, "Approved", None],
            [None, None, None, None, None, None],
            ["A", "B", None, None, "C", "D"],
            [1, 2, None, None, 3, 4],
        ],
    )

    elements = partition_xlsx(str(xlsx_path))

    assert elements == [
        Title("North Report"),
        Table("Region Revenue North 100"),
        Title("Reviewed"),
        Title("South Report"),
        Table("Region Revenue EU 200"),
        Title("Approved"),
        Table("A B C D 1 2 3 4"),
    ]
    assert elements[1].metadata.text_as_html == (
        "<table><tr><td>Region</td><td>Revenue</td></tr><tr><td>North</td><td>100</td></tr></table>"
    )
    assert elements[4].metadata.text_as_html == (
        "<table><tr><td>Region</td><td>Revenue</td></tr><tr><td>EU</td><td>200</td></tr></table>"
    )
    assert elements[6].metadata.text_as_html == (
        "<table>"
        "<tr><td>A</td><td>B</td><td/><td/><td>C</td><td>D</td></tr>"
        "<tr><td>1</td><td>2</td><td/><td/><td>3</td><td>4</td></tr>"
        "</table>"
    )


# -- worksheet cell-count limit ------------------------------------------------------------------


def test_partition_xlsx_rejects_a_stray_far_cell_before_pandas_reads_it(
    tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("XLSX_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    # -- one cell in the last column makes each of 400 rows 16,384 cells wide: 6.5M cells --
    cells = {(row, 1): f"r{row}" for row in range(1, 401)}
    file_path = _write_xlsx(tmp_path, {"Sheet": {**cells, (400, 16_384): "c"}})
    read_excel_ = mocker.patch.object(pd, "read_excel")
    reader_ = mocker.patch("unstructured.partition.xlsx._RowCompactingOpenpyxlReader")

    with pytest.raises(UnprocessableEntityError, match="rows x 16,384 columns"):
        partition_xlsx(file_path)

    read_excel_.assert_not_called()
    reader_.assert_not_called()


def test_partition_xlsx_partitions_a_stray_cell_in_the_last_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("XLSX_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    # -- the empty rows before a far-away row are read as one, so this spans 4 x 5 cells --
    file_path = _write_xlsx(tmp_path, {"Sheet": {(1, 1): "a", (2, 3): "b", (1_048_576, 5): "c"}})

    elements = partition_xlsx(file_path)

    assert [e.text for e in elements] == ["a", "b", "c"]


def test_partition_xlsx_rejects_a_stray_cell_in_the_last_row_of_a_whole_worksheet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("XLSX_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    # -- a whole worksheet is rendered with all its empty rows, so this spans 1M x 5 cells --
    file_path = _write_xlsx(tmp_path, {"Sheet": {(1, 1): "a", (2, 3): "b", (1_048_576, 5): "c"}})

    with pytest.raises(UnprocessableEntityError, match="1,048,576 rows x 5 columns"):
        partition_xlsx(file_path, find_subtable=False)


def test_partition_xlsx_partitions_a_stray_far_cell_within_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("XLSX_MAX_CELLS", raising=False)  # -- default limit of 5M cells --
    file_path = _write_xlsx(tmp_path, {"Sheet": {(1, 1): "a", (1, 2): "b", (200_000, 3): "c"}})

    elements = partition_xlsx(file_path)

    assert [e.text for e in elements] == ["a b", "c"]


def test_partition_xlsx_limits_cells_summed_across_worksheets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # -- each worksheet spans 10 x 10 = 100 cells --
    column = {(row, 1): f"r{row}" for row in range(1, 10)}
    file_path = _write_xlsx(
        tmp_path, {"One": {**column, (10, 10): "b"}, "Two": {**column, (10, 10): "d"}}
    )

    monkeypatch.setenv("XLSX_MAX_CELLS", "200")
    assert partition_xlsx(file_path)

    monkeypatch.setenv("XLSX_MAX_CELLS", "199")
    with pytest.raises(UnprocessableEntityError, match="worksheet 'Two'"):
        partition_xlsx(file_path)


@pytest.mark.parametrize(("max_cells", "raises"), [("1", True), (None, False)])
def test_partition_xlsx_applies_the_cell_limit_to_xls_files(
    max_cells: str | None, raises: bool, monkeypatch: pytest.MonkeyPatch
):
    if max_cells is None:
        monkeypatch.delenv("XLSX_MAX_CELLS", raising=False)
    else:
        monkeypatch.setenv("XLSX_MAX_CELLS", max_cells)

    if raises:
        with pytest.raises(UnprocessableEntityError, match="XLSX_MAX_CELLS"):
            partition_xlsx(example_doc_path("tests-example.xls"))
    else:
        assert partition_xlsx(example_doc_path("tests-example.xls"))


def test_partition_xlsx_keeps_cell_text_that_pandas_reads_as_missing_by_default():
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    for row in (
        ["Item", "Status"],
        ["Pear", "N/A"],
        ["Fig", "NA"],
        ["Plum", "null"],
        ["Kiwi", "None"],
    ):
        worksheet.append(row)
    file = io.BytesIO()
    workbook.save(file)

    (table,) = partition_xlsx(file=file)

    assert table.text == "Item Status Pear N/A Fig NA Plum null Kiwi None"
    assert "<td>N/A</td>" in table.metadata.text_as_html


def _budget_workbook_file() -> io.BytesIO:
    """A workbook whose last row totals the two above it with a SUM formula.

    openpyxl stores the formula without a computed result, the way the issue-#4637 files are
    written.
    """
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    for row in (["Item", "Amount"], ["Rent", 1000], ["Power", 450], ["Total", "=SUM(B2:B3)"]):
        worksheet.append(row)
    file = io.BytesIO()
    workbook.save(file)
    file.seek(0)
    return file


def test_partition_xlsx_warns_when_a_formula_cell_has_no_saved_result(
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=_budget_workbook_file())

    # -- the cell still reads as empty, so its row still falls out of the table --
    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text
    assert "B4" in caplog.text


def test_partition_xlsx_does_not_warn_when_the_formula_result_is_saved(
    caplog: pytest.LogCaptureFixture,
):
    # -- rewrite the workbook the way a calculating writer does, with the result in <v> --
    source = zipfile.ZipFile(_budget_workbook_file())
    file = io.BytesIO()
    with zipfile.ZipFile(file, "w") as destination:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content = content.replace(
                    b"<f>SUM(B2:B3)</f><v></v>", b"<f>SUM(B2:B3)</f><v>1450</v>"
                )
            destination.writestr(item, content)
    file.seek(0)

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        (table,) = partition_xlsx(file=file)

    assert table.text == "Item Amount Rent 1000 Power 450 Total 1450"
    assert "formula cell" not in caplog.text


def test_partition_xlsx_does_not_warn_when_the_workbook_has_no_formulas(
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(example_doc_path("stanley-cups.xlsx"))

    assert "formula cell" not in caplog.text


def test_partition_xlsx_formula_warning_scans_sparse_sheets_by_their_cells_not_dimensions(
    caplog: pytest.LogCaptureFixture,
):
    # -- a value in the last grid cell stretches the sheet's dimensions to 16,384 columns by
    # -- 1,048,576 rows; a dimensions-driven scan visits billions of empty cells before
    # -- returning, a cell-driven one only the nine populated ones. A formula on another
    # -- worksheet gets its own warning.
    workbook = openpyxl.Workbook()
    sheet_one = workbook.active
    for row in (["Item", "Amount"], ["Rent", 1000], ["Power", 450], ["Total", "=SUM(B2:B3)"]):
        sheet_one.append(row)
    sheet_one["XFD1048576"] = "far"
    sheet_two = workbook.create_sheet("Rates")
    sheet_two["A1"] = "=1+1"
    file = io.BytesIO()
    workbook.save(file)
    file.seek(0)

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=file)

    assert any(isinstance(e, Table) for e in elements)
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text
    assert "B4" in caplog.text
    assert "worksheet 'Rates': 1 formula cell(s) have no saved result" in caplog.text
    assert "A1" in caplog.text


def test_partition_xlsx_formula_warning_names_a_bounded_sample_of_a_large_formula_count(
    caplog: pytest.LogCaptureFixture,
):
    # -- a template holding many formulas without results extracts almost nothing; the warning
    # -- carries the full count but names only the first ten cells --
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(["Metric"])
    for row_num in range(2, 202):
        worksheet.cell(row=row_num, column=1, value=f"=A{row_num - 1}+1")
    file = io.BytesIO()
    workbook.save(file)
    file.seek(0)

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(file=file)

    assert "worksheet 'Sheet': 200 formula cell(s) have no saved result" in caplog.text
    assert "A2, A3, A4, A5, A6, A7, A8, A9, A10, A11 and 190 more" in caplog.text


def test_partition_xlsx_formula_warning_skips_styled_blank_cells(
    caplog: pytest.LogCaptureFixture,
):
    # -- styled blanks are stored as value-less cells; they are neither formulas nor results --
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(["Item", "Amount"])
    worksheet.append(["Rent", "=1000+0"])
    bold = openpyxl.styles.Font(bold=True)
    for row_num in range(3, 103):
        for col_num in range(1, 21):
            worksheet.cell(row=row_num, column=col_num).font = bold
    file = io.BytesIO()
    workbook.save(file)
    file.seek(0)
    source = zipfile.ZipFile(file)
    with_result = io.BytesIO()
    with zipfile.ZipFile(with_result, "w") as destination:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content = content.replace(b"<f>1000+0</f><v></v>", b"<f>1000+0</f><v>1000</v>")
            destination.writestr(item, content)
    with_result.seek(0)

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(file=with_result)

    assert "formula cell" not in caplog.text


def test_partition_xlsx_formula_warning_reads_no_external_link_parts(
    caplog: pytest.LogCaptureFixture,
):
    # -- an external-link relationship whose part is missing from the package: loading links
    # -- would fail or buy an unbounded cache, so the diagnostic must not touch them --
    source = zipfile.ZipFile(_budget_workbook_file())
    file = io.BytesIO()
    with zipfile.ZipFile(file, "w") as destination:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "xl/workbook.xml":
                content = content.replace(
                    b"</workbook>",
                    b"<externalReferences><externalReference"
                    b' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
                    b'relationships" r:id="rId99"/></externalReferences></workbook>',
                )
            if item.filename == "xl/_rels/workbook.xml.rels":
                content = content.replace(
                    b"</Relationships>",
                    b'<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/'
                    b'officeDocument/2006/relationships/externalLink"'
                    b' Target="externalLinks/externalLink1.xml"/></Relationships>',
                )
            destination.writestr(item, content)
    file.seek(0)

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=file)

    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text


def _repackaged(
    file: io.BytesIO, rewrites: dict[str, Callable[[bytes], tuple[str, bytes]]]
) -> io.BytesIO:
    """The workbook in `file` with each named member passed through its rewrite.

    A rewrite returns the member's new name and content, so a part can be moved as well as
    rewritten.
    """
    source = zipfile.ZipFile(file)
    repackaged = io.BytesIO()
    with zipfile.ZipFile(repackaged, "w") as destination:
        for item in source.infolist():
            name, content = item.filename, source.read(item.filename)
            if name in rewrites:
                name, content = rewrites[name](content)
            destination.writestr(name, content)
    repackaged.seek(0)
    return repackaged


def test_partition_xlsx_formula_warning_survives_a_comment_and_diagnoses_later_sheets(
    caplog: pytest.LogCaptureFixture,
):
    # -- a comment or processing instruction is not an element, so reading one as a cell took
    # -- down the diagnostic for the rest of the workbook, not just the sheet holding it --
    workbook = openpyxl.Workbook()
    sheet_one = workbook.active
    sheet_one.append(["Item", "Amount"])
    sheet_one.append(["Total", "=SUM(B1:B1)"])
    workbook.create_sheet("Rates")["A1"] = "=1+1"
    file = io.BytesIO()
    workbook.save(file)
    file.seek(0)

    annotated = _repackaged(
        file,
        {
            "xl/worksheets/sheet1.xml": lambda content: (
                "xl/worksheets/sheet1.xml",
                content.replace(b'<row r="1">', b'<row r="1"><!-- totals below --><?calc off?>'),
            )
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(file=annotated)

    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text
    assert "worksheet 'Rates': 1 formula cell(s) have no saved result" in caplog.text


def test_partition_xlsx_formula_warning_reads_a_namespace_prefixed_worksheet(
    caplog: pytest.LogCaptureFixture,
):
    # -- the same worksheet spelled with an explicit prefix holds no literal "<f" bytes, so a
    # -- byte search that finds none of them has proved nothing --
    def with_prefixed_tags(content: bytes) -> tuple[str, bytes]:
        content = content.replace(
            b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
            b'<x:worksheet xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
        )
        for tag in (b"worksheet", b"sheetData", b"row", b"c", b"f", b"v", b"is", b"t"):
            for opening, closing in (
                (b"<" + tag + b">", b"<x:" + tag + b">"),
                (b"<" + tag + b" ", b"<x:" + tag + b" "),
                (b"</" + tag + b">", b"</x:" + tag + b">"),
            ):
                content = content.replace(opening, closing)
        return "xl/worksheets/sheet1.xml", content

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(
            file=_repackaged(
                _budget_workbook_file(), {"xl/worksheets/sheet1.xml": with_prefixed_tags}
            )
        )

    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text
    assert "B4" in caplog.text


def test_partition_xlsx_formula_warning_reads_a_utf_16_encoded_worksheet(
    caplog: pytest.LogCaptureFixture,
):
    # -- UTF-16 pads every character, so the formula tag's bytes never appear next to each other
    def as_utf_16(content: bytes) -> tuple[str, bytes]:
        declared = content.decode("utf-8").replace('encoding="UTF-8"', 'encoding="UTF-16"')
        return "xl/worksheets/sheet1.xml", declared.encode("utf-16")

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(
            file=_repackaged(_budget_workbook_file(), {"xl/worksheets/sheet1.xml": as_utf_16})
        )

    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text
    assert "B4" in caplog.text


def test_partition_xlsx_formula_warning_follows_a_worksheet_outside_the_usual_directory(
    caplog: pytest.LogCaptureFixture,
):
    # -- readers follow the relationship wherever it points, so recognizing a worksheet by the
    # -- directory in its name left this workbook undiagnosed although it partitions normally --
    relocated = _repackaged(
        _budget_workbook_file(),
        {
            "xl/worksheets/sheet1.xml": lambda content: ("xl/sheets/sheet1.xml", content),
            "xl/_rels/workbook.xml.rels": lambda content: (
                "xl/_rels/workbook.xml.rels",
                content.replace(
                    b'Target="/xl/worksheets/sheet1.xml"', b'Target="sheets/sheet1.xml"'
                ),
            ),
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=relocated)

    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text


def test_partition_xlsx_formula_warning_finds_a_relocated_workbook_part(
    caplog: pytest.LogCaptureFixture,
):
    # -- the package manifest names the workbook part, so a writer may call it anything; reading
    # -- the conventional path left this workbook's relationships unreadable and undiagnosed --
    relocated = _repackaged(
        _budget_workbook_file(),
        {
            "xl/workbook.xml": lambda content: ("xl/book.xml", content),
            "xl/_rels/workbook.xml.rels": lambda content: ("xl/_rels/book.xml.rels", content),
            "[Content_Types].xml": lambda content: (
                "[Content_Types].xml",
                content.replace(b'PartName="/xl/workbook.xml"', b'PartName="/xl/book.xml"'),
            ),
            "_rels/.rels": lambda content: (
                "_rels/.rels",
                content.replace(b'Target="xl/workbook.xml"', b'Target="xl/book.xml"'),
            ),
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=relocated)

    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text


def test_partition_xlsx_formula_warning_resolves_a_worksheet_against_the_workbook_part(
    caplog: pytest.LogCaptureFixture,
):
    # -- a relative worksheet target resolves against the directory holding the workbook part,
    # -- which is not always `xl/`; assuming it was pointed the diagnostic at nothing --
    relocated = _repackaged(
        _budget_workbook_file(),
        {
            "xl/workbook.xml": lambda content: ("book/workbook.xml", content),
            "xl/worksheets/sheet1.xml": lambda content: ("book/sheets/sheet1.xml", content),
            "xl/_rels/workbook.xml.rels": lambda content: (
                "book/_rels/workbook.xml.rels",
                content.replace(
                    b'Target="/xl/worksheets/sheet1.xml"', b'Target="sheets/sheet1.xml"'
                ),
            ),
            "[Content_Types].xml": lambda content: (
                "[Content_Types].xml",
                content.replace(
                    b'PartName="/xl/workbook.xml"', b'PartName="/book/workbook.xml"'
                ).replace(
                    b'PartName="/xl/worksheets/sheet1.xml"',
                    b'PartName="/book/sheets/sheet1.xml"',
                ),
            ),
            "_rels/.rels": lambda content: (
                "_rels/.rels",
                content.replace(b'Target="xl/workbook.xml"', b'Target="book/workbook.xml"'),
            ),
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=relocated)

    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text


def test_partition_xlsx_formula_warning_keeps_quiet_about_a_cached_empty_string(
    caplog: pytest.LogCaptureFixture,
):
    # -- a string formula can compute the empty string, and a calculating writer caches it as an
    # -- empty <v> under a string cell type; recalculating would not recover anything --
    cached_blank = _repackaged(
        _budget_workbook_file(),
        {
            "xl/worksheets/sheet1.xml": lambda content: (
                "xl/worksheets/sheet1.xml",
                content.replace(
                    b'<c r="B4"><f>SUM(B2:B3)</f><v></v></c>',
                    b'<c r="B4" t="str"><f>IF(B2=0,"",B2)</f><v></v></c>',
                ),
            )
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        partition_xlsx(file=cached_blank)

    assert "formula cell" not in caplog.text


def test_partition_xlsx_formula_warning_keeps_quiet_about_a_cached_zero(
    caplog: pytest.LogCaptureFixture,
):
    # -- zero is a result like any other; only an absent or empty numeric cache is missing one --
    cached_zero = _repackaged(
        _budget_workbook_file(),
        {
            "xl/worksheets/sheet1.xml": lambda content: (
                "xl/worksheets/sheet1.xml",
                content.replace(b"<f>SUM(B2:B3)</f><v></v>", b"<f>SUM(B2:B3)</f><v>0</v>"),
            )
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        (table,) = partition_xlsx(file=cached_zero)

    assert table.text == "Item Amount Rent 1000 Power 450 Total 0"
    assert "formula cell" not in caplog.text


def test_partition_xlsx_formula_warning_retains_no_worksheet_xml_outside_the_rows(
    caplog: pytest.LogCaptureFixture,
):
    # -- a sheet can carry megabytes of merge, formatting or extension XML around a handful of
    # -- populated rows; the diagnostic parses into a target that builds no tree, so none of it
    # -- is retained while the DataFrames are already resident --
    padded = _repackaged(
        _budget_workbook_file(),
        {
            "xl/worksheets/sheet1.xml": lambda content: (
                "xl/worksheets/sheet1.xml",
                content.replace(
                    b"</sheetData>",
                    b"</sheetData><mergeCells>"
                    + b'<mergeCell ref="Z1:Z2"/>' * 50_000
                    + b"</mergeCells>",
                ),
            )
        },
    )

    with caplog.at_level(logging.WARNING, logger="unstructured"):
        elements = partition_xlsx(file=padded)

    assert elements == [Table("Item Amount Rent 1000 Power 450"), Title("Total")]
    assert "worksheet 'Sheet': 1 formula cell(s) have no saved result" in caplog.text


# ================================================================================================
# OTHER ARGS
# ================================================================================================


# -- `find_subtable` -----------------------------------------------------------------------------


def test_partition_xlsx_with_find_subtables_False_emits_one_Table_element_per_worksheet():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", find_subtable=False)
    assert elements == [
        Table(
            "Stanley Cups Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
        ),
        Table(
            "Stanley Cups Since 67 Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple"
            " Leafs TOR 0"
        ),
    ]


def test_partition_xlsx_with_find_subtables_False_and_infer_table_structure_False_works():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", find_subtable=False, infer_table_structure=False
    )
    assert elements == [
        Table(
            "Stanley Cups Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
        ),
        Table(
            "Stanley Cups Since 67 Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple"
            " Leafs TOR 0"
        ),
    ]
    assert all(e.metadata.text_as_html is None for e in elements)


# ------------------------------------------------------------------------------------------------
# UNIT TESTS
# ------------------------------------------------------------------------------------------------
# These test components used by `partition_xlsx()` in isolation such that all edge cases can be
# exercised.
# ------------------------------------------------------------------------------------------------


def _write_generated_xlsx(tmp_path: Path, rows: list[list[Any]]) -> Path:
    xlsx_path = tmp_path / "generated.xlsx"
    pd.DataFrame(rows).to_excel(xlsx_path, index=False, header=False)
    return xlsx_path


class Describe_XlsxPartitionerOptions:
    """Unit-test suite for `unstructured.partition.xlsx._XlsxPartitionerOptions` objects."""

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_find_subtables_within_each_worksheet_or_return_table_per_worksheet(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["find_subtable"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.find_subtable is arg_value

    @pytest.mark.parametrize(("arg_value", "expected_value"), [(True, 0), (False, None)])
    def it_knows_the_header_row_index_for_Pandas(
        self, arg_value: bool, expected_value: int | None, opts_args: dict[str, Any]
    ):
        opts_args["include_header"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.header_row_idx == expected_value

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_include_column_headings_in_Table_text_as_html(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["include_header"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.include_header is arg_value

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_include_text_as_html_in_Table_metadata(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["infer_table_structure"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.infer_table_structure is arg_value

    # -- .last_modified --------------------------------------------------------------------------

    def it_gets_last_modified_from_the_filesystem_when_a_path_is_provided(
        self, opts_args: dict[str, Any], get_last_modified_date_: Mock
    ):
        filesystem_last_modified = "2024-04-02T20:32:35"
        opts_args["file_path"] = "a/b/spreadsheet.xlsx"
        get_last_modified_date_.return_value = filesystem_last_modified
        opts = _XlsxPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        get_last_modified_date_.assert_called_once_with("a/b/spreadsheet.xlsx")
        assert last_modified == filesystem_last_modified

    def but_it_falls_back_to_None_for_the_last_modified_date_when_no_file_path_is_provided(
        self, opts_args: dict[str, Any]
    ):
        file = io.BytesIO(b"abcdefg")
        opts_args["file"] = file
        opts = _XlsxPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        assert last_modified is None

    # -- .metadata_file_path ---------------------------------------------------------------------

    def it_uses_the_file_path_argument_when_provided(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = "x/y/z.xlsx"
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == "x/y/z.xlsx"

    # -- ._excel_engine ---------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"),
        [("stanley-cups.xlsx", "openpyxl"), ("tests-example.xls", "xlrd")],
    )
    def it_picks_the_Pandas_engine_from_the_file_signature(
        self, file_name: str, expected_value: str, opts_args: dict[str, Any]
    ):
        opts_args["file_path"] = example_doc_path(file_name)
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts._excel_engine == expected_value

    def but_it_rejects_a_file_that_is_neither_XLSX_nor_XLS(self, opts_args: dict[str, Any]):
        opts_args["file"] = io.BytesIO(b"not a spreadsheet")
        opts = _XlsxPartitionerOptions(**opts_args)

        with pytest.raises(UnprocessableEntityError, match="Not a valid XLSX or XLS file"):
            opts._excel_engine

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def get_last_modified_date_(self, request: FixtureRequest):
        return function_mock(request, "unstructured.partition.xlsx.get_last_modified_date")

    @pytest.fixture()
    def opts_args(self) -> dict[str, Any]:
        """All default arguments for `_XlsxPartitionerOptions`.

        Individual argument values can be changed to suit each test. Makes construction of opts more
        compact for testing purposes.
        """
        return {
            "file_path": None,
            "file": None,
            "find_subtable": True,
            "include_header": False,
            "infer_table_structure": True,
        }


class Describe_ConnectedComponent:
    """Unit-test suite for `unstructured.partition.xlsx._ConnectedComponent` objects."""

    def it_knows_its_top_and_left_extents(self):
        component = _ConnectedComponent(pd.DataFrame(), {(0, 1), (2, 2), (1, 1), (2, 3), (1, 2)})

        assert component.min_x == 0
        assert component.max_x == 2

    def it_can_merge_with_another_component_to_make_a_new_component(self):
        df = pd.DataFrame()
        component = _ConnectedComponent(df, {(0, 1), (0, 2), (1, 1)})
        other = _ConnectedComponent(df, {(0, 4), (1, 3), (1, 4)})

        merged = component.merge(other)

        assert merged._worksheet is df
        assert merged._cell_coordinate_set == {(0, 1), (0, 2), (1, 1), (0, 4), (1, 3), (1, 4)}

    def it_can_extract_the_rectangular_subtable_containing_its_cells_from_the_worksheet(self):
        worksheet_df = pd.DataFrame(
            [["a", "b", "c"], [], ["d", "e"], ["f", "g"], [None, "h"], [], ["i"]],
            index=[0, 1, 2, 3, 4, 5, 6],
        )
        cell_coordinate_set = {(2, 0), (2, 1), (3, 0), (3, 1), (4, 1)}
        component = _ConnectedComponent(worksheet_df, cell_coordinate_set)

        subtable = component.subtable

        print(f"{subtable=}")
        pdt.assert_frame_equal(
            subtable, pd.DataFrame([["d", "e"], ["f", "g"], [None, "h"]], index=[2, 3, 4])
        )


class Describe_ConnectedComponents:
    """Unit-test suite for `unstructured.partition.xlsx._ConnectedComponents` objects."""

    @pytest.mark.parametrize("seed", range(20))
    def it_finds_the_same_components_as_a_full_grid_graph(self, seed: int):
        rng = np.random.default_rng(seed)
        n_rows, n_cols = rng.integers(1, 15, size=2)
        cells = np.where(rng.random((n_rows, n_cols)) < 0.4, "x", None)
        worksheet_df = pd.DataFrame(cells)

        components = _ConnectedComponents.from_worksheet_df(worksheet_df)

        # -- reference: every cell is a grid node, then the empty ones are removed --
        graph = nx.grid_2d_graph(n_rows, n_cols)
        graph.remove_nodes_from(tuple(rc) for rc in np.argwhere(worksheet_df.isna().to_numpy()))
        expected = _ConnectedComponents(worksheet_df)._merge_overlapping_tables(
            [_ConnectedComponent(worksheet_df, s) for s in nx.connected_components(graph)]
        )
        assert sorted(sorted(c._cell_coordinate_set) for c in components) == sorted(
            sorted(c._cell_coordinate_set) for c in expected
        )

    def it_treats_a_completely_empty_worksheet_as_having_no_components(self):
        # -- regression: `.notna().to_numpy()` on a 0x0 frame is float64, so the `&` in
        # -- `_connected_components` raised `TypeError: ufunc 'bitwise_and' not supported`; a
        # -- workbook with any empty sheet (e.g. a trailing blank `Sheet2`) failed to partition --
        components = _ConnectedComponents.from_worksheet_df(pd.DataFrame())

        assert list(components) == []


class Describe_iter_worksheet_shapes:
    """Unit-test suite for `unstructured.partition.xlsx._iter_worksheet_shapes()`."""

    @pytest.mark.parametrize(
        "file_name", ["stanley-cups.xlsx", "more-than-1k-cells.xlsx", "tests-example.xls"]
    )
    def it_measures_the_shape_read_for_each_worksheet(self, file_name: str):
        file_path = example_doc_path(file_name)
        self._assert_shapes_match_what_is_read(file_path)

    def and_it_measures_sparse_worksheets_with_trailing_empty_cells(self, tmp_path: Path):
        file_path = _write_xlsx(
            tmp_path,
            {
                "Sparse": {(3, 2): "a", (7, 5): 0, (12, 1): "b", (13, 9): ""},
                "Adjacent": {(1, 1): "a", (2, 1): "b", (4, 2): "c", (100_000, 3): "d"},
                "Leading": {(5, 1): 1, (6, 1): 2, (9, 2): 3},
                "Empty": {},
                "Blank": {(4, 4): ""},
            },
        )
        self._assert_shapes_match_what_is_read(file_path)

    def _assert_shapes_match_what_is_read(self, file_path: str):
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        for find_subtable in (True, False):
            opts = _XlsxPartitionerOptions(
                file_path=file_path,
                file=None,
                find_subtable=find_subtable,
                include_header=False,
                infer_table_structure=True,
            )
            engine = opts._excel_engine
            # -- the last shape generated for each worksheet is its full shape --
            shapes = {
                name: (n_rows, n_cols)
                for _, name, n_rows, n_cols in _iter_worksheet_shapes(
                    file_bytes, engine, engine == "openpyxl" and find_subtable
                )
            }

            assert shapes == {name: df.shape for name, df in opts.sheets.items()}


class Describe_RowCompactingOpenpyxlReader:
    """Unit-test suite for `unstructured.partition.xlsx._RowCompactingOpenpyxlReader`."""

    def it_reads_each_run_of_empty_rows_as_one_empty_row(self, tmp_path: Path):
        file_path = _write_xlsx(
            tmp_path,
            {"Sheet": {(4, 1): "a", (5, 2): 1, (40, 1): "b", (41, 1): "c", (1_048_576, 3): "d"}},
        )

        df = _RowCompactingOpenpyxlReader(file_path).parse(sheet_name=None, header=None)["Sheet"]

        # -- except the leading run, which keeps two: one for a header row, one for the data --
        expected = pd.DataFrame(
            [
                [None, None, None],
                [None, None, None],
                ["a", None, None],
                [None, 1, None],
                [None, None, None],
                ["b", None, None],
                ["c", None, None],
                [None, None, None],
                [None, None, "d"],
            ]
        )
        pdt.assert_frame_equal(df, expected, check_dtype=False)
        assert df.iloc[3, 1] == 1  # -- cell values are converted exactly as Pandas does --

    @pytest.mark.parametrize(
        "file_name",
        [
            "2023-half-year-analyses-by-segment.xlsx",
            "emoji.xlsx",
            "more-than-1k-cells.xlsx",
            "stanley-cups.xlsx",
            "vodafone.xlsx",
            "xlsx-subtable-cases.xlsx",
            None,
            "leading-empty-rows",
        ],
    )
    @pytest.mark.parametrize("include_header", [False, True])
    @pytest.mark.parametrize("find_subtable", [True, False])
    def it_partitions_exactly_as_the_stock_reader_does(
        self,
        file_name: str | None,
        include_header: bool,
        find_subtable: bool,
        tmp_path: Path,
        mocker: MockerFixture,
    ):
        if file_name == "leading-empty-rows":
            # -- with a header, the stock reader infers this complete integer column as float --
            cells = {(row, 1): row for row in range(4, 8)}
            cells.update({(row, 2): f"v{row}" for row in range(4, 8)})
            file_path = _write_xlsx(tmp_path, {"Sheet": cells, "Gap": {(1, 1): "a", (5, 1): "b"}})
        elif file_name is None:
            # -- tables separated by long runs of empty rows, and leading empty rows --
            cells: dict[tuple[int, int], Any] = {
                (row + 2, col): f"t{row}-{col}" for row in range(4) for col in range(1, 4)
            }
            cells.update({(50, 2): "Title", (51, 2): 1.5, (51, 3): 2, (52, 2): None})
            cells.update({(row, 1): row for row in range(300, 303)})
            cells[(9_000, 2)] = "far"
            file_path = _write_xlsx(tmp_path, {"Sheet": cells, "Other": {(5, 5): "x"}})
        else:
            file_path = example_doc_path(file_name)

        def partition() -> list[tuple[Any, ...]]:
            return [
                (e.category, e.text, e.metadata.text_as_html, e.metadata.page_name)
                for e in partition_xlsx(
                    file_path, find_subtable=find_subtable, include_header=include_header
                )
            ]

        actual = partition()

        class StockReader(OpenpyxlReader):
            pass

        mocker.patch("unstructured.partition.xlsx._RowCompactingOpenpyxlReader", StockReader)
        assert actual == partition()


class Describe_SubtableParser:
    """Unit-test suite for `unstructured.partition.xlsx._SubtableParser` objects."""

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            # -- 1. no leading or trailing single-cell rows --
            (
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 2. one leading single-cell row --
            (
                pd.DataFrame([["a"], ["b", "c"], ["d", "e"]], index=[0, 1, 2]),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 3. two leading single-cell rows --
            (
                pd.DataFrame(
                    [[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]], index=[0, 1, 2, 3]
                ),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 4. one trailing single-cell row --
            (
                pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]], index=[0, 1, 2]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 5. two trailing single-cell rows --
            (
                pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]], index=[0, 1, 2, 3]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 6. one leading, one trailing single-cell rows --
            (
                pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]], index=[0, 1, 2, 3]),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 7. two leading, one trailing single-cell rows --
            (
                pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]], index=[0, 1, 2, 3, 4]),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 8. one leading, two trailing single-cell rows --
            (
                pd.DataFrame(
                    [[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]],
                    index=[0, 1, 2, 3, 4],
                ),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 9. two leading, two trailing single-cell rows --
            (
                pd.DataFrame(
                    [["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]], index=[0, 1, 2, 3, 4, 5]
                ),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 10. single-row core-table, no leading or trailing single-cell rows --
            (
                pd.DataFrame([["a", "b", "c"]], index=[0]),
                pd.DataFrame([["a", "b", "c"]], index=[0]),
            ),
            # -- 11. single-row core-table, one leading single-cell row --
            (
                pd.DataFrame([["a"], ["b", "c", "d"]], index=[0, 1]),
                pd.DataFrame([["b", "c", "d"]], index=[1]),
            ),
            # -- 12. single-row core-table, two trailing single-cell rows --
            (
                pd.DataFrame([["a", "b", "c"], ["d"], ["e"]], index=[0, 1, 2]),
                pd.DataFrame([["a", "b", "c"]], index=[0]),
            ),
        ],
    )
    def it_extracts_the_core_table_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        """core-table is correctly distinguished from leading and trailing single-cell rows."""
        subtable_parser = _SubtableParser(subtable)

        core_table = subtable_parser.core_table

        assert core_table is not None
        pdt.assert_frame_equal(core_table, expected_value)

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            (pd.DataFrame([["a", "b"], ["c", "d"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"]]), ["a"]),
            (pd.DataFrame([[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]]), ["a", "b"]),
            (pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]]), []),
            (pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]]), ["a"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]]), ["a", "b"]),
            (pd.DataFrame([[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]]), ["a"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]]), ["a", "b"]),
            (pd.DataFrame([["a", "b", "c"]]), []),
            (pd.DataFrame([["a"], ["b", "c", "d"]]), ["a"]),
            (pd.DataFrame([["a", "b", "c"], ["d"], ["e"]]), []),
        ],
    )
    def it_extracts_the_leading_single_cell_rows_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        subtable_parser = _SubtableParser(subtable)
        leading_single_cell_row_texts = list(subtable_parser.iter_leading_single_cell_rows_texts())
        assert leading_single_cell_row_texts == expected_value

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            (pd.DataFrame([["a", "b"], ["c", "d"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"]]), []),
            (pd.DataFrame([[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]]), []),
            (pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]]), ["e"]),
            (pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]]), ["e", "f"]),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]]), ["f"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]]), ["g"]),
            (
                pd.DataFrame([[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]]),
                ["f", "g"],
            ),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]]), ["g", "h"]),
            (pd.DataFrame([["a", "b", "c"]]), []),
            (pd.DataFrame([["a"], ["b", "c", "d"]]), []),
            (pd.DataFrame([["a", "b", "c"], ["d"], ["e"]]), ["d", "e"]),
        ],
    )
    def it_extracts_the_trailing_single_cell_rows_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        subtable_parser = _SubtableParser(subtable)

        trailing_single_cell_row_texts = list(
            subtable_parser.iter_trailing_single_cell_rows_texts()
        )

        assert trailing_single_cell_row_texts == expected_value


def _legacy_xlsx_components(worksheet_df):
    """Original dense graph implementation, retained only as a compatibility oracle."""
    rows, cols = worksheet_df.shape
    graph = nx.grid_2d_graph(rows, cols)
    graph.remove_nodes_from(
        (row, col)
        for row in range(rows)
        for col in range(cols)
        if pd.isna(worksheet_df.iloc[row, col])
    )
    return list(
        _ConnectedComponents(worksheet_df)._merge_overlapping_tables(
            [_ConnectedComponent(worksheet_df, cells) for cells in nx.connected_components(graph)]
        )
    )


def test_sparse_xlsx_matches_legacy_for_every_three_by_three_occupancy():
    # Exhaustive shapes cover diagonal separation, holes, bridges, and row-overlap merging.
    for bits in range(1 << 9):
        frame = pd.DataFrame(
            [
                ["value" if bits & (1 << (row * 3 + col)) else None for col in range(3)]
                for row in range(3)
            ]
        )
        actual = list(_ConnectedComponents(frame))
        expected = _legacy_xlsx_components(frame)
        assert [c._cell_coordinate_set for c in actual] == [
            c._cell_coordinate_set for c in expected
        ], bits


@pytest.mark.parametrize("include_header", [False, True])
@pytest.mark.parametrize("infer_table_structure", [False, True])
def test_sparse_xlsx_serialized_output_matches_legacy(
    tmp_path, monkeypatch, include_header, infer_table_structure
):
    rng = np.random.default_rng(4357)
    path = tmp_path / "compatibility.xlsx"
    with pd.ExcelWriter(path) as writer:
        for index, density in enumerate([0.0, 0.05, 0.3, 0.7, 1.0]):
            values = rng.choice([None, "", "text", 0, False, 3.5], size=(12, 9))
            values[rng.random((12, 9)) > density] = None
            pd.DataFrame(values).to_excel(
                writer, sheet_name=f"case{index}", index=False, header=False
            )
    kwargs = {"include_header": include_header, "infer_table_structure": infer_table_structure}
    actual = [element.to_dict() for element in partition_xlsx(str(path), **kwargs)]
    monkeypatch.setattr(
        _ConnectedComponents,
        "_connected_components",
        property(lambda self: _legacy_xlsx_components(self._worksheet_df)),
    )
    expected = [element.to_dict() for element in partition_xlsx(str(path), **kwargs)]
    assert actual == expected


@pytest.mark.parametrize(
    "filename",
    [
        "stanley-cups.xlsx",
        "emoji.xlsx",
        "empty.xlsx",
        "more-than-1k-cells.xlsx",
        "xlsx-subtable-cases.xlsx",
        "language-docs/eng_spa.xlsx",
    ],
)
def test_sparse_xlsx_existing_workbook_output_matches_legacy(filename, monkeypatch):
    path = str(Path("example-docs") / filename)
    actual = [element.to_dict() for element in partition_xlsx(path)]
    monkeypatch.setattr(
        _ConnectedComponents,
        "_connected_components",
        property(lambda self: _legacy_xlsx_components(self._worksheet_df)),
    )
    expected = [element.to_dict() for element in partition_xlsx(path)]
    assert actual == expected


# ------------------------------------------------------------------------------------------------
# MODULE-LEVEL FIXTURES
# ------------------------------------------------------------------------------------------------


def _write_xlsx(tmp_path: Path, sheets: dict[str, dict[tuple[int, int], Any]]) -> str:
    """Write an XLSX file with the `{(row, col): value}` cells (1-based) of each named worksheet."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)  # pyright: ignore[reportArgumentType]
    for sheet_name, cells in sheets.items():
        worksheet = workbook.create_sheet(sheet_name)
        for (row, col), value in cells.items():
            worksheet.cell(row, col, value)
    file_path = str(tmp_path / "workbook.xlsx")
    workbook.save(file_path)
    return file_path
