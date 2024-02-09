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

                # -- select all single-cell rows in the subtable --
                single_non_empty_rows, single_non_empty_row_contents = _single_non_empty_rows(
                    subtable,
                )

                # -- work out which are leading and which are trailing
                # XXX: badly broken
                (
                    front_non_consecutive,
                    last_non_consecutive,
                ) = _find_first_and_last_non_consecutive_row(
                    single_non_empty_rows,
                    subtable.shape,
                )

                metadata = _get_metadata(
                    include_metadata,
                    sheet_name,
                    page_number,
                    metadata_filename or filename,
                    metadata_last_modified or last_modification_date,
                )

                # -- extract the core-table when there are leading or trailing single-cell rows.
                # XXX: also badly broken.
                if front_non_consecutive is not None and last_non_consecutive is not None:
                    first_row = int(front_non_consecutive - max_x)
                    last_row = int(max_x - last_non_consecutive)
                    subtable = _get_sub_subtable(subtable, (first_row, last_row))

                # -- emit each leading single-cell row as its own `Text`-subtype element
                # XXX: this only works when there is exactly one leading single-cell row.
                if front_non_consecutive is not None:
                    for content in single_non_empty_row_contents[: front_non_consecutive + 1]:
                        element = _check_content_element_type(str(content))
                        element.metadata = metadata
                        elements.append(element)

                # -- emit the core-table as a `Text`-subtype element if it only has one row --
                # XXX: This is a bug. Just because a core-table only has one row doesn't mean it
                # only has one cell. This drops all but the first cell and emits a `Text`-subtype
                # element when it should emit a table (with one row).
                if subtable is not None and len(subtable) == 1:
                    element = _check_content_element_type(
                        str(subtable.iloc[0].values[0])  # pyright: ignore[reportUnknownMemberType]
                    )
                    elements.append(element)

                # -- emit core-table (if it exists) as a `Table` element --
                elif subtable is not None:
                    # XXX: Text parsed from HTML this way is bloated with a lot of extra newlines.
                    # I think we should strip leading and traling "\n"s and replace all others with
                    # a single space. Possibly a newline at the end of each row but not sure how we
                    # would do that exactly.
                    html_text = subtable.to_html(  # pyright: ignore[reportUnknownMemberType]
                        index=False, header=include_header, na_rep=""
                    )
                    text = cast(
                        str,
                        soupparser_fromstring(  # pyright: ignore[reportUnknownMemberType]
                            html_text
                        ).text_content(),
                    )
                    subtable = Table(text=text)
                    subtable.metadata = metadata
                    subtable.metadata.text_as_html = html_text if infer_table_structure else None
                    elements.append(subtable)

                # -- no core-table is emitted if it's empty (all rows are single-cell rows) --

                # -- emit each trailing single-cell row as a `Text`-subtype element --
                if front_non_consecutive is not None and last_non_consecutive is not None:
                    for content in single_non_empty_row_contents[
                        front_non_consecutive + 1 :  # noqa: E203
                    ]:
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


def _get_sub_subtable(
    subtable: pd.DataFrame, first_and_last_row: tuple[int, int]
) -> Optional[pd.DataFrame]:
    """Extract core-table from `subtable` based on the first and last row range.

    A core-table is the rows of a subtable when leading and trailing single-cell rows are removed.
    """
    # TODO(klaijan) - to further check for sub subtable, we could check whether
    # two consecutive rows contains full row of cells.
    # if yes, it might not be a header. We should check the length.
    first_row, last_row = first_and_last_row
    if last_row == first_row:
        return None
    return subtable.iloc[first_row : last_row + 1]  # noqa: E203


def _find_first_and_last_non_consecutive_row(
    row_indices: list[int], table_shape: tuple[int, int]
) -> tuple[Optional[int], Optional[int]]:
    """Find the first and last non-consecutive row indices in `single_cell_row_indices`.

    This can be used to indicate where a contiguous region of cells is "prefixed" or "suffixed" with
    one or more single-cell rows, like this example:

        x
        x
        x x x
        x x x
        x

    We want to identify the start of the core table (the 2 x 3 block of xs) so we can emit it as a
    `Table` element. The leading and trailing single-cell rows get handled separately.
    """
    # If the table is a single column with one or more rows
    table_rows, table_cols = table_shape
    if len(row_indices) == 1 or (len(row_indices) == table_rows and table_cols == 1):
        return row_indices[0], row_indices[0]

    arr = np.array(row_indices)
    front_non_consecutive = next(
        (i for i, (x, y) in enumerate(zip(arr, arr[1:])) if x + 1 != y),
        None,
    )
    reversed_arr = arr[::-1]  # Reverse the array
    last_non_consecutive = next(
        (i for i, (x, y) in enumerate(zip(reversed_arr, reversed_arr[1:])) if x - 1 != y),
        None,
    )
    return front_non_consecutive, last_non_consecutive


def _single_non_empty_rows(subtable: pd.DataFrame) -> tuple[list[int], list[str]]:
    """Row index and contents of each row in `subtable` containing exactly one cell."""
    single_non_empty_rows: list[int] = []
    single_non_empty_row_contents: list[str] = []
    for index, row in subtable.iterrows():  # pyright: ignore
        if row.count() == 1:
            single_non_empty_rows.append(cast(int, index))
            single_non_empty_row_contents.append(str(row.dropna().iloc[0]))  # pyright: ignore
    return single_non_empty_rows, single_non_empty_row_contents


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
