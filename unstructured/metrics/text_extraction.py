from typing import Dict, Optional, Tuple

from rapidfuzz.distance import Levenshtein

from unstructured.cleaners.core import clean_bullets, remove_sentence_punctuation


def calculate_accuracy(
    output: Optional[str],
    source: Optional[str],
    weights: Tuple[int, int, int] = (2, 1, 1),
) -> float:
    """
    Calculates accuracy by calling calculate_edit_distance function using `return_as=score`.
    The function will return complement of the edit distance instead.
    """
    return calculate_edit_distance(output, source, weights, return_as="score")


def calculate_edit_distance(
    output: Optional[str],
    source: Optional[str],
    weights: Tuple[int, int, int] = (2, 1, 1),
    return_as: str = "distance",
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
            ["score", "distance"].
            Default is "distance".

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
    output = _prepare_str(output)
    source = _prepare_str(source)
    distance = Levenshtein.distance(output, source, weights=weights)  # type: ignore
    # lower bounded the char length for source string at 1.0 because to avoid division by zero
    # in the case where source string is empty, the distance should be at 100%
    source_char_len = max(len(source), 1.0)  # type: ignore
    bounded_percentage_distance = min(max(distance / source_char_len, 0.0), 1.0)
    if return_as == "score":
        return 1 - bounded_percentage_distance
    elif return_as == "distance":
        return distance
    return 0.0


def bag_of_words(text: str) -> Dict[str, int]:
    """
    Outputs the bag of words (BOW) found in the input text and their frequencies.

    Takes "clean, concatenated text" (CCT) from a document as input.

    Removes sentence punctuation, but not punctuation within a word (ex. apostrophes).
    """
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

            if len(incorrect_word) == 1 and words[i].isalnum():
                if incorrect_word in bow:
                    bow[incorrect_word] += 1
                else:
                    bow[incorrect_word] = 1
            i = j
    return bow


def calculate_percent_missing_text(
    output: Optional[str],
    source: Optional[str],
) -> float:
    """
    Creates the bag of words (BOW) found in each input text and their frequencies, then compares the
    output BOW against the source BOW to calculate the % of text from the source text missing from
    the output text.

    Takes "clean, concatenated text" (CCT) from a document output and the ground truth source text
    as inputs.

    If the output text contains all words from the source text and then some extra, result will be
    0% missing text - this calculation does not penalize duplication.

    A spaced-out word (ex. h e l l o) is considered missing; individual characters of a word
    will not be counted as separate words.

    Returns the percentage of missing text represented as a decimal between 0 and 1.
    """
    output = _prepare_str(output)
    source = _prepare_str(source)
    output_bow = bag_of_words(output)
    source_bow = bag_of_words(source)

    # get total words in source bow while counting missing words
    total_source_word_count = 0
    total_missing_word_count = 0

    for source_word, source_count in source_bow.items():
        total_source_word_count += source_count
        if source_word not in output_bow:
            # entire count is missing
            total_missing_word_count += source_count
        else:
            output_count = output_bow[source_word]
            total_missing_word_count += max(source_count - output_count, 0)

    # calculate percent missing text
    if total_source_word_count == 0:
        return 0  # nothing missing because nothing in source document

    fraction_missing = round(total_missing_word_count / total_source_word_count, 3)
    return min(fraction_missing, 1)  # limit to 100%


def _prepare_str(string: Optional[str]) -> str:
    if not string:
        return ""
    return str(string)  # type: ignore
