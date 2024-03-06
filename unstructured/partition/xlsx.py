"""Partitioner for Excel 2007+ (XLSX) spreadsheets."""

from __future__ import annotations

import io
from tempfile import SpooledTemporaryFile
from typing import IO, Any, Iterator, Optional, cast

import networkx as nx
import numpy as np
import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring  # pyright: ignore
from typing_extensions import Self, TypeAlias

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import clean_bullets
from unstructured.documents.elements import (
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
    process_metadata,
)
from unstructured.file_utils.filetype import FileType, add_metadata_with_filetype
from unstructured.partition.common import get_last_modified_date, get_last_modified_date_from_file
from unstructured.partition.lang import apply_lang_metadata
from unstructured.partition.text_type import (
    is_bulleted_text,
    is_possible_narrative_text,
    is_possible_numbered_list,
    is_possible_title,
)
from unstructured.utils import lazyproperty

_CellCoordinate: TypeAlias = "tuple[int, int]"

DETECTION_ORIGIN: str = "xlsx"


@process_metadata()
@add_metadata_with_filetype(FileType.XLSX)
@add_chunking_strategy
def partition_xlsx(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    metadata_filename: Optional[str] = None,
    include_metadata: bool = True,
    infer_table_structure: bool = True,
    languages: Optional[list[str]] = ["auto"],
    detect_language_per_element: bool = False,
    metadata_last_modified: Optional[str] = None,
    include_header: bool = False,
    find_subtable: bool = True,
    **kwargs: Any,
) -> list[Element]:
    """Partitions Microsoft Excel Documents in .xlsx format into its document elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object using "rb" mode --> open(filename, "rb").
    include_metadata
        Determines whether or not metadata is included in the output.
    infer_table_structure
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    languages
        User defined value for metadata.languages if provided. Otherwise language is detected
        using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be
        in either language.
        Additional Parameters:
            detect_language_per_element
                Detect language per element instead of at the document level.
    metadata_last_modified
        The day of the last modification
    include_header
        Determines whether or not header info is included in text and medatada.text_as_html
    """
    last_modification_date = None
    header = 0 if include_header else None

    sheets: dict[str, pd.DataFrame] = {}
    if filename:
        sheets = pd.read_excel(  # pyright: ignore[reportUnknownMemberType]
            filename, sheet_name=None, header=header
        )
        last_modification_date = get_last_modified_date(filename)

    elif file:
        if isinstance(file, SpooledTemporaryFile):
            file.seek(0)
            f = io.BytesIO(file.read())
        else:
            f = file
        sheets = pd.read_excel(  # pyright: ignore[reportUnknownMemberType]
            f, sheet_name=None, header=header
        )
        last_modification_date = get_last_modified_date_from_file(file)
    else:
        raise ValueError("Either 'filename' or 'file' argument must be specified")

    elements: list[Element] = []
    for page_number, (sheet_name, sheet) in enumerate(sheets.items(), start=1):
        if not find_subtable:
            html_text = (
                sheet.to_html(  # pyright: ignore[reportUnknownMemberType]
                    index=False, header=include_header, na_rep=""
                )
                if infer_table_structure
                else None
            )
            # XXX: `html_text` can be `None`. What happens on this call in that case?
            text = cast(
                str,
                soupparser_fromstring(  # pyright: ignore[reportUnknownMemberType]
                    html_text
                ).text_content(),
            )

            if include_metadata:
                metadata = ElementMetadata(
                    text_as_html=html_text,
                    page_name=sheet_name,
                    page_number=page_number,
                    filename=metadata_filename or filename,
                    last_modified=metadata_last_modified or last_modification_date,
                )
                metadata.detection_origin = DETECTION_ORIGIN
            else:
                metadata = ElementMetadata()

            table = Table(text=text, metadata=metadata)
            elements.append(table)
        else:
            for component in _ConnectedComponents.from_worksheet_df(sheet):
                subtable_parser = _SubtableParser(component.subtable)

                metadata = _get_metadata(
                    include_metadata,
                    sheet_name,
                    page_number,
                    metadata_filename or filename,
                    metadata_last_modified or last_modification_date,
                )

                # -- emit each leading single-cell row as its own `Text`-subtype element --
                for content in subtable_parser.iter_leading_single_cell_rows_texts():
                    element = _check_content_element_type(str(content))
                    element.metadata = metadata
                    elements.append(element)

                # -- emit core-table (if it exists) as a `Table` element --
                core_table = subtable_parser.core_table
                if core_table is not None:
                    html_text = core_table.to_html(  # pyright: ignore[reportUnknownMemberType]
                        index=False, header=include_header, na_rep=""
                    )
                    text = cast(
                        str,
                        soupparser_fromstring(  # pyright: ignore[reportUnknownMemberType]
                            html_text
                        ).text_content(),
                    )
                    element = Table(text=text)
                    element.metadata = metadata
                    element.metadata.text_as_html = html_text if infer_table_structure else None
                    elements.append(element)

                # -- no core-table is emitted if it's empty (all rows are single-cell rows) --

                # -- emit each trailing single-cell row as its own `Text`-subtype element --
                for content in subtable_parser.iter_trailing_single_cell_rows_texts():
                    element = _check_content_element_type(str(content))
                    element.metadata = metadata
                    elements.append(element)

    elements = list(
        apply_lang_metadata(
            elements=elements,
            languages=languages,
            detect_language_per_element=detect_language_per_element,
        ),
    )
    return elements


class _ConnectedComponent:
    """A collection of cells that are "2d-connected" in a worksheet.

    2d-connected means there is a path from each cell to every other cell by traversing up, down,
    left, or right (not diagonally).
    """

    def __init__(self, worksheet: pd.DataFrame, cell_coordinate_set: set[_CellCoordinate]):
        self._worksheet = worksheet
        self._cell_coordinate_set = cell_coordinate_set

    @lazyproperty
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

    @lazyproperty
    def min_x(self) -> int:
        """The left-most column index of the connected component."""
        return self._extents[0]

    @lazyproperty
    def subtable(self) -> pd.DataFrame:
        """The connected region of the worksheet as a `DataFrame`.

        The subtable is the rectangular region of the worksheet inside the connected-component
        bounding-box. Row-indices and column labels are preserved, not restarted at 0.
        """
        min_x, min_y, max_x, max_y = self._extents
        return self._worksheet.iloc[min_x : max_x + 1, min_y : max_y + 1]

    @lazyproperty
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

    @lazyproperty
    def _connected_components(self) -> list[_ConnectedComponent]:
        """The `_ConnectedComponent` objects comprising this collection."""
        # -- produce a 2D-graph representing the populated cells of the worksheet (or subsheet).
        # -- A 2D-graph relates each populated cell to the one above, below, left, and right of it.
        max_row, max_col = self._worksheet_df.shape
        node_array = np.indices((max_row, max_col)).T
        empty_cells = self._worksheet_df.isna().T
        nodes_to_remove = [tuple(pair) for pair in node_array[empty_cells]]

        graph: nx.Graph = nx.grid_2d_graph(max_row, max_col)  # pyright: ignore
        graph.remove_nodes_from(nodes_to_remove)  # pyright: ignore

        # -- compute sets of nodes representing each connected-component --
        connected_node_sets: Iterator[set[_CellCoordinate]]
        connected_node_sets = nx.connected_components(  # pyright: ignore[reportUnknownMemberType]
            graph
        )

        return list(
            self._merge_overlapping_tables(
                [
                    _ConnectedComponent(self._worksheet_df, component_node_set)
                    for component_node_set in connected_node_sets
                ]
            )
        )

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

    @lazyproperty
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

    @lazyproperty
    def _leading_single_cell_row_indices(self) -> tuple[int, ...]:
        """Index of each leading single-cell row in subtable, in top-down order."""

        def iter_leading_single_cell_row_indices() -> Iterator[int]:
            for next_row_idx, idx in enumerate(self._single_cell_row_indices):
                if idx != next_row_idx:
                    return
                yield next_row_idx

        return tuple(iter_leading_single_cell_row_indices())

    @lazyproperty
    def _single_cell_row_indices(self) -> tuple[int, ...]:
        """Index of each single-cell row in subtable, in top-down order."""

        def iter_single_cell_row_idxs() -> Iterator[int]:
            for idx, (_, row) in enumerate(self._subtable.iterrows()):  # pyright: ignore
                if row.count() != 1:
                    continue
                yield idx

        return tuple(iter_single_cell_row_idxs())

    @lazyproperty
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


def _check_content_element_type(text: str) -> Element:
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
    include_metadata: bool = True,
    sheet_name: Optional[str] = None,
    page_number: Optional[int] = -1,
    filename: Optional[str] = None,
    last_modification_date: Optional[str] = None,
) -> ElementMetadata:
    """Returns metadata depending on `include_metadata` flag"""
    if include_metadata:
        metadata = ElementMetadata(
            page_name=sheet_name,
            page_number=page_number,
            filename=filename,
            last_modified=last_modification_date,
        )
    else:
        metadata = ElementMetadata()
    return metadata
