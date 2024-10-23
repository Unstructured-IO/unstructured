# End 2 End tests for 15 types
from bs4 import BeautifulSoup

from unstructured.documents.elements import (
    ElementMetadata,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.partition.html.html_utils import indent_html
from unstructured.partition.html.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology_element,
    unstructured_elements_to_ontology,
)


def _wrap_in_body_and_page(html_code):
    return (
        f'<body class="Document" id="0">'
        f'<div class="Page" data-page-number="1" id="1">'
        f"{html_code}"
        f"</div>"
        f"</body>"
    )


_page_elements = [
    Text(
        text="",
        element_id="1",
        detection_origin="vlm_partitioner",
        metadata=ElementMetadata(
            text_as_html='<div class="Page" data-page-number="1" id="1" />', parent_id="0"
        ),
    ),
]


def _assert_elements_equal(actual_elements, expected_elements):
    assert len(actual_elements) == len(expected_elements)
    for actual, expected in zip(actual_elements, expected_elements):
        assert actual == expected, f"Actual: {actual}, Expected: {expected}"
        assert actual._element_id == expected._element_id, f"Actual: {actual}, Expected: {expected}"
        assert (
            actual.metadata.detection_origin == expected.metadata.detection_origin
        ), f"Actual: {actual}, Expected: {expected}"
        # Not all elements are considered be __eq__ Elements method
        assert (
            actual.metadata.parent_id == expected.metadata.parent_id
        ), f"Actual: {actual}, Expected: {expected}"
        assert (
            actual.metadata.text_as_html == expected.metadata.text_as_html
        ), f"Actual: {actual}, Expected: {expected}"


def _parse_to_unstructured_elements_and_back_to_html(html_as_str: str):
    html_tag = BeautifulSoup(html_as_str, "html.parser").find()
    ontology = parse_html_to_ontology_element(html_tag)
    unstructured_elements = ontology_to_unstructured_elements(ontology)
    parsed_ontology = unstructured_elements_to_ontology(unstructured_elements)
    return unstructured_elements, parsed_ontology


def test_simple_narrative_text_with_id():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <p class="NarrativeText" id="73cd7b4a-2444-4910-87a4-138117dfaab9">
     DEALER ONLY
    </p>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )

    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        NarrativeText(
            text="DEALER ONLY",
            element_id="73cd7b4a-2444-4910-87a4-138117dfaab9",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<p class="NarrativeText" '
                'id="73cd7b4a-2444-4910-87a4-138117dfaab9">DEALER ONLY </p>',
                parent_id="1",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_input_with_radio_button_checked():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
       <input class="RadioButton" id="2" name="health-comparison" type="radio" checked/>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )

    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        Text(
            text="",
            detection_origin="vlm_partitioner",
            element_id="2",
            metadata=ElementMetadata(
                text_as_html='<input class="RadioButton" '
                'id="2" name="health-comparison" '
                'type="radio" checked />',
                parent_id="1",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_multiple_elements():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <p class="Paragraph" id='2'>
        About the same
    </p>
    <input class="RadioButton" name="health-comparison" type="radio" id='3'/>
    <p class="Paragraph" id='4'>
        Some text
    </p>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )

    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        NarrativeText(
            text="About the same",
            detection_origin="vlm_partitioner",
            element_id="2",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph" id="2">About the same </p>',
                parent_id="1",
            ),
        ),
        Text(
            text="",
            detection_origin="vlm_partitioner",
            element_id="3",
            metadata=ElementMetadata(
                text_as_html='<input class="RadioButton" '
                'name="health-comparison" '
                'type="radio" id="3" />',
                parent_id="1",
            ),
        ),
        NarrativeText(
            element_id="4",
            text="Some text",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph" ' 'id="4">Some text </p>',
                parent_id="1",
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_multiple_pages():
    # language=HTML
    html_as_str = """
    <body class="Document" id='0'>
        <div class="Page" data-page-number="1" id='1'>
            <p class="Paragraph" id='2'>
                Some text
            </p>
        </div>
        <div class="Page" data-page-number="2" id='3'>
            <p class="Paragraph" id='4'>
                Another text
            </p>
        </div>
    </body>
    """

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )

    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html

    expected_elements = [
        Text(
            text="",
            element_id="1",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<div class="Page" data-page-number="1" id="1" />', parent_id="0"
            ),
        ),
        NarrativeText(
            text="Some text",
            detection_origin="vlm_partitioner",
            element_id="2",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph" id="2">Some text </p>', parent_id="1"
            ),
        ),
        Text(
            text="",
            element_id="3",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<div class="Page" data-page-number="2" id="3" />', parent_id="0"
            ),
        ),
        NarrativeText(
            text="Another text",
            detection_origin="vlm_partitioner",
            element_id="4",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph" id="4">Another text </p>', parent_id="3"
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_forms():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
        <form class="Form" id="2">
            <label class="FormField" for="option1" id="3">
                <input class="FormFieldValue" type="radio"
                 name="options" value="2" id="4" checked>
                <p class="Paragraph" id="5">
                    Option 1 (Checked)
                </p>
            </label>
        </form>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )

    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")
    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        Text(
            text="Option 1 (Checked)",
            element_id="2",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html=""
                '<form class="Form" id="2"> '
                '<label class="FormField" '
                'for="option1" id="3"> '
                '<input class="FormFieldValue" type="radio" '
                'name="options" value="2" id="4" checked />'
                '<p class="Paragraph" id="5">'
                "Option 1 (Checked) "
                "</p></label></form>",
                parent_id="1",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_table():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <table class="Table" id="2">
        <tbody class="TableBody" id="3">
            <tr class="TableRow" id="4">
              <td class="TableCell" id="5">
                Fair Value1
              </td>
              <th class="TableCellHeader" rowspan="2" id="6">
                Fair Value2
             </th>
           </tr>
       </tbody>
    </table>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )
    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        Table(
            text="Fair Value1 Fair Value2",
            detection_origin="vlm_partitioner",
            element_id="2",
            metadata=ElementMetadata(
                text_as_html='<table class="Table" id="2"> '
                '<tbody class="TableBody" id="3"> '
                '<tr class="TableRow" id="4"> '
                '<td class="TableCell" id="5">'
                "Fair Value1 "
                "</td>"
                '<th class="TableCellHeader" rowspan="2" id="6">'
                "Fair Value2 "
                "</th></tr></tbody></table>",
                parent_id="1",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_very_nested_structure_is_preserved():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <section class='Section' id='11'>
        <div class='Column' id='2'>
            <header class='Header' id='3'>
                <h1 class='Title' id='10'>
                    Title
                </h1>
            </header>
        </div>
    </section>
    <div class='Column' id='4'>
            <blockquote class="Quote" id='5'>
                <p class="Paragraph" id='6'>
                    Clever Quote
                </p>
            </blockquote id='7'>
            <div class='Footnote' id='8'>
                <span class='UncategorizedText' id='9'>
                    Uncategorized footnote text
                </span>
            </div>
    </div>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )
    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        Text(
            text="",
            element_id="11",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<section class="Section" id="11" />', parent_id="1"
            ),
        ),
        Text(
            text="",
            element_id="2",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(text_as_html='<div class="Column" id="2" />', parent_id="11"),
        ),
        Text(
            text="",
            element_id="3",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<header class="Header" id="3" />', parent_id="2"
            ),
        ),
        Title(
            text="Title",
            element_id="10",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<h1 class="Title" id="10">Title </h1>', parent_id="3"
            ),
        ),
        Text(
            text="",
            element_id="4",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(text_as_html='<div class="Column" id="4" />', parent_id="1"),
        ),
        NarrativeText(
            text="Clever Quote",
            element_id="5",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<blockquote class="Quote" id="5"> '
                '<p class="Paragraph" id="6">'
                "Clever Quote "
                "</p>"
                "</blockquote>",
                parent_id="4",
            ),
        ),
        Text(
            text="Uncategorized footnote text",
            element_id="8",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<div class="Footnote" id="8"> '
                '<span class="UncategorizedText" id="9">'
                "Uncategorized footnote text "
                "</span>"
                "</div>",
                parent_id="4",
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_ordered_list():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <ul class="UnorderedList" id='2'>
        <li class="ListItem" id='3'>
            Item 1
        </li>
        <li class="ListItem" id='4'>
            Item 2
        </li>
        <li class="ListItem" id='5'>
            Item 3
        </li>
    </ul>
    """
    )

    unstructured_elements, parsed_ontology = _parse_to_unstructured_elements_and_back_to_html(
        html_as_str
    )
    expected_html = indent_html(html_as_str, html_parser="html.parser")
    parsed_html = indent_html(parsed_ontology.to_html(), html_parser="html.parser")

    assert expected_html == parsed_html
    expected_elements = _page_elements + [
        Text(
            text="Item 1 Item 2 Item 3",
            element_id="2",
            detection_origin="vlm_partitioner",
            metadata=ElementMetadata(
                text_as_html='<ul class="UnorderedList" id="2"> '
                '<li class="ListItem" id="3">'
                "Item 1 "
                "</li>"
                '<li class="ListItem" id="4">'
                "Item 2 </li>"
                '<li class="ListItem" id="5">'
                "Item 3 "
                "</li></ul>",
                parent_id="1",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)
