import re

import pytest

from unstructured.metrics import text_extraction
from unstructured.metrics.table.table_extraction import (
    deckerd_table_to_html,
    extract_cells_from_table_as_cells,
    extract_cells_from_text_as_html,
    html_table_to_deckerd,
)
from unstructured.partition.auto import partition


def test_calculate_edit_distance():
    source_cct = "I like pizza. I like bagels."
    source_cct_word_space = "I like p i z z a . I like bagles."
    source_cct_spaces = re.sub(r"\s+", " ", " ".join(source_cct))
    source_cct_no_space = source_cct.replace(" ", "")
    source_cct_one_sentence = "I like pizza."
    source_cct_missing_word = "I like pizza. I like ."
    source_cct_addn_char = "I like pizza. I like beagles."
    source_cct_dup_word = "I like pizza pizza. I like bagels."

    assert (
        round(text_extraction.calculate_edit_distance(source_cct, source_cct, return_as="score"), 2)
        == 1.0
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_word_space,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.75
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_spaces,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.39
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_no_space,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.64
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_one_sentence,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.0
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_missing_word,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.57
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_addn_char,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.89
    )
    assert (
        round(
            text_extraction.calculate_edit_distance(
                source_cct_dup_word,
                source_cct,
                return_as="score",
            ),
            2,
        )
        == 0.79
    )


@pytest.mark.parametrize(
    ("filename", "standardize_whitespaces", "expected_score", "expected_distance"),
    [
        ("fake-text.txt", False, 0.78, 38),
        ("fake-text.txt", True, 0.92, 12),
    ],
)
def test_calculate_edit_distance_with_filename(
    filename, standardize_whitespaces, expected_score, expected_distance
):
    with open("example-docs/fake-text.txt") as f:
        source_cct = f.read()

    elements = partition(filename=f"example-docs/{filename}")
    output_cct = "\n".join([str(el) for el in elements])

    score = text_extraction.calculate_edit_distance(
        output_cct, source_cct, return_as="score", standardize_whitespaces=standardize_whitespaces
    )
    distance = text_extraction.calculate_edit_distance(
        output_cct,
        source_cct,
        return_as="distance",
        standardize_whitespaces=standardize_whitespaces,
    )

    assert score >= 0
    assert score <= 1.0
    assert distance >= 0
    assert round(score, 2) == expected_score
    assert distance == expected_distance


@pytest.mark.parametrize(
    ("text1", "text2"),
    [
        (
            "The  dog\rloved the cat, but\t\n    the cat\tloved the\n cow",
            "The dog loved the cat, but the cat loved the cow",
        ),
        (
            "Hello    my\tname\tis H a r p e r, \nwhat's your\vname?",
            "Hello my name is H a r p e r, what's your name?",
        ),
        (
            "I have a\t\n\tdog and a\tcat,\fI love my\n\n\n\ndog.",
            "I have a dog and a cat, I love my dog.",
        ),
        (
            """
            Name    Age City           Occupation
            Alice   30  New York       Engineer
            Bob     25  Los Angeles    Designer
            Charlie 35  Chicago        Teacher
            David   40  San Francisco  Developer
            """,
            """
            Name\tAge\tCity\tOccupation
            Alice\t30\tNew York\tEngineer
            Bob\t25\tLos Angeles\tDesigner
            Charlie\t35\tChicago\tTeacher
            David\t40\tSan Francisco\tDeveloper
            """,
        ),
        (
            """
            Name\tAge\tCity\tOccupation
            Alice\t30\tNew York\tEngineer
            Bob\t25\tLos Angeles\tDesigner
            Charlie\t35\tChicago\tTeacher
            David\t40\tSan Francisco\tDeveloper
            """,
            "Name\tAge\tCity\tOccupation\n\n \nAlice\t30\tNew York\tEngineer\nBob\t25\tLos Angeles\tDesigner\nCharlie\t35\tChicago\tTeacher\nDavid\t40\tSan Francisco\tDeveloper",  # noqa: E501
        ),
    ],
)
def test_calculate_edit_distance_with_various_whitespace_1(text1, text2):
    assert (
        text_extraction.calculate_edit_distance(
            text1, text2, return_as="score", standardize_whitespaces=True
        )
        == 1.0
    )
    assert (
        text_extraction.calculate_edit_distance(
            text1, text2, return_as="distance", standardize_whitespaces=True
        )
        == 0
    )
    assert (
        text_extraction.calculate_edit_distance(
            text1, text2, return_as="score", standardize_whitespaces=False
        )
        < 1.0
    )
    assert (
        text_extraction.calculate_edit_distance(
            text1, text2, return_as="distance", standardize_whitespaces=False
        )
        > 0
    )


def test_calculate_edit_distance_with_various_whitespace_2():
    source_cct_tabs = """
            Name\tAge\tCity\tOccupation
            Alice\t30\tNew York\tEngineer
            Bob\t25\tLos Angeles\tDesigner
            Charlie\t35\tChicago\tTeacher
            David\t40\tSan Francisco\tDeveloper
            """
    source_cct_with_borders = """

            | Name    | Age | City         | Occupation     |
            |---------|-----|--------------|----------------|
            | Alice   | 30  | New York     | Engineer       |
            | Bob     | 25  | Los Angeles  | Designer       |
            | Charlie | 35  | Chicago      | Teacher        |
            | David   | 40  | San Francisco| Developer      |

            """
    assert text_extraction.calculate_edit_distance(
        source_cct_tabs, source_cct_with_borders, return_as="score", standardize_whitespaces=True
    ) > text_extraction.calculate_edit_distance(
        source_cct_tabs, source_cct_with_borders, return_as="score", standardize_whitespaces=False
    )
    assert text_extraction.calculate_edit_distance(
        source_cct_tabs, source_cct_with_borders, return_as="distance", standardize_whitespaces=True
    ) < text_extraction.calculate_edit_distance(
        source_cct_tabs,
        source_cct_with_borders,
        return_as="distance",
        standardize_whitespaces=False,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The dog loved the cat, but the cat loved the cow",
            {"the": 4, "cat": 2, "loved": 2, "dog": 1, "but": 1, "cow": 1},
        ),
        (
            "Hello my name is H a r p e r, what's your name?",
            {"hello": 1, "my": 1, "name": 2, "is": 1, "what's": 1, "your": 1},
        ),
        (
            "I have a dog and a cat, I love my dog.",
            {"i": 2, "have": 1, "a": 2, "dog": 2, "and": 1, "cat": 1, "love": 1, "my": 1},
        ),
        (
            "My dog's hair is red, but the dogs' houses are blue.",
            {
                "my": 1,
                "dog's": 1,
                "hair": 1,
                "is": 1,
                "red": 1,
                "but": 1,
                "the": 1,
                "dogs'": 1,
                "houses": 1,
                "are": 1,
                "blue": 1,
            },
        ),
        (
            """Sometimes sentences have a dash - like this one!
                    A hyphen connects 2 words with no gap: easy-peasy.""",
            {
                "sometimes": 1,
                "sentences": 1,
                "have": 1,
                "a": 2,
                "dash": 1,
                "like": 1,
                "this": 1,
                "one": 1,
                "hyphen": 1,
                "connects": 1,
                "2": 1,
                "words": 1,
                "with": 1,
                "no": 1,
                "gap": 1,
                "easy-peasy": 1,
            },
        ),
    ],
)
def test_bag_of_words(text, expected):
    assert text_extraction.bag_of_words(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The  dog\rloved the cat, but\t\n    the cat\tloved the\n cow\n\n",
            "The dog loved the cat, but the cat loved the cow",
        ),
        (
            "\n\nHello    my\tname\tis H a r p e r, \nwhat's your\vname?",
            "Hello my name is H a r p e r, what's your name?",
        ),
        (
            "I have a\t\n\tdog and a\tcat,\fI love my\n\n\n\ndog.",
            "I have a dog and a cat, I love my dog.",
        ),
        (
            """L     is for the way you look at me
            O    is for the only one I see
            V    is very, very extraordinary
            E    is even more than anyone that you adore can""",
            "L is for the way you look at me O is for the only one I see V is very, very extraordinary E is even more than anyone that you adore can",  # noqa: E501
        ),
        (
            """
            | Name    | Age | City         | Occupation     |
            |---------|-----|--------------|----------------|
            | Alice   | 30  | New York     | Engineer       |
            | Bob     | 25  | Los Angeles  | Designer       |
            | Charlie | 35  | Chicago      | Teacher        |
            | David   | 40  | San Francisco| Developer      |
            """,
            "| Name | Age | City | Occupation | |---------|-----|--------------|----------------| | Alice | 30 | New York | Engineer | | Bob | 25 | Los Angeles | Designer | | Charlie | 35 | Chicago | Teacher | | David | 40 | San Francisco| Developer |",  # noqa: E501
        ),
    ],
)
def test_prepare_string(text, expected):
    assert text_extraction.prepare_str(text, standardize_whitespaces=True) == expected
    assert text_extraction.prepare_str(text) == text


@pytest.mark.parametrize(
    ("output_text", "source_text", "expected_percentage"),
    [
        (
            "extra",
            "",
            0,
        ),
        (
            "",
            "Source text has a sentence.",
            1,
        ),
        (
            "The original s e n t e n c e is normal.",
            "The original sentence is normal...",
            0.2,
        ),
        (
            "We saw 23% improvement in this quarter.",
            "We saw 23% improvement in sales this quarter.",
            0.125,
        ),
        (
            "no",
            "Is it possible to have more than everything missing?",
            1,
        ),
    ],
)
def test_calculate_percent_missing_text(output_text, source_text, expected_percentage):
    assert (
        text_extraction.calculate_percent_missing_text(output_text, source_text)
        == expected_percentage
    )


@pytest.mark.parametrize(
    ("table_as_cells", "expected_extraction"),
    [
        pytest.param(
            [
                {"x": 0, "y": 0, "w": 1, "h": 1, "content": "Month A."},
                {"x": 0, "y": 1, "w": 1, "h": 1, "content": "22"},
            ],
            [
                {"row_index": 0, "col_index": 0, "content": "Month A."},
                {"row_index": 1, "col_index": 0, "content": "22"},
            ],
            id="Simple table, 1 head cell, 1 body cell, no spans",
        ),
        pytest.param(
            [
                {"x": 0, "y": 0, "w": 1, "h": 1, "content": "Month A."},
                {"x": 1, "y": 0, "w": 1, "h": 1, "content": "Month B."},
                {"x": 2, "y": 0, "w": 1, "h": 1, "content": "Month C."},
                {"x": 0, "y": 1, "w": 1, "h": 1, "content": "11"},
                {"x": 1, "y": 1, "w": 1, "h": 1, "content": "12"},
                {"x": 2, "y": 1, "w": 1, "h": 1, "content": "13"},
                {"x": 0, "y": 2, "w": 1, "h": 1, "content": "21"},
                {"x": 1, "y": 2, "w": 1, "h": 1, "content": "22"},
                {"x": 2, "y": 2, "w": 1, "h": 1, "content": "23"},
            ],
            [
                {"row_index": 0, "col_index": 0, "content": "Month A."},
                {"row_index": 0, "col_index": 1, "content": "Month B."},
                {"row_index": 0, "col_index": 2, "content": "Month C."},
                {"row_index": 1, "col_index": 0, "content": "11"},
                {"row_index": 1, "col_index": 1, "content": "12"},
                {"row_index": 1, "col_index": 2, "content": "13"},
                {"row_index": 2, "col_index": 0, "content": "21"},
                {"row_index": 2, "col_index": 1, "content": "22"},
                {"row_index": 2, "col_index": 2, "content": "23"},
            ],
            id="Simple table, 3 head cell, 5 body cell, no spans",
        ),
        # +----------+---------------------+----------+
        # |          |       h1col23       |  h1col4  |
        # | h12col1  |----------+----------+----------|
        # |          |  h2col2  |       h2col34       |
        # |----------|----------+----------+----------+
        # |  r3col1  |  r3col2  |                     |
        # |----------+----------|      r34col34       |
        # |       r4col12       |                     |
        # +----------+----------+----------+----------+
        pytest.param(
            [
                {
                    "y": 0,
                    "x": 0,
                    "w": 2,
                    "h": 1,
                    "content": "h12col1",
                },
                {
                    "y": 0,
                    "x": 1,
                    "w": 1,
                    "h": 2,
                    "content": "h1col23",
                },
                {
                    "y": 0,
                    "x": 3,
                    "w": 1,
                    "h": 1,
                    "content": "h1col4",
                },
                {
                    "y": 1,
                    "x": 1,
                    "w": 1,
                    "h": 1,
                    "content": "h2col2",
                },
                {
                    "y": 1,
                    "x": 2,
                    "w": 1,
                    "h": 2,
                    "content": "h2col34",
                },
                {
                    "y": 2,
                    "x": 0,
                    "w": 1,
                    "h": 1,
                    "content": "r3col1",
                },
                {
                    "y": 2,
                    "x": 1,
                    "w": 1,
                    "h": 1,
                    "content": "r3col2",
                },
                {
                    "y": 2,
                    "x": 2,
                    "w": 2,
                    "h": 2,
                    "content": "r34col34",
                },
                {
                    "y": 3,
                    "x": 0,
                    "w": 1,
                    "h": 2,
                    "content": "r4col12",
                },
            ],
            [
                {
                    "row_index": 0,
                    "col_index": 0,
                    "content": "h12col1",
                },
                {
                    "row_index": 0,
                    "col_index": 1,
                    "content": "h1col23",
                },
                {
                    "row_index": 0,
                    "col_index": 3,
                    "content": "h1col4",
                },
                {
                    "row_index": 1,
                    "col_index": 1,
                    "content": "h2col2",
                },
                {
                    "row_index": 1,
                    "col_index": 2,
                    "content": "h2col34",
                },
                {
                    "row_index": 2,
                    "col_index": 0,
                    "content": "r3col1",
                },
                {
                    "row_index": 2,
                    "col_index": 1,
                    "content": "r3col2",
                },
                {
                    "row_index": 2,
                    "col_index": 2,
                    "content": "r34col34",
                },
                {
                    "row_index": 3,
                    "col_index": 0,
                    "content": "r4col12",
                },
            ],
            id="various spans, with 2 row header",
        ),
    ],
)
def test_cells_table_extraction_from_prediction(table_as_cells, expected_extraction):
    example_element = {
        "type": "Table",
        "metadata": {"table_as_cells": table_as_cells},
    }
    assert extract_cells_from_table_as_cells(example_element) == expected_extraction


@pytest.mark.parametrize(
    ("text_as_html", "expected_extraction"),
    [
        pytest.param(
            """
<table>
    <thead>
        <tr>
            <th>Month A.</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>22</td>
        </tr>
    </tbody>
</table>"
            """,
            [
                {"row_index": 0, "col_index": 0, "content": "Month A."},
                {"row_index": 1, "col_index": 0, "content": "22"},
            ],
            id="Simple table, 1 head cell, 1 body cell, no spans",
        ),
        pytest.param(
            """
<table>
    <thead>
        <tr>
            <th>Month A.</th>
            <th>Month B.</th>
            <th>Month C.</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>11</td>
            <td>12</td>
            <td>13</td>
        </tr>
        <tr>
            <td>21</td>
            <td>22</td>
            <td>23</td>
        </tr>
    </tbody>
</table>"
""",
            [
                {"row_index": 0, "col_index": 0, "content": "Month A."},
                {"row_index": 0, "col_index": 1, "content": "Month B."},
                {"row_index": 0, "col_index": 2, "content": "Month C."},
                {"row_index": 1, "col_index": 0, "content": "11"},
                {"row_index": 1, "col_index": 1, "content": "12"},
                {"row_index": 1, "col_index": 2, "content": "13"},
                {"row_index": 2, "col_index": 0, "content": "21"},
                {"row_index": 2, "col_index": 1, "content": "22"},
                {"row_index": 2, "col_index": 2, "content": "23"},
            ],
            id="Simple table, 3 head cell, 5 body cell, no spans",
        ),
        # +----------+---------------------+----------+
        # |          |       h1col23       |  h1col4  |
        # | h12col1  |----------+----------+----------|
        # |          |  h2col2  |       h2col34       |
        # |----------|----------+----------+----------+
        # |  r3col1  |  r3col2  |                     |
        # |----------+----------|      r34col34       |
        # |       r4col12       |                     |
        # +----------+----------+----------+----------+
        pytest.param(
            """
<table>
    <thead>
        <tr>
            <th rowspan="2">h12col1</th>
            <th colspan="2">h1col23</th>
            <th>h1col4</th>
        </tr>
        <tr>
            <th>h2col2</th>
            <th colspan="2">h2col34</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>r3col1</td>
            <td>r3col2</td>
            <td colspan="2" rowspan="2">r34col34</td>
        </tr>
        <tr>
            <td colspan="2">r4col12</td>
        </tr>
    </tbody>
</table>
""",
            [
                {
                    "row_index": 0,
                    "col_index": 0,
                    "content": "h12col1",
                },
                {
                    "row_index": 0,
                    "col_index": 1,
                    "content": "h1col23",
                },
                {
                    "row_index": 0,
                    "col_index": 3,
                    "content": "h1col4",
                },
                {
                    "row_index": 1,
                    "col_index": 1,
                    "content": "h2col2",
                },
                {
                    "row_index": 1,
                    "col_index": 2,
                    "content": "h2col34",
                },
                {
                    "row_index": 2,
                    "col_index": 0,
                    "content": "r3col1",
                },
                {
                    "row_index": 2,
                    "col_index": 1,
                    "content": "r3col2",
                },
                {
                    "row_index": 2,
                    "col_index": 2,
                    "content": "r34col34",
                },
                {
                    "row_index": 3,
                    "col_index": 0,
                    "content": "r4col12",
                },
            ],
            id="various spans, with 2 row header",
        ),
    ],
)
def test_html_table_extraction_from_prediction(text_as_html, expected_extraction):
    example_element = {
        "type": "Table",
        "metadata": {
            "text_as_html": text_as_html,
        },
    }
    assert extract_cells_from_text_as_html(example_element) == expected_extraction


def test_cells_extraction_from_prediction_when_missing_prediction():
    example_element = {"type": "Table", "metadata": {"text_as_html": "", "table_as_cells": []}}
    assert extract_cells_from_text_as_html(example_element) is None
    assert extract_cells_from_table_as_cells(example_element) is None


def _trim_html(html: str) -> str:
    html_lines = [line.strip() for line in html.split("\n") if line]
    return "".join(html_lines)


@pytest.mark.parametrize(
    "html_to_test",
    [
        """
<table>
    <thead>
        <tr>
            <th>Month A.</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>22</td>
        </tr>
    </tbody>
</table>
""",
        """
<table>
    <thead>
        <tr>
            <th>Month A.</th>
            <th>Month B.</th>
            <th>Month C.</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>11</td>
            <td>12</td>
            <td>13</td>
        </tr>
        <tr>
            <td>21</td>
            <td>22</td>
            <td>23</td>
        </tr>
    </tbody>
</table>
""",
        """
<table>
    <thead>
        <tr>
            <th rowspan="2">h12col1</th>
            <th colspan="2">h1col23</th>
            <th>h1col4</th>
        </tr>
        <tr>
            <th>h2col2</th>
            <th colspan="2">h2col34</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>r3col1</td>
            <td>r3col2</td>
            <td colspan="2" rowspan="2">r34col34</td>
        </tr>
        <tr>
            <td colspan="2">r4col12</td>
        </tr>
    </tbody>
</table>
""",
    ],
)
def test_deckerd_html_converter(html_to_test):
    deckerd_table = html_table_to_deckerd(html_to_test)
    html_table = deckerd_table_to_html(deckerd_table)
    assert _trim_html(html_to_test) == html_table
