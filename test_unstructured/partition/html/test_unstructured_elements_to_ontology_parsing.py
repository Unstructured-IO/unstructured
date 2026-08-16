from unstructured.documents.elements import ElementMetadata, NarrativeText, Text
from unstructured.documents.ontology import Column, Document, Page, Paragraph
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


def test_elements_without_text_as_html_are_skipped_not_fatal():
    # An element with no HTML payload (text_as_html=None) carries nothing to rebuild the
    # ontology tree from. It must be skipped per-element, not crash the whole conversion.
    unstructured_elements = [
        Text(
            element_id="1",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        NarrativeText(
            element_id="2",
            text="no html payload",
            metadata=ElementMetadata(text_as_html=None, parent_id="1"),
        ),
        NarrativeText(
            element_id="3",
            text="Example text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Example text </p>', parent_id="1"
            ),
        ),
    ]

    ontology = unstructured_elements_to_ontology(unstructured_elements)  # must not raise

    assert isinstance(ontology, Document)
    page = ontology.children[0]
    assert isinstance(page, Page)
    # the None-payload element is skipped; the valid one still reconstructs
    assert len(page.children) == 1
    assert isinstance(page.children[0], Paragraph)
    assert page.children[0].text == "Example text"


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


def test_content_element_without_parent_nests_in_current_container():
    """ML-1328: tree reconstruction is layout-container driven, not content-`parent_id` driven.

    Content elements nest in the innermost open layout container regardless of their (now
    heading-based, possibly absent) `parent_id`. A paragraph with no `parent_id` therefore lands in
    the current Page rather than being lifted to a Document-level sibling -- and is not lost.
    """
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
        NarrativeText(
            element_id="3",
            text="Example text without parent",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Example text without parent </p>'
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)
    assert len(ontology.children) == 1
    page = ontology.children[0]
    assert isinstance(page, Page)
    assert len(page.children) == 2
    first, second = page.children
    assert first.text == "Example text"
    assert second.text == "Example text without parent"


def test_multiple_pages_can_be_combined():
    unstructured_elements = [
        Text(
            element_id="1",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        NarrativeText(
            element_id="2",
            text="Example text on page 1",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Example text on page 1 </p>', parent_id="1"
            ),
        ),
        Text(
            element_id="3",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        NarrativeText(
            element_id="4",
            text="Example text on page 2",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Example text on page 2 </p>', parent_id="3"
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)
    assert len(ontology.children) == 2
    page1 = ontology.children[0]
    page2 = ontology.children[1]
    assert isinstance(page1, Page)
    assert isinstance(page2, Page)
    assert len(page1.children) == 1
    assert len(page2.children) == 1
    paragraph1 = page1.children[0]
    paragraph2 = page2.children[0]
    assert isinstance(paragraph1, Paragraph)
    assert isinstance(paragraph2, Paragraph)
    assert paragraph1.text == "Example text on page 1"
    assert paragraph2.text == "Example text on page 2"


def test_empty_input_returns_empty_document():
    """ML-1328: empty input must return an empty Document, not raise IndexError."""
    ontology = unstructured_elements_to_ontology([])

    assert isinstance(ontology, Document)
    assert ontology.children == []


def test_nested_layout_containers_rebuild_column_nesting():
    """ML-1328: a Column nests inside its Page (container `parent_id` drives the layout tree).

    Two columns under one page; content nests in the innermost open container. This is the
    multi-column round-trip that exercises container-under-container nesting.
    """
    unstructured_elements = [
        Text(
            element_id="page",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        Text(
            element_id="col1",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Column"/>', parent_id="page"),
        ),
        NarrativeText(
            element_id="c1",
            text="Left column text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Left column text </p>', parent_id="col1"
            ),
        ),
        Text(
            element_id="col2",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Column"/>', parent_id="page"),
        ),
        NarrativeText(
            element_id="c2",
            text="Right column text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Right column text </p>', parent_id="col2"
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)
    assert len(ontology.children) == 1
    page = ontology.children[0]
    assert isinstance(page, Page)
    # -- both columns nest under the page; the second column did not pop past the page to root --
    assert len(page.children) == 2
    col1, col2 = page.children
    assert isinstance(col1, Column)
    assert isinstance(col2, Column)
    assert [c.text for c in col1.children] == ["Left column text"]
    assert [c.text for c in col2.children] == ["Right column text"]


def test_layout_container_with_unknown_parent_id_does_not_pop_to_root():
    """ML-1328: a container whose `parent_id` matches no open container nests in the current one.

    Malformed/reordered input (violating the documented parent-before-child precondition) must not
    pop past valid ancestors to the Document root and mis-nest subsequent content. The Column here
    references a non-existent parent; it should stay inside the open Page, and nothing is lost.
    """
    unstructured_elements = [
        Text(
            element_id="page",
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page"/>'),
        ),
        Text(
            element_id="col",
            text="",
            metadata=ElementMetadata(
                text_as_html='<div class="Column"/>', parent_id="DOES_NOT_EXIST"
            ),
        ),
        NarrativeText(
            element_id="c1",
            text="Body text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph"> Body text </p>', parent_id="col"
            ),
        ),
    ]
    ontology = unstructured_elements_to_ontology(unstructured_elements)

    assert isinstance(ontology, Document)
    assert len(ontology.children) == 1
    page = ontology.children[0]
    assert isinstance(page, Page)
    # -- the Column stayed nested in the Page rather than being lifted to a Document-level sibling
    assert len(page.children) == 1
    column = page.children[0]
    assert isinstance(column, Column)
    assert [c.text for c in column.children] == ["Body text"]
