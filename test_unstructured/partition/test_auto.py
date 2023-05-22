import json
import os
import pathlib
import warnings
from importlib import import_module
from unittest.mock import patch

import docx
import pypandoc
import pytest

from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    Address,
    ElementMetadata,
    ListItem,
    NarrativeText,
    PageBreak,
    Table,
    Text,
    Title,
)
from unstructured.file_utils.filetype import FILETYPE_TO_MIMETYPE, FileType
from unstructured.partition import auto
from unstructured.partition.auto import partition
from unstructured.partition.common import convert_office_doc
from unstructured.staging.base import elements_to_json

DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(DIRECTORY, "..", "..", "example-docs")

EXPECTED_EMAIL_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]

is_in_docker = os.path.exists("/.dockerenv")
rtf_not_supported = "rtf" not in pypandoc.get_pandoc_formats()[0]
odt_not_supported = "odt" not in pypandoc.get_pandoc_formats()[0]


def test_auto_partition_email_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    elements = partition(filename=filename, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_email_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


@pytest.fixture()
def mock_docx_document():
    document = docx.Document()

    document.add_paragraph("These are a few of my favorite things:", style="Heading 1")
    # NOTE(robinson) - this should get picked up as a list item due to the •
    document.add_paragraph("• Parrots", style="Normal")
    document.add_paragraph("Hockey", style="List Bullet")
    # NOTE(robinson) - this should get picked up as a title
    document.add_paragraph("Analysis", style="Normal")
    # NOTE(robinson) - this should get dropped because it is empty
    document.add_paragraph("", style="Normal")
    # NOTE(robinson) - this should get picked up as a narrative text
    document.add_paragraph("This is my first thought. This is my second thought.", style="Normal")
    document.add_paragraph("This is my third thought.", style="Body Text")
    # NOTE(robinson) - this should just be regular text
    document.add_paragraph("2023")

    return document


@pytest.fixture()
def expected_docx_elements():
    return [
        Title("These are a few of my favorite things:"),
        ListItem("Parrots"),
        ListItem("Hockey"),
        Title("Analysis"),
        NarrativeText("This is my first thought. This is my second thought."),
        NarrativeText("This is my third thought."),
        Text("2023"),
    ]


def test_auto_partition_docx_with_filename(mock_docx_document, expected_docx_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_docx_document.save(filename)

    elements = partition(filename=filename, strategy="hi_res")
    assert elements == expected_docx_elements
    assert elements[0].metadata.filename == os.path.basename(filename)


def test_auto_partition_docx_with_file(mock_docx_document, expected_docx_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_docx_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert elements == expected_docx_elements


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "application/msword"), (True, "application/msword"), (True, None)],
)
def test_auto_partition_doc_with_filename(
    mock_docx_document,
    expected_docx_elements,
    tmpdir,
    pass_file_filename,
    content_type,
):
    docx_filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    doc_filename = os.path.join(tmpdir.dirname, "mock_document.doc")
    mock_docx_document.save(docx_filename)
    convert_office_doc(docx_filename, tmpdir.dirname, "doc")
    file_filename = doc_filename if pass_file_filename else None
    elements = partition(
        filename=doc_filename,
        file_filename=file_filename,
        content_type=content_type,
        strategy="hi_res",
    )
    assert elements == expected_docx_elements
    assert elements[0].metadata.filename == "mock_document.doc"
    assert elements[0].metadata.file_directory == tmpdir.dirname


# NOTE(robinson) - the application/x-ole-storage mime type is not specific enough to
# determine that the file is an .doc document
@pytest.mark.xfail()
def test_auto_partition_doc_with_file(mock_docx_document, expected_docx_elements, tmpdir):
    docx_filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    doc_filename = os.path.join(tmpdir.dirname, "mock_document.doc")
    mock_docx_document.save(docx_filename)
    convert_office_doc(docx_filename, tmpdir.dirname, "doc")

    with open(doc_filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert elements == expected_docx_elements


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_filename(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "example-10k.html")
    file_filename = filename if pass_file_filename else None
    elements = partition(
        filename=filename,
        file_filename=file_filename,
        content_type=content_type,
        strategy="hi_res",
    )
    assert len(elements) > 0
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_file(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    file_filename = filename if pass_file_filename else None
    with open(filename) as f:
        elements = partition(
            file=f,
            file_filename=file_filename,
            content_type=content_type,
            strategy="hi_res",
        )
    assert len(elements) > 0


def test_auto_partition_html_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0


def test_auto_partition_json_from_filename():
    """Test auto-processing an unstructured json output file by filename."""
    filename = os.path.join(
        EXAMPLE_DOCS_DIRECTORY,
        "..",
        "test_unstructured_ingest",
        "expected-structured-output",
        "azure-blob-storage",
        "spring-weather.html.json",
    )
    with open(filename) as json_f:
        json_data = json.load(json_f)
    json_elems = json.loads(elements_to_json(partition(filename=filename, strategy="hi_res")))
    for elem in json_elems:
        # coordinates are always in the element data structures, even if None
        elem.pop("coordinates")
        elem.pop("metadata")
    for elem in json_data:
        elem.pop("metadata")
    assert json_data == json_elems


@pytest.mark.xfail(
    reason="parsed as text not json, https://github.com/Unstructured-IO/unstructured/issues/492",
)
def test_auto_partition_json_from_file():
    """Test auto-processing an unstructured json output file by file handle."""
    filename = os.path.join(
        EXAMPLE_DOCS_DIRECTORY,
        "..",
        "test_unstructured_ingest",
        "expected-structured-output",
        "azure-blob-storage",
        "spring-weather.html.json",
    )
    with open(filename) as json_f:
        json_data = json.load(json_f)
    with open(filename, encoding="utf-8") as partition_f:
        json_elems = json.loads(elements_to_json(partition(file=partition_f, strategy="hi_res")))
    for elem in json_elems:
        # coordinates are always in the element data structures, even if None
        elem.pop("coordinates")
    assert json_data == json_elems


EXPECTED_TEXT_OUTPUT = [
    NarrativeText(text="This is a test document to use for unit tests."),
    Address(text="Doylestown, PA 18901"),
    Title(text="Important points:"),
    ListItem(text="Hamburgers are delicious"),
    ListItem(text="Dogs are the best"),
    ListItem(text="I love fuzzy blankets"),
]


def test_auto_partition_text_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    elements = partition(filename=filename, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_TEXT_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_text_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_TEXT_OUTPUT


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_filename(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    file_filename = filename if pass_file_filename else None

    elements = partition(
        filename=filename,
        file_filename=file_filename,
        content_type=content_type,
        strategy="hi_res",
    )

    assert isinstance(elements[0], Title)
    assert elements[0].text.startswith("LayoutParser")

    assert isinstance(elements[1], NarrativeText)
    assert elements[1].text.startswith("Zejiang Shen")

    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_pdf_uses_table_extraction():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    with patch(
        "unstructured_inference.inference.layout.process_file_with_model",
    ) as mock_process_file_with_model:
        partition(filename, pdf_infer_table_structure=True, strategy="hi_res")
        assert mock_process_file_with_model.call_args[1]["extract_tables"]


def test_auto_partition_pdf_with_fast_strategy():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")

    mock_return = [NarrativeText("Hello there!")]
    with patch.object(auto, "partition_pdf", return_value=mock_return) as mock_partition:
        partition(filename=filename, strategy="fast")

    mock_partition.assert_called_once_with(
        filename=filename,
        file=None,
        url=None,
        include_page_breaks=False,
        encoding="utf-8",
        infer_table_structure=False,
        strategy="fast",
        ocr_languages="eng",
    )


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_file(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    file_filename = filename if pass_file_filename else None

    with open(filename, "rb") as f:
        elements = partition(
            file=f,
            file_filename=file_filename,
            content_type=content_type,
            strategy="hi_res",
        )

    assert isinstance(elements[0], Title)
    assert elements[0].text.startswith("LayoutParser")

    assert isinstance(elements[1], NarrativeText)
    assert elements[1].text.startswith("Zejiang Shen")


def test_partition_pdf_doesnt_raise_warning():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    # NOTE(robinson): This is the recommended way to check that no warning is emitted,
    # per the pytest docs.
    # ref: https://docs.pytest.org/en/7.0.x/how-to/capture-warnings.html
    #      #additional-use-cases-of-warnings-in-tests
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        partition(filename=filename, strategy="hi_res")


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.jpg")
    file_filename = filename if pass_file_filename else None
    elements = partition(
        filename=filename,
        file_filename=file_filename,
        content_type=content_type,
        strategy="hi_res",
    )
    assert len(elements) > 0


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg_from_file(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.jpg")
    file_filename = filename if pass_file_filename else None
    with open(filename, "rb") as f:
        elements = partition(
            file=f,
            file_filename=file_filename,
            content_type=content_type,
            strategy="hi_res",
        )
    assert len(elements) > 0


def test_auto_partition_raises_with_bad_type(monkeypatch):
    monkeypatch.setattr(auto, "detect_filetype", lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        partition(filename="made-up.fake", strategy="hi_res")


EXPECTED_PPTX_OUTPUT = [
    Title(text="Adding a Bullet Slide"),
    ListItem(text="Find the bullet slide layout"),
    ListItem(text="Use _TextFrame.text for first bullet"),
    ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
    NarrativeText(text="Here is a lot of text!"),
    NarrativeText(text="Here is some text in a text box!"),
]


def test_auto_partition_pptx_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_ppt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_with_page_breaks():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    elements = partition(filename=filename, include_page_breaks=True, strategy="hi_res")
    assert PageBreak() in elements


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition(filename=filename, strategy="hi_res")
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


EXPECTED_MSG_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_auto_partition_msg_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.msg")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements == EXPECTED_MSG_OUTPUT


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(rtf_not_supported, reason="RTF not supported in this version of pypandoc.")
def test_auto_partition_rtf_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-doc.rtf")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements[0] == Title("My First Heading")


def test_auto_partition_from_url():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"
    elements = partition(url=url, content_type="text/plain", strategy="hi_res")
    assert elements[0] == Title("Apache License")
    assert elements[0].metadata.url == url


def test_partition_md_works_with_embedded_html():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/README.md"
    elements = partition(url=url, content_type="text/markdown", strategy="hi_res")
    elements[0].text
    unstructured_found = False
    for element in elements:
        if "unstructured" in elements[0].text:
            unstructured_found = True
            break
    assert unstructured_found is True


def test_auto_partition_warns_if_header_set_and_not_url(caplog):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    partition(filename=filename, headers={"Accept": "application/pdf"}, strategy="hi_res")
    assert caplog.records[0].levelname == "WARNING"


def test_auto_partition_works_with_unstructured_jsons():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "spring-weather.html.json")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements[0].text == "News Around NOAA"


def test_auto_partition_works_with_unstructured_jsons_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "spring-weather.html.json")

    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")
    assert elements[0].text == "News Around NOAA"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(odt_not_supported, reason="odt not supported in this version of pypandoc.")
def test_auto_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements == [Title("Lorem ipsum dolor sit amet.")]


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(odt_not_supported, reason="odt not supported in this version of pypandoc.")
def test_auto_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")

    assert elements == [Title("Lorem ipsum dolor sit amet.")]


@pytest.mark.parametrize(
    ("content_type", "routing_func", "expected"),
    [
        ("application/json", "json", "application/json"),
        ("text/html", "html", "text/html"),
        ("jdsfjdfsjkds", "pdf", None),
    ],
)
def test_auto_adds_filetype_to_metadata(content_type, routing_func, expected):
    with patch(
        f"unstructured.partition.auto.partition_{routing_func}",
        lambda *args, **kwargs: [Text("text 1"), Text("text 2")],
    ):
        elements = partition("example-docs/layout-parser-paper-fast.pdf", content_type=content_type)
    assert len(elements) == 2
    assert all(el.metadata.filetype == expected for el in elements)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("application/pdf", FILETYPE_TO_MIMETYPE[FileType.PDF]),
        (None, FILETYPE_TO_MIMETYPE[FileType.PDF]),
    ],
)
def test_auto_filetype_overrides_file_specific(content_type, expected):
    pdf_metadata = ElementMetadata(filetype="imapdf")
    with patch(
        "unstructured.partition.auto.partition_pdf",
        lambda *args, **kwargs: [
            Text("text 1", metadata=pdf_metadata),
            Text("text 2", metadata=pdf_metadata),
        ],
    ):
        elements = partition("example-docs/layout-parser-paper-fast.pdf", content_type=content_type)
    assert len(elements) == 2
    assert all(el.metadata.filetype == expected for el in elements)


supported_filetypes = [
    _
    for _ in FileType
    if _
    not in (
        FileType.UNK,
        FileType.ZIP,
        FileType.XLS,
    )
]


FILETYPE_TO_MODULE = {
    FileType.JPG: "image",
    FileType.PNG: "image",
    FileType.TXT: "text",
    FileType.EML: "email",
}


@pytest.mark.parametrize("filetype", supported_filetypes)
def test_file_specific_produces_correct_filetype(filetype: FileType):
    if filetype in (FileType.JPG, FileType.PNG):
        pytest.skip()
    if (filetype is FileType.RTF) and (is_in_docker or rtf_not_supported):
        pytest.skip()
    if (filetype is FileType.ODT) and (is_in_docker or odt_not_supported):
        pytest.skip()
    if (filetype is FileType.EPUB) and is_in_docker:
        pytest.skip()
    extension = filetype.name.lower()
    filetype_module = (
        extension if filetype not in FILETYPE_TO_MODULE else FILETYPE_TO_MODULE[filetype]
    )
    fun_name = "partition_" + filetype_module
    module = import_module(f"unstructured.partition.{filetype_module}")  # noqa
    fun = eval(f"module.{fun_name}")
    for file in pathlib.Path("example-docs").iterdir():
        if file.is_file() and file.suffix == f".{extension}":
            elements = fun(str(file))
            assert all(el.metadata.filetype == FILETYPE_TO_MIMETYPE[filetype] for el in elements)
            break


def test_auto_partition_xml_from_filename(filename="example-docs/factbook.xml"):
    elements = partition(filename=filename, xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition(file=f, xml_keep_tags=False)

    assert elements[0].text == "United States"


def test_auto_partition_xml_from_filename_with_tags(filename="example-docs/factbook.xml"):
    elements = partition(filename=filename, xml_keep_tags=True)

    assert elements[5].text == "<name>United States</name>"
    assert elements[5].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file_with_tags(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition(file=f, xml_keep_tags=True)

    assert elements[5].text == "<name>United States</name>"


EXPECTED_XLSX_TABLE = """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>Team</td>
      <td>Location</td>
      <td>Stanley Cups</td>
    </tr>
    <tr>
      <td>Blues</td>
      <td>STL</td>
      <td>1</td>
    </tr>
    <tr>
      <td>Flyers</td>
      <td>PHI</td>
      <td>2</td>
    </tr>
    <tr>
      <td>Maple Leafs</td>
      <td>TOR</td>
      <td>13</td>
    </tr>
  </tbody>
</table>"""


EXPECTED_XLSX_TEXT = "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"

EXPECTED_XLSX_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_auto_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition(filename=filename)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_XLSX_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_XLSX_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_XLSX_FILETYPE


def test_auto_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition(file=f)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_XLSX_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_XLSX_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_XLSX_FILETYPE


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_csv_from_filename(filename="example-docs/stanley-cups.csv"):
    elements = partition(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_XLSX_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_XLSX_TABLE
    assert elements[0].metadata.filetype == "text/csv"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_csv_from_file(filename="example-docs/stanley-cups.csv"):
    with open(filename, "rb") as f:
        elements = partition(file=f)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_XLSX_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == EXPECTED_XLSX_TABLE
    assert elements[0].metadata.filetype == "text/csv"
