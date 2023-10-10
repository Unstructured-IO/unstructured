from typing import Dict, Tuple

from rapidfuzz.distance import Levenshtein

from unstructured.cleaners.core import clean_bullets, remove_sentence_punctuation


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
            ["score",, "distance"].
            Default is "score".

    Returns:
        float: The calculated edit distance or similarity score between
            the 'output' and 'source' strings.

    Raises:
        ValueError: If 'return_as' is not one of the valid return types
        ["score", "distance"].

    Note:
        This function calculates the edit distance (or similarity score) between
        two strings using the Levenshtein distance algorithm. The 'weights' parameter
        allows customizing the cost of insertion, deletion, and substitution
        operations. The 'return_as' parameter determines the type of result to return:
        - "score": Returns the similarity score, where 1.0 indicates a perfect match.
        - "distance": Returns the raw edit distance value.

    """
    return_types = ["score", "distance"]
    if return_as not in return_types:
        raise ValueError("Invalid return value type. Expected one of: %s" % return_types)
    distance = Levenshtein.distance(output, source, weights=weights)
    char_len = len(source)
    bounded_percentage_distance = min(max(distance / char_len, 0.0), 1.0)
    if return_as == "score":
        return 1 - bounded_percentage_distance
    elif return_as == "distance":
        return distance
    return 0.0


def bag_of_words(text: str) -> Dict[str, int]:
    bow: Dict[str, int] = {}
    incorrect_word: str = ""
    words = clean_bullets(remove_sentence_punctuation(text.lower(), ["-", "'"])).split()

    i = 0
    while i < len(words):
        if len(words[i]) > 1:
            if words[i] in bow:
                bow[words[i]] += 1
            else:
                bow[words[i]] = 1
            i += 1
        else:
            j = i
            incorrect_word = ""

            while j < len(words) and len(words[j]) == 1:
                incorrect_word += words[j]
                j += 1

            if len(incorrect_word) == 1:
                if incorrect_word in bow:
                    bow[incorrect_word] += 1
                else:
                    bow[incorrect_word] = 1
            i = j
    return bow
