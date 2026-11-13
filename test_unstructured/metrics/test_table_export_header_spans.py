from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.metrics.table.table_extraction import deckerd_table_to_html


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
