"""Partitioner for Excel 2007+ (XLSX) spreadsheets."""

from __future__ import annotations

import io
import struct
from contextlib import contextmanager
from functools import cached_property
from typing import IO, Any, Iterator, Optional

import numpy as np
import openpyxl
import pandas as pd
import xlrd
from msoffcrypto import OfficeFile
from msoffcrypto.exceptions import FileFormatError
from pandas.io.excel._openpyxl import OpenpyxlReader
from pandas.io.formats.format import DataFrameFormatter
from pandas.io.formats.html import HTMLFormatter
from typing_extensions import Self, TypeAlias

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import clean_bullets
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_numbered_list,
    is_possible_title,
)
from unstructured.partition.utils.config import env_config
from unstructured.telemetry import partition_runtime_telemetry

_CellCoordinate: TypeAlias = "tuple[int, int]"

DETECTION_ORIGIN: str = "xlsx"

_ZIP_SIGNATURE = b"PK\x03\x04"
_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


@partition_runtime_telemetry("xlsx")
@apply_metadata(FileType.XLSX)
@add_chunking_strategy
def partition_xlsx(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    find_subtable: bool = True,
    include_header: bool = False,
    infer_table_structure: bool = True,
    starting_page_number: int = 1,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft Excel Documents in .xlsx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    find_subtable
        Detect "subtables" on each worksheet and partition each of those as a separate `Table`
        element. When `False`, each worksheet is partitioned as a single `Table` element. A
        subtable is a contiguous block of cells with more than two cells in each row.
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    include_header
        Determines whether or not header info is included in text and medatada.text_as_html

    Notes
    -----
    The shared XLSX/XLS reader preserves literal text such as "NA", "N/A", "None", and "null".
    Empty cells and empty strings remain missing. Excel error cells and formula caches retain
    the engine's existing behavior. Retained tokens can change table boundaries and inferred
    column types, including numeric rendering.
    """
    opts = _XlsxPartitionerOptions(
        file_path=filename,
        file=file,
        find_subtable=find_subtable,
        include_header=include_header,
        infer_table_structure=infer_table_structure,
    )

    elements: list[Element] = []
    for page_number, (sheet_name, sheet) in enumerate(
        opts.sheets.items(), start=starting_page_number
    ):
        if not opts.find_subtable:
            text, html = _render_table(sheet, opts)

            metadata = ElementMetadata(
                text_as_html=html,
                page_name=sheet_name,
                page_number=page_number,
                filename=opts.metadata_file_path,
                last_modified=opts.last_modified,
            )
            metadata.detection_origin = DETECTION_ORIGIN

            elements.append(Table(text=text, metadata=metadata))

        else:
            for component in _ConnectedComponents.from_worksheet_df(sheet):
                subtable_parser = _SubtableParser(component.subtable)

                # -- emit each leading single-cell row as its own `Text`-subtype element --
                for content in subtable_parser.iter_leading_single_cell_rows_texts():
                    element = _create_element(str(content))
                    element.metadata = _get_metadata(sheet_name, page_number, opts)
                    elements.append(element)

                # -- emit core-table (if it exists) as a `Table` element --
                core_table = subtable_parser.core_table
                if core_table is not None:
                    text, html = _render_table(core_table, opts)
                    element = Table(text=text)
                    element.metadata = _get_metadata(sheet_name, page_number, opts)
                    element.metadata.text_as_html = html
                    elements.append(element)

                # -- no core-table is emitted if it's empty (all rows are single-cell rows) --

                # -- emit each trailing single-cell row as its own `Text`-subtype element --
                for content in subtable_parser.iter_trailing_single_cell_rows_texts():
                    element = _create_element(str(content))
                    element.metadata = _get_metadata(sheet_name, page_number, opts)
                    elements.append(element)

    return elements


class _TableRowRenderer(HTMLFormatter):
    """Apply Pandas' column formatting while retaining only one row of HTML at a time."""

    def __init__(self, frame: pd.DataFrame, *, header: bool, include_html: bool):
        super().__init__(DataFrameFormatter(frame, index=False, header=header, na_rep=""))
        self._html = io.StringIO() if include_html else None
        self._text = io.StringIO()

    def write_tr(self, *args: Any, **kwargs: Any) -> None:
        self.elements.clear()
        super().write_tr(*args, **kwargs)
        table = HtmlTable.from_html_text("<table>" + "\n".join(self.elements) + "</table>")
        self.elements.clear()
        if self._html is not None:
            self._html.write(table.html[len("<table>") : -len("</table>")])
        if table.text:
            if self._text.tell():
                self._text.write(" ")
            self._text.write(table.text)

    def table_text_and_html(self) -> tuple[str, str | None]:
        self.render()
        html = None
        if self._html is not None:
            html = "<table>" + self._html.getvalue() + "</table>"
        return self._text.getvalue(), html


def _render_table(frame: pd.DataFrame, opts: _XlsxPartitionerOptions) -> tuple[str, str | None]:
    """Render normalized text and optional HTML without a worksheet-sized HTML tree."""
    return _TableRowRenderer(
        frame, header=opts.include_header, include_html=opts.infer_table_structure
    ).table_text_and_html()


class ExcelWorkbookReader:
    """A validated workbook supporting worksheet-at-a-time reads."""

    def __init__(self, reader: Any):
        self._reader = reader

    @property
    def sheet_names(self) -> list[str]:
        """Worksheet titles in workbook order."""
        return self._reader.sheet_names

    def parse(self, sheet_name: str, *, header: int | None = None) -> pd.DataFrame:
        """Read one worksheet, preserving NA-like text while keeping blank cells missing."""
        return self._reader.parse(
            sheet_name=sheet_name, header=header, keep_default_na=False, na_values=[""]
        )


@contextmanager
def open_excel_workbook(
    file_bytes: bytes, *, compact_empty_rows: bool = False
) -> Iterator[ExcelWorkbookReader]:
    """Open a workbook after rejecting password-protected files and validating its cell count.

    The returned Pandas reader supports reading individual sheets in workbook order. Callers
    should release each data-frame before parsing the next sheet. Empty-row compaction is safe
    for subtable detection, but must be disabled when sheet row coordinates are significant.
    The context closes the reader even if parsing or processing a worksheet fails.
    """
    _reject_encrypted_workbook(file_bytes)
    if file_bytes.startswith(_ZIP_SIGNATURE):
        engine = "openpyxl"
    elif file_bytes.startswith(_OLE_SIGNATURE):
        engine = "xlrd"
    else:
        raise UnprocessableEntityError("Not a valid XLSX or XLS file.")
    compact_empty_rows = compact_empty_rows and engine == "openpyxl"
    _check_worksheet_cell_count(file_bytes, engine, env_config.XLSX_MAX_CELLS, compact_empty_rows)
    reader = (
        _RowCompactingOpenpyxlReader(io.BytesIO(file_bytes))
        if compact_empty_rows
        else pd.ExcelFile(io.BytesIO(file_bytes), engine=engine)
    )
    try:
        yield ExcelWorkbookReader(reader)
    finally:
        reader.close()


def _reject_encrypted_workbook(file_bytes: bytes) -> None:
    """Raise `UnprocessableEntityError` for a file that is not an Office file or is encrypted."""
    try:
        office_file = OfficeFile(io.BytesIO(file_bytes))
    except FileFormatError as e:
        raise UnprocessableEntityError("Not a valid XLSX file.") from e

    try:
        is_encrypted = office_file.is_encrypted()
    except struct.error:
        # -- msoffcrypto reads an XLS "Workbook" stream as 4-byte record headers and raises when
        # -- the stream ends in fewer than 4 bytes of padding, as in many files written by
        # -- `xlwt` (nolze/msoffcrypto-tool#83). The FilePass record of an encrypted XLS
        # -- directly follows its BOF record, so the check finds it before any padding.
        is_encrypted = False

    if is_encrypted:
        raise UnprocessableEntityError("XLSX file is password protected.")


class _XlsxPartitionerOptions:
    """Encapsulates partitioning option validation, computation, and application of defaults."""

    def __init__(
        self,
        *,
        file_path: Optional[str],
        file: Optional[IO[bytes]],
        find_subtable: bool,
        include_header: bool,
        infer_table_structure: bool,
    ):
        self._file_path = file_path
        self._file = file
        self._find_subtable = find_subtable
        self._include_header = include_header
        self._infer_table_structure = infer_table_structure

    @cached_property
    def find_subtable(self) -> bool:
        """True when partitioner should detect and emit separate `Table` elements for subtables.

        A subtable is (roughly) a contiguous rectangle of populated cells bounded by empty rows.
        """
        return self._find_subtable

    @cached_property
    def header_row_idx(self) -> int | None:
        """The index of the row Pandas should treat as column-headings. Either 0 or None."""
        return 0 if self._include_header else None

    @cached_property
    def include_header(self) -> bool:
        """True when column headers should be included in tables."""
        return self._include_header

    @cached_property
    def infer_table_structure(self) -> bool:
        """True when partitioner should compute and apply `text_as_html` metadata."""
        return self._infer_table_structure

    @cached_property
    def last_modified(self) -> Optional[str]:
        """The best last-modified date available, None if no sources are available."""
        return get_last_modified_date(self._file_path) if self._file_path else None

    @cached_property
    def metadata_file_path(self) -> str | None:
        """The best available file-path for this document or `None` if unavailable."""
        return self._file_path

    @cached_property
    def sheets(self) -> dict[str, pd.DataFrame]:
        """The spreadsheet worksheets, each as a data-frame mapped by sheet-name."""
        with open_excel_workbook(self._file_bytes, compact_empty_rows=self.find_subtable) as reader:
            return {
                name: reader.parse(name, header=self.header_row_idx) for name in reader.sheet_names
            }

    @cached_property
    def _excel_engine(self) -> str:
        """The Pandas engine for this file: "openpyxl" for XLSX (zip), "xlrd" for XLS (OLE)."""
        file_bytes = self._file_bytes
        if file_bytes.startswith(_ZIP_SIGNATURE):
            return "openpyxl"
        if file_bytes.startswith(_OLE_SIGNATURE):
            return "xlrd"
        raise UnprocessableEntityError("Not a valid XLSX or XLS file.")

    @cached_property
    def _file_bytes(self) -> bytes:
        if file := self._file:
            file.seek(0)
            return file.read()
        elif self._file_path:
            with open(self._file_path, "rb") as file:
                return file.read()
        else:
            raise ValueError("Either 'filename' or 'file' argument must be specified.")


class _ConnectedComponent:
    """A collection of cells that are "2d-connected" in a worksheet.

    2d-connected means there is a path from each cell to every other cell by traversing up, down,
    left, or right (not diagonally).
    """

    def __init__(self, worksheet: pd.DataFrame, cell_coordinate_set: set[_CellCoordinate]):
        self._worksheet = worksheet
        self._cell_coordinate_set = cell_coordinate_set

    @cached_property
    def max_x(self) -> int:
        """The right-most column index of the connected component."""
        return self._extents[2]

    def merge(self, other: _ConnectedComponent) -> _ConnectedComponent:
        """Produce new instance with union of cells in `self` and `other`.

        Used to combine regions of workshet that are "overlapping" row-wise but not actually
        2D-connected.
        """
        return _ConnectedComponent(
            self._worksheet, self._cell_coordinate_set.union(other._cell_coordinate_set)
        )

    @cached_property
    def min_x(self) -> int:
        """The left-most column index of the connected component."""
        return self._extents[0]

    @cached_property
    def subtable(self) -> pd.DataFrame:
        """The connected region of the worksheet as a `DataFrame`.

        The subtable is the rectangular region of the worksheet inside the connected-component
        bounding-box. Row-indices and column labels are preserved, not restarted at 0.
        """
        min_x, min_y, max_x, max_y = self._extents
        return self._worksheet.iloc[min_x : max_x + 1, min_y : max_y + 1]

    @cached_property
    def _extents(self) -> tuple[int, int, int, int]:
        """Compute bounding box of this connected component."""
        min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
        for x, y in self._cell_coordinate_set:
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
        return int(min_x), int(min_y), int(max_x), int(max_y)


class _ConnectedComponents:
    """The collection of connected-components for a single worksheet.

    "Connected-components" refers to the graph algorithm we use to detect contiguous groups of
    non-empty cells in an excel sheet.
    """

    def __init__(self, worksheet_df: pd.DataFrame):
        self._worksheet_df = worksheet_df

    def __iter__(self) -> Iterator[_ConnectedComponent]:
        return iter(self._connected_components)

    @classmethod
    def from_worksheet_df(cls, worksheet_df: pd.DataFrame) -> Self:
        """Construct from a worksheet dataframe produced by reading Excel with pandas."""
        return cls(worksheet_df)

    @cached_property
    def _connected_components(self) -> list[_ConnectedComponent]:
        """The `_ConnectedComponent` objects comprising this collection."""
        return list(
            self._merge_overlapping_tables(
                [
                    _ConnectedComponent(self._worksheet_df, cells)
                    for cells in self._iter_connected_node_sets()
                ]
            )
        )

    def _iter_connected_node_sets(self) -> Iterator[set[_CellCoordinate]]:
        """Sets of 4-neighbor connected populated-cell coordinates in row-major order."""
        populated_cell_mask = self._worksheet_df.notna().to_numpy(dtype=bool)
        row_indices, col_indices = np.nonzero(populated_cell_mask)
        row_coordinates, col_coordinates = row_indices.tolist(), col_indices.tolist()
        unvisited_cells = set(zip(row_coordinates, col_coordinates))

        for cell in zip(row_coordinates, col_coordinates):
            if cell not in unvisited_cells:
                continue

            component_node_set: set[_CellCoordinate] = set()
            cells_to_visit = [cell]
            unvisited_cells.remove(cell)

            while cells_to_visit:
                row_idx, col_idx = cells_to_visit.pop()
                component_node_set.add((row_idx, col_idx))

                for neighbor in (
                    (row_idx - 1, col_idx),
                    (row_idx + 1, col_idx),
                    (row_idx, col_idx - 1),
                    (row_idx, col_idx + 1),
                ):
                    if neighbor not in unvisited_cells:
                        continue

                    unvisited_cells.remove(neighbor)
                    cells_to_visit.append(neighbor)

            yield component_node_set

    def _merge_overlapping_tables(
        self, connected_components: list[_ConnectedComponent]
    ) -> Iterator[_ConnectedComponent]:
        """Merge connected-components that overlap row-wise.

        A pair of overlapping components might look like one of these:

            x x x        x x
                x        x x   x x
            x   x   OR         x x
            x
            x x x
        """
        # -- order connected-components by their top row --
        sorted_components = sorted(connected_components, key=lambda x: x.min_x)

        current_component = None

        for component in sorted_components:
            # -- prime the pump --
            if current_component is None:
                current_component = component
                continue

            # -- merge this next component with prior if it overlaps row-wise. Note the merged
            # -- component becomes the new current-component.
            if component.min_x <= current_component.max_x:
                current_component = current_component.merge(component)

            # -- otherwise flush and move on --
            else:
                yield current_component
                current_component = component

        # -- flush last component --
        if current_component is not None:
            yield current_component


class _SubtableParser:
    """Distinguishes core-table from leading and trailing title rows in a subtable.

    A *subtable* is a contiguous block of populated cells in the spreadsheet. Leading or trailing
    rows of that block containing only one populated cell are called "single-cell rows" and are
    not considered part of the core table. These are each emitted separately as a `Text`-subtype
    element.
    """

    def __init__(self, subtable: pd.DataFrame):
        self._subtable = subtable

    @cached_property
    def core_table(self) -> pd.DataFrame | None:
        """The part between the leading and trailing single-cell rows, if any."""
        core_table_start = len(self._leading_single_cell_row_indices)

        # -- if core-table start is the end of table, there is no core-table
        # -- (all rows are single-cell)
        if core_table_start == len(self._subtable):
            return None

        # -- assert: there is at least one core-table row (leading single-cell rows greedily
        # -- consumes all consecutive single-cell rows.

        core_table_stop = len(self._subtable) - len(self._trailing_single_cell_row_indices)

        # -- core-table is what's left in-between --
        return self._subtable[core_table_start:core_table_stop]

    def iter_leading_single_cell_rows_texts(self) -> Iterator[str]:
        """Generate the cell-text for each leading single-cell row."""
        for row_idx in self._leading_single_cell_row_indices:
            yield self._subtable.iloc[row_idx].dropna().iloc[0]  # pyright: ignore

    def iter_trailing_single_cell_rows_texts(self) -> Iterator[str]:
        """Generate the cell-text for each trailing single-cell row."""
        for row_idx in self._trailing_single_cell_row_indices:
            yield self._subtable.iloc[row_idx].dropna().iloc[0]  # pyright: ignore

    @cached_property
    def _leading_single_cell_row_indices(self) -> tuple[int, ...]:
        """Index of each leading single-cell row in subtable, in top-down order."""

        def iter_leading_single_cell_row_indices() -> Iterator[int]:
            for next_row_idx, idx in enumerate(self._single_cell_row_indices):
                if idx != next_row_idx:
                    return
                yield next_row_idx

        return tuple(iter_leading_single_cell_row_indices())

    @cached_property
    def _single_cell_row_indices(self) -> tuple[int, ...]:
        """Index of each single-cell row in subtable, in top-down order."""

        def iter_single_cell_row_idxs() -> Iterator[int]:
            for idx, (_, row) in enumerate(self._subtable.iterrows()):
                if row.count() != 1:
                    continue
                yield idx

        return tuple(iter_single_cell_row_idxs())

    @cached_property
    def _trailing_single_cell_row_indices(self) -> tuple[int, ...]:
        """Index of each trailing single-cell row in subtable, in top-down order."""
        # -- if all subtable rows are single-cell, then by convention they are all leading --
        if len(self._leading_single_cell_row_indices) == len(self._subtable):
            return ()

        def iter_trailing_single_cell_row_indices() -> Iterator[int]:
            """... moving from end upward ..."""
            next_row_idx = len(self._subtable) - 1
            for idx in self._single_cell_row_indices[::-1]:
                if idx != next_row_idx:
                    return
                yield next_row_idx
                next_row_idx -= 1

        return tuple(reversed(list(iter_trailing_single_cell_row_indices())))


# -- the most empty rows `_RowCompactingOpenpyxlReader` keeps before a worksheet's first value --
_LEADING_EMPTY_ROWS_KEPT = 2


class _RowCompactingOpenpyxlReader(OpenpyxlReader):
    """Pandas' openpyxl reader, but each run of empty rows is read as a single empty row.

    A worksheet whose used-range is stretched by a far-away cell, such as one value at row 1M below
    a small table, otherwise becomes a data-frame of mostly empty rows. Keeping one empty row per
    run preserves everything subtable detection depends on: which cells are adjacent (the connected
    components and the subtables cut from them), row-wise overlap between components, column dtype
    inference (a column that had an empty cell still has one) and the header row. A leading run
    keeps up to two empty rows, because the header row can consume the first and the column dtypes
    still need the empty data row after it. A subtable never contains an all-empty row, so its
    output is unchanged. A whole worksheet does render its empty rows, so it is not read this way.
    """

    def get_sheet_data(self, sheet: Any, file_rows_needed: int | None = None) -> list[list[Any]]:
        if file_rows_needed is not None:
            return super().get_sheet_data(sheet, file_rows_needed)

        if self.book.read_only:
            sheet.reset_dimensions()

        data: list[list[Any]] = []
        last_row_with_data = -1
        empty_rows_in_run, empty_rows_to_keep = 0, _LEADING_EMPTY_ROWS_KEPT
        for row in sheet.rows:
            converted_row = [self._convert_cell(cell) for cell in row]
            # -- trim trailing empty cells, as Pandas does --
            while converted_row and converted_row[-1] == "":
                converted_row.pop()
            if converted_row:
                last_row_with_data = len(data)
                empty_rows_in_run, empty_rows_to_keep = 0, 1
            elif empty_rows_in_run >= empty_rows_to_keep:
                continue
            else:
                empty_rows_in_run += 1
            data.append(converted_row)

        # -- trim trailing empty rows and pad the rest to the widest row, as Pandas does --
        data = data[: last_row_with_data + 1]
        if not data:
            return data
        max_width = max(len(row) for row in data)
        return [row + [""] * (max_width - len(row)) for row in data]


def _check_worksheet_cell_count(
    file_bytes: bytes, engine: str, max_cells: int, compact_empty_rows: bool
) -> None:
    """Raise `UnprocessableEntityError` when the worksheets' data-frames would exceed `max_cells`.

    The count is the sum across worksheets of the `rows x columns` shape Pandas would allocate,
    measured without materializing any cells. It raises as soon as the running total passes
    `max_cells`, so the scan itself never reads further than needed.
    """
    total_cells = 0
    cells_by_sheet: dict[int, int] = {}
    for sheet_idx, sheet_name, n_rows, n_cols in _iter_worksheet_shapes(
        file_bytes, engine, compact_empty_rows
    ):
        # -- a later shape for the same worksheet supersedes the earlier, partial one --
        total_cells += n_rows * n_cols - cells_by_sheet.get(sheet_idx, 0)
        cells_by_sheet[sheet_idx] = n_rows * n_cols
        if total_cells > max_cells:
            raise UnprocessableEntityError(
                f"Spreadsheet exceeds the maximum of {max_cells:,} worksheet cells"
                f" (XLSX_MAX_CELLS): worksheet '{sheet_name}' spans at least {n_rows:,} rows"
                f" x {n_cols:,} columns."
            )


def _iter_worksheet_shapes(
    file_bytes: bytes, engine: str, compact_empty_rows: bool
) -> Iterator[tuple[int, str, int, int]]:
    """Generate `(sheet_idx, sheet_name, n_rows, n_cols)` per worksheet, as it would be read.

    With `compact_empty_rows` the shape is the one `_RowCompactingOpenpyxlReader` reads, otherwise
    the one Pandas' own reader does.

    For XLSX the shape grows while the worksheet is streamed, so a partial shape is generated each
    time it grows and the caller can stop early. The last shape generated for each worksheet is its
    full shape.
    """
    if engine == "xlrd":
        # -- Pandas' xlrd reader does not trim, its data-frame is exactly `nrows x ncols`. Ragged
        # -- rows and on-demand loading keep this scan proportional to the populated cells.
        book = xlrd.open_workbook(file_contents=file_bytes, on_demand=True, ragged_rows=True)
        try:
            for sheet_idx in range(book.nsheets):
                sheet = book.sheet_by_index(sheet_idx)
                yield sheet_idx, sheet.name, sheet.nrows, sheet.ncols
                book.unload_sheet(sheet_idx)
        finally:
            book.release_resources()
        return

    # -- Load exactly as the openpyxl readers do. They ignore the stored `<dimension>` and trim
    # -- trailing empty rows and cells, so the shape spans the last row and column with a value,
    # -- or compacts each run of empty rows as `_RowCompactingOpenpyxlReader` does. Read-only
    # -- mode streams the XML and generates rows missing from it as empty tuples, so the gap
    # -- before a far-away cell costs next to nothing.
    workbook = openpyxl.load_workbook(
        io.BytesIO(file_bytes), read_only=True, data_only=True, keep_links=False
    )
    try:
        for sheet_idx, worksheet in enumerate(workbook.worksheets):
            worksheet.reset_dimensions()  # pyright: ignore[reportAttributeAccessIssue]
            n_rows, n_cols, last_row_with_data = 0, 0, 0
            for row in worksheet.iter_rows():
                # -- the last cell in this row holding a value, if any --
                last_cell = next((c for c in reversed(row) if c.value not in (None, "")), None)
                if last_cell is None:
                    continue
                empty_rows = last_cell.row - last_row_with_data - 1
                if compact_empty_rows:
                    empty_rows = min(empty_rows, 1 if n_rows else _LEADING_EMPTY_ROWS_KEPT)
                n_rows += empty_rows + 1
                last_row_with_data = last_cell.row
                n_cols = max(n_cols, last_cell.column)
                yield sheet_idx, worksheet.title, n_rows, n_cols
            yield sheet_idx, worksheet.title, n_rows, n_cols
    finally:
        workbook.close()


def _create_element(text: str) -> Element:
    """Create `Text`-subtype document element appropriate to `text`."""
    if is_bulleted_text(text):
        return ListItem(text=clean_bullets(text))
    elif is_possible_numbered_list(text):
        return ListItem(text=text)
    elif is_possible_narrative_text(text):
        return NarrativeText(text=text)
    elif is_possible_title(text):
        return Title(text=text)
    else:
        return Text(text=text)


def _get_metadata(
    sheet_name: str, page_number: int, opts: _XlsxPartitionerOptions
) -> ElementMetadata:
    return ElementMetadata(
        page_name=sheet_name,
        page_number=page_number,
        filename=opts.metadata_file_path,
        last_modified=opts.last_modified,
    )
