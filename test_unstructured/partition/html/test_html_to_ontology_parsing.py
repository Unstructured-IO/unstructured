from bs4 import BeautifulSoup

from unstructured.documents.ontology import Form, FormFieldValue, OntologyElement, Page
from unstructured.partition.html.html_utils import indent_html
from unstructured.partition.html.transformations import RECURSION_LIMIT, parse_html_to_ontology


def _wrap_with_body(html: str) -> str:
    return f'<body class="Document">{html}</body>'


def remove_all_ids(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup.find_all(True):
        if tag.has_attr("id"):
            del tag["id"]
    return str(soup)


def test_wrong_html_parser_causes_paragraph_to_be_nested_in_div():
    # This test would fail if html5lib parser would be applied on the input HTML.
    # It would result in Page: <p></p> <address></address>
    #         instead of Page: <p><address></address></p>

    # language=HTML
    input_html = """
    <div class="Page">
    <p class="NarrativeText">
     <address class="Address">
      Mountain View, California
     </address>
    </p>
    </div>
    """
    page = parse_html_to_ontology(input_html)

    assert len(page.children) == 1
    narrative_text = page.children[0]

    assert len(narrative_text.children) == 1
    address = narrative_text.children[0]

    assert address.text == "Mountain View, California"


def test_when_class_is_missing_it_can_be_inferred_from_type():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <aside>Some text</aside>
    </div>
    """
    )

    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <aside class='Sidebar'><p class='Paragraph'>Some text</p></aside>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_when_class_is_wrong_tag_name_is_overwritten():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <p class='Sidebar'>Some text</p>
    </div>
    """
    )

    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <aside class='Sidebar'><p class='Paragraph'>Some text</p></aside>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_when_tag_not_supported_by_ontology_and_wrong_then_consider_them_text():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <newtag class="wrongclass">Some text
        </newtag>
    </div>
    """
    )

    base_html = indent_html(base_html)

    # TODO (Pluto): Maybe it should be considered as plain text?

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <span class="UncategorizedText">Some text
        </span>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_div_are_ignored_when_no_attrs():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
      <div>
           <input class="RadioButton" name="health-comparison" type="radio"/>
      </div>
    </div>
    """
    )

    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
       <input class="RadioButton" name="health-comparison" type="radio"/>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_ids_are_preserved():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
      <div style="background-color: lightblue" id="important_div">
           <input class="RadioButton" name="health-comparison" type="radio"/>
      </div>
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
      <div class="UncategorizedText" style="background-color: lightblue" id="important_div">
           <input class="RadioButton" name="health-comparison" type="radio"/>
      </div>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)

    page = ontology.children[0]
    div_obj = page.children[0]
    assert div_obj.additional_attributes["id"] == "important_div"


def test_br_is_not_considered_uncategorized_text():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <br/>
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <br/>
    </div>
    """
    )

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_text_without_tag_is_marked_as_uncategorized_text_when_there_are_other_elements():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        About the same
        <input class="RadioButton" name="health-comparison" type="radio"/>
        Some text
    </div>
    """
    )

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <p class="Paragraph">
            About the same
        </p>
        <input class="RadioButton" name="health-comparison" type="radio"/>
        <p class="Paragraph">
            Some text
        </p>
    </div>
    """
    )
    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_keyword_only_attributes_are_preserved_during_mapping():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <input class="FormFieldValue" type="radio" name="options" value="2" checked>
    """
    )  # noqa: E501
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <input class="FormFieldValue" type="radio" name="options" value="2" checked>
    """
    )  # noqa: E501

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_when_unknown_element_keyword_only_attributes_are_preserved_during_mapping():
    # <input> can be assigned to multiple classes so it is not clear what it is
    #  thus we assign it to UncategorizedText

    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <form class="Form">
            <label class="FormField" for="option1">
                <input type="radio" name="option1" value="2" checked>
                <span class="UncategorizedText">
                    Option 1 (Checked)
                </span>
            </label>
        </form>
    </div>
    """
    )
    base_html = indent_html(base_html)

    # TODO(Pluto): Maybe tag also should be overwritten? Or just leave it as it is?
    #  We classify <input> as UncategorizedText but all the text is preserved
    #  for UnstructuredElement so it make sense now as well

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <form class="Form">
            <label class="FormField" for="option1">
                <input class="Checkbox" type="radio" name="option1" value="2" checked />
                <span class="UncategorizedText">
                    Option 1 (Checked)
                </span>
            </label>
        </form>
    </div>
    """
    )  # noqa: E501

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_broken_cell_is_not_raising_error():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <table class="Table">
            <tbody class="TableBody">
                <tr class="TableRow">
                   <td class="TableCell&gt;11,442,231&lt;/td&gt;&lt;td class=" tablecell"="">
                    83.64 GiB
                   </td>
                  <th class="TableCellHeader" rowspan="2">
                    Fair Value
                 </th>
               </tr>
           </tbody>
        </table>
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <table class="Table">
            <tbody>
                <tr>
                   <td tablecell&quot;="">
                    83.64 GiB
                   </td>
                  <th rowspan="2">
                    Fair Value
                 </th>
               </tr>
           </tbody>
        </table>
    </div>
    """
    )

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_table():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
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
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <table class="Table">
            <tbody>
                <tr>
                  <td>
                    Fair Value1
                  </td>
                  <th rowspan="2">
                    Fair Value2
                 </th>
               </tr>
           </tbody>
        </table>
    </div>
    """
    )

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_table_and_time():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        <table class="Table">
            <thead class='TableHeader'>
                <tr class="TableRow">
                    <th class="TableCellHeader"  colspan="6">
                        Carrying Value
                    </th>
                </tr>
            </thead>
            <tbody class='TableBody'>
                <tr class="TableRow">
                    <td class="TableCell" colspan="5">
                        <time class="CalendarDate">
                            June 30, 2023
                        </time>
                    </td>
                <td class="TableCell">
                    <span class="Currency">
                        $—
                    </span>
                </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <table class="Table">
            <thead>
                <tr>
                    <th colspan="6">
                        Carrying Value
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="5">
                            June 30, 2023
                    </td>
                <td>
                        $—
                </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    )

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_malformed_html():
    # language=HTML
    input_html = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    <html>
      <head>
        <title>Super Malformed HTML</title>
      </head>
      <body class="Document">
        <!-- Unclosed comment
        <div class=>
          <p>Paragraph with missing closing angle bracket
        <div>
          <span>
            <p>Improperly nested paragraph within a span</span>
          </p>
        </div>
        <script>
          var x = "Unclosed script tag example;
        </script>
        <p>Paragraph with invalid characters: � � �</p>
      </div>
    </html>
    """

    # Such malformed HTML won't be returned by html_partitioning as it uses html5lib parser
    # to imitate the same behaviour it will be first parsed the same way

    input_html = indent_html(input_html, html_parser="html5lib")

    # Ontology has 1 element and everything inside is just Text
    # language=HTML
    expected_html = """
    <body class="Document">

      <p class="Paragraph">
     Unclosed comment
     <div class="">
      <p>
       Paragraph with missing closing angle bracket
       <div>
        <span>
         <p>
          Improperly nested paragraph within a span
         </p>
        </span>
       </div>
      </p>
     </div>
     <script>
      var x = "Unclosed script tag example;
     </script>
     <p>
      Paragraph with invalid characters: � � �
     </p>
     </p>
    </body>
    """

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(input_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_text_is_wrapped_inside_layout_element():
    # language=HTML
    base_html = _wrap_with_body(
        """
    <div class="Page">
        Text
    </div>
    """
    )
    base_html = indent_html(base_html)

    # language=HTML
    expected_html = _wrap_with_body(
        """
    <div class="Page">
        <p class='Paragraph'>Text</p>
    </div>
    """
    )

    expected_html = indent_html(expected_html)

    ontology: OntologyElement = parse_html_to_ontology(base_html)
    parsed_ontology = indent_html(remove_all_ids(ontology.to_html()))

    assert parsed_ontology == expected_html


def test_text_in_form_field_value():
    # language=HTML
    input_html = """
    <div class="Page">
    <input class="FormFieldValue" value="Random Input Value"/>
    </div>
    """
    page = parse_html_to_ontology(input_html)

    assert len(page.children) == 1
    form_field_value = page.children[0]
    assert form_field_value.text == ""
    assert form_field_value.to_text() == "Random Input Value"


def test_text_in_form_field_value_with_null_value():
    # language=HTML
    input_html = """
    <div class="Page">
    <input class="FormFieldValue" value=""/>
    </div>
    """
    page = parse_html_to_ontology(input_html)

    assert len(page.children) == 1
    form_field_value = page.children[0]
    assert form_field_value.text == ""
    assert form_field_value.to_text() == ""


def test_to_text_when_form_field():
    ontology = Page(
        children=[
            Form(
                tag="input",
                additional_attributes={"value": "Random Input Value"},
                children=[
                    FormFieldValue(
                        tag="input",
                        additional_attributes={"value": "Random Input Value"},
                    )
                ],
            )
        ]
    )
    assert ontology.to_text(add_children=True) == "Random Input Value"


def test_recursion_limit_is_limiting_parsing():
    # language=HTML
    broken_html = "some text"
    for i in range(100):
        broken_html = f"<p class='Paragraph'>{broken_html}</p>"
    broken_html = _wrap_with_body(broken_html)
    ontology = parse_html_to_ontology(broken_html)

    iterator = 1
    last_child = ontology.children[0]
    while last_child.children:
        last_child = last_child.children[0]
        iterator += 1
    assert last_child.text.startswith('<p class="Paragraph">')
    assert iterator == RECURSION_LIMIT


def test_get_text_when_recursion_limit_activated():
    broken_html = "some text"
    for i in range(100):
        broken_html = f"<p class='Paragraph'>{broken_html}</p>"
    broken_html = _wrap_with_body(broken_html)
    ontology = parse_html_to_ontology(broken_html)

    last_child = ontology.children[0]
    while last_child.children:
        last_child = last_child.children[0]

    assert last_child.to_text() == "some text"
