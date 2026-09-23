import numpy as np
import pytest

from unstructured_inference.math import FLOAT_EPSILON, safe_division


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(0, 0, 0), (0, 1, 0), (1, 0, np.round(1 / FLOAT_EPSILON, 1)), (2, 3, 0.7)],
)
def test_safe_division(a, b, expected):
    assert np.round(safe_division(a, b), 1) == expected
