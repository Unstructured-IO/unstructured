import pytest

from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.table_structure import (
    eval_table_transformer_for_file,
    image_or_pdf_to_dataframe,
)


@pytest.mark.parametrize(
    "filename",
    [
        "example-docs/table-multi-row-column-cells.png",
        "example-docs/table-multi-row-column-cells.pdf",
    ],
)
def test_image_or_pdf_to_dataframe(filename):
    df = image_or_pdf_to_dataframe(filename)
    assert ["Blind", "5", "1", "4", "34.5%, n=1", "1199 sec, n=1"] in df.values


def test_eval_table_transformer_for_file():
    score = eval_table_transformer_for_file(
        "example-docs/table-multi-row-column-cells.png",
        "example-docs/table-multi-row-column-cells-actual.csv",
    )
    # avoid severe degradation of performance
    assert 0.8 < score < 1


def test_table_eval_processor_simple():
    prediction = [
        {
            "type": "Table",
            "metadata": {
                "text_as_html": """<table><thead><tr><th>r1c1</th><th>r1c2</th></tr></thead>
                    <tbody><tr><td>r2c1</td><td>r2c2</td></tr></tbody></table>"""
            },
        }
    ]

    ground_truth = [
        {
            "type": "Table",
            "text": [
                {
                    "id": "ee862c7a-d27e-4484-92de-4faa42a63f3b",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c1",
                },
                {
                    "id": "6237ac7b-bfc8-40d2-92f2-d138277205e2",
                    "x": 0,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c1",
                },
                {
                    "id": "9d0933a9-5984-4cad-80d9-6752bf9bc4df",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c2",
                },
                {
                    "id": "1152d043-5ead-4ab8-8b88-888d48831ac2",
                    "x": 1,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c2",
                },
            ],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth)
    result = te_processor.process_file()
    assert result.total_tables == 1
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_content_acc == 1.0
    assert result.element_col_level_content_acc == 1.0


def test_table_eval_processor_simple_when_input_as_cells():
    prediction = [
        {
            "type": "Table",
            "metadata": {
                "table_as_cells": [
                    {
                        "x": 1,
                        "y": 1,
                        "w": 1,
                        "h": 1,
                        "content": "r2c2",
                    },
                    {
                        "x": 0,
                        "y": 0,
                        "w": 1,
                        "h": 1,
                        "content": "r1c1",
                    },
                    {
                        "x": 0,
                        "y": 1,
                        "w": 1,
                        "h": 1,
                        "content": "r2c1",
                    },
                    {
                        "x": 1,
                        "y": 0,
                        "w": 1,
                        "h": 1,
                        "content": "r1c2",
                    },
                ]
            },
        }
    ]

    ground_truth = [
        {
            "type": "Table",
            "text": [
                {
                    "id": "ee862c7a-d27e-4484-92de-4faa42a63f3b",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c1",
                },
                {
                    "id": "6237ac7b-bfc8-40d2-92f2-d138277205e2",
                    "x": 0,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c1",
                },
                {
                    "id": "9d0933a9-5984-4cad-80d9-6752bf9bc4df",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c2",
                },
                {
                    "id": "1152d043-5ead-4ab8-8b88-888d48831ac2",
                    "x": 1,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c2",
                },
            ],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth, source_type="cells")
    result = te_processor.process_file()
    assert result.total_tables == 1
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_content_acc == 1.0
    assert result.element_col_level_content_acc == 1.0


def test_table_eval_processor_when_wrong_source_type():
    prediction = [
        {
            "type": "Table",
            "metadata": {"table_as_cells": []},
        }
    ]

    ground_truth = [
        {
            "type": "Table",
            "text": [],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth, source_type="wrong_type")
    with pytest.raises(ValueError):
        te_processor.process_file()


@pytest.mark.parametrize(
    "text_as_html",
    [
        """
<table>
    <thead>
        <tr>
            <th>r1c1</th>
            <th>r1c2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>r2c1</td>
            <td>r2c2</td>
        </tr>
        <tr>
            <td>r3c1</td>
            <td>r3c2</td>
        </tr>
    </tbody>
</table>
""",
        """
<table>
    <tr>
        <th>r1c1</th>
        <th>r1c2</th>
    </tr>
    <tbody>
        <tr>
            <td>r2c1</td>
            <td>r2c2</td>
        </tr>
        <tr>
            <td>r3c1</td>
            <td>r3c2</td>
        </tr>
    </tbody>
</table>
""",
        """
<table>
    </tbody>
        <tr>
            <td>r1c1</td>
            <td>r1c2</td>
        </tr>
        <tr>
            <td>r2c1</td>
            <td>r2c2</td>
        </tr>
        <tr>
            <td>r3c1</td>
            <td>r3c2</td>
        </tr>
    </tbody>
</table>
""",
    ],
)
def test_table_eval_processor_various_table_html_structures(text_as_html):
    prediction = [{"type": "Table", "metadata": {"text_as_html": text_as_html}}]

    ground_truth = [
        {
            "type": "Table",
            "text": [
                {
                    "id": "ee862c7a-d27e-4484-92de-4faa42a63f3b",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c1",
                },
                {
                    "id": "6237ac7b-bfc8-40d2-92f2-d138277205e2",
                    "x": 0,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c1",
                },
                {
                    "id": "9d0933a9-5984-4cad-80d9-6752bf9bc4df",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c2",
                },
                {
                    "id": "1152d043-5ead-4ab8-8b88-888d48831ac2",
                    "x": 1,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c2",
                },
                {
                    "id": "364f4a17-2979-4506-ae77-e8adf8e3f554",
                    "x": 0,
                    "y": 2,
                    "w": 1,
                    "h": 1,
                    "content": "r3c1",
                },
                {
                    "id": "30f87503-ac1f-4db1-b924-b316af585702",
                    "x": 1,
                    "y": 2,
                    "w": 1,
                    "h": 1,
                    "content": "r3c2",
                },
            ],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth)
    result = te_processor.process_file()
    assert result.total_tables == 1
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_content_acc == 1.0
    assert result.element_col_level_content_acc == 1.0


def test_table_eval_processor_non_str_values_in_table():
    prediction = [
        {
            "type": "Table",
            "metadata": {
                "text_as_html": """
<table>
    <thead>
        <tr>
            <th>11</th>
            <th>12</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>21</td>
            <td>22</td>
        </tr>
    </tbody>
</table>"""
            },
        }
    ]

    ground_truth = [
        {
            "type": "Table",
            "text": [
                {
                    "id": "ee862c7a-d27e-4484-92de-4faa42a63f3b",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "11",
                },
                {
                    "id": "6237ac7b-bfc8-40d2-92f2-d138277205e2",
                    "x": 0,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "21",
                },
                {
                    "id": "9d0933a9-5984-4cad-80d9-6752bf9bc4df",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "12",
                },
                {
                    "id": "1152d043-5ead-4ab8-8b88-888d48831ac2",
                    "x": 1,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "22",
                },
            ],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth)
    result = te_processor.process_file()
    assert result.total_tables == 1
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_content_acc == 1.0
    assert result.element_col_level_content_acc == 1.0


def test_table_eval_processor_merged_cells():
    prediction = [
        {
            "type": "Table",
            "metadata": {
                "text_as_html": """
<table>
    <thead>
        <tr>
            <th rowspan="2">r1c1</th>
            <th>r1c2</th>
            <th colspan="2">r1c3</th>
        </tr>
        <tr>
            <th>r2c2</th>
            <th>r2c3</th>
            <th>r2c4</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>r3c1</td>
            <td>r3c2</td>
            <td colspan="2" rowspan="2">r3c3</td>
        </tr>
        <tr>
            <td>r4c1</td>
            <td>r4c2</td>
        </tr>
    </tbody>
</table>
"""
            },
        }
    ]

    ground_truth = [
        {
            "type": "Table",
            "text": [
                {
                    "id": "f399ef57-5b88-4509-8971-9cb63246866e",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 2,
                    "content": "r1c1",
                },
                {
                    "id": "2dfdec2f-e8f3-4be7-a6ac-8ff21c4e8556",
                    "x": 0,
                    "y": 2,
                    "w": 1,
                    "h": 1,
                    "content": "r3c1",
                },
                {
                    "id": "9c771c58-88c7-49d8-9c12-85d0e44b920e",
                    "x": 0,
                    "y": 3,
                    "w": 1,
                    "h": 1,
                    "content": "r4c1",
                },
                {
                    "id": "5bd6f3f0-34c5-495b-8a28-c4ac96989ef8",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r1c2",
                },
                {
                    "id": "7b8e6bc2-a310-4dd6-997c-313f951e7f96",
                    "x": 1,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c2",
                },
                {
                    "id": "1c152ad4-12fa-4a7b-90de-a992aa6410a4",
                    "x": 1,
                    "y": 2,
                    "w": 1,
                    "h": 1,
                    "content": "r3c2",
                },
                {
                    "id": "55063f64-0003-4217-b6ca-aff5914793ff",
                    "x": 1,
                    "y": 3,
                    "w": 1,
                    "h": 1,
                    "content": "r4c2",
                },
                {
                    "id": "22852e86-0e22-4d32-b63a-9ba7dd4118a2",
                    "x": 2,
                    "y": 0,
                    "w": 2,
                    "h": 1,
                    "content": "r1c3",
                },
                {
                    "id": "eae013c5-5597-4a8b-9771-82e28c5c5cba",
                    "x": 2,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c3",
                },
                {
                    "id": "0dea3a42-8523-4d6e-9e70-d65cc2314678",
                    "x": 2,
                    "y": 2,
                    "w": 2,
                    "h": 2,
                    "content": "r3c3",
                },
                {
                    "id": "60093e2c-d3e2-4146-92b5-97a2fc16c061",
                    "x": 3,
                    "y": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r2c4",
                },
            ],
        }
    ]

    te_processor = TableEvalProcessor(prediction, ground_truth)
    result = te_processor.process_file()
    assert result.total_tables == 1
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert result.element_row_level_content_acc == 1.0
    assert result.element_col_level_content_acc == 1.0
