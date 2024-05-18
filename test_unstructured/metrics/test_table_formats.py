import pytest

from unstructured.metrics.table.table_formats import SimpleTableCell


@pytest.mark.parametrize(
    ("row_nums", "column_nums", "x", "y", "w", "h"),
    [
        ([3, 2, 1], [6, 7], 6, 1, 2, 3),
        ([2], [6, 7], 6, 2, 2, 1),
        ([1, 2, 3], [20], 20, 1, 1, 3),
        ([5], [5], 5, 5, 1, 1),
    ],
)
def test_simple_table_cell_parsing_from_table_transformer_when_expected_input(
    row_nums, column_nums, x, y, w, h
):
    table_transformer_cell = {"row_nums": row_nums, "column_nums": column_nums, "cell text": "text"}
    transformed_cell = SimpleTableCell.from_table_transformer_cell(table_transformer_cell)
    expected_cell = SimpleTableCell(x=x, y=y, w=w, h=h, content="text")
    assert expected_cell == transformed_cell


def test_simple_table_cell_parsing_from_table_transformer_when_missing_row_nums():
    cell = {"row_nums": [], "column_nums": [1], "cell text": "text"}
    with pytest.raises(ValueError, match='has missing values under "row_nums" key'):
        SimpleTableCell.from_table_transformer_cell(cell)


def test_simple_table_cell_parsing_from_table_transformer_when_missing_column_nums():
    cell = {"row_nums": [1], "column_nums": [], "cell text": "text"}
    with pytest.raises(ValueError, match='has missing values under "column_nums" key'):
        SimpleTableCell.from_table_transformer_cell(cell)
