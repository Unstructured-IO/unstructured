import pytest

from unstructured.partition.html import partition_html


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_opt_in_extracts_authored_form_labels_and_values(version):
    html = (
        '<body class="Document"><div class="Page"><form>'
        '<p class="NarrativeText"><label>Name: <input value="Ada"></label></p>'
        '<p class="NarrativeText">Country: <select><option>France</option>'
        "<option selected>Japan</option></select></p>"
        '<p class="NarrativeText">Notes: <textarea>Use clear words.</textarea></p>'
        "</form></div></body>"
    )

    elements = partition_html(
        text=html, include_form_values=True, html_parser_version=version, languages=["eng"]
    )

    assert [" ".join(e.text.split()) for e in elements if e.text] == [
        "Name: Ada",
        "Country: Japan",
        "Notes: Use clear words.",
    ]


def test_forms_remain_excluded_by_default():
    elements = partition_html(
        text='<div>Before<form><label>Name<input value="Ada"></label></form>After</div>',
        languages=["eng"],
    )

    assert all("Ada" not in e.text and "Name" not in e.text for e in elements)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("text", "Ada"),
        ("email", "ada@example.com"),
        ("search", "query"),
        ("tel", "+1 555 0100"),
        ("url", "https://example.com"),
        ("number", "42.5"),
        ("date", "2026-11-21"),
    ],
)
def test_textual_input_values_are_retained(kind, value):
    elements = partition_html(
        text=f'<p>Field: <input type="{kind}" value="{value}"></p>',
        include_form_values=True,
        languages=["eng"],
    )

    assert elements[0].text == f"Field: {value}"


def test_values_containing_markup_stay_text():
    elements = partition_html(
        text='<p>Example: <input value="&lt;safe&gt;"></p>',
        include_form_values=True,
        languages=["eng"],
    )

    assert elements[0].text == "Example: <safe>"


@pytest.mark.parametrize("kind", ["password", "hidden", "file", "submit", "reset", "button"])
def test_nontext_controls_do_not_expose_value_attributes(kind):
    elements = partition_html(
        text=f'<p>Field: <input type="{kind}" value="Never expose"></p>',
        include_form_values=True,
        languages=["eng"],
    )

    assert [e.text for e in elements] == ["Field:"]


@pytest.mark.parametrize(
    ("select", "expected"),
    [
        (
            "<select><option disabled>Unavailable</option><option>First usable</option></select>",
            "First usable",
        ),
        ("<select><option selected>First</option><option selected>Last</option></select>", "Last"),
        (
            "<select multiple><option selected>A</option><option>B</option>"
            "<option selected>C</option></select>",
            "A; C",
        ),
        (
            "<select><optgroup disabled><option>A</option></optgroup>"
            '<option label="Label">Value</option></select>',
            "Label",
        ),
        ('<select size="invalid"><option>First</option><option>Second</option></select>', "First"),
    ],
)
def test_select_extracts_the_selected_label_instead_of_the_entire_option_list(select, expected):
    elements = partition_html(
        text=f"<p>Choice: {select}</p>", include_form_values=True, languages=["eng"]
    )

    assert elements[0].text == f"Choice: {expected}"


def test_hidden_forms_and_controls_are_not_materialized():
    html = (
        '<div>Before<form hidden><label>Secret<input value="hidden form"></label></form>'
        '<p>Visible <input hidden value="hidden input"></p>After</div>'
    )

    elements = partition_html(text=html, include_form_values=True, languages=["eng"])

    text = " ".join(e.text for e in elements)
    assert "Visible" in text
    assert "Secret" not in text
    assert "hidden" not in text
