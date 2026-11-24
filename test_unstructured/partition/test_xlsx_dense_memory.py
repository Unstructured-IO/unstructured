"""Output parity and working-memory bounds for spreadsheet table rendering."""

import gc
import tracemalloc
import weakref
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from unstructured.common.html_table import HtmlTable
from unstructured.partition import xlsx


def _legacy_render(frame, opts):
    table = HtmlTable.from_html_text(
        frame.to_html(index=False, header=opts.include_header, na_rep="")
    )
    return table.text, table.html if opts.infer_table_structure else None


def _options(header, html):
    return xlsx._XlsxPartitionerOptions(
        file_path=None,
        file=None,
        find_subtable=True,
        include_header=header,
        infer_table_structure=html,
    )


@pytest.mark.parametrize("header", [False, True])
@pytest.mark.parametrize("html", [False, True])
@pytest.mark.parametrize(
    "frame",
    [
        pd.DataFrame(),
        pd.DataFrame(columns=["empty", "columns"]),
        pd.DataFrame(index=range(3)),
        pd.DataFrame([[None, "", np.nan], [" \t\n ", "<>&\"' é 😀", "x\ny\tz\r &nbsp;"]]),
        pd.DataFrame(
            {
                "floats": [1e-12, 12345.0, np.nan, -np.inf],
                "dates": [datetime(2024, 1, 1), pd.NaT, datetime(2024, 1, 2, 1, 2), pd.NaT],
                "mixed": [False, 12345678901234567, "NaN", "http://example.com"],
            }
        ),
        pd.DataFrame([["heading", "value"], ["x", 1], ["y", 1.23456789e-10]]),
    ],
)
def test_row_renderer_matches_pandas_table(frame, header, html):
    opts = _options(header, html)
    assert xlsx._render_table(frame, opts) == _legacy_render(frame, opts)


@pytest.mark.parametrize("header", [False, True])
@pytest.mark.parametrize("subtables", [False, True])
@pytest.mark.parametrize("html", [False, True])
def test_serialized_fixture_outputs_match_whole_table_renderer(
    monkeypatch, header, subtables, html
):
    paths = sorted(Path("example-docs").rglob("*.xlsx"))
    paths += sorted(Path("example-docs").rglob("*.xls"))
    paths = [p for p in paths if "password" not in p.name]
    kwargs = {
        "include_header": header,
        "find_subtable": subtables,
        "infer_table_structure": html,
        "languages": ["eng"],
        "metadata_last_modified": "2026-01-01T00:00:00",
    }
    actual = {p: [e.to_dict() for e in xlsx.partition_xlsx(str(p), **kwargs)] for p in paths}
    monkeypatch.setattr(xlsx, "_render_table", _legacy_render)
    expected = {p: [e.to_dict() for e in xlsx.partition_xlsx(str(p), **kwargs)] for p in paths}
    assert actual == expected


def test_renderer_releases_each_row_tree(monkeypatch):
    original = HtmlTable.from_html_text
    previous = None
    calls = 0

    def read_row(html):
        nonlocal previous, calls
        assert previous is None or previous() is None
        assert len(html) < 1024
        table = original(html)
        previous = weakref.ref(table)
        calls += 1
        return table

    monkeypatch.setattr(HtmlTable, "from_html_text", read_row)
    frame = pd.DataFrame([["a", "b", 1.25]] * 10000)
    xlsx._render_table(frame, _options(False, True))
    assert calls == len(frame)
    assert previous() is None


def test_component_traversal_has_no_per_cell_graph_overhead():
    frame = pd.DataFrame(np.ones((2000, 10)))
    gc.collect()
    tracemalloc.start()
    try:
        components = list(xlsx._ConnectedComponents(frame))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(components) == 1
    assert peak < frame.size * 500
