import re

import pytest

from unstructured.metrics.text_extraction import calculate_edit_distance
from unstructured.partition.auto import partition


def test_calculate_edit_distance():
    source_cct = "I like pizza. I like bagels."
    source_cct_word_space = "I like p i z z a . I like bagles."
    source_cct_spaces = re.sub(r"\s+", " ", " ".join(source_cct))
    source_cct_no_space = source_cct.replace(" ", "")
    source_cct_one_sentence = "I like pizza."
    source_cct_missing_word = "I like pizza. I like ."
    source_cct_addn_char = "I like pizza. I like beagles."
    source_cct_dup_word = "I like pizza pizza. I like bagels."

    assert round(calculate_edit_distance(source_cct, source_cct, return_as="score"), 2) == 1.0
    assert (
        round(calculate_edit_distance(source_cct_word_space, source_cct, return_as="score"), 2)
        == 0.75
    )
    assert (
        round(calculate_edit_distance(source_cct_spaces, source_cct, return_as="score"), 2) == 0.39
    )
    assert (
        round(calculate_edit_distance(source_cct_no_space, source_cct, return_as="score"), 2)
        == 0.64
    )
    assert (
        round(calculate_edit_distance(source_cct_one_sentence, source_cct, return_as="score"), 2)
        == 0.0
    )
    assert (
        round(calculate_edit_distance(source_cct_missing_word, source_cct, return_as="score"), 2)
        == 0.57
    )
    assert (
        round(calculate_edit_distance(source_cct_addn_char, source_cct, return_as="score"), 2)
        == 0.89
    )
    assert (
        round(calculate_edit_distance(source_cct_dup_word, source_cct, return_as="score"), 2)
        == 0.79
    )


@pytest.mark.parametrize(
    ("filename", "expected_score", "expected_distance"),
    [
        ("fake-text.txt", 0.82, 30),
        ("eml/fake-email.eml", 0.03, 164),
        ("README.md", 0.0, 719),
    ],
)
def test_calculate_edit_distance_with_filename(filename, expected_score, expected_distance):
    with open("example-docs/fake-text.txt") as f:
        source_cct = f.read()

    elements = partition(filename=f"example-docs/{filename}")
    output_cct = "\n\n".join([str(el) for el in elements])

    score = calculate_edit_distance(output_cct, source_cct, return_as="score")
    distance = calculate_edit_distance(output_cct, source_cct, return_as="distance")

    assert score >= 0
    assert score <= 1.0
    assert distance >= 0
    assert round(score, 2) == expected_score
    assert distance == expected_distance
