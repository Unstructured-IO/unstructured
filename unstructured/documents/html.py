# pyright: reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Iterator, cast

from lxml import etree

from unstructured.cleaners.core import clean_bullets, replace_unicode_quotes
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    EmailAddress,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_email_address,
    is_possible_narrative_text,
    is_possible_title,
    is_us_city_state_zip,
)
from unstructured.partition.utils.constants import HTML_MAX_PREDECESSOR_LEN
from unstructured.utils import htmlify_matrix_of_cell_texts, lazyproperty

if TYPE_CHECKING:
    from unstructured.partition.html.partition import HtmlPartitionerOptions

TEXT_TAGS: Final[list[str]] = ["p", "a", "td", "span", "b", "font"]
LIST_ITEM_TAGS: Final[list[str]] = ["li", "dd"]
LIST_TAGS: Final[list[str]] = ["ul", "ol", "dl"]
HEADING_TAGS: Final[list[str]] = ["h1", "h2", "h3", "h4", "h5", "h6"]
TABLE_TAGS: Final[list[str]] = ["table", "tbody", "td", "tr"]
TEXTBREAK_TAGS: Final[list[str]] = ["br"]
EMPTY_TAGS: Final[list[str]] = ["br", "hr"]
HEADER_OR_FOOTER_TAGS: Final[list[str]] = ["header", "footer"]
SECTION_TAGS: Final[list[str]] = ["div", "pre"]

DEPTH_CLASSES = ListItem, Title


class HTMLDocument:
    """Class for handling HTML documents.

    Uses rules based parsing to identify sections of interest within the document.
    """

    def __init__(self, html_text: str, opts: HtmlPartitionerOptions):
        self._html_text = html_text
        self._opts = opts

    @classmethod
    def load(cls, opts: HtmlPartitionerOptions) -> HTMLDocument:
        """Construct instance from whatever source is specified in `opts`."""
        return cls(opts.html_text, opts)

    @lazyproperty
    def elements(self) -> list[Element]:
        """All "regular" elements (e.g. Title, NarrativeText, etc.) parsed from document.

        Elements appear in document order.
        """

        def iter_elements() -> Iterator[Element]:
            """Generate each element in document."""
            for e in self._iter_elements(self._main):
                e.metadata.last_modified = self._opts.last_modified
                e.metadata.detection_origin = self._opts.detection_origin
                yield e

        return list(iter_elements())

    def _classify_text(self, text: str, tag: str) -> type[Text] | None:
        """Produce a document-element of the appropriate sub-type for `text`."""
        if is_bulleted_text(text):
            if not clean_bullets(text):
                return None
            return ListItem

        if is_us_city_state_zip(text):
            return Address

        if is_email_address(text):
            return EmailAddress

        if len(text) < 2:
            return None

        if tag not in HEADING_TAGS and is_possible_narrative_text(text):
            return NarrativeText

        if tag in HEADING_TAGS or is_possible_title(text):
            return Title

        return Text

    @lazyproperty
    def _document_tree(self) -> etree._Element:
        """The root HTML element."""
        content = self._html_text
        parser = etree.HTMLParser(remove_comments=True)
        # NOTE(robinson) - without the carriage return at the beginning, you get
        # output that looks like the following when you run partition_pdf
        #   'h   3       a   l   i   g   n   =   "   c   e   n   t   e   r   "   >'
        # The correct output is returned once you add the initial return.
        if content and not content.startswith("\n"):
            content = "\n" + content

        try:
            document_tree = etree.fromstring(content, parser)
            if document_tree is None:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError("document_tree is None")

        # NOTE(robinson) - The following ValueError occurs with unicode strings. In that case, we
        # fall back to encoding the string and passing in bytes.
        #     ValueError: Unicode strings with encoding declaration are not supported.
        #     Please use bytes input or XML fragments without declaration.
        except ValueError:
            document_tree = etree.fromstring(content.encode(), parser)

        # -- remove all <script> and <style> tags so we don't have to worry about accidentally
        # -- parsing elements out of those.
        etree.strip_elements(document_tree, ["script", "style"], with_tail=False)

        # -- remove <header> and <footer> tags if the caller doesn't want their contents --
        if self._opts.skip_headers_and_footers:
            etree.strip_elements(document_tree, ["header", "footer"], with_tail=False)

        return document_tree

    def _iter_elements(self, subtree: etree._Element) -> Iterator[Element]:
        """Parse HTML-subtree into `Element` objects in document order."""
        descendant_tag_elems: tuple[etree._Element, ...] = ()
        for tag_elem in subtree.iter():
            # -- Prevent repeating something that's been flagged as text as we descend branch --
            if tag_elem in descendant_tag_elems:
                continue

            if self._is_text_tag(tag_elem):
                yield from self._process_text_tag(tag_elem)
                descendant_tag_elems = tuple(tag_elem.iterdescendants())

            elif self._is_container_with_text(tag_elem):
                tag_elem_tail = tag_elem.tail.strip() if tag_elem.tail else None
                if tag_elem_tail:
                    yield from self._process_text_tag(tag_elem, False)
                    descendant_tag_elems = tuple(tag_elem.iterdescendants())

                    # NOTE(christine): generate a separate element using a tag tail
                    assert tag_elem.tail is not None
                    ElementCls = self._classify_text(tag_elem.tail, tag_elem.tag)
                    if ElementCls:
                        yield ElementCls(
                            text=clean_bullets(tag_elem.tail),
                            metadata=ElementMetadata(
                                category_depth=0 if ElementCls in DEPTH_CLASSES else None
                            ),
                        )
                else:
                    link_texts, link_urls, link_start_indexes = _get_links_from_tag(tag_elem)
                    emphasized_texts, emphasized_tags = _get_emphasized_texts_from_tag(tag_elem)
                    assert tag_elem.text is not None
                    ElementCls = self._classify_text(tag_elem.text, tag_elem.tag)
                    if ElementCls:
                        yield ElementCls(
                            text=clean_bullets(tag_elem.text),
                            metadata=ElementMetadata(
                                category_depth=0 if ElementCls in DEPTH_CLASSES else None,
                                emphasized_text_contents=emphasized_texts,
                                emphasized_text_tags=emphasized_tags,
                                link_texts=link_texts,
                                link_urls=link_urls,
                                link_start_indexes=link_start_indexes,
                            ),
                        )

            elif self._is_bulleted_table(tag_elem):
                yield from self._parse_bulleted_text_from_table(tag_elem)
                descendant_tag_elems = tuple(tag_elem.iterdescendants())

            elif self._is_list_item_tag(tag_elem):
                element, next_tag_elem = self._process_list_item(tag_elem)
                if element is not None:
                    yield element
                    descendant_tag_elems = (
                        () if next_tag_elem is None else tuple(next_tag_elem.iterdescendants())
                    )

            elif tag_elem.tag in TABLE_TAGS:
                element = self._parse_Table_from_table_elem(tag_elem)
                if element is not None:
                    yield element
                if element or tag_elem.tag == "table":
                    descendant_tag_elems = tuple(tag_elem.iterdescendants())

    @lazyproperty
    def _main(self) -> etree._Element:
        """The first <main> tag under `root` if it exists, othewise `root`."""
        main_tag_elem = self._document_tree.find(".//main")
        return main_tag_elem if main_tag_elem is not None else self._document_tree

    # -- tag classifiers --------------------------------------------------

    def _has_adjacent_bulleted_spans(
        self, tag_elem: etree._Element, children: list[etree._Element]
    ) -> bool:
        """True when `tag_elem` is a <div> or <pre> containing two or more adjacent bulleted spans.

        A bulleted span is one beginning with a bullet. If there are two or more adjacent to each
        other they are treated as a single bulleted text element.
        """
        if tag_elem.tag in SECTION_TAGS:
            all_spans = all(child.tag == "span" for child in children)
            _is_bulleted = children[0].text is not None and is_bulleted_text(children[0].text)
            if all_spans and _is_bulleted:
                return True
        return False

    def _is_bulleted_table(self, table_elem: etree._Element) -> bool:
        """True when all text in `table_elem` is bulleted text.

        A table-row containing no text is not considered, but at least one bulleted-text item must
        be present. A table with no text in any row is not a bulleted table.
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

    def _is_container_with_text(self, tag_elem: etree._Element) -> bool:
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

    def _is_list_item_tag(self, tag_elem: etree._Element) -> bool:
        """True when `tag_elem` contains bulleted text."""
        return tag_elem.tag in LIST_ITEM_TAGS or (
            tag_elem.tag in SECTION_TAGS and is_bulleted_text(_construct_text(tag_elem))
        )

    def _is_text_tag(
        self, tag_elem: etree._Element, max_predecessor_len: int = HTML_MAX_PREDECESSOR_LEN
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

        if self._has_adjacent_bulleted_spans(tag_elem, children):
            return True

        return False

    # -- tag processors ---------------------------------------------------

    def _parse_bulleted_text_from_table(self, table: etree._Element) -> Iterator[Element]:
        """Generate zero or more document elements from `table` tag.

        Extracts bulletized narrative text from the table.

        NOTE: if a table has mixed bullets and non-bullets, only bullets are extracted; i.e.
        non-bullet narrative text in the table is dropped.
        """
        rows = table.findall(".//tr")
        for row in rows:
            text = _construct_text(row)
            if is_bulleted_text(text):
                yield ListItem(text=clean_bullets(text))

    def _parse_Table_from_table_elem(self, table_elem: etree._Element) -> Element | None:
        """Form `Table` element from `tbl_elem`."""
        if table_elem.tag != "table":
            return None

        # -- NOTE that this algorithm handles a nested-table by parsing all of its text into the
        # -- text for the _cell_ containing the table (and this is recursive, so a table nested
        # -- within a cell within the table within the cell too.)

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
                # -- a cell can contain other elements like spans etc. so we can't count on the
                # -- text being directly below the `<td>` element. `.itertext()` gets all of it
                # -- recursively. Filter out whitespace text nodes resulting from HTML formatting.
                stripped_text_nodes = (t.strip() for t in td.itertext())
                yield " ".join(t for t in stripped_text_nodes if t)

        table_data = [list(iter_cell_texts(tr)) for tr in trs]
        html_table = htmlify_matrix_of_cell_texts(table_data)
        table_text = " ".join(" ".join(t for t in row if t) for row in table_data).strip()

        if table_text == "":
            return None

        return Table(text=table_text, metadata=ElementMetadata(text_as_html=html_table))

    def _process_list_item(
        self, tag_elem: etree._Element, max_predecessor_len: int = HTML_MAX_PREDECESSOR_LEN
    ) -> tuple[Element | None, etree._Element | None]:
        """Produces an `ListItem` document element from `tag_elem`.

        When `tag_elem` contains bulleted text, the relevant bulleted text is extracted. Also
        returns the next html element so we can skip processing if bullets are found in a div
        element.
        """
        if tag_elem.tag in LIST_TAGS + LIST_ITEM_TAGS:
            text = _construct_text(tag_elem)
            link_texts, link_urls, link_start_indexes = _get_links_from_tag(tag_elem)
            emphasized_texts, emphasized_tags = _get_emphasized_texts_from_tag(tag_elem)
            depth = len(
                [el for el in tag_elem.iterancestors() if el.tag in LIST_TAGS + LIST_ITEM_TAGS],
            )
            return (
                ListItem(
                    text=text,
                    metadata=ElementMetadata(
                        category_depth=depth,
                        emphasized_text_contents=emphasized_texts,
                        emphasized_text_tags=emphasized_tags,
                        link_texts=link_texts,
                        link_urls=link_urls,
                        link_start_indexes=link_start_indexes,
                    ),
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
                return ListItem(text=next_text), next_element

        return None, None

    def _parse_tag(
        self, tag_elem: etree._Element, include_tail_text: bool = True
    ) -> Element | None:
        """Parses `tag_elem` to a Text element if it contains qualifying text.

        Ancestor tags are kept so they can be used for filtering or classification without
        processing the document tree again. In the future we might want to keep descendants too,
        but we don't have a use for them at the moment.
        """
        text = _construct_text(tag_elem, include_tail_text)
        if not text:
            return None

        ElementCls = self._classify_text(text, tag_elem.tag)
        if not ElementCls:
            return None

        depth = (
            # -- zero index the depth --
            int(tag_elem.tag[1]) - 1
            if tag_elem.tag in HEADING_TAGS
            else (
                len([el for el in tag_elem.iterancestors() if el.tag in LIST_TAGS + LIST_ITEM_TAGS])
                if tag_elem.tag in LIST_TAGS + LIST_ITEM_TAGS
                else 0
            )
        )
        emphasized_texts, emphasized_tags = _get_emphasized_texts_from_tag(tag_elem)
        link_texts, link_urls, link_start_indexes = _get_links_from_tag(tag_elem)

        return ElementCls(
            text=clean_bullets(text),
            metadata=ElementMetadata(
                category_depth=depth if ElementCls in DEPTH_CLASSES else None,
                emphasized_text_contents=emphasized_texts,
                emphasized_text_tags=emphasized_tags,
                link_texts=link_texts,
                link_urls=link_urls,
                link_start_indexes=link_start_indexes,
            ),
        )

    def _process_text_tag(
        self, tag_elem: etree._Element, include_tail_text: bool = True
    ) -> Iterator[Element]:
        """Generate zero or more document elements from `tag_elem`."""
        if _has_break_tags(tag_elem):
            flattened_elems = _unfurl_break_tags(tag_elem)
            for _tag_elem in flattened_elems:
                element = self._parse_tag(_tag_elem, include_tail_text)
                if element is not None:
                    yield element

        else:
            element = self._parse_tag(tag_elem, include_tail_text)
            if element is not None:
                yield element


# -- tag processors ------------------------------------------------------------------------------


def _construct_text(tag_elem: etree._Element, include_tail_text: bool = True) -> str:
    """Extract "clean"" text from `tag_elem`."""
    text = "".join(str(t) for t in tag_elem.itertext() if t)

    if include_tail_text and tag_elem.tail:
        text = text + tag_elem.tail

    text = replace_unicode_quotes(text)
    return text.strip()


def _get_emphasized_texts_from_tag(
    tag_elem: etree._Element,
) -> tuple[list[str] | None, list[str] | None]:
    """Emphasized text within and below `tag_element`.

    Emphasis is indicated by `<strong>`, `<em>`, `<span>`, `<b>`, `<i>` tags.

    Return value is a pair of lists like `(["foo", "bar"], ["b", "i"])` ready for assignment to
    `.metadata.emphasized_text_contents` and `.metadata.emphasized_text_tagS` respectively. These
    values are both `None` when no emphasized_text is present in `tag_elem`.
    """
    tags_to_track = ["strong", "em", "span", "b", "i"]

    def iter_text_tag_pairs() -> Iterator[tuple[str, str]]:
        """Generate (text, tag) pair for each emphasized text in or in child of `tag_elem`."""
        if tag_elem.tag in tags_to_track:
            text = _construct_text(tag_elem, False)
            if text:
                yield text, tag_elem.tag

        for descendant_tag_elem in tag_elem.iterdescendants(*tags_to_track):
            text = _construct_text(descendant_tag_elem, False)
            if text:
                yield text, descendant_tag_elem.tag

    text_tag_pairs = list(iter_text_tag_pairs())
    emphasized_texts = [text for text, _ in text_tag_pairs]
    emphasized_tags = [tag for _, tag in text_tag_pairs]

    return emphasized_texts or None, emphasized_tags or None


def _get_links_from_tag(
    tag_elem: etree._Element,
) -> tuple[list[str] | None, list[str] | None, list[int] | None]:
    """Hyperlinks within and below `tag_elem`."""

    def iter_link_triples() -> Iterator[tuple[str, str, int]]:
        """Generate (text, url, offset) pair for each link in `tag_elem` or descendant."""
        href = tag_elem.get("href")
        if href:
            tag_elem_text = _construct_text(tag_elem, False)
            yield tag_elem_text, href, -1
        else:
            start_index = len(tag_elem.text.lstrip()) if tag_elem.text else 0
            for tag in tag_elem.iterdescendants():
                href = tag.get("href")
                if href:
                    yield tag.text or "", href, start_index
                # -- recompute start-index for next link --
                if tag.text and not (tag.text.isspace()):
                    start_index = start_index + len(tag.text)
                if tag.tail and not (tag.tail.isspace()):
                    start_index = start_index + len(tag.tail)

    link_triples = list(iter_link_triples())
    link_texts = [text for text, _, _ in link_triples]
    link_urls = [url for _, url, _ in link_triples]
    link_start_indexes = [offset for _, _, offset in link_triples]

    return link_texts or None, link_urls or None, link_start_indexes or None


def _has_break_tags(tag_elem: etree._Element) -> bool:
    """True when `tab_elem` contains a `<br>` descendant."""
    return any(descendant.tag in TEXTBREAK_TAGS for descendant in tag_elem.iterdescendants())


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
