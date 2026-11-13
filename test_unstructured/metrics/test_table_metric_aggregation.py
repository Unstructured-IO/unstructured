import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from unstructured.metrics.evaluate import AGG_HEADERS, TableStructureMetricsCalculator


def _write_tables(documents, references, name, actual, predicted):
    reference = [
        {"type": "Table", "text": [{"x": 0, "y": 0, "w": 1, "h": 1, "content": text}]}
        for text in actual
    ]
    prediction = [
        {"type": "Table", "metadata": {"text_as_html": f"<table><tr><td>{text}</td></tr></table>"}}
        for text in predicted
    ]
    (documents / name).write_text(json.dumps(prediction), encoding="utf-8")
    (references / name).write_text(json.dumps(reference), encoding="utf-8")


def _calculate(tmp_path, documents, references, **options):
    calculator = TableStructureMetricsCalculator(documents, references, **options)
    export_dir = tmp_path / "reports"
    with ThreadPoolExecutor(max_workers=1) as executor:
        rows = calculator.calculate(
            executor=executor,
            export_dir=export_dir,
            visualize_progress=False,
            display_agg_df=False,
        )
    aggregate = pd.read_csv(export_dir / calculator.default_agg_tsv_name, sep="\t")
    assert set(aggregate.columns) == set(AGG_HEADERS)
    return rows, aggregate.set_index("metric")


@pytest.fixture
def table_directories(tmp_path):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    documents.mkdir()
    references.mkdir()
    return documents, references


@pytest.mark.parametrize("weighted_average", [True, False])
@pytest.mark.parametrize("include_false_positives", [True, False])
def test_table_aggregate_honors_averaging_policy_and_metric_eligibility(
    tmp_path, table_directories, weighted_average, include_false_positives
):
    documents, references = table_directories
    _write_tables(documents, references, "misses.pdf.json", ["one", "two", "three"], [])
    _write_tables(documents, references, "match.pdf.json", ["matched"], ["matched"])
    _write_tables(documents, references, "false-positive.pdf.json", [], ["extra"])

    rows, aggregate = _calculate(
        tmp_path,
        documents,
        references,
        weighted_average=weighted_average,
        include_false_positives=include_false_positives,
    )

    assert len(rows) == 3
    eligible_count = 3 if include_false_positives else 2
    denominator = (4 if weighted_average else 2) + int(include_false_positives)
    assert aggregate.loc["table_level_acc", "average"] == pytest.approx(round(1 / denominator, 3))
    assert aggregate.loc["table_level_acc", "count"] == eligible_count
    assert aggregate.loc["total_tables", "average"] == pytest.approx(4 / eligible_count)
    for metric in aggregate.index.difference(["total_tables", "table_level_acc"]):
        assert aggregate.loc[metric, "average"] == (0.25 if weighted_average else 0.5)
        assert aggregate.loc[metric, "count"] == 2
        assert aggregate.loc[metric, "population_sd"] == 0.5


@pytest.mark.parametrize("weighted_average", [True, False])
@pytest.mark.parametrize("include_false_positives", [True, False])
def test_false_positive_only_dataset_exports_defined_metrics_without_zero_weight_errors(
    tmp_path, table_directories, weighted_average, include_false_positives
):
    documents, references = table_directories
    _write_tables(documents, references, "extra.pdf.json", [], ["unexpected"])

    rows, aggregate = _calculate(
        tmp_path,
        documents,
        references,
        weighted_average=weighted_average,
        include_false_positives=include_false_positives,
    )

    assert len(rows) == 1
    for metric in aggregate.index:
        if include_false_positives and metric in ("total_tables", "table_level_acc"):
            assert aggregate.loc[metric, "average"] == 0
            assert aggregate.loc[metric, "count"] == 1
        else:
            assert pd.isna(aggregate.loc[metric, "average"])
            assert aggregate.loc[metric, "count"] == 0


@pytest.mark.parametrize("weighted_average", [True, False])
def test_no_documents_exports_named_empty_aggregate_rows(
    tmp_path, table_directories, weighted_average
):
    rows, aggregate = _calculate(tmp_path, *table_directories, weighted_average=weighted_average)

    assert rows.empty
    assert aggregate["average"].isna().all()
    assert aggregate["count"].eq(0).all()
