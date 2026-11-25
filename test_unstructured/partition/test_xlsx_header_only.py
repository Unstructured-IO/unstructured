"""Public API coverage for worksheets whose only content is their header row."""

import io

import openpyxl
import pytest

from unstructured.documents.elements import Table
from unstructured.partition.xlsx import partition_xlsx


def _workbook_bytes(rows):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Template"
    for row in rows:
        worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@pytest.mark.parametrize("headers", [["Name", "Age"], ["Heading"], ["नाम", "单价", "<value>"]])
@pytest.mark.parametrize("infer_table_structure", [False, True])
@pytest.mark.parametrize("find_subtable", [False, True])
@pytest.mark.parametrize("input_type", ["filename", "file"])
def test_header_only_worksheet_keeps_its_requested_headers(
    headers, infer_table_structure, find_subtable, input_type, tmp_path
):
    payload = _workbook_bytes([headers])
    if input_type == "filename":
        path = tmp_path / "template.xlsx"
        path.write_bytes(payload)
        source = {"filename": str(path)}
    else:
        source = {"file": io.BytesIO(payload)}

    elements = partition_xlsx(
        **source,
        include_header=True,
        find_subtable=find_subtable,
        infer_table_structure=infer_table_structure,
        starting_page_number=7,
    )

    assert len(elements) == 1
    table = elements[0]
    assert isinstance(table, Table)
    assert table.text == " ".join(headers)
    assert table.metadata.page_name == "Template"
    assert table.metadata.page_number == 7
    if infer_table_structure:
        from lxml import html

        document = html.fromstring(table.metadata.text_as_html)
        assert document.xpath("//tr/*/text()") == headers
    else:
        assert table.metadata.text_as_html is None


@pytest.mark.parametrize("include_header", [False, True])
def test_truly_empty_worksheet_still_has_no_elements(include_header):
    assert partition_xlsx(file=io.BytesIO(_workbook_bytes([])), include_header=include_header) == []


def test_header_and_data_rows_remain_a_single_table():
    elements = partition_xlsx(
        file=io.BytesIO(_workbook_bytes([["Name", "Age"], ["Alice", 30]])), include_header=True
    )

    assert len(elements) == 1
    assert isinstance(elements[0], Table)
    assert elements[0].text == "Name Age Alice 30"


def test_a_single_content_row_without_header_mode_is_retained():
    elements = partition_xlsx(
        file=io.BytesIO(_workbook_bytes([["Name", "Age"]])), include_header=False
    )

    assert len(elements) == 1
    assert isinstance(elements[0], Table)
    assert elements[0].text == "Name Age"
