import pytest

from unstructured.metrics.element_type import get_element_type_frequency
from unstructured.partition.auto import partition


@pytest.mark.parametrize(
    ("filename", "frequency"),
    [
        (
            "fake-email.txt",
            {
                "UncategorizedText": {"None": 6},
                "ListItem": {"None": 12},
                "Title": {"None": 5},
                "NarrativeText": {"None": 2},
            },
        ),
        (
            "sample-presentation.pptx",
            {
                "Title": {"0": 4, "1": 1},
                "NarrativeText": {"0": 3},
                "ListItem": {"0": 6, "1": 6, "2": 3},
                "Table": {"None": 1},
            },
        ),
    ],
)
def test_get_element_type_frequency(filename, frequency):
    elements = partition(filename=f"example-docs/{filename}")
    elements_freq = get_element_type_frequency(elements)
    assert elements_freq == frequency
