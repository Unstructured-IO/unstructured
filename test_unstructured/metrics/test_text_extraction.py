import pytest

from unstructured.metrics.text_extraction import calculate_edit_distance
from unstructured.partition.auto import partition


@pytest.mark.parametrize(
    ("filename", "expected_score", "expected_distance"),
    [
        ("fake-text.txt", 0.82, 30),
        ("eml/fake-email.eml", 0.03, 164),
        ("README.md", 0.0, 719),
    ],
)
def test_calculate_edit_distance(filename, expected_score, expected_distance):
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
