import pytest

from unstructured.documents.elements import Element
from unstructured.partition.utils.sorting import sort_page_elements


@pytest.mark.parametrize("sort_mode", ["xy-cut", "basic"])
def test_sort_page_elements_without_coordinates(sort_mode):
    elements = [Element(str(idx)) for idx in range(5)]
    assert sort_page_elements(elements) == elements
