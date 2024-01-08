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
