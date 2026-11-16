from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import CheckBox, ElementMetadata, ElementType, Text, Title
from unstructured.partition.html.convert import elements_to_html
from unstructured.staging.base import create_file_from_elements, elements_from_dicts


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize("checked", [False, True])
@pytest.mark.parametrize("rehydrate", [False, True])
def test_checkbox_export_preserves_checked_state(exporter, checked, rehydrate, tmp_path):
    checkbox = CheckBox(
        checked=checked, element_id="answer-1", metadata=ElementMetadata(page_number=2)
    )
    if rehydrate:
        checkbox = elements_from_dicts([checkbox.to_dict()])[0]
    before = deepcopy(checkbox.to_dict())
    if exporter == "elements_to_html":
        result = elements_to_html([checkbox])
    else:
        output = tmp_path / "form.html"
        result = create_file_from_elements(
            iter([checkbox]), output_format="html", filename=str(output)
        )
        assert output.read_text(encoding="utf-8") == result

    tag = BeautifulSoup(result, "html.parser").find(id="answer-1")
    assert tag.name == "input"
    assert tag["type"] == "checkbox"
    assert tag.has_attr("checked") is checked
    assert checkbox.to_dict() == before


@pytest.mark.parametrize("checked", [False, True])
def test_checkbox_state_overrides_stale_checked_attribute(checked):
    checkbox = CheckBox(
        checked=checked,
        metadata=ElementMetadata(
            text_as_html=(
                '<input type="checkbox" checked="checked">'
                if not checked
                else '<input type="checkbox">'
            )
        ),
    )

    result = elements_to_html([checkbox], no_group_by_page=True)

    tag = BeautifulSoup(result, "html.parser").input
    assert tag.has_attr("checked") is checked


@pytest.mark.parametrize(
    ("category", "input_type", "checked"),
    [
        (ElementType.CHECKED, "checkbox", True),
        (ElementType.UNCHECKED, "checkbox", False),
        (ElementType.CHECK_BOX_CHECKED, "checkbox", True),
        (ElementType.CHECK_BOX_UNCHECKED, "checkbox", False),
        (ElementType.RADIO_BUTTON_CHECKED, "radio", True),
        (ElementType.RADIO_BUTTON_UNCHECKED, "radio", False),
    ],
)
def test_category_based_form_controls_keep_their_state(category, input_type, checked):
    element = Text("")
    element.category = category

    result = elements_to_html([element], no_group_by_page=True)

    tag = BeautifulSoup(result, "html.parser").input
    assert tag["type"] == input_type
    assert tag.has_attr("checked") is checked


def test_checkbox_stays_in_its_element_hierarchy():
    title = Title("Form", element_id="form")
    checkbox = CheckBox(
        checked=True, element_id="answer", metadata=ElementMetadata(parent_id="form")
    )
    caption = Text("Accept the terms", metadata=ElementMetadata(parent_id="answer"))

    result = elements_to_html([title, checkbox, caption], no_group_by_page=True)

    soup = BeautifulSoup(result, "html.parser")
    assert soup.find(id="form").parent.find(id="answer").name == "input"
    assert soup.find(id="answer").find_next_sibling("p").get_text(strip=True) == caption.text
