"""Unit-test suite for the `unstructured.common.html_table` module."""

from __future__ import annotations

from unstructured.common.html_table import htmlify_matrix_of_cell_texts


class Describe_htmlify_matrix_of_cell_texts:
    """Unit-test suite for `unstructured.common.html_table.htmlify_matrix_of_cell_texts()`."""

    def test_htmlify_matrix_handles_empty_cells(self):
        assert htmlify_matrix_of_cell_texts([["cell1", "", "cell3"], ["", "cell5", ""]]) == (
            "<table>"
            "<tr><td>cell1</td><td></td><td>cell3</td></tr>"
            "<tr><td></td><td>cell5</td><td></td></tr>"
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
