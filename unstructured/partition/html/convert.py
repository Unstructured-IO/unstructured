import logging
from collections import defaultdict
from typing import Any

from bs4 import BeautifulSoup, Tag

from unstructured.documents.elements import Element, ElementType

logger = logging.getLogger(__name__)


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


def _element_to_html_attrs(element: Element) -> dict[str, Any]:
    element_attrs = element.to_dict()
    element_metadata = element_attrs.pop("metadata", {})
    if element_metadata is not None:
        element_attrs = {
            **{key: str(val) for key, val in element_attrs.items()},
            **{key: str(val) for key, val in element_metadata.items()},
        }
    return {f"data-{key}": value for key, value in element_attrs.items()}


def _elements_to_html_tags(
    elements: list[Element], exclude_binary_image_data: bool = False
) -> list[Tag]:
    soup = BeautifulSoup("", "html.parser")
    elements_tags: list[Tag] = []
    for element in elements:
        element_html: Tag
        element_attrs = _element_to_html_attrs(element)
        if (
            element.category == ElementType.IMAGE
            and element.metadata.image_base64
            and not exclude_binary_image_data
        ):
            image_mime_type = element.metadata.image_mime_type
            if image_mime_type is None:
                logger.warning(
                    "Image MIME type is not set for an element. Assuming the image is a PNG."
                )
                image_mime_type = "image/png"
            element_attrs.pop("data-image_base64", None)
            element_html = soup.new_tag(name="img", attrs=element_attrs)
            element_html["src"] = f"data:{image_mime_type};base64, {element.metadata.image_base64}"
        elif element.category == ElementType.TABLE and element.metadata.text_as_html:
            table_html = BeautifulSoup(element.metadata.text_as_html, "html.parser")
            element_html = table_html.find()
            element_html["style"] = f"{TABLE_BORDER_STYLE} {TABLE_BORDER_COLLAPSE_STYLE}"
            for tag in element_html.find_all(["tr", "th", "td"]):
                tag["style"] = TABLE_BORDER_STYLE
            element_html.attrs.update(element_attrs)
        else:
            element_html = soup.new_tag(name="div", attrs=element_attrs)
            element_html.string = element.text
        elements_tags.append(element_html)
    return elements_tags


def _elements_to_html_tags_by_page(
    elements: list[Element], exclude_binary_image_data: bool = False
) -> list[Tag]:
    soup = BeautifulSoup("", "html.parser")
    pages_tags: list[Tag] = []
    grouped_elements = group_elements_by_page(elements)
    for page, elements in enumerate(grouped_elements, start=1):
        page_html = soup.new_tag(name="div", attrs={"data-page_number": page})
        elements_html = _elements_to_html_tags(elements, exclude_binary_image_data)
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
    soup = BeautifulSoup(HTML_TEMPLATE, "html.parser")
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
