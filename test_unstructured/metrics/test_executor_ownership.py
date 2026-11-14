import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from unstructured.metrics.evaluate import (
    ElementTypeMetricsCalculator,
    TextExtractionMetricsCalculator,
)


@pytest.fixture
def calculator_dirs(tmp_path):
    documents = tmp_path / "documents"
    references = tmp_path / "references"
    documents.mkdir()
    references.mkdir()
    content = json.dumps([{"type": "NarrativeText", "text": "hello world", "metadata": {}}])
    (documents / "sample.pdf.json").write_text(content, encoding="utf-8")
    (references / "sample.pdf.json").write_text(content, encoding="utf-8")
    (references / "sample.pdf.txt").write_text("hello world", encoding="utf-8")
    return documents, references


@pytest.mark.parametrize(
    "calculator_type", [ElementTypeMetricsCalculator, TextExtractionMetricsCalculator]
)
def test_caller_can_reuse_executor_after_calculation(calculator_dirs, calculator_type):
    calculator = calculator_type(*calculator_dirs)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = calculator.calculate(
            executor=executor, visualize_progress=False, display_agg_df=False
        )

        assert len(first) == 1
        assert executor.submit(lambda: "still available").result() == "still available"
        second = calculator.calculate(
            executor=executor, visualize_progress=False, display_agg_df=False
        )
        pd.testing.assert_frame_equal(first, second)


class _FailingMapExecutor(ThreadPoolExecutor):
    def map(self, *args, **kwargs):
        raise RuntimeError("map failed")


@pytest.mark.parametrize("failure_stage", ["map", "dataframe"])
def test_caller_executor_stays_available_after_calculation_failure(
    calculator_dirs, mocker, failure_stage
):
    calculator = ElementTypeMetricsCalculator(*calculator_dirs)
    executor_type = _FailingMapExecutor if failure_stage == "map" else ThreadPoolExecutor
    if failure_stage == "dataframe":
        mocker.patch.object(
            calculator, "_generate_dataframes", side_effect=RuntimeError("dataframe failed")
        )

    with executor_type(max_workers=1) as executor:
        with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
            calculator.calculate(executor=executor, visualize_progress=False, display_agg_df=False)

        assert executor.submit(lambda: "still available").result() == "still available"


@pytest.mark.parametrize("failure_stage", [None, "map", "dataframe"])
def test_calculator_closes_its_own_executor_on_success_or_failure(
    calculator_dirs, mocker, failure_stage
):
    calculator = ElementTypeMetricsCalculator(*calculator_dirs)
    executor_type = _FailingMapExecutor if failure_stage == "map" else ThreadPoolExecutor
    owned_executor = executor_type(max_workers=1)
    mocker.patch.object(calculator, "_default_executor", return_value=owned_executor)
    if failure_stage == "dataframe":
        mocker.patch.object(
            calculator, "_generate_dataframes", side_effect=RuntimeError("dataframe failed")
        )

    try:
        if failure_stage:
            with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
                calculator.calculate(visualize_progress=False, display_agg_df=False)
        else:
            assert len(calculator.calculate(visualize_progress=False, display_agg_df=False)) == 1
        with pytest.raises(RuntimeError, match="cannot schedule new futures"):
            owned_executor.submit(lambda: None)
    finally:
        owned_executor.shutdown()
