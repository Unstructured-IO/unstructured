from __future__ import annotations

from itertools import chain
from typing import Sequence, Type

from bs4 import BeautifulSoup, Tag

from unstructured.documents import elements, ontology
from unstructured.documents.html_sanitization import sanitize_attributes
from unstructured.documents.mappings import (
    CSS_CLASS_TO_ELEMENT_TYPE_MAP,
    HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP,
    HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP,
    ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE,
)
from unstructured.partition.common.metadata import (
    HEADING_TAGS,
    category_depth_from_html_tag,
)

RECURSION_LIMIT = 50


def ontology_to_unstructured_elements(
    ontology_element: ontology.OntologyElement,
    parent_id: str | None = None,
    page_number: int | None = None,
    depth: int = 0,
    filename: str | None = None,
    add_img_alt_text: bool = True,
) -> list[elements.Element]:
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
        filename (str, optional): The name of the file the element comes from. Defaults to None.
        add_img_alt_text (bool): Whether to include the alternative text of images
                                            in the output. Defaults to True.
    Returns:
        list[Element]: A list of unstructured Element objects.

    Note on `category_depth` and `parent_id` (ML-1328):
        `category_depth` is derived from the element's HTML *heading level* (h1 -> 0, h2 -> 1, ...)
        via the shared `category_depth_from_html_tag` helper, NOT from DOM/recursion nesting depth.
        This keeps the v2 (ontology) parser consistent with the v1 parser and with the documented
        metadata contract, and makes depth independent of layout (e.g. multi-column pages no longer
        bump every element's depth).

        `parent_id` is left to the metadata layer, like every other partitioner. Layout/container
        elements (Page, Column, ...) keep their tree parent so the physical layout structure is
        preserved; content elements are emitted with ``parent_id=None``. The `@apply_metadata`
        decorator that wraps `partition_html` then runs `set_element_hierarchy`, which fills each
        content element's heading-based parent (a subsection's parent becomes its enclosing heading)
        from the heading-level `category_depth` and skips the containers that already have a parent.
        Both production callers -- `partition_html` and the VLM partitioner -- go through that
        decorator, so this converter does not run `set_element_hierarchy` itself.
    """
    # -- The worker carries each element's DOM-nesting depth alongside it (used only to decide
    # -- inline merging); strip those depths here so the public output is plain Elements. --
    elements_with_depth = _ontology_to_unstructured_elements(
        ontology_element,
        parent_id=parent_id,
        page_number=page_number,
        depth=depth,
        filename=filename,
        add_img_alt_text=add_img_alt_text,
    )
    return [element for element, _nesting_depth in elements_with_depth]


def _ontology_to_unstructured_elements(
    ontology_element: ontology.OntologyElement,
    parent_id: str | None = None,
    page_number: int | None = None,
    depth: int = 0,
    filename: str | None = None,
    add_img_alt_text: bool = True,
) -> list[tuple[elements.Element, int]]:
    """Recursive worker for `ontology_to_unstructured_elements`.

    Builds the flat element list with layout-container `parent_id` set to the tree parent and
    content `parent_id` left as ``None`` -- the `@apply_metadata` decorator on `partition_html`
    fills in content elements' heading-based `parent_id` via `set_element_hierarchy`.

    Each element is returned paired with its DOM-nesting `depth`. That depth is recursion-local
    bookkeeping consumed only by `combine_inline_elements` (to gate inline merging by tree level);
    it is deliberately NOT stored on the element or its `ElementMetadata`, and the public wrapper
    discards it.
    """
    elements_to_return: list[tuple[elements.Element, int]] = []
    if ontology_element.elementType == ontology.ElementTypeEnum.layout and depth <= RECURSION_LIMIT:
        if page_number is None and isinstance(ontology_element, ontology.Page):
            page_number = ontology_element.page_number

        if not isinstance(ontology_element, ontology.Document):
            # -- Layout/container element (Page, Column, ...). Keep its tree `parent_id` so the
            # -- physical layout structure is preserved, and leave `category_depth` unset -- a
            # -- container is not a heading. --
            container_element = elements.Text(
                text="",
                element_id=ontology_element.id,
                detection_origin="vlm_partitioner",
                metadata=elements.ElementMetadata(
                    parent_id=parent_id,
                    text_as_html=ontology_element.to_html(add_children=False),
                    page_number=page_number,
                    category_depth=None,
                    filename=filename,
                ),
            )
            # -- pair the container with its DOM-nesting depth, used only to decide inline merging;
            # -- `category_depth` now carries heading level, not nesting, so it can't be reused. --
            elements_to_return += [(container_element, depth)]
        children: list[tuple[elements.Element, int]] = []
        for child in ontology_element.children:
            child = _ontology_to_unstructured_elements(
                child,
                parent_id=ontology_element.id,
                page_number=page_number,
                depth=0 if isinstance(ontology_element, ontology.Document) else depth + 1,
                filename=filename,
                add_img_alt_text=add_img_alt_text,
            )
            children += child

        combined_children = combine_inline_elements(children)
        elements_to_return += combined_children
    else:
        element_class: type[elements.Element] = ONTOLOGY_CLASS_TO_UNSTRUCTURED_ELEMENT_TYPE[
            ontology_element.__class__
        ]
        html_code_of_ontology_element = ontology_element.to_html()
        element_text = ontology_element.to_text(add_img_alt_text=add_img_alt_text)

        # -- `category_depth` from heading level (not nesting depth); see function docstring. --
        category_depth = category_depth_from_html_tag(
            element_class,
            ontology_element.html_tag_name,
        )

        unstructured_element = element_class(
            text=element_text,  # type: ignore
            element_id=ontology_element.id,
            detection_origin="vlm_partitioner",
            metadata=elements.ElementMetadata(
                # -- `parent_id` left unset; `@apply_metadata` runs `set_element_hierarchy` to
                # -- assign a heading-based parent (see the docstring). --
                parent_id=None,
                text_as_html=html_code_of_ontology_element,
                page_number=page_number,
                category_depth=category_depth,
                filename=filename,
            ),
        )
        elements_to_return = [(unstructured_element, depth)]

    return elements_to_return


def combine_inline_elements(
    elements_with_depth: list[tuple[elements.Element, int]],
) -> list[tuple[elements.Element, int]]:
    """
    Combines consecutive inline elements into a single element. Inline elements
    can be also combined with text elements.

    Combined elements contains multiple HTML tags together eg.
    {
        'text': "Text from element 1 Text from element 2",
        'metadata': {
            'text_as_html': "<p>Text from element 1</p><a>Text from element 2</a>"
        }
    }

    Each element is paired with its DOM-nesting depth; merging is only allowed between elements at
    the same depth (see `can_unstructured_elements_be_merged`). The depth travels with the element
    rather than being stored on it.

    Args:
        elements_with_depth (list[tuple[Element, int]]): (element, nesting-depth) pairs to combine.

    Returns:
        list[tuple[Element, int]]: The combined (element, nesting-depth) pairs.
    """
    result_elements: list[tuple[elements.Element, int]] = []

    current: tuple[elements.Element, int] | None = None
    for nxt in elements_with_depth:
        if current is None:
            current = nxt
            continue

        current_element, current_depth = current
        next_element, next_depth = nxt
        if can_unstructured_elements_be_merged(
            current_element, next_element, current_depth=current_depth, next_depth=next_depth
        ):
            current_element.text += " " + next_element.text
            current_element.metadata.text_as_html += next_element.metadata.text_as_html
        else:
            result_elements.append(current)
            current = nxt

    if current is not None:
        result_elements.append(current)

    return result_elements


def can_unstructured_elements_be_merged(
    current_element: elements.Element,
    next_element: elements.Element,
    *,
    current_depth: int,
    next_depth: int,
) -> bool:
    """
    Elements can be merged when:
    - They are on the same level in the HTML tree
    - Neither of them has children
    - All elements are inline elements or text element
    """
    # NOTE(ML-1328): "same level in the HTML tree" is the DOM-nesting depth, passed in alongside
    # each element. It used to live on `category_depth`, but that field now carries heading level,
    # so it can no longer be used as the nesting signal here.
    if current_depth != next_depth:
        return False

    current_html_tags = BeautifulSoup(
        current_element.metadata.text_as_html, "html.parser"
    ).find_all(recursive=False)
    next_html_tags = BeautifulSoup(next_element.metadata.text_as_html, "html.parser").find_all(
        recursive=False
    )

    ontology_elements = [
        parse_html_to_ontology_element(html_tag)
        for html_tag in chain(current_html_tags, next_html_tags)
    ]

    for ontology_element in ontology_elements:
        if ontology_element.children:
            return False

        if not (is_inline_element(ontology_element) or is_text_element(ontology_element)):
            return False

    return True


def is_text_element(ontology_element: ontology.OntologyElement) -> bool:
    """Categories or classes that we want to combine with inline text"""

    text_classes = [
        ontology.NarrativeText,
        ontology.Quote,
        ontology.Paragraph,
        ontology.Footnote,
        ontology.FootnoteReference,
        ontology.Citation,
        ontology.Bibliography,
        ontology.Glossary,
    ]
    text_categories = [ontology.ElementTypeEnum.metadata]

    if any(isinstance(ontology_element, class_) for class_ in text_classes):
        return True

    return any(ontology_element.elementType == category for category in text_categories)


def is_inline_element(ontology_element: ontology.OntologyElement) -> bool:
    """Categories or classes that we want to combine with text elements"""

    inline_classes = [ontology.Hyperlink]
    inline_categories = [
        ontology.ElementTypeEnum.specialized_text,
        ontology.ElementTypeEnum.annotation,
    ]

    if any(isinstance(ontology_element, class_) for class_ in inline_classes):
        return True

    return any(ontology_element.elementType == category for category in inline_categories)


def unstructured_elements_to_ontology(
    unstructured_elements: Sequence[elements.Element],
) -> ontology.OntologyElement:
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
    if not unstructured_elements:
        # -- empty input -> empty Document; avoid an IndexError dereferencing element[0] --
        return ontology.Document(
            additional_attributes={"id": ontology.OntologyElement.generate_unique_id()}
        )

    root_element_id = unstructured_elements[0].metadata.parent_id

    if root_element_id is None:
        root_element_id = ontology.OntologyElement.generate_unique_id()
        unstructured_elements[0].metadata.parent_id = root_element_id

    root_element = ontology.Document(additional_attributes={"id": root_element_id})

    # NOTE(ML-1328): Tree reconstruction is driven by the *layout-container* elements (Page,
    # Column, Section, ...), which retain their tree `parent_id`. Content-element `parent_id` is no
    # longer the tree parent -- it is the heading-based parent assigned by `set_element_hierarchy`
    # -- so it must NOT be used to rebuild the layout tree. Instead, each content element is nested
    # in the innermost open layout container, tracked with a stack keyed on the containers' own
    # (tree) `parent_id`. This is independent of document content `parent_id` and reproduces the
    # original layout nesting exactly.
    container_stack: list[tuple[str, ontology.OntologyElement]] = [(root_element_id, root_element)]

    for element in unstructured_elements:
        # -- an element with no HTML payload carries nothing to rebuild the tree from;
        # -- skip it per-element rather than letting BeautifulSoup(None) abort the whole
        # -- reconstruction (e.g. mixed/partially-stripped element streams). --
        if not element.metadata.text_as_html:
            continue
        html_as_tags = BeautifulSoup(element.metadata.text_as_html, "html.parser").find_all(
            recursive=False
        )
        for html_as_tag in html_as_tags:
            ontology_element = parse_html_to_ontology_element(html_as_tag)

            is_layout_container = ontology_element.elementType == ontology.ElementTypeEnum.layout
            if is_layout_container:
                # -- pop back to this container's tree parent, then attach + open it. Only pop if
                # -- that parent is actually open on the stack; a `parent_id` matching no open
                # -- container (e.g. malformed/reordered input that violates the documented
                # -- parent-before-child precondition) must not pop past valid ancestors to root --
                # -- which would mis-nest later content. In that case attach to the current
                # -- innermost container instead, preserving document order and losing nothing. --
                # -- a container with no `parent_id` is a top-level container -> attach at root --
                parent_id = element.metadata.parent_id or root_element_id
                if any(container_id == parent_id for container_id, _ in container_stack):
                    while len(container_stack) > 1 and container_stack[-1][0] != parent_id:
                        container_stack.pop()
                container_stack[-1][1].children.append(ontology_element)
                container_stack.append((element.id, ontology_element))
            else:
                # -- content nests in the innermost currently-open layout container --
                container_stack[-1][1].children.append(ontology_element)

    return root_element


def parse_html_to_ontology(html_code: str) -> ontology.OntologyElement:
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
        if tag.name not in (*HEADING_TAGS, "p", "span", "div"):
            return False

        if tag.find():
            return False

        if tag.attrs:
            return False

        return bool(not tag.get_text(strip=True))

    def remove_empty_tags(soup):
        for tag in soup.find_all():
            if is_empty(tag):
                tag.decompose()

    remove_empty_tags(soup)

    return str(soup)


def parse_html_to_ontology_element(soup: Tag, recursion_depth: int = 1) -> ontology.OntologyElement:
    """
    Converts a BeautifulSoup Tag object into an OntologyElement object. This function is recursive.
    First tries to recognize a class from Unstructured Ontology, then if class is matched tries
    to go deeper inside HTML tree. The recursive parsing is ended if the class is not recognized or
    there are no HTML Tags inside HTML - just text. Then it is parsed to
    Paragraph or UncategorizedText object.

    Args:
        soup (Tag): The BeautifulSoup Tag object to be converted.
        recursion_depth (int): Flag to control limit of recursion depth.
    Returns:
        OntologyElement: The converted OntologyElement object.
    """
    ontology_html_tag, ontology_class = extract_tag_and_ontology_class_from_tag(soup)
    escaped_attrs = get_sanitized_attributes(soup, tag_name=ontology_html_tag)

    if soup.name == "br":  # Note(Pluto) should it be <br class="UncategorizedText">?
        return ontology.Paragraph(
            text="",
            css_class_name=None,
            html_tag_name="br",
            additional_attributes=escaped_attrs,
        )

    has_children = (
        (ontology_class != ontology.UncategorizedText)
        and any(isinstance(content, Tag) for content in soup.contents)
        or ontology_class().elementType == ontology.ElementTypeEnum.layout
    )
    should_unwrap_html = has_children and recursion_depth <= RECURSION_LIMIT

    if should_unwrap_html:
        text = ""
        children = [
            (
                parse_html_to_ontology_element(child, recursion_depth=recursion_depth + 1)
                if isinstance(child, Tag)
                else ontology.Paragraph(text=str(child).strip())
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


def extract_tag_and_ontology_class_from_tag(
    soup: Tag,
) -> tuple[str, Type[ontology.OntologyElement]]:
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
        html_tag, element_class = (
            soup.name,
            HTML_TAG_AND_CSS_NAME_TO_ELEMENT_TYPE_MAP.get((soup.name, soup.attrs["class"][0])),
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

    # Scenario 3: <input> elements, handled explicitly based on their 'type' attribute
    if not element_class and soup.name == "input":
        input_type = (str(soup.get("type")) or "").lower()
        if input_type == "checkbox":
            element_class = ontology.Checkbox
        elif input_type == "radio":
            element_class = ontology.RadioButton
        else:
            # Any other input (including missing type or text/number/etc.) is considered
            # a generic form field value.
            element_class = ontology.FormFieldValue
        html_tag = "input"

    # Scenario 4: CSS class incorrect, but HTML tag correct and exclusive in ontology
    if not element_class and soup.name in HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP:
        html_tag, element_class = soup.name, HTML_TAG_TO_DEFAULT_ELEMENT_TYPE_MAP[soup.name]

    # Scenario 5: CSS class incorrect, HTML tag incorrect
    # Fallback to default UncategorizedText
    if not element_class:
        # TODO (Pluto): Sometimes we could infer that from parent type and soup.name
        #  e.g. parent=FormField soup.name=input -> element=FormFieldInput

        html_tag = "span"
        element_class = ontology.UncategorizedText

    # Scenario 6: UncategorizedText has image and no text
    # Typically, this happens with a span or div tag with an image inside
    if element_class == ontology.UncategorizedText and soup.find("img") and not soup.text.strip():
        element_class = ontology.Image

    return html_tag, element_class


def get_sanitized_attributes(soup: Tag, tag_name: str | None = None) -> dict[str, str | list[str]]:
    """
    Sanitizes the attributes of a BeautifulSoup Tag object for the ontology.

    Drops event-handler (``on*``) attributes and URL attributes with unsafe
    schemes (``javascript:`` / ``vbscript:`` / non-image ``data:``) so an
    ontology element never carries a dangerous attribute in the first place.

    Values are intentionally left un-escaped: HTML-escaping is done exactly once,
    at emit time, in ``OntologyElement.to_html`` (see
    ``unstructured.documents.html_sanitization``). Escaping here as well would
    double-encode entities (e.g. ``&`` -> ``&amp;amp;``).

    Args:
        soup (Tag): The BeautifulSoup Tag object whose attributes to sanitize.
        tag_name: The ontology tag that will be emitted for this element.

    Returns:
        dict: A dictionary with the safe subset of attributes.
    """
    return sanitize_attributes(dict(soup.attrs), tag_name=tag_name)  # type: ignore[return-value]


# -- Backwards-compatible alias; the previous name implied it html-escaped, which
# -- it no longer does (escaping moved to emit time). --
get_escaped_attributes = get_sanitized_attributes
