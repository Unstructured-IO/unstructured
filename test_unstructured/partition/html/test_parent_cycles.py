from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import ElementMetadata, NarrativeText
from unstructured.partition.html.convert import elements_to_html


def make_element(text: str, element_id: str, parent_id: str | None = None):
    return NarrativeText(
        text,
        element_id=element_id,
        metadata=ElementMetadata(parent_id=parent_id, page_number=1),
    )


@pytest.mark.parametrize("group_by_page", [False, True])
@pytest.mark.parametrize(
    "records",
    [
        [("Self parent", "a", "a")],
        [("First", "a", "b"), ("Second", "b", "a")],
        [("Descendant", "c", "b"), ("First", "a", "b"), ("Second", "b", "a")],
        [
            ("First cycle", "a", "b"),
            ("First child", "b", "a"),
            ("Second cycle", "c", "c"),
            ("Root", "root", None),
            ("Root child", "leaf", "root"),
        ],
    ],
)
def test_cycles_do_not_silently_drop_elements_or_their_descendants(records, group_by_page):
    elements = [make_element(*record) for record in records]
    before = deepcopy([element.to_dict() for element in elements])

    output = elements_to_html(elements, no_group_by_page=not group_by_page)

    text = list(BeautifulSoup(output, "html.parser").body.stripped_strings)
    assert sorted(text) == sorted(record[0] for record in records)
    assert [element.to_dict() for element in elements] == before


def test_valid_parent_links_keep_their_nesting_even_when_children_precede_parents():
    elements = [
        make_element("Child", "child", "parent"),
        make_element("Parent", "parent"),
        make_element("Next root", "next"),
    ]

    output = elements_to_html(elements, no_group_by_page=True)

    assert list(BeautifulSoup(output, "html.parser").body.stripped_strings) == [
        "Parent",
        "Child",
        "Next root",
    ]


def test_missing_parents_still_render_as_roots():
    elements = [make_element("Orphan", "a", "missing"), make_element("Root", "b")]

    output = elements_to_html(elements, no_group_by_page=True)

    assert list(BeautifulSoup(output, "html.parser").body.stripped_strings) == ["Orphan", "Root"]


def test_duplicate_ids_keep_the_first_matching_parent():
    elements = [
        make_element("First parent", "parent"),
        make_element("Second parent", "parent"),
        make_element("Child", "child", "parent"),
    ]

    output = elements_to_html(elements, no_group_by_page=True)

    assert list(BeautifulSoup(output, "html.parser").body.stripped_strings) == [
        "First parent",
        "Child",
        "Second parent",
    ]


def test_a_duplicate_id_pointing_at_the_first_instance_is_not_a_cycle(caplog):
    elements = [make_element("Parent", "shared"), make_element("Child", "shared", "shared")]

    output = elements_to_html(elements, no_group_by_page=True)

    assert list(BeautifulSoup(output, "html.parser").body.stripped_strings) == ["Parent", "Child"]
    assert "cycle" not in caplog.text.lower()


def test_empty_input_still_produces_an_empty_body():
    output = elements_to_html([], no_group_by_page=True)

    assert list(BeautifulSoup(output, "html.parser").body.stripped_strings) == []
