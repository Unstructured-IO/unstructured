import re

import pytest

from unstructured.metrics import text_extraction
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

    assert (
        round(text_extraction.calculate_edit_distance(source_cct, source_cct, return_as="score"), 2)
        == 1.0
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_word_space,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.75
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_spaces,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.39
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_no_space,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.64
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_one_sentence,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.0
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_missing_word,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.57
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_addn_char,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.89
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_dup_word,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.79
    )


@pytest.mark.parametrize(
    ("filename", "expected_score", "expected_distance"),
    [
        ("fake-text.txt", 0.78, 38),
    ],
)
def test_calculate_edit_distance_with_filename(filename, expected_score, expected_distance):
    with open("example-docs/fake-text.txt") as f:
        source_cct = f.read()

    elements = partition(filename=f"example-docs/{filename}")
    output_cct = "\n".join([str(el) for el in elements])

    score = text_extraction.calculate_edit_distance(output_cct, source_cct, return_as="score")
    distance = text_extraction.calculate_edit_distance(output_cct, source_cct, return_as="distance")

    assert score >= 0
    assert score <= 1.0
    assert distance >= 0
    assert round(score, 2) == expected_score
    assert distance == expected_distance


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The dog loved the cat, but the cat loved the cow",
            {"the": 4, "cat": 2, "loved": 2, "dog": 1, "but": 1, "cow": 1},
        ),
        (
            "Hello my name is H a r p e r, what's your name?",
            {"hello": 1, "my": 1, "name": 2, "is": 1, "what's": 1, "your": 1},
        ),
        (
            "I have a dog and a cat, I love my dog.",
            {"i": 2, "have": 1, "a": 2, "dog": 2, "and": 1, "cat": 1, "love": 1, "my": 1},
        ),
        (
            "My dog's hair is red, but the dogs' houses are blue.",
            {
                "my": 1,
                "dog's": 1,
                "hair": 1,
                "is": 1,
                "red": 1,
                "but": 1,
                "the": 1,
                "dogs'": 1,
                "houses": 1,
                "are": 1,
                "blue": 1,
            },
        ),
        (
            """Sometimes sentences have a dash - like this one!
            A hyphen connects 2 words with no gap: easy-peasy.""",
            {
                "sometimes": 1,
                "sentences": 1,
                "have": 1,
                "a": 2,
                "dash": 1,
                "like": 1,
                "this": 1,
                "one": 1,
                "hyphen": 1,
                "connects": 1,
                "2": 1,
                "words": 1,
                "with": 1,
                "no": 1,
                "gap": 1,
                "easy-peasy": 1,
            },
        ),
    ],
)
def test_bag_of_words(text, expected):
    assert text_extraction.bag_of_words(text) == expected


@pytest.mark.parametrize(
    ("output_text", "source_text", "expected_percentage"),
    [
        (
            "extra",
            "",
            0,
        ),
        (
            "",
            "Source text has a sentence.",
            1,
        ),
        (
            "The original s e n t e n c e is normal.",
            "The original sentence is normal...",
            0.2,
        ),
        (
            "We saw 23% improvement in this quarter.",
            "We saw 23% improvement in sales this quarter.",
            0.125,
        ),
        (
            "no",
            "Is it possible to have more than everything missing?",
            1,
        ),
    ],
)
def test_calculate_percent_missing_text(output_text, source_text, expected_percentage):
    assert (
        text_extraction.calculate_percent_missing_text(output_text, source_text)
        == expected_percentage
    )
