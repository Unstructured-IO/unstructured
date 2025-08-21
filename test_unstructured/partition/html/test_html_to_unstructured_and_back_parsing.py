# End 2 End tests for 15 types

from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    Header,
    NarrativeText,
    Table,
    Text,
)
from unstructured.documents.ontology import Address, Paragraph
from unstructured.partition.html.html_utils import indent_html
from unstructured.partition.html.partition import partition_html
from unstructured.partition.html.transformations import (
    ontology_to_unstructured_elements,
    parse_html_to_ontology,
    unstructured_elements_to_ontology,
)


def _wrap_in_body_and_page(html_code):
    return (
        f'<body class="Document">'
        f'<div class="Page" data-page-number="1">'
        f"{html_code}"
        f"</div>"
        f"</body>"
    )


_page_elements = [
    Text(
        text="",
        metadata=ElementMetadata(text_as_html='<div class="Page" data-page-number="1" />'),
    ),
]


def _assert_elements_equal(actual_elements: list[Element], expected_elements: list[Element]):
    assert len(actual_elements) == len(expected_elements)
    for actual, expected in zip(actual_elements, expected_elements):
        assert actual == expected, f"Actual: {actual}, Expected: {expected}"
        # Not all elements are considered be __eq__ Elements method
        actual_html = indent_html(actual.metadata.text_as_html, html_parser="html.parser")
        expected_html = indent_html(expected.metadata.text_as_html, html_parser="html.parser")
        assert actual_html == expected_html, f"Actual: {actual_html}, Expected: {expected_html}"


def _parse_to_unstructured_elements_and_back_to_html(html_as_str: str):
    unstructured_elements = partition_html(
        text=html_as_str, add_img_alt_text=False, html_parser_version="v2", unique_element_ids=True
    )
    parsed_ontology = unstructured_elements_to_ontology(unstructured_elements)
    return unstructured_elements, parsed_ontology


def test_simple_narrative_text_with_id():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <p class="NarrativeText">
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
            metadata=ElementMetadata(
                text_as_html='<p class="NarrativeText">DEALER ONLY</p>',
            ),
        )
    ]

    _assert_elements_equal(unstructured_elements, expected_elements)


def test_input_with_radio_button_checked():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
       <input class="RadioButton" name="health-comparison" type="radio" checked/>
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
            metadata=ElementMetadata(
                text_as_html=(
                    '<input class="RadioButton" name="health-comparison"' 'type="radio" checked />'
                ),
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_multiple_elements():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <p class="Paragraph">
        About the same
    </p>
    <input class="RadioButton" name="health-comparison" type="radio"/>
    <p class="Paragraph">
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
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph">About the same</p>',
            ),
        ),
        Text(
            text="",
            metadata=ElementMetadata(
                text_as_html='<input class="RadioButton" name="health-comparison" type="radio" />',
            ),
        ),
        NarrativeText(
            text="Some text",
            metadata=ElementMetadata(
                text_as_html='<p class="Paragraph">Some text</p>',
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_multiple_pages():
    # language=HTML
    html_as_str = """
    <body class="Document">
        <div class="Page" data-page-number="1">
            <p class="Paragraph">
                Some text
            </p>
        </div>
        <div class="Page" data-page-number="2">
            <p class="Paragraph">
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
            metadata=ElementMetadata(text_as_html='<div class="Page" data-page-number="1" />'),
        ),
        NarrativeText(
            text="Some text",
            metadata=ElementMetadata(text_as_html='<p class="Paragraph">Some text</p>'),
        ),
        Text(
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Page" data-page-number="2" />'),
        ),
        NarrativeText(
            text="Another text",
            metadata=ElementMetadata(text_as_html='<p class="Paragraph">Another text</p>'),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_forms():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
        <form class="Form">
            <label class="FormField" for="option1">
                <input class="FormFieldValue" type="radio"
                 name="options" value="2" checked>
                <p class="Paragraph">
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
            text="2 Option 1 (Checked)",
            metadata=ElementMetadata(
                text_as_html=""
                '<form class="Form">'
                '<label class="FormField" '
                'for="option1">'
                '<input class="FormFieldValue" type="radio" '
                'name="options" value="2" checked />'
                '<p class="Paragraph">'
                "Option 1 (Checked)"
                "</p></label></form>",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_table():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <table class="Table">
        <tbody class="TableBody">
            <tr class="TableRow">
              <td class="TableCell">
                Fair Value1
              </td>
              <th class="TableCellHeader" rowspan="2">
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

    expected_elements = _page_elements + [
        Table(
            text="Fair Value1 Fair Value2",
            metadata=ElementMetadata(
                text_as_html='<table class="Table">'
                "<tbody>"
                "<tr>"
                "<td>"
                "Fair Value1"
                "</td>"
                '<th rowspan="2">'
                "Fair Value2"
                "</th></tr></tbody></table>",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_very_nested_structure_is_preserved():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <section class='Section'>
        <div class='Column'>
            <header class='Header'>
                <h1 class='Title'>
                    Title
                </h1>
            </header>
        </div>
    </section>
    <div class='Column'>
            <header class='Header'>
                Page 1
            </header>
            <blockquote class="Quote">
                <p class="Paragraph">
                    Clever Quote
                </p>
            </blockquote>
            <div class='Footnote'>
                <span class='UncategorizedText'>
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
            metadata=ElementMetadata(text_as_html='<section class="Section" />'),
        ),
        Text(
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Column" />'),
        ),
        Header(
            text="Title",
            metadata=ElementMetadata(
                text_as_html='<header class="Header"><h1 class="Title">Title</h1></header>'
            ),
        ),
        Text(
            text="",
            metadata=ElementMetadata(text_as_html='<div class="Column" />'),
        ),
        Header(
            text="Page 1",
            metadata=ElementMetadata(text_as_html='<header class="Header">Page 1</header>'),
        ),
        NarrativeText(
            text="Clever Quote",
            metadata=ElementMetadata(
                text_as_html='<blockquote class="Quote">'
                '<p class="Paragraph">'
                "Clever Quote"
                "</p>"
                "</blockquote>",
            ),
        ),
        Text(
            text="Uncategorized footnote text",
            metadata=ElementMetadata(
                text_as_html='<div class="Footnote">'
                '<span class="UncategorizedText">'
                "Uncategorized footnote text"
                "</span>"
                "</div>",
            ),
        ),
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_ordered_list():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
    <ul class="UnorderedList">
        <li class="ListItem">
            Item 1
        </li>
        <li class="ListItem">
            Item 2
        </li>
        <li class="ListItem">
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
            metadata=ElementMetadata(
                text_as_html='<ul class="UnorderedList">'
                '<li class="ListItem">'
                "Item 1"
                "</li>"
                '<li class="ListItem">'
                "Item 2</li>"
                '<li class="ListItem">'
                "Item 3"
                "</li></ul>",
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_squeezed_elements_are_parsed_back():
    # language=HTML
    html_as_str = _wrap_in_body_and_page(
        """
       <p class="NarrativeText">
        Table of Contents
       </p>
       <address class="Address">
        68 Prince Street Palmdale, CA 93550
       </address>
       <a class="Hyperlink">
        www.google.com
       </a>
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
            text="Table of Contents 68 Prince Street Palmdale, CA 93550 www.google.com",
            metadata=ElementMetadata(
                text_as_html='<p class="NarrativeText">Table of Contents</p>'
                '<address class="Address">'
                "68 Prince Street Palmdale, CA 93550"
                "</address>"
                '<a class="Hyperlink">www.google.com</a>',
            ),
        )
    ]
    _assert_elements_equal(unstructured_elements, expected_elements)


def test_inline_elements_are_squeezed_when_text_wrapped_into_paragraphs():
    # language=HTML
    base_html = """
        <div class="Page">
            About the same
            <address class="Address">
                1356 Hornor Avenue Oklahoma
            </address>
            Some text
        </div>
        """
    # Such HTML is transformed into Page: [Pargraph, Address, Paragraph]
    # We would like it to be parsed to UnstructuredElements as [Page, NarrativeText]

    ontology = parse_html_to_ontology(base_html)

    p1, address, p2 = ontology.children
    assert isinstance(p1, Paragraph)
    assert isinstance(address, Address)
    assert isinstance(p2, Paragraph)

    unstructured_elements = ontology_to_unstructured_elements(ontology)

    assert len(unstructured_elements) == 2
    assert isinstance(unstructured_elements[0], Text)
    assert isinstance(unstructured_elements[1], NarrativeText)


def test_alternate_text_from_image_is_passed():
    # language=HTML
    input_html = """
    <div class="Page">
    <table>
        <tr>
            <td rowspan="2">Example image nested in the table:</td>
            <td rowspan="2"><img src="my-logo.png" alt="ALT TEXT Logo"></td>
        </tr>
    </table>
    </div>add_img_alt_text
    """
    page = parse_html_to_ontology(input_html)
    unstructured_elements = ontology_to_unstructured_elements(page)
    assert len(unstructured_elements) == 2
    assert "ALT TEXT Logo" in unstructured_elements[1].text
