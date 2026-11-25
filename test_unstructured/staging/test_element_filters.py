import pytest

from unstructured.documents.elements import NarrativeText, Title
from unstructured.staging.base import filter_element_types


@pytest.mark.parametrize("selection", [[], ()])
@pytest.mark.parametrize("use_iterator", [False, True])
def test_empty_include_selection_returns_no_elements(selection, use_iterator):
    elements = [Title("Heading"), NarrativeText("Body")]

    result = filter_element_types(
        iter(elements) if use_iterator else elements,
        include_element_types=selection,
    )

    assert result == []
    assert [element.text for element in elements] == ["Heading", "Body"]


@pytest.mark.parametrize("selection", [[], ()])
@pytest.mark.parametrize("use_iterator", [False, True])
def test_empty_exclude_selection_returns_every_element(selection, use_iterator):
    elements = [Title("Heading"), NarrativeText("Body")]

    result = filter_element_types(
        iter(elements) if use_iterator else elements,
        exclude_element_types=selection,
    )

    assert len(result) == len(elements)
    assert all(actual is original for actual, original in zip(result, elements))


@pytest.mark.parametrize("selection", [[Title], (Title,)])
@pytest.mark.parametrize("mode", ["include", "exclude"])
def test_nonempty_selection_preserves_order_and_element_identity(selection, mode):
    elements = [Title("First"), NarrativeText("Middle"), Title("Last")]

    result = filter_element_types(iter(elements), **{f"{mode}_element_types": selection})

    expected = [elements[0], elements[2]] if mode == "include" else [elements[1]]
    assert len(result) == len(expected)
    assert all(actual is original for actual, original in zip(result, expected))


@pytest.mark.parametrize(
    ("include", "exclude"),
    [(None, None), ([], []), ([], [Title]), ([Title], [])],
)
def test_filter_requires_exactly_one_selection_even_when_empty(include, exclude):
    elements = iter([Title("Heading")])

    with pytest.raises(ValueError, match="Exactly one"):
        filter_element_types(elements, include_element_types=include, exclude_element_types=exclude)

    assert next(elements).text == "Heading"
