import os

import docx
import pytest

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
from unstructured.partition.docx import partition_docx


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

    from tempfile import SpooledTemporaryFile

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
