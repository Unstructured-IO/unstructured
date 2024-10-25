from __future__ import annotations

import html
from collections import OrderedDict
from typing import Sequence, Type

from bs4 import BeautifulSoup, Tag

from unstructured.documents.elements import (
    TYPE_TO_TEXT_ELEMENT_MAP,
    Element,
    ElementMetadata,
    Text,
)
from unstructured.documents.mappings import (
    CSS_CLASS_TO_ELEMENT_TYPE_MAP,
    EXCLUSIVE_HTML_TAG_TO_ELEMENT_TYPE_MAP,
    HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP,
    ONTOLOGY_CLASS_NAME_TO_UNSTRUCTURED_ELEMENT_TYPE_NAME,
)
from unstructured.documents.ontology import (
    Document,
    ElementTypeEnum,
    OntologyElement,
    Page,
    Paragraph,
    UncategorizedText,
)


def ontology_to_unstructured_elements(
    ontology_element: OntologyElement,
    parent_id: str = None,
    page_number: int = None,
    depth: int = 0,
    filename: str | None = None,
) -> list[Element]:
    """
    Converts an OntologyElement object to a list of unstructured Element objects.

    To preserve the structure of the ontology, the function is recursive
    and the tree structure is represented in flatten list by the parent_id
    attribute in the metadata of each Element object.
    To preserve all the attributes of the ontology element, the HTML code
    is injected to unstructured Element in ElementMetadata.text_as_html attribute.

    For Layout elements, the function creates an empty Text Element (with the
    HTML code injected the same way).

    TODO (Pluto): Better way would be to have special Element type in Unstructured

    Args:
        ontology_element (OntologyElement): The ontology element to be converted.
        parent_id (str, optional): The ID of the parent element. Defaults to None.
        page_number (int, optional): The page number of the element. Defaults to None.
        depth (int, optional): The depth of the element in the hierarchy. Defaults to 0.

    Returns:
        list[Element]: A list of unstructured Element objects.
    """
    elements_to_return = []
    if ontology_element.elementType == ElementTypeEnum.layout:

        if page_number is None and isinstance(ontology_element, Page):
            page_number = ontology_element.page_number

        if not isinstance(ontology_element, Document):
            elements_to_return += [
                Text(
                    text="",
                    element_id=ontology_element.id,
                    detection_origin="vlm_partitioner",
                    metadata=ElementMetadata(
                        parent_id=parent_id,
                        text_as_html=ontology_element.to_html(add_children=False),
                        page_number=page_number,
                        category_depth=depth,
                        filename=filename,
                    ),
                )
            ]
        childreen = []
        for child in ontology_element.children:
            childreen += ontology_to_unstructured_elements(
                child,
                parent_id=ontology_element.id,
                page_number=page_number,
                depth=0 if isinstance(ontology_element, Document) else depth + 1,
                filename=filename,
            )

        elements_to_return += childreen
    else:
        unstructured_element_class_name = ONTOLOGY_CLASS_NAME_TO_UNSTRUCTURED_ELEMENT_TYPE_NAME[
            ontology_element.__class__.__name__
        ]
        element_class = TYPE_TO_TEXT_ELEMENT_MAP[unstructured_element_class_name]
        html_code_of_ontology_element = ontology_element.to_html()
        element_text = (
            BeautifulSoup(html_code_of_ontology_element, "html.parser").get_text().strip()
        )
        # TODO value attribute from form input should be added to the text
        unstructured_element = element_class(
            text=element_text,
            element_id=ontology_element.id,
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                parent_id=parent_id,
                text_as_html=html_code_of_ontology_element,
                page_number=page_number,
                category_depth=depth,
                filename=filename,
            ),
        )
        elements_to_return = [unstructured_element]

    return elements_to_return


def unstructured_elements_to_ontology(unstructured_elements: Sequence[Element]) -> OntologyElement:
    """
    Converts a sequence of unstructured Element objects to an OntologyElement object.

    The function caches the elements in a dictionary and each element is assigned to its parent.
    At the end the root element is popped from the dictionary and returned.

    Such approach comes with limitations:
        - The parent element has to be in the list before the child element

    Args:
        unstructured_elements (Sequence[Element]): The sequence of unstructured Element objects.

    Returns:
        OntologyElement: The converted OntologyElement object.
    """
    id_to_element_mapping = OrderedDict()

    document_element_id = unstructured_elements[0].metadata.parent_id

    if document_element_id is None:
        document_element_id = OntologyElement.generate_unique_id()
        unstructured_elements[0].metadata.parent_id = document_element_id

    id_to_element_mapping[document_element_id] = Document(
        additional_attributes={"id": document_element_id}
    )

    for element in unstructured_elements:
        html_as_tag = BeautifulSoup(element.metadata.text_as_html, "html.parser").find()
        ontology_element = parse_html_to_ontology_element(html_as_tag)
        # Note: Each HTML of non-terminal Element doesn't have children in HTML
        # So we just add Ontology Element with tag and class, later children are appended by
        # parent_id.
        # For terminal Elements entire HTML is added to text_as_html, thus it allows us to
        # recreate the entire HTML structure

        id_to_element_mapping[ontology_element.id] = ontology_element

        if element.metadata.parent_id and element.metadata.parent_id in id_to_element_mapping:
            id_to_element_mapping[element.metadata.parent_id].children.append(ontology_element)

    root_id, root_element = id_to_element_mapping.popitem(last=False)
    return root_element


def parse_html_to_ontology(html_code: str) -> OntologyElement:
    """
    Parses the given HTML code and converts it into an Element object.

    Args:
        html_code (str): The HTML code to be parsed.
            Parsing HTML will start from <div class="Page">.

    Returns:
        OntologyElement: The parsed Element object.

    Raises:
        ValueError: If no <body class="Document"> element is found in the HTML.
    """
    html_code = remove_empty_divs_from_html_content(html_code)
    html_code = remove_empty_tags_from_html_content(html_code)
    soup = BeautifulSoup(html_code, "html.parser")
    document = soup.find("body", class_="Document")
    if not document:
        document = soup.find("div", class_="Page")

    if not document:
        raise ValueError(
            "No <body class='Document'> or <div class='Page'> element found in the HTML."
        )

    document_element = parse_html_to_ontology_element(document)
    return document_element


def remove_empty_divs_from_html_content(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    divs = soup.find_all("div")
    for div in reversed(divs):
        if not div.attrs:
            div.unwrap()
    return str(soup)


def remove_empty_tags_from_html_content(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    def is_empty(tag):
        # Remove only specific tags, omit self-closing ones
        if tag.name not in ["p", "span", "div", "h1", "h2", "h3", "h4", "h5", "h6"]:
            return False

        if tag.find():
            return False

        if tag.attrs:
            return False

        if not tag.get_text(strip=True):
            return True

        return False

    def remove_empty_tags(soup):
        for tag in soup.find_all():
            if is_empty(tag):
                tag.decompose()

    remove_empty_tags(soup)

    return str(soup)


def parse_html_to_ontology_element(soup: Tag) -> OntologyElement | None:
    """
    Converts a BeautifulSoup Tag object into an OntologyElement object. This function is recursive.
    First tries to recognize a class from Unstructured Ontology, then if class is matched tries
    to go deeper inside HTML tree. The recursive parsing is ended if the class is not recognized or
    there are no HTML Tags inside HTML - just text. Then it is parsed to
    Paragraph or UncategorizedText object.

    Args:
        soup (Tag): The BeautifulSoup Tag object to be converted.

    Returns:
        OntologyElement: The converted OntologyElement object.
    """
    ontology_html_tag, ontology_class = extract_tag_and_ontology_class_from_tag(soup)
    escaped_attrs = get_escaped_attributes(soup)

    if soup.name == "br":  # Note(Pluto) should it be <br class="UncategorizedText">?
        return Paragraph(
            text="",
            css_class_name=None,
            html_tag_name="br",
            additional_attributes=escaped_attrs,
        )

    has_children = (
        (ontology_class != UncategorizedText)
        and any(isinstance(content, Tag) for content in soup.contents)
        or ontology_class().elementType == ElementTypeEnum.layout
    )

    if has_children:
        text = ""
        children = [
            (
                parse_html_to_ontology_element(child)
                if isinstance(child, Tag)
                else Paragraph(text=str(child).strip())
            )
            for child in soup.children
            if str(child).strip()
        ]
    else:
        text = "\n".join([str(content).strip() for content in soup.contents]).strip()
        children = []

    output_element = ontology_class(
        text=text,
        children=children,
        html_tag_name=ontology_html_tag,
        additional_attributes=escaped_attrs,
    )
    # TODO (Pluto): <input class="FormFieldValue"/> requires being wrapped in <label> tags
    return output_element


def extract_tag_and_ontology_class_from_tag(soup: Tag) -> tuple[str, Type[OntologyElement]]:
    """
    Extracts the HTML tag and corresponding ontology class
    from a BeautifulSoup Tag object. The CSS class is prioritized over
    the HTML tag. If not recognized soup.name and UnstructuredText is returned.

    Args:
        soup (Tag): The BeautifulSoup Tag object to extract information from.

    Returns:
        tuple: A tuple containing the HTML tag (str) and the ontology class (Type[OntologyElement]).
    """
    html_tag, element_class = None, None

    # Scenario 1: Valid Ontology Element
    if soup.attrs.get("class"):
        html_tag, element_class = soup.name, HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP.get(
            (soup.name, soup.attrs["class"][0])
        )

    # Scenario 2: HTML tag incorrect, CSS class correct
    # Fallback to css name selector and overwrite html tag
    if (
        not element_class
        and soup.attrs.get("class")
        and soup.attrs["class"][0] in CSS_CLASS_TO_ELEMENT_TYPE_MAP
    ):
        element_class = CSS_CLASS_TO_ELEMENT_TYPE_MAP.get(soup.attrs["class"][0])
        html_tag = element_class().allowed_tags[0]

    # Scenario 3: CSS class incorrect, but HTML tag correct and exclusive in ontology
    if not element_class and soup.name in EXCLUSIVE_HTML_TAG_TO_ELEMENT_TYPE_MAP:
        html_tag, element_class = soup.name, EXCLUSIVE_HTML_TAG_TO_ELEMENT_TYPE_MAP[soup.name]

    # Scenario 4: CSS class incorrect, HTML tag incorrect
    # Fallback to default UncategorizedText
    if not element_class:
        # TODO (Pluto): Sometimes we could infer that from parent type and soup.name
        #  e.g. parent=FormField soup.name=input -> element=FormFieldInput

        html_tag = "span"
        element_class = UncategorizedText

    return html_tag, element_class


def get_escaped_attributes(soup: Tag):
    """
    Escapes the attributes of a BeautifulSoup Tag object.

    Args:
        soup (Tag): The BeautifulSoup Tag object whose attributes need to be escaped.

    Returns:
        dict: A dictionary with escaped attribute names and values.
    """
    escaped_attrs = {}
    for key, value in soup.attrs.items():
        escaped_key = html.escape(key)
        escaped_value = None
        if value:
            if isinstance(value, list):
                escaped_value = [html.escape(v) for v in value]
            else:
                escaped_value = html.escape(value)
        escaped_attrs[escaped_key] = escaped_value
    return escaped_attrs
