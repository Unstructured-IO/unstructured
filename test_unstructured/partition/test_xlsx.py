# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.xlsx` module."""

from __future__ import annotations

import io
import sys
import tempfile
from typing import Any

import pandas as pd
import pandas.testing as pdt
import pytest
from pytest_mock import MockerFixture

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT_XLSX,
    EXPECTED_TITLE,
)
from test_unstructured.unit_utils import (
    FixtureRequest,
    Mock,
    assert_round_trips_through_JSON,
    example_doc_path,
    function_mock,
)
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import ListItem, Table, Text, Title
from unstructured.partition.xlsx import (
    _ConnectedComponent,
    _SubtableParser,
    _XlsxPartitionerOptions,
    partition_xlsx,
)

EXPECTED_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXCEPTED_PAGE_NAME = "Stanley Cups"


# ------------------------------------------------------------------------------------------------
# INTEGRATION TESTS
# ------------------------------------------------------------------------------------------------
# These test `partition_xlsx()` as a whole by calling `partition_xlsx()` and inspecting the
# outputs.
# ------------------------------------------------------------------------------------------------


def test_partition_xlsx_from_filename():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[1].metadata.filename == "stanley-cups.xlsx"


def test_partition_xlsx_from_SpooledTemporaryFile_with_emoji():
    f = tempfile.SpooledTemporaryFile()
    with open("example-docs/emoji.xlsx", "rb") as g:
        f.write(g.read())
    elements = partition_xlsx(file=f, include_header=False)
    assert sum(isinstance(element, Text) for element in elements) == 1
    assert len(elements) == 1
    assert clean_extra_whitespace(elements[0].text) == "🤠😅"


def test_partition_xlsx_raises_on_no_file_or_path_provided():
    with pytest.raises(ValueError, match="Either 'filename' or 'file' argument must be specif"):
        partition_xlsx()


def test_partition_xlsx_from_filename_with_metadata_filename():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", metadata_filename="test", include_header=False
    )

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_xlsx_infer_table_structure(infer_table_structure: bool):
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", infer_table_structure=infer_table_structure
    )
    table_elements = [e for e in elements if isinstance(e, Table)]
    for table_element in table_elements:
        table_element_has_text_as_html_field = (
            hasattr(table_element.metadata, "text_as_html")
            and table_element.metadata.text_as_html is not None
        )
        assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_xlsx_from_filename_with_header():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=True)

    assert len(elements) == 2
    assert all(isinstance(e, Table) for e in elements)
    e = elements[0]
    assert e.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert e.metadata.text_as_html is not None


def test_partition_xlsx_from_file():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME
    assert elements[1].metadata.filename is None


def test_partition_xlsx_from_file_like_object_with_name():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        file = io.BytesIO(f.read())
    file.name = "stanley-cups-downloaded-from-network.xlsx"

    elements = partition_xlsx(file=file, include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_FILETYPE
    assert elements[1].metadata.page_name == EXCEPTED_PAGE_NAME


def test_partition_xlsx_from_file_with_metadata_filename():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, metadata_filename="test", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.filename == "test"


def test_partition_xlsx_from_file_with_header():
    with open("example-docs/stanley-cups.xlsx", "rb") as f:
        elements = partition_xlsx(file=f, include_header=True)

    assert len(elements) == 2
    assert all(isinstance(e, Table) for e in elements)
    e = elements[0]
    assert e.text == "Stanley Cups Unnamed: 1 Unnamed: 2 " + EXPECTED_TEXT_XLSX
    assert e.metadata.text_as_html is not None


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_xlsx_from_file_path_gets_last_modified_from_filesystem(mocker: MockerFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xlsx(example_doc_path("stanley-cups.xlsx"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_xlsx_from_file_gets_last_modified_None():
    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        elements = partition_xlsx(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_xlsx_from_file_path_prefers_metadata_last_modified(mocker: MockerFixture):
    filesystem_last_modified = "2024-05-01T15:37:28"
    metadata_last_modified = "2020-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.xlsx.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xlsx(
        example_doc_path("stanley-cups.xlsx"), metadata_last_modified=metadata_last_modified
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_xlsx_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2020-07-05T09:24:28"

    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        elements = partition_xlsx(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_xlsx_with_json():
    elements = partition_xlsx(example_doc_path("stanley-cups.xlsx"), include_header=False)
    assert_round_trips_through_JSON(elements)


def test_partition_xlsx_metadata_language_from_filename():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", include_header=False)

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 4
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xlsx_subtables():
    assert partition_xlsx("example-docs/xlsx-subtable-cases.xlsx") == [
        Table("a b c d e"),
        ListItem("f"),
        Title("a"),
        Table("b c d e"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Table("a b c d"),
        ListItem("2. e"),
        Table("a b c d"),
        Title("e"),
        Title("f"),
        Title("a"),
        Table("b c d e"),
        Title("f"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Title("g"),
        Title("a"),
        Table("b c d e"),
        Title("f"),
        Title("g"),
        Title("a"),
        Title("b"),
        Table("c d e f"),
        Title("g"),
        Title("h"),
        Table("a b c"),
        Title("a"),
        Table("b c d"),
        Table("a b c"),
        Title("d"),
        Title("e"),
    ]


def test_partition_xlsx_element_metadata_has_languages():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx")
    assert elements[0].metadata.languages == ["eng"]


def test_partition_eml_respects_detect_language_per_element():
    elements = partition_xlsx(
        "example-docs/language-docs/eng_spa.xlsx", detect_language_per_element=True
    )

    langs = {e.metadata.languages[0] for e in elements if e.metadata.languages}
    assert "eng" in langs
    assert "spa" in langs


def test_partition_xlsx_with_more_than_1k_cells():
    old_recursion_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(1000)
        partition_xlsx("example-docs/more-than-1k-cells.xlsx")
    finally:
        sys.setrecursionlimit(old_recursion_limit)


# ================================================================================================
# OTHER ARGS
# ================================================================================================


# -- `find_subtable` -----------------------------------------------------------------------------


def test_partition_xlsx_with_find_subtables_False_emits_one_Table_element_per_worksheet():
    elements = partition_xlsx("example-docs/stanley-cups.xlsx", find_subtable=False)
    assert elements == [
        Table(
            "Stanley Cups Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
        ),
        Table(
            "Stanley Cups Since 67 Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple"
            " Leafs TOR 0"
        ),
    ]


def test_partition_xlsx_with_find_subtables_False_and_infer_table_structure_False_works():
    elements = partition_xlsx(
        "example-docs/stanley-cups.xlsx", find_subtable=False, infer_table_structure=False
    )
    assert elements == [
        Table(
            "Stanley Cups Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
        ),
        Table(
            "Stanley Cups Since 67 Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple"
            " Leafs TOR 0"
        ),
    ]
    assert all(e.metadata.text_as_html is None for e in elements)


# ------------------------------------------------------------------------------------------------
# UNIT TESTS
# ------------------------------------------------------------------------------------------------
# These test components used by `partition_xlsx()` in isolation such that all edge cases can be
# exercised.
# ------------------------------------------------------------------------------------------------


class Describe_XlsxPartitionerOptions:
    """Unit-test suite for `unstructured.partition.xlsx._XlsxPartitionerOptions` objects."""

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_find_subtables_within_each_worksheet_or_return_table_per_worksheet(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["find_subtable"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.find_subtable is arg_value

    @pytest.mark.parametrize(("arg_value", "expected_value"), [(True, 0), (False, None)])
    def it_knows_the_header_row_index_for_Pandas(
        self, arg_value: bool, expected_value: int | None, opts_args: dict[str, Any]
    ):
        opts_args["include_header"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.header_row_idx == expected_value

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_include_column_headings_in_Table_text_as_html(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["include_header"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.include_header is arg_value

    @pytest.mark.parametrize("arg_value", [True, False])
    def it_knows_whether_to_include_text_as_html_in_Table_metadata(
        self, arg_value: bool, opts_args: dict[str, Any]
    ):
        opts_args["infer_table_structure"] = arg_value
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.infer_table_structure is arg_value

    # -- .last_modified --------------------------------------------------------------------------

    def it_gets_last_modified_from_the_filesystem_when_a_path_is_provided(
        self, opts_args: dict[str, Any], get_last_modified_date_: Mock
    ):
        filesystem_last_modified = "2024-04-02T20:32:35"
        opts_args["file_path"] = "a/b/spreadsheet.xlsx"
        get_last_modified_date_.return_value = filesystem_last_modified
        opts = _XlsxPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        get_last_modified_date_.assert_called_once_with("a/b/spreadsheet.xlsx")
        assert last_modified == filesystem_last_modified

    def but_it_falls_back_to_None_for_the_last_modified_date_when_no_file_path_is_provided(
        self, opts_args: dict[str, Any]
    ):
        file = io.BytesIO(b"abcdefg")
        opts_args["file"] = file
        opts = _XlsxPartitionerOptions(**opts_args)

        last_modified = opts.last_modified

        assert last_modified is None

    # -- .metadata_file_path ---------------------------------------------------------------------

    def it_uses_the_file_path_argument_when_provided(self, opts_args: dict[str, Any]):
        opts_args["file_path"] = "x/y/z.xlsx"
        opts = _XlsxPartitionerOptions(**opts_args)

        assert opts.metadata_file_path == "x/y/z.xlsx"

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def get_last_modified_date_(self, request: FixtureRequest):
        return function_mock(request, "unstructured.partition.xlsx.get_last_modified_date")

    @pytest.fixture()
    def opts_args(self) -> dict[str, Any]:
        """All default arguments for `_XlsxPartitionerOptions`.

        Individual argument values can be changed to suit each test. Makes construction of opts more
        compact for testing purposes.
        """
        return {
            "file_path": None,
            "file": None,
            "find_subtable": True,
            "include_header": False,
            "infer_table_structure": True,
        }


class Describe_ConnectedComponent:
    """Unit-test suite for `unstructured.partition.xlsx._ConnectedComponent` objects."""

    def it_knows_its_top_and_left_extents(self):
        component = _ConnectedComponent(pd.DataFrame(), {(0, 1), (2, 2), (1, 1), (2, 3), (1, 2)})

        assert component.min_x == 0
        assert component.max_x == 2

    def it_can_merge_with_another_component_to_make_a_new_component(self):
        df = pd.DataFrame()
        component = _ConnectedComponent(df, {(0, 1), (0, 2), (1, 1)})
        other = _ConnectedComponent(df, {(0, 4), (1, 3), (1, 4)})

        merged = component.merge(other)

        assert merged._worksheet is df
        assert merged._cell_coordinate_set == {(0, 1), (0, 2), (1, 1), (0, 4), (1, 3), (1, 4)}

    def it_can_extract_the_rectangular_subtable_containing_its_cells_from_the_worksheet(self):
        worksheet_df = pd.DataFrame(
            [["a", "b", "c"], [], ["d", "e"], ["f", "g"], [None, "h"], [], ["i"]],
            index=[0, 1, 2, 3, 4, 5, 6],
        )
        cell_coordinate_set = {(2, 0), (2, 1), (3, 0), (3, 1), (4, 1)}
        component = _ConnectedComponent(worksheet_df, cell_coordinate_set)

        subtable = component.subtable

        print(f"{subtable=}")
        pdt.assert_frame_equal(
            subtable, pd.DataFrame([["d", "e"], ["f", "g"], [None, "h"]], index=[2, 3, 4])
        )


class Describe_SubtableParser:
    """Unit-test suite for `unstructured.partition.xlsx._SubtableParser` objects."""

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            # -- 1. no leading or trailing single-cell rows --
            (
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 2. one leading single-cell row --
            (
                pd.DataFrame([["a"], ["b", "c"], ["d", "e"]], index=[0, 1, 2]),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 3. two leading single-cell rows --
            (
                pd.DataFrame(
                    [[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]], index=[0, 1, 2, 3]
                ),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 4. one trailing single-cell row --
            (
                pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]], index=[0, 1, 2]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 5. two trailing single-cell rows --
            (
                pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]], index=[0, 1, 2, 3]),
                pd.DataFrame([["a", "b"], ["c", "d"]], index=[0, 1]),
            ),
            # -- 6. one leading, one trailing single-cell rows --
            (
                pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]], index=[0, 1, 2, 3]),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 7. two leading, one trailing single-cell rows --
            (
                pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]], index=[0, 1, 2, 3, 4]),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 8. one leading, two trailing single-cell rows --
            (
                pd.DataFrame(
                    [[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]],
                    index=[0, 1, 2, 3, 4],
                ),
                pd.DataFrame([["b", "c"], ["d", "e"]], index=[1, 2]),
            ),
            # -- 9. two leading, two trailing single-cell rows --
            (
                pd.DataFrame(
                    [["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]], index=[0, 1, 2, 3, 4, 5]
                ),
                pd.DataFrame([["c", "d"], ["e", "f"]], index=[2, 3]),
            ),
            # -- 10. single-row core-table, no leading or trailing single-cell rows --
            (
                pd.DataFrame([["a", "b", "c"]], index=[0]),
                pd.DataFrame([["a", "b", "c"]], index=[0]),
            ),
            # -- 11. single-row core-table, one leading single-cell row --
            (
                pd.DataFrame([["a"], ["b", "c", "d"]], index=[0, 1]),
                pd.DataFrame([["b", "c", "d"]], index=[1]),
            ),
            # -- 12. single-row core-table, two trailing single-cell rows --
            (
                pd.DataFrame([["a", "b", "c"], ["d"], ["e"]], index=[0, 1, 2]),
                pd.DataFrame([["a", "b", "c"]], index=[0]),
            ),
        ],
    )
    def it_extracts_the_core_table_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        """core-table is correctly distinguished from leading and trailing single-cell rows."""
        subtable_parser = _SubtableParser(subtable)

        core_table = subtable_parser.core_table

        assert core_table is not None
        pdt.assert_frame_equal(core_table, expected_value)

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            (pd.DataFrame([["a", "b"], ["c", "d"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"]]), ["a"]),
            (pd.DataFrame([[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]]), ["a", "b"]),
            (pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]]), []),
            (pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]]), ["a"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]]), ["a", "b"]),
            (pd.DataFrame([[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]]), ["a"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]]), ["a", "b"]),
            (pd.DataFrame([["a", "b", "c"]]), []),
            (pd.DataFrame([["a"], ["b", "c", "d"]]), ["a"]),
            (pd.DataFrame([["a", "b", "c"], ["d"], ["e"]]), []),
        ],
    )
    def it_extracts_the_leading_single_cell_rows_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        subtable_parser = _SubtableParser(subtable)
        leading_single_cell_row_texts = list(subtable_parser.iter_leading_single_cell_rows_texts())
        assert leading_single_cell_row_texts == expected_value

    @pytest.mark.parametrize(
        ("subtable", "expected_value"),
        [
            (pd.DataFrame([["a", "b"], ["c", "d"]]), []),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"]]), []),
            (pd.DataFrame([[None, "a"], [None, "b"], ["c", "d"], ["e", "f"]]), []),
            (pd.DataFrame([["a", "b"], ["c", "d"], [None, "e"]]), ["e"]),
            (pd.DataFrame([["a", "b"], ["c", "d"], ["e"], ["f"]]), ["e", "f"]),
            (pd.DataFrame([["a"], ["b", "c"], ["d", "e"], [None, "f"]]), ["f"]),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"]]), ["g"]),
            (
                pd.DataFrame([[None, "a"], ["b", "c"], ["d", "e"], [None, "f"], [None, "g"]]),
                ["f", "g"],
            ),
            (pd.DataFrame([["a"], ["b"], ["c", "d"], ["e", "f"], ["g"], ["h"]]), ["g", "h"]),
            (pd.DataFrame([["a", "b", "c"]]), []),
            (pd.DataFrame([["a"], ["b", "c", "d"]]), []),
            (pd.DataFrame([["a", "b", "c"], ["d"], ["e"]]), ["d", "e"]),
        ],
    )
    def it_extracts_the_trailing_single_cell_rows_from_a_subtable(
        self, subtable: pd.DataFrame, expected_value: pd.DataFrame
    ):
        subtable_parser = _SubtableParser(subtable)

        trailing_single_cell_row_texts = list(
            subtable_parser.iter_trailing_single_cell_rows_texts()
        )

        assert trailing_single_cell_row_texts == expected_value
