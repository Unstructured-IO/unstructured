import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from unstructured.metrics.evaluate import (
    ElementTypeMetricsCalculator,
    ObjectDetectionAggregatedMetricsCalculator,
    TextExtractionMetricsCalculator,
)


@pytest.fixture
def calculator_dirs(tmp_path):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    documents.mkdir()
    references.mkdir()
    content = json.dumps([{"type": "NarrativeText", "text": "hello world", "metadata": {}}])
    for name in ("first", "second"):
        (documents / f"{name}.pdf.json").write_text(content, encoding="utf-8")
        (references / f"{name}.pdf.json").write_text(content, encoding="utf-8")
        (references / f"{name}.pdf.txt").write_text("hello world", encoding="utf-8")
    return documents, references


@pytest.mark.parametrize(
    "calculator_type", [TextExtractionMetricsCalculator, ElementTypeMetricsCalculator]
)
@pytest.mark.parametrize(
    ("selection", "expected_count"), [(None, 2), ([], 0), (["first.pdf.json"], 1)]
)
def test_explicit_empty_document_selection_does_not_evaluate_discovered_files(
    calculator_dirs, calculator_type, selection, expected_count
):
    calculator = calculator_type(*calculator_dirs).on_files(document_paths=selection)

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = calculator.calculate(
            executor=executor, visualize_progress=False, display_agg_df=False
        )

    assert len(result) == expected_count


def test_unspecified_followup_selection_preserves_an_explicit_empty_selection(calculator_dirs):
    calculator = (
        ElementTypeMetricsCalculator(*calculator_dirs).on_files(document_paths=[]).on_files()
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = calculator.calculate(
            executor=executor, visualize_progress=False, display_agg_df=False
        )

    assert result.empty


@pytest.mark.parametrize(("selection", "expected_match"), [(None, True), ([], False)])
def test_explicit_empty_ground_truth_selection_clears_detection_file_matching(
    calculator_dirs, selection, expected_match
):
    calculator = ObjectDetectionAggregatedMetricsCalculator(*calculator_dirs).on_files(
        ground_truth_paths=selection
    )

    assert (calculator._find_file_in_ground_truth("first") is not None) == expected_match
