# pyright: reportPrivateUsage=false

import pathlib
import re
from tempfile import SpooledTemporaryFile
from typing import Dict, List

import docx
import pytest
from docx.document import Document
from pytest_mock import MockFixture

from test_unstructured.unit_utils import assert_round_trips_through_JSON
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Address,
    CompositeElement,
    Element,
    ElementType,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    PageBreak,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.docx import _DocxPartitioner, partition_docx
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


class Describe_DocxPartitioner:
    """Unit-test suite for `unstructured.partition.docx._DocxPartitioner`."""

    # -- table behaviors -------------------------------------------------------------------------

    def it_can_convert_a_table_to_html(self):
        table = docx.Document(example_doc_path("docx-tables.docx")).tables[0]
        assert _DocxPartitioner()._convert_table_to_html(table) == (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1  </th><th>Header Col 2  </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lorem ipsum   </td><td>A link example</td></tr>\n"
            "</tbody>\n"
            "</table>"
        )

    def and_it_can_convert_a_nested_table_to_html(self):
        """
        Fixture table is:

            +---+-------------+---+
            | a |     >b<     | c |
            +---+-------------+---+
            |   | +-----+---+ |   |
            |   | |  e  | f | |   |
            | d | +-----+---+ | i |
            |   | | g&t | h | |   |
            |   | +-----+---+ |   |
            +---+-------------+---+
            | j |      k      | l |
            +---+-------------+---+
        """
        table = docx.Document(example_doc_path("docx-tables.docx")).tables[1]

        # -- re.sub() strips out the extra padding inserted by tabulate --
        html = re.sub(r" +<", "<", _DocxPartitioner()._convert_table_to_html(table))

        expected_lines = [
            "<table>",
            "<thead>",
            "<tr><th>a</th><th>&gt;b&lt;</th><th>c</th></tr>",
            "</thead>",
            "<tbody>",
            "<tr><td>d</td><td><table>",
            "<tbody>",
            "<tr><td>e</td><td>f</td></tr>",
            "<tr><td>g&amp;t</td><td>h</td></tr>",
            "</tbody>",
            "</table></td><td>i</td></tr>",
            "<tr><td>j</td><td>k</td><td>l</td></tr>",
            "</tbody>",
            "</table>",
        ]
        actual_lines = html.splitlines()
        for expected, actual in zip(expected_lines, actual_lines):
            assert actual == expected, f"\nexpected: {repr(expected)}\nactual:   {repr(actual)}"

    def it_can_convert_a_table_to_plain_text(self):
        table = docx.Document(example_doc_path("docx-tables.docx")).tables[0]
        assert " ".join(_DocxPartitioner()._iter_table_texts(table)) == (
            "Header Col 1 Header Col 2 Lorem ipsum A link example"
        )

    def and_it_can_convert_a_nested_table_to_plain_text(self):
        """
        Fixture table is:

            +---+-------------+---+
            | a |     >b<     | c |
            +---+-------------+---+
            |   | +-----+---+ |   |
            |   | |  e  | f | |   |
            | d | +-----+---+ | i |
            |   | | g&t | h | |   |
            |   | +-----+---+ |   |
            +---+-------------+---+
            | j |      k      | l |
            +---+-------------+---+
        """
        table = docx.Document(example_doc_path("docx-tables.docx")).tables[1]
        assert " ".join(_DocxPartitioner()._iter_table_texts(table)) == (
            "a >b< c d e f g&t h i j k l"
        )

    def but_the_text_of_a_merged_cell_appears_only_once(self):
        """
        Fixture table is:

            +---+-------+
            | a | b     |
            |   +---+---+
            |   | c | d |
            +---+---+   |
            | e     |   |
            +-------+---+
        """
        table = docx.Document(example_doc_path("docx-tables.docx")).tables[2]
        assert " ".join(_DocxPartitioner()._iter_table_texts(table)) == "a b c d e"

    # -- page-break behaviors --------------------------------------------------------------------

    def it_places_page_breaks_precisely_where_they_occur(self):
        """Page-break behavior has some subtleties.

        * A hard page-break does not generate a PageBreak element (because that would double-count
          it). Word inserts a rendered page-break for the hard break at the effective location.
        * A (rendered) page-break mid-paragraph produces two elements, like `Text, PageBreak, Text`,
          so each Text (subclass) element gets the right page-number.
        * A rendered page-break mid-hyperlink produces two text elements, but the hyperlink itself
          is not split; the entire hyperlink goes on the page where the hyperlink starts, even
          though some of its text appears on the following page. The rest of the paragraph, after
          the hyperlink, appears on the following page.
        * Odd and even-page section starts can lead to two page-breaks, like an odd-page section
          start could go from page 3 to page 5 because 5 is the next odd page.
        """

        def str_repr(e: Element) -> str:
            """A more detailed `repr()` to aid debugging when assertion fails."""
            return f"{e.__class__.__name__}('{e}')"

        expected = [
            # NOTE(scanny) - -- page 1 --
            NarrativeText(
                "First page, tab here:\t"
                "followed by line-break here:\n"
                "here:\n"
                "and here:\n"
                "no-break hyphen here:-"
                "and hard page-break here>>"
            ),
            PageBreak(""),
            # NOTE(scanny) - -- page 2 --
            NarrativeText(
                "<<Text on second page. The font is big so it breaks onto third page--"
                "------------------here-->> <<but break falls inside link so text stays"
                " together."
            ),
            PageBreak(""),
            # NOTE(scanny) - -- page 3 --
            NarrativeText("Continuous section break here>>"),
            NarrativeText("<<followed by text on same page"),
            NarrativeText("Odd-page section break here>>"),
            PageBreak(""),
            # NOTE(scanny) - -- page 4 --
            PageBreak(""),
            # NOTE(scanny) - -- page 5 --
            NarrativeText("<<producing two page-breaks to get from page-3 to page-5."),
            NarrativeText(
                'Then text gets big again so a "natural" rendered page break happens again here>> '
            ),
            PageBreak(""),
            # NOTE(scanny) - -- page 6 --
            Title("<<and then more text proceeds."),
        ]

        elements = _DocxPartitioner.iter_document_elements(example_doc_path("page-breaks.docx"))

        for idx, e in enumerate(elements):
            assert e == expected[idx], (
                f"\n\nExpected: {str_repr(expected[idx])}"
                # --
                f"\n\nGot:      {str_repr(e)}\n"
            )

    # -- header/footer behaviors -----------------------------------------------------------------

    def it_includes_table_cell_text_in_Header_text(self):
        partitioner = _DocxPartitioner(example_doc_path("docx-hdrftr.docx"))
        section = partitioner._document.sections[0]

        header_iter = partitioner._iter_section_headers(section)

        element = next(header_iter)
        assert element.text == "First header para\nTable cell1 Table cell2\nLast header para"

    def it_includes_table_cell_text_in_Footer_text(self):
        """This case also verifies nested-table and merged-cell behaviors."""
        partitioner = _DocxPartitioner(example_doc_path("docx-hdrftr.docx"))
        section = partitioner._document.sections[0]

        footer_iter = partitioner._iter_section_footers(section)

        element = next(footer_iter)
        assert element.text == "para1\ncell1 a b c d e f\npara2"


# -- docx-file loading behaviors -----------------------------------------------------------------


def test_partition_docx_from_filename(
    mock_document_file_path: str,
    expected_elements: List[Element],
):
    elements = partition_docx(mock_document_file_path)

    assert elements == expected_elements
    assert elements[0].metadata.page_number is None
    for element in elements:
        assert element.metadata.filename == "mock_document.docx"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"docx"}


def test_partition_docx_from_filename_with_metadata_filename(mock_document_file_path: str):
    elements = partition_docx(mock_document_file_path, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_docx_with_spooled_file(
    mock_document_file_path: str, expected_elements: List[Text]
):
    """`partition_docx()` accepts a SpooledTemporaryFile as its `file` argument.

    `python-docx` will NOT accept a `SpooledTemporaryFile` in Python versions before 3.11 so we need
    to ensure the source file is appropriately converted in this case.
    """
    with open(mock_document_file_path, "rb") as test_file:
        spooled_temp_file = SpooledTemporaryFile()
        spooled_temp_file.write(test_file.read())
        spooled_temp_file.seek(0)
        elements = partition_docx(file=spooled_temp_file)
        assert elements == expected_elements
        for element in elements:
            assert element.metadata.filename is None


def test_partition_docx_from_file(mock_document_file_path: str, expected_elements: List[Text]):
    with open(mock_document_file_path, "rb") as f:
        elements = partition_docx(file=f)
    assert elements == expected_elements
    for element in elements:
        assert element.metadata.filename is None


def test_partition_docx_from_file_with_metadata_filename(
    mock_document_file_path: str, expected_elements: List[Text]
):
    with open(mock_document_file_path, "rb") as f:
        elements = partition_docx(file=f, metadata_filename="test")
    assert elements == expected_elements
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_docx_raises_with_both_specified(mock_document_file_path: str):
    with open(mock_document_file_path, "rb") as f:
        with pytest.raises(ValueError, match="Exactly one of filename and file must be specified"):
            partition_docx(filename=mock_document_file_path, file=f)


def test_partition_docx_raises_with_neither():
    with pytest.raises(ValueError, match="Exactly one of filename and file must be specified"):
        partition_docx()


# ------------------------------------------------------------------------------------------------


def test_parition_docx_from_team_chat():
    """Docx with no sections partitions recognizing both paragraphs and tables."""
    elements = partition_docx(example_doc_path("teams_chat.docx"))
    assert [e.text for e in elements] == [
        "0:0:0.0 --> 0:0:1.510\nSome Body\nOK. Yeah.",
        "0:0:3.270 --> 0:0:4.250\nJames Bond\nUmm.",
        "saved-by Dennis Forsythe",
    ]
    assert [e.category for e in elements] == [
        ElementType.UNCATEGORIZED_TEXT,
        ElementType.UNCATEGORIZED_TEXT,
        ElementType.TABLE,
    ]


@pytest.mark.parametrize("infer_table_structure", [True, False])
def test_partition_docx_infer_table_structure(infer_table_structure: bool):
    elements = partition_docx(
        example_doc_path("fake_table.docx"), infer_table_structure=infer_table_structure
    )
    table_element_has_text_as_html_field = (
        hasattr(elements[0].metadata, "text_as_html")
        and elements[0].metadata.text_as_html is not None
    )
    assert table_element_has_text_as_html_field == infer_table_structure


def test_partition_docx_processes_table():
    elements = partition_docx(example_doc_path("fake_table.docx"))

    assert isinstance(elements[0], Table)
    assert elements[0].text == ("Header Col 1 Header Col 2 Lorem ipsum A Link example")
    assert elements[0].metadata.text_as_html == (
        "<table>\n"
        "<thead>\n"
        "<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>\n"
        "</thead>\n"
        "<tbody>\n"
        "<tr><td>Lorem ipsum    </td><td>A Link example</td></tr>\n"
        "</tbody>\n"
        "</table>"
    )
    assert elements[0].metadata.filename == "fake_table.docx"


def test_partition_docx_grabs_header_and_footer():
    elements = partition_docx(example_doc_path("handbook-1p.docx"))

    assert elements[0] == Header("US Trustee Handbook")
    assert elements[-1] == Footer("Copyright")
    for element in elements:
        assert element.metadata.filename == "handbook-1p.docx"


# -- page-break behaviors ------------------------------------------------------------------------


def test_partition_docx_includes_neither_page_breaks_nor_numbers_when_rendered_breaks_not_present():
    """Hard page-breaks by themselves are not enough to locate page-breaks in a document.

    In particular, they are redundant when rendered page-breaks are present, which they usually are
    in a native Word document, so lead to double-counting those page-breaks. When rendered page
    breaks are *not* present, only a small fraction will be represented by hard page-breaks so hard
    breaks are a false-positive and will generally produce incorrect page numbers.
    """
    elements = partition_docx(
        example_doc_path("handbook-1p-no-rendered-page-breaks.docx"), include_page_breaks=True
    )

    assert "PageBreak" not in [type(e).__name__ for e in elements]
    assert all(e.metadata.page_number is None for e in elements)


def test_partition_docx_includes_page_numbers_when_page_break_elements_are_suppressed():
    """Page-number metadata is not supressed when `include_page_breaks` arga is False.

    Only inclusion of PageBreak elements is affected by that option.
    """
    elements = partition_docx(example_doc_path("handbook-1p.docx"), include_page_breaks=False)

    assert "PageBreak" not in [type(e).__name__ for e in elements]
    assert elements[1].metadata.page_number == 1
    assert elements[-2].metadata.page_number == 2


def test_partition_docx_includes_page_break_elements_when_so_instructed():
    elements = partition_docx(example_doc_path("handbook-1p.docx"), include_page_breaks=True)

    assert "PageBreak" in [type(e).__name__ for e in elements]
    assert elements[1].metadata.page_number == 1
    assert elements[-2].metadata.page_number == 2


# ------------------------------------------------------------------------------------------------


def test_partition_docx_detects_lists():
    elements = partition_docx(example_doc_path("example-list-items-multiple.docx"))

    assert elements[-1] == ListItem(
        "This is simply dummy text of the printing and typesetting industry.",
    )
    assert sum(1 for e in elements if isinstance(e, ListItem)) == 10


def test_partition_docx_from_filename_exclude_metadata():
    elements = partition_docx(example_doc_path("handbook-1p.docx"), include_metadata=False)

    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_docx_from_file_exclude_metadata(mock_document_file_path: str):
    with open(mock_document_file_path, "rb") as f:
        elements = partition_docx(file=f, include_metadata=False)

    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_docx_metadata_date(mocker: MockFixture):
    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date", return_value="2029-07-05T09:24:28"
    )

    elements = partition_docx(example_doc_path("fake.docx"))

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


def test_partition_docx_metadata_date_with_custom_metadata(mocker: MockFixture):
    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date", return_value="2023-11-01T14:13:07"
    )

    elements = partition_docx(
        example_doc_path("fake.docx"), metadata_last_modified="2020-07-05T09:24:28"
    )

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_docx_from_file_metadata_date(mocker: MockFixture):
    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date_from_file",
        return_value="2029-07-05T09:24:28",
    )

    with open(example_doc_path("fake.docx"), "rb") as f:
        elements = partition_docx(file=f)

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


def test_partition_docx_from_file_metadata_date_with_custom_metadata(mocker: MockFixture):
    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date_from_file",
        return_value="2023-11-01T14:13:07",
    )

    with open(example_doc_path("fake.docx"), "rb") as f:
        elements = partition_docx(file=f, metadata_last_modified="2020-07-05T09:24:28")

    assert elements[0].metadata.last_modified == "2020-07-05T09:24:28"


def test_partition_docx_from_file_without_metadata_date():
    """Test partition_docx() with file that are not possible to get last modified date"""
    with open(example_doc_path("fake.docx"), "rb") as f:
        sf = SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = partition_docx(file=sf)

    assert elements[0].metadata.last_modified is None


def test_get_emphasized_texts_from_paragraph(expected_emphasized_texts: List[Dict[str, str]]):
    partitioner = _DocxPartitioner(
        "example-docs/fake-doc-emphasized-text.docx",
        None,
        None,
        False,
        True,
        None,
    )
    paragraph = partitioner._document.paragraphs[1]
    emphasized_texts = list(partitioner._iter_paragraph_emphasis(paragraph))
    assert paragraph.text == "I am a bold italic bold-italic text."
    assert emphasized_texts == expected_emphasized_texts

    paragraph = partitioner._document.paragraphs[2]
    emphasized_texts = list(partitioner._iter_paragraph_emphasis(paragraph))
    assert paragraph.text == ""
    assert emphasized_texts == []

    paragraph = partitioner._document.paragraphs[3]
    emphasized_texts = list(partitioner._iter_paragraph_emphasis(paragraph))
    assert paragraph.text == "I am a normal text."
    assert emphasized_texts == []


def test_iter_table_emphasis(expected_emphasized_texts: List[Dict[str, str]]):
    partitioner = _DocxPartitioner(
        "example-docs/fake-doc-emphasized-text.docx",
        None,
        None,
        False,
        True,
        None,
    )
    table = partitioner._document.tables[0]
    emphasized_texts = list(partitioner._iter_table_emphasis(table))
    assert emphasized_texts == expected_emphasized_texts


def test_table_emphasis(
    expected_emphasized_text_contents: List[str],
    expected_emphasized_text_tags: List[str],
):
    partitioner = _DocxPartitioner(
        "example-docs/fake-doc-emphasized-text.docx",
        None,
        None,
        False,
        True,
        None,
    )
    table = partitioner._document.tables[0]
    emphasized_text_contents, emphasized_text_tags = partitioner._table_emphasis(table)
    assert emphasized_text_contents == expected_emphasized_text_contents
    assert emphasized_text_tags == expected_emphasized_text_tags


def test_partition_docx_grabs_emphasized_texts(
    expected_emphasized_text_contents: List[str],
    expected_emphasized_text_tags: List[str],
):
    elements = partition_docx(example_doc_path("fake-doc-emphasized-text.docx"))

    assert isinstance(elements[0], Table)
    assert elements[0].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[0].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[1] == NarrativeText("I am a bold italic bold-italic text.")
    assert elements[1].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[1].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[2] == NarrativeText("I am a normal text.")
    assert elements[2].metadata.emphasized_text_contents is None
    assert elements[2].metadata.emphasized_text_tags is None


def test_partition_docx_with_json(mock_document_file_path: str):
    elements = partition_docx(mock_document_file_path)
    assert_round_trips_through_JSON(elements)


def test_parse_category_depth_by_style():
    partitioner = _DocxPartitioner(
        "example-docs/category-level.docx",
        None,
        None,
        False,
        True,
        None,
    )

    # Category depths are 0-indexed and relative to the category type
    # Title, list item, bullet, narrative text, etc.
    test_cases = [
        (0, "Call me Ishmael."),
        (0, "A Heading 1"),
        (0, "Whenever I find myself growing grim"),
        (0, "A top level list item"),
        (1, "Next level"),
        (1, "Same"),
        (0, "Second top-level list item"),
        (0, "whenever I find myself involuntarily"),
        (0, ""),  # Empty paragraph
        (1, "A Heading 2"),
        (0, "This is my substitute for pistol and ball"),
        (0, "Another Heading 1"),
        (0, "There now is your insular city"),
    ]

    paragraphs = partitioner._document.paragraphs
    for idx, (depth, text) in enumerate(test_cases):
        paragraph = paragraphs[idx]
        actual_depth = partitioner._parse_category_depth_by_style(paragraph)
        assert text in paragraph.text, f"paragraph[{[idx]}].text does not contain {text}"
        assert (
            actual_depth == depth
        ), f"expected paragraph[{idx}] to have depth=={depth}, got {actual_depth}"


def test_parse_category_depth_by_style_name():
    partitioner = _DocxPartitioner(None, None, None, False, True, None)

    test_cases = [
        (0, "Heading 1"),
        (1, "Heading 2"),
        (2, "Heading 3"),
        (1, "Subtitle"),
        (0, "List"),
        (1, "List 2"),
        (2, "List 3"),
        (0, "List Bullet"),
        (1, "List Bullet 2"),
        (2, "List Bullet 3"),
        (0, "List Number"),
        (1, "List Number 2"),
        (2, "List Number 3"),
    ]

    for idx, (depth, text) in enumerate(test_cases):
        assert (
            partitioner._parse_category_depth_by_style_name(text) == depth
        ), f"test case {test_cases[idx]} failed"


def test_parse_category_depth_by_style_ilvl():
    partitioner = _DocxPartitioner(None, None, None, False, True, None)
    assert partitioner._parse_category_depth_by_style_ilvl() == 0


def test_add_chunking_strategy_on_partition_docx_default_args():
    chunk_elements = partition_docx(
        example_doc_path("handbook-1p.docx"), chunking_strategy="by_title"
    )
    elements = partition_docx(example_doc_path("handbook-1p.docx"))
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_docx():
    docx_path = example_doc_path("fake-doc-emphasized-text.docx")

    chunk_elements = partition_docx(
        docx_path, chunking_strategy="by_title", max_characters=9, combine_text_under_n_chars=5
    )
    elements = partition_docx(docx_path)
    chunks = chunk_by_title(elements, max_characters=9, combine_text_under_n_chars=5)

    assert chunk_elements == chunks
    assert elements != chunk_elements
    for chunk in chunks:
        assert isinstance(chunk, (CompositeElement, TableChunk))
        assert len(chunk.text) <= 9


# -- language behaviors --------------------------------------------------------------------------


def test_partition_docx_element_metadata_has_languages():
    filename = "example-docs/handbook-1p.docx"
    elements = partition_docx(filename=filename)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_docx_respects_detect_language_per_element():
    filename = "example-docs/language-docs/eng_spa_mult.docx"
    elements = partition_docx(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


def test_partition_docx_respects_languages_arg():
    filename = "example-docs/handbook-1p.docx"
    elements = partition_docx(filename=filename, languages=["deu"])
    assert elements[0].metadata.languages == ["deu"]


def test_partition_docx_raises_TypeError_for_invalid_languages():
    with pytest.raises(TypeError):
        filename = "example-docs/handbook-1p.docx"
        partition_docx(
            filename=filename,
            languages="eng",  # pyright: ignore[reportGeneralTypeIssues]
        )


# ------------------------------------------------------------------------------------------------


def test_partition_docx_includes_hyperlink_metadata():
    elements = partition_docx(example_doc_path("hlink-meta.docx"))

    # -- regular paragraph, no hyperlinks --
    element = elements[0]
    assert element.text == "One"
    metadata = element.metadata
    assert metadata.links is None
    assert metadata.link_texts is None
    assert metadata.link_urls is None

    # -- paragraph with "internal-jump" hyperlinks, no URL --
    element = elements[1]
    assert element.text == "Two with link to bookmark."
    metadata = element.metadata
    assert metadata.links is None
    assert metadata.link_texts is None
    assert metadata.link_urls is None

    # -- paragraph with external link, no fragment --
    element = elements[2]
    assert element.text == "Three with link to foo.com."
    metadata = element.metadata
    assert metadata.links == [
        {
            "start_index": 11,
            "text": "link to foo.com",
            "url": "https://foo.com",
        },
    ]
    assert metadata.link_texts == ["link to foo.com"]
    assert metadata.link_urls == ["https://foo.com"]

    # -- paragraph with external link that has query string --
    element = elements[3]
    assert element.text == "Four with link to foo.com searching for bar."
    metadata = element.metadata
    assert metadata.links == [
        {
            "start_index": 10,
            "text": "link to foo.com searching for bar",
            "url": "https://foo.com?q=bar",
        },
    ]
    assert metadata.link_texts == ["link to foo.com searching for bar"]
    assert metadata.link_urls == ["https://foo.com?q=bar"]

    # -- paragraph with external link with separate URI fragment --
    element = elements[4]
    assert element.text == "Five with link to foo.com introduction section."
    metadata = element.metadata
    assert metadata.links == [
        {
            "start_index": 10,
            "text": "link to foo.com introduction section",
            "url": "http://foo.com/#intro",
        },
    ]
    assert metadata.link_texts == ["link to foo.com introduction section"]
    assert metadata.link_urls == ["http://foo.com/#intro"]

    # -- paragraph with link to file on local filesystem --
    element = elements[7]
    assert element.text == "Eight with link to file."
    metadata = element.metadata
    assert metadata.links == [
        {
            "start_index": 11,
            "text": "link to file",
            "url": "court-exif.jpg",
        },
    ]
    assert metadata.link_texts == ["link to file"]
    assert metadata.link_urls == ["court-exif.jpg"]

    # -- regular paragraph, no hyperlinks, ensure no state is retained --
    element = elements[8]
    assert element.text == "Nine."
    metadata = element.metadata
    assert metadata.links is None
    assert metadata.link_texts is None
    assert metadata.link_urls is None


# -- shape behaviors -----------------------------------------------------------------------------


def test_it_considers_text_inside_shapes():
    # -- <bracketed> text is written inside inline shapes --
    partitioned_doc = partition_docx(example_doc_path("docx-shapes.docx"))
    assert [element.text for element in partitioned_doc] == [
        "Paragraph with single <inline-image> within.",
        "Paragraph with <inline-image1> and <inline-image2> within.",
        # -- text "<floating-shape>" in floating shape is ignored --
        "Paragraph with floating shape attached.",
    ]


# -- module-level fixtures -----------------------------------------------------------------------


def example_doc_path(filename: str) -> str:
    """String path to a file in the example-docs/ directory."""
    return str(pathlib.Path(__file__).parent.parent.parent.parent / "example-docs" / filename)


@pytest.fixture()
def expected_elements() -> List[Text]:
    return [
        Title("These are a few of my favorite things:"),
        ListItem("Parrots"),
        ListItem("Hockey"),
        Title("Analysis"),
        NarrativeText("This is my first thought. This is my second thought."),
        NarrativeText("This is my third thought."),
        Text("2023"),
        Address("DOYLESTOWN, PA 18901"),
    ]


@pytest.fixture()
def expected_emphasized_text_contents() -> List[str]:
    return ["bold", "italic", "bold-italic", "bold-italic"]


@pytest.fixture()
def expected_emphasized_text_tags() -> List[str]:
    return ["b", "i", "b", "i"]


@pytest.fixture()
def expected_emphasized_texts():
    return [
        {"text": "bold", "tag": "b"},
        {"text": "italic", "tag": "i"},
        {"text": "bold-italic", "tag": "b"},
        {"text": "bold-italic", "tag": "i"},
    ]


@pytest.fixture()
def mock_document():
    document = docx.Document()

    document.add_paragraph("These are a few of my favorite things:", style="Heading 1")
    # NOTE(robinson) - this should get picked up as a list item due to the •
    document.add_paragraph("• Parrots", style="Normal")
    # NOTE(robinson) - this should get dropped because it's empty
    document.add_paragraph("• ", style="Normal")
    document.add_paragraph("Hockey", style="List Bullet")
    # NOTE(robinson) - this should get dropped because it's empty
    document.add_paragraph("", style="List Bullet")
    # NOTE(robinson) - this should get picked up as a title
    document.add_paragraph("Analysis", style="Normal")
    # NOTE(robinson) - this should get dropped because it is empty
    document.add_paragraph("", style="Normal")
    # NOTE(robinson) - this should get picked up as a narrative text
    document.add_paragraph("This is my first thought. This is my second thought.", style="Normal")
    document.add_paragraph("This is my third thought.", style="Body Text")
    # NOTE(robinson) - this should just be regular text
    document.add_paragraph("2023")
    # NOTE(robinson) - this should be an address
    document.add_paragraph("DOYLESTOWN, PA 18901")

    return document


@pytest.fixture()
def mock_document_file_path(mock_document: Document, tmp_path: pathlib.Path) -> str:
    filename = str(tmp_path / "mock_document.docx")
    mock_document.save(filename)
    return filename
