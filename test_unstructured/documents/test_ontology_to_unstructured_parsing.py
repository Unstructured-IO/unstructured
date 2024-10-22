from pathlib import Path

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.ontology import Column, Document, Page, Paragraph
from unstructured.documents.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
)
from unstructured.embed.openai import OpenAIEmbeddingConfig, OpenAIEmbeddingEncoder
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
        ("html_files/example.html", "structured_jsons/example.json"),
    ],
)
def test_ingest(html_file_path, json_file_path):
    html_code = Path(html_file_path).read_text()
    expected_json_elements = elements_from_json(str(Path(json_file_path)))

    ontology = parse_html_to_ontology(html_code)
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    assert unstructured_elements == expected_json_elements
