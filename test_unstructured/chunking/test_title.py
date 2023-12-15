# pyright: reportPrivateUsage=false

from typing import List

import pytest

from unstructured.chunking.base import ChunkingOptions
from unstructured.chunking.title import (
    PreChunkCombiner,
    TablePreChunk,
    TextPreChunk,
    TextPreChunkAccumulator,
    TextPreChunkBuilder,
    _split_elements_by_title_and_table,
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
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.html import partition_html


def test_it_splits_a_large_element_into_multiple_chunks():
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
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]

    pre_chunks = _split_elements_by_title_and_table(elements, opts=ChunkingOptions.new())

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
    elements: List[Element] = [
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
    elements: List[Element] = [
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
    elements: List[Element] = [
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


def test_it_considers_separator_length_when_pre_chunking():
    """PreChunker includes length of separators when computing remaining space."""
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


# == PreChunks ===================================================================================


class DescribeTablePreChunk:
    """Unit-test suite for `unstructured.chunking.title.TablePreChunk objects."""

    def it_uses_its_table_as_the_sole_chunk_when_it_fits_in_the_window(self):
        html_table = (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1 </th><th>Header Col 2 </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lorem ipsum  </td><td>adipiscing   </td></tr>\n"
            "</tbody>\n"
            "</table>"
        )
        text_table = "Header Col 1  Header Col 2\n" "Lorem ipsum   adipiscing"
        pre_chunk = TablePreChunk(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            opts=ChunkingOptions.new(max_characters=175),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert isinstance(chunk, Table)
        assert chunk.text == "Header Col 1  Header Col 2\nLorem ipsum   adipiscing"
        assert chunk.metadata.text_as_html == (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1 </th><th>Header Col 2 </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lorem ipsum  </td><td>adipiscing   </td></tr>\n"
            "</tbody>\n"
            "</table>"
        )
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def but_it_splits_its_table_into_TableChunks_when_the_table_text_exceeds_the_window(self):
        # fixed-overhead = 8+8+9+8+9+8 = 50
        # per-row overhead = 27
        html_table = (
            "<table>\n"  # 8
            "<thead>\n"  # 8
            "<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>\n"
            "</thead>\n"  # 9
            "<tbody>\n"  # 8
            "<tr><td>Lorem ipsum    </td><td>A Link example</td></tr>\n"
            "<tr><td>Consectetur    </td><td>adipiscing elit</td></tr>\n"
            "<tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>\n"
            "<tr><td>Vivamus quis   </td><td>nunc ipsum donec ac fermentum</td></tr>\n"
            "</tbody>\n"  # 9
            "</table>"  # 8
        )
        text_table = (
            "Header Col 1   Header Col 2\n"
            "Lorem ipsum    dolor sit amet\n"
            "Consectetur    adipiscing elit\n"
            "Nunc aliquam   id enim nec molestie\n"
            "Vivamus quis   nunc ipsum donec ac fermentum"
        )
        pre_chunk = TablePreChunk(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            opts=ChunkingOptions.new(max_characters=100),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == (
            "Header Col 1   Header Col 2\n"
            "Lorem ipsum    dolor sit amet\n"
            "Consectetur    adipiscing elit\n"
            "Nunc aliqua"
        )
        assert chunk.metadata.text_as_html == (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lo"
        )
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert (
            chunk.text == "m   id enim nec molestie\nVivamus quis   nunc ipsum donec ac fermentum"
        )
        assert chunk.metadata.text_as_html == (
            "rem ipsum    </td><td>A Link example</td></tr>\n"
            "<tr><td>Consectetur    </td><td>adipiscing elit</td><"
        )
        # -- note that text runs out but HTML continues because it's significantly longer. So two
        # -- of these chunks have HTML but no text.
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == ""
        assert chunk.metadata.text_as_html == (
            "/tr>\n"
            "<tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>\n"
            "<tr><td>Vivamus quis   </td><td>"
        )
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == ""
        assert chunk.metadata.text_as_html == (
            "nunc ipsum donec ac fermentum</td></tr>\n</tbody>\n</table>"
        )
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)


class DescribeTextPreChunk:
    """Unit-test suite for `unstructured.chunking.title.TextPreChunk objects."""

    def it_can_combine_itself_with_another_TextPreChunk_instance(self):
        """.combine() produces a new pre-chunk by appending the elements of `other_pre-chunk`.

        Note that neither the original or other pre_chunk are mutated.
        """
        opts = ChunkingOptions.new()
        pre_chunk = TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            opts=opts,
        )
        other_pre_chunk = TextPreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )

        new_pre_chunk = pre_chunk.combine(other_pre_chunk)

        assert new_pre_chunk == TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )
        assert pre_chunk == TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            opts=opts,
        )
        assert other_pre_chunk == TextPreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )

    def it_generates_a_single_chunk_from_its_elements_if_they_together_fit_in_window(self):
        pre_chunk = TextPreChunk(
            [
                Title("Introduction"),
                Text(
                    "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                    "lectus porta volutpat.",
                ),
            ],
            opts=ChunkingOptions.new(max_characters=200),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "Introduction\n\nLorem ipsum dolor sit amet consectetur adipiscing elit."
            " In rhoncus ipsum sedlectus porta volutpat.",
        )
        assert chunk.metadata is pre_chunk._consolidated_metadata

    def but_it_generates_split_chunks_when_its_single_element_exceeds_window_size(self):
        # -- Chunk-splitting only occurs when a *single* element is too big to fit in the window.
        # -- The pre-chunker will isolate that element in a pre_chunk of its own.
        pre_chunk = TextPreChunk(
            [
                Text(
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod"
                    " tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim"
                    " veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea"
                    " commodo consequat."
                ),
            ],
            opts=ChunkingOptions.new(max_characters=200),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod"
            " tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim"
            " veniam, quis nostrud exercitation ullamco laboris nisi ut a"
        )
        assert chunk.metadata is pre_chunk._consolidated_metadata
        # --
        chunk = next(chunk_iter)
        assert chunk == CompositeElement("liquip ex ea commodo consequat.")
        assert chunk.metadata is pre_chunk._consolidated_metadata
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def it_knows_the_length_of_the_combined_text_of_its_elements_which_is_the_chunk_size(self):
        """.text_length is the size of chunk this pre-chunk will produce (before any splitting)."""
        pre_chunk = TextPreChunk(
            [PageBreak(""), Text("foo"), Text("bar")], opts=ChunkingOptions.new()
        )
        assert pre_chunk.text_length == 8

    def it_extracts_all_populated_metadata_values_from_the_elements_to_help(self):
        pre_chunk = TextPreChunk(
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
            ],
            opts=ChunkingOptions.new(),
        )

        assert pre_chunk._all_metadata_values == {
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

        pre_chunk = TextPreChunk(
            [
                Title("Lorem Ipsum", metadata=metadata),
                Text("'Lorem ipsum dolor' means 'Thank you very much'.", metadata=metadata_2),
            ],
            opts=ChunkingOptions.new(),
        )

        # -- ad-hoc fields "coefficient" and "quotient" do not appear --
        assert pre_chunk._all_metadata_values == {
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
        pre_chunk = TextPreChunk(
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
            ],
            opts=ChunkingOptions.new(),
        )

        regex_metadata = pre_chunk._consolidated_regex_meta

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
        consolidation of the values across the pre_chunk elements.
        """
        pre_chunk = TextPreChunk(
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
            ],
            opts=ChunkingOptions.new(),
        )

        meta_kwargs = pre_chunk._meta_kwargs

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

    @pytest.mark.parametrize(
        ("elements", "expected_value"),
        [
            ([Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), PageBreak(""), Text("bar")], "foo\n\nbar"),
            ([PageBreak(""), Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), Text("bar"), PageBreak("")], "foo\n\nbar"),
        ],
    )
    def it_knows_the_concatenated_text_of_the_pre_chunk(
        self, elements: List[Text], expected_value: str
    ):
        """._text is the "joined" text of the pre-chunk elements.

        The text-segment contributed by each element is separated from the next by a blank line
        ("\n\n"). An element that contributes no text does not give rise to a separator.
        """
        pre_chunk = TextPreChunk(elements, opts=ChunkingOptions.new())
        assert pre_chunk._text == expected_value


class DescribeTextPreChunkBuilder:
    """Unit-test suite for `unstructured.chunking.title.TextPreChunkBuilder`."""

    def it_is_empty_on_construction(self):
        builder = TextPreChunkBuilder(opts=ChunkingOptions.new(max_characters=50))

        assert builder.text_length == 0
        assert builder.remaining_space == 50

    def it_accumulates_elements_added_to_it(self):
        builder = TextPreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))

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

    def it_generates_a_TextPreChunk_when_flushed_and_resets_itself_to_empty(self):
        builder = TextPreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))
        builder.add_element(Title("Introduction"))
        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )

        pre_chunk = next(builder.flush())

        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        ]
        assert builder.text_length == 0
        assert builder.remaining_space == 150

    def but_it_does_not_generate_a_TextPreChunk_on_flush_when_empty(self):
        builder = TextPreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))

        pre_chunks = list(builder.flush())

        assert pre_chunks == []
        assert builder.text_length == 0
        assert builder.remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        builder = TextPreChunkBuilder(opts=ChunkingOptions.new(max_characters=50))
        builder.add_element(Text("abcde"))
        builder.add_element(Text("fghij"))

        # -- .text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert builder.text_length == 12
        # -- .remaining_space is reduced by the length (2) of the trailing separator which would go
        # -- between the current text and that of the next element if one was added.
        # -- So 50 - 12 - 2 = 36 here, not 50 - 12 = 38
        assert builder.remaining_space == 36


# == PreChunkCombiner =============================================================================


class DescribePreChunkCombiner:
    """Unit-test suite for `unstructured.chunking.title.PreChunkCombiner`."""

    def it_combines_sequential_small_text_pre_chunks(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        pre_chunks = [
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def but_it_does_not_combine_table_pre_chunks(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        pre_chunks = [
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            ),
            TablePreChunk(Table("Heading\nCell text"), opts=opts),
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(
            pre_chunks, ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        ).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TablePreChunk)
        assert pre_chunk._table == Table("Heading\nCell text")
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_specified_combination_threshold(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=80)
        pre_chunks = [
            TextPreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            # -- len == 139
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_hard_maximum_window_length(self):
        opts = ChunkingOptions.new(max_characters=200, combine_text_under_n_chars=200)
        pre_chunks = [
            TextPreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            # -- len == 139
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
            # -- len == 214
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_accommodates_and_isolates_an_oversized_pre_chunk(self):
        """Such as occurs when a single element exceeds the window size."""
        opts = ChunkingOptions.new(max_characters=150, combine_text_under_n_chars=150)
        pre_chunks = [
            TextPreChunk([Title("Lorem Ipsum")], opts=opts),
            TextPreChunk(  # 179
                [
                    Text(
                        "Lorem ipsum dolor sit amet consectetur adipiscing elit."  # 55
                        " Mauris nec urna non augue vulputate consequat eget et nisi."  # 60
                        " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."  # 64
                    )
                ],
                opts=opts,
            ),
            TextPreChunk([Title("Vulputate Consequat")], opts=opts),
        ]

        pre_chunk_iter = PreChunkCombiner(
            pre_chunks, ChunkingOptions.new(max_characters=150, combine_text_under_n_chars=150)
        ).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [Title("Lorem Ipsum")]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit."
                " Mauris nec urna non augue vulputate consequat eget et nisi."
                " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."
            )
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [Title("Vulputate Consequat")]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)


class DescribeTextPreChunkAccumulator:
    """Unit-test suite for `unstructured.chunking.title.TextPreChunkAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = TextPreChunkAccumulator(opts=ChunkingOptions.new(max_characters=100))

        assert accum.text_length == 0
        assert accum.remaining_space == 100

    def it_accumulates_pre_chunks_added_to_it(self):
        opts = ChunkingOptions.new(max_characters=500)
        accum = TextPreChunkAccumulator(opts=opts)

        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            )
        )
        assert accum.text_length == 68
        assert accum.remaining_space == 430

        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            )
        )
        assert accum.text_length == 141
        assert accum.remaining_space == 357

    def it_generates_a_TextPreChunk_when_flushed_and_resets_itself_to_empty(self):
        opts = ChunkingOptions.new(max_characters=150)
        accum = TextPreChunkAccumulator(opts=opts)
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            )
        )
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            )
        )
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Sed Orci"),
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
                ],
                opts=opts,
            )
        )

        pre_chunk_iter = accum.flush()

        # -- iterator generates exactly one pre_chunk --
        pre_chunk = next(pre_chunk_iter)
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)
        # -- and it is a _TextPreChunk containing all the elements --
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
        ]
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def but_it_does_not_generate_a_TextPreChunk_on_flush_when_empty(self):
        accum = TextPreChunkAccumulator(opts=ChunkingOptions.new(max_characters=150))

        pre_chunks = list(accum.flush())

        assert pre_chunks == []
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        opts = ChunkingOptions.new(max_characters=100)
        accum = TextPreChunkAccumulator(opts=opts)
        accum.add_pre_chunk(TextPreChunk([Text("abcde")], opts=opts))
        accum.add_pre_chunk(TextPreChunk([Text("fghij")], opts=opts))

        # -- .text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert accum.text_length == 12
        # -- .remaining_space is reduced by the length (2) of the trailing separator which would
        # -- go between the current text and that of the next pre-chunk if one was added.
        # -- So 100 - 12 - 2 = 86 here, not 100 - 12 = 88
        assert accum.remaining_space == 86
