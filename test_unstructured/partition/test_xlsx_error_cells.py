import io

import openpyxl
import pandas as pd
import pytest

from unstructured.partition.xlsx import open_excel_workbook, partition_xlsx


@pytest.mark.parametrize("find_subtable", [False, True])
@pytest.mark.parametrize(
    "error", ["#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A"]
)
def test_excel_error_cells_remain_visible_in_text_and_html(find_subtable, error):
    book = openpyxl.Workbook()
    book.active.append(["Check", "Result"])
    book.active.append(["Calculation", error])
    assert book.active["B2"].data_type == "e"
    file = io.BytesIO()
    book.save(file)

    elements = partition_xlsx(
        file=file, find_subtable=find_subtable, include_cell_errors=True, languages=["eng"]
    )

    assert len(elements) == 1
    assert error in elements[0].text
    assert f"<td>{error}</td>" in elements[0].metadata.text_as_html


def test_error_only_sheet_is_not_discarded_as_empty():
    book = openpyxl.Workbook()
    book.active["A1"] = "#REF!"
    file = io.BytesIO()
    book.save(file)

    assert [
        element.text
        for element in partition_xlsx(file=file, include_cell_errors=True, languages=["eng"])
    ] == ["#REF!"]


@pytest.mark.parametrize("compact", [False, True])
def test_reader_preserves_error_text_without_changing_blank_numeric_or_boolean_cells(compact):
    book = openpyxl.Workbook()
    book.active.append(["#DIV/0!", None, 3.5, True, "NA"])
    file = io.BytesIO()
    book.save(file)

    with open_excel_workbook(
        file.getvalue(), compact_empty_rows=compact, preserve_error_cells=True
    ) as reader:
        frame = reader.parse("Sheet")

    assert frame.iloc[0, 0] == "#DIV/0!"
    assert pd.isna(frame.iloc[0, 1])
    assert frame.iloc[0, 2] == 3.5
    assert bool(frame.iloc[0, 3]) is True
    assert frame.iloc[0, 4] == "NA"
