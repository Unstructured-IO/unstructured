import pytest

from unstructured.chunking.title import (
    _split_elements_by_title_and_table,
    chunk_by_title,
)
from unstructured.documents.coordinates import CoordinateSystem
from unstructured.documents.elements import (
    CheckBox,
    CompositeElement,
    CoordinatesMetadata,
    ElementMetadata,
    Table,
    Text,
    Title,
)
from unstructured.partition.html import partition_html


def test_split_elements_by_title_and_table():
    elements = [
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
    sections = _split_elements_by_title_and_table(elements, combine_text_under_n_chars=0)

    assert sections == [
        [
            Title("A Great Day"),
            Text("Today is a great day."),
            Text("It is sunny outside."),
        ],
        [
            Table("<table></table>"),
        ],
        [
            Title("An Okay Day"),
            Text("Today is an okay day."),
            Text("It is rainy outside."),
        ],
        [
            Title("A Bad Day"),
            Text("Today is a bad day."),
            Text("It is storming outside."),
        ],
        [
            CheckBox(),
        ],
    ]


def test_chunk_by_title():
    elements = [
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
            metadata=ElementMetadata(regex_metadata=[{"text": "A", "start": 0, "end": 1}]),
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
        regex_metadata=[{"text": "A", "start": 11, "end": 12}],
    )


def test_chunk_by_title_respects_section_change():
    elements = [
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
            metadata=ElementMetadata(regex_metadata=[{"text": "A", "start": 0, "end": 1}]),
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
    elements = [
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
            metadata=ElementMetadata(regex_metadata=[{"text": "A", "start": 0, "end": 1}]),
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


def test_chunk_by_title_groups_across_pages():
    elements = [
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
            metadata=ElementMetadata(regex_metadata=[{"text": "A", "start": 0, "end": 1}]),
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
        assert len(chunk.text) <= 100
    for chunk_element in chunk_elements:
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


@pytest.mark.parametrize(
    ("combine_text_under_n_chars", "new_after_n_chars", "max_characters"),
    [
        (-1, -1, -1),  # invalid chunk size
        (0, 0, 0),  # invalid max_characters
        (-5666, -6777, -8999),  # invalid chunk size
        (-5, 40, 50),  # invalid chunk size
        (50, 70, 20),  # max_characters needs to be greater than new_after_n_chars
        (70, 50, 50),  # combine_text_under_n_chars needs to be les than new_after_n_chars
    ],
)
def test_add_chunking_strategy_raises_error_for_invalid_n_chars(
    combine_text_under_n_chars,
    new_after_n_chars,
    max_characters,
):
    elements = [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
        Table("<table></table>"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("It is storming outside."),
        CheckBox(),
    ]
    with pytest.raises(ValueError):
        chunk_by_title(
            elements,
            combine_text_under_n_chars=combine_text_under_n_chars,
            new_after_n_chars=new_after_n_chars,
            max_characters=max_characters,
        )


def test_chunk_by_title_drops_detection_class_prob():
    elements = [
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
    elements = [
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
