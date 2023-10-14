import pytest

from unstructured.documents.base import Document, Page
from unstructured.documents.elements import Formula, NarrativeText, Title


class MockDocument(Document):
    def __init__(self):
        super().__init__()
        elements = [
            Title(text="This is a narrative."),
            NarrativeText(text="This is a narrative."),
            NarrativeText(text="This is a narrative."),
        ]
        page = Page(number=0)
        page.elements = elements
        self._pages = [page]


class MockDocumentWithFormula(Document):
    def __init__(self):
        super().__init__()
        elements = [
            Title(text="This is a narrative."),
            Formula(text="e=mc2"),
        ]
        page = Page(number=0)
        page.elements = elements
        self._pages = [page]


def test_get_narrative():
    document = MockDocument()
    narrative = document.get_narrative()
    for element in narrative:
        assert isinstance(element, NarrativeText)
    document.print_narrative()


def test_get_formula():
    document = MockDocumentWithFormula()
    formula = [e for e in document.elements if isinstance(e, Formula)]
    assert formula[0].text != ""


@pytest.mark.parametrize("index", [0, 1, 2])
def test_split(index):
    document = MockDocument()
    elements = document.pages[0].elements
    split_before_doc = document.before_element(elements[index])
    before_elements = split_before_doc.pages[0].elements if split_before_doc.pages else []
    split_after_doc = document.after_element(elements[index])
    after_elements = split_after_doc.pages[0].elements if split_after_doc.pages else []
    expected_before_elements = document.pages[0].elements[:index]
    next_index = index + 1
    expected_after_elements = document.pages[0].elements[next_index:]
    assert all(a.id == b.id for a, b in zip(before_elements, expected_before_elements))
    assert all(a.id == b.id for a, b in zip(after_elements, expected_after_elements))
