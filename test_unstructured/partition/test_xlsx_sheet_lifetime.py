import gc
import io
import weakref

import openpyxl
import pytest

from unstructured.partition import xlsx


@pytest.mark.parametrize("find_subtable", [False, True])
@pytest.mark.parametrize("include_header", [False, True])
def test_partition_releases_worksheet_frames_before_reading_next(
    monkeypatch, find_subtable, include_header
):
    workbook = openpyxl.Workbook()
    for number in range(3):
        sheet = workbook.active if number == 0 else workbook.create_sheet()
        sheet.title = f"Page {number}"
        sheet.append(["Product", "Quantity"])
        sheet.append([f"Item {number}", number + 1])
        sheet.append([f"Other {number}", number + 2])
    file = io.BytesIO()
    workbook.save(file)
    original_parse = xlsx.ExcelWorkbookReader.parse
    previous = None
    parsed = []

    def parse(reader, name, *, header=None):
        nonlocal previous
        gc.collect()
        assert previous is None or previous() is None, "previous worksheet is still resident"
        frame = original_parse(reader, name, header=header)
        previous = weakref.ref(frame)
        parsed.append(name)
        return frame

    monkeypatch.setattr(xlsx.ExcelWorkbookReader, "parse", parse)

    elements = xlsx.partition_xlsx(
        file=file,
        find_subtable=find_subtable,
        include_header=include_header,
        starting_page_number=7,
        languages=["eng"],
    )

    assert parsed == ["Page 0", "Page 1", "Page 2"]
    assert [e.metadata.page_number for e in elements] == [7, 8, 9]
    assert [e.metadata.page_name for e in elements] == parsed
    assert all(f"Item {i}" in e.text for i, e in enumerate(elements))
    assert all("<table>" in e.metadata.text_as_html for e in elements)
    gc.collect()
    assert previous() is None
