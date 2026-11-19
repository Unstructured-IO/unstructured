import pytest

from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.table.table_extraction import html_table_to_deckerd

NESTED_TABLES = [
    ("<table><tr><td>inner</td></tr></table>", "inner"),
    (
        "<table><tbody><tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr></tbody></table>",
        "ABCD",
    ),
    (
        "<table><tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>",
        "outerinner",
    ),
    (
        "<table><tr><th colspan='2'>header</th></tr><tr><td>A</td><td>B</td></tr></table>",
        "headerAB",
    ),
]


def _outer_table(nested_html, nested_text):
    html = (
        "<table><thead><tr><th>Heading</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>entry</td><td>prefix{nested_html}suffix</td></tr>"
        "<tr><td>tail</td><td>end</td></tr></tbody></table>"
    )
    values = [["Heading", "Value"], ["entry", f"prefix{nested_text}suffix"], ["tail", "end"]]
    cells = [
        {"x": x, "y": y, "w": 1, "h": 1, "content": content}
        for y, row in enumerate(values)
        for x, content in enumerate(row)
    ]
    return html, cells


@pytest.mark.parametrize(("nested_html", "nested_text"), NESTED_TABLES)
def test_nested_table_text_belongs_to_one_outer_cell(nested_html, nested_text):
    html, expected = _outer_table(nested_html, nested_text)

    assert html_table_to_deckerd(html) == expected


@pytest.mark.parametrize(("nested_html", "nested_text"), NESTED_TABLES)
def test_nested_table_does_not_create_phantom_rows_or_columns_in_evaluation(
    nested_html, nested_text
):
    html, expected = _outer_table(nested_html, nested_text)
    report = TableEvalProcessor(
        prediction=[{"type": "Table", "metadata": {"text_as_html": html}}],
        ground_truth=[{"type": "Table", "text": expected}],
    ).process_file()

    assert report.total_tables == report.total_predicted_tables == 1
    assert report.table_level_acc == 1
    assert report.element_col_level_index_acc == 1
    assert report.element_row_level_index_acc == 1
    assert report.element_col_level_content_acc == 1
    assert report.element_row_level_content_acc == 1


@pytest.mark.parametrize("section", ["", "tbody", "tfoot"])
def test_ordinary_table_sections_and_inline_text_are_preserved(section):
    rows = "<tr><td>a<b>b</b></td><td>c</td></tr>"
    if section:
        rows = f"<{section}>{rows}</{section}>"

    assert html_table_to_deckerd(f"<table>{rows}</table>") == [
        {"x": 0, "y": 0, "w": 1, "h": 1, "content": "ab"},
        {"x": 1, "y": 0, "w": 1, "h": 1, "content": "c"},
    ]
