from functools import cached_property
from io import BytesIO

import numpy as np
import pandas as pd
import pytest

from unstructured.partition.xlsx import (
    _ConnectedComponent,
    _ConnectedComponents,
    partition_xlsx,
)


def _legacy_merge(self, components):
    """Previous pairwise-union implementation, used only as an output oracle."""
    current = None
    for component in sorted(components, key=lambda item: item.min_x):
        if current is None:
            current = component
        elif component.min_x <= current.max_x:
            current = current.merge(component)
        else:
            yield current
            current = component
    if current is not None:
        yield current


def test_wide_sparse_worksheet_does_not_rescan_every_accumulated_cell(monkeypatch):
    count = 200
    frame = pd.DataFrame([["cell" if index % 2 == 0 else None for index in range(2 * count)]])
    visited = 0
    original = _ConnectedComponent._extents.func

    def extents(component):
        nonlocal visited
        visited += len(component._cell_coordinate_set)
        return original(component)

    tracked = cached_property(extents)
    tracked.__set_name__(_ConnectedComponent, "_extents")
    monkeypatch.setattr(_ConnectedComponent, "_extents", tracked)

    components = list(_ConnectedComponents(frame))

    assert len(components) == 1
    assert components[0]._cell_coordinate_set == {(0, 2 * index) for index in range(count)}
    assert visited <= 3 * count


def test_row_overlap_membership_matches_previous_algorithm():
    rng = np.random.default_rng(190)
    for _ in range(100):
        frame = pd.DataFrame(rng.choice([None, "cell"], size=(8, 9)))
        groups = _ConnectedComponents(frame)
        source = [_ConnectedComponent(frame, cells) for cells in groups._iter_connected_node_sets()]
        before = list(_legacy_merge(groups, source))
        original_cells = [set(component._cell_coordinate_set) for component in source]

        after = list(groups._merge_overlapping_tables(source))

        assert [component._cell_coordinate_set for component in after] == [
            component._cell_coordinate_set for component in before
        ]
        assert [component._extents for component in after] == [
            component._extents for component in before
        ]
        assert [component._cell_coordinate_set for component in source] == original_cells


@pytest.mark.parametrize("include_header", [False, True])
@pytest.mark.parametrize("infer_table_structure", [False, True])
def test_real_workbook_output_matches_pairwise_merging(
    monkeypatch, include_header, infer_table_structure
):
    rows = [
        ["A", None, "B", None, None, None],
        [1, None, 2, None, None, None],
        [None, None, "Bridge", None, "C", None],
        [None, None, None, None, 3, None],
        [None] * 6,
        [None, "Separated", None, None, "D", None],
        [None, 4, None, None, 5, None],
    ]
    workbook = BytesIO()
    pd.DataFrame(rows).to_excel(workbook, index=False, header=False)
    payload = workbook.getvalue()
    options = {
        "languages": [""],
        "include_header": include_header,
        "infer_table_structure": infer_table_structure,
    }
    actual = [element.to_dict() for element in partition_xlsx(file=BytesIO(payload), **options)]
    monkeypatch.setattr(_ConnectedComponents, "_merge_overlapping_tables", _legacy_merge)
    expected = [element.to_dict() for element in partition_xlsx(file=BytesIO(payload), **options)]

    assert actual == expected
