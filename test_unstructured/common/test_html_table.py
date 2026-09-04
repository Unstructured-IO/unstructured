# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.common.html_table` module."""

from __future__ import annotations

import pytest
from lxml.html import fragment_fromstring

from unstructured.common.html_table import (
    HtmlCell,
    HtmlRow,
    HtmlTable,
    collapse_matrix_of_keyed_cells_to_spans,
    htmlify_matrix_of_cell_texts,
    htmlify_matrix_of_spanned_cell_texts,
)


class Describe_htmlify_matrix_of_cell_texts:
    """Unit-test suite for `unstructured.common.html_table.htmlify_matrix_of_cell_texts()`."""

    def test_htmlify_matrix_handles_empty_cells(self):
        assert htmlify_matrix_of_cell_texts([["cell1", "", "cell3"], ["", "cell5", ""]]) == (
            "<table>"
            "<tr><td>cell1</td><td/><td>cell3</td></tr>"
            "<tr><td/><td>cell5</td><td/></tr>"
            "</table>"
        )

    def test_htmlify_matrix_handles_special_characters(self):
        assert htmlify_matrix_of_cell_texts([['<>&"', "newline\n"]]) == (
            "<table><tr><td>&lt;&gt;&amp;&quot;</td><td>newline<br/></td></tr></table>"
        )

    def test_htmlify_matrix_handles_multiple_rows_and_cells(self):
        assert htmlify_matrix_of_cell_texts([["cell1", "cell2"], ["cell3", "cell4"]]) == (
            "<table>"
            "<tr><td>cell1</td><td>cell2</td></tr>"
            "<tr><td>cell3</td><td>cell4</td></tr>"
            "</table>"
        )

    def test_htmlify_matrix_handles_empty_matrix(self):
        assert htmlify_matrix_of_cell_texts([]) == ""


class Describe_htmlify_matrix_of_spanned_cell_texts:
    """Unit-test suite for `html_table.htmlify_matrix_of_spanned_cell_texts()`."""

    def it_emits_plain_cells_when_no_span_is_greater_than_1(self):
        assert htmlify_matrix_of_spanned_cell_texts(
            [[("a", 1, 1), ("b", 1, 1)], [("c", 1, 1), ("d", 1, 1)]]
        ) == ("<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>")

    def it_emits_colspan_and_rowspan_attributes_only_when_greater_than_1(self):
        assert htmlify_matrix_of_spanned_cell_texts([[("a", 2, 3)], [("b", 1, 1)]]) == (
            '<table><tr><td colspan="2" rowspan="3">a</td></tr><tr><td>b</td></tr></table>'
        )

    def it_emits_a_void_td_for_an_empty_spanned_cell(self):
        assert htmlify_matrix_of_spanned_cell_texts([[("", 2, 1)]]) == (
            '<table><tr><td colspan="2"/></tr></table>'
        )

    def it_emits_an_empty_tr_for_a_row_entirely_consumed_by_a_rowspan(self):
        """A row with no originating cells still needs its own `<tr>`.

        HTML `rowspan` counts actual `<tr>` elements, not "rows that happened to have content";
        dropping this row would shift the column-placement of every row after it.
        """
        assert htmlify_matrix_of_spanned_cell_texts([[("a", 1, 2)], [], [("b", 1, 1)]]) == (
            '<table><tr><td rowspan="2">a</td></tr><tr></tr><tr><td>b</td></tr></table>'
        )

    def it_handles_an_empty_matrix(self):
        assert htmlify_matrix_of_spanned_cell_texts([]) == ""

    def it_renders_a_full_width_vertical_merge_via_the_full_collapse_and_render_pipeline(self):
        """Regression: `collapse_matrix_of_keyed_cells_to_spans()` and
        `htmlify_matrix_of_spanned_cell_texts()` were each unit-tested individually, but their
        interaction was not -- the collapse step legitimately produces an empty row for a grid-row
        entirely covered by a multi-column `rowspan`, and the render step must still emit a `<tr>`
        for it rather than suppressing it.
        """
        keyed_matrix = [
            [("a", "M"), ("a", "M")],
            [("a", "M"), ("a", "M")],
            [("c", "C1"), ("d", "C2")],
        ]
        spanned_matrix = collapse_matrix_of_keyed_cells_to_spans(keyed_matrix)
        assert spanned_matrix == [[("a", 2, 2)], [], [("c", 1, 1), ("d", 1, 1)]]
        assert htmlify_matrix_of_spanned_cell_texts(spanned_matrix) == (
            '<table><tr><td colspan="2" rowspan="2">a</td></tr>'
            "<tr></tr>"
            "<tr><td>c</td><td>d</td></tr></table>"
        )


class Describe_collapse_matrix_of_keyed_cells_to_spans:
    """Unit-test suite for `html_table.collapse_matrix_of_keyed_cells_to_spans()`."""

    def it_leaves_a_matrix_with_no_repeated_keys_unchanged(self):
        matrix = [[("a", 1), ("b", 2)], [("c", 3), ("d", 4)]]
        assert collapse_matrix_of_keyed_cells_to_spans(matrix) == [
            [("a", 1, 1), ("b", 1, 1)],
            [("c", 1, 1), ("d", 1, 1)],
        ]

    def it_collapses_a_horizontal_run_of_matching_keys_into_a_colspan(self):
        matrix = [[("a", 1), ("a", 1), ("b", 2)]]
        assert collapse_matrix_of_keyed_cells_to_spans(matrix) == [[("a", 2, 1), ("b", 1, 1)]]

    def it_collapses_a_vertical_run_of_matching_keys_into_a_rowspan(self):
        matrix = [[("a", 1)], [("a", 1)], [("b", 2)]]
        assert collapse_matrix_of_keyed_cells_to_spans(matrix) == [
            [("a", 1, 2)],
            [],
            [("b", 1, 1)],
        ]

    def it_collapses_a_rectangular_region_into_a_single_cell_with_colspan_and_rowspan(self):
        """Reproduces the docx-tables.docx merged-cell fixture geometry.

        +---+-------+
        | a | b     |
        |   +---+---+
        |   | c | d |
        +---+---+   |
        | e     |   |
        +-------+---+
        """
        matrix = [
            [("a", 1), ("b", 2), ("b", 2)],
            [("a", 1), ("c", 3), ("d", 4)],
            [("e", 5), ("e", 5), ("d", 4)],
        ]
        assert collapse_matrix_of_keyed_cells_to_spans(matrix) == [
            [("a", 1, 2), ("b", 2, 1)],
            [("c", 1, 1), ("d", 1, 2)],
            [("e", 2, 1)],
        ]

    def it_treats_distinct_keys_as_never_merged_even_when_their_text_matches(self):
        matrix = [[("", 1), ("", 2)]]
        assert collapse_matrix_of_keyed_cells_to_spans(matrix) == [
            [("", 1, 1), ("", 1, 1)],
        ]

    def it_handles_an_empty_matrix(self):
        assert collapse_matrix_of_keyed_cells_to_spans([]) == []


class DescribeHtmlTable:
    """Unit-test suite for `unstructured.common.html_table.HtmlTable`."""

    def it_can_construct_from_html_text(self):
        html_table = HtmlTable.from_html_text("<table><tr><td>foobar</td></tr></table>")

        assert isinstance(html_table, HtmlTable)
        assert html_table._table.tag == "table"

    @pytest.mark.parametrize(
        "html_text",
        [
            "<table><tr><td>foobar</td></tr></table>",
            "<body><table><tr><td>foobar</td></tr></table></body>",
            "<html><body><table><tr><td>foobar</td></tr></table></body></html>",
        ],
    )
    def it_can_find_a_table_wrapped_in_an_html_or_body_element(self, html_text: str):
        html_table = HtmlTable.from_html_text(html_text)

        assert isinstance(html_table, HtmlTable)
        assert html_table._table.tag == "table"

    def but_it_raises_when_no_table_element_is_present_in_the_html(self):
        with pytest.raises(ValueError, match="`html_text` contains no `<table>` element"):
            HtmlTable.from_html_text("<html><body><tr><td>foobar</td></tr></body></html>")

    def it_removes_any_attributes_present_on_the_table_element(self):
        html_table = HtmlTable.from_html_text(
            '<table border="1", class="foobar"><tr><td>foobar</td></tr></table>',
        )
        assert html_table.html == "<table><tr><td>foobar</td></tr></table>"

    def but_it_preserves_colspan_and_rowspan_as_structural_cell_attributes(self):
        html_table = HtmlTable.from_html_text(
            "<table>"
            "<tr><th colspan='2' class='hdr' style='x'>A</th>"
            "<th rowspan='2' id='foo'>B</th></tr>"
            "<tr><td colspan='2' rowspan='3' data-k='v'>C</td><td>D</td></tr>"
            "</table>"
        )
        table = fragment_fromstring(html_table.html)

        # -- colspan/rowspan survive compactification --
        assert table.xpath("./tr[1]/td[1]/@colspan") == ["2"]
        assert table.xpath("./tr[1]/td[2]/@rowspan") == ["2"]
        assert table.xpath("./tr[2]/td[1]/@colspan") == ["2"]
        assert table.xpath("./tr[2]/td[1]/@rowspan") == ["3"]
        # -- cosmetic / arbitrary attributes are still stripped --
        assert table.xpath("./tr[1]/td[1]/@class") == []
        assert table.xpath("./tr[1]/td[1]/@style") == []
        assert table.xpath("./tr[1]/td[2]/@id") == []
        assert table.xpath("./tr[2]/td[1]/@data-k") == []

    @pytest.mark.parametrize(
        "html_text",
        [
            "<table><thead><tr><td>foobar</td></tr></thead></table>",
            "<table><thead><tr><td>foobar</td></tr></thead><tbody></tbody></table>",
            "<table><tbody><tr><td>foobar</td></tr></tbody><tfoot></tfoot></table>",
        ],
    )
    def it_removes_any_thead_tbody_or_tfoot_elements_present_within_the_table_element(
        self, html_text: str
    ):
        html_table = HtmlTable.from_html_text(html_text)
        assert html_table.html == "<table><tr><td>foobar</td></tr></table>"

    def it_changes_any_th_elements_to_td_elements_for_cell_element_uniformity(self):
        html_table = HtmlTable.from_html_text(
            "<table>  <tr><th>a</th><th/><th>b</th></tr>  <tr><td/><td>c</td><td/></tr></table>"
        )
        assert html_table.html == (
            "<table><tr><td>a</td><td/><td>b</td></tr><tr><td/><td>c</td><td/></tr></table>"
        )

    def it_removes_any_extra_whitespace_between_elements_and_normalizes_whitespace_in_text(self):
        html_table = HtmlTable.from_html_text(
            "\n  <table>\n  <tr>\n    <td>\tabc   def\nghi </td>\n  </tr>\n</table>\n  ",
        )
        assert html_table.html == "<table><tr><td>abc def ghi</td></tr></table>"

    def it_preserves_tail_text_in_mixed_content_cells(self):
        """Tail text (between inline children) carries real content and must not be dropped."""
        html_table = HtmlTable.from_html_text(
            "<table><tr>"
            "<td><b>foo</b> bar <b>baz</b></td>"
            "<td><b>x</b><br/>y<br/>z</td>"
            "</tr></table>"
        )
        assert html_table.html == (
            "<table><tr>"
            "<td><b>foo</b> bar <b>baz</b></td>"
            "<td><b>x</b><br/>y<br/>z</td>"
            "</tr></table>"
        )

    def and_it_normalizes_whitespace_within_tail_text(self):
        """Tail whitespace runs are collapsed, but leading/trailing spaces are kept."""
        html_table = HtmlTable.from_html_text(
            "<table><tr><td><b>a</b>   b\n  c  <b>d</b></td></tr></table>"
        )
        assert html_table.html == "<table><tr><td><b>a</b> b c <b>d</b></td></tr></table>"

    def it_can_serialize_the_table_element_to_str_html_text(self):
        table = fragment_fromstring("<table><tr><td>foobar</td></tr></table>")
        html_table = HtmlTable(table)

        assert html_table.html == "<table><tr><td>foobar</td></tr></table>"

    def it_can_iterate_the_rows_in_the_table(self):
        html_table = HtmlTable.from_html_text(
            "<table>"
            "  <tr><td>abc</td><td>def</td><td>ghi</td></tr>"
            "  <tr><td>jkl</td><td>mno</td><td>pqr</td></tr>"
            "  <tr><td>stu</td><td>vwx</td><td>yz</td></tr>"
            "</table>"
        )

        row_iter = html_table.iter_rows()

        row = next(row_iter)
        assert isinstance(row, HtmlRow)
        assert row.html == "<tr><td>abc</td><td>def</td><td>ghi</td></tr>"
        # --
        row = next(row_iter)
        assert isinstance(row, HtmlRow)
        assert row.html == "<tr><td>jkl</td><td>mno</td><td>pqr</td></tr>"
        # --
        row = next(row_iter)
        assert isinstance(row, HtmlRow)
        assert row.html == "<tr><td>stu</td><td>vwx</td><td>yz</td></tr>"
        # --
        with pytest.raises(StopIteration):
            next(row_iter)

    def it_preserves_row_header_semantics_when_iterating_rows(self):
        html_table = HtmlTable.from_html_text(
            "<table>"
            "  <thead><tr><td>head-from-thead</td></tr></thead>"
            "  <tbody>"
            "    <tr><th>head-from-th</th></tr>"
            "    <tr><td>body</td></tr>"
            "  </tbody>"
            "</table>"
        )

        assert [row.is_header for row in html_table.iter_rows()] == [True, True, False]

    def and_it_preserves_source_row_html_before_compactification(self):
        html_table = HtmlTable.from_html_text(
            "<table>"
            "  <thead><tr data-row='header'><th scope='col'>Header</th></tr></thead>"
            "  <tbody><tr><td class='body-cell'>Body</td></tr></tbody>"
            "</table>"
        )
        rows = list(html_table.iter_rows())
        header_row = fragment_fromstring(rows[0].source_html or "<tr/>")
        body_row = fragment_fromstring(rows[1].source_html or "<tr/>")

        assert header_row.xpath("./@data-row") == ["header"]
        assert header_row.xpath("./th/@scope") == ["col"]
        assert body_row.xpath("./td/@class") == ["body-cell"]

        # -- compactified row HTML contract remains unchanged --
        assert rows[0].html == "<tr><td>Header</td></tr>"
        assert rows[1].html == "<tr><td>Body</td></tr>"

    def it_provides_access_to_the_clear_concatenated_text_of_the_table(self):
        html_table = HtmlTable.from_html_text(
            "<table>"
            "  <tr><th> a\n b  c  </th><th/><th>def</th></tr>"
            "  <tr><td>gh \ti</td><td/><td>\n jk l </td></tr>"
            "  <tr><td/><td> m n op\n</td><td/></tr>"
            "</table>"
        )
        assert html_table.text == "a b c def gh i jk l m n op"


class DescribeHtmlRow:
    """Unit-test suite for `unstructured.common.html_table.HtmlRow`."""

    def it_can_serialize_the_row_to_html(self):
        assert HtmlRow(fragment_fromstring("<tr><td>a</td><td>b</td><td/></tr>")).html == (
            "<tr><td>a</td><td>b</td><td/></tr>"
        )

    def it_can_iterate_the_cells_in_the_row(self):
        row = HtmlRow(fragment_fromstring("<tr><td>a</td><td>b</td><td/></tr>"))

        cell_iter = row.iter_cells()

        cell = next(cell_iter)
        assert isinstance(cell, HtmlCell)
        assert cell.html == "<td>a</td>"
        # --
        cell = next(cell_iter)
        assert isinstance(cell, HtmlCell)
        assert cell.html == "<td>b</td>"
        # --
        cell = next(cell_iter)
        assert isinstance(cell, HtmlCell)
        assert cell.html == "<td/>"
        # --
        with pytest.raises(StopIteration):
            next(cell_iter)

    def it_can_iterate_the_texts_of_the_cells_in_the_row(self):
        row = HtmlRow(fragment_fromstring("<tr><td>a</td><td>b</td><td/></tr>"))

        text_iter = row.iter_cell_texts()

        assert next(text_iter) == "a"
        assert next(text_iter) == "b"
        with pytest.raises(StopIteration):
            next(text_iter)

    def and_it_includes_descendant_inline_text_in_cell_texts(self):
        row = HtmlRow(
            fragment_fromstring(
                "<tr>"
                "<td>ID</td>"
                "<td><a href='#'>Category Link</a></td>"
                "<td><span>  Extra  spacing </span></td>"
                "</tr>"
            )
        )

        assert list(row.iter_cell_texts()) == ["ID", "Category Link", "Extra spacing"]

    def it_knows_when_it_represents_a_header_row(self):
        assert HtmlRow(fragment_fromstring("<tr><td>a</td></tr>")).is_header is False
        assert HtmlRow(fragment_fromstring("<tr><td>a</td></tr>"), is_header=True).is_header is True


class DescribeHtmlCell:
    """Unit-test suite for `unstructured.common.html_table.HtmlCell`."""

    def it_can_serialize_the_cell_to_html(self):
        assert HtmlCell(fragment_fromstring("<td>a b c</td>")).html == "<td>a b c</td>"

    def and_it_preserves_nested_markup_when_serializing_nonempty_cells(self):
        assert HtmlCell(fragment_fromstring("<td><a href='#'>Category Link</a></td>")).html == (
            '<td><a href="#">Category Link</a></td>'
        )

    @pytest.mark.parametrize(
        ("cell_html", "expected_value"),
        [
            ("<td>  Lorem ipsum  </td>", "Lorem ipsum"),
            ("<td><a href='#'>Category Link</a></td>", "Category Link"),
            ("<td/>", ""),
        ],
    )
    def it_knows_the_text_in_the_cell(self, cell_html: str, expected_value: str):
        assert HtmlCell(fragment_fromstring(cell_html)).text == expected_value
