from __future__ import annotations

import pytest

from test_unstructured.unit_utils import example_doc_path
from unstructured.metrics.element_type import (
    FrequencyDict,
    calculate_element_type_percent_match,
    get_element_type_frequency,
)
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json


@pytest.mark.parametrize(
    ("filename", "frequency"),
    [
        (
            "fake-email.txt",
            {
                ("NarrativeText", None): 1,
                ("Title", None): 1,
                ("ListItem", None): 2,
            },
        ),
        (
            "sample-presentation.pptx",
            {
                ("Title", 0): 4,
                ("Title", 1): 1,
                ("NarrativeText", 0): 3,
                ("ListItem", 0): 6,
                ("ListItem", 1): 6,
                ("ListItem", 2): 3,
                ("Table", None): 1,
            },
        ),
    ],
)
def test_get_element_type_frequency(filename: str, frequency: dict[tuple[str, int | None], int]):
    elements = partition(example_doc_path(filename))
    elements_freq = get_element_type_frequency(elements_to_json(elements))
    assert elements_freq == frequency


@pytest.mark.parametrize(
    ("filename", "expected_frequency", "percent_matched"),
    [
        (
            "fake-email.txt",
            {
                ("Title", None): 1,
                ("ListItem", None): 2,
                ("NarrativeText", None): 2,
            },
            (0.8, 0.8, 0.80),
        ),
        (
            "sample-presentation.pptx",
            {
                ("Title", 0): 3,
                ("Title", 1): 1,
                ("NarrativeText", None): 1,
                ("NarrativeText", 0): 3,
                ("ListItem", 0): 6,
                ("ListItem", 1): 6,
                ("ListItem", 2): 3,
                ("Table", None): 1,
            },
            (0.96, 0.96, 0.96),
        ),
        (
            "handbook-1p.docx",
            {
                ("Header", None): 1,
                ("Title", 0): 1,
                ("Title", 1): 1,
                ("Title", 2): 1,
                ("ListItem", 3): 3,
                ("NarrativeText", 4): 7,
                ("Footer", None): 1,
            },
            (0.43, 0.07, 0.65),
        ),
        (
            "handbook-1p.docx",
            {
                ("Header", None): 1,
                ("Title", 0): 6,
                ("NarrativeText", 0): 7,
                ("PageBreak", None): 1,
                ("Footer", None): 1,
            },
            (0.94, 0.88, 0.98),
        ),
    ],
)
def test_calculate_element_type_percent_match(
    filename: str, expected_frequency: FrequencyDict, percent_matched: tuple[float, float, float]
):
    elements = partition(example_doc_path(filename))
    elements_frequency = get_element_type_frequency(elements_to_json(elements))
    assert (
        round(calculate_element_type_percent_match(elements_frequency, expected_frequency), 2)
        == percent_matched[0]
    )
    assert (
        round(calculate_element_type_percent_match(elements_frequency, expected_frequency, 0.0), 2)
        == percent_matched[1]
    )
    assert (
        round(calculate_element_type_percent_match(elements_frequency, expected_frequency, 0.8), 2)
        == percent_matched[2]
    )
