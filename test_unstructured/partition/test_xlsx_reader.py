import io

import openpyxl
import pytest

from unstructured.errors import UnprocessableEntityError
from unstructured.partition.xlsx import open_excel_workbook


def workbook_bytes():
    book = openpyxl.Workbook()
    book.active["A1"] = "first"
    book.active["Z1000000"] = "far"
    book.create_sheet("second")["A1"] = "second"
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def test_compaction_and_sheet_order():
    with open_excel_workbook(workbook_bytes(), compact_empty_rows=True) as reader:
        assert reader.sheet_names == ["Sheet", "second"]
        first = reader.parse("Sheet")
        assert first.shape == (3, 26)
        assert first.iloc[-1, -1] == "far"
        assert reader.parse("second").iloc[0, 0] == "second"


def test_guard_before_dense_read():
    with pytest.raises(UnprocessableEntityError, match="XLSX_MAX_CELLS"):
        with open_excel_workbook(workbook_bytes()):
            pytest.fail("oversized workbook was opened")


def test_reader_closed_after_consumer_failure(monkeypatch):
    from unstructured.partition import xlsx

    closed = []
    original = xlsx._RowCompactingOpenpyxlReader.close

    def close(reader):
        closed.append(True)
        original(reader)

    monkeypatch.setattr(xlsx._RowCompactingOpenpyxlReader, "close", close)
    with pytest.raises(RuntimeError, match="consumer"):
        with open_excel_workbook(workbook_bytes(), compact_empty_rows=True):
            raise RuntimeError("consumer")
    assert closed
