from copy import deepcopy

import pytest
from bs4 import BeautifulSoup

from unstructured.documents.elements import (
    ElementMetadata,
    ElementType,
    ListItem,
    Table,
    Text,
    Title,
)
from unstructured.partition.html.convert import ElementHtml, elements_to_html
from unstructured.staging.base import create_file_from_elements


@pytest.mark.parametrize("exporter", ["elements_to_html", "create_file_from_elements"])
@pytest.mark.parametrize(
    ("fragment", "expected_text"),
    [
        ("<p>First paragraph.</p><p>Second paragraph.</p>", "First paragraph. Second paragraph."),
        ("Before <b>bold</b> after.", "Before bold after."),
        ("<p>First</p> between <p>Second</p> after", "First between Second after"),
        ("<section><p>Nested first</p></section><p>Second</p>", "Nested first Second"),
        ("<p>First</p><!-- comment --><p>Second</p>", "First Second"),
        ('<script>alert(1)</script><p onclick="alert(2)">Safe content</p>', "Safe content"),
    ],
)
def test_export_preserves_every_html_fragment_node(exporter, fragment, expected_text, tmp_path):
    element = Text(
        "fallback",
        element_id="fragment",
        metadata=ElementMetadata(text_as_html=fragment, page_number=2),
    )
    before = deepcopy(element.to_dict())
    if exporter == "elements_to_html":
        result = elements_to_html([element])
    else:
        output = tmp_path / "fragment.html"
        result = create_file_from_elements([element], output_format="html", filename=str(output))
        assert output.read_text(encoding="utf-8") == result

    soup = BeautifulSoup(result, "html.parser")
    assert soup.body.get_text(" ", strip=True) == expected_text
    # The sanitizer removes the original identity along with an unsafe first tag.
    assert len(soup.find_all(id="fragment")) == int(not fragment.startswith("<script>"))
    assert soup.script is None
    assert not soup.select("[onclick]")
    assert element.to_dict() == before


@pytest.mark.parametrize(
    "fragment",
    ["<p>Content</p>", "\n <p>Content</p> \n", "<!-- comment --><p>Content</p><!-- end -->"],
)
def test_single_html_root_keeps_its_tag(fragment):
    renderer = ElementHtml(Text("fallback", metadata=ElementMetadata(text_as_html=fragment)))

    tag = renderer.get_text_as_html()

    assert tag.name == "p"
    assert tag.get_text() == "Content"


@pytest.mark.parametrize("fragment", [None, "", " \n ", "plain text without a tag"])
def test_html_without_a_tag_keeps_the_existing_text_fallback(fragment):
    element = Text("fallback", metadata=ElementMetadata(text_as_html=fragment))

    result = elements_to_html([element], no_group_by_page=True)

    assert BeautifulSoup(result, "html.parser").body.get_text(" ", strip=True) == "fallback"


def test_fragment_content_and_element_children_both_survive_export():
    parent = Title(
        "fallback",
        element_id="parent",
        metadata=ElementMetadata(text_as_html="<h2>Heading</h2><p>Summary</p>"),
    )
    child = Text("Child text", element_id="child", metadata=ElementMetadata(parent_id="parent"))

    result = elements_to_html([parent, child], no_group_by_page=True)

    soup = BeautifulSoup(result, "html.parser")
    assert soup.body.get_text(" ", strip=True) == "Heading Summary Child text"
    assert soup.find(id="parent").parent.find_next_sibling(id="child") is not None


@pytest.mark.parametrize(
    ("category", "fragment", "tag_name", "expected_attrs"),
    [
        (ElementType.LINK, "<a>Link</a> following text", "a", {"href": "https://example.com/"}),
        (
            ElementType.CHECKED,
            "<input><span>Caption</span>",
            "input",
            {"type": "checkbox", "checked": "true"},
        ),
        (ElementType.TABLE, "<table><tr><td>Cell</td></tr></table><p>Note</p>", "table", {}),
    ],
)
def test_fragment_wrapper_keeps_type_attributes_on_the_original_tag(
    category, fragment, tag_name, expected_attrs
):
    element = Table("fallback") if category == ElementType.TABLE else Text("fallback")
    element.category = category
    element.metadata.text_as_html = fragment
    element.metadata.url = "https://example.com/"

    result = elements_to_html([element], no_group_by_page=True)

    tag = BeautifulSoup(result, "html.parser").find(tag_name)
    for key, value in expected_attrs.items():
        assert tag[key] == value
    if category == ElementType.TABLE:
        assert "border-collapse" in tag["style"]
        assert tag.find_next_sibling("p").get_text(strip=True) == "Note"
    assert tag.parent.name == "div"
    assert not any(name in tag.parent.attrs for name in ["href", "type", "checked", "style"])


def test_fragment_wrapper_preserves_nested_list_children():
    parent = ListItem(
        "fallback",
        element_id="parent",
        metadata=ElementMetadata(text_as_html="<li>Parent text</li><span>Extra detail</span>"),
    )
    child = ListItem("Child item", element_id="child", metadata=ElementMetadata(parent_id="parent"))

    result = elements_to_html([parent, child], no_group_by_page=True)

    soup = BeautifulSoup(result, "html.parser")
    assert soup.find(id="parent").find(id="child") is not None
    assert "Extra detail" in soup.body.get_text()
    assert len(soup.find_all(id="child")) == 1
