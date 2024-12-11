"""Provides operations related to the HTML table stored in `.metadata.text_as_html`.

Used during partitioning as well as chunking.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Iterator, Sequence, cast

from lxml import etree
from lxml.html import fragment_fromstring

from unstructured.utils import lazyproperty

if TYPE_CHECKING:
    from lxml.html import HtmlElement


def htmlify_matrix_of_cell_texts(matrix: Sequence[Sequence[str]]) -> str:
    """Form an HTML table from "rows" and "columns" of `matrix`.

    Character overhead is minimized:
    - No whitespace padding is added for human readability
    - No newlines ("\n") are added
    - No `<thead>`, `<tbody>`, or `<tfoot>` elements are used; we can't tell where those might be
      semantically appropriate anyway so at best they would consume unnecessary space and at worst
      would be misleading.
    """

    def iter_trs(rows_of_cell_strs: Sequence[Sequence[str]]) -> Iterator[str]:
        for row_cell_strs in rows_of_cell_strs:
            # -- suppress emission of rows with no cells --
            if not row_cell_strs:
                continue
            yield f"<tr>{''.join(iter_tds(row_cell_strs))}</tr>"

    def iter_tds(row_cell_strs: Sequence[str]) -> Iterator[str]:
        for s in row_cell_strs:
            # -- take care of things like '<' and '>' in the text --
            s = html.escape(s)
            # -- substitute <br/> elements for line-feeds in the text --
            s = "<br/>".join(s.split("\n"))
            # -- normalize whitespace in cell --
            cell_text = " ".join(s.split())
            # -- emit void `<td/>` when cell text is empty string --
            yield f"<td>{cell_text}</td>" if cell_text else "<td/>"

    return f"<table>{''.join(iter_trs(matrix))}</table>" if matrix else ""


class HtmlTable:
    """A `<table>` element."""

    def __init__(self, table: HtmlElement):
        self._table = table

    @classmethod
    def from_html_text(cls, html_text: str) -> HtmlTable:
        # -- root is always a `<table>` element so far but let's be robust --
        root = fragment_fromstring(html_text)
        tables = root.xpath("//table")
        if not tables:
            raise ValueError("`html_text` contains no `<table>` element")
        table = tables[0]

        # -- remove `<thead>`, `<tbody>`, and `<tfoot>` noise elements when present --
        noise_elements = table.xpath(".//thead | .//tbody | .//tfoot")
        for e in noise_elements:
            e.drop_tag()

        # -- normalize and compactify the HTML --
        for e in table.iter():
            # -- Strip all attributes from elements, like border="1", class="dataframe" added
            # -- by pandas.DataFrame.to_html(), style="text-align: right;", etc.
            e.attrib.clear()

            # -- change any `<th>` elements to `<td>` so all cells have the same tag --
            if e.tag == "th":
                e.tag = "td"

            # -- normalize whitespace in element text; this removes indent whitespace before nested
            # -- elements and reduces whitespace between words to a single space.
            if e.text:
                e.text = " ".join(e.text.split())

            # -- remove all tails, those are newline + indent if anything --
            if e.tail:
                e.tail = None

        return cls(table)

    @lazyproperty
    def html(self) -> str:
        """The HTML-fragment for this `<table>` element, all on one line.

        Like: `<table><tr><td>foo</td></tr><tr><td>bar</td></tr></table>`

        The HTML contains no human-readability whitespace, attributes, or `<thead>`, `<tbody>`, or
        `<tfoot>` tags. It is made as compact as possible to maximize the semantic content in a
        given space. This is particularly important for chunking.
        """
        return etree.tostring(self._table, encoding=str)

    def iter_rows(self) -> Iterator[HtmlRow]:
        yield from (HtmlRow(tr) for tr in cast("list[HtmlElement]", self._table.xpath("./tr")))

    @lazyproperty
    def text(self) -> str:
        """The clean, concatenated, text for this table."""
        table_text = " ".join(self._table.itertext())
        # -- blank cells will introduce extra whitespace, so normalize after accumulating --
        return " ".join(table_text.split())


class HtmlRow:
    """A `<tr>` element."""

    def __init__(self, tr: HtmlElement):
        self._tr = tr

    @lazyproperty
    def html(self) -> str:
        """Like  "<tr><td>foo</td><td>bar</td></tr>"."""
        return etree.tostring(self._tr, encoding=str)

    def iter_cells(self) -> Iterator[HtmlCell]:
        for td in self._tr:
            yield HtmlCell(td)

    def iter_cell_texts(self) -> Iterator[str]:
        """Generate contents of each cell of this row as a separate string.

        A cell that is empty or contains only whitespace does not generate a string.
        """
        for td in self._tr:
            if (text := td.text) is None:
                continue
            if not text:
                continue
            yield text

    @lazyproperty
    def text_len(self) -> int:
        """Length of the normalized text, as it would appear in `element.text`."""
        return len(" ".join(self.iter_cell_texts()))


class HtmlCell:
    """A `<td>` element."""

    def __init__(self, td: HtmlElement):
        self._td = td

    @lazyproperty
    def html(self) -> str:
        """Like  "<td>foo bar baz</td>"."""
        return etree.tostring(self._td, encoding=str) if self.text else "<td/>"

    @lazyproperty
    def text(self) -> str:
        """Text inside `<td>` element, empty string when no text."""
        if (text := self._td.text) is None:
            return ""
        return " ".join(text.strip().split())
