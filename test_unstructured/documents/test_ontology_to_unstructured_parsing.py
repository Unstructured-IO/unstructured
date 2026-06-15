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


def test_partition_html_v2_assigns_heading_based_parent_id():
    """ML-1328 (AC #3): partition_html(v2) yields section->subsection parent_id.

    Hierarchy is assigned by the `@apply_metadata` decorator from the heading-level
    `category_depth`, exactly as for every other partitioner -- the v2 converter only
    sets `category_depth`, it does not run `set_element_hierarchy` itself. Both production
    callers (unstructured and the VLM partitioner) go through `partition_html`, so the
    decorator always runs; this exercises that real path end to end.
    """
    html = (
        '<div class="Page">'
        '<h1 class="Title">Section A</h1>'
        '<p class="NarrativeText">intro body under A</p>'
        '<h2 class="Subtitle">Sub A1</h2>'
        '<p class="NarrativeText">body under A1</p>'
        '<h3 class="Heading">Sub A1a</h3>'
        '<p class="NarrativeText">body under A1a</p>'
        '<h2 class="Subtitle">Sub A2</h2>'
        '<p class="NarrativeText">body under A2</p>'
        "</div>"
    )

    elements = partition_html(text=html, html_parser_version="v2")
    by_id = {e.id: e for e in elements}
    by_text = {e.text: e for e in elements if e.text}

    def parent_of(text):
        pid = by_text[text].metadata.parent_id
        return by_id.get(pid) if pid else None

    # top-level heading has no heading ancestor
    assert parent_of("Section A") is None
    # content + subsections are parented to their enclosing heading
    assert parent_of("intro body under A") is by_text["Section A"]
    assert parent_of("Sub A1") is by_text["Section A"]
    assert parent_of("body under A1") is by_text["Sub A1"]
    assert parent_of("Sub A1a") is by_text["Sub A1"]
    assert parent_of("body under A1a") is by_text["Sub A1a"]
    # a sibling subsection resets back to its section, not the deeper preceding heading
    assert parent_of("Sub A2") is by_text["Section A"]
    assert parent_of("body under A2") is by_text["Sub A2"]


def test_converter_leaves_content_parent_id_for_the_metadata_layer():
    """ML-1328 contract (abstraction boundary): called directly, the converter sets
    `category_depth` but leaves content `parent_id=None` -- hierarchy is the
    `@apply_metadata` layer's job, as for every other partitioner. This documents the
    intended boundary (a direct caller does NOT get heading-based parent_id) and guards
    against silently reintroducing a self-sufficient hierarchy pass in the converter.
    """
    ontology = Document(
        children=[
            Page(
                children=[
                    Title(text="Section A"),  # h1 -> category_depth 0
                    Paragraph(text="intro body"),
                    Subtitle(text="Sub A1"),  # h2 -> category_depth 1
                ]
            ),
        ]
    )

    page, section_a, intro, sub_a1 = ontology_to_unstructured_elements(ontology)

    # layout container keeps its tree parent (physical structure preserved)
    assert page.metadata.parent_id is not None
    # content carries heading-level category_depth ...
    assert section_a.metadata.category_depth == 0
    assert sub_a1.metadata.category_depth == 1
    # ... but no parent_id yet -- the decorator assigns the heading-based parent downstream
    assert section_a.metadata.parent_id is None
    assert intro.metadata.parent_id is None
    assert sub_a1.metadata.parent_id is None


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
