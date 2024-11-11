from pathlib import Path

import pytest

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, NarrativeText, Text, Title
from unstructured.staging.base import elements_from_json


@pytest.mark.parametrize(
    "json_file_path",
    [
        "unstructured_json_output/example.json",
        "unstructured_json_output/example_full_doc.json",
        "unstructured_json_output/example_with_inline_fields.json",
    ],
)
def test_chunking_output(json_file_path):
    json_file_path = Path(__file__).parent / json_file_path
    expected_json_elements = elements_from_json(str(json_file_path))
    chunks = chunk_by_title(expected_json_elements, combine_text_under_n_chars=0)

    assert False


def test_combining_html_metadata():
    meta_1 = '<h1 class="Title" id="1">Header </h1>'
    meta_2 = '<time class="CalendarDate" id="2">Date: October 30, 2023 </time>'
    meta_3 = '<form class="Form" id="3"> <label class="FormField" for="company-name" id="4">From field name </label><input class="FormFieldValue" id="5" value="Example value" /></form>'
    combined_metadata = meta_1 + meta_2 + meta_3

    elements = [
        Title(text="Header", metadata=ElementMetadata(text_as_html=meta_1)),
        Text(text="Date: October 30, 2023", metadata=ElementMetadata(text_as_html=meta_2)),
        Text(text="From field name Example value", metadata=ElementMetadata(text_as_html=meta_3)),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)
    assert len(chunks) == 1
    assert chunks[0].metadata.text_as_html == combined_metadata


def test_combining_html_metadata_with_parent():
    """
    Ground truth
    <Document>
        <Page>
            <Section>
                <p>First </p>
                <p>Second </p>
            </Section>
        </Page>
    </Document>
    Elements: Document, Page, Section, Paragraph, Paragraph
    Chunk 1: Document, Page, Section, Paragraph

    Chunk 2:
        Current: Paragraph
        Okay? or: Document, Page, Section, Paragraph
    """

    meta_1 = '<div class="Section" id="1" />'
    meta_2 = '<p class="Paragraph" id="2">First </p>'
    meta_3 = '<p class="Paragraph" id="3">Second </p>'

    elements = [
        Text(text="", metadata=ElementMetadata(text_as_html=meta_1)),
        NarrativeText(text="First", metadata=ElementMetadata(text_as_html=meta_2, parent_id="1")),
        NarrativeText(text="Second", metadata=ElementMetadata(text_as_html=meta_3, parent_id="1")),
    ]
    chunks = chunk_by_title(elements, max_characters=6, combine_text_under_n_chars=0)
    assert len(chunks) == 2
    assert chunks[0].text == "First"
    assert chunks[1].text == "Second"

    assert chunks[0].metadata.text_as_html == meta_1 + meta_2
    assert chunks[1].metadata.text_as_html == meta_3


def test_splitting_html_metadata():
    meta_1 = '<h1 class="Title" id="1">Header </h1>'
    elements = [
        Title(text="Header", metadata=ElementMetadata(text_as_html=meta_1)),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0, max_characters=3)
    assert len(chunks) == 2

    assert chunks[0].text == "Hea"
    assert chunks[1].text == "der"
    assert chunks[0].metadata.text_as_html == '<h1 class="Title" id="1">Header </h1>'
    assert chunks[1].metadata.text_as_html == '<h1 class="Title" id="1">Header </h1>'


def test_splitting_text():
    elements = [
        Title(text="Header", metadata=ElementMetadata(text_as_html="Header")),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0, max_characters=3)
    assert len(chunks) == 2

    assert chunks[0].text == "Hea"
    assert chunks[1].text == "der"
    assert chunks[0].metadata.text_as_html == "Header"
    assert chunks[1].metadata.text_as_html == "Header"
