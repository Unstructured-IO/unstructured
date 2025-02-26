# pyright: reportPrivateUsage=false
from collections import defaultdict
from typing import Any, Optional

import pytest
from bs4 import BeautifulSoup, Tag
from pytest_mock import MockerFixture

from unstructured.documents.elements import Element, ElementMetadata, ElementType
from unstructured.partition.html.convert import (
    HTML_PARSER,
    ElementHtml,
    ImageElementHtml,
    LinkElementHtml,
    ListItemElementHtml,
    TableElementHtml,
    TextElementHtml,
    TitleElementHtml,
    UnorderedListElementHtml,
    _elements_to_html_tags,
    _elements_to_html_tags_by_page,
    _elements_to_html_tags_by_parent,
    _group_element_children,
    elements_to_html,
    group_elements_by_page,
)


class MockElement(Element):
    def __init__(
        self,
        text: str = "",
        metadata: Optional[ElementMetadata] = None,
        category: str = "",
        id: str = "",
    ) -> None:
        self.text = text
        self.metadata = metadata or ElementMetadata()
        self.category = category
        self._element_id = id


class MockElementMetadata(ElementMetadata):
    def __init__(
        self,
        text_as_html: Optional[str] = None,
        category_depth: Optional[int] = None,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        url: Optional[str] = None,
        parent_id: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> None:
        self.text_as_html = text_as_html
        self.category_depth = category_depth
        self.image_base64 = image_base64
        self.image_mime_type = image_mime_type
        self.url = url
        self.parent_id = parent_id
        self.page_number = page_number


@pytest.fixture
def mock_element() -> MockElement:
    metadata = MockElementMetadata(text_as_html="<p>Test HTML</p>")
    return MockElement(text="Test Text", metadata=metadata, category="test-category", id="test-id")


@pytest.fixture
def element_html(mock_element: MockElement) -> ElementHtml:
    return ElementHtml(mock_element)


@pytest.fixture
def title_element_html(mock_element: MockElement) -> TitleElementHtml:
    metadata = MockElementMetadata(text_as_html="<p>Test HTML</p>")
    MockElement(text="Test Text", metadata=metadata, category="test-category", id="test-id")
    return TitleElementHtml(mock_element)


@pytest.fixture
def image_element_html(mock_element: MockElement) -> ImageElementHtml:
    return ImageElementHtml(mock_element)


@pytest.fixture
def table_element_html(mock_element: MockElement) -> TableElementHtml:
    return TableElementHtml(mock_element)


@pytest.fixture
def link_element_html(mock_element: MockElement) -> LinkElementHtml:
    return LinkElementHtml(mock_element)


@pytest.fixture
def unordered_list_element_html(mock_element: MockElement) -> UnorderedListElementHtml:
    return UnorderedListElementHtml(mock_element)


def test_inject_html_element_content(element_html: ElementHtml) -> None:
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("div")
    element_html._inject_html_element_content(tag)
    assert tag.string == "Test Text"


def test_get_text_as_html(element_html: ElementHtml) -> None:
    tag = element_html.get_text_as_html()
    assert isinstance(tag, Tag)
    assert tag.name == "p"
    assert tag.string == "Test HTML"


def test_get_children_html(element_html: ElementHtml) -> None:
    soup = BeautifulSoup("", HTML_PARSER)
    parent_tag = soup.new_tag("div")
    child_element = MockElement(text="Child Text")
    child_element_html = ElementHtml(child_element)
    element_html.set_children([child_element_html])
    result_tag = element_html._get_children_html(soup, parent_tag)
    assert result_tag.name == "div"
    assert len(result_tag.contents) == 2
    assert result_tag.contents[1].string == "Child Text"


def test_get_html_element(element_html: ElementHtml) -> None:
    tag = element_html.get_html_element()
    assert isinstance(tag, Tag)
    assert tag.name == "div"
    assert tag.string == "Test Text"
    assert tag["class"] == "test-category"
    assert tag["id"] == "test-id"


def test_set_children(element_html: ElementHtml) -> None:
    child_element = MockElement(text="Child Text")
    child_element_html = ElementHtml(child_element)
    element_html.set_children([child_element_html])
    assert len(element_html.children) == 1
    assert element_html.children[0].element.text == "Child Text"


def test_title_element_html_tag(title_element_html: TitleElementHtml) -> None:
    assert title_element_html.html_tag == "h1"


def test_image_element_html_content(image_element_html: ImageElementHtml) -> None:
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("img")
    image_element_html._inject_html_element_content(tag)
    assert tag["alt"] == "Test Text"


def test_image_element_html_content_with_base64(image_element_html: ImageElementHtml) -> None:
    image_element_html.element.metadata.image_base64 = "base64data"
    image_element_html.element.metadata.image_mime_type = "image/png"
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("img")
    image_element_html._inject_html_element_content(tag)
    assert tag["src"] == "data:image/png;base64,base64data"
    assert tag["alt"] == "Test Text"


def test_table_element_html_attrs(table_element_html: TableElementHtml) -> None:
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("table")
    table_element_html._inject_html_element_attrs(tag)
    assert tag["style"] == "border: 1px solid black; border-collapse: collapse;"


def test_link_element_html_attrs(link_element_html: LinkElementHtml) -> None:
    link_element_html.element.metadata.url = "http://example.com"
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("a")
    link_element_html._inject_html_element_attrs(tag)
    assert tag["href"] == "http://example.com"


def test_unordered_list_element_html(unordered_list_element_html: UnorderedListElementHtml) -> None:
    soup = BeautifulSoup("", HTML_PARSER)
    tag = soup.new_tag("ul")
    child_element = MockElement(text="Child Text")
    child_element_html = ListItemElementHtml(child_element)
    unordered_list_element_html.set_children([child_element_html])
    result_tag = unordered_list_element_html._get_children_html(soup, tag)
    assert result_tag.name == "ul"
    assert len(result_tag.contents) == 1
    assert result_tag.contents[0].name == "li"
    assert result_tag.contents[0].string == "Child Text"


def test_group_element_children() -> None:
    children: list[ElementHtml] = [
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                category=ElementType.LIST_ITEM,
                id="test-element-1",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-2",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-3",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                category=ElementType.LIST_ITEM,
                id="test-element-4",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                category=ElementType.LIST_ITEM,
                id="test-element-5",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-6",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item Other",
                category=ElementType.LIST_ITEM_OTHER,
                id="test-element-7",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                category=ElementType.LIST_ITEM,
                id="test-element-8",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item Other",
                category=ElementType.LIST_ITEM_OTHER,
                id="test-element-9",
            )
        ),
    ]
    grouped_children = _group_element_children(children)
    assert len(grouped_children) == 6
    assert len(grouped_children[0].children) == 1
    assert grouped_children[0].children[0].element.category == ElementType.LIST_ITEM
    assert len(grouped_children[3].children) == 2
    assert grouped_children[3].children[0].element.category == ElementType.LIST_ITEM
    assert grouped_children[3].children[1].element.category == ElementType.LIST_ITEM
    assert len(grouped_children[5].children) == 3
    assert grouped_children[5].children[0].element.category == ElementType.LIST_ITEM_OTHER
    assert grouped_children[5].children[1].element.category == ElementType.LIST_ITEM
    assert grouped_children[5].children[2].element.category == ElementType.LIST_ITEM_OTHER


def test_elements_to_html_tags_by_parent(mocker: MockerFixture) -> None:
    mocker.patch(
        "unstructured.partition.html.convert._group_element_children",
        side_effect=lambda children: children,  # type: ignore
    )
    elements: list[ElementHtml] = [
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                category=ElementType.LIST_ITEM,
                id="test-element-1",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-2",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-3",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                metadata=MockElementMetadata(parent_id="test-element-3"),
                category=ElementType.LIST_ITEM,
                id="test-element-4",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                metadata=MockElementMetadata(parent_id="test-element-3"),
                category=ElementType.LIST_ITEM,
                id="test-element-5",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                category=ElementType.TEXT,
                id="test-element-6",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item Other",
                metadata=MockElementMetadata(parent_id="test-element-6"),
                category=ElementType.LIST_ITEM_OTHER,
                id="test-element-7",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item",
                metadata=MockElementMetadata(parent_id="test-element-7"),
                category=ElementType.LIST_ITEM,
                id="test-element-8",
            )
        ),
        ListItemElementHtml(
            MockElement(
                text="Test List Item Other",
                metadata=MockElementMetadata(parent_id="test-element-6"),
                category=ElementType.LIST_ITEM_OTHER,
                id="test-element-9",
            )
        ),
        TextElementHtml(
            MockElement(
                text="Test Text",
                metadata=MockElementMetadata(parent_id="test-element-6"),
                category=ElementType.TEXT,
                id="test-element-10",
            )
        ),
    ]
    result = _elements_to_html_tags_by_parent(elements)
    assert len(result) == 4
    assert result[0].element.id == "test-element-1"
    assert len(result[0].children) == 0
    assert result[1].element.id == "test-element-2"
    assert len(result[1].children) == 0
    assert result[2].element.id == "test-element-3"
    assert len(result[2].children) == 2
    assert result[2].children[0].element.id == "test-element-4"
    assert result[2].children[1].element.id == "test-element-5"
    assert result[3].element.id == "test-element-6"
    assert len(result[3].children) == 3
    assert result[3].children[0].element.id == "test-element-7"
    assert len(result[3].children[0].children) == 1
    assert result[3].children[0].children[0].element.id == "test-element-8"
    assert result[3].children[1].element.id == "test-element-9"
    assert result[3].children[2].element.id == "test-element-10"


def test_elements_to_html_tags(mocker: MockerFixture) -> None:
    def _mock_get_html_element(self: ElementHtml, **kwargs: Any):
        return BeautifulSoup(f"<div>{self.element.id}</div>", HTML_PARSER).find()

    mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags_by_parent",
        side_effect=lambda elements: elements,  # type: ignore
    )
    mocker.patch(
        "unstructured.partition.html.convert.ElementHtml.get_html_element",
        side_effect=_mock_get_html_element,
        autospec=True,
    )
    elements: list[Element] = [
        MockElement(
            text="Test Text",
            category=ElementType.TEXT,
            id="test-element-1",
        ),
        MockElement(
            text="Test List Item",
            category=ElementType.LIST_ITEM,
            id="test-element-2",
        ),
        MockElement(
            text="Test Uncategorized Text",
            category=ElementType.UNCATEGORIZED_TEXT,
            id="test-element-3",
        ),
    ]
    result = _elements_to_html_tags(elements)
    assert len(result) == 3
    assert all(isinstance(tag, Tag) for tag in result)
    assert result[0].string == "test-element-1"
    assert result[1].string == "test-element-2"
    assert result[2].string == "test-element-3"


def test_elements_to_html_tags_by_page(mocker: MockerFixture) -> None:
    def _mock_elements_to_html_tags(elements: list[Element], _: bool):
        return [
            BeautifulSoup(f"<div>{element.id}</div>", HTML_PARSER).find() for element in elements
        ]

    def _mock_group_elements_by_page(elements: list[Element]) -> list[list[Element]]:
        pages_dict: defaultdict[int, list[Element]] = defaultdict(list)
        for element in elements:
            pages_dict[element.metadata.page_number].append(element)  # type: ignore
        return list(pages_dict.values())

    mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags",
        side_effect=_mock_elements_to_html_tags,
    )
    mocker.patch(
        "unstructured.partition.html.convert.group_elements_by_page",
        side_effect=_mock_group_elements_by_page,
    )
    elements: list[Element] = [
        MockElement(
            text="Test Text",
            category=ElementType.TEXT,
            id="test-element-1",
            metadata=MockElementMetadata(page_number=1),
        ),
        MockElement(
            text="Test List Item",
            category=ElementType.LIST_ITEM,
            id="test-element-2",
            metadata=MockElementMetadata(page_number=1),
        ),
        MockElement(
            text="Test Uncategorized Text",
            category=ElementType.UNCATEGORIZED_TEXT,
            id="test-element-3",
            metadata=MockElementMetadata(page_number=2),
        ),
    ]
    result = _elements_to_html_tags_by_page(elements)
    assert len(result) == 2
    assert all(isinstance(tag, Tag) for tag in result)
    assert result[0].name == "div"
    assert result[0]["data-page_number"] == 1
    assert len(result[0].contents) == 2
    assert result[0].contents[0].string == "test-element-1"  # type: ignore
    assert result[0].contents[1].string == "test-element-2"  # type: ignore
    assert result[1].name == "div"
    assert result[1]["data-page_number"] == 2
    assert len(result[1].contents) == 1
    assert result[1].contents[0].string == "test-element-3"  # type: ignore


def test_group_elements_by_page(caplog: pytest.LogCaptureFixture) -> None:
    elements: list[Element] = [
        MockElement(
            text="Test Text 1",
            category=ElementType.TEXT,
            id="test-element-1",
            metadata=MockElementMetadata(page_number=1),
        ),
        MockElement(
            text="Test Text 2",
            category=ElementType.TEXT,
            id="test-element-2",
            metadata=MockElementMetadata(page_number=1),
        ),
        MockElement(
            text="Test Text 3",
            category=ElementType.TEXT,
            id="test-element-3",
            metadata=MockElementMetadata(page_number=None),
        ),
        MockElement(
            text="Test Text 4",
            category=ElementType.TEXT,
            id="test-element-4",
            metadata=MockElementMetadata(page_number=2),
        ),
        MockElement(
            text="Test Text 5",
            category=ElementType.TEXT,
            id="test-element-5",
            metadata=MockElementMetadata(page_number=2),
        ),
    ]
    result = group_elements_by_page(elements)
    assert len(result) == 2
    assert len(result[0]) == 2
    assert len(result[1]) == 2
    assert result[0][0].id == "test-element-1"
    assert result[0][1].id == "test-element-2"
    assert result[1][0].id == "test-element-4"
    assert result[1][1].id == "test-element-5"
    assert "Page number is not set for an element test-element-3. Skipping." in caplog.text


def test_elements_to_html_no_group_by_page(mocker: MockerFixture) -> None:
    def _mock_elements_to_html_tags(elements: list[Element], _: bool):
        return [
            BeautifulSoup(f"<div>{element.id}</div>", HTML_PARSER).find() for element in elements
        ]

    mock_elements_to_html_tags = mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags",
        side_effect=_mock_elements_to_html_tags,
    )
    mock_elements_to_html_tags_by_page = mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags_by_page",
    )

    elements: list[Element] = [
        MockElement(
            text="Test Text 1",
            category=ElementType.TEXT,
            id="test-element-1",
        ),
        MockElement(
            text="Test Text 2",
            category=ElementType.TEXT,
            id="test-element-2",
        ),
    ]

    result = elements_to_html(elements, exclude_binary_image_data=True, no_group_by_page=True)
    assert "<div>\n   test-element-1\n  </div>" in result
    assert "<div>\n   test-element-2\n  </div>" in result
    assert "data-page_number" not in result
    mock_elements_to_html_tags.assert_called_once_with(elements, True)
    mock_elements_to_html_tags_by_page.assert_not_called()


def test_elements_to_html_group_by_page(mocker: MockerFixture) -> None:
    def _mock_elements_to_html_tags_by_page(elements: list[Element], _: bool):
        return [
            BeautifulSoup(
                f"<div data-page_number='{element.metadata.page_number}'>{element.id}</div>",
                HTML_PARSER,
            ).find()
            for element in elements
        ]

    mock_elements_to_html_tags_by_page = mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags_by_page",
        side_effect=_mock_elements_to_html_tags_by_page,
    )
    mock_elements_to_html_tags = mocker.patch(
        "unstructured.partition.html.convert._elements_to_html_tags"
    )

    elements: list[Element] = [
        MockElement(
            text="Test Text 1",
            category=ElementType.TEXT,
            id="test-element-1",
            metadata=MockElementMetadata(page_number=1),
        ),
        MockElement(
            text="Test Text 2",
            category=ElementType.TEXT,
            id="test-element-2",
            metadata=MockElementMetadata(page_number=2),
        ),
    ]

    result = elements_to_html(elements, exclude_binary_image_data=True, no_group_by_page=False)
    assert "<div>\n   test-element-1\n  </div>" in result
    assert "<div>\n   test-element-2\n  </div>" in result
    assert "data-page_number='1'" in result
    assert "data-page_number='2'" in result
    mock_elements_to_html_tags_by_page.assert_called_once_with(elements, True)
    mock_elements_to_html_tags.assert_not_called()
    soup = BeautifulSoup(result, HTML_PARSER)
    assert soup.body is not None
    assert len(soup.body.contents) == 2
    assert soup.body.contents[0]["data-page_number"] == "1"
    assert soup.body.contents[0].string == "test-element-1"
    assert soup.body.contents[1]["data-page_number"] == "2"
    assert soup.body.contents[1].string == "test-element-2"


def test_elements_to_html_invalid_html_template(mocker: MockerFixture) -> None:
    mocker.patch(
        "unstructured.partition.html.convert.HTML_TEMPLATE",
        "<html><head><title>Test</title></head></html>",
    )

    elements: list[Element] = [
        MockElement(
            text="Test Text 1",
            category=ElementType.TEXT,
            id="test-element-1",
        ),
    ]

    with pytest.raises(ValueError, match="Body tag not found in the HTML template"):
        elements_to_html(elements)
