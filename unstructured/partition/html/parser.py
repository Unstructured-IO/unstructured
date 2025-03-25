# pyright: reportPrivateUsage=false

"""Provides the HTML parser used by `partition_html()`.

The names "flow" and "phrasing" derive from the language of the HTML Standard.

PRINCIPLES

- _Elements are paragraphs._ Each paragraph in the HTML document should become a distinct element.
  In particular, a paragraph should not be split into two elements and an element should not
  contain more than one paragraph.

- _An empty paragraph is not an Element._ A paragraph which contains no text or contains only
  whitespace does not give rise to an Element (is skipped).

- _The browser rendering is the document._ The HTML "source-code" is not the document. The document
  is the way that HTML is rendered by a browser (Chrome for a first authority). This foundational
  principle gives rise to a few that are more specific.

- _Whitespace is normalized._ Whitespace used for formatting the HTML source is _normalized_ to a
  single space between text segments. More specifically:
  - Any leading or trailing space on a paragraph is removed.
  - All other runs of whitespace in the paragraph are reduced to a single space (" ").
  - Whitespace is never added where none existed in the HTML source.
  - Whitespace within a `<pre>` element is the exception and is not normalized. Its
    whitespace is preserved excepting a leading and/or trailing newline ("\n").

- _Block-items are paragraphs._ Visible content in HTML can be divided into _block-items_ and
  _phrasing content_ (aka. _inline content_).
  - As an example, a `<p>` element is a block item and a `<b>` element is phrasing.
  - A block item starts a new paragraph and so represents an Element boundary.
  - A phrasing item affects the appearance of a run of text within a paragraph, like making it
    bold or making it into a link.
  - Some elements can take either role, depending upon their ancestors and descendants.
  - The final authority for whether a particular element is displayed as a block or as inline
    "formatting" is the CSS. We do not attempt to interpret the CSS and assume the default role
    for each element.

Other background

- The parser's design is _recursive_, consistent with the recursive (tree) structure of HTML. The
  nodes of the tree are _HTML elements_. Unfortunately this naming sometimes conflicts with
  Unstructured _document-elements_. In the parser code the term "document-element" is used when
  there may be ambiguity.

- The parser is primarily composed of `lxml` Custom Element Classes. The gist is you write a class
  like `Anchor` and then tell the `lxml` parser that all `<a>` elements should be instantiated
  using the `Anchor` class. We also provide a default class for any elements that we haven't
  called out explicitly.

- _Anatomy of an HTML element._ Some basic terms are important to know to understand the domain
  language of the parser code. Consider this example:
  ```html
  <div>
    <p>Text <b>bold child</b> tail of child</p>
    tail of p
  </div>
  ```
  - An element can have _text_.
    - All visible content within an HTML document is the text (or tail) of some element.
    - The text of the `<p>` element (`p.text`) is "Text ".
    - Note the formatting whitespace is included.
  - An element can have _child elements_.
    - The `<p>` element (`p`) is a child of `div`.
    - `b` is a child of `p`.
  - An element can have a _tail_.
    - Whatever text follows an element, before the next element starts, is the tail of
      that element.
    - `b.tail` is `" tail of child"`. Note the included whitespace.
    - `p.tail` is `"\n    tail of p\n"`.
    - Tail text is _accessed_ via the element that precedes it but that element does not
      _influence_ its tail text. For example, "tail of child" does not appear in a bold
      typeface even though it is the tail of `b`.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Mapping, NamedTuple, Sequence, cast

from lxml import etree
from typing_extensions import TypeAlias

from unstructured.cleaners.core import clean_bullets
from unstructured.common.html_table import htmlify_matrix_of_cell_texts
from unstructured.documents.elements import (
    Address,
    Element,
    ElementMetadata,
    EmailAddress,
    Image,
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
from unstructured.utils import lazyproperty

# ------------------------------------------------------------------------------------------------
# DOMAIN MODEL
# ------------------------------------------------------------------------------------------------


Annotation: TypeAlias = Mapping[str, Any]
"""A mapping with zero or more keywords, each represening a noted characteristic.

An annotation can be associated with a text segment or element. In general the keys and value-types
differ between the individual (text-segment) and consolidated (Element) forms.
"""


def _consolidate_annotations(annotations: Iterable[Annotation]) -> Annotation:
    """Combine individual text-segment annotations into an element-level annotation.

    Sequence is significant.
    """
    combined_annotations = cast(defaultdict[str, list[str]], defaultdict(list))
    for a in annotations:
        for k, v in a.items():
            if isinstance(v, list):
                combined_annotations[k].extend(cast(list[Any], v))
            else:
                combined_annotations[k].append(v)

    return MappingProxyType(dict(combined_annotations))


def _normalize_text(text: str) -> str:
    """`text` with normalized whitespace.

    - leading and trailing whitespace are removed
    - all whitespace segments within text (spacing between words) are reduced to a single space
      each.

    Produces the empty string when `text` contains only whitespace.
    """
    return " ".join(text.strip().split())


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


Phrase: TypeAlias = Sequence[TextSegment]
"""Contiguous text-segments formed from text and contiguous phrasing.

These occur within a block element as the element text and contiguous phrasing or the tail and
contiguous phrasing. For example, there are two phrases in this div, one before and one after the
<p> child element:

    <div>
      Seagulls <b>gonna <i>come</i></b> and
      <p>Poke me in the coconut</p>
      And they <b>did</b>, they <i>did</i>
    </div>

The first is `div.text` and the phrasing (text and tail of phrasing elements) that follow it. A
phrase terminates at a block element (`<p>` in this case) or at the end of the enclosing block (the
`</div>` in this example).
"""


# ------------------------------------------------------------------------------------------------
# PHRASING ACCUMULATORS
# ------------------------------------------------------------------------------------------------


class _PhraseAccumulator:
    """Accumulates sequential `TextSegment`s making them available as iterable on flush().

    - The accumulator starts empty.
    - `.flush()` is a Phrase iterator and generates zero or one Phrase.
    - `.flush()` generates zero items when no text-segments have been accumulated
    - `flush()` resets the accumulator to its initial empty state.

    So far, phrases are used only by the Anchor class.
    """

    def __init__(self):
        self._text_segments: list[TextSegment] = []

    def add(self, text_segment: TextSegment) -> None:
        """Add `text_segment` to this collection."""
        self._text_segments.append(text_segment)

    def flush(self) -> Iterator[Phrase]:
        """Generate each of the stored `TextSegment` objects and clears the accumulator."""
        # -- harvest accumulated text-segments and empty the accumulator --
        text_segments = self._text_segments[:]
        self._text_segments.clear()

        if not text_segments:
            return

        yield tuple(text_segments)


class _ElementAccumulator:
    """Accumulates sequential `TextSegment`s and forms them into an element on flush().

    The text segments come from element text or tails and any contiguous phrasing elements that
    follow that text or tail.

    - The accumulator starts empty.
    - `.flush()` is an element iterator and generates zero or one Element.
    - `.flush()` generates zero elements when no text-segments have been accumulated or the ones
      that have been accumulated contain only whitespace.
    - `flush()` resets the accumulator to its initial empty state.
    """

    def __init__(self, element: etree.ElementBase):
        self._element = element
        self._text_segments: list[TextSegment] = []

    def add(self, text_segment: TextSegment) -> None:
        """Add `text_segment` to this Element-under-construction."""
        self._text_segments.append(text_segment)

    def flush(self, ElementCls: type[Element] | None) -> Iterator[Element]:
        """Generate zero-or-one document-`Element` object and clear the accumulator."""
        # -- normalized-text must be computed before resetting the accumulator --
        normalized_text = self._normalized_text

        # -- harvest accumulated text-segments and empty the accumulator --
        text_segments = self._text_segments[:]
        self._text_segments.clear()

        if not text_segments or not normalized_text:
            return

        # -- if we don't have a more specific element-class, choose one based on the text --
        if ElementCls is None:
            ElementCls = derive_element_type_from_text(normalized_text)
            # -- normalized text that contains only a single character is skipped unless it
            # -- identifies as a list-item
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
                **_consolidate_annotations(ts.annotation for ts in text_segments),
                category_depth=category_depth,
            ),
        )

    def _category_depth(self, ElementCls: type[Element]) -> int | None:
        """Not clear on concept. Something to do with hierarchy ..."""
        if ElementCls is ListItem:
            return (
                len([e for e in self._element.iterancestors() if e.tag in ("dl", "ol", "ul")])
                if self._element.tag in ("li", "dd")
                else 0
            )

        if ElementCls is Title:
            return (
                int(self._element.tag[1]) - 1
                if self._element.tag in ("h1", "h2", "h3", "h4", "h5", "h6")
                else 0
            )

        return None

    @property
    def _normalized_text(self) -> str:
        """Consolidate text-segment text values into a single whitespace-normalized string.

        This normalization is suitable for text inside a block element including any segments from
        phrasing elements immediately following that text. The spec is:

        - All text segments are concatenated (without adding or removing whitespace)
        - Leading and trailing whitespace are removed.
        - Each run of whitespace in the string is reduced to a single space.

        For example:
          "  \n   foo  bar\nbaz bada \t bing\n  "
        becomes:
          "foo bar baz bada bing"
        """
        return " ".join("".join(ts.text for ts in self._text_segments).split())


class _PreElementAccumulator(_ElementAccumulator):
    """Accumulator specific to `<pre>` element, preserves (most) whitespace in normalized text."""

    @property
    def _normalized_text(self) -> str:
        """Consolidate `texts` into a single whitespace-normalized string.

        This normalization is specific to the `<pre>` element. Only a leading and or trailing
        newline is removed. All other whitespace is preserved.
        """
        text = "".join(ts.text for ts in self._text_segments)

        start = 1 if text.startswith("\n") else 0
        end = -1 if text.endswith("\n") else len(text)

        return text[start:end]


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

    @lazyproperty
    def _element_accum(self) -> _ElementAccumulator:
        """Text-segment accumulator suitable for this block-element."""
        return _ElementAccumulator(self)

    def _element_from_text_or_tail(
        self, text: str, q: deque[Flow | Phrasing], ElementCls: type[Element] | None = None
    ) -> Iterator[Element]:
        """Generate zero-or-one paragraph formed from text and leading phrasing elements.

        Note this mutates `q` by popping phrasing elements off as they are processed.
        """
        element_accum = self._element_accum

        for node in self._iter_text_segments(text, q):
            if isinstance(node, TextSegment):
                element_accum.add(node)
            else:
                # -- otherwise x is an Element, which terminates any accumulating Element --
                yield from element_accum.flush(ElementCls)
                yield node

        yield from element_accum.flush(ElementCls)

    def _iter_text_segments(
        self, text: str, q: deque[Flow | Phrasing]
    ) -> Iterator[TextSegment | Element]:
        """Generate zero-or-more `TextSegment`s or `Element`s from text and leading phrasing.

        Note that while this method is named "._iter_text_segments()", it can also generate
        `Element` objects when a block item is nested within a phrasing element. This is not
        technically valid HTML, but folks write some wacky HTML and the browser is pretty forgiving
        so we try to do the right thing (what the browser does) when that happens, generally
        interpret each nested block as its own paragraph and generate a separate `Element` object
        for each.

        This method is used to process the text or tail of a block element, including any phrasing
        elements immediately following the text or tail.

        For example, this <div>:

            <div>
               For a <b>moment, <i>nothing</i> happened.</b>
               <p>Then, after a second or so, nothing continued to happen.</p>
               The dolphins had always believed that <em>they</em> were far more intelligent.
            </div>

        Should generate three distinct elements:
        - One for the div's text "For a " and the <b> phrasing element after it,
        - one for the <p> element, and
        - one for the tail of the <p> and the phrasing <em> element that follows it.

        This method is invoked to process the first line beginning "For a" and the third line
        beginning "The dolphins", in two separate calls.

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


class Pre(BlockItem):
    """Custom element-class for `<pre>` element.

    Can only contain phrasing content.
    """

    @lazyproperty
    def _element_accum(self) -> _ElementAccumulator:
        """Text-segment accumulator suitable for this block-element."""
        return _PreElementAccumulator(self)


class ImageBlock(Flow):
    """Custom element-class for `<img>` elements."""

    BASE64_IMAGE_REGEX = re.compile(r"^data:(image/[^;]+);base64,(.*)")

    def iter_elements(self) -> Iterator[Element]:
        """Generate an Image element based on `src`, `data-src`, and `alt`."""
        img_src = self.get("data-src", "").strip() or self.get("src", "").strip()
        img_alt = self.get("alt", "").strip()

        if not img_src:  # Early exit if no image source
            return

        mime_match = self.BASE64_IMAGE_REGEX.match(img_src)
        img_mime_type = mime_match.group(1) if mime_match else None
        img_base64 = mime_match.group(2) if mime_match else None
        img_url = None if img_base64 else img_src

        yield Image(
            text=img_alt,
            metadata=ElementMetadata(
                image_mime_type=img_mime_type,
                image_base64=img_base64,
                image_url=img_url,
            ),
        )


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

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment | Element]:
        """Generate text segments for text, children, and tail of this element."""
        inside_emphasis = self._inside_emphasis(enclosing_emphasis)

        yield from self._iter_text_segment(inside_emphasis)

        # -- Recurse into any nested tags. All child tags are assumed to also be phrasing tags. --
        yield from self._iter_child_text_segments(inside_emphasis)

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
            if (normalized_text := _normalize_text(text)) and emphasis
            else {}
        )

    def _inside_emphasis(self, enclosing_emphasis: str) -> str:
        """By default, the inside emphasis is the same as the outside emphasis.

        This method is overridden by sub-classes that annotate particular emphasis types but many
        phrasing elements do not contribute to annotations.
        """
        return enclosing_emphasis

    def _iter_child_text_segments(self, emphasis: str) -> Iterator[TextSegment | Element]:
        """Generate zero-or-more text-segments for phrasing children of this element.

        All generated text segments will be annotated with `emphasis` when it is other than the
        empty string.
        """
        q: deque[Flow | Phrasing] = deque(self)
        # -- Recurse into any nested tags. Phrasing children contribute `TextSegment`s to the
        # -- stream. Block children contribute document `Element`s. Note however that a phrasing
        # -- child can also produce an `Element` from any nested block element.
        while q:
            child = q.popleft()
            if child.is_phrasing:
                yield from cast(Phrasing, child).iter_text_segments(emphasis)
            else:
                yield from cast(Flow, child).iter_elements()
                yield from self._iter_text_segments_from_block_tail_and_phrasing(
                    child.tail or "", q, emphasis
                )

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

    def _iter_text_segments_from_block_tail_and_phrasing(
        self, tail: str, q: deque[Flow | Phrasing], emphasis: str
    ) -> Iterator[TextSegment | Element]:
        """Generate zero-or-more `TextSegment`s or `Element`s from tail+phrasing of block child.

        When this phrasing element contains a block child (not valid HTML but accepted by
        browsers), the tail of that block child and any phrasing elements contiguous with that tail
        also need to contribute their text. This method takes care of that job.

        Note this mutates `q` by popping phrasing elements off as they are processed.
        """
        if tail:
            yield TextSegment(tail, self._annotation(tail, emphasis))
        while q and q[0].is_phrasing:
            e = cast(Phrasing, q.popleft())
            yield from e.iter_text_segments(emphasis)


class Anchor(Phrasing):
    """Custom element-class for `<a>` element.

    Provides link annotations.
    """

    def iter_text_segments(self, enclosing_emphasis: str = "") -> Iterator[TextSegment | Element]:
        """Generate text segments for contents and tail of this element, when they exist.

        Phrasing is emitted as `TextSegment` objects. Any nested block items (not valid HTML but
        are accepted by browser so can occur) are emitted as `Element` objects.

        When an anchor contains a nested block element, there can be multiple phrases and/or
        elements. Link annotation is only added to the first phrase or element. Otherwise the link
        annotation would span multiple document-elements.
        """
        q: deque[Phrase | Element] = deque(self._iter_phrases_and_elements(enclosing_emphasis))

        # -- the first non-whitespace phrase or element gets the link annotation --
        while q:
            x = q.popleft()
            if isinstance(x, Element):
                yield self._link_annotate_element(x)
                break
            else:
                # -- a whitespace-only phrase will not receive the link annotation (no link text) --
                if lts := self._link_text_segment(x):
                    yield lts
                    break
                else:
                    yield from x

        # -- whatever phrases or elements remain are emitted without link annotation --

        while q:
            x = q.popleft()
            if isinstance(x, Element):
                yield x
            else:
                yield from x

        # -- A tail is emitted when present whether anchor itself was emitted or not --
        yield from self._iter_tail_segment(enclosing_emphasis)

    def _iter_phrases_and_elements(self, emphasis: str) -> Iterator[Phrase | Element]:
        """Divide contents (text+children, but not tail) into phrases and document-elements."""
        # -- place child elements in a queue, method calls use some and leave the rest --
        q: deque[Flow | Phrasing] = deque(self)

        yield from self._iter_phrasing(self.text or "", q, emphasis)

        while q:
            assert not q[0].is_phrasing
            block_item = cast(Flow, q.popleft())
            yield from block_item.iter_elements()
            yield from self._iter_phrasing(block_item.tail or "", q, emphasis)

    def _iter_phrasing(
        self, text: str, q: deque[Flow | Phrasing], emphasis: str
    ) -> Iterator[Phrase | Element]:
        """Generate zero-or-more `TextSegment`s or `Element`s from text and leading phrasing.

        Note that while this method is named "._iter_phrasing()", it can also generate `Element`
        objects when a block item is nested within a phrasing element. This is not technically
        valid HTML, but folks write some wacky HTML and the browser is pretty forgiving so we try
        to do the right thing (what the browser does) when that happens, generally interpret each
        nested block as its own paragraph and generate a separate `Element` object for each.

        This method is used to process the text or tail of a block element, including any phrasing
        elements immediately following the text or tail.

        Note this method mutates `q` by popping phrasing elements off as they are processed.
        """
        phrase_accum = _PhraseAccumulator()

        if text:
            phrase_accum.add(TextSegment(text, self._annotation(text, emphasis)))

        while q and q[0].is_phrasing:
            e = cast(Phrasing, q.popleft())
            for x in e.iter_text_segments(emphasis):
                if isinstance(x, TextSegment):
                    phrase_accum.add(x)
                # -- otherwise x is an `Element`, which terminates the accumulating phrase --
                else:
                    yield from phrase_accum.flush()
                    yield x

        # -- emit any phrase remaining in accumulator --
        yield from phrase_accum.flush()

    def _link_annotate_element(self, element: Element) -> Element:
        """Apply this link's annotation to `element` and return it."""
        link_text = element.text
        link_url = self.get("href")

        if not link_text or not link_url:
            return element

        element.metadata.link_texts = (element.metadata.link_texts or []) + [link_text]
        element.metadata.link_urls = (element.metadata.link_urls or []) + [link_url]

        return element

    def _link_text_segment(self, phrase: Phrase) -> TextSegment | None:
        """Consolidate `phrase` into a single text-segment with link annotation.

        Returns None if the phrase contains only whitespace.
        """
        consolidated_text = "".join(text_segment.text for text_segment in phrase)
        link_text = _normalize_text(consolidated_text)
        link_url = self.get("href")

        if not link_text or not link_url:
            return None

        # -- the emphasis annotations must come from the individual text segments in the phrase --
        consolidated_annotations = _consolidate_annotations(
            (
                {"link_texts": [link_text], "link_urls": [link_url]},
                *(text_segment.annotation for text_segment in phrase),
            )
        )

        return TextSegment(consolidated_text, consolidated_annotations)


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
        """If asked (by a parent Flow element), identify as a phrasing element.

        It's not possible to determine the display intent (block|inline) of an unknown element
        (like `<foobar>`) and phrasing is less disruptive, adding the tail of this element to any
        text or phrasing content before and after it without starting a new paragraph.
        """
        return True

    def iter_elements(self) -> Iterator[Element]:
        """Don't generate any document-elements when behaving like a Flow element.

        Because the element identifies as phrasing and will always be enclosed by at least a
        `<body>` element, this method should never be called. However, it's easier to prove it does
        the appropriate thing if it is called than prove that it can never happen.
        """
        return
        yield

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
        "section": Flow,
        # -- block items --
        "h1": Heading,
        "h2": Heading,
        "h3": Heading,
        "h4": Heading,
        "h5": Heading,
        "h6": Heading,
        "p": BlockItem,
        "pre": Pre,
        # -- list blocks --
        "ol": ListBlock,
        "ul": ListBlock,
        "li": ListItemBlock,
        # -- image --
        "img": ImageBlock,
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
        "label": RemovedPhrasing,
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
        "summary": RemovedBlock,  # -- child of `details`
    }
)
