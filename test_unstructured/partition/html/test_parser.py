# pyright: reportPrivateUsage=false
# pyright: reportUnknownArgumentType=false

"""Test suite for `unstructured.partition.html.parser` module."""

from __future__ import annotations

from collections import deque

import pytest
from lxml import etree

from unstructured.documents.elements import Address, Element, ListItem, NarrativeText, Text, Title
from unstructured.partition.html.parser import (
    Annotation,
    DefaultElement,
    Flow,
    Phrasing,
    RemovedPhrasing,
    TextSegment,
    _consolidate_annotations,
    _ElementAccumulator,
    _normalize_text,
    _PhraseAccumulator,
    _PreElementAccumulator,
    html_parser,
)

# -- MODULE-LEVEL FUNCTIONS ----------------------------------------------------------------------

# -- _consolidate_annotations() ------------------


def it_consolidates_annotations_from_multiple_text_segments():
    annotations = [
        {
            "link_texts": "Ford Prefect",
            "link_url": "https://wikipedia/Ford_Prefect",
            "emphasized_text_contents": "Ford Prefect",
            "emphasized_text_tags": "b",
        },
        {
            "emphasized_text_contents": "alien encounter",
            "emphasized_text_tags": "bi",
        },
    ]

    annotations = _consolidate_annotations(annotations)

    assert annotations == {
        # -- each distinct key gets a list of values --
        "emphasized_text_contents": ["Ford Prefect", "alien encounter"],
        "emphasized_text_tags": ["b", "bi"],
        # -- even when there is only one value --
        "link_texts": ["Ford Prefect"],
        "link_url": ["https://wikipedia/Ford_Prefect"],
    }
    # -- and the annotations mapping is immutable --
    with pytest.raises(TypeError, match="object does not support item assignment"):
        annotations["new_key"] = "foobar"  # pyright: ignore[reportIndexIssue]
    # -- (but not its list values unfortunately) --
    annotations["emphasized_text_tags"].append("xyz")
    assert annotations["emphasized_text_tags"] == ["b", "bi", "xyz"]


# -- _normalize_text() ---------------------------


@pytest.mark.parametrize(
    ("text", "expected_value"),
    [
        # -- already normalized text is left unchanged --
        ("iterators allow", "iterators allow"),
        # -- newlines are treated as whitespace --
        ("algorithm\nto   be", "algorithm to be"),
        ("  separated\n  from  ", "separated from"),
        ("\n container\n details\n ", "container details"),
        (
            "\n  iterators  allow \n algorithm to be   \nexpressed  without container  \nnoise",
            "iterators allow algorithm to be expressed without container noise",
        ),
    ],
)
def test_normalize_text_produces_normalized_text(text: str, expected_value: str):
    assert _normalize_text(text) == expected_value


# -- PHRASING ACCUMULATORS -----------------------------------------------------------------------


class Describe_PhraseAccumulator:
    """Isolated unit-test suite for `unstructured.partition.html.parser._PhraseAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = _PhraseAccumulator()

        phrase_iter = accum.flush()

        with pytest.raises(StopIteration):
            next(phrase_iter)

    # -- .add() -----------------------------------------------------------

    def it_accumulates_text_segments(self):
        accum = _PhraseAccumulator()

        accum.add(TextSegment("Ford... you're turning ", {}))
        accum.add(TextSegment("into a penguin.", {}))
        phrase_iter = accum.flush()

        phrase = next(phrase_iter)
        assert phrase == (
            TextSegment("Ford... you're turning ", {}),
            TextSegment("into a penguin.", {}),
        )

        with pytest.raises(StopIteration):
            next(phrase_iter)

    # -- .flush() ---------------------------------------------------------

    def it_generates_zero_phrases_on_flush_when_empty(self):
        accum = _PhraseAccumulator()

        phrase_iter = accum.flush()

        with pytest.raises(StopIteration):
            next(phrase_iter)


class Describe_ElementAccumulator:
    """Isolated unit-test suite for `unstructured.partition.html.parser._ElementAccumulator`."""

    def it_is_empty_on_construction(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)

        element_iter = accum.flush(None)

        with pytest.raises(StopIteration):
            next(element_iter)

    # -- .add() -----------------------------------------------------------

    def it_accumulates_text_segments(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)

        accum.add(TextSegment("Ford... you're turning ", {}))
        accum.add(TextSegment("into a penguin.", {}))
        element_iter = accum.flush(None)

        element = next(element_iter)
        assert element == NarrativeText("Ford... you're turning into a penguin.")

        with pytest.raises(StopIteration):
            next(element_iter)

    # -- .flush() ---------------------------------------------------------

    def it_generates_zero_elements_when_empty(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)

        element_iter = accum.flush(None)

        with pytest.raises(StopIteration):
            next(element_iter)

    def and_it_generates_zero_elements_when_all_its_text_segments_are_whitespace_only(
        self, html_element: etree.ElementBase
    ):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment(" \n   \t \n", {}))
        accum.add(TextSegment("   \n", {}))

        with pytest.raises(StopIteration):
            next(accum.flush(None))

    def and_it_generates_zero_elements_when_there_is_only_one_non_whitespace_character(
        self, html_element: etree.ElementBase
    ):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment(" \n   \t \n", {}))
        accum.add(TextSegment(" X \n", {}))

        with pytest.raises(StopIteration):
            next(accum.flush(None))

    def it_normalizes_the_text_of_its_text_segments_on_flush(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment(" \n  Ford...   you're \t turning\n", {}))
        accum.add(TextSegment("into a   penguin.\n", {}))

        (element,) = accum.flush(None)

        assert element.text == "Ford... you're turning into a penguin."

    def it_creates_a_document_element_of_the_specified_type(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment("Ford... you're turning into a penguin.", {}))

        (element,) = accum.flush(ListItem)

        assert element == ListItem("Ford... you're turning into a penguin.")

    def but_it_derives_the_element_type_from_the_text_when_none_is_specified(
        self, html_element: etree.ElementBase
    ):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment("Ford... you're turning into a penguin.", {}))

        (element,) = accum.flush(None)

        assert element == NarrativeText("Ford... you're turning into a penguin.")

    def it_removes_an_explicit_leading_bullet_character_from_a_list_item(
        self, html_element: etree.ElementBase
    ):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment("* turning into a penguin", {}))

        (element,) = accum.flush(None)

        assert element == ListItem("turning into a penguin")

    def it_applies_category_depth_metadata(self):
        html_element = etree.fromstring("<h3>About fish</h3>", html_parser).xpath(".//h3")[0]
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment("Thanks for all those!", {}))

        (element,) = accum.flush(Title)

        e = element.to_dict()
        e.pop("element_id")
        assert e == {
            "metadata": {"category_depth": 2},
            "text": "Thanks for all those!",
            "type": "Title",
        }

    def and_it_consolidates_annotations_into_metadata(self, html_element: etree.ElementBase):
        accum = _ElementAccumulator(html_element)
        accum.add(
            TextSegment(
                "\n    Ford...",
                {
                    "emphasized_text_contents": "Ford",
                    "emphasized_text_tags": "b",
                },
            )
        )
        accum.add(TextSegment(" you're turning into a ", {}))
        accum.add(
            TextSegment(
                "penguin",
                {
                    "emphasized_text_contents": "penguin",
                    "emphasized_text_tags": "i",
                },
            )
        )
        accum.add(TextSegment(".\n", {}))

        (element,) = accum.flush(NarrativeText)

        e = element.to_dict()
        e.pop("element_id")
        assert e == {
            "metadata": {
                "emphasized_text_contents": [
                    "Ford",
                    "penguin",
                ],
                "emphasized_text_tags": [
                    "b",
                    "i",
                ],
            },
            "text": "Ford... you're turning into a penguin.",
            "type": "NarrativeText",
        }

    # -- ._category_depth() -----------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "tag", "ElementCls", "expected_value"),
        [
            ("<p>Ford... you're turning into a penguin. Stop it.<p>", "p", Text, None),
            ("<p>* thanks for all the fish.</p>", "p", ListItem, 0),
            ("<li>thanks for all the fish.</li>", "li", ListItem, 0),
            ("<ul><li>So long</li><li>and thanks for all the fish.</li></ul>", "li", ListItem, 1),
            ("<dl><dd>So long<ol><li>and thanks for the fish.</li></ol></ul>", "li", ListItem, 2),
            ("<p>Examples</p>", "p", Title, 0),
            ("<h1>Examples</h1>", "h1", Title, 0),
            ("<h2>Examples</h2>", "h2", Title, 1),
            ("<h3>Examples</h3>", "h3", Title, 2),
            ("<h4>Examples</h4>", "h4", Title, 3),
            ("<h5>Examples</h5>", "h5", Title, 4),
            ("<h6>Examples</h6>", "h6", Title, 5),
        ],
    )
    def it_computes_the_category_depth_to_help(
        self, html_text: str, tag: str, ElementCls: type[Element], expected_value: int | None
    ):
        e = etree.fromstring(html_text, html_parser).xpath(f".//{tag}")[0]
        accum = _ElementAccumulator(e)
        assert accum._category_depth(ElementCls) == expected_value

    # -- ._normalized_text ------------------------------------------------

    def it_computes_the_normalized_text_of_its_text_segments_to_help(
        self, html_element: etree.ElementBase
    ):
        accum = _ElementAccumulator(html_element)
        accum.add(TextSegment(" \n  Ford...   you're \t turning\n", {}))
        accum.add(TextSegment("into a   penguin.\n", {}))

        assert accum._normalized_text == "Ford... you're turning into a penguin."

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def html_element(self) -> etree.ElementBase:
        return etree.fromstring("<p/>", html_parser).xpath(".//p")[0]


class Describe_PreElementAccumulator:
    """Isolated unit-test suite for `unstructured.partition.html.parser._PreElementAccumulator`."""

    def it_computes_the_normalized_text_of_its_text_segments_to_help(self):
        html_element = etree.fromstring("<p/>", html_parser).xpath(".//p")[0]
        accum = _PreElementAccumulator(html_element)
        accum.add(TextSegment("\n\n", {}))
        accum.add(TextSegment("    The panel lit up\n", {}))
        accum.add(TextSegment("    with the words 'Please do not press\n", {}))
        accum.add(TextSegment("    this button again'\n\n", {}))

        # -- note single leading and trailing newline stripped --
        assert accum._normalized_text == (
            "\n"
            "    The panel lit up\n"
            "    with the words 'Please do not press\n"
            "    this button again'\n"
        )


# -- FLOW (BLOCK-ITEM) ELEMENTS ------------------------------------------------------------------


class DescribeFlow:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Flow`.

    The `Flow` class provides most behaviors for flow (block-level) elements.
    """

    # -- .is_phrasing -----------------------------------------------------

    def it_knows_it_is_NOT_a_phrasing_element(self):
        p = etree.fromstring("<p>Hello</p>", html_parser).xpath(".//p")[0]

        assert isinstance(p, Flow)
        assert p.is_phrasing is False

    # -- .iter_elements() -------------------------------------------------

    def it_generates_the_document_elements_from_the_Flow_element(self):
        """Phrasing siblings of child block elements are processed with text or tail.

        In the general case, a Flow element can contain text, phrasing content, and child flow
        elements.

        Each of these five lines in this example is a "paragraph" and gives rise to a distinct
        document-element.
        """
        html_text = """
          <div>
            Text of div <b>with <i>hierarchical</i>\nphrasing</b> content before first block item
            <p>Click <a href="http://blurb.io">here</a> to see the blurb for this block item. </p>
            tail of block item <b>with <i>hierarchical</i> phrasing </b> content
            <p>second block item</p>
            tail of block item <b>with <i>  hierarchical  </i></b> phrasing content
          </div>
        """
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div.iter_elements()

        e = next(elements)
        assert e == Title("Text of div with hierarchical phrasing content before first block item")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical", "phrasing"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }
        e = next(elements)
        assert e == NarrativeText("Click here to see the blurb for this block item.")
        assert e.metadata.to_dict() == {"link_texts": ["here"], "link_urls": ["http://blurb.io"]}
        e = next(elements)
        assert e == Title("tail of block item with hierarchical phrasing content")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical", "phrasing"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }
        e = next(elements)
        assert e == Title("second block item")
        assert e.metadata.to_dict() == {"category_depth": 0}
        e = next(elements)
        assert e == Title("tail of block item with hierarchical phrasing content")
        assert e.metadata.to_dict() == {
            "category_depth": 0,
            "emphasized_text_contents": ["with", "hierarchical"],
            "emphasized_text_tags": ["b", "bi"],
        }
        with pytest.raises(StopIteration):
            e = next(elements)

    # -- ._element_from_text_or_tail() ------------------------------------

    def it_assembles_text_and_tail_document_elements_to_help(self):
        """Text and tails and their phrasing content are both processed the same way."""
        html_text = "<div>The \n Roman <b>poet <i>   Virgil</i> gave</b> his <q>pet</q> fly</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Text)

        e = next(elements)
        # -- element text is normalized --
        assert e == Text("The Roman poet Virgil gave his pet fly")
        # -- individual annotations are consolidated --
        assert e.metadata.to_dict() == {
            "emphasized_text_contents": ["poet", "Virgil", "gave"],
            "emphasized_text_tags": ["b", "bi", "b"],
        }

    def but_it_does_not_generate_a_document_element_when_only_whitespace_is_contained(self):
        html_text = "<div>   <b> \n <i>  \n </i>  </b>   <q> \n </q> \n  </div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Text)

        with pytest.raises(StopIteration):
            next(elements)

    def it_uses_the_specified_element_class_to_form_the_document_element(self):
        html_text = "<div>\n  The line-storm clouds fly tattered and swift\n</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div), Address)

        e = next(elements)
        assert e == Address("The line-storm clouds fly tattered and swift")
        assert e.metadata.to_dict() == {}
        with pytest.raises(StopIteration):
            next(elements)

    def and_it_selects_the_document_element_class_by_analyzing_the_text_when_not_specified(self):
        html_text = "<div>\n  The line-storm clouds fly tattered and swift,\n</div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div))

        assert next(elements) == NarrativeText("The line-storm clouds fly tattered and swift,")

    def but_it_does_not_generate_a_document_element_when_only_a_bullet_character_is_contained(self):
        html_text = "<div> * </div>"
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        elements = div._element_from_text_or_tail(div.text, deque(div))

        with pytest.raises(StopIteration):
            next(elements)

    # -- ._iter_text_segments() -------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            (  # -- text with no phrasing --
                "<p>Ford... you're turning into a penguin.<p>",
                [("Ford... you're turning into a penguin.", {})],
            ),
            (  # -- text with phrasing --
                "<p>Ford... <b>you're turning</b> into\na <i>penguin</i>.<p>",
                [
                    ("Ford... ", {}),
                    (
                        "you're turning",
                        {"emphasized_text_contents": "you're turning", "emphasized_text_tags": "b"},
                    ),
                    (" into\na ", {}),
                    (
                        "penguin",
                        {"emphasized_text_contents": "penguin", "emphasized_text_tags": "i"},
                    ),
                    (".", {}),
                ],
            ),
            (  # -- text with nested phrasing --
                "<p>Ford... <b>you're <i>turning</i></b> into a penguin.<p>",
                [
                    ("Ford... ", {}),
                    (
                        "you're ",
                        {"emphasized_text_contents": "you're", "emphasized_text_tags": "b"},
                    ),
                    (
                        "turning",
                        {"emphasized_text_contents": "turning", "emphasized_text_tags": "bi"},
                    ),
                    (" into a penguin.", {}),
                ],
            ),
        ],
    )
    def it_recursively_generates_text_segments_from_text_and_phrasing_to_help(
        self, html_text: str, expected_value: list[Annotation]
    ):
        p = etree.fromstring(html_text, html_parser).xpath(".//p")[0]
        text_segments = list(p._iter_text_segments(p.text, deque(p)))

        assert text_segments == expected_value


class DescribePre:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Pre`.

    The `Pre` class specializes behaviors for the `<pre>` (pre-formatted text) element.
    """

    def it_preserves_the_whitespace_of_its_phrasing_only_contents(self):
        """A `<pre>` element can contain only phrasing content."""
        html_text = (
            "<pre>\n"
            "  The Answer to the Great Question...   Of Life, the Universe and Everything...\n"
            "  Is... Forty-two, said Deep Thought, with infinite majesty and calm.\n"
            "</pre>\n"
        )
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]

        elements = pre.iter_elements()

        e = next(elements)
        assert e == Text(
            "  The Answer to the Great Question...   Of Life, the Universe and Everything...\n"
            "  Is... Forty-two, said Deep Thought, with infinite majesty and calm."
        )
        with pytest.raises(StopIteration):
            next(elements)

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- a newline in the 0th position of pre.text is dropped --
            ("<pre>\n  foo  </pre>", "  foo  "),
            # -- but not when preceded by any other whitespace --
            ("<pre> \n  foo  </pre>", " \n  foo  "),
            # -- and only one is dropped --
            ("<pre>\n\n  foo  </pre>", "\n  foo  "),
            # -- a newline in the -1th position is dropped --
            ("<pre>  foo  \n</pre>", "  foo  "),
            # -- but not when followed by any other whitespace --
            ("<pre>  foo  \n </pre>", "  foo  \n "),
            # -- and only one is dropped --
            ("<pre>  foo  \n\n</pre>", "  foo  \n"),
            # -- a newline in both positions are both dropped --
            ("<pre>\n  foo  \n</pre>", "  foo  "),
            # -- or not when not at the absolute edge --
            ("<pre> \n  foo  \n </pre>", " \n  foo  \n "),
        ],
    )
    def but_it_strips_a_single_leading_or_trailing_newline(
        self, html_text: str, expected_value: str
    ):
        """Content starts on next line when opening `<pre>` tag is immediately followed by `\n`"""
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]
        e = next(pre.iter_elements())

        assert e.text == expected_value

    def it_assigns_emphasis_and_link_metadata_when_contents_have_those_phrasing_elements(self):
        html_text = '<pre>You\'re <b>turning</b> into a <a href="http://eie.io">penguin</a>.</pre>'
        pre = etree.fromstring(html_text, html_parser).xpath(".//pre")[0]

        e = next(pre.iter_elements())

        assert e.text == "You're turning into a penguin."
        assert e.metadata.emphasized_text_contents == ["turning"]
        assert e.metadata.emphasized_text_tags == ["b"]
        assert e.metadata.link_texts == ["penguin"]
        assert e.metadata.link_urls == ["http://eie.io"]


class DescribeRemovedBlock:
    """Isolated unit-test suite for `unstructured.partition.html.parser.RemovedBlock`.

    This class is used for block level items we want to skip like `<hr/>` and `<figure>`.
    """

    def it_is_skipped_during_parsing(self):
        html_text = """
          <div>
            <hr/>
            <figure>
              <img src="/media/cc0-images/elephant-660-480.jpg" alt="Elephant at sunset" />
              <figcaption>An elephant at sunset</figcaption>
            </figure>
            <p>Content we want.</p>
          </div>
          """
        div = etree.fromstring(html_text, html_parser).xpath(".//div")[0]

        assert list(div.iter_elements()) == [NarrativeText("Content we want.")]


# -- PHRASING (INLINE) ELEMENTS ------------------------------------------------------------------


class DescribePhrasing:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Phrasing`.

    The `Phrasing` class provides most behaviors for phrasing (inline) elements.
    """

    # -- .is_phrasing -----------------------------------------------------

    def it_knows_it_is_a_phrasing_element(self):
        b = etree.fromstring("<b>Hello</b>", html_parser).xpath(".//b")[0]

        assert isinstance(b, Phrasing)
        assert b.is_phrasing is True

    # -- .iter_text_segments() --------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- an empty element produces no text segments --
            ("<code></code>", []),
            # -- element text produces one segment --
            ("<data> foo </data>", [(" foo ", {})]),
            # -- element tail produces one segment --
            ("<dfn/> bar ", [(" bar ", {})]),
            # -- element descendants each produce one segment --
            ("<kbd><mark>foo <meter>bar</meter></mark></kbd>", [("foo ", {}), ("bar", {})]),
            # -- and any combination produces a segment for each text, child, and tail --
            (
                "<kbd> <mark>foo <meter>bar</meter> baz</mark> </kbd>",
                [
                    (" ", {}),
                    ("foo ", {}),
                    ("bar", {}),
                    (" baz", {}),
                    (" ", {}),
                ],
            ),
        ],
    )
    def it_generates_text_segments_for_its_text_and_children_and_tail(
        self, html_text: str, expected_value: list[TextSegment]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        assert list(e.iter_text_segments()) == expected_value

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- Phrasing with nested block but no text or tail produces only element for block --
            ("<strong><p>aaa</p></strong>", [Title("aaa")]),
            # -- Phrasing with text produces annotated text-segment for the text --
            (
                "<strong>aaa<p>bbb</p></strong>",
                [
                    TextSegment(
                        "aaa", {"emphasized_text_contents": "aaa", "emphasized_text_tags": "b"}
                    ),
                    Title("bbb"),
                ],
            ),
            # -- Phrasing with tail produces annotated text-segment for the tail --
            (
                "<strong><p>aaa</p>bbb</strong>",
                [
                    Title("aaa"),
                    TextSegment(
                        "bbb", {"emphasized_text_contents": "bbb", "emphasized_text_tags": "b"}
                    ),
                ],
            ),
            # -- Phrasing with text, nested block, and tail produces all three --
            (
                "<strong>aaa<p>bbb</p>ccc</strong>",
                [
                    TextSegment(
                        "aaa", {"emphasized_text_contents": "aaa", "emphasized_text_tags": "b"}
                    ),
                    Title("bbb"),
                    TextSegment(
                        "ccc", {"emphasized_text_contents": "ccc", "emphasized_text_tags": "b"}
                    ),
                ],
            ),
        ],
    )
    def but_it_can_also_generate_an_element_when_it_has_a_nested_block_element(
        self, html_text: str, expected_value: list[TextSegment | Element]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        assert list(e.iter_text_segments()) == expected_value

    # -- ._annotation() ---------------------------------------------------

    def it_forms_its_annotations_from_emphasis(self):
        cite = etree.fromstring("<cite/>", html_parser).xpath(".//cite")[0]
        assert cite._annotation("\n  foobar\n  ", "bi") == {
            "emphasized_text_contents": "foobar",
            "emphasized_text_tags": "bi",
        }

    @pytest.mark.parametrize("text", ["", "\n  \t  "])
    def but_not_when_text_is_empty_or_whitespace(self, text: str):
        cite = etree.fromstring("<cite/>", html_parser).xpath(".//cite")[0]
        assert cite._annotation(text, "bi") == {}

    def and_not_when_there_is_no_emphasis(self):
        cite = etree.fromstring("<cite/>", html_parser).xpath(".//cite")[0]
        assert cite._annotation("foobar", "") == {}

    # -- ._inside_emphasis() ----------------------------------------------

    @pytest.mark.parametrize("enclosing_emphasis", ["", "b", "bi"])
    def it_uses_the_enclosing_emphasis_as_the_default_inside_emphasis(
        self, enclosing_emphasis: str
    ):
        """Inside emphasis is applied to text inside the phrasing element (but not its tail).

        The `._inside_emphasis()` method is overridden by Bold and Italic classes which add their
        specific emphasis characters.
        """
        abbr = etree.fromstring("<abbr/>", html_parser).xpath(".//abbr")[0]
        assert abbr._inside_emphasis(enclosing_emphasis) == enclosing_emphasis

    # -- ._iter_child_text_segments() -------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "expected_value"),
        [
            # -- a phrasing element with no children produces no text segments
            # -- (element text is handled elsewhere)
            ("<abbr>aaa</abbr>", []),
            # -- child phrasing element produces text-segment for its text --
            ("<bdi>x<bdo>bbb</bdo></bdi>", [TextSegment("bbb", {})]),
            # -- and also for its tail when it has one --
            ("<bdi>x<bdo>bbb</bdo>ccc</bdi>", [TextSegment("bbb", {}), TextSegment("ccc", {})]),
            # -- nested phrasing recursively each produce a segment for text and tail, in order --
            (
                "<big>xxx<cite>aaa<code>bbb<data>ccc</data>ddd</code>eee</cite>fff</big>",
                [
                    TextSegment("aaa", {}),
                    TextSegment("bbb", {}),
                    TextSegment("ccc", {}),
                    TextSegment("ddd", {}),
                    TextSegment("eee", {}),
                    TextSegment("fff", {}),
                ],
            ),
        ],
    )
    def it_generates_text_segments_for_its_children_and_their_tails(
        self, html_text: str, expected_value: list[TextSegment]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        assert list(e._iter_child_text_segments("")) == expected_value

    @pytest.mark.parametrize(
        ("html_text", "inside_emphasis", "expected_value"),
        [
            # -- a phrasing element with no block children produces no elements --
            ("<dfn></dfn>", "", []),
            # -- a child block element produces an element --
            ("<kbd><p>aaa</p></kbd>", "", [Title("aaa")]),
            # -- a child block element with a tail also produces a text-segment for the tail --
            ("<kbd><p>aaa</p>bbb</kbd>", "", [Title("aaa"), TextSegment("bbb", {})]),
            # -- and also text-segments for phrasing following the tail --
            (
                "<kbd><p>aaa</p>bbb<mark>ccc</mark>ddd</kbd>",
                "",
                [
                    Title("aaa"),
                    TextSegment("bbb", {}),
                    TextSegment("ccc", {}),
                    TextSegment("ddd", {}),
                ],
            ),
            # -- and emphasis is applied before and after block-item --
            (
                "<strong><q>aaa</q><p>bbb</p>ccc<s>ddd</s>eee</strong>",
                "b",
                [
                    TextSegment(
                        "aaa", {"emphasized_text_contents": "aaa", "emphasized_text_tags": "b"}
                    ),
                    Title("bbb"),
                    TextSegment(
                        "ccc", {"emphasized_text_contents": "ccc", "emphasized_text_tags": "b"}
                    ),
                    TextSegment(
                        "ddd", {"emphasized_text_contents": "ddd", "emphasized_text_tags": "b"}
                    ),
                    TextSegment(
                        "eee", {"emphasized_text_contents": "eee", "emphasized_text_tags": "b"}
                    ),
                ],
            ),
        ],
    )
    def and_it_generates_elements_for_its_block_children(
        self, html_text: str, inside_emphasis: str, expected_value: list[TextSegment | Element]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        assert list(e._iter_child_text_segments(inside_emphasis)) == expected_value

    # -- ._iter_text_segments_from_block_tail_and_phrasing() --------------

    @pytest.mark.parametrize(
        ("html_text", "emphasis", "expected_value"),
        [
            # -- no tail and no contiguous phrasing produces no text-segments --
            ("<cite><p/></cite>", "", []),
            # -- tail produces a text-segment --
            ("<cite><p/>aaa</cite>", "", [TextSegment("aaa", {})]),
            # -- contiguous phrasing produces a text-segment --
            ("<cite><p/><s>aaa</s></cite>", "", [TextSegment("aaa", {})]),
            # -- tail of contiguous phrasing also produces a text-segment --
            ("<bdi><p/><s>aaa</s>bbb</bdi>", "", [TextSegment("aaa", {}), TextSegment("bbb", {})]),
            # -- nested phrasing produces a text-segment --
            (
                "<sub><p/>aaa<s>bbb<q>ccc</q>ddd</s>eee</sub>",
                "",
                [
                    TextSegment("aaa", {}),
                    TextSegment("bbb", {}),
                    TextSegment("ccc", {}),
                    TextSegment("ddd", {}),
                    TextSegment("eee", {}),
                ],
            ),
            # -- and emphasis is added to each text-segment when specified --
            (
                "<strong><p/>aaa<s>bbb<i>ccc</i>ddd</s>eee</strong>",
                "b",
                [
                    TextSegment(
                        "aaa", {"emphasized_text_contents": "aaa", "emphasized_text_tags": "b"}
                    ),
                    TextSegment(
                        "bbb", {"emphasized_text_contents": "bbb", "emphasized_text_tags": "b"}
                    ),
                    TextSegment(
                        "ccc", {"emphasized_text_contents": "ccc", "emphasized_text_tags": "bi"}
                    ),
                    TextSegment(
                        "ddd", {"emphasized_text_contents": "ddd", "emphasized_text_tags": "b"}
                    ),
                    TextSegment(
                        "eee", {"emphasized_text_contents": "eee", "emphasized_text_tags": "b"}
                    ),
                ],
            ),
            # -- a block item nested in contiguous phrasing produces an Element --
            (
                "<cite><p/>aaa<abbr>bbb<p>ccc</p>ddd</abbr>eee</cite>",
                "",
                [
                    TextSegment("aaa", {}),
                    TextSegment("bbb", {}),
                    Title("ccc"),
                    TextSegment("ddd", {}),
                    TextSegment("eee", {}),
                ],
            ),
        ],
    )
    def it_generates_text_segments_from_the_tail_and_contiguous_phrasing(
        self, html_text: str, emphasis: str, expected_value: list[TextSegment | Element]
    ):
        e = etree.fromstring(html_text, html_parser).xpath(".//body")[0][0]
        p = e.xpath("./p")[0]
        tail = p.tail or ""
        q = deque(e[1:])

        assert (
            list(e._iter_text_segments_from_block_tail_and_phrasing(tail, q, emphasis))
            == expected_value
        )


class DescribeAnchor:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Anchor`.

    The `Anchor` class is used for `<a>` tags and provides link metadata.
    """

    # -- .iter_text_segments() --------------------------------------------

    @pytest.mark.parametrize(
        ("html_text", "emphasis", "expected_value"),
        [
            # -- produces no text-segment or annotation for anchor.text when there is none --
            ('<a href="http://abc.com"></a>', "", []),
            # -- but it produces a text-segment for the tail if there is one --
            ('<a href="http://abc.com"></a> long tail ', "", [TextSegment(" long tail ", {})]),
            # -- produces text-segment but no annotation for anchor.text when it is whitespace --
            ('<a href="http://abc.com">  </a>', "", [TextSegment("  ", {})]),
            # -- produces text-segment and annotation for anchor text. Note `link_texts:`
            # -- annotation value is whitespace-normalized but text-segment text is not.
            (
                '<a href="http://abc.com"> click here </a>',
                "",
                [
                    TextSegment(
                        " click here ",
                        {"link_texts": ["click here"], "link_urls": ["http://abc.com"]},
                    )
                ],
            ),
            # -- produces text-segment for both text and tail when present --
            (
                '<a href="http://abc.com"> click here </a> long tail',
                "",
                [
                    TextSegment(
                        " click here ",
                        {"link_texts": ["click here"], "link_urls": ["http://abc.com"]},
                    ),
                    TextSegment(" long tail", {}),
                ],
            ),
            # -- nested phrasing inside <a> element is handled as expected --
            (
                '<p>I am <a href="http://eie.io">one <u>with<i> the</i></u> Force</a>.</p>',
                "",
                [
                    TextSegment(
                        "one with the Force",
                        {
                            "emphasized_text_contents": ["the"],
                            "emphasized_text_tags": ["i"],
                            "link_texts": ["one with the Force"],
                            "link_urls": ["http://eie.io"],
                        },
                    ),
                    TextSegment(".", {}),
                ],
            ),
            # -- enclosing_emphasis is applied to all segments --
            (
                '<p>I am <strong><a href="http://eie.io">one with</a> the Force.</strong></p>',
                "b",
                [
                    TextSegment(
                        "one with",
                        {
                            "emphasized_text_contents": ["one with"],
                            "emphasized_text_tags": ["b"],
                            "link_texts": ["one with"],
                            "link_urls": ["http://eie.io"],
                        },
                    ),
                    TextSegment(
                        " the Force.",
                        {
                            "emphasized_text_contents": "the Force.",
                            "emphasized_text_tags": "b",
                        },
                    ),
                ],
            ),
        ],
    )
    def it_generates_link_annotated_text_segments_for_its_text_and_a_tail_text_segment(
        self, html_text: str, emphasis: str, expected_value: list[TextSegment]
    ):
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        assert list(a.iter_text_segments(emphasis)) == expected_value

    def it_generates_enclosed_block_items_as_separate_elements(self):
        html_text = """<a href="http://eie.io">I am <p>one with</p> the Force.</a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a.iter_text_segments("b")) == [
            TextSegment(
                "I am ",
                {
                    "emphasized_text_contents": ["I am"],
                    "emphasized_text_tags": ["b"],
                    "link_texts": ["I am"],
                    "link_urls": ["http://eie.io"],
                },
            ),
            Title("one with"),
            TextSegment(
                " the Force.",
                {
                    "emphasized_text_contents": "the Force.",
                    "emphasized_text_tags": "b",
                },
            ),
        ]

    def and_it_annotates_first_enclosed_block_Element_when_no_non_whitespace_phrase_appears_first(
        self,
    ):
        html_text = """<a href="http://eie.io"> \n <p>I am one with</p> the Force.</a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        actual = list(a.iter_text_segments("i"))

        assert actual == [
            TextSegment(" \n ", {}),
            NarrativeText("I am one with"),
            TextSegment(
                " the Force.",
                {
                    "emphasized_text_contents": "the Force.",
                    "emphasized_text_tags": "i",
                },
            ),
        ]
        element = actual[1]
        assert element.metadata.link_texts == ["I am one with"]
        assert element.metadata.link_urls == ["http://eie.io"]

    # -- ._iter_phrases_and_elements() ------------------------------------

    def it_divides_the_anchor_contents_but_not_tail_into_phrases_and_elements(self):
        html_text = """
          <a href="http://eie.io">But always <p>see first.</p> Otherwise you </a> will only see
        """
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrases_and_elements(emphasis="")) == [
            (TextSegment("But always ", {}),),
            NarrativeText("see first."),
            (TextSegment(" Otherwise you ", {}),),
        ]

    # -- ._iter_phrasing() ------------------------------------------------

    def it_generates_zero_items_when_both_text_and_q_are_empty(self):
        html_text = """<a href="http://eie.io"></a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        with pytest.raises(StopIteration):
            next(a._iter_phrasing(text="", q=deque([]), emphasis=""))

    def it_generates_a_phrase_when_only_text_is_present(self):
        html_text = """<a href="http://eie.io">\n  But always see first.\n</a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrasing(text=a.text, q=deque(a), emphasis="")) == [
            (TextSegment("\n  But always see first.\n", {}),)
        ]

    def and_it_generates_a_phrase_when_that_text_is_followed_by_a_phrasing_element(self):
        html_text = """<a href="http://eie.io">But always <b>see <i>first</i></b>. Otherwise</a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrasing(text=a.text, q=deque(a), emphasis="")) == [
            (
                TextSegment("But always ", {}),
                TextSegment(
                    "see ",
                    {
                        "emphasized_text_contents": "see",
                        "emphasized_text_tags": "b",
                    },
                ),
                TextSegment(
                    "first",
                    {
                        "emphasized_text_contents": "first",
                        "emphasized_text_tags": "bi",
                    },
                ),
                TextSegment(". Otherwise", {}),
            )
        ]

    def it_ends_the_phrase_at_the_end_of_the_element(self):
        html_text = """<a href="http://eie.io">But always see first.</a> Otherwise you will """
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrasing(text=a.text, q=deque(a), emphasis="")) == [
            (TextSegment("But always see first.", {}),)
        ]

    def but_it_ends_at_a_block_element_if_one_occurs_first(self):
        html_text = """<a href="http://eie.io">But always see first. <p>Otherwise you </p> </a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrasing(text=a.text, q=deque(a), emphasis="")) == [
            (TextSegment("But always see first. ", {}),)
        ]

    def it_generates_an_element_for_a_block_item_nested_inside_phrasing(self):
        html_text = """
          <a href="http://eie.io">But <strong>always <p>see first.</p>Otherwise</strong> you </a>
        """
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]

        assert list(a._iter_phrasing(text=a.text, q=deque(a), emphasis="")) == [
            (
                TextSegment("But ", {}),
                TextSegment(
                    "always ",
                    {
                        "emphasized_text_contents": "always",
                        "emphasized_text_tags": "b",
                    },
                ),
            ),
            NarrativeText("see first."),
            (
                TextSegment(
                    "Otherwise",
                    {
                        "emphasized_text_contents": "Otherwise",
                        "emphasized_text_tags": "b",
                    },
                ),
                TextSegment(" you ", {}),
            ),
        ]

    # -- ._link_annotate_element() ----------------------------------------

    def it_adds_link_metadata_to_an_element_to_help(self):
        html_text = """<a href="http://eie.io"></a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        element = Text("aaa")

        e = a._link_annotate_element(element)

        assert e is element
        assert e.metadata.link_texts == ["aaa"]
        assert e.metadata.link_urls == ["http://eie.io"]

    def and_it_preserves_any_existing_link_metadata_on_the_element(self):
        # -- nested anchors shouldn't be possible but easier to test than prove it can't happen --
        html_text = """<a href="http://eie.io"></a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        element = Text("bbb")
        element.metadata.link_texts = ["abc"]
        element.metadata.link_urls = ["http://abc.com"]

        e = a._link_annotate_element(element)

        assert e is element
        assert e.metadata.link_texts == ["abc", "bbb"]
        assert e.metadata.link_urls == ["http://abc.com", "http://eie.io"]

    def but_not_when_the_text_is_empty(self):
        html_text = """<a href="http://eie.io"/>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        element = Text("")

        e = a._link_annotate_element(element)

        assert e is element
        assert e.metadata.link_texts is None
        assert e.metadata.link_urls is None

    def and_not_when_there_is_no_url(self):
        html_text = """<a/>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        element = Text("zzz")

        e = a._link_annotate_element(element)

        assert e is element
        assert e.metadata.link_texts is None
        assert e.metadata.link_urls is None

    # -- ._link_text_segment() --------------------------------------------

    def it_consolidates_a_phrase_into_a_single_link_annotated_TextSegment_to_help(self):
        html_text = """<a href="http://eie.io"></a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        phrase = (
            TextSegment(
                "Otherwise you will only ",
                {
                    "emphasized_text_contents": ["Otherwise"],
                    "emphasized_text_tags": ["i"],
                },
            ),
            TextSegment(
                "see what you were expecting.\n",
                {
                    "emphasized_text_contents": "expecting",
                    "emphasized_text_tags": "b",
                },
            ),
        )

        link_text_segment = a._link_text_segment(phrase)

        assert link_text_segment == TextSegment(
            "Otherwise you will only see what you were expecting.\n",
            {
                "emphasized_text_contents": ["Otherwise", "expecting"],
                "emphasized_text_tags": ["i", "b"],
                "link_texts": ["Otherwise you will only see what you were expecting."],
                "link_urls": ["http://eie.io"],
            },
        )

    @pytest.mark.parametrize("text", ["", " \n \t "])
    def but_not_when_the_text_is_empty_or_whitespace_only(self, text: str):
        html_text = """<a href="http://eie.io"></a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        phrase = (TextSegment(text, {}), TextSegment(text, {}), TextSegment(text, {}))

        assert a._link_text_segment(phrase) is None

    def and_not_when_the_anchor_has_no_href_url(self):
        html_text = """<a>foobar</a>"""
        a = etree.fromstring(html_text, html_parser).xpath(".//a")[0]
        phrase = (TextSegment("Otherwise", {}), TextSegment(" you will", {}))

        assert a._link_text_segment(phrase) is None


class DescribeBold:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Bold`.

    The `Bold` class is used for `<b>` and `<strong>` tags and adds emphasis metadata.
    """

    def it_annotates_its_text_segment_with_bold_emphasis(self):
        b = etree.fromstring("<b>rhombus</b>", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }

    def and_its_children_are_also_annotated_with_bold_emphasis(self):
        b = etree.fromstring("<b>rhombus <i>pentagon</i></b>", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus "
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }
        text, annotation = next(text_segments)
        assert text == "pentagon"
        assert annotation == {
            "emphasized_text_contents": "pentagon",
            "emphasized_text_tags": "bi",
        }

    def but_not_its_tail(self):
        b = etree.fromstring("<b>rhombus</b> pentagon", html_parser).xpath(".//b")[0]

        text_segments = b.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "b",
        }
        text, annotation = next(text_segments)
        assert text == " pentagon"
        assert annotation == {}


class DescribeItalic:
    """Isolated unit-test suite for `unstructured.partition.html.parser.Italic`.

    The `Italic` class is used for `<i>` and `<em>` tags and adds emphasis metadata.
    """

    def it_annotates_its_text_segment_with_italic_emphasis(self):
        i = etree.fromstring("<i>rhombus</i>", html_parser).xpath(".//i")[0]

        text_segments = i.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }

    def and_its_children_are_also_annotated_with_italic_emphasis(self):
        em = etree.fromstring("<em>rhombus <b>pentagon</b></em>", html_parser).xpath(".//em")[0]

        text_segments = em.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus "
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }
        text, annotation = next(text_segments)
        assert text == "pentagon"
        assert annotation == {
            "emphasized_text_contents": "pentagon",
            "emphasized_text_tags": "bi",
        }

    def but_not_its_tail(self):
        i = etree.fromstring("<i>rhombus</i> pentagon", html_parser).xpath(".//i")[0]

        text_segments = i.iter_text_segments()

        text, annotation = next(text_segments)
        assert text == "rhombus"
        assert annotation == {
            "emphasized_text_contents": "rhombus",
            "emphasized_text_tags": "i",
        }
        text, annotation = next(text_segments)
        assert text == " pentagon"
        assert annotation == {}


class DescribeLineBreak:
    """Isolated unit-test suite for `unstructured.partition.html.parser.LineBreak`.

    Used for `<br/>` elements, it's only special behavior is to add whitespace such that phrasing
    butted up tight on both sides of the `<br/>` element is not joined, like `abc<br/>def` should
    become "abc def", not "abcdef".
    """

    def it_adds_a_newline_in_its_place(self):
        cite = etree.fromstring(
            "<cite>spaceships of the<br/>Vogon Constructor Fleet</cite>", html_parser
        ).xpath(".//cite")[0]

        text_segments = cite.iter_text_segments()

        texts = [ts.text for ts in text_segments]
        assert texts == ["spaceships of the", "\n", "Vogon Constructor Fleet"]
        assert _normalize_text("".join(texts)) == "spaceships of the Vogon Constructor Fleet"


class DescribeRemovedPhrasing:
    """Isolated unit-test suite for `unstructured.partition.html.parser.RemovedPhrasing`.

    Used for phrasing elements like `<label>` that we want to skip, including any content they
    enclose. The tail of such an element is not skipped though.
    """

    def it_behaves_like_an_empty_element(self):
        label = etree.fromstring(
            "<div>\n"
            "  <label>Space<p>is big</p>, <b>mind-bogglingly</b> big.</label>\n"
            "  Like vastly, hugely big.\n"
            "</div>",
            html_parser,
        ).xpath(".//label")[0]

        (text_segment,) = list(label.iter_text_segments())

        assert isinstance(label, RemovedPhrasing)
        assert label.is_phrasing is True
        assert text_segment.text == "\n  Like vastly, hugely big.\n"


# -- DEFAULT ELEMENT -----------------------------------------------------------------------------


class DescribeDefaultElement:
    """Isolated unit-test suite for `unstructured.partition.html.parser.DefaultElement`.

    Used for any element we haven't assigned a custom element-class too. This prominently includes
    any non-HTML elements that can be embedded in the HTML.

    It identifies as a block item but it can behave as either a block-item or phrasing. Its behavior
    is a combination of RemovedBlock and RemovedPhrasing. Namely, it iterates zero elements and only
    iterates a text-segment for its tail.
    """

    # -- .is_phrasing -----------------------------------------------------

    def it_identifies_as_a_phrasing_element(self):
        foobar = etree.fromstring("<foobar>Vogon</foobar>", html_parser).xpath(".//foobar")[0]

        assert isinstance(foobar, DefaultElement)
        assert foobar.is_phrasing is True

    # -- .iter_elements() -------------------------------------------------

    def it_generates_zero_elements_as_a_block_item(self):
        """Should never be called but belts and suspenders."""
        foobar = etree.fromstring(
            "<foobar>Space<p>is big</p>, <b>mind-bogglingly</b> big.</foobar>",
            html_parser,
        ).xpath(".//foobar")[0]

        elements = foobar.iter_elements()

        with pytest.raises(StopIteration):
            next(elements)

    # -- .iter_text_segments() --------------------------------------------

    def it_generates_its_tail_but_no_inner_text_segments_when_called_like_phrasing(self):
        foobar = etree.fromstring(
            "<div>\n"
            "  O Deep Thought computer, he said,\n"
            "  <foobar>Vogon Constructor Fleet</foobar>\n"
            "  The task we have designed you to perform is this.\n"
            "  <p>We want you to tell us.... he paused,</p>\n"
            "</div>",
            html_parser,
        ).xpath(".//foobar")[0]

        texts = [ts.text for ts in foobar.iter_text_segments()]

        assert texts == ["\n  The task we have designed you to perform is this.\n  "]

    def and_it_behaves_like_an_empty_phrasing_element_inside_a_block_element(self):
        div = etree.fromstring(
            "<div>\n"
            "  O Deep Thought computer, he said,\n"
            "  <foobar>Vogon Constructor Fleet</foobar>\n"
            "  The task we have designed you to perform is this.\n"
            "  <p>We want you to tell us.... he paused,</p>\n"
            "</div>",
            html_parser,
        ).xpath(".//div")[0]

        texts = [e.text for e in div.iter_elements()]

        assert texts == [
            "O Deep Thought computer, he said, The task we have designed you to perform is this.",
            "We want you to tell us.... he paused,",
        ]
