from unstructured.chunking.title import (
    _split_elements_by_title_and_table,
    chunk_by_title,
)
from unstructured.documents.elements import (
    CheckBox,
    ElementMetadata,
    Section,
    Table,
    Text,
    Title,
)


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
    sections = _split_elements_by_title_and_table(elements)

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
    sections = chunk_by_title(elements)

    assert sections == [
        Section("A Great Day\n\nToday is a great day.\n\nIt is sunny outside."),
        Table("<table></table>"),
        Section("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        Section("A Bad Day\n\nToday is a bad day.\n\nIt is storming outside."),
        CheckBox(),
    ]
