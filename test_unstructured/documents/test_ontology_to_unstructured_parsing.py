from pathlib import Path

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.ontology import (
    Column,
    Document,
    Hyperlink,
    Image,
    Page,
    Paragraph,
    Section,
    Table,
)
from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder
from unstructured.partition.html import partition_html
from unstructured.partition.html.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_from_json


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


def test_depth_is_passed_correctly():
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

    assert page1.metadata.category_depth == 0
    assert page2.metadata.category_depth == 0

    assert p1.metadata.category_depth == 1

    assert c2.metadata.category_depth == 1
    assert c1.metadata.category_depth == 1

    assert p2.metadata.category_depth == 2
    assert p3.metadata.category_depth == 2


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
