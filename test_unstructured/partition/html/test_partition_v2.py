from unstructured.partition.html import partition_html


def test_alternative_image_text_can_be_included():
    # language=HTML
    html = """
    <div class="Page">
        <img src="my-logo.png" alt="ALT TEXT Logo"/>
    </div>
    """
    _, image_to_text_alt_mode = partition_html(
        text=html,
        image_alt_mode="to_text",
        html_parser_version="v2",
    )
    assert "ALT TEXT Logo" in image_to_text_alt_mode.text

    _, image_none_alt_mode = partition_html(
        text=html,
        image_alt_mode=None,
        html_parser_version="v2",
    )
    assert "ALT TEXT Logo" not in image_none_alt_mode.text


def test_alternative_image_text_can_be_included_when_nested_in_paragraph():
    # language=HTML
    html = """
    <div class="Page">
        <p class="Paragraph">
            <img src="my-logo.png" alt="ALT TEXT Logo"/>
        </p>
    </div>
    """
    _, paragraph_to_text_alt_mode = partition_html(
        text=html,
        image_alt_mode="to_text",
        html_parser_version="v2",
    )
    assert "ALT TEXT Logo" in paragraph_to_text_alt_mode.text

    _, paragraph_none_alt_mode = partition_html(
        text=html,
        image_alt_mode=None,
        html_parser_version="v2",
    )
    assert "ALT TEXT Logo" not in paragraph_none_alt_mode.text


def test_attr_and_html_inside_table_cell_is_kept():
    # language=HTML
    html = """
    <div class="Page">
        <table class="Table">
            <tbody>
                <tr>
                    <td colspan="2">
                        Some text
                    </td>
                    <td>
                        <input checked="" class="Checkbox" type="checkbox"/>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    page, table = partition_html(
        text=html,
        image_alt_mode="to_text",
        html_parser_version="v2",
    )

    assert (
        '<input checked="" class="Checkbox" type="checkbox"/>' in table.metadata.text_as_html
    )  # class is removed
    assert 'colspan="2"' in table.metadata.text_as_html
