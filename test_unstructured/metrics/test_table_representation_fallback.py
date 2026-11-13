from copy import deepcopy

import pytest

from unstructured.metrics.table.table_eval import TableEvalProcessor
from unstructured.metrics.table.table_extraction import (
    extract_and_convert_tables_from_prediction,
)


@pytest.mark.parametrize("source_type", ["html", "cells"])
@pytest.mark.parametrize("preferred_state", ["missing", "null", "empty"])
def test_table_evaluation_uses_the_other_representation_when_preferred_is_empty(
    source_type, preferred_state
):
    cells = [{"x": 0, "y": 0, "w": 1, "h": 1, "content": "Revenue"}]
    metadata = {
        "text_as_html": "<table><tr><td>Revenue</td></tr></table>",
        "table_as_cells": cells,
    }
    preferred_key = "text_as_html" if source_type == "html" else "table_as_cells"
    if preferred_state == "missing":
        metadata.pop(preferred_key)
    elif preferred_state == "null":
        metadata[preferred_key] = None
    else:
        metadata[preferred_key] = "" if source_type == "html" else []
    prediction = [{"type": "Table", "metadata": metadata}]
    original = deepcopy(prediction)

    result = TableEvalProcessor(
        prediction, [{"type": "Table", "text": cells}], source_type=source_type
    ).process_file()

    assert result.total_predicted_tables == 1
    assert result.table_detection_recall == 1.0
    assert result.table_detection_precision == 1.0
    assert result.table_level_acc == 1.0
    assert result.element_row_level_index_acc == 1.0
    assert result.element_col_level_index_acc == 1.0
    assert prediction == original


@pytest.mark.parametrize("source_type", ["html", "cells"])
def test_table_evaluation_keeps_the_selected_representation_when_both_are_present(source_type):
    prediction = [
        {
            "type": "Table",
            "metadata": {
                "text_as_html": "<table><tr><td>HTML content</td></tr></table>",
                "table_as_cells": [{"x": 0, "y": 0, "w": 1, "h": 1, "content": "Cell content"}],
            },
        }
    ]

    tables = extract_and_convert_tables_from_prediction(prediction, source_type=source_type)

    assert tables == [
        [
            {
                "row_index": 0,
                "col_index": 0,
                "content": "HTML content" if source_type == "html" else "Cell content",
            }
        ]
    ]


@pytest.mark.parametrize("source_type", ["html", "cells"])
def test_table_evaluation_without_either_representation_still_returns_no_tables(source_type):
    assert (
        extract_and_convert_tables_from_prediction(
            [{"type": "Table", "metadata": {}}], source_type=source_type
        )
        == []
    )
