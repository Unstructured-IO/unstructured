from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, Text
from unstructured.documents.ontology import (
    Column,
    Document,
    Heading,
    Hyperlink,
    Image,
    Page,
    Paragraph,
    Section,
    Subtitle,
    Table,
    Title,
    remove_ids_and_class_from_table,
)
from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder
from unstructured.partition.html import partition_html
from unstructured.partition.html.transformations import (
    can_unstructured_elements_be_merged,
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_from_json


def test_remove_ids_and_class_from_table():
    html_text = """
    <table>
        <tr class="TableRow">
            <td><img class="Signature" alt="cell 1"/></td>
            <td>cell 2</td>
        </tr>
        <tr>
            <td><IMG class="Signature" alt="cell 3"/></td>
            <td>cell 4</td>
        </tr>
        <tr>
            <td><input class="Checkbox" type="checkbox"/></td>
            <td>Option 1</td>
        </tr>
    </table>
    """
    soup = BeautifulSoup(html_text, "html.parser")
    assert (
        str(remove_ids_and_class_from_table(soup))
        == """
<table>
<tr>
<td><img alt="cell 1" class="Signature"/></td>
<td>cell 2</td>
</tr>
<tr>
<td><img alt="cell 3" class="Signature"/></td>
<td>cell 4</td>
</tr>
<tr>
<td><input class="Checkbox" type="checkbox"/></td>
<td>Option 1</td>
</tr>
</table>
"""
    )


def test_page_number_is_passed_correctly():
    ontology = Document(
        children=[
            Page(
                children=[Paragraph(text="Paragraph1")],
                additional_attributes={"data-page-number": "1"},
            ),
            Page(
                children=[Paragraph(text="Paragraph2")],
                additional_attributes={"data-page-number": "2"},
            ),
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    page1, p1, page2, p2 = unstructured_elements
    assert p1.metadata.page_number == 1
    assert p2.metadata.page_number == 2


def test_invalid_page_number_is_not_passed():
    ontology = Document(
        children=[
            Page(
                children=[Paragraph(text="Paragraph1")],
                additional_attributes={"data-page-number": "invalid"},
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    page1, p1 = unstructured_elements
    assert not p1.metadata.page_number


def test_category_depth_is_not_derived_from_layout_nesting():
    """ML-1328: `category_depth` reflects heading level, not DOM/layout nesting.

    Layout containers (Page/Column) and non-heading content carry no `category_depth`, so a
    paragraph reads the same whether it sits in a single-column page or inside a column of a
    two-column page (i.e. depth does not change solely due to multi-column layout).
    """
    ontology = Document(
        children=[
            Page(children=[Paragraph(text="Paragraph1")]),
            Page(
                children=[
                    Column(children=[Paragraph(text="Paragraph2")]),
                    Column(children=[Paragraph(text="Paragraph3")]),
                ]
            ),
        ]
    )

    unstructured_elements = ontology_to_unstructured_elements(ontology)
    page1, p1, page2, c1, p2, c2, p3 = unstructured_elements

    # -- layout containers are not headings -> no depth --
    assert page1.metadata.category_depth is None
    assert page2.metadata.category_depth is None
    assert c1.metadata.category_depth is None
    assert c2.metadata.category_depth is None

    # -- plain paragraphs are not headings -> no depth, regardless of single- vs multi-column --
    assert p1.metadata.category_depth is None
    assert p2.metadata.category_depth is None
    assert p3.metadata.category_depth is None


def test_category_depth_is_derived_from_heading_level():
    """ML-1328: heading elements get `category_depth` from their HTML heading level."""
    ontology = Document(
        children=[
            Page(
                children=[
                    Title(text="Section"),  # <h1> -> 0
                    Subtitle(text="Subsection"),  # <h2> -> 1
                    Heading(text="Sub-subsection", html_tag_name="h3"),  # <h3> -> 2
                    Paragraph(text="Body text"),  # not a heading -> None
                ]
            ),
        ]
    )

    unstructured_elements = ontology_to_unstructured_elements(ontology)
    _page, title, subtitle, heading, body = unstructured_elements

    assert title.metadata.category_depth == 0
    assert subtitle.metadata.category_depth == 1
    assert heading.metadata.category_depth == 2
    assert body.metadata.category_depth is None


def test_converter_assigns_heading_based_parent_id_without_decorator():
    """ML-1328: the converter's output is self-sufficient.

    `ontology_to_unstructured_elements` applies `set_element_hierarchy` itself, so content elements
    get their heading-based `parent_id` directly from the converter -- no dependency on the
    `@apply_metadata` decorator on `partition_html`. Layout containers keep their tree `parent_id`.
    """
    ontology = Document(
        children=[
            Page(
                children=[
                    Title(text="Section A"),  # h1 -> root (no heading ancestor)
                    Paragraph(text="intro body"),  # -> Section A
                    Subtitle(text="Sub A1"),  # h2 -> Section A
                    Paragraph(text="a1 body"),  # -> Sub A1
                    Heading(text="Sub A1a", html_tag_name="h3"),  # h3 -> Sub A1
                    Paragraph(text="a1a body"),  # -> Sub A1a
                ]
            ),
        ]
    )

    elements = ontology_to_unstructured_elements(ontology)
    page, section_a, intro, sub_a1, a1_body, sub_a1a, a1a_body = elements
    by_id = {e.id: e for e in elements}

    # -- layout container keeps its tree parent (here the Document root, not a heading) --
    assert page.metadata.parent_id not in {e.id for e in elements}
    # -- top-level heading has no heading ancestor --
    assert section_a.metadata.parent_id is None
    # -- content/subsections are parented to their enclosing heading --
    assert by_id[intro.metadata.parent_id] is section_a
    assert by_id[sub_a1.metadata.parent_id] is section_a
    assert by_id[a1_body.metadata.parent_id] is sub_a1
    assert by_id[sub_a1a.metadata.parent_id] is sub_a1
    assert by_id[a1a_body.metadata.parent_id] is sub_a1a


def test_re_running_set_element_hierarchy_on_converter_output_is_a_noop():
    """ML-1328: the decorator's second `set_element_hierarchy` pass must not change anything.

    `partition_html` runs the converter inside `@apply_metadata`, which re-runs
    `set_element_hierarchy`. Because the converter already assigned every `parent_id`, that pass
    must be a no-op (no reassignment, no reordering).
    """
    from unstructured.partition.common.metadata import set_element_hierarchy

    ontology = Document(
        children=[
            Page(
                children=[
                    Title(text="Section A"),
                    Paragraph(text="intro body"),
                    Subtitle(text="Sub A1"),
                    Paragraph(text="a1 body"),
                ]
            ),
        ]
    )

    elements = ontology_to_unstructured_elements(ontology)
    before = [(e.id, e.metadata.parent_id) for e in elements]

    reprocessed = set_element_hierarchy(elements)

    after = [(e.id, e.metadata.parent_id) for e in reprocessed]
    assert [e.id for e in reprocessed] == [e.id for e in elements]  # order preserved
    assert after == before  # parent_ids unchanged


def test_chunking_is_applied_on_elements():
    ontology = Document(
        children=[
            Page(children=[Paragraph(text="Paragraph1")]),
            Page(
                children=[
                    Column(children=[Paragraph(text="Paragraph2")]),
                    Column(children=[Paragraph(text="Paragraph3")]),
                ]
            ),
        ]
    )

    unstructured_elements = ontology_to_unstructured_elements(ontology)

    chunked_basic = chunk_elements(unstructured_elements)
    assert str(chunked_basic[0]) == "Paragraph1\n\nParagraph2\n\nParagraph3"
    chunked_by_title = chunk_by_title(unstructured_elements)
    assert str(chunked_by_title[0]) == "Paragraph1\n\nParagraph2\n\nParagraph3"


def test_embeddings_are_applied_on_elements(mocker):
    ontology = Document(
        children=[
            Page(children=[Paragraph(text="Paragraph1")]),
            Page(
                children=[
                    Column(children=[Paragraph(text="Paragraph2")]),
                    Column(children=[Paragraph(text="Paragraph3")]),
                ]
            ),
        ]
    )

    unstructured_elements = ontology_to_unstructured_elements(ontology)
    # Mocked client with the desired behavior for embed_documents
    mock_client = mocker.MagicMock()
    mock_client.embed_documents.return_value = [1, 2, 3, 4, 5, 6, 7]

    # Mock get_client to return our mock_client
    mocker.patch.object(OpenAIEmbeddingConfig, "get_client", return_value=mock_client)

    encoder = OpenAIEmbeddingEncoder(config=OpenAIEmbeddingConfig(api_key="api_key"))
    elements = encoder.embed_documents(
        elements=unstructured_elements,
    )

    assert len(elements) == 7

    page1, p1, page2, c1, p2, c2, p3 = elements

    assert p1.embeddings == 2
    assert p2.embeddings == 5
    assert p3.embeddings == 7


@pytest.mark.parametrize(
    ("html_file_path", "json_file_path"),
    [
        ("html_files/example.html", "unstructured_json_output/example.json"),
    ],
)
def test_ingest(html_file_path, json_file_path):
    html_file_path = Path(__file__).parent / html_file_path
    json_file_path = Path(__file__).parent / json_file_path

    html_code = html_file_path.read_text()
    expected_json_elements = elements_from_json(str(json_file_path))

    ontology = parse_html_to_ontology(html_code)
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert unstructured_elements == expected_json_elements


@pytest.mark.parametrize("json_file_path", ["unstructured_json_output/example.json"])
def test_parsed_ontology_can_be_serialized_from_json(json_file_path):
    json_file_path = Path(__file__).parent / json_file_path

    expected_json_elements = elements_from_json(str(json_file_path))

    json_elements_text = json_file_path.read_text()
    elements = partition_json(text=json_elements_text)

    assert len(elements) == len(expected_json_elements)
    for i in range(len(elements)):
        assert elements[i] == expected_json_elements[i]
        # The partitioning output comes from PDF file, so only stem is compared
        # as the suffix is different .pdf != .json
        assert Path(elements[i].metadata.filename).stem == json_file_path.stem


@pytest.mark.parametrize(
    ("html_file_path", "json_file_path"),
    [
        ("html_files/example.html", "unstructured_json_output/example.json"),
        ("html_files/example_full_doc.html", "unstructured_json_output/example_full_doc.json"),
        (
            "html_files/example_with_alternative_text.html",
            "unstructured_json_output/example_with_alternative_text.json",
        ),
        ("html_files/three_tables.html", "unstructured_json_output/three_tables.json"),
        (
            "html_files/example_with_inline_fields.html",
            "unstructured_json_output/example_with_inline_fields.json",
        ),
    ],
)
def test_parsed_ontology_can_be_serialized_from_html(html_file_path, json_file_path):
    html_file_path = Path(__file__).parent / html_file_path
    json_file_path = Path(__file__).parent / json_file_path
    expected_json_elements = elements_from_json(str(json_file_path))
    html_code = html_file_path.read_text()

    predicted_elements = partition_html(
        text=html_code, html_parser_version="v2", unique_element_ids=True
    )

    assert len(expected_json_elements) == len(predicted_elements)

    for i in range(len(expected_json_elements)):
        assert expected_json_elements[i] == predicted_elements[i]
        assert (
            expected_json_elements[i].metadata.text_as_html
            == predicted_elements[i].metadata.text_as_html
        )


def test_inline_elements_are_squeezed():
    ontology = Document(
        children=[
            Page(
                children=[
                    Hyperlink(text="Hyperlink1"),
                    Hyperlink(text="Hyperlink2"),
                    Hyperlink(text="Hyperlink3"),
                ],
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert len(unstructured_elements) == 2

    page, text1 = unstructured_elements
    assert text1.text == "Hyperlink1 Hyperlink2 Hyperlink3"


def test_text_elements_are_squeezed():
    ontology = Document(
        children=[
            Page(
                children=[
                    Paragraph(text="Paragraph1"),
                    Paragraph(text="Paragraph2"),
                ],
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert len(unstructured_elements) == 2

    page, text1 = unstructured_elements
    assert text1.text == "Paragraph1 Paragraph2"


def test_inline_elements_are_squeezed_when_image():
    ontology = Document(
        children=[
            Page(
                children=[
                    Paragraph(text="Paragraph1"),
                    Hyperlink(text="Hyperlink1"),
                    Image(text="Image1"),
                    Hyperlink(text="Hyperlink2"),
                    Hyperlink(text="Hyperlink3"),
                    Paragraph(text="Paragraph2"),
                    Paragraph(text="Paragraph3"),
                ],
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert len(unstructured_elements) == 4

    page, text1, image, text2 = unstructured_elements
    assert text1.text == "Paragraph1 Hyperlink1"
    assert text2.text == "Hyperlink2 Hyperlink3 Paragraph2 Paragraph3"

    assert '<a class="Hyperlink"' in text1.metadata.text_as_html
    assert '<p class="Paragraph"' in text1.metadata.text_as_html

    assert '<a class="Hyperlink"' in text2.metadata.text_as_html
    assert '<p class="Paragraph"' in text2.metadata.text_as_html


def test_inline_elements_are_squeezed_when_table():
    ontology = Document(
        children=[
            Page(
                children=[
                    Hyperlink(text="Hyperlink1"),
                    Paragraph(text="Paragraph1"),
                    Paragraph(text="Paragraph2"),
                    Table(text="Table1"),
                    Paragraph(text="Paragraph2"),
                    Hyperlink(text="Hyperlink2"),
                    Hyperlink(text="Hyperlink3"),
                ],
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert len(unstructured_elements) == 4

    page, text1, table1, text3 = unstructured_elements
    assert text1.text == "Hyperlink1 Paragraph1 Paragraph2"
    assert table1.text == "Table1"
    assert text3.text == "Paragraph2 Hyperlink2 Hyperlink3"


def test_inline_elements_are_on_many_depths():
    ontology = Document(
        children=[
            Page(
                children=[
                    Hyperlink(text="Hyperlink1"),
                    Paragraph(text="Paragraph1"),
                    Section(
                        children=[
                            Section(
                                children=[
                                    Hyperlink(text="Hyperlink2"),
                                    Hyperlink(text="Hyperlink3"),
                                ]
                            ),
                            Paragraph(text="Paragraph2"),
                            Hyperlink(text="Hyperlink4"),
                        ]
                    ),
                ],
            )
        ]
    )
    unstructured_elements = ontology_to_unstructured_elements(ontology)

    assert len(unstructured_elements) == 6

    page, text1, section1, section2, text2, text3 = unstructured_elements

    assert text1.text == "Hyperlink1 Paragraph1"
    assert text2.text == "Hyperlink2 Hyperlink3"
    assert text3.text == "Paragraph2 Hyperlink4"


def _inline_element(text: str) -> Text:
    """A childless inline (Hyperlink) element -- mergeable on the content rules alone."""
    html = f'<a class="Hyperlink">{text}</a>'
    return Text(text=text, metadata=ElementMetadata(text_as_html=html))


def test_inline_elements_at_the_same_nesting_depth_can_be_merged():
    # ML-1328: "same level in the HTML tree" is the DOM-nesting depth. Two childless inline
    # elements sitting at the same depth are eligible to be merged into one element.
    first, second = _inline_element("a"), _inline_element("b")

    assert can_unstructured_elements_be_merged(first, second, current_depth=2, next_depth=2) is True


def test_inline_elements_at_different_nesting_depths_are_not_merged():
    # ML-1328: elements on different levels of the HTML tree must never merge, even when their
    # content (childless inline) would otherwise allow it.
    first, second = _inline_element("a"), _inline_element("b")

    assert (
        can_unstructured_elements_be_merged(first, second, current_depth=1, next_depth=2) is False
    )
