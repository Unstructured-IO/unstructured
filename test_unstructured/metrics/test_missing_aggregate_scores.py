import io
import statistics

import pandas as pd
import pytest

from unstructured.metrics.utils import _mean, _pstdev, _stdev, _write_to_file


@pytest.mark.parametrize(
    ("aggregate", "expected"),
    [(_mean, 0.7), (_stdev, round(statistics.stdev([0.8, 0.6]), 3)), (_pstdev, 0.1)],
)
@pytest.mark.parametrize("missing", [float("nan"), pd.NA, None])
def test_statistics_ignore_missing_scores_instead_of_failing_or_poisoning_the_result(
    aggregate, expected, missing
):
    assert aggregate([0.8, missing, 0.6]) == expected


@pytest.mark.parametrize("aggregate", [_mean, _stdev, _pstdev])
def test_all_missing_group_has_no_measured_statistic(aggregate):
    assert aggregate([float("nan"), None, pd.NA]) is None


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_grouped_scores_loaded_from_tsv_can_be_aggregated_and_exported(tmp_path, dtype):
    source = pd.read_csv(
        io.StringIO("doctype\tscore\npdf\t0.8\npdf\t\npdf\t0.6\nhtml\t\n"),
        sep="\t",
    )
    source["score"] = source["score"].astype(dtype)

    grouped = source.groupby("doctype")["score"].agg([_mean, _stdev, _pstdev])
    _write_to_file(str(tmp_path), "grouped.tsv", grouped.reset_index())
    exported = pd.read_csv(tmp_path / "grouped.tsv", sep="\t").set_index("doctype")

    assert exported.loc["pdf"].tolist() == [0.7, 0.141, 0.1]
    assert exported.loc["html"].isna().all()


@pytest.mark.parametrize("aggregate", [_mean, _stdev, _pstdev])
def test_valid_zero_scores_remain_in_the_aggregation(aggregate):
    assert aggregate([0.0, float("nan"), 1.0]) == aggregate([0.0, 1.0])
