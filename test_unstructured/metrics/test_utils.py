import builtins

import pytest

from unstructured.metrics.utils import (
    _mean,
    _pstdev,
    _read_text_file,
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


@pytest.mark.parametrize(
    ("stat", "scores", "expected"),
    [
        (_mean, [1.4, 1.6], 2),
        (_stdev, [1, 2, 3], 1),
        # stdev([1,2,3]) is already exactly 1.0, so use a raw stdev that differs
        # from its integer rounding to prove rounding=0 is not ignored.
        (_stdev, [1, 2, 4], 2),
        (_pstdev, [1, 2, 3], 1),
    ],
)
def test_rounding_zero_rounds_to_integer(stat, scores, expected):
    """rounding=0 is a documented-valid value: round to integer, not 'no rounding'."""
    assert stat(scores, rounding=0) == expected


def test_rounding_default_and_none_preserve_unrounded_behavior():
    """Controls: rounding=3 rounds to 3 dp; rounding=None returns the raw value."""
    assert _mean([1.4, 1.6], rounding=3) == 1.5
    assert _mean([1.4, 1.6], rounding=None) == 1.5
    assert _stdev([1, 2, 3], rounding=3) == 1.0
    assert _stdev([1, 2, 3], rounding=None) == 1.0
    assert _pstdev([1, 2, 3], rounding=3) == 0.816
    assert _pstdev([1, 2, 3], rounding=None) == 0.816496580927726


def test_read_text_file_decodes_utf8_regardless_of_locale(tmp_path, monkeypatch):
    """Ground truths are decoded as UTF-8, like the JSON output they are scored against.

    `open()` without an `encoding` falls back to the locale encoding, which is cp1252 on most
    Windows machines. The patched `open` makes cp1252 that fallback on every platform.
    """
    text = "It’s a café — “naïve” résumé. 中文"
    ground_truth = tmp_path / "doc.pdf.txt"
    ground_truth.write_text(text, encoding="utf-8")

    def open_with_cp1252_default(file, mode="r", *args, encoding=None, **kwargs):
        return builtins.open(file, mode, *args, encoding=encoding or "cp1252", **kwargs)

    monkeypatch.setattr("unstructured.metrics.utils.open", open_with_cp1252_default, raising=False)

    assert _read_text_file(ground_truth) == text
