# pyright: reportPrivateUsage=false

import os
import pathlib
from tempfile import SpooledTemporaryFile
from typing import Dict, List, cast

import docx
import pytest
from docx.document import Document

from test_unstructured.unit_utils import assert_round_trips_through_JSON
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Address,
    Element,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import _DocxPartitioner, partition_docx
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


def test_partition_docx_from_filename(
    mock_document_filename: str,
    expected_elements: List[Element],
):
    elements = partition_docx(filename=mock_document_filename)

    assert elements == expected_elements
    assert elements[0].metadata.page_number is None
    for element in elements:
        assert element.metadata.filename == "mock_document.docx"
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"docx"}


def test_partition_docx_from_filename_with_metadata_filename(mock_document, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)
    elements = partition_docx(filename=filename, metadata_filename="test")
    assert all(element.metadata.filename == "test" for element in elements)


def test_partition_docx_with_spooled_file(mock_document, expected_elements, tmpdir):
    # Test that the partition_docx function can handle a SpooledTemporaryFile
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    with open(filename, "rb") as test_file:
        spooled_temp_file = SpooledTemporaryFile()
        spooled_temp_file.write(test_file.read())
        spooled_temp_file.seek(0)
        elements = partition_docx(file=spooled_temp_file)
        assert elements == expected_elements
        for element in elements:
            assert element.metadata.filename is None


def test_partition_docx_from_file(mock_document, expected_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition_docx(file=f)
    assert elements == expected_elements
    for element in elements:
        assert element.metadata.filename is None


def test_partition_docx_from_file_with_metadata_filename(mock_document, expected_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition_docx(file=f, metadata_filename="test")
    assert elements == expected_elements
    for element in elements:
        assert element.metadata.filename == "test"


def test_partition_docx_raises_with_both_specified(mock_document, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    with open(filename, "rb") as f, pytest.raises(ValueError):
        partition_docx(filename=filename, file=f)


def test_partition_docx_raises_with_neither():
    with pytest.raises(ValueError):
        partition_docx()


def test_partition_docx_processes_table(filename="example-docs/fake_table.docx"):
    elements = partition_docx(filename=filename)

    assert isinstance(elements[0], Table)
    assert (
        elements[0].metadata.text_as_html
        == """<table>
<thead>
<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>
</thead>
<tbody>
<tr><td>Lorem ipsum    </td><td>A Link example</td></tr>
</tbody>
</table>"""
    )
    assert elements[0].metadata.filename == "fake_table.docx"


def test_partition_docx_grabs_header_and_footer(filename="example-docs/handbook-1p.docx"):
    elements = partition_docx(filename=filename)
    assert elements[0] == Header("US Trustee Handbook")
    assert elements[-1] == Footer("Copyright")
    for element in elements:
        assert element.metadata.filename == "handbook-1p.docx"


def test_partition_docx_includes_pages_if_present(filename="example-docs/handbook-1p.docx"):
    elements = partition_docx(filename=filename, include_page_breaks=False)
    assert "PageBreak" not in [elem.category for elem in elements]
    assert elements[1].metadata.page_number == 1
    assert elements[-2].metadata.page_number == 2
    for element in elements:
        assert element.metadata.filename == "handbook-1p.docx"


def test_partition_docx_includes_page_breaks(filename="example-docs/handbook-1p.docx"):
    elements = partition_docx(filename=filename, include_page_breaks=True)
    assert "PageBreak" in [elem.category for elem in elements]
    assert elements[1].metadata.page_number == 1
    assert elements[-2].metadata.page_number == 2
    for element in elements:
        assert element.metadata.filename == "handbook-1p.docx"


def test_partition_docx_detects_lists(filename="example-docs/example-list-items-multiple.docx"):
    elements = partition_docx(filename=filename)
    list_elements = []
    narrative_elements = []
    for element in elements:
        if isinstance(element, ListItem):
            list_elements.append(element)
        else:
            narrative_elements.append(element)
    assert elements[-1] == ListItem(
        "This is simply dummy text of the printing and typesetting industry.",
    )
    assert len(list_elements) == 10


def test_partition_docx_from_filename_exclude_metadata(filename="example-docs/handbook-1p.docx"):
    elements = partition_docx(filename=filename, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_docx_from_file_exclude_metadata(mock_document, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition_docx(file=f, include_metadata=False)
    assert elements[0].metadata.filetype is None
    assert elements[0].metadata.page_name is None
    assert elements[0].metadata.filename is None


def test_partition_docx_metadata_date(
    mocker,
    filename="example-docs/fake.docx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_docx(filename=filename)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_docx_metadata_date_with_custom_metadata(
    mocker,
    filename="example-docs/fake.docx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modified_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_docx(
        filename=filename,
        metadata_last_modified=expected_last_modified_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modified_date


def test_partition_docx_from_file_metadata_date(
    mocker,
    filename="example-docs/fake.docx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = partition_docx(file=f)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_docx_from_file_metadata_date_with_custom_metadata(
    mocker,
    filename="example-docs/fake.docx",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modified_date = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.docx.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = partition_docx(file=f, metadata_last_modified=expected_last_modified_date)

    assert elements[0].metadata.last_modified == expected_last_modified_date


def test_partition_docx_from_file_without_metadata_date(
    filename="example-docs/fake.docx",
):
    """Test partition_docx() with file that are not possible to get last modified date"""

    with open(filename, "rb") as f:
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
        None,
    )
    table = partitioner._document.tables[0]
    emphasized_text_contents, emphasized_text_tags = partitioner._table_emphasis(table)
    assert emphasized_text_contents == expected_emphasized_text_contents
    assert emphasized_text_tags == expected_emphasized_text_tags


@pytest.mark.parametrize(
    ("filename", "partition_func"),
    [
        ("fake-doc-emphasized-text.docx", partition_docx),
        ("fake-doc-emphasized-text.doc", partition_doc),
    ],
)
def test_partition_docx_grabs_emphasized_texts(
    filename,
    partition_func,
    expected_emphasized_text_contents,
    expected_emphasized_text_tags,
):
    elements = partition_func(filename=f"example-docs/{filename}")

    assert isinstance(elements[0], Table)
    assert elements[0].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[0].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[1] == NarrativeText("I am a bold italic bold-italic text.")
    assert elements[1].metadata.emphasized_text_contents == expected_emphasized_text_contents
    assert elements[1].metadata.emphasized_text_tags == expected_emphasized_text_tags

    assert elements[2] == NarrativeText("I am a normal text.")
    assert elements[2].metadata.emphasized_text_contents is None
    assert elements[2].metadata.emphasized_text_tags is None


def test_partition_docx_with_json(mock_document, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    elements = partition_docx(filename=filename)
    assert_round_trips_through_JSON(elements)


def test_parse_category_depth_by_style():
    partitioner = _DocxPartitioner("example-docs/category-level.docx", None, None, False, None)

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
    partitioner = _DocxPartitioner(None, None, None, False, None)

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
    partitioner = _DocxPartitioner(None, None, None, False, None)
    assert partitioner._parse_category_depth_by_style_ilvl() == 0


def test_add_chunking_strategy_on_partition_docx_default_args(
    filename="example-docs/handbook-1p.docx",
):
    chunk_elements = partition_docx(filename, chunking_strategy="by_title")
    elements = partition_docx(filename)
    chunks = chunk_by_title(elements)

    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_docx(
    filename="example-docs/fake-doc-emphasized-text.docx",
):
    chunk_elements = partition_docx(
        filename,
        chunking_strategy="by_title",
        max_characters=9,
        combine_text_under_n_chars=5,
    )
    elements = partition_docx(filename)
    chunks = chunk_by_title(elements, max_characters=9, combine_text_under_n_chars=5)

    assert chunk_elements == chunks
    assert elements != chunk_elements

    for chunk in chunks:
        assert len(chunk.text) <= 9


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


def test_partition_docx_includes_hyperlink_metadata():
    elements = cast(List[Text], partition_docx(get_test_file_path("hlink-meta.docx")))

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


# -- module-level fixtures -----------------------------------------------------------------------


@pytest.fixture()
def expected_elements():
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
def expected_emphasized_text_contents():
    return ["bold", "italic", "bold-italic", "bold-italic"]


@pytest.fixture()
def expected_emphasized_text_tags():
    return ["b", "i", "b", "i"]


@pytest.fixture()
def expected_emphasized_texts():
    return [
        {"text": "bold", "tag": "b"},
        {"text": "italic", "tag": "i"},
        {"text": "bold-italic", "tag": "b"},
        {"text": "bold-italic", "tag": "i"},
    ]


def get_test_file_path(filename: str) -> str:
    """String path to a file in the docx/test_files directory."""
    # -- needs the `get_` prefix on name so this doesn't get picked up as a test-function --
    return str(pathlib.Path(__file__).parent / "test_files" / filename)


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
def mock_document_filename(mock_document: Document, tmp_path: pathlib.Path) -> str:
    filename = str(tmp_path / "mock_document.docx")
    print(f"filename = {filename}")
    mock_document.save(filename)
    return filename
