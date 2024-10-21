from unstructured.documents.ontology import Column, Document, Page, Paragraph
from unstructured.documents.transformations import (
    ontology_to_unstructured_elements,
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
    body, page1, p1, page2, p2 = unstructured_elements
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
    body, page1, p1 = unstructured_elements
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
    body, page1, p1, page2, c1, p2, c2, p3 = unstructured_elements
    assert body.metadata.category_depth == 0

    assert page1.metadata.category_depth == 1
    assert page2.metadata.category_depth == 1

    assert p1.metadata.category_depth == 2

    assert c2.metadata.category_depth == 2
    assert c1.metadata.category_depth == 2

    assert p2.metadata.category_depth == 3
    assert p3.metadata.category_depth == 3
