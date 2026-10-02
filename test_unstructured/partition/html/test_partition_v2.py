from unstructured.partition.html import partition_html


def _by_text(elements):
    return {(e.text or ""): e for e in elements}


def test_category_depth_follows_heading_level_on_a_multi_level_page():
    """ML-1328 AC1/AC3: a heading's `category_depth` is its heading level (h1->0, h2->1, h3->2),
    and `parent_id` chains each subsection under its enclosing section heading."""
    # language=HTML
    html = """
    <body class="Document">
        <div class="Page" data-page-number="1">
            <h1 class="Title">Cost Share Summary</h1>
            <p class="NarrativeText">Intro paragraph.</p>
            <h2 class="Heading">Accumulation Period</h2>
            <p class="NarrativeText">Accumulation body.</p>
            <h2 class="Heading">Cost Share Summary Tables by Benefit</h2>
            <h3 class="Heading">How to read the Cost Share summary tables</h3>
            <p class="NarrativeText">How-to body.</p>
        </div>
    </body>
    """
    elements = partition_html(text=html, html_parser_version="v2", unique_element_ids=False)
    by_text = _by_text(elements)

    section = by_text["Cost Share Summary"]
    subsection_a = by_text["Accumulation Period"]
    subsection_b = by_text["Cost Share Summary Tables by Benefit"]
    sub_subsection = by_text["How to read the Cost Share summary tables"]

    # -- depth tracks heading level --
    assert section.metadata.category_depth == 0
    assert subsection_a.metadata.category_depth == 1
    assert subsection_b.metadata.category_depth == 1
    assert sub_subsection.metadata.category_depth == 2

    # -- parent_id chains section -> subsection -> sub-subsection --
    assert subsection_a.metadata.parent_id == section.id
    assert subsection_b.metadata.parent_id == section.id
    assert sub_subsection.metadata.parent_id == subsection_b.id

    # -- body text parents to its enclosing heading, not the page/column container --
    assert by_text["How-to body."].metadata.parent_id == sub_subsection.id

    # -- v2's defining behavior is preserved: every element keeps its text_as_html --
    assert all(e.metadata.text_as_html for e in elements)


def test_category_depth_does_not_change_with_multi_column_layout():
    """ML-1328 AC2: the same heading reads the same `category_depth` whether the page is single- or
    multi-column. Layout nesting (Page -> Column) must not bump the depth."""
    # language=HTML
    single_column = """
    <body class="Document">
        <div class="Page" data-page-number="1">
            <h1 class="Title">Introduction</h1>
            <h2 class="Heading">About</h2>
        </div>
    </body>
    """
    two_column = """
    <body class="Document">
        <div class="Page" data-page-number="1">
            <div class="Column">
                <h1 class="Title">Introduction</h1>
                <h2 class="Heading">About</h2>
            </div>
            <div class="Column">
                <h2 class="Heading">Contact</h2>
            </div>
        </div>
    </body>
    """
    single = _by_text(
        partition_html(text=single_column, html_parser_version="v2", unique_element_ids=False)
    )
    multi = _by_text(
        partition_html(text=two_column, html_parser_version="v2", unique_element_ids=False)
    )

    # -- identical depth across layouts: h1 -> 0, h2 -> 1 -- column wrapping is irrelevant --
    assert single["Introduction"].metadata.category_depth == 0
    assert multi["Introduction"].metadata.category_depth == 0
    assert single["About"].metadata.category_depth == 1
    assert multi["About"].metadata.category_depth == 1
    assert multi["Contact"].metadata.category_depth == 1


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
