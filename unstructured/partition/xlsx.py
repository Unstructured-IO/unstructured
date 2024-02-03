"""Partitioner for Excel 2007+ (XLSX) spreadsheets."""

from __future__ import annotations

import io
from tempfile import SpooledTemporaryFile
from typing import IO, Any, Iterator, Optional, cast

import networkx as nx
import numpy as np
import pandas as pd
from lxml.html.soupparser import fromstring as soupparser_fromstring  # pyright: ignore
from typing_extensions import TypeAlias

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
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
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
@add_chunking_strategy()
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
    exactly_one(filename=filename, file=file)

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
        raise ValueError("Either 'filename' or 'file' argument must be specified.")

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
            _connected_components = _get_connected_components(sheet)
            for _, _min_max_coords in _connected_components:
                min_x, min_y, max_x, max_y = _min_max_coords

                # -- subtable is rectangular region (as DataFrame) of portion of worksheet
                # -- inside the connected-component bounding-box. Row-index and column label are
                # -- preserved.
                subtable = sheet.iloc[min_x : max_x + 1, min_y : max_y + 1]  # noqa: E203

                subtable_parser = _SubtableParser(subtable)

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


def _get_connected_components(
    sheet: pd.DataFrame, filter: bool = True
) -> list[tuple[list[tuple[int, int]], tuple[int, int, int, int]]]:
    """Identify contiguous groups of non-empty cells in an excel sheet.

    Args:
        sheet: an excel sheet read in DataFrame.
        filter (bool, optional): If True (default), filters out overlapping components
        to return distinct components.

    Returns:
        A list of tuples, each containing:
            - A list of tuples representing the connected component's cell coordinates.
            - A tuple with the min and max x and y coordinates bounding the connected component.

    Note:
        This function performs a depth-first search (DFS) to identify connected components of
        non-empty cells in the sheet. If 'filter' is set to True, it also filters out
        overlapping components to return distinct components.
    """
    # -- produce a 2D-graph representing the populated cells of the worksheet (or subsheet).
    # -- A 2D-graph relates each populated cell to the one above, below, left, and right of it.
    max_row, max_col = sheet.shape
    node_array = np.indices((max_row, max_col)).T
    empty_cells = sheet.isna().T
    nodes_to_remove = [tuple(pair) for pair in node_array[empty_cells]]

    graph: nx.Graph = nx.grid_2d_graph(max_row, max_col)  # pyright: ignore
    graph.remove_nodes_from(nodes_to_remove)  # pyright: ignore

    # -- compute sets of nodes representing each connected-component --
    connected_node_sets: Iterator[set[_CellCoordinate]]
    connected_node_sets = nx.connected_components(graph)  # pyright: ignore[reportUnknownMemberType]
    connected_components: list[dict[str, Any]] = []
    for _component in connected_node_sets:
        component = list(_component)
        min_x, min_y, max_x, max_y = _find_min_max_coord(component)
        connected_components.append(
            {
                "component": component,
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
            },
        )

    if filter:
        connected_components = _filter_overlapping_tables(connected_components)
    return [
        (
            connected_component["component"],
            (
                connected_component["min_x"],
                connected_component["min_y"],
                connected_component["max_x"],
                connected_component["max_y"],
            ),
        )
        for connected_component in connected_components
    ]


def _filter_overlapping_tables(
    connected_components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge connected-components that overlap row-wise.

    A pair of overlapping components might look like one of these:

        x x x        x x
            x        x x   x x
        x   x   OR         x x
        x
        x x x
    """
    # -- order connected-components by their top row --
    sorted_components = sorted(connected_components, key=lambda x: x["min_x"])

    merged_components: list[dict[str, Any]] = []
    current_component = None
    for component in sorted_components:
        if current_component is None:
            current_component = component
        else:
            # -- merge this next component with prior if it overlaps row-wise. Note the merged
            # -- component becomes the new current-component.
            if component["min_x"] <= current_component["max_x"]:
                # Merge the components and update min_x, max_x
                current_component["component"].extend(component["component"])
                current_component["min_x"] = min(current_component["min_x"], component["min_x"])
                current_component["max_x"] = max(current_component["max_x"], component["max_x"])
                current_component["min_y"] = min(current_component["min_y"], component["min_y"])
                current_component["max_y"] = max(current_component["max_y"], component["max_y"])

            # -- otherwise flush and move on --
            else:
                merged_components.append(current_component)
                current_component = component

    # Append the last current_component to the merged list
    if current_component is not None:
        merged_components.append(current_component)

    return merged_components


def _find_min_max_coord(connected_component: list[_CellCoordinate]) -> tuple[int, int, int, int]:
    """Find the minimum and maximum coordinates (bounding box) of a connected component."""
    min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
    for _x, _y in connected_component:
        if _x < min_x:
            min_x = _x
        if _y < min_y:
            min_y = _y
        if _x > max_x:
            max_x = _x
        if _y > max_y:
            max_y = _y
    return int(min_x), int(min_y), int(max_x), int(max_y)


def _check_content_element_type(text: str) -> Element:
    """Create `Text`-subtype document element appropriate to `text`."""
    if is_bulleted_text(text):
        return ListItem(
            text=clean_bullets(text),
        )
    elif is_possible_numbered_list(text):
        return ListItem(
            text=text,
        )
    elif is_possible_narrative_text(text):
        return NarrativeText(
            text=text,
        )
    elif is_possible_title(text):
        return Title(
            text=text,
        )
    else:
        return Text(
            text=text,
        )


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
