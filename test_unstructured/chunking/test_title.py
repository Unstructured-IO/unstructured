# pyright: reportPrivateUsage=false

from typing import List

import pytest

from unstructured.chunking.title import (
    _NonTextSection,
    _split_elements_by_title_and_table,
    _TableSection,
    _TextSection,
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
        combine_text_under_n_chars=0,
        new_after_n_chars=500,
        max_characters=500,
    )

    section = next(sections)
    assert isinstance(section, _TextSection)
    assert section.elements == [
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
    assert section.elements == [
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
    ]
    # --
    section = next(sections)
    assert isinstance(section, _TextSection)
    assert section.elements == [
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
            "\n\nPreserve semantic boundaries"
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

    def it_provides_access_to_its_elements(self):
        elements: List[Element] = [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        ]
        section = _TextSection(elements)
        assert section.elements == elements


class Describe_TextSectionBuilder:
    """Unit-test suite for `unstructured.chunking.title._TextSection objects."""

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
                "lectus porta volutpat."
            )
        )
        assert builder.text_length == 112
        assert builder.remaining_space == 36

    def it_generates_a_TextSection_when_flushed_and_resets_itself_to_empty(self):
        builder = _TextSectionBuilder(maxlen=150)
        builder.add_element(Title("Introduction"))
        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat."
            )
        )

        section = next(builder.flush())

        assert isinstance(section, _TextSection)
        assert section.elements == [
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
