# pyright: reportPrivateUsage=false

"""Provides the HTML parser used by `partition_html()`."""

from __future__ import annotations

from collections import defaultdict, deque
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Mapping, NamedTuple, cast

from lxml import etree
from typing_extensions import TypeAlias

from unstructured.cleaners.core import clean_bullets
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
    is_us_city_state_zip,
)
from unstructured.utils import htmlify_matrix_of_cell_texts

# ------------------------------------------------------------------------------------------------
# DOMAIN MODEL
# ------------------------------------------------------------------------------------------------


Annotation: TypeAlias = Mapping[str, Any]
"""A mapping with zero or more keywords, each represening a noted characteristic.

An annotation can be associated with a text segment or element. In general the keys and value-types
differ between the individual (text-segment) and consolidated (Element) forms.
"""


class TextSegment(NamedTuple):
    """An annotated string from a Phrasing element.

    Annotations are for emphasis and for links. The text includes any leading, trailing, and
    inter-word whitespace, just as it occurred in the HTML. The text-segments for a paragraph are
    consolidated once the paragraph is fully parsed and whitespace it normalized at that time. It
    cannot be normalized prior to that without distoring or losing inter-word spacing.

    However, text within annotations, like the text of a link, is normalized since its full extents
    are known.
    """

    text: str
    annotation: Annotation


# ------------------------------------------------------------------------------------------------
# CUSTOM ELEMENT-CLASSES
# ------------------------------------------------------------------------------------------------


# -- FLOW (BLOCK-ITEM) ELEMENTS ------------------------------------------------------------------


class Flow(etree.ElementBase):
    """Base and default class for elements that act like a div.

    These can contain other flow elements or phrasing elements.
    """

    # -- by default, choose the element class based on the form of the text --
    _ElementCls = None

    @property
    def is_phrasing(self) -> bool:
        return False

    def iter_elements(self) -> Iterator[Element]:
        """Generate paragraph string for each block item within."""
        # -- place child elements in a queue --
        q: deque[Flow | Phrasing] = deque(self)

        yield from self._element_from_text_or_tail(self.text or "", q, self._ElementCls)

        while q:
            assert not q[0].is_phrasing
            block_item = cast(Flow, q.popleft())
            yield from block_item.iter_elements()
            yield from self._element_from_text_or_tail(block_item.tail or "", q)

    def _category_depth(self, ElementCls: type[Element]) -> int | None:
        """Not clear on concept. Something to do with hierarchy ..."""
        if ElementCls is ListItem:
            return (
                len([e for e in self.iterancestors() if e.tag in ("dl", "ol", "ul")])
                if self.tag in ("li", "dd")
                else 0
            )

        if ElementCls is Title:
            return int(self.tag[1]) - 1 if self.tag in ("h1", "h2", "h3", "h4", "h5", "h6") else 0

        return None

    @staticmethod
    def _consolidate_annotations(text_segments: Iterable[TextSegment]) -> Annotation:
        """Combine individual text-segment annotation into an element-level annotation.

        Sequence is significant.
        """
        combined_annotations = cast(defaultdict[str, list[str]], defaultdict(list))
        for ts in text_segments:
            for k, v in ts.annotation.items():
                combined_annotations[k].append(v)

        return MappingProxyType(dict(combined_annotations))

    def _element_from_text_or_tail(
        self, text: str, q: deque[Flow | Phrasing], ElementCls: type[Element] | None = None
    ) -> Iterator[Element]:
        """Generate zero-or-one paragraph formed from text and leading phrasing elements.

        Note this mutates `q` by popping phrasing elements off as they are processed.
        """
        text_segments = tuple(self._iter_text_segments(text, q))
        normalized_text = " ".join("".join(ts.text for ts in text_segments).split())

        if not normalized_text:
            return

        # -- if we don't have a more specific element-class, choose one based on the text --
        if ElementCls is None:
            ElementCls = derive_element_type_from_text(normalized_text)
            # -- normalized text that contains only a bullet character is skipped --
            if ElementCls is None:
                return
            # -- derived ListItem means text starts with a bullet character that needs removing --
            if ElementCls is ListItem:
                normalized_text = clean_bullets(normalized_text)
                if not normalized_text:
                    return

        category_depth = self._category_depth(ElementCls)

        yield ElementCls(
            normalized_text,
            metadata=ElementMetadata(
                **self._consolidate_annotations(text_segments), category_depth=category_depth
            ),
        )

    def _iter_text_segments(self, text: str, q: deque[Flow | Phrasing]) -> Iterator[TextSegment]:
        """Generate zero-or-more `TextSegment`s from text and leading phrasing elements.

        This is used to process the text or tail of a flow element. For example, this <div>:

            <div>
               For a <b>moment, <i>nothing</i> happened.</b>
               <p>Then, after a second or so, nothing continued to happen.</p>
               The dolphins had always believed that <em>they</em> were far more intelligent.
            </div>

        Should generate three distinct elements, one for each contained line. This method is
        invoked to process the first beginning "For a" and the third line beginning "The dolphins".

        Note this method mutates `q` by popping phrasing elements off as they are processed.
        """
        yield TextSegment(text, {})
        while q and q[0].is_phrasing:
            e = cast(Phrasing, q.popleft())
            yield from e.iter_text_segments()


class BlockItem(Flow):
    """Custom element-class for `<p>` element, `<h1>`, and others like it.

    These can appear in a flow container like a div but can only contain phrasing content.
    """

    # -- Turns out there are no implementation differences so far between Flow and BlockItem, but
    # -- maintaining the distinction for now. We may use it to add hierarchy information or
    # -- customize how we deal with invalid HTML that places flow items inside one of these.


class Heading(Flow):
    """An `<h1>..<h6>` element.

    These are distinguished because they generate a `Title` element.
    """

    _ElementCls = Title


class ListBlock(Flow):
    """Either a `<ul>` or `<ol>` element, maybe a `<dl>` element at some point.

    The primary reason for distinguishing these is because they increment the hierarchy depth for
    lists that are nested inside them.

    Can only contain `<li>` elements (ignoring `<script>` and `<template>`). A list nested inside
    must actually be a child of one of these `<li>` elements.
    """

    # TODO: might want alternate `.iter_elements()` since these can only contain `<li>` elements and
    # not text nodes (I believe).


class ListItemBlock(Flow):
    """A `<li>` element.

    These are distinguished because they generate a `ListItem` element.
    """

    _ElementCls = ListItem


class TableBlock(Flow):
    """Custom element-class for `<table>` element."""

    def iter_elements(self) -> Iterator[Table]:
        """Generate paragraph string for each block item within."""

        # -- NOTE this algorithm handles a nested-table by parsing all of its text into the text
        # -- for the _cell_ containing the table (and this is recursive, so a table nested within
        # -- a cell within a table within a cell too.)

        trs = cast(list[etree._Element], self.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr"))

        if not trs:
            return

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
            return

        yield Table(table_text, metadata=ElementMetadata(text_as_html=html_table))


class RemovedBlock(Flow):
    """Elements that are to be ignored.

    An element may be ignored because it commonly contains boilerplate that would dilute the meaning
    extracted rather than contribute to it.

    All contents of a removed block item are ignored but its tail is emitted by its container.
    """

    def iter_elements(self) -> Iterator[Element]:
        """Don't generate any document-elements."""
        return
        yield


# -- PHRASING ELEMENTS ---------------------------------------------------------------------------


class Phrasing(etree.ElementBase):
    """Base-class for phrasing (inline/run) elements like bold and italic."""

    @property
    def is_phrasing(self) -> bool:
        return True

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment]:
        """Generate text segments for text, children, and tail of this element."""
        inside_emphasis = self._inside_emphasis(enclosing_emphasis)

        yield from self._iter_text_segment(inside_emphasis)

        # -- Recurse into any nested tags. All child tags are assumed to also be phrasing tags. --
        for child in self:
            yield from child.iter_text_segments(inside_emphasis)

        # -- It is the phrasing element's job to emit its tail when it has one (there is no one
        # -- else who can do it). Note that the tail gets the _enclosing-emphasis_, not the
        # -- _inside-emphasis_ since the tail occurs after this phrasing element's closing tag.
        yield from self._iter_tail_segment(enclosing_emphasis)

    def _annotation(self, text: str, emphasis: str) -> Annotation:
        """Emphasis annotations that apply to text inside this element.

        No annotations are added when the text contains only whitespace. Otherwise, emphasis
        annotations are returned for the text contents, normalized as it will appear in the
        document-element.

        Emphasis annotations apply to the contents of all elements enclosed by the emphasis element.
        Sub-classes like the one for anchor elements that add non-emphasis annotations will need to
        override this method.
        """
        # -- emphasis annotation is only added when there is both emphasis and non-whitespace text
        # -- to apply it to
        return MappingProxyType(
            {"emphasized_text_contents": normalized_text, "emphasized_text_tags": emphasis}
            if (normalized_text := self._normalize_text(text)) and emphasis
            else {}
        )

    def _inside_emphasis(self, enclosing_emphasis: str) -> str:
        """By default, the inside emphasis is the same as the outside emphasis.

        This method is overridden by sub-classes that annotate particular emphasis types but many
        phrasing elements do not contribute to annotations.
        """
        return enclosing_emphasis

    def _iter_tail_segment(self, emphasis: str) -> Iterator[TextSegment]:
        """Generate zero-or-one text-segment for tail of this element.

        No text-segment is generated when this element has no tail node. However a segment _is_
        generated for a whitespace-only tail node.
        """
        if tail := self.tail:
            yield TextSegment(tail, self._annotation(tail, emphasis))

    def _iter_text_segment(self, emphasis: str) -> Iterator[TextSegment]:
        """Generate zero-or-one text-segment for text of this element.

        No text-segment is generated when this element has no text node. However a segment _is_
        generated for a whitespace-only text node.
        """
        if text := self.text:
            yield TextSegment(text, self._annotation(text, emphasis))

    @staticmethod
    def _normalize_text(text: str) -> str:
        """`text` with normalized whitespace.

        - leading and trailing whitespace are removed
        - all whitespace segments within text (spacing between words) are reduced to a single space
          each.

        Produces the empty string when `text` contains only whitespace.
        """
        return " ".join(text.strip().split())


class Anchor(Phrasing):
    """Custom element-class for `<a>` element.

    Provides link annotations.
    """

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment]:
        """Generate text segments for text and tail of this element, when they exist.

        The behavior for an anchor element is slightly different because link annotations are only
        added to the text, not the tail. Also an anchor can have no children.
        """
        # -- No text pair is emitted when there is absolutely no text (quite rare I expect) --
        if text := self.text:
            yield TextSegment(text, self._link_annotations(text, enclosing_emphasis))

        # -- A tail is emitted when present whether anchor itself was or not --
        yield from self._iter_tail_segment(enclosing_emphasis)

    def _link_annotations(self, text: str, emphasis: str) -> Annotation:
        """Link and emphasis annotations that apply to the text of this anchor.

        An anchor element does not add any emphasis but uses any introduced by enclosing elements.
        """
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return {}

        def iter_annotation_pairs() -> Iterator[tuple[str, Any]]:
            # -- emphasis annotation is only added when there is enclosing emphasis --
            if emphasis:
                yield "emphasized_text_contents", normalized_text
                yield "emphasized_text_tags", emphasis

            if href := self.get("href"):
                yield "link_texts", normalized_text
                yield "link_urls", href

        return MappingProxyType(dict(iter_annotation_pairs()))


class Bold(Phrasing):
    """Provides annotations for bold/strong text."""

    def _inside_emphasis(self, enclosing_emphasis: str) -> str:
        """Emphasis tags that apply to text inside this element.

        Formed by adding "b" (for "bold") to the enclosing emphasis, unless it's already there.
        The returned emphasis tuple is sorted to make its form canonical, which eases testing. For
        Example `("b", "i")` and `("i", "b")` are semantically the same but don't directly compare
        equal in a test. Sorting it basically gives it some set-like properties.
        """
        chars = set(enclosing_emphasis + "b")
        return "".join(sorted(chars))


class Italic(Phrasing):
    """Provides annotations for italic/emphasized text."""

    def _inside_emphasis(self, enclosing_emphasis: str) -> str:
        """Emphasis tags that apply to text inside this element.

        Formed by adding "i" (for "italic") to the enclosing emphasis, unless it's already there.
        """
        chars = set(enclosing_emphasis + "i")
        return "".join(sorted(chars))


class LineBreak(Phrasing):
    """A `<br/>` line-break element.

    It's only special behavior is to add whitespace such that phrasing tight on both sides is not
    joined, like `abc<br/>def` should become "abc def", not "abcdef".
    """

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment]:
        """Generate text segments for text, children, and tail of this element."""
        yield TextSegment("\n", {})
        yield from self._iter_tail_segment(enclosing_emphasis)


class RemovedPhrasing(Phrasing):
    """Phrasing where we want to skip the content.

    - `.is_phrasing` is True so it doesn't break the paragraph like a block.
    - `element.text` is discarded
    - `element.tail` is preserved
    """

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment]:
        """Generate text segment for tail only of this element."""
        yield from self._iter_tail_segment(enclosing_emphasis)


# -- DEFAULT ELEMENT -----------------------------------------------------------------------------


class DefaultElement(Flow, Phrasing):
    """Custom element-class used for any element without an assigned custom element class.

    An unrecognized element is given both Flow (block) and Phrasing (inline) behaviors. It behaves
    like a Flow element When nested in a Flow element like a Phrasing element when nested in a
    Phrasing element.

    The contents of the element is skipped in either case, but its tail is not when it behaves as a
    Phrasing element. The tail is processed by its parent when that is a Flow element.
    """

    @property
    def is_phrasing(self) -> bool:
        """If asked (by a parent Flow element), identify as a Flow element."""
        return False

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment]:
        """Generate text segment for tail of this element only.

        This method is only called on Phrasing elements and their children. In that case, act like a
        Phrasing element but don't generate a text segment for this element or any children. Do
        however generate a tail text-segment.
        """
        # -- It is the phrasing element's job to emit its tail when it has one (there is no one
        # -- else who can do it). Note that the tail gets the _enclosing-emphasis_, not the
        # -- _inside-emphasis_ since the tail occurs after this phrasing element's closing tag.
        yield from self._iter_tail_segment(enclosing_emphasis)

    def iter_elements(self) -> Iterator[Element]:
        """Don't generate any document-elements when behaving like a Flow element."""
        return
        yield
        return Text


# ------------------------------------------------------------------------------------------------
# TEXT-ELEMENT CLASSIFIER
# ------------------------------------------------------------------------------------------------


def derive_element_type_from_text(text: str) -> type[Text] | None:
    """Produce a document-element of the appropriate sub-type for `text`."""
    if is_bulleted_text(text):
        return ListItem

    if is_us_city_state_zip(text):
        return Address

    if is_email_address(text):
        return EmailAddress

    if len(text) < 2:
        return None

    if is_possible_narrative_text(text):
        return NarrativeText

    # NOTE (scanny): I think classifying short paragraphs as titles produces noise much more
    # frequently than it does value. A `Title` element is very consequential in its effect on
    # chunking and document hierarchy. Classifying any small paragraph as a heading is frequently
    # wrong and throws off these important downstream processes much more than missing the
    # occasional heading does. If we want to infer headings, I think we have to be much more
    # intelligent about it and consider what elements came before and after to see if the text
    # _behaves_ like a heading, maybe whether it is bold and how many text elements follow it before
    # the next title and how long since the prior title, whether `h1..h6` are used elsewhere in the
    # document, etc.
    # if is_possible_title(text):
    #     return Title

    return Text


# ------------------------------------------------------------------------------------------------
# HTML PARSER
# ------------------------------------------------------------------------------------------------


html_parser = etree.HTMLParser(remove_comments=True)
# -- elements that don't have a registered class get DefaultElement --
fallback = etree.ElementDefaultClassLookup(element=DefaultElement)
# -- elements that do have a registered class are assigned that class via lookup --
element_class_lookup = etree.ElementNamespaceClassLookup(fallback)
html_parser.set_element_class_lookup(element_class_lookup)

# -- register classes --
element_class_lookup.get_namespace(None).update(
    {
        # -- flow/containers --
        "address": Flow,
        "article": Flow,
        "aside": Flow,
        "blockquote": Flow,
        "body": Flow,
        "center": Flow,
        "div": Flow,
        "footer": Flow,
        "header": Flow,
        "hgroup": Flow,
        "main": Flow,
        "pre": Flow,
        "section": Flow,
        # -- block items --
        "h1": Heading,
        "h2": Heading,
        "h3": Heading,
        "h4": Heading,
        "h5": Heading,
        "h6": Heading,
        "p": BlockItem,
        # -- list blocks --
        "ol": ListBlock,
        "ul": ListBlock,
        "li": ListItemBlock,
        # -- table --
        "table": TableBlock,
        # -- annotated phrasing --
        "a": Anchor,
        "b": Bold,
        "em": Italic,
        "i": Italic,
        "strong": Bold,
        # -- transparent phrasing --
        "abbr": Phrasing,  # -- abbreviation, like "LLM (Large Language Model)"
        "bdi": Phrasing,  # -- Bidirectional Isolate - important for RTL languages
        "bdo": Phrasing,  # -- Bidirectional Override - maybe reverse
        "big": Phrasing,  # -- deprecated --
        "br": LineBreak,  # -- line break --
        "cite": Phrasing,  # -- title of book or article etc. --
        "code": Phrasing,  # -- monospaced terminal font --
        "data": Phrasing,  # -- similar to `time`, provides machine readable value as attribute --
        "dfn": Phrasing,  # -- definition, like new term in italic when first introduced --
        "kbd": Phrasing,  # -- font that looks like keyboard keys --
        "mark": Phrasing,  # -- like yellow highlighter --
        "meter": Phrasing,  # -- bar thermometer progress-meter thing --
        "q": Phrasing,  # -- inline quotation, usually quoted and maybe italic --
        "s": Phrasing,  # -- strikethrough --
        "samp": Phrasing,  # -- sample terminal output; like markdown back-ticks for inline code --
        "small": Phrasing,  # -- fine-print; maybe likely boilerplate --
        "span": Phrasing,
        "strike": Phrasing,  # -- deprecated - obsolete version of `del` or `s` --
        "sub": Phrasing,  # -- subscript --
        "sup": Phrasing,  # -- superscript --
        "time": Phrasing,  # -- wrap human-readable time to provide machine-readable time as attr --
        "tt": Phrasing,  # -- deprecated - "teletype", obsolete version of `code` or `samp` --
        "u": Phrasing,  # -- red squiggly underline for e.g. spelling mistake; was underscore --
        "var": Phrasing,  # -- variable like "x" in a mathematical expression --
        "wbr": Phrasing,  # -- word-break opportunity; empty --
        # -- removed phrasing --
        "button": RemovedPhrasing,
        # -- removed block --
        "details": RemovedBlock,  # -- likely boilerplate --
        "dl": RemovedBlock,
        "dd": RemovedBlock,
        "dt": RemovedBlock,
        "figure": RemovedBlock,
        "hr": RemovedBlock,
        "nav": RemovedBlock,
        "template": RemovedBlock,
        # -- removed form-related --
        "form": RemovedBlock,
        "input": RemovedBlock,
        "label": RemovedBlock,
        "summary": RemovedBlock,  # -- child of `details`
    }
)
