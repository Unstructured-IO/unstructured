from unstructured.documents.elements import ElementMetadata, NarrativeText, Text
from unstructured.documents.ontology import Document, Page, Paragraph
from unstructured.partition.html.transformations import unstructured_elements_to_ontology


def test_when_first_elements_does_not_have_id():
    unstructured_elements = [
        Text(
            element_id="1",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        NarrativeText(
            element_id="2",
            text="Example text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Example text </p>', parent_id="1"
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)

    assert len(ontology.children) == 1
    page = ontology.children[0]

    assert isinstance(page, Page)
    assert len(page.children) == 1
    paragraph = page.children[0]

    assert isinstance(paragraph, Paragraph)
    assert paragraph.text == "Example text"


def test_when_two_combined_elements_have_the_same_parent():
    unstructured_elements = [
        Text(
            element_id="1",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        NarrativeText(
            element_id="2",
            text="Example text",
            metadata=ElementMetadata(
                text_as_html=(
                    '<p class="Paragraph"> Example text </p>'
                    '<p class="Paragraph"> Example text 2 </p>'
                ),
                parent_id="1",
            ),
        ),
        NarrativeText(
            element_id="3",
            text="Example text 2",
            metadata=ElementMetadata(
                text_as_html=(
                    '<p class="Paragraph"> Example text 3 </p>'
                    '<p class="Paragraph"> Example text 4 </p>'
                ),
                parent_id="1",
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)

    assert len(ontology.children) == 1
    page = ontology.children[0]

    assert isinstance(page, Page)
    assert len(page.children) == 4
