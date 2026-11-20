"""Whitespace-only extracted text must not abort overlap inspection."""

import pytest

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, NarrativeText, Title
from unstructured.utils import (
    calculate_largest_ngram_percentage,
    catch_overlapping_and_nested_bboxes,
)


@pytest.mark.parametrize("blank", ["", " ", "\t\n", "\u00a0\u2003"])
@pytest.mark.parametrize("reverse", [False, True])
def test_largest_ngram_handles_empty_token_sequences(blank, reverse):
    texts = ("banana orange pineapple", blank) if reverse else (blank, "banana orange pineapple")

    assert calculate_largest_ngram_percentage(*texts) == (0, set(), "0")


def test_two_empty_token_sequences_have_no_matching_ngram():
    assert calculate_largest_ngram_percentage("\t", "\n") == (0, set(), "0")


@pytest.mark.parametrize("blank", ["\t", "\n", "\u2003"])
@pytest.mark.parametrize("reverse", [False, True])
def test_whitespace_content_does_not_abort_a_document_overlap_report(blank, reverse):
    texts = ("ordinary paragraph", blank) if reverse else (blank, "ordinary paragraph")
    elements = [
        Title(
            texts[0],
            coordinates=((4, 5), (4, 8), (7, 8), (7, 5)),
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
        NarrativeText(
            texts[1],
            coordinates=((2, 3), (2, 6), (5, 6), (5, 3)),
            coordinate_system=PixelSpace(width=20, height=20),
            metadata=ElementMetadata(page_number=1),
        ),
    ]

    overlapping, cases = catch_overlapping_and_nested_bboxes(elements, nested_error_tolerance_px=0)

    assert overlapping is True
    assert len(cases) == 1
    assert cases[0]["overlapping_case"] == "partial overlap without sharing text"
    assert cases[0]["metadata"]["largest_ngram_percentage"] == 0
    assert [element.text for element in elements] == list(texts)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("Some lovely title", "Some lovely text", (50.0, {("Some", "lovely")}, "2")),
        ("apple", "orange", (0, set(), "1")),
        ("a b c", "x y z", (0, set(), "1")),
        ("a b", "a b c", (100.0, {("a",), ("b",)}, "1")),
    ],
)
def test_nonempty_token_sequences_keep_existing_results(first, second, expected):
    assert calculate_largest_ngram_percentage(first, second) == expected
