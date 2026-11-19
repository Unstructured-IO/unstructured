from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.metrics.table.table_extraction import (
    deckerd_table_to_html,
    html_table_to_deckerd,
)


@pytest.mark.parametrize(("colspan", "rowspan"), [(3, 1), (1, 2), (2, 3), (3, 2), (1, 1), (2, 2)])
def test_header_row_extent_comes_from_height_not_width(colspan, rowspan):
    cells = [{"x": 0, "y": 0, "w": colspan, "h": rowspan, "content": "Header"}]
    for row in range(5):
        for col in range(4):
            if row < rowspan and col < colspan:
                continue
            cells.append({"x": col, "y": row, "w": 1, "h": 1, "content": f"r{row}c{col}"})
    original = deepcopy(cells)

    soup = BeautifulSoup(deckerd_table_to_html(cells), "html.parser")

    header_rows = soup.thead.find_all("tr", recursive=False)
    body_rows = soup.tbody.find_all("tr", recursive=False)
    assert len(header_rows) == rowspan
    assert len(body_rows) == 5 - rowspan
    assert len(soup.find_all(["th", "td"])) == len(cells)
    assert soup.th.get("colspan", "1") == str(colspan)
    assert soup.th.get("rowspan", "1") == str(rowspan)
    assert f"r{rowspan}c0" in body_rows[0].get_text()
    assert cells == original


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("spans", "row_count", "missing_cells", "header_row_count"),
    [
        ([(0, 0, 4, 2), (4, 0, 1, 1), (4, 1, 1, 3)], 5, {(0, 3)}, 4),
        ([(0, 0, 2, 2), (2, 1, 1, 2), (3, 2, 1, 2), (4, 3, 1, 2)], 7, set(), 5),
        ([(2, 1, 1, 3)], 5, set(), 1),
    ],
    ids=["sparse-staggered-header", "chained-header-spans", "body-span-stays-in-body"],
)
def test_header_spans_preserve_row_order_and_spans_on_reimport(
    reverse, spans, row_count, missing_cells, header_row_count
):
    cells = [
        {"x": x, "y": y, "w": width, "h": height, "content": f"r{y}c{x}"}
        for x, y, width, height in spans
    ]
    covered = {
        (col, row)
        for x, y, width, height in spans
        for row in range(y, y + height)
        for col in range(x, x + width)
    }
    excluded = covered | missing_cells
    cells.extend(
        {"x": col, "y": row, "w": 1, "h": 1, "content": f"r{row}c{col}"}
        for row in range(row_count)
        for col in range(5)
        if (col, row) not in excluded
    )
    if reverse:
        cells.reverse()
    original = deepcopy(cells)

    html = deckerd_table_to_html(cells)
    soup = BeautifulSoup(html, "html.parser")

    assert len(soup.thead.find_all("tr", recursive=False)) == header_row_count
    assert len(soup.tbody.find_all("tr", recursive=False)) == row_count - header_row_count
    row_labels = []
    for row in soup.table.find_all("tr"):
        contents = [cell.get_text() for cell in row.find_all(["th", "td"]) if cell.get_text()]
        row_labels.append({int(text[1:].split("c")[0]) for text in contents})
    assert row_labels == [{row} for row in range(row_count)]
    round_trip = {
        cell["content"]: (cell["y"], cell["w"], cell["h"])
        for cell in html_table_to_deckerd(html)
        if cell["content"]
    }
    assert round_trip == {cell["content"]: (cell["y"], cell["w"], cell["h"]) for cell in cells}
    assert cells == original
