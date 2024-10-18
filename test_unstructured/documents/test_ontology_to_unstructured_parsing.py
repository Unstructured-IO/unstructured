from bs4 import BeautifulSoup

from unstructured.documents.elements import Element, ElementMetadata, NarrativeText, Text
from unstructured.documents.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology_element,
)


def html_to_unstructured_elements(html_as_str: str) -> list[Element]:
    first_element = BeautifulSoup(html_as_str, "html.parser").find()
    ontology = parse_html_to_ontology_element(first_element)
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    return unstructured_elements


def _assert_elements_equal(actual_elements, expected_elements):
    assert len(actual_elements) == len(expected_elements)
    for actual, expected in zip(actual_elements, expected_elements):
        assert actual == expected
        assert actual._element_id == expected._element_id
        assert actual.metadata.detection_origin == expected.metadata.detection_origin
        # Not all elements are considered be __eq__ Elements method
        assert actual.metadata.parent_id == expected.metadata.parent_id
        assert actual.metadata.text_as_html == expected.metadata.text_as_html


def test_simple_paragraph_parsing():
    # language=HTML
    html_as_str = """
        <span class="UncategorizedText" id="2">Example text </span>
    """
    unstructured_elements = html_to_unstructured_elements(html_as_str)
    expected_elements = [
        Text(
            text="Example text",
            element_id="2",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<span class="UncategorizedText" id="2">Example text </span>'
            ),
        )
    ]

    _assert_elements_equal(unstructured_elements, expected_elements)


def test_paragraph_parsing_with_id():
    # language=HTML
    html_as_str = """
    <p class="NarrativeText" id="73cd7b4a-2444-4910-87a4-138117dfaab9">
     DEALER ONLY
    </p>
    """
    unstructured_elements = html_to_unstructured_elements(html_as_str)
    expected_elements = [
        NarrativeText(
            text="DEALER ONLY",
            element_id="73cd7b4a-2444-4910-87a4-138117dfaab9",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<p class="NarrativeText" '
                'id="73cd7b4a-2444-4910-87a4-138117dfaab9">DEALER ONLY </p>'
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_paragraph_parsing_with_pages():
    # language=HTML
    html_as_str = """
    <body class='Document' id="0">
        <div class="Page" data-page-number="1"
        id="eb2cd96d-cd71-4970-b733-2e9b761bada8">
            <p class="NarrativeText" id="6135aeb6-9558-46e2-9da4-473a74db3e9d">
             DEALER ONLY
            </p>
        </div>
        <div class="Page" data-page-number="2"
        id="af1ccd96-2503-4597-aa78-41e020e5fcd8">
            <p class="NarrativeText" id="33d66969-b274-4f88-abaa-e7f258b1595f">
             Example Text
            </p>
        </div>
    </body>
    """
    unstructured_elements = html_to_unstructured_elements(html_as_str)
    expected_elements = [
        Text(
            text="",
            element_id="0",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(text_as_html='<body class="Document" id="0" />'),
        ),
        Text(
            text="",
            element_id="eb2cd96d-cd71-4970-b733-2e9b761bada8",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<div class="Page" data-page-number="1" '
                'id="eb2cd96d-cd71-4970-b733-2e9b761bada8" />',
                parent_id="0",
            ),
        ),
        NarrativeText(
            text="DEALER ONLY",
            element_id="6135aeb6-9558-46e2-9da4-473a74db3e9d",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                parent_id="eb2cd96d-cd71-4970-b733-2e9b761bada8",
                page_number=1,
                text_as_html='<p class="NarrativeText" '
                'id="6135aeb6-9558-46e2-9da4-473a74db3e9d">DEALER ONLY </p>',
            ),
        ),
        # PageBreak(text=""), # TODO
        Text(
            text="",
            element_id="af1ccd96-2503-4597-aa78-41e020e5fcd8",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<div class="Page" data-page-number="2" '
                'id="af1ccd96-2503-4597-aa78-41e020e5fcd8" />',
                parent_id="0",
            ),
        ),
        NarrativeText(
            text="Example Text",
            element_id="33d66969-b274-4f88-abaa-e7f258b1595f",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                parent_id="af1ccd96-2503-4597-aa78-41e020e5fcd8",
                page_number=2,
                text_as_html='<p class="NarrativeText" '
                'id="33d66969-b274-4f88-abaa-e7f258b1595f">Example Text </p>',
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)
