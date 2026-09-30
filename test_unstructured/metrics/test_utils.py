import pytest

from unstructured.metrics.utils import (
    _mean,
    _pstdev,
    _stdev,
    _uniquity_file,
)


@pytest.mark.parametrize(
    ("numbers", "expected_mean", "expected_stdev", "expected_pstdev"),
    [
        ([2, 5, 6, 7], 5, 2.16, 1.871),
        ([1, 100], 50.5, 70.004, 49.5),
        ([1], 1, None, None),
        ([], None, None, None),
    ],
)
def test_stats(numbers, expected_mean, expected_stdev, expected_pstdev):
    mean = _mean(numbers)
    stdev = _stdev(numbers)
    pstdev = _pstdev(numbers)
    assert mean == expected_mean
    assert stdev == expected_stdev
    assert pstdev == expected_pstdev


@pytest.mark.parametrize(
    ("filenames"),
    [("filename.ext", "filename (1).ext", "randomfile.ext", "filename.txt", "filename (5).txt")],
)
def test_uniquity_file(filenames):
    final_filename = _uniquity_file(filenames, "filename.ext")
    assert final_filename == "filename (2).ext"


def test_mean_ignores_unmeasured_scores():
    """_mean must filter None like _stdev and _pstdev do.

    An unmeasured score is not a score; statistics.mean raises TypeError on None
    rather than ignoring it, so the helper has to drop those values itself.
    """
    assert _mean([0.9, None, 0.8]) == 0.85
    assert _mean([None, None]) is None
    assert _mean([]) is None
    assert _mean([1.0, 2.0]) == 1.5
