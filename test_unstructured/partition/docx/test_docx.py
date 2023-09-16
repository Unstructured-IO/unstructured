import os
from tempfile import SpooledTemporaryFile

import docx
import pytest

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Address,
    Footer,
    Header,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import (
    _extract_contents_and_tags,
    _get_emphasized_texts_from_paragraph,
    _get_emphasized_texts_from_table,
    partition_docx,
)
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_to_json


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
def expected_emphasized_texts():
    return [
        {"text": "bold", "tag": "b"},
        {"text": "italic", "tag": "i"},
        {"text": "bold-italic", "tag": "b"},
        {"text": "bold-italic", "tag": "i"},
    ]


@pytest.fixture()
def expected_emphasized_text_contents():
    return ["bold", "italic", "bold-italic", "bold-italic"]


@pytest.fixture()
def expected_emphasized_text_tags():
    return ["b", "i", "b", "i"]


def test_partition_docx_from_filename(mock_document, expected_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    elements = partition_docx(filename=filename)
    assert elements == expected_elements
    assert elements[0].metadata.page_number is None
    for element in elements:
        assert element.metadata.filename == "mock_document.docx"


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


def test_get_emphasized_texts_from_paragraph(
    expected_emphasized_texts,
    filename="example-docs/fake-doc-emphasized-text.docx",
):
    document = docx.Document(filename)
    paragraph = document.paragraphs[1]
    emphasized_texts = _get_emphasized_texts_from_paragraph(paragraph)
    assert paragraph.text == "I am a bold italic bold-italic text."
    assert emphasized_texts == expected_emphasized_texts

    paragraph = document.paragraphs[2]
    emphasized_texts = _get_emphasized_texts_from_paragraph(paragraph)
    assert paragraph.text == ""
    assert emphasized_texts == []

    paragraph = document.paragraphs[3]
    emphasized_texts = _get_emphasized_texts_from_paragraph(paragraph)
    assert paragraph.text == "I am a normal text."
    assert emphasized_texts == []


def test_get_emphasized_texts_from_table(
    expected_emphasized_texts,
    filename="example-docs/fake-doc-emphasized-text.docx",
):
    document = docx.Document(filename)
    table = document.tables[0]
    emphasized_texts = _get_emphasized_texts_from_table(table)
    assert emphasized_texts == expected_emphasized_texts


def test_extract_contents_and_tags(
    expected_emphasized_texts,
    expected_emphasized_text_contents,
    expected_emphasized_text_tags,
):
    emphasized_text_contents, emphasized_text_tags = _extract_contents_and_tags(
        expected_emphasized_texts,
    )
    assert emphasized_text_contents == expected_emphasized_text_contents
    assert emphasized_text_tags == expected_emphasized_text_tags

    emphasized_text_contents, emphasized_text_tags = _extract_contents_and_tags([])
    assert emphasized_text_contents is None
    assert emphasized_text_tags is None


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


def test_partition_docx_with_json(mock_document, expected_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_document.save(filename)

    elements = partition_docx(filename=filename)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    assert elements[0].metadata.filename == test_elements[0].metadata.filename
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_add_chunking_strategy_on_partition_docx(filename="example-docs/handbook-1p.docx"):
    chunk_elements = partition_docx(filename, chunking_strategy="by_title")
    elements = partition_docx(filename)
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks
