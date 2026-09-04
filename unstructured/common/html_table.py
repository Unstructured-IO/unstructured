"""Provides operations related to the HTML table stored in `.metadata.text_as_html`.

Used during partitioning as well as chunking.
"""

from __future__ import annotations

import copy
import html
from functools import cached_property
from typing import TYPE_CHECKING, Iterator, Sequence, cast

from lxml import etree
from lxml.html import fragment_fromstring
from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from lxml.html import HtmlElement

# -- (cell_text, colspan, rowspan) for one HTML `<td>` --
SpannedCell: TypeAlias = "tuple[str, int, int]"


def _format_td(cell_text: str, colspan: int = 1, rowspan: int = 1) -> str:
    """Format a single `<td>` element, escaping and normalizing `cell_text`.

    `colspan`/`rowspan` attributes are only emitted when greater than 1 (the implicit default),
    to minimize character overhead in the common no-span case.
    """
    # -- take care of things like '<' and '>' in the text --
    s = html.escape(cell_text)
    # -- substitute <br/> elements for line-feeds in the text --
    s = "<br/>".join(s.split("\n"))
    # -- normalize whitespace in cell --
    text = " ".join(s.split())

    attrs = ""
    if colspan > 1:
        attrs += f' colspan="{colspan}"'
    if rowspan > 1:
        attrs += f' rowspan="{rowspan}"'

    # -- emit void `<td/>` when cell text is empty string --
    return f"<td{attrs}>{text}</td>" if text else f"<td{attrs}/>"


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
            yield f"<tr>{''.join(_format_td(s) for s in row_cell_strs)}</tr>"

    return f"<table>{''.join(iter_trs(matrix))}</table>" if matrix else ""


def _tr_html(cells: Sequence[SpannedCell]) -> str:
    """Serialize one `<tr>` from `(cell_text, colspan, rowspan)` triples."""
    tds = (_format_td(text, colspan, rowspan) for text, colspan, rowspan in cells)
    return f"<tr>{''.join(tds)}</tr>"


def htmlify_matrix_of_spanned_cell_texts(matrix: Sequence[Sequence[SpannedCell]]) -> str:
    """Like `htmlify_matrix_of_cell_texts()` but each cell can also carry a colspan/rowspan.

    Each row of `matrix` is a sequence of `(cell_text, colspan, rowspan)` triples, one for each
    grid-position that is the top-left corner of a (possibly 1x1) cell. A grid-position covered by
    the colspan/rowspan of an earlier cell (in the same row or a prior row) must simply be omitted
    from `matrix` by the caller; this function has no notion of the overall grid-shape, only of the
    cells it is told to emit.
    """

    def iter_trs(rows: Sequence[Sequence[SpannedCell]]) -> Iterator[str]:
        for row in rows:
            # -- Unlike `htmlify_matrix_of_cell_texts()`, an empty row here is NOT suppressed: it
            # -- represents a real grid-row entirely covered by a `rowspan` from an earlier row
            # -- (its cells were already emitted there). Suppressing it would drop a `<tr>`, which
            # -- shifts the column-placement of every subsequent row under HTML's rowspan model
            # -- (rowspan counts actual `<tr>` elements, not "rows that happened to have content").
            yield _tr_html(row)

    return f"<table>{''.join(iter_trs(matrix))}</table>" if matrix else ""


def collapse_matrix_of_keyed_cells_to_spans(
    matrix: Sequence[Sequence[tuple[str, object]]],
) -> list[list[SpannedCell]]:
    """Collapse a full row/column grid of `(cell_text, merge_key)` cells into merged spans.

    `matrix` must be "rectangular" in the sense that it represents every grid-position of the
    table, including positions covered by a merge, unlike the `matrix` consumed by
    `htmlify_matrix_of_spanned_cell_texts()`. Two grid-positions belong to the same merged region
    exactly when their `merge_key` compares equal with `==`; a grid-position that is not merged
    with any other must be given a `merge_key` that compares equal only to itself (e.g. a unique
    `object()` instance).

    Only rectangular merged regions are supported (as is guaranteed by, e.g., DOCX and XLSX merge
    semantics) -- an "L-shaped" or otherwise irregular region of matching keys produces undefined
    (but not exception-raising) results.

    Returns one row per row of `matrix`, each containing a `(cell_text, colspan, rowspan)` triple
    for each cell that "originates" a merged region (or an unmerged 1x1 cell), in left-to-right
    order. A grid-position covered by the colspan/rowspan of such a cell is omitted.
    """
    n_rows = len(matrix)
    consumed = [[False] * len(row) for row in matrix]
    spanned_rows: list[list[SpannedCell]] = []

    for r, row in enumerate(matrix):
        spanned_row: list[SpannedCell] = []
        for c, (text, key) in enumerate(row):
            if consumed[r][c]:
                continue
            consumed[r][c] = True

            # -- extend rightward while the merge-key matches --
            colspan = 1
            while c + colspan < len(row) and row[c + colspan][1] == key:
                consumed[r][c + colspan] = True
                colspan += 1

            # -- extend downward while the same colspan-wide run of merge-keys matches --
            rowspan = 1
            next_r = r + 1
            while next_r < n_rows:
                next_row = matrix[next_r]
                if c + colspan > len(next_row):
                    break
                if any(next_row[c + i][1] != key for i in range(colspan)):
                    break
                for i in range(colspan):
                    consumed[next_r][c + i] = True
                rowspan += 1
                next_r += 1

            spanned_row.append((text, colspan, rowspan))
        spanned_rows.append(spanned_row)

    return spanned_rows


class HtmlTable:
    """A `<table>` element."""

    def __init__(
        self,
        table: HtmlElement,
        header_row_idxs: set[int] | None = None,
        source_row_htmls: Sequence[str] | None = None,
        row_group_keys: Sequence[object] | None = None,
    ):
        self._table = table
        self._header_row_idxs = header_row_idxs or set()
        self._source_row_htmls = tuple(source_row_htmls or ())
        self._row_group_keys = tuple(row_group_keys or ())

    @classmethod
    def from_html_text(cls, html_text: str) -> HtmlTable:
        # -- root is always a `<table>` element so far but let's be robust --
        root = fragment_fromstring(html_text)
        tables = root.xpath("//table")
        if not tables:
            raise ValueError("`html_text` contains no `<table>` element")
        table = tables[0]

        # -- capture header semantics, source row HTML, and row-group identity before
        # -- compactification strips those details --
        rows = cast("list[HtmlElement]", table.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr"))
        source_row_htmls = tuple(etree.tostring(tr, encoding=str) for tr in rows)
        header_row_idxs = {
            idx
            for idx, tr in enumerate(rows)
            if tr.getparent().tag == "thead" or bool(tr.xpath("./th"))
        }
        # -- Each row's row-group is identified by its immediate parent element: a specific
        # -- `<thead>`/`<tbody>`/`<tfoot>` when present, or the `<table>` itself for a row with no
        # -- section wrapper. Captured now (identity survives the `.drop_tag()` below even though
        # -- the dropped element becomes detached) so a `rowspan` can later be prevented from
        # -- binding rows across a real section boundary.
        row_group_keys = tuple(tr.getparent() for tr in rows)

        # -- remove `<thead>`, `<tbody>`, and `<tfoot>` noise elements when present --
        noise_elements = table.xpath(".//thead | .//tbody | .//tfoot")
        for e in noise_elements:
            e.drop_tag()

        # -- normalize and compactify the HTML --
        for e in table.iter():
            # -- Strip cosmetic attributes like border="1", class="dataframe" added
            # -- by pandas.DataFrame.to_html(), style="text-align: right;", etc.
            # -- Preserve colspan/rowspan: they are structural, not cosmetic, and are
            # -- required to reconstruct merged-cell layout in chunk HTML.
            preserved = {k: e.attrib[k] for k in ("colspan", "rowspan") if k in e.attrib}
            e.attrib.clear()
            for k, v in preserved.items():
                e.attrib[k] = v

            # -- change any `<th>` elements to `<td>` so all cells have the same tag --
            if e.tag == "th":
                e.tag = "td"

            # -- normalize whitespace in element text; this removes indent whitespace before nested
            # -- elements and reduces whitespace between words to a single space.
            if e.text:
                e.text = " ".join(e.text.split())

            # -- normalize tails. A tail is the text between an element's closing tag and the
            # -- start of the next sibling. Pure-whitespace tails are pretty-printing noise and
            # -- can be dropped, but tails can also carry real content (e.g. mixed inline
            # -- markup like `<b>foo</b> bar <b>baz</b>` or text between `<br/>` tags), which
            # -- must be preserved.
            if e.tail:
                parts = e.tail.split()
                if not parts:
                    e.tail = None
                else:
                    prefix = " " if e.tail[0].isspace() else ""
                    suffix = " " if e.tail[-1].isspace() else ""
                    e.tail = prefix + " ".join(parts) + suffix

        return cls(
            table,
            header_row_idxs=header_row_idxs,
            source_row_htmls=source_row_htmls,
            row_group_keys=row_group_keys,
        )

    @cached_property
    def html(self) -> str:
        """The HTML-fragment for this `<table>` element, all on one line.

        Like: `<table><tr><td>foo</td></tr><tr><td>bar</td></tr></table>`

        The HTML contains no human-readability whitespace, attributes, or `<thead>`, `<tbody>`, or
        `<tfoot>` tags. It is made as compact as possible to maximize the semantic content in a
        given space. This is particularly important for chunking.
        """
        return etree.tostring(self._table, encoding=str)

    def iter_rows(self) -> Iterator[HtmlRow]:
        rows = cast("list[HtmlElement]", self._table.xpath("./tr"))
        for idx, tr in enumerate(rows):
            source_html = self._source_row_htmls[idx] if idx < len(self._source_row_htmls) else None
            row_group_key = self._row_group_keys[idx] if idx < len(self._row_group_keys) else None
            yield HtmlRow(
                tr,
                is_header=(idx in self._header_row_idxs),
                source_html=source_html,
                row_group_key=row_group_key,
            )

    @cached_property
    def text(self) -> str:
        """The clean, concatenated, text for this table."""
        table_text = " ".join(self._table.itertext())
        # -- blank cells will introduce extra whitespace, so normalize after accumulating --
        return " ".join(table_text.split())


class HtmlRow:
    """A `<tr>` element."""

    def __init__(
        self,
        tr: HtmlElement,
        is_header: bool = False,
        source_html: str | None = None,
        row_group_key: object = None,
    ):
        self._tr = tr
        self._is_header = is_header
        self._source_html = source_html
        self._row_group_key = row_group_key

    @cached_property
    def html(self) -> str:
        """Like  "<tr><td>foo</td><td>bar</td></tr>"."""
        return etree.tostring(self._tr, encoding=str)

    def iter_cells(self) -> Iterator[HtmlCell]:
        for td in self._tr:
            yield HtmlCell(td)

    @property
    def is_header(self) -> bool:
        """True when this row originated from `<thead>` or contains `<th>` cells."""
        return self._is_header

    @property
    def source_html(self) -> str | None:
        """Original source `<tr>` HTML captured before compactification, when available."""
        return self._source_html

    @property
    def row_group_key(self) -> object:
        """Identity of this row's containing row-group (a `<thead>`/`<tbody>`/`<tfoot>` element,
        or the `<table>` itself for a row with no section wrapper).

        Two rows compare equal on this value (`is`) exactly when they belong to the same row-group
        for `rowspan` purposes. `None` when unknown (e.g. an `HtmlRow` constructed directly rather
        than via `HtmlTable.iter_rows()`), in which case all such rows are treated as one group.
        """
        return self._row_group_key

    def iter_cell_texts(self) -> Iterator[str]:
        """Generate contents of each cell of this row as a separate string.

        A cell that is empty or contains only whitespace does not generate a string.
        """
        for td in self._tr:
            text = " ".join(td.text_content().split())
            if not text:
                continue
            yield text

    @cached_property
    def text_len(self) -> int:
        """Length of the normalized text, as it would appear in `element.text`."""
        return len(" ".join(self.iter_cell_texts()))

    @cached_property
    def max_rowspan(self) -> int | None:
        """Largest `rowspan` declared by any cell in this row, `1` when none span multiple rows.

        `None` when any cell in this row declares `rowspan="0"` (HTML's "span every remaining
        row"), since it reaches farther than any positive count could name.
        """
        spans = [cell.rowspan for cell in self.iter_cells()]
        if any(span is None for span in spans):
            return None
        return max((span for span in spans if span is not None), default=1)

    def _clipped_tr(self, max_rowspan: int) -> HtmlElement:
        """A deep-copied `<tr>` with any over-reaching cell `rowspan` clipped to `max_rowspan`.

        `max_rowspan` is supplied by the caller as the number of rows -- including this one --
        that are actually going to be present, in order, starting at this row in the emitted
        fragment; this method has no notion of the wider table or chunking context. Passing the
        row's own true remaining reach here is what makes the emitted `rowspan` self-correct: it
        can never claim more rows than truly follow it, regardless of what a caller subsequently
        decides to place after this row.

        Cells whose declared span already fits within `max_rowspan` are left completely untouched
        (not even reserialized). A cell that needs correction has ONLY its `rowspan` attribute
        rewritten (set to the corrected value, or removed entirely when the correction is `1`) --
        every other tag, child element, attribute, and cell content is preserved exactly as in the
        source. This operates on a deep-copied `<tr>` so nested tables, links, images, and other
        markup a naive text-only reconstruction would discard all survive unchanged.
        """
        tr = copy.deepcopy(self._tr)
        for td in tr:
            rowspan = HtmlCell(td).rowspan
            if rowspan is not None and rowspan <= max_rowspan:
                continue  # -- already fits; leave this cell untouched --
            if max_rowspan <= 1:
                td.attrib.pop("rowspan", None)
            else:
                td.attrib["rowspan"] = str(max_rowspan)
        return tr

    def html_clipped_to_rows(self, max_rowspan: int) -> str:
        """Serialize this row's `<tr>`, clipping any cell's `rowspan` down to `max_rowspan` when
        its declared value (or `rowspan="0"`, HTML's "spans every remaining row") would otherwise
        claim more rows than `max_rowspan` names. See `_clipped_tr()` for the clipping rules.
        """
        return etree.tostring(self._clipped_tr(max_rowspan), encoding=str)

    def row_clipped_to_rows(self, max_rowspan: int) -> "HtmlRow":
        """This row, with any over-reaching cell `rowspan` clipped to `max_rowspan` (see
        `_clipped_tr()`), as a fresh `HtmlRow` -- for callers (like `_iter_row_splits()`'s
        singleton-oversized-row path) that need to keep working with a row object rather than a
        serialized string, e.g. to iterate its cells for further splitting.
        """
        return HtmlRow(
            self._clipped_tr(max_rowspan),
            is_header=self._is_header,
            source_html=self._source_html,
            row_group_key=self._row_group_key,
        )


class HtmlCell:
    """A `<td>` element."""

    def __init__(self, td: HtmlElement):
        self._td = td

    @cached_property
    def html(self) -> str:
        """Like  "<td>foo bar baz</td>"."""
        return etree.tostring(self._td, encoding=str) if self.text else "<td/>"

    @cached_property
    def text(self) -> str:
        """Text inside `<td>` element, empty string when no text."""
        return " ".join(self._td.text_content().split())

    @cached_property
    def rowspan(self) -> int | None:
        """Declared `rowspan` for this cell, `1` when absent or unparseable.

        `None` for `rowspan="0"`, HTML's spelling for "spans every remaining row in the
        containing row group." This model doesn't track `<thead>`/`<tbody>`/`<tfoot>`
        boundaries (see `HtmlTable`), so that resolves to the end of the table.
        """
        try:
            value = int(self._td.attrib.get("rowspan", 1))
        except (TypeError, ValueError):
            return 1
        return None if value == 0 else max(1, value)

    @cached_property
    def colspan(self) -> int:
        """Declared `colspan` for this cell, `1` when absent, unparseable, or non-positive.

        Unlike `rowspan`, HTML gives `colspan="0"` no special "spans every remaining column"
        meaning, so it is simply treated as the default of `1`.
        """
        try:
            value = int(self._td.attrib.get("colspan", 1))
        except (TypeError, ValueError):
            return 1
        return max(1, value)
