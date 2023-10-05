import pytest

from unstructured.metrics.text_extraction import calculate_edit_distance
from unstructured.partition.auto import partition


@pytest.mark.parametrize(
    ("filename", "similarity", "percentage"),
    [
        ("fake-text.txt", 0.82, 0.18),
        ("eml/fake-email.eml", 0.03, 0.97),
        ("README.md", 0.0, 1.00),
    ],
)
def test_calculate_edit_distance(filename, similarity, percentage):
    with open("example-docs/fake-text.txt") as f:
        source_cct = f.read()

    elements = partition(filename=f"example-docs/{filename}")
    output_cct = "\n\n".join([str(el) for el in elements])

    score = calculate_edit_distance(output_cct, source_cct, return_as="score")
    distance = calculate_edit_distance(output_cct, source_cct, return_as="percentage")
    assert round(score, 2) == similarity
    assert round(distance, 2) == percentage
