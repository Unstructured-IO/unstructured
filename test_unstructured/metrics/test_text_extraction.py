import pytest

from unstructured.metrics.text_extraction import calculate_edit_distance
from unstructured.partition.auto import partition


@pytest.mark.parametrize(
    ("filename", "similarity"),
    [
        ("fake-text.txt", 0.82),
        ("eml/fake-email.eml", 0.03),
        ("README.md", 0.0),
    ],
)
def test_calculate_edit_distance(filename, similarity):
    with open("example-docs/fake-text.txt") as f:
        source_cct = f.read()

    elements = partition(filename=f"example-docs/{filename}")
    output_cct = "\n\n".join([str(el) for el in elements])

    score = calculate_edit_distance(output_cct, source_cct)
    assert round(score, 2) == similarity
