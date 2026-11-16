from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import CheckBox, ElementMetadata, ElementType, Text, Title
from unstructured.documents.ontology import Checkbox, RadioButton
from unstructured.partition.common.common import normalize_layout_element
from unstructured.partition.html.convert import elements_to_html
from unstructured.partition.html.transformations import parse_html_to_ontology_element
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


def _export_control(element: CheckBox, exporter: str, tmp_path: Path) -> str:
    """Export a control through either public HTML entry point."""
    if exporter == "elements_to_html":
        return elements_to_html([element])
    output = tmp_path / "form.html"
    result = create_file_from_elements(iter([element]), output_format="html", filename=str(output))
    assert output.read_text(encoding="utf-8") == result
    return result


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize("rehydrate", [False, True])
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
def test_normalized_controls_preserve_kind_and_state_in_export(
    category, input_type, checked, rehydrate, exporter, tmp_path
):
    control = normalize_layout_element({"type": category, "text": ""})
    assert isinstance(control, CheckBox)
    control.metadata.page_number = 1
    if rehydrate:
        control = elements_from_dicts([control.to_dict()])[0]
    before = deepcopy(control.to_dict())

    result = _export_control(control, exporter, tmp_path)

    tag = BeautifulSoup(result, "html.parser").find(id=control.id)
    assert tag.name == "input"
    assert tag["type"] == input_type
    assert tag.has_attr("checked") is checked
    parsed = parse_html_to_ontology_element(tag)
    assert type(parsed) is (RadioButton if input_type == "radio" else Checkbox)
    assert parsed.html_tag_name == "input"
    assert ("checked" in parsed.additional_attributes) is checked
    assert control.category == ElementType.UNCATEGORIZED_TEXT
    assert control.to_dict() == before


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize("rehydrate", [False, True])
@pytest.mark.parametrize("checked", [False, True])
@pytest.mark.parametrize(
    "source_html",
    [
        '<label><input type="checkbox" checked>Accept</label>',
        '<label><input type="checkbox">Accept</label>',
        '<div><input type="checkbox" checked><input type="checkbox"></div>',
        "<span>Accept</span>",
    ],
)
def test_checkbox_export_replaces_non_input_source_root(
    source_html, checked, rehydrate, exporter, tmp_path
):
    control = CheckBox(
        checked=checked,
        element_id="answer",
        metadata=ElementMetadata(text_as_html=source_html, page_number=1),
    )
    if rehydrate:
        control = elements_from_dicts([control.to_dict()])[0]
    before = deepcopy(control.to_dict())

    result = _export_control(control, exporter, tmp_path)

    soup = BeautifulSoup(result, "html.parser")
    tag = soup.find(id="answer")
    assert tag.name == "input"
    assert len(soup.find_all("input")) == 1
    assert tag["type"] == "checkbox"
    assert tag.has_attr("checked") is checked
    assert control.to_dict() == before


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize("rehydrate", [False, True])
@pytest.mark.parametrize("extra_input", ["", '<input type="checkbox" checked name="other">'])
@pytest.mark.parametrize(
    ("category", "input_type", "checked"),
    [
        (ElementType.CHECK_BOX_CHECKED, "checkbox", True),
        (ElementType.CHECK_BOX_UNCHECKED, "checkbox", False),
        (ElementType.RADIO_BUTTON_CHECKED, "radio", True),
        (ElementType.RADIO_BUTTON_UNCHECKED, "radio", False),
    ],
)
def test_control_export_reuses_input_attributes_but_overrides_kind_and_state(
    category, input_type, checked, extra_input, rehydrate, exporter, tmp_path
):
    control = normalize_layout_element({"type": category, "text": ""})
    assert isinstance(control, CheckBox)
    stale_state = ' checked="false"' if not checked else ""
    control.metadata = ElementMetadata(
        page_number=1,
        text_as_html=(
            f'<input type="text" name="choice" value="option1"{stale_state}>{extra_input}'
        ),
    )
    if rehydrate:
        control = elements_from_dicts([control.to_dict()])[0]
    before = deepcopy(control.to_dict())

    result = _export_control(control, exporter, tmp_path)

    inputs = BeautifulSoup(result, "html.parser").find_all("input")
    assert len(inputs) == 1
    tag = inputs[0]
    assert tag["type"] == input_type
    assert tag.has_attr("checked") is checked
    assert tag["name"] == "choice"
    assert tag["value"] == "option1"
    assert control.to_dict() == before
