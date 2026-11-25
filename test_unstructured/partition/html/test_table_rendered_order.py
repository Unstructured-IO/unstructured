import pytest

from unstructured.common.html_table import HtmlTable
from unstructured.partition.html import partition_html


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "<tfoot><tr><td>Footer</td></tr></tfoot>"
            "<tbody><tr><td>Body</td></tr></tbody>"
            "<thead><tr><th>Header</th></tr></thead>",
            "Header Body Footer",
        ),
        (
            "<tfoot><tr><td>Footer</td></tr></tfoot>"
            "<tr><td>First</td></tr><tbody><tr><td>Second</td></tr></tbody>",
            "First Second Footer",
        ),
        (
            "<tfoot><tr><td>Footer</td></tr></tfoot>"
            "<tfoot><tr><td>Extra footer</td></tr></tfoot>"
            "<tbody><tr><td>Body</td></tr></tbody>"
            "<thead><tr><th>Header</th></tr></thead>"
            "<thead><tr><th>Extra header</th></tr></thead>",
            "Header Extra footer Body Extra header Footer",
        ),
        ("<tbody><tr><td>First</td></tr><tr><td>Second</td></tr></tbody>", "First Second"),
    ],
)
def test_partition_and_chunking_table_reader_follow_rendered_row_group_order(body, expected):
    html = f"<table>{body}</table>"

    element = partition_html(text=html, languages=["eng"])[0]
    compact = HtmlTable.from_html_text(html)

    assert element.text == expected
    assert compact.text == expected
    assert " ".join(" ".join(row.iter_cell_texts()) for row in compact.iter_rows()) == expected


def test_source_rows_and_header_flags_remain_aligned_after_ordering():
    table = HtmlTable.from_html_text(
        '<table><tfoot><tr><td data-id="f">Foot</td></tr></tfoot>'
        '<tbody><tr><td rowspan="0">Body</td></tr></tbody>'
        '<thead><tr><th scope="col">Head</th></tr></thead></table>'
    )
    rows = list(table.iter_rows())

    assert [list(row.iter_cell_texts()) for row in rows] == [["Head"], ["Body"], ["Foot"]]
    assert [row.is_header for row in rows] == [True, False, False]
    assert [row.row_group_key.tag for row in rows] == ["thead", "tbody", "tfoot"]
    assert 'scope="col"' in rows[0].source_html
    assert 'rowspan="0"' in rows[1].html
    assert 'data-id="f"' in rows[2].source_html


def test_nested_table_order_is_normalized_without_moving_rows_between_tables():
    html = (
        "<table><tbody><tr><td>Outer <table>"
        "<tfoot><tr><td>Inner footer</td></tr></tfoot>"
        "<tbody><tr><td>Inner body</td></tr></tbody>"
        "</table></td></tr></tbody></table>"
    )
    table = HtmlTable.from_html_text(html)

    assert table.text == "Outer Inner body Inner footer"
    assert len(list(table.iter_rows())) == 1
    assert partition_html(text=html, languages=["eng"])[0].text == table.text
