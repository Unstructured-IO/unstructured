# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.common.html_table` module."""

from __future__ import annotations

import pytest
from lxml.html import fragment_fromstring

from unstructured.common.html_table import (
    HtmlCell,
    HtmlRow,
    HtmlTable,
    htmlify_matrix_of_cell_texts,
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
            "<table>"
            "  <tr><th>a</th><th/><th>b</th></tr>"
            "  <tr><td/><td>c</td><td/></tr>"
            "</table>"
        )
        assert html_table.html == (
            "<table><tr><td>a</td><td/><td>b</td></tr><tr><td/><td>c</td><td/></tr></table>"
        )

    def it_removes_any_extra_whitespace_between_elements_and_normalizes_whitespace_in_text(self):
        html_table = HtmlTable.from_html_text(
            "\n  <table>\n  <tr>\n    <td>\tabc   def\nghi </td>\n  </tr>\n</table>\n  ",
        )
        assert html_table.html == "<table><tr><td>abc def ghi</td></tr></table>"

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


class DescribeHtmlCell:
    """Unit-test suite for `unstructured.common.html_table.HtmlCell`."""

    def it_can_serialize_the_cell_to_html(self):
        assert HtmlCell(fragment_fromstring("<td>a b c</td>")).html == "<td>a b c</td>"

    @pytest.mark.parametrize(
        ("cell_html", "expected_value"),
        [("<td>  Lorem ipsum  </td>", "Lorem ipsum"), ("<td/>", "")],
    )
    def it_knows_the_text_in_the_cell(self, cell_html: str, expected_value: str):
        assert HtmlCell(fragment_fromstring(cell_html)).text == expected_value
