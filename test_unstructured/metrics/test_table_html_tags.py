import pytest

from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.table.table_extraction import extract_cells_from_text_as_html


@pytest.mark.parametrize(
    ("opening", "closing"),
    [
        ("<table>", "</table>"),
        ('<table class="dataframe">', "</table>"),
        ('<table border="1" style="width:100%">', "</table>"),
        ("<table >", "</table>"),
        ("<table\n>", "</table>"),
        ("<TABLE>", "</TABLE>"),
        ('<TaBlE class="report">', "</TaBlE>"),
    ],
)
def test_evaluation_accepts_valid_html_table_opening_tags(opening, closing):
    prediction = [
        {
            "type": "Table",
            "metadata": {"text_as_html": f"{opening}<tr><td>Revenue</td><td>42</td></tr>{closing}"},
        }
    ]
    ground_truth = [
        {
            "type": "Table",
            "text": [
                {"x": 0, "y": 0, "w": 1, "h": 1, "content": "Revenue"},
                {"x": 1, "y": 0, "w": 1, "h": 1, "content": "42"},
            ],
        }
    ]

    result = TableEvalProcessor(prediction, ground_truth).process_file()

    assert result.total_predicted_tables == 1
    assert result.table_detection_recall == 1.0
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0


@pytest.mark.parametrize("html", [None, "", "<p>not a table</p>", "&lt;table&gt;"])
def test_non_table_html_is_still_not_a_prediction(html):
    assert extract_cells_from_text_as_html({"metadata": {"text_as_html": html}}) is None
