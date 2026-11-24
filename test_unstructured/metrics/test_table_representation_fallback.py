import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pandas as pd
import pytest

from unstructured.metrics.evaluate import AGG_HEADERS, TableStructureMetricsCalculator
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


@pytest.mark.parametrize("representation", ["html", "cells"])
@pytest.mark.parametrize("weighted_average", [True, False])
@pytest.mark.parametrize("include_false_positives", [True, False])
def test_false_positive_fallback_tables_survive_calculation_and_export(
    tmp_path, representation, weighted_average, include_false_positives
):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    documents.mkdir()
    references.mkdir()
    prediction = []
    for content in ["Revenue 100", "Expenses 50"]:
        metadata = (
            {"text_as_html": f"<table><tr><td>{content}</td></tr></table>"}
            if representation == "html"
            else {"table_as_cells": [{"x": 0, "y": 0, "w": 1, "h": 1, "content": content}]}
        )
        prediction.append({"type": "Table", "metadata": metadata})
    prediction_file = documents / "no-tables.pdf.json"
    reference_file = references / prediction_file.name
    prediction_file.write_text(json.dumps(prediction), encoding="utf-8")
    reference_file.write_text("[]", encoding="utf-8")
    original_bytes = (prediction_file.read_bytes(), reference_file.read_bytes())

    calculator = TableStructureMetricsCalculator(
        documents,
        references,
        weighted_average=weighted_average,
        include_false_positives=include_false_positives,
    )
    exports = tmp_path / "reports"
    with ThreadPoolExecutor(max_workers=1) as executor:
        rows = calculator.calculate(
            executor=executor,
            export_dir=exports,
            visualize_progress=False,
            display_agg_df=False,
        )

    assert len(rows) == 1
    assert rows.iloc[0]["total_predicted_tables"] == 2
    assert rows.iloc[0]["total_tables"] == 0
    assert rows.iloc[0]["table_detection_precision"] == 0
    exported_rows = pd.read_csv(exports / calculator.default_tsv_name, sep="\t")
    assert exported_rows["total_predicted_tables"].tolist() == [2]
    aggregate = pd.read_csv(exports / calculator.default_agg_tsv_name, sep="\t")
    assert set(aggregate.columns) == set(AGG_HEADERS)
    for metric, row in aggregate.set_index("metric").iterrows():
        if include_false_positives and metric in ("total_tables", "table_level_acc"):
            assert row["average"] == 0
            assert row["count"] == 1
        else:
            assert pd.isna(row["average"])
            assert row["count"] == 0
    assert (prediction_file.read_bytes(), reference_file.read_bytes()) == original_bytes
