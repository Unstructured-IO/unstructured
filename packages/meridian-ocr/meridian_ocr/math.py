"""a lightweight module that provides helpers to common math operations"""

import numpy as np

FLOAT_EPSILON = np.finfo(float).eps


def safe_division(a, b) -> float:
    """a safer division to avoid division by zero when b == 0

    returns a/b or a/FLOAT_EPSILON (should be around 2.2E-16) when b == 0

    Parameters:
    - a (int/float): a in a/b
    - b (int/float): b in a/b

    Returns:
    float: a/b or a/FLOAT_EPSILON (should be around 2.2E-16) when b == 0
    """
    return a / max(b, FLOAT_EPSILON)
