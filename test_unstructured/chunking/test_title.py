# pyright: reportPrivateUsage=false

from typing import List

import pytest

from unstructured.chunking.title import (
    _NonTextSection,
    _SectionCombiner,
    _split_elements_by_title_and_table,
    _TableSection,
    _TextSection,
    _TextSectionAccumulator,
    _TextSectionBuilder,
    chunk_by_title,
)
from unstructured.documents.coordinates import CoordinateSystem
from unstructured.documents.elements import (
    CheckBox,
    CompositeElement,
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ListItem,
    PageBreak,
    RegexMetadata,
    Table,
    Text,
    Title,
)
from unstructured.partition.html import partition_html

# == chunk_by_title() validation behaviors =======================================================


@pytest.mark.parametrize("max_characters", [0, -1, -42])
def test_it_rejects_max_characters_not_greater_than_zero(max_characters: int):
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    with pytest.raises(
        ValueError,
        match=f"'max_characters' argument must be > 0, got {max_characters}",
    ):
        chunk_by_title(elements, max_characters=max_characters)


def test_it_does_not_complain_when_specifying_max_characters_by_itself():
    """Caller can specify `max_characters` arg without specifying any others.

    In particular, When `combine_text_under_n_chars` is not specified it defaults to the value of
    `max_characters`; it has no fixed default value that can be greater than `max_characters` and
    trigger an exception.
    """
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    try:
        chunk_by_title(elements, max_characters=50)
    except ValueError:
        pytest.fail("did not accept `max_characters` as option by itself")


@pytest.mark.parametrize("n_chars", [-1, -42])
def test_it_rejects_combine_text_under_n_chars_for_n_less_than_zero(n_chars: int):
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    with pytest.raises(
        ValueError,
        match=f"'combine_text_under_n_chars' argument must be >= 0, got {n_chars}",
    ):
        chunk_by_title(elements, combine_text_under_n_chars=n_chars)


def test_it_accepts_0_for_combine_text_under_n_chars_to_disable_chunk_combining():
    """Specifying `combine_text_under_n_chars=0` is how a caller disables chunk-combining."""
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    chunks = chunk_by_title(elements, max_characters=50, combine_text_under_n_chars=0)

    assert chunks == [CompositeElement("Lorem ipsum dolor.")]


def test_it_does_not_complain_when_specifying_combine_text_under_n_chars_by_itself():
    """Caller can specify `combine_text_under_n_chars` arg without specifying any other options."""
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    try:
        chunk_by_title(elements, combine_text_under_n_chars=50)
    except ValueError:
        pytest.fail("did not accept `combine_text_under_n_chars` as option by itself")


def test_it_silently_accepts_combine_text_under_n_chars_greater_than_maxchars():
    """`combine_text_under_n_chars` > `max_characters` doesn't affect chunking behavior.

    So rather than raising an exception or warning, we just cap that value at `max_characters` which
    is the behavioral equivalent.
    """
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    try:
        chunk_by_title(elements, max_characters=500, combine_text_under_n_chars=600)
    except ValueError:
        pytest.fail("did not accept `new_after_n_chars` greater than `max_characters`")


@pytest.mark.parametrize("n_chars", [-1, -42])
def test_it_rejects_new_after_n_chars_for_n_less_than_zero(n_chars: int):
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    with pytest.raises(
        ValueError,
        match=f"'new_after_n_chars' argument must be >= 0, got {n_chars}",
    ):
        chunk_by_title(elements, new_after_n_chars=n_chars)


def test_it_does_not_complain_when_specifying_new_after_n_chars_by_itself():
    """Caller can specify `new_after_n_chars` arg without specifying any other options.

    In particular, `combine_text_under_n_chars` value is adjusted down to the `new_after_n_chars`
    value when the default for `combine_text_under_n_chars` exceeds the value of
    `new_after_n_chars`.
    """
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    try:
        chunk_by_title(elements, new_after_n_chars=50)
    except ValueError:
        pytest.fail("did not accept `new_after_n_chars` as option by itself")


def test_it_accepts_0_for_new_after_n_chars_to_put_each_element_into_its_own_chunk():
    """Specifying `new_after_n_chars=0` places each element into its own section.

    This puts each element into its own chunk, although long chunks are still split.
    """
    elements: List[Element] = [
        Text("Lorem"),
        Text("ipsum"),
        Text("dolor"),
    ]

    chunks = chunk_by_title(elements, max_characters=50, new_after_n_chars=0)

    assert chunks == [
        CompositeElement("Lorem"),
        CompositeElement("ipsum"),
        CompositeElement("dolor"),
    ]


def test_it_silently_accepts_new_after_n_chars_greater_than_maxchars():
    """`new_after_n_chars` > `max_characters` doesn't affect chunking behavior.

    So rather than raising an exception or warning, we just cap that value at `max_characters` which
    is the behavioral equivalent.
    """
    elements: List[Element] = [Text("Lorem ipsum dolor.")]

    try:
        chunk_by_title(elements, max_characters=500, new_after_n_chars=600)
    except ValueError:
        pytest.fail("did not accept `new_after_n_chars` greater than `max_characters`")


# ================================================================================================


def test_it_splits_a_large_section_into_multiple_chunks():
    elements: List[Element] = [
        Title("Introduction"),
        Text(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed lectus"
            " porta volutpat.",
        ),
    ]

    chunks = chunk_by_title(elements, max_characters=50)

    assert chunks == [
        CompositeElement("Introduction"),
        CompositeElement("Lorem ipsum dolor sit amet consectetur adipiscing "),
        CompositeElement("elit. In rhoncus ipsum sed lectus porta volutpat."),
    ]


def test_split_elements_by_title_and_table():
    elements: List[Element] = [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]

    sections = _split_elements_by_title_and_table(
        elements,
        multipage_sections=True,
        new_after_n_chars=500,
        max_characters=500,
    )

    section = next(sections)
    assert isinstance(section, _TextSection)
    assert section._elements == [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
    ]
    # --
    section = next(sections)
    assert isinstance(section, _TableSection)
    assert section.table == Table("<table></table>")
    # ==
    section = next(sections)
    assert isinstance(section, _TextSection)
    assert section._elements == [
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
    ]
    # --
    section = next(sections)
    assert isinstance(section, _TextSection)
    assert section._elements == [
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
    ]
    # --
    section = next(sections)
    assert isinstance(section, _NonTextSection)
    assert section.element == CheckBox()
    # --
    with pytest.raises(StopIteration):
        next(sections)


def test_chunk_by_title():
    elements: List[Element] = [
        Title("A Great Day", metadata=ElementMetadata(emphasized_text_contents=["Day"])),
        Text("Today is a great day.", metadata=ElementMetadata(emphasized_text_contents=["day"])),
        Text("It is sunny outside."),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text(
            "Today is a bad day.",
            metadata=ElementMetadata(
                regex_metadata={"a": [RegexMetadata(text="A", start=0, end=1)]},
            ),
        ),
        Text("It is storming outside."),
        CheckBox(),
    ]

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day\n\nToday is a great day.\n\nIt is sunny outside.",
        ),
        Table("<table></table>"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
        CheckBox(),
    ]
    assert chunks[0].metadata == ElementMetadata(emphasized_text_contents=["Day", "day"])
    assert chunks[3].metadata == ElementMetadata(
        regex_metadata={"a": [RegexMetadata(text="A", start=11, end=12)]},
    )


def test_chunk_by_title_respects_section_change():
    elements: List[Element] = [
        Title("A Great Day", metadata=ElementMetadata(section="first")),
        Text("Today is a great day.", metadata=ElementMetadata(section="second")),
        Text("It is sunny outside.", metadata=ElementMetadata(section="second")),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text(
            "Today is a bad day.",
            metadata=ElementMetadata(
                regex_metadata={"a": [RegexMetadata(text="A", start=0, end=1)]},
            ),
        ),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day",
        ),
        CompositeElement(
            "Today is a great day.\n\nIt is sunny outside.",
        ),
        Table("<table></table>"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
        CheckBox(),
    ]


def test_chunk_by_title_separates_by_page_number():
    elements: List[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text(
            "Today is a bad day.",
            metadata=ElementMetadata(
                regex_metadata={"a": [RegexMetadata(text="A", start=0, end=1)]},
            ),
        ),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, multipage_sections=False, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day",
        ),
        CompositeElement(
            "Today is a great day.\n\nIt is sunny outside.",
        ),
        Table("<table></table>"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
        CheckBox(),
    ]


def test_chunk_by_title_does_not_break_on_regex_metadata_change():
    """Sectioner is insensitive to regex-metadata changes.

    A regex-metadata match in an element does not signify a semantic boundary and a section should
    not be split based on such a difference.
    """
    elements: List[Element] = [
        Title(
            "Lorem Ipsum",
            metadata=ElementMetadata(
                regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
            ),
        ),
        Text(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit.",
            metadata=ElementMetadata(
                regex_metadata={"dolor": [RegexMetadata(text="dolor", start=12, end=17)]},
            ),
        ),
        Text(
            "In rhoncus ipsum sed lectus porta volutpat.",
            metadata=ElementMetadata(
                regex_metadata={"ipsum": [RegexMetadata(text="ipsum", start=11, end=16)]},
            ),
        ),
    ]

    chunks = chunk_by_title(elements)

    assert chunks == [
        CompositeElement(
            "Lorem Ipsum\n\nLorem ipsum dolor sit amet consectetur adipiscing elit.\n\nIn rhoncus"
            " ipsum sed lectus porta volutpat.",
        ),
    ]


def test_chunk_by_title_consolidates_and_adjusts_offsets_of_regex_metadata():
    """ElementMetadata.regex_metadata of chunk is union of regex_metadatas of its elements.

    The `start` and `end` offsets of each regex-match are adjusted to reflect their new position in
    the chunk after element text has been concatenated.
    """
    elements: List[Element] = [
        Title(
            "Lorem Ipsum",
            metadata=ElementMetadata(
                regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
            ),
        ),
        Text(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit.",
            metadata=ElementMetadata(
                regex_metadata={
                    "dolor": [RegexMetadata(text="dolor", start=12, end=17)],
                    "ipsum": [RegexMetadata(text="ipsum", start=6, end=11)],
                },
            ),
        ),
        Text(
            "In rhoncus ipsum sed lectus porta volutpat.",
            metadata=ElementMetadata(
                regex_metadata={"ipsum": [RegexMetadata(text="ipsum", start=11, end=16)]},
            ),
        ),
    ]
    chunks = chunk_by_title(elements)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk == CompositeElement(
        "Lorem Ipsum\n\nLorem ipsum dolor sit amet consectetur adipiscing elit.\n\nIn rhoncus"
        " ipsum sed lectus porta volutpat.",
    )
    assert chunk.metadata.regex_metadata == {
        "dolor": [RegexMetadata(text="dolor", start=25, end=30)],
        "ipsum": [
            RegexMetadata(text="Ipsum", start=6, end=11),
            RegexMetadata(text="ipsum", start=19, end=24),
            RegexMetadata(text="ipsum", start=81, end=86),
        ],
    }


def test_chunk_by_title_groups_across_pages():
    elements: List[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text(
            "Today is a bad day.",
            metadata=ElementMetadata(
                regex_metadata={"a": [RegexMetadata(text="A", start=0, end=1)]},
            ),
        ),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, multipage_sections=True, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day\n\nToday is a great day.\n\nIt is sunny outside.",
        ),
        Table("<table></table>"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
        CheckBox(),
    ]


def test_add_chunking_strategy_on_partition_html():
    filename = "example-docs/example-10k-1p.html"
    chunk_elements = partition_html(filename, chunking_strategy="by_title")
    elements = partition_html(filename)
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_respects_max_characters():
    filename = "example-docs/example-10k-1p.html"
    chunk_elements = partition_html(
        filename,
        chunking_strategy="by_title",
        combine_text_under_n_chars=0,
        new_after_n_chars=50,
        max_characters=100,
    )
    elements = partition_html(filename)
    chunks = chunk_by_title(
        elements,
        combine_text_under_n_chars=0,
        new_after_n_chars=50,
        max_characters=100,
    )

    for chunk in chunks:
        assert isinstance(chunk, Text)
        assert len(chunk.text) <= 100
    for chunk_element in chunk_elements:
        assert isinstance(chunk_element, Text)
        assert len(chunk_element.text) <= 100
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_html_respects_multipage():
    filename = "example-docs/example-10k-1p.html"
    partitioned_elements_multipage_false_combine_chars_0 = partition_html(
        filename,
        chunking_strategy="by_title",
        multipage_sections=False,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    partitioned_elements_multipage_true_combine_chars_0 = partition_html(
        filename,
        chunking_strategy="by_title",
        multipage_sections=True,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    elements = partition_html(filename)
    cleaned_elements_multipage_false_combine_chars_0 = chunk_by_title(
        elements,
        multipage_sections=False,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    cleaned_elements_multipage_true_combine_chars_0 = chunk_by_title(
        elements,
        multipage_sections=True,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    assert (
        partitioned_elements_multipage_false_combine_chars_0
        == cleaned_elements_multipage_false_combine_chars_0
    )
    assert (
        partitioned_elements_multipage_true_combine_chars_0
        == cleaned_elements_multipage_true_combine_chars_0
    )
    assert len(partitioned_elements_multipage_true_combine_chars_0) != len(
        partitioned_elements_multipage_false_combine_chars_0,
    )


def test_chunk_by_title_drops_detection_class_prob():
    elements: List[Element] = [
        Title(
            "A Great Day",
            metadata=ElementMetadata(
                detection_class_prob=0.5,
            ),
        ),
        Text(
            "Today is a great day.",
            metadata=ElementMetadata(
                detection_class_prob=0.62,
            ),
        ),
        Text(
            "It is sunny outside.",
            metadata=ElementMetadata(
                detection_class_prob=0.73,
            ),
        ),
        Title(
            "An Okay Day",
            metadata=ElementMetadata(
                detection_class_prob=0.84,
            ),
        ),
        Text(
            "Today is an okay day.",
            metadata=ElementMetadata(
                detection_class_prob=0.95,
            ),
        ),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)
    assert str(chunks[0]) == str(
        CompositeElement("A Great Day\n\nToday is a great day.\n\nIt is sunny outside."),
    )
    assert str(chunks[1]) == str(CompositeElement("An Okay Day\n\nToday is an okay day."))


def test_chunk_by_title_drops_extra_metadata():
    elements: List[Element] = [
        Title(
            "A Great Day",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.1, 0.1),
                        (0.2, 0.1),
                        (0.1, 0.2),
                        (0.2, 0.2),
                    ),
                    system=CoordinateSystem(width=0.1, height=0.1),
                ),
            ),
        ),
        Text(
            "Today is a great day.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.2, 0.2),
                        (0.3, 0.2),
                        (0.2, 0.3),
                        (0.3, 0.3),
                    ),
                    system=CoordinateSystem(width=0.2, height=0.2),
                ),
            ),
        ),
        Text(
            "It is sunny outside.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.3, 0.3),
                        (0.4, 0.3),
                        (0.3, 0.4),
                        (0.4, 0.4),
                    ),
                    system=CoordinateSystem(width=0.3, height=0.3),
                ),
            ),
        ),
        Title(
            "An Okay Day",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.3, 0.3),
                        (0.4, 0.3),
                        (0.3, 0.4),
                        (0.4, 0.4),
                    ),
                    system=CoordinateSystem(width=0.3, height=0.3),
                ),
            ),
        ),
        Text(
            "Today is an okay day.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.4, 0.4),
                        (0.5, 0.4),
                        (0.4, 0.5),
                        (0.5, 0.5),
                    ),
                    system=CoordinateSystem(width=0.4, height=0.4),
                ),
            ),
        ),
    ]

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert str(chunks[0]) == str(
        CompositeElement("A Great Day\n\nToday is a great day.\n\nIt is sunny outside."),
    )

    assert str(chunks[1]) == str(CompositeElement("An Okay Day\n\nToday is an okay day."))


def test_it_considers_separator_length_when_sectioning():
    """Sectioner includes length of separators when computing remaining space."""
    elements: List[Element] = [
        Title("Chunking Priorities"),  # 19 chars
        ListItem("Divide text into manageable chunks"),  # 34 chars
        ListItem("Preserve semantic boundaries"),  # 28 chars
        ListItem("Minimize mid-text chunk-splitting"),  # 33 chars
    ]  # 114 chars total but 120 chars with separators

    chunks = chunk_by_title(elements, max_characters=115)

    assert chunks == [
        CompositeElement(
            "Chunking Priorities"
            "\n\nDivide text into manageable chunks"
            "\n\nPreserve semantic boundaries",
        ),
        CompositeElement("Minimize mid-text chunk-splitting"),
    ]


# == Sections ====================================================================================


class Describe_NonTextSection:
    """Unit-test suite for `unstructured.chunking.title._NonTextSection objects."""

    def it_provides_access_to_its_element(self):
        checkbox = CheckBox()
        section = _NonTextSection(checkbox)
        assert section.element is checkbox


class Describe_TableSection:
    """Unit-test suite for `unstructured.chunking.title._TableSection objects."""

    def it_provides_access_to_its_table(self):
        table = Table("<table></table>")
        section = _TableSection(table)
        assert section.table is table


class Describe_TextSection:
    """Unit-test suite for `unstructured.chunking.title._TextSection objects."""

    def it_can_combine_itself_with_another_TextSection_instance(self):
        """.combine() produces a new section by appending the elements of `other_section`.

        Note that neither the original or other section are mutated.
        """
        section = _TextSection(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ]
        )
        other_section = _TextSection(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ]
        )

        new_section = section.combine(other_section)

        assert new_section == _TextSection(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ]
        )
        assert section == _TextSection(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ]
        )
        assert other_section == _TextSection(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ]
        )

    @pytest.mark.parametrize(
        ("elements", "expected_value"),
        [
            ([Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), PageBreak(""), Text("bar")], "foo\n\nbar"),
            ([PageBreak(""), Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), Text("bar"), PageBreak("")], "foo\n\nbar"),
        ],
    )
    def it_provides_access_to_the_concatenated_text_of_the_section(
        self, elements: List[Text], expected_value: str
    ):
        """.text is the "joined" text of the section elements.

        The text-segment contributed by each element is separated from the next by a blank line
        ("\n\n"). An element that contributes no text does not give rise to a separator.
        """
        section = _TextSection(elements)
        assert section.text == expected_value

    def it_knows_the_length_of_the_combined_text_of_its_elements_which_is_the_chunk_size(self):
        """.text_length is the size of chunk this section will produce (before any splitting)."""
        section = _TextSection([PageBreak(""), Text("foo"), Text("bar")])
        assert section.text_length == 8

    def it_extracts_all_populated_metadata_values_from_the_elements_to_help(self):
        section = _TextSection(
            [
                Title(
                    "Lorem Ipsum",
                    metadata=ElementMetadata(
                        category_depth=0,
                        filename="foo.docx",
                        languages=["lat"],
                        parent_id="f87731e0",
                    ),
                ),
                Text(
                    "'Lorem ipsum dolor' means 'Thank you very much' in Latin.",
                    metadata=ElementMetadata(
                        category_depth=1,
                        filename="foo.docx",
                        image_path="sprite.png",
                        languages=["lat", "eng"],
                    ),
                ),
            ]
        )

        assert section._all_metadata_values == {
            # -- scalar values are accumulated in a list in element order --
            "category_depth": [0, 1],
            # -- all values are accumulated, not only unique ones --
            "filename": ["foo.docx", "foo.docx"],
            # -- list-type fields produce a list of lists --
            "languages": [["lat"], ["lat", "eng"]],
            # -- fields that only appear in some elements are captured --
            "image_path": ["sprite.png"],
            "parent_id": ["f87731e0"],
            # -- A `None` value never appears, neither does a field-name with an empty list --
        }

    def but_it_discards_ad_hoc_metadata_fields_during_consolidation(self):
        metadata = ElementMetadata(
            category_depth=0,
            filename="foo.docx",
            languages=["lat"],
            parent_id="f87731e0",
        )
        metadata.coefficient = 0.62
        metadata_2 = ElementMetadata(
            category_depth=1,
            filename="foo.docx",
            image_path="sprite.png",
            languages=["lat", "eng"],
        )
        metadata_2.quotient = 1.74

        section = _TextSection(
            [
                Title("Lorem Ipsum", metadata=metadata),
                Text("'Lorem ipsum dolor' means 'Thank you very much'.", metadata=metadata_2),
            ]
        )

        # -- ad-hoc fields "coefficient" and "quotient" do not appear --
        assert section._all_metadata_values == {
            "category_depth": [0, 1],
            "filename": ["foo.docx", "foo.docx"],
            "image_path": ["sprite.png"],
            "languages": [["lat"], ["lat", "eng"]],
            "parent_id": ["f87731e0"],
        }

    def it_consolidates_regex_metadata_in_a_field_specific_way(self):
        """regex_metadata of chunk is combined regex_metadatas of its elements.

        Also, the `start` and `end` offsets of each regex-match are adjusted to reflect their new
        position in the chunk after element text has been concatenated.
        """
        section = _TextSection(
            [
                Title(
                    "Lorem Ipsum",
                    metadata=ElementMetadata(
                        regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
                    ),
                ),
                Text(
                    "Lorem ipsum dolor sit amet consectetur adipiscing elit.",
                    metadata=ElementMetadata(
                        regex_metadata={
                            "dolor": [RegexMetadata(text="dolor", start=12, end=17)],
                            "ipsum": [RegexMetadata(text="ipsum", start=6, end=11)],
                        },
                    ),
                ),
                Text(
                    "In rhoncus ipsum sed lectus porta volutpat.",
                    metadata=ElementMetadata(
                        regex_metadata={"ipsum": [RegexMetadata(text="ipsum", start=11, end=16)]},
                    ),
                ),
            ]
        )

        regex_metadata = section._consolidated_regex_meta

        assert regex_metadata == {
            "dolor": [RegexMetadata(text="dolor", start=25, end=30)],
            "ipsum": [
                RegexMetadata(text="Ipsum", start=6, end=11),
                RegexMetadata(text="ipsum", start=19, end=24),
                RegexMetadata(text="ipsum", start=81, end=86),
            ],
        }

    def it_forms_ElementMetadata_constructor_kwargs_by_applying_consolidation_strategies(self):
        """._meta_kwargs is used like `ElementMetadata(**self._meta_kwargs)` to construct metadata.

        Only non-None fields should appear in the dict and each field value should be the
        consolidation of the values across the section elements.
        """
        section = _TextSection(
            [
                PageBreak(""),
                Title(
                    "Lorem Ipsum",
                    metadata=ElementMetadata(
                        filename="foo.docx",
                        # -- category_depth has DROP strategy so doesn't appear in result --
                        category_depth=0,
                        emphasized_text_contents=["Lorem", "Ipsum"],
                        emphasized_text_tags=["b", "i"],
                        languages=["lat"],
                        regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
                    ),
                ),
                Text(
                    "'Lorem ipsum dolor' means 'Thank you very much' in Latin.",
                    metadata=ElementMetadata(
                        # -- filename change doesn't happen IRL but demonstrates FIRST strategy --
                        filename="bar.docx",
                        # -- emphasized_text_contents has LIST_CONCATENATE strategy, so "Lorem"
                        # -- appears twice in consolidated-meta (as it should) and length matches
                        # -- that of emphasized_text_tags both before and after consolidation.
                        emphasized_text_contents=["Lorem", "ipsum"],
                        emphasized_text_tags=["i", "b"],
                        # -- languages has LIST_UNIQUE strategy, so "lat(in)" appears only once --
                        languages=["eng", "lat"],
                        # -- regex_metadata has its own dedicated consolidation-strategy (REGEX) --
                        regex_metadata={
                            "dolor": [RegexMetadata(text="dolor", start=12, end=17)],
                            "ipsum": [RegexMetadata(text="ipsum", start=6, end=11)],
                        },
                    ),
                ),
            ]
        )

        meta_kwargs = section._meta_kwargs

        assert meta_kwargs == {
            "filename": "foo.docx",
            "emphasized_text_contents": ["Lorem", "Ipsum", "Lorem", "ipsum"],
            "emphasized_text_tags": ["b", "i", "i", "b"],
            "languages": ["lat", "eng"],
            "regex_metadata": {
                "ipsum": [
                    RegexMetadata(text="Ipsum", start=6, end=11),
                    RegexMetadata(text="ipsum", start=19, end=24),
                ],
                "dolor": [RegexMetadata(text="dolor", start=25, end=30)],
            },
        }


class Describe_TextSectionBuilder:
    """Unit-test suite for `unstructured.chunking.title._TextSectionBuilder`."""

    def it_is_empty_on_construction(self):
        builder = _TextSectionBuilder(maxlen=50)

        assert builder.text_length == 0
        assert builder.remaining_space == 50

    def it_accumulates_elements_added_to_it(self):
        builder = _TextSectionBuilder(maxlen=150)

        builder.add_element(Title("Introduction"))
        assert builder.text_length == 12
        assert builder.remaining_space == 136

        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )
        assert builder.text_length == 112
        assert builder.remaining_space == 36

    def it_generates_a_TextSection_when_flushed_and_resets_itself_to_empty(self):
        builder = _TextSectionBuilder(maxlen=150)
        builder.add_element(Title("Introduction"))
        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )

        section = next(builder.flush())

        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        ]
        assert builder.text_length == 0
        assert builder.remaining_space == 150

    def but_it_does_not_generate_a_TextSection_on_flush_when_empty(self):
        builder = _TextSectionBuilder(maxlen=150)

        sections = list(builder.flush())

        assert sections == []
        assert builder.text_length == 0
        assert builder.remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        builder = _TextSectionBuilder(maxlen=50)
        builder.add_element(Text("abcde"))
        builder.add_element(Text("fghij"))

        # -- .text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert builder.text_length == 12
        # -- .remaining_space is reduced by the length (2) of the trailing separator which would go
        # -- between the current text and that of the next element if one was added.
        # -- So 50 - 12 - 2 = 36 here, not 50 - 12 = 38
        assert builder.remaining_space == 36


# == SectionCombiner =============================================================================


class Describe_SectionCombiner:
    """Unit-test suite for `unstructured.chunking.title._SectionCombiner`."""

    def it_combines_sequential_small_text_sections(self):
        sections = [
            _TextSection(
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ]
            ),
            _TextSection(
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ]
            ),
            _TextSection(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ]
            ),
        ]

        section_iter = _SectionCombiner(
            sections, maxlen=250, combine_text_under_n_chars=250
        ).iter_combined_sections()

        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        with pytest.raises(StopIteration):
            next(section_iter)

    def but_it_does_not_combine_table_or_non_text_sections(self):
        sections = [
            _TextSection(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ]
            ),
            _TableSection(Table("<table></table>")),
            _TextSection(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ]
            ),
            _NonTextSection(CheckBox()),
            _TextSection(
                [
                    Title("Sed Orci"),
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
                ]
            ),
        ]

        section_iter = _SectionCombiner(
            sections, maxlen=250, combine_text_under_n_chars=250
        ).iter_combined_sections()

        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
        ]
        # --
        section = next(section_iter)
        assert isinstance(section, _TableSection)
        assert section.table == Table("<table></table>")
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        section = next(section_iter)
        assert isinstance(section, _NonTextSection)
        assert section.element == CheckBox()
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(section_iter)

    def it_respects_the_specified_combination_threshold(self):
        sections = [
            _TextSection(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ]
            ),
            _TextSection(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ]
            ),
            # -- len == 139
            _TextSection(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ]
            ),
        ]

        section_iter = _SectionCombiner(
            sections, maxlen=250, combine_text_under_n_chars=80
        ).iter_combined_sections()

        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(section_iter)

    def it_respects_the_hard_maximum_window_length(self):
        sections = [
            _TextSection(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ]
            ),
            _TextSection(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ]
            ),
            # -- len == 139
            _TextSection(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ]
            ),
            # -- len == 214
        ]

        section_iter = _SectionCombiner(
            sections, maxlen=200, combine_text_under_n_chars=200
        ).iter_combined_sections()

        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(section_iter)

    def it_accommodates_and_isolates_an_oversized_section(self):
        """Such as occurs when a single element exceeds the window size."""

        sections = [
            _TextSection([Title("Lorem Ipsum")]),
            _TextSection(  # 179
                [
                    Text(
                        "Lorem ipsum dolor sit amet consectetur adipiscing elit."  # 55
                        " Mauris nec urna non augue vulputate consequat eget et nisi."  # 60
                        " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."  # 64
                    )
                ]
            ),
            _TextSection([Title("Vulputate Consequat")]),
        ]

        section_iter = _SectionCombiner(
            sections, maxlen=150, combine_text_under_n_chars=150
        ).iter_combined_sections()

        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [Title("Lorem Ipsum")]
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit."
                " Mauris nec urna non augue vulputate consequat eget et nisi."
                " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."
            )
        ]
        # --
        section = next(section_iter)
        assert isinstance(section, _TextSection)
        assert section._elements == [Title("Vulputate Consequat")]
        # --
        with pytest.raises(StopIteration):
            next(section_iter)


class Describe_TextSectionAccumulator:
    """Unit-test suite for `unstructured.chunking.title._TextSectionAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = _TextSectionAccumulator(maxlen=100)

        assert accum.text_length == 0
        assert accum.remaining_space == 100

    def it_accumulates_sections_added_to_it(self):
        accum = _TextSectionAccumulator(maxlen=500)

        accum.add_section(
            _TextSection(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ]
            )
        )
        assert accum.text_length == 68
        assert accum.remaining_space == 430

        accum.add_section(
            _TextSection(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ]
            )
        )
        assert accum.text_length == 141
        assert accum.remaining_space == 357

    def it_generates_a_TextSection_when_flushed_and_resets_itself_to_empty(self):
        accum = _TextSectionAccumulator(maxlen=150)
        accum.add_section(
            _TextSection(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ]
            )
        )
        accum.add_section(
            _TextSection(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ]
            )
        )
        accum.add_section(
            _TextSection(
                [
                    Title("Sed Orci"),
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
                ]
            )
        )

        section_iter = accum.flush()

        # -- iterator generates exactly one section --
        section = next(section_iter)
        with pytest.raises(StopIteration):
            next(section_iter)
        # -- and it is a _TextSection containing all the elements --
        assert isinstance(section, _TextSection)
        assert section._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
        ]
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def but_it_does_not_generate_a_TextSection_on_flush_when_empty(self):
        accum = _TextSectionAccumulator(maxlen=150)

        sections = list(accum.flush())

        assert sections == []
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        accum = _TextSectionAccumulator(maxlen=100)
        accum.add_section(_TextSection([Text("abcde")]))
        accum.add_section(_TextSection([Text("fghij")]))

        # -- .text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert accum.text_length == 12
        # -- .remaining_space is reduced by the length (2) of the trailing separator which would
        # -- go between the current text and that of the next section if one was added.
        # -- So 100 - 12 - 2 = 86 here, not 100 - 12 = 88
        assert accum.remaining_space == 86
