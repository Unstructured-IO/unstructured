import pytest

from unstructured.metrics.element_type import (
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
                ("UncategorizedText", None): 6,
                ("ListItem", None): 2,
                ("Title", None): 5,
                ("NarrativeText", None): 2,
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
def test_get_element_type_frequency(filename, frequency):
    elements = partition(filename=f"example-docs/{filename}")
    elements_freq = get_element_type_frequency(elements_to_json(elements))
    assert elements_freq == frequency


@pytest.mark.parametrize(
    ("filename", "expected_frequency", "percent_matched"),
    [
        (
            "fake-email.txt",
            {
                ("UncategorizedText", None): 14,
                ("ListItem", None): 2,
                ("NarrativeText", None): 2,
            },
            (0.56, 0.56, 0.56),
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
def test_calculate_element_type_percent_match(filename, expected_frequency, percent_matched):
    elements = partition(filename=f"example-docs/{filename}")
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
