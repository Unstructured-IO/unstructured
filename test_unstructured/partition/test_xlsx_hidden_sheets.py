import io
from unittest.mock import Mock

import openpyxl
import pytest
import xlrd

from unstructured.partition import xlsx


@pytest.mark.parametrize("find_subtable", [False, True])
def test_hidden_worksheets_can_be_skipped_without_renumbering(monkeypatch, find_subtable):
    workbook = openpyxl.Workbook()
    workbook.active.title = "Visible first"
    workbook.create_sheet("Hidden").sheet_state = "hidden"
    workbook.create_sheet("Very hidden").sheet_state = "veryHidden"
    workbook.create_sheet("Visible last")
    for sheet in workbook:
        sheet.append(["Name", "Value"])
        sheet.append([sheet.title, 1])
    file = io.BytesIO()
    workbook.save(file)
    parsed = []
    original = xlsx.ExcelWorkbookReader.parse

    def parse(reader, name, *, header=None):
        parsed.append(name)
        return original(reader, name, header=header)

    monkeypatch.setattr(xlsx.ExcelWorkbookReader, "parse", parse)

    elements = xlsx.partition_xlsx(
        file=file,
        find_subtable=find_subtable,
        include_hidden_sheets=False,
        starting_page_number=5,
        languages=["eng"],
    )

    assert parsed == ["Visible first", "Visible last"]
    assert [e.metadata.page_name for e in elements] == parsed
    assert [e.metadata.page_number for e in elements] == [5, 8]


def test_hidden_worksheets_remain_included_by_default():
    workbook = openpyxl.Workbook()
    workbook.active.append(["Public", "value"])
    hidden = workbook.create_sheet("Hidden")
    hidden.sheet_state = "hidden"
    hidden.append(["Hidden", "value"])
    file = io.BytesIO()
    workbook.save(file)

    elements = xlsx.partition_xlsx(file=file, find_subtable=False, languages=["eng"])

    assert [e.metadata.page_name for e in elements] == ["Sheet", "Hidden"]


@pytest.mark.parametrize(("visibility", "expected"), [(0, False), (1, True), (2, True)])
def test_xls_hidden_and_very_hidden_states_are_recognized(visibility, expected):
    book = Mock(spec=xlrd.book.Book)
    book.sheet_by_name.return_value.visibility = visibility
    reader = xlsx.ExcelWorkbookReader(Mock(book=book))

    assert reader.is_sheet_hidden("Legacy sheet") is expected
    book.sheet_by_name.assert_called_once_with("Legacy sheet")
