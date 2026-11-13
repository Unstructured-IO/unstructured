import pytest

from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.table.table_extraction import html_table_to_deckerd

CASES = [
    (
        '<table><tr><td colspan="2">A</td><td colspan="2">B</td><td>C</td></tr></table>',
        [("A", 0, 0, 2, 1), ("B", 2, 0, 2, 1), ("C", 4, 0, 1, 1)],
    ),
    (
        '<table><tr><td rowspan="2">A</td><td>B</td><td>C</td></tr>'
        '<tr><td colspan="2">D</td></tr><tr><td>E</td><td>F</td><td>G</td></tr></table>',
        [
            ("A", 0, 0, 1, 2),
            ("B", 1, 0, 1, 1),
            ("C", 2, 0, 1, 1),
            ("D", 1, 1, 2, 1),
            ("E", 0, 2, 1, 1),
            ("F", 1, 2, 1, 1),
            ("G", 2, 2, 1, 1),
        ],
    ),
    (
        '<table><tr><td rowspan="2">A</td><td>B</td><td>C</td><td>D</td></tr>'
        '<tr><td colspan="2" rowspan="2">E</td><td>F</td></tr>'
        "<tr><td>G</td><td>H</td></tr></table>",
        [
            ("A", 0, 0, 1, 2),
            ("B", 1, 0, 1, 1),
            ("C", 2, 0, 1, 1),
            ("D", 3, 0, 1, 1),
            ("E", 1, 1, 2, 2),
            ("F", 3, 1, 1, 1),
            ("G", 0, 2, 1, 1),
            ("H", 3, 2, 1, 1),
        ],
    ),
    (
        '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>',
        [("A", 0, 0, 1, 2), ("B", 1, 0, 1, 1), ("C", 1, 1, 1, 1)],
    ),
]


@pytest.mark.parametrize(("html", "expected"), CASES)
def test_merged_cells_reserve_their_final_grid_coordinates(html, expected):
    cells = html_table_to_deckerd(html)

    assert [
        (cell["content"], cell["x"], cell["y"], cell["w"], cell["h"]) for cell in cells
    ] == expected
    occupied = set()
    for cell in cells:
        positions = {
            (row, column)
            for row in range(cell["y"], cell["y"] + cell["h"])
            for column in range(cell["x"], cell["x"] + cell["w"])
        }
        assert occupied.isdisjoint(positions)
        occupied.update(positions)


@pytest.mark.parametrize(("html", "expected"), CASES)
def test_correct_html_spans_receive_perfect_structure_scores(html, expected):
    ground_truth_cells = [
        {"content": content, "x": x, "y": y, "w": width, "h": height}
        for content, x, y, width, height in expected
    ]
    prediction = [{"type": "Table", "metadata": {"text_as_html": html}}]
    ground_truth = [{"type": "Table", "text": ground_truth_cells}]

    result = TableEvalProcessor(prediction, ground_truth).process_file()

    assert result.table_detection_f1 == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.composite_structure_acc == 1.0
