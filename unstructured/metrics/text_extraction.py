from typing import Tuple

from rapidfuzz.distance import Levenshtein


def calculate_edit_distance(
    output: str,
    source: str,
    weights: Tuple[int, int, int] = (2, 1, 1),
    return_as: str = "score",
) -> float:
    """
    Calculates edit distance using Levenshtein distance between two strings.

    Args:
        output (str): The target string to be compared.
        source (str): The reference string against which 'output' is compared.
        weights (Tuple[int, int, int], optional): A tuple containing weights
            for insertion, deletion, and substitution operations in the edit
            distance calculation. Default is (2, 1, 1).
        return_as (str, optional): The type of result to return, one of
            ["score", "percentage", "distance"].
            Default is "score".

    Returns:
        float: The calculated edit distance or similarity score between
            the 'output' and 'source' strings.

    Raises:
        ValueError: If 'return_as' is not one of the valid return types
        ["score", "percentage", "distance"].

    Note:
        This function calculates the edit distance (or similarity score) between
        two strings using the Levenshtein distance algorithm. The 'weights' parameter
        allows customizing the cost of insertion, deletion, and substitution
        operations. The 'return_as' parameter determines the type of result to return:
        - "score": Returns the similarity score, where 1.0 indicates a perfect match.
        - "percentage": Returns the normalized edit distance as a percentage.
        - "distance": Returns the raw edit distance value.

    """
    return_types = ["score", "percentage", "distance"]
    if return_as not in return_types:
        raise ValueError("Invalid return value type. Expected one of: %s" % return_types)
    distance = Levenshtein.distance(output, source, weights=weights)
    char_len = len(source)
    bounded_percentage_distance = min(max(distance / char_len, 0.0), 1.0)
    if return_as == "score":
        return 1 - bounded_percentage_distance
    elif return_as == "percentage":
        return bounded_percentage_distance
    elif return_as == "distance":
        return distance
    return 0.0
