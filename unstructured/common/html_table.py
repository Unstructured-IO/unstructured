"""Provides operations related to the HTML table stored in `.metadata.text_as_html`.

Used during partitioning as well as chunking.
"""

from __future__ import annotations

import html
from typing import Iterator, Sequence


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
