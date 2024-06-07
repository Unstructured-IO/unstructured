# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import Final, Iterator, Optional, cast

from lxml import etree

from unstructured.cleaners.core import clean_bullets, replace_unicode_quotes
from unstructured.documents.base import Page
from unstructured.documents.elements import Element, ElementMetadata, Link
from unstructured.documents.html_elements import (
    HTMLAddress,
    HTMLEmailAddress,
    HTMLListItem,
    HTMLNarrativeText,
    HTMLTable,
    HTMLText,
    HTMLTitle,
)
from unstructured.documents.xml import VALID_PARSERS, XMLDocument
from unstructured.logger import logger
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)
from unstructured.partition.utils.constants import HTML_MAX_PREDECESSOR_LEN
from unstructured.utils import htmlify_matrix_of_cell_texts

TEXT_TAGS: Final[list[str]] = ["p", "a", "td", "span", "b", "font"]
LIST_ITEM_TAGS: Final[list[str]] = ["li", "dd"]
LIST_TAGS: Final[list[str]] = ["ul", "ol", "dl"]
HEADING_TAGS: Final[list[str]] = ["h1", "h2", "h3", "h4", "h5", "h6"]
TABLE_TAGS: Final[list[str]] = ["table", "tbody", "td", "tr"]
TEXTBREAK_TAGS: Final[list[str]] = ["br"]
PAGEBREAK_TAGS: Final[list[str]] = ["hr"]
EMPTY_TAGS: Final[list[str]] = PAGEBREAK_TAGS + TEXTBREAK_TAGS
HEADER_OR_FOOTER_TAGS: Final[list[str]] = ["header", "footer"]
SECTION_TAGS: Final[list[str]] = ["div", "pre"]


class HTMLDocument(XMLDocument):
    """Class for handling HTML documents. Uses rules based parsing to identify sections
    of interest within the document."""

    def __init__(
        self,
        stylesheet: Optional[str] = None,
        parser: VALID_PARSERS = None,
        assemble_articles: bool = True,
    ):
        self.assembled_articles = assemble_articles
        super().__init__(stylesheet=stylesheet, parser=parser)

    def _parse_pages_from_element_tree(self) -> list[Page]:
        """Parse HTML elements into pages.

        A *page* is a subsequence of the document-elements parsed from the HTML document
        corresponding to a distinct topic. At present pagination is determined by `<article>`
        elements that surround something like a blog-post. Each article becomes its own page. If no
        article tags are present in the HTML the entire HTML document is a single page.
        """
        if self._pages:
            return self._pages
        logger.info("Reading document ...")
        pages: list[Page] = []
        etree.strip_elements(self.document_tree, ["script", "style"], with_tail=False)
        root = _find_main(self.document_tree)

        articles = _find_articles(root, assemble_articles=self.assembled_articles)
        page_number = 0
        page = Page(number=page_number)
        for article in articles:
            descendanttag_elems: tuple[etree._Element, ...] = ()
            for tag_elem in article.iter():
                if tag_elem in descendanttag_elems:
                    # Prevent repeating something that's been flagged as text as we chase it
                    # down a chain
                    continue

                if _is_text_tag(tag_elem):
                    _page_elements, descendanttag_elems = _process_text_tag(tag_elem)
                    page.elements.extend(_page_elements)

                elif _is_container_with_text(tag_elem):
                    tag_elem_tail = tag_elem.tail.strip() if tag_elem.tail else None
                    if tag_elem_tail:
                        _page_elements, descendanttag_elems = _process_text_tag(tag_elem, False)
                        page.elements.extend(_page_elements)

                        # NOTE(christine): generate a separate element using a tag tail
                        assert tag_elem.tail is not None
                        element = _text_to_element(
                            tag_elem.tail,
                            tag_elem.tag,
                            (),
                            depth=0,
                        )
                    else:
                        links = _get_links_from_tag(tag_elem)
                        emphasized_texts = _get_emphasized_texts_from_tag(tag_elem)
                        assert tag_elem.text is not None
                        element = _text_to_element(
                            tag_elem.text,
                            tag_elem.tag,
                            (),
                            depth=0,
                            links=links,
                            emphasized_texts=emphasized_texts,
                        )
                    if element is not None:
                        page.elements.append(element)

                elif _is_bulleted_table(tag_elem):
                    bulleted_text = _bulleted_text_from_table(tag_elem)
                    page.elements.extend(bulleted_text)
                    descendanttag_elems = tuple(tag_elem.iterdescendants())

                elif _is_list_item_tag(tag_elem):
                    element, next_element = _process_list_item(tag_elem)
                    if element is not None:
                        page.elements.append(element)
                        descendanttag_elems = _get_bullet_descendants(
                            tag_elem,
                            next_element,
                        )

                elif tag_elem.tag in TABLE_TAGS:
                    element = _parse_HTMLTable_from_table_elem(tag_elem)
                    if element is not None:
                        page.elements.append(element)
                    if element or tag_elem.tag == "table":
                        descendanttag_elems = tuple(tag_elem.iterdescendants())

                elif tag_elem.tag in PAGEBREAK_TAGS and len(page.elements) > 0:
                    pages.append(page)
                    page_number += 1
                    page = Page(number=page_number)

            if len(page.elements) > 0:
                pages.append(page)
                page_number += 1
                page = Page(number=page_number)

        return pages


# -- candidate HTMLDocument methods --------------------------------------------------------------


def _find_articles(root: etree._Element, assemble_articles: bool = True) -> list[etree._Element]:
    """Parse articles from `root` of an HTML document.

    Each `<article>` element in the HTML becomes its own "sub-document" (article). If no article
    elements are present, the entire document (`root`) is returned as the single document article.
    """
    if assemble_articles is False:
        return [root]

    articles = root.findall(".//article")
    if len(articles) == 0:
        # NOTE(robinson) - ref: https://schema.org/Article
        articles = root.findall(".//div[@itemprop='articleBody']")
    return [root] if len(articles) == 0 else articles


def _find_main(root: etree._Element) -> etree._Element:
    """The first <main> tag under `root` if it exists, othewise `root`."""
    main_tag_elem = root.find(".//main")
    return main_tag_elem if main_tag_elem is not None else root


# -- tag classifiers -----------------------------------------------------------------------------


def _is_bulleted_table(table_elem: etree._Element) -> bool:
    """True when all text in `table_elem` is bulleted text.

    A table-row containing no text is not considered, but at least one bulleted-text item must be
    present. A table with no text in any row is not a bulleted table.
    """
    if table_elem.tag != "table":
        return False

    trs = table_elem.findall(".//tr")
    tr_texts = [_construct_text(tr) for tr in trs]

    # -- a table with no text is not a bulleted table --
    if all(not text for text in tr_texts):
        return False

    # -- all non-empty rows must contain bulleted text --
    if any(text and not is_bulleted_text(text) for text in tr_texts):
        return False

    return True


def _is_container_with_text(tag_elem: etree._Element) -> bool:
    """Checks if a tag is a container that also happens to contain text.

    Example
    -------
    <div>Hi there,
        <div>This is my message.</div>
        <div>Please read my message!</div>
    </div>
    """
    if tag_elem.tag not in SECTION_TAGS + ["body"] or len(tag_elem) == 0:
        return False

    tag_elem_text = tag_elem.text.strip() if tag_elem.text else None
    tag_elem_tail = tag_elem.tail.strip() if tag_elem.tail else None
    if not tag_elem_text and not tag_elem_tail:
        return False

    return True


def _is_list_item_tag(tag_elem: etree._Element) -> bool:
    """True when `tag_elem` contains bulleted text."""
    return tag_elem.tag in LIST_ITEM_TAGS or (
        tag_elem.tag in SECTION_TAGS and is_bulleted_text(_construct_text(tag_elem))
    )


def _is_text_tag(
    tag_elem: etree._Element, max_predecessor_len: int = HTML_MAX_PREDECESSOR_LEN
) -> bool:
    """True when `tag_element` potentially contains narrative text."""
    # NOTE(robinson) - Only consider elements with limited depth. Otherwise,
    # it could be the text representation of a giant div
    # Exclude empty tags from tag_elem
    empty_elems_len = len([el for el in tag_elem if el.tag in EMPTY_TAGS])
    if len(tag_elem) > max_predecessor_len + empty_elems_len:
        return False

    if tag_elem.tag in TEXT_TAGS + HEADING_TAGS + TEXTBREAK_TAGS:
        return True

    # NOTE(robinson) - This indicates that a div tag has no children. If that's the
    # case and the tag has text, its potential a text tag
    children = list(tag_elem)
    if tag_elem.tag in SECTION_TAGS + ["body"] and len(children) == 0:
        return True

    if _has_adjacent_bulleted_spans(tag_elem, children):
        return True

    return False


# -- tag processors ------------------------------------------------------------------------------


def _bulleted_text_from_table(table: etree._Element) -> list[Element]:
    """Extracts bulletized narrative text from the `<table>` element in `table`.

    NOTE: if a table has mixed bullets and non-bullets, only bullets are extracted. I.e., _read()
    will drop non-bullet narrative text in the table.
    """
    bulleted_text: list[Element] = []
    rows = table.findall(".//tr")
    for row in rows:
        text = _construct_text(row)
        if is_bulleted_text(text):
            bulleted_text.append(HTMLListItem(text=clean_bullets(text), tag=row.tag))
    return bulleted_text


def _construct_text(tag_elem: etree._Element, include_tail_text: bool = True) -> str:
    """Extract "clean"" text from `tag_elem`."""
    text = "".join(str(t) for t in tag_elem.itertext() if t)

    if include_tail_text and tag_elem.tail:
        text = text + tag_elem.tail

    text = replace_unicode_quotes(text)
    return text.strip()


def _get_bullet_descendants(
    element: Optional[etree._Element], next_element: Optional[etree._Element]
) -> tuple[etree._Element, ...]:
    """Helper for list-item processing.

    Gathers the descendants of `next_element` so they can be marked visited.
    """
    return () if element is None or next_element is None else tuple(next_element.iterdescendants())


def _get_emphasized_texts_from_tag(tag_elem: etree._Element) -> list[dict[str, str]]:
    """Emphasized text within and below `tag_element`.

    Emphasis is indicated by `<strong>`, `<em>`, `<span>`, `<b>`, `<i>` tags.
    """
    emphasized_texts: list[dict[str, str]] = []
    tags_to_track = ["strong", "em", "span", "b", "i"]

    if tag_elem.tag in tags_to_track:
        text = _construct_text(tag_elem, False)
        if text:
            emphasized_texts.append({"text": text, "tag": tag_elem.tag})

    for descendant_tag_elem in tag_elem.iterdescendants(*tags_to_track):
        text = _construct_text(descendant_tag_elem, False)
        if text:
            emphasized_texts.append({"text": text, "tag": descendant_tag_elem.tag})

    return emphasized_texts


def _get_links_from_tag(tag_elem: etree._Element) -> list[Link]:
    """Hyperlinks within and below `tag_elem`."""
    links: list[Link] = []
    tag_elem_href = tag_elem.get("href")
    if tag_elem_href:
        tag_elem_text = _construct_text(tag_elem, False)
        links.append({"text": tag_elem_text, "url": tag_elem_href, "start_index": -1})
    else:
        start_index = len(tag_elem.text.lstrip()) if tag_elem.text else 0
        for tag in tag_elem.iterdescendants():
            href = tag.get("href")
            if href:
                links.append({"text": tag.text, "url": href, "start_index": start_index})

            if tag.text and not (tag.text.isspace()):
                start_index = start_index + len(tag.text)
            if tag.tail and not (tag.tail.isspace()):
                start_index = start_index + len(tag.tail)

    return links


def _has_adjacent_bulleted_spans(tag_elem: etree._Element, children: list[etree._Element]) -> bool:
    """True when `tag_elem` is a <div> or <pre> containing two or more adjacent bulleted spans.

    A bulleted span is one beginning with a bullet. If there are two or more adjacent to each other
    they are treated as a single bulleted text element.
    """
    if tag_elem.tag in SECTION_TAGS:
        all_spans = all(child.tag == "span" for child in children)
        _is_bulleted = children[0].text is not None and is_bulleted_text(children[0].text)
        if all_spans and _is_bulleted:
            return True
    return False


def _has_break_tags(tag_elem: etree._Element) -> bool:
    """True when `tab_elem` contains a `<br>` descendant."""
    return any(descendant.tag in TEXTBREAK_TAGS for descendant in tag_elem.iterdescendants())


def _parse_HTMLTable_from_table_elem(table_elem: etree._Element) -> Optional[Element]:
    """Form `HTMLTable` element from `tbl_elem`."""
    if table_elem.tag != "table":
        return None

    # -- NOTE that this algorithm handles a nested-table by parsing all of its text into the text
    # -- for the _cell_ containing the table (and this is recursive, so a table nested within a
    # -- cell within the table within the cell too.)

    trs = cast(
        list[etree._Element], table_elem.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr")
    )

    if not trs:
        return None

    def iter_cell_texts(tr: etree._Element) -> Iterator[str]:
        """Generate the text of each cell in `tr`."""
        # -- a cell can be either a "data" cell (td) or a "heading" cell (th) --
        tds = cast(list[etree._Element], tr.xpath("./td | ./th"))
        for td in tds:
            # -- a cell can contain other elements like spans etc. so we can't count on the text
            # -- being directly below the `<td>` element. `.itertext()` gets all of it recursively.
            # -- Filter out whitespace text nodes that result from HTML formatting.
            stripped_text_nodes = (t.strip() for t in td.itertext())
            yield " ".join(t for t in stripped_text_nodes if t)

    table_data = [list(iter_cell_texts(tr)) for tr in trs]
    html_table = htmlify_matrix_of_cell_texts(table_data)
    table_text = " ".join(" ".join(t for t in row if t) for row in table_data).strip()

    if table_text == "":
        return None

    return HTMLTable(
        text=table_text,
        text_as_html=html_table,
        tag=table_elem.tag,
        ancestortags=tuple(el.tag for el in table_elem.iterancestors())[::-1],
    )


def _parse_tag(
    tag_elem: etree._Element,
    include_tail_text: bool = True,
) -> Optional[Element]:
    """Parses `tag_elem` to a Text element if it contains qualifying text.

    Ancestor tags are kept so they can be used for filtering or classification without processing
    the document tree again. In the future we might want to keep descendants too, but we don't have
    a use for them at the moment.
    """
    ancestortags: tuple[str, ...] = tuple(el.tag for el in tag_elem.iterancestors())[::-1]
    links = _get_links_from_tag(tag_elem)
    emphasized_texts = _get_emphasized_texts_from_tag(tag_elem)

    depth = (
        # TODO(newel): Check the surrounding divs to see if should be root level
        # -- zero index the depth --
        int(tag_elem.tag[1]) - 1
        if tag_elem.tag in HEADING_TAGS
        else (
            len([el for el in tag_elem.iterancestors() if el.tag in LIST_TAGS + LIST_ITEM_TAGS])
            if tag_elem.tag in LIST_TAGS + LIST_ITEM_TAGS
            else 0
        )
    )

    if tag_elem.tag == "script":
        return None
    text = _construct_text(tag_elem, include_tail_text)
    if not text:
        return None
    return _text_to_element(
        text,
        tag_elem.tag,
        ancestortags,
        links=links,
        emphasized_texts=emphasized_texts,
        depth=depth,
    )


def _process_list_item(
    tag_elem: etree._Element,
    max_predecessor_len: int = HTML_MAX_PREDECESSOR_LEN,
) -> tuple[Optional[Element], Optional[etree._Element]]:
    """Produces an `HTMLListItem` document element from `tag_elem`.

    When `tag_elem` contains bulleted text, the relevant bulleted text is extracted. Also returns
    the next html element so we can skip processing if bullets are found in a div element.
    """
    if tag_elem.tag in LIST_TAGS + LIST_ITEM_TAGS:
        text = _construct_text(tag_elem)
        links = _get_links_from_tag(tag_elem)
        emphasized_texts = _get_emphasized_texts_from_tag(tag_elem)
        depth = len(
            [el for el in tag_elem.iterancestors() if el.tag in LIST_TAGS + LIST_ITEM_TAGS],
        )
        return (
            HTMLListItem(
                text=text,
                tag=tag_elem.tag,
                links=links,
                emphasized_texts=emphasized_texts,
                metadata=ElementMetadata(category_depth=depth),
            ),
            tag_elem,
        )

    elif tag_elem.tag in SECTION_TAGS:
        text = _construct_text(tag_elem)
        next_element = tag_elem.getnext()
        if next_element is None:
            return None, None
        next_text = _construct_text(next_element)
        # NOTE(robinson) - Only consider elements with limited depth. Otherwise,
        # it could be the text representation of a giant div
        empty_elems_len = len([el for el in tag_elem if el.tag in EMPTY_TAGS])
        if len(tag_elem) > max_predecessor_len + empty_elems_len:
            return None, None
        if next_text:
            return HTMLListItem(text=next_text, tag=next_element.tag), next_element

    return None, None


def _process_text_tag(
    tag_elem: etree._Element, include_tail_text: bool = True
) -> tuple[list[Element], tuple[etree._Element, ...]]:
    """Produces a document element from `tag_elem`."""

    page_elements: list[Element] = []
    if _has_break_tags(tag_elem):
        flattened_elems = _unfurl_break_tags(tag_elem)
        for _tag_elem in flattened_elems:
            element = _parse_tag(_tag_elem, include_tail_text)
            if element is not None:
                page_elements.append(element)

    else:
        element = _parse_tag(tag_elem, include_tail_text)
        if element is not None:
            page_elements.append(element)
    descendant_tag_elems = tuple(tag_elem.iterdescendants())

    return page_elements, descendant_tag_elems


def _unfurl_break_tags(tag_elem: etree._Element) -> list[etree._Element]:
    """Sequence of `tag_elem` and its children with `<br>` elements removed.

    NOTE that these are "loose" `etree._Element` instances that are NOT linked to the original HTML
    element-tree, so methods like `.getchildren()`, `.find()` etc. will happily produce empty
    results.
    """
    unfurled: list[etree._Element] = []

    if tag_elem.text:
        _tag_elem = etree.Element(tag_elem.tag)
        _tag_elem.text = tag_elem.text
        unfurled.append(_tag_elem)

    for child in tag_elem:
        if not _has_break_tags(child):
            unfurled.append(child)
        else:
            if child.text:
                _tag_elem = etree.Element(child.tag)
                _tag_elem.text = child.text
                unfurled.append(_tag_elem)
            unfurled.extend(_unfurl_break_tags(child))

    return unfurled


# -- text-element classifier ---------------------------------------------------------------------


def _text_to_element(
    text: str,
    tag: str,
    ancestortags: tuple[str, ...],
    depth: int,
    links: list[Link] = [],
    emphasized_texts: list[dict[str, str]] = [],
) -> Optional[Element]:
    """Produce a document-element of the appropriate sub-type for `text`."""
    if is_bulleted_text(text):
        if not clean_bullets(text):
            return None
        return HTMLListItem(
            text=clean_bullets(text),
            tag=tag,
            ancestortags=ancestortags,
            links=links,
            emphasized_texts=emphasized_texts,
            metadata=ElementMetadata(category_depth=depth),
        )
    elif is_us_city_state_zip(text):
        return HTMLAddress(
            text=text,
            tag=tag,
            ancestortags=ancestortags,
            links=links,
            emphasized_texts=emphasized_texts,
        )
    elif is_email_address(text):
        return HTMLEmailAddress(
            text=text,
            tag=tag,
            links=links,
            emphasized_texts=emphasized_texts,
        )

    if len(text) < 2:
        return None
    elif _is_narrative_tag(text, tag):
        return HTMLNarrativeText(
            text,
            tag=tag,
            ancestortags=ancestortags,
            links=links,
            emphasized_texts=emphasized_texts,
        )
    elif _is_heading_tag(tag) or is_possible_title(text):
        return HTMLTitle(
            text,
            tag=tag,
            ancestortags=ancestortags,
            links=links,
            emphasized_texts=emphasized_texts,
            metadata=ElementMetadata(category_depth=depth),
        )
    else:
        return HTMLText(
            text,
            tag=tag,
            ancestortags=ancestortags,
            links=links,
            emphasized_texts=emphasized_texts,
        )


# -- HTML-specific text classifiers --------------------------------------------------------------


def _is_heading_tag(tag: str) -> bool:
    """Uses tag information to infer whether text is a heading."""
    return tag in HEADING_TAGS


def _is_narrative_tag(text: str, tag: str) -> bool:
    """Uses tag information to infer whether text is narrative."""
    return tag not in HEADING_TAGS and is_possible_narrative_text(text)
