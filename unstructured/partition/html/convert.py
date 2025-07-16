import logging
from abc import ABC
from collections import defaultdict
from typing import Any, Optional, Union

from bs4 import BeautifulSoup, Tag

from unstructured.documents.elements import Element, ElementType

logger = logging.getLogger(__name__)

HTML_PARSER = "html.parser"
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title></title>
</head>
<body>
</body>
</html>
"""

TABLE_BORDER_STYLE = "border: 1px solid black;"
TABLE_BORDER_COLLAPSE_STYLE = "border-collapse: collapse;"


class ElementHtml(ABC):
    element: Element
    children: list["ElementHtml"]
    _html_tag: str = "div"

    def __init__(self, element: Element, children: Optional[list["ElementHtml"]] = None):
        self.element = element
        self.children = children or []

    @property
    def html_tag(self) -> str:
        return self._html_tag

    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        return None

    def _inject_html_element_content(self, element_html: Tag, **kwargs: Any) -> None:
        element_html.string = self.element.text

    def get_text_as_html(self) -> Union[Tag, None]:
        element_html = BeautifulSoup(self.element.metadata.text_as_html or "", HTML_PARSER).find()
        if not isinstance(element_html, Tag):
            return None
        return element_html

    def _get_children_html(self, soup: BeautifulSoup, element_html: Tag, **kwargs: Any) -> Tag:
        wrapper = soup.new_tag(name="div")
        wrapper.append(element_html)
        for child in self.children:
            child_html = child.get_html_element(**kwargs)
            wrapper.append(child_html)
        return wrapper

    def get_html_element(self, **kwargs: Any) -> Tag:
        soup = BeautifulSoup("", HTML_PARSER)
        element_html = self.get_text_as_html()
        if element_html is None:
            element_html = soup.new_tag(name=self.html_tag)
            self._inject_html_element_content(element_html, **kwargs)
        element_html["class"] = self.element.category
        element_html["id"] = self.element.id
        self._inject_html_element_attrs(element_html)
        if self.children:  # if element has children wrap it with a 'div' tag
            return self._get_children_html(soup, element_html, **kwargs)
        return element_html

    def set_children(self, children: list["ElementHtml"]) -> None:
        self.children = children


class TitleElementHtml(ElementHtml):
    _html_tag = "h%d"

    @property
    def html_tag(self) -> str:
        return self._html_tag % (self.element.metadata.category_depth or 1)


class ImageElementHtml(ElementHtml):
    _html_tag = "img"

    def _inject_html_element_content(self, element_html: Tag, **kwargs: Any) -> None:
        exclude_binary_image_data = kwargs.get("exclude_binary_image_data", False)
        if self.element.metadata.image_base64 and not exclude_binary_image_data:
            image_mime_type = self.element.metadata.image_mime_type or "image/png"
            element_html["src"] = (
                f"data:{image_mime_type};base64,{self.element.metadata.image_base64}"
            )
        element_html["alt"] = self.element.text


class TableElementHtml(ElementHtml):
    _html_tag = "table"

    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["style"] = f"{TABLE_BORDER_STYLE} {TABLE_BORDER_COLLAPSE_STYLE}"
        for tag in element_html.find_all(["tr", "th", "td"]):
            tag["style"] = TABLE_BORDER_STYLE


class LinkElementHtml(ElementHtml):
    _html_tag = "a"

    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["href"] = self.element.metadata.url or ""


class TextElementHtml(ElementHtml):
    _html_tag = "p"


class UnorderedListElementHtml(ElementHtml):
    _html_tag = "ul"

    def _get_children_html(self, soup: BeautifulSoup, element_html: Tag, **kwargs: Any) -> Tag:
        for child in self.children:
            child_html = child.get_html_element(**kwargs)
            element_html.append(child_html)
        return element_html


class OrderedListElementHtml(UnorderedListElementHtml):
    _html_tag = "ol"


class ListItemElementHtml(UnorderedListElementHtml):
    _html_tag = "li"


class LabelElementHtml(ElementHtml):
    _html_tag = "label"


class FormElementHtml(ElementHtml):
    _html_tag = "form"


class InputElementHtml(ElementHtml):
    _html_tag = "input"


class CheckboxElementHtml(InputElementHtml):
    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["type"] = "checkbox"


class CheckboxCheckedElementHtml(InputElementHtml):
    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["type"] = "checkbox"
        element_html["checked"] = "true"


class RadioElementHtml(InputElementHtml):
    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["type"] = "radio"


class RadioCheckedElementHtml(InputElementHtml):
    def _inject_html_element_attrs(self, element_html: Tag) -> None:
        element_html["type"] = "radio"
        element_html["checked"] = "true"


LIST_ELEMENTS = [ElementType.LIST_ITEM, ElementType.LIST_ITEM_OTHER]

TYPE_TO_HTML_MAP = {
    ElementType.UNCATEGORIZED_TEXT: TextElementHtml,
    ElementType.TITLE: TitleElementHtml,
    ElementType.IMAGE: ImageElementHtml,
    ElementType.TABLE: TableElementHtml,
    ElementType.LINK: LinkElementHtml,
    ElementType.TEXT: TextElementHtml,
    ElementType.PARAGRAPH: TextElementHtml,
    ElementType.LIST: OrderedListElementHtml,
    ElementType.LIST_ITEM: ListItemElementHtml,
    ElementType.LIST_ITEM_OTHER: ListItemElementHtml,
    ElementType.FIELD_NAME: LabelElementHtml,
    ElementType.BULLETED_TEXT: ListItemElementHtml,
    ElementType.FORM: FormElementHtml,
    ElementType.CAPTION: TextElementHtml,
    ElementType.CHECKED: CheckboxCheckedElementHtml,
    ElementType.UNCHECKED: CheckboxElementHtml,
    ElementType.CHECK_BOX_CHECKED: CheckboxCheckedElementHtml,
    ElementType.CHECK_BOX_UNCHECKED: CheckboxElementHtml,
    ElementType.RADIO_BUTTON_CHECKED: RadioCheckedElementHtml,
    ElementType.RADIO_BUTTON_UNCHECKED: RadioElementHtml,
    ElementType.NARRATIVE_TEXT: TextElementHtml,
    ElementType.FIGURE_CAPTION: TextElementHtml,
    ElementType.VALUE: InputElementHtml,
    ElementType.ABSTRACT: ElementHtml,
    ElementType.THREADING: ElementHtml,
    ElementType.COMPOSITE_ELEMENT: ElementHtml,
    ElementType.PICTURE: ElementHtml,
    ElementType.FIGURE: ElementHtml,
    ElementType.ADDRESS: ElementHtml,
    ElementType.EMAIL_ADDRESS: ElementHtml,
    ElementType.PAGE_BREAK: ElementHtml,
    ElementType.FORMULA: ElementHtml,
    ElementType.HEADER: ElementHtml,
    ElementType.HEADLINE: ElementHtml,
    ElementType.SUB_HEADLINE: ElementHtml,
    ElementType.PAGE_HEADER: ElementHtml,
    ElementType.SECTION_HEADER: ElementHtml,
    ElementType.FOOTER: ElementHtml,
    ElementType.FOOTNOTE: ElementHtml,
    ElementType.PAGE_FOOTER: ElementHtml,
    ElementType.PAGE_NUMBER: ElementHtml,
    ElementType.CODE_SNIPPET: ElementHtml,
    ElementType.FORM_KEYS_VALUES: ElementHtml,
    ElementType.DOCUMENT_DATA: ElementHtml,
}


def _group_element_children(children: list[ElementHtml]) -> list[ElementHtml]:
    grouped_children: list[ElementHtml] = []
    temp_group: list["ElementHtml"] = []
    prev_grouping = False
    for child in children:
        grouping = child.element.category in LIST_ELEMENTS
        if grouping:
            temp_group.append(child)
        elif prev_grouping:
            grouped_children.append(OrderedListElementHtml(Element(), temp_group))
            grouped_children.append(child)
            temp_group = []
        else:
            grouped_children.append(child)
        prev_grouping = grouping
    if temp_group:
        grouped_children.append(OrderedListElementHtml(Element(), temp_group))
    return grouped_children


def _elements_to_html_tags_by_parent(elements: list[ElementHtml]) -> list[ElementHtml]:
    parent_to_children_map: dict[str, list[ElementHtml]] = defaultdict(list)
    for element in elements:
        if element.element.metadata.parent_id is not None:
            parent_to_children_map[element.element.metadata.parent_id].append(element)
    for parent_id, children in parent_to_children_map.items():
        grouped_children = _group_element_children(children)
        parent = next((el for el in elements if el.element.id == parent_id), None)
        if parent is None:
            logger.warning(f"Parent element with id {parent_id} not found. Skipping.")
            continue
        parent.set_children(grouped_children)
    return [el for el in elements if el.element.metadata.parent_id is None]


def _elements_to_html_tags(
    elements: list[Element], exclude_binary_image_data: bool = False
) -> list[Tag]:
    elements_html = [
        TYPE_TO_HTML_MAP.get(element.category, ElementHtml)(element) for element in elements
    ]
    elements_html = _elements_to_html_tags_by_parent(elements_html)
    return [
        element_html.get_html_element(exclude_binary_image_data=exclude_binary_image_data)
        for element_html in elements_html
    ]


def _elements_to_html_tags_by_page(
    elements: list[Element], exclude_binary_image_data: bool = False
) -> list[Tag]:
    soup = BeautifulSoup("", HTML_PARSER)
    pages_tags: list[Tag] = []
    grouped_elements = group_elements_by_page(elements)
    for page, g_elements in enumerate(grouped_elements, start=1):
        page_html = soup.new_tag(name="div", attrs={"data-page_number": page})
        elements_html = _elements_to_html_tags(g_elements, exclude_binary_image_data)
        for element_html in elements_html:
            page_html.append(element_html)
        pages_tags.append(page_html)
    return pages_tags


def group_elements_by_page(
    unstructured_elements: list[Element],
) -> list[list[Element]]:
    pages_dict: defaultdict[int, list[Element]] = defaultdict(list)

    for element in unstructured_elements:
        page_number = element.metadata.page_number
        if page_number is None:
            logger.warning(f"Page number is not set for an element {element.id}. Skipping.")
            continue
        pages_dict[page_number].append(element)

    pages_list = list(pages_dict.values())
    return pages_list


def elements_to_html(
    elements: list[Element],
    exclude_binary_image_data: bool = False,
    no_group_by_page: bool = False,
) -> str:
    soup = BeautifulSoup(HTML_TEMPLATE, HTML_PARSER)
    if soup.body is None:
        raise ValueError("Body tag not found in the HTML template")
    elements_html = (
        _elements_to_html_tags(elements, exclude_binary_image_data)
        if no_group_by_page
        else _elements_to_html_tags_by_page(elements, exclude_binary_image_data)
    )
    for element_html in elements_html:
        soup.body.append(element_html)
    return soup.prettify()
