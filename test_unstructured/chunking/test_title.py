# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.title` module."""

from __future__ import annotations

import pytest

from unstructured.chunking.base import ChunkingOptions, TablePreChunk, TextPreChunk
from unstructured.chunking.title import _ByTitlePreChunker, chunk_by_title
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


def test_it_splits_a_large_element_into_multiple_chunks():
    elements: list[Element] = [
        Title("Introduction"),
        Text(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed lectus"
            " porta volutpat.",
        ),
    ]

    chunks = chunk_by_title(elements, max_characters=50)

    assert chunks == [
        CompositeElement("Introduction"),
        CompositeElement("Lorem ipsum dolor sit amet consectetur adipiscing"),
        CompositeElement("elit. In rhoncus ipsum sed lectus porta volutpat."),
    ]


def test_split_elements_by_title_and_table():
    elements: list[Element] = [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]

    pre_chunks = _ByTitlePreChunker.iter_pre_chunks(elements, opts=ChunkingOptions.new())

    pre_chunk = next(pre_chunks)
    assert isinstance(pre_chunk, TextPreChunk)
    assert pre_chunk._elements == [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
    ]
    # --
    pre_chunk = next(pre_chunks)
    assert isinstance(pre_chunk, TablePreChunk)
    assert pre_chunk._table == Table("Heading\nCell text")
    # ==
    pre_chunk = next(pre_chunks)
    assert isinstance(pre_chunk, TextPreChunk)
    assert pre_chunk._elements == [
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
    ]
    # --
    pre_chunk = next(pre_chunks)
    assert isinstance(pre_chunk, TextPreChunk)
    assert pre_chunk._elements == [
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]
    # --
    with pytest.raises(StopIteration):
        next(pre_chunks)


def test_chunk_by_title():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(emphasized_text_contents=["Day"])),
        Text("Today is a great day.", metadata=ElementMetadata(emphasized_text_contents=["day"])),
        Text("It is sunny outside."),
        Table("Heading\nCell text"),
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
        Table("Heading\nCell text"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]
    assert chunks[0].metadata == ElementMetadata(emphasized_text_contents=["Day", "day"])
    assert chunks[3].metadata == ElementMetadata(
        regex_metadata={"a": [RegexMetadata(text="A", start=11, end=12)]},
    )


def test_chunk_by_title_respects_section_change():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(section="first")),
        Text("Today is a great day.", metadata=ElementMetadata(section="second")),
        Text("It is sunny outside.", metadata=ElementMetadata(section="second")),
        Table("Heading\nCell text"),
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
        Table("Heading\nCell text"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]


def test_chunk_by_title_separates_by_page_number():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("Heading\nCell text"),
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
        Table("Heading\nCell text"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]


def test_chunk_by_title_does_not_break_on_regex_metadata_change():
    """PreChunker is insensitive to regex-metadata changes.

    A regex-metadata match in an element does not signify a semantic boundary and a pre-chunk should
    not be split based on such a difference.
    """
    elements: list[Element] = [
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
    elements: list[Element] = [
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
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("Heading\nCell text"),
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
        Table("Heading\nCell text"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
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
    elements: list[Element] = [
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
    elements: list[Element] = [
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


def test_it_considers_separator_length_when_pre_chunking():
    """PreChunker includes length of separators when computing remaining space."""
    elements: list[Element] = [
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
