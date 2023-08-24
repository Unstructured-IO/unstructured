import json
import os
import pathlib
import warnings
from importlib import import_module
from unittest.mock import patch

import docx
import pytest

from test_unstructured.partition.test_constants import EXPECTED_TABLE, EXPECTED_TEXT
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    Address,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)
from unstructured.file_utils.filetype import FILETYPE_TO_MIMETYPE, FileType
from unstructured.partition import auto
from unstructured.partition.auto import _get_partition_with_extras, partition
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

EML_TEST_FILE = "eml/fake-email.eml"

is_in_docker = os.path.exists("/.dockerenv")


def test_auto_partition_email_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
    elements = partition(filename=filename, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
    with open(filename) as f:
        elements = partition(file=f, strategy="hi_res")
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_email_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
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
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/msword"), (True, "application/msword"), (True, None)],
)
def test_auto_partition_doc_with_filename(
    mock_docx_document,
    expected_docx_elements,
    tmpdir,
    pass_metadata_filename,
    content_type,
):
    docx_filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    doc_filename = os.path.join(tmpdir.dirname, "mock_document.doc")
    mock_docx_document.save(docx_filename)
    convert_office_doc(docx_filename, tmpdir.dirname, "doc")
    metadata_filename = doc_filename if pass_metadata_filename else None
    elements = partition(
        filename=doc_filename,
        metadata_filename=metadata_filename,
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
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_filename(pass_metadata_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "example-10k.html")
    metadata_filename = filename if pass_metadata_filename else None
    elements = partition(
        filename=filename,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy="hi_res",
    )
    assert len(elements) > 0
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_file(pass_metadata_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    metadata_filename = filename if pass_metadata_filename else None
    with open(filename) as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
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
        "azure",
        "spring-weather.html.json",
    )
    with open(filename) as json_f:
        json_data = json.load(json_f)
    json_elems = json.loads(elements_to_json(partition(filename=filename, strategy="hi_res")))
    for elem in json_elems:
        elem.pop("metadata")
    for elem in json_data:
        elem.pop("metadata")
    assert json_data == json_elems


def test_auto_partition_json_raises_with_unprocessable_json(tmpdir):
    # NOTE(robinson) - This is unprocessable because it is not a list of dicts,
    # per the Unstructured ISD format
    text = '{"hi": "there"}'

    filename = os.path.join(tmpdir, "unprocessable.json")
    with open(filename, "w") as f:
        f.write(text)

    with pytest.raises(ValueError):
        partition(filename=filename)


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
        elem.pop("coordinate_system")
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
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_filename(pass_metadata_filename, content_type, request):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    metadata_filename = filename if pass_metadata_filename else None

    elements = partition(
        filename=filename,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy="hi_res",
    )

    assert isinstance(elements[0], Title)
    assert elements[0].text.startswith("LayoutParser")

    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]

    # NOTE(alan): Xfail since new model skips the word Zejiang
    request.applymarker(pytest.mark.xfail)

    assert isinstance(elements[1], NarrativeText)
    assert elements[1].text.startswith("Zejiang Shen")


def test_auto_partition_pdf_uses_table_extraction():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    with patch(
        "unstructured_inference.inference.layout.process_file_with_model",
    ) as mock_process_file_with_model:
        partition(filename, pdf_infer_table_structure=True, strategy="hi_res")
        assert mock_process_file_with_model.call_args[1]["extract_tables"]


def test_auto_partition_pdf_with_fast_strategy(monkeypatch):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")

    mock_return = [NarrativeText("Hello there!")]
    with patch.object(auto, "partition_pdf", return_value=mock_return) as mock_partition:
        mock_partition_with_extras_map = {"pdf": mock_partition}
        monkeypatch.setattr(auto, "PARTITION_WITH_EXTRAS_MAP", mock_partition_with_extras_map)
        partition(filename=filename, strategy="fast")

    mock_partition.assert_called_once_with(
        filename=filename,
        metadata_filename=None,
        file=None,
        url=None,
        include_page_breaks=False,
        infer_table_structure=False,
        strategy="fast",
        ocr_languages="eng",
    )


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_file(pass_metadata_filename, content_type, request):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    metadata_filename = filename if pass_metadata_filename else None

    with open(filename, "rb") as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
            content_type=content_type,
            strategy="hi_res",
        )

    assert isinstance(elements[0], Title)
    assert elements[0].text.startswith("LayoutParser")

    # NOTE(alan): Xfail since new model misses the first word Zejiang
    request.applymarker(pytest.mark.xfail)

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
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_image_default_strategy_hi_res(pass_metadata_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.jpg")
    metadata_filename = filename if pass_metadata_filename else None
    elements = partition(
        filename=filename,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy="auto",
    )

    # should be same result as test_partition_image_default_strategy_hi_res() in test_image.py
    first_line = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[0].text == first_line
    assert elements[0].metadata.coordinates is not None


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg(pass_metadata_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.jpg")
    metadata_filename = filename if pass_metadata_filename else None
    elements = partition(
        filename=filename,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy="auto",
    )
    assert len(elements) > 0


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg_from_file(pass_metadata_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.jpg")
    metadata_filename = filename if pass_metadata_filename else None
    with open(filename, "rb") as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
            content_type=content_type,
            strategy="auto",
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
    assert "PageBreak" in [elem.category for elem in elements]


def test_auto_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition(filename=filename, strategy="hi_res")
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


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
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
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


def test_auto_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition(filename=filename, strategy="hi_res")
    assert elements == [Title("Lorem ipsum dolor sit amet.")]


def test_auto_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy="hi_res")

    assert elements == [Title("Lorem ipsum dolor sit amet.")]


@pytest.mark.parametrize(
    ("content_type", "routing_func", "expected"),
    [
        ("text/csv", "csv", "text/csv"),
        ("text/html", "html", "text/html"),
        ("jdsfjdfsjkds", "pdf", None),
    ],
)
def test_auto_adds_filetype_to_metadata(content_type, routing_func, expected, monkeypatch):
    with patch(
        f"unstructured.partition.auto.partition_{routing_func}",
        lambda *args, **kwargs: [Text("text 1"), Text("text 2")],
    ) as mock_partition:
        mock_partition_with_extras_map = {routing_func: mock_partition}
        monkeypatch.setattr(auto, "PARTITION_WITH_EXTRAS_MAP", mock_partition_with_extras_map)
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
def test_auto_filetype_overrides_file_specific(content_type, expected, monkeypatch):
    pdf_metadata = ElementMetadata(filetype="imapdf")
    with patch(
        "unstructured.partition.auto.partition_pdf",
        lambda *args, **kwargs: [
            Text("text 1", metadata=pdf_metadata),
            Text("text 2", metadata=pdf_metadata),
        ],
    ) as mock_partition:
        mock_partition_with_extras_map = {"pdf": mock_partition}
        monkeypatch.setattr(auto, "PARTITION_WITH_EXTRAS_MAP", mock_partition_with_extras_map)
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
    if filetype in (FileType.JPG, FileType.PNG, FileType.TIFF, FileType.EMPTY):
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
            assert all(
                el.metadata.filetype == FILETYPE_TO_MIMETYPE[filetype]
                for el in elements
                if el.metadata.filetype is not None
            )
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

    assert elements[5].text == "<leader>Joe Biden</leader>"
    assert elements[5].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file_with_tags(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition(file=f, xml_keep_tags=True)

    assert elements[5].text == "<leader>Joe Biden</leader>"


EXPECTED_XLSX_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_auto_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition(filename=filename, include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_XLSX_FILETYPE


def test_auto_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition(file=f, include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 2

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.page_number == 1
    assert elements[0].metadata.filetype == EXPECTED_XLSX_FILETYPE


EXPECTED_XLS_TEXT_LEN = 507


EXPECTED_XLS_INITIAL_45_CLEAN_TEXT = "MA What C datatypes are 8 bits? (assume i386)"

EXPECTED_XLS_TABLE = (
    """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>MA</td>
      <td>What C datatypes are 8 bits? (assume i386)</td>
      <td>int</td>
      <td></td>
      <td>float</td>
      <td></td>
      <td>double</td>
      <td></td>
      <td>char</td>
    </tr>
    <tr>
      <td>TF</td>
      <td>Bagpipes are awesome.</td>
      <td>true</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>ESS</td>
      <td>How have the original Henry Hornbostel buildings """
    """influenced campus architecture and design in the last 30 years?</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>ORD</td>
      <td>Rank the following in their order of operation.</td>
      <td>Parentheses</td>
      <td>Exponents</td>
      <td>Division</td>
      <td>Addition</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>FIB</td>
      <td>The student activities fee is</td>
      <td>95</td>
      <td>dollars for students enrolled in</td>
      <td>19</td>
      <td>units or more,</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>MAT</td>
      <td>Match the lower-case greek letter with its capital form.</td>
      <td>λ</td>
      <td>Λ</td>
      <td>α</td>
      <td>γ</td>
      <td>Γ</td>
      <td>φ</td>
      <td>Φ</td>
    </tr>
  </tbody>
</table>"""
)


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_xls_from_filename(filename="example-docs/tests-example.xls"):
    elements = partition(filename=filename, include_header=False)

    assert all(isinstance(element, Table) for element in elements)
    assert len(elements) == 3

    assert clean_extra_whitespace(elements[0].text)[:45] == EXPECTED_XLS_INITIAL_45_CLEAN_TEXT
    # NOTE(crag): if the beautifulsoup4 package is installed, some (but not all) additional
    # whitespace is removed, so the expected text length is less than is the case
    # when beautifulsoup4 is *not* installed. E.g.
    # "\n\n\nMA\nWhat C datatypes are 8 bits" vs.
    # '\n  \n    \n      MA\n      What C datatypes are 8 bits?... "
    assert len(elements[0].text) == EXPECTED_XLS_TEXT_LEN
    assert elements[0].metadata.text_as_html == EXPECTED_XLS_TABLE


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_csv_from_filename(filename="example-docs/stanley-cups.csv"):
    elements = partition(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/csv"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_tsv_from_filename(filename="example-docs/stanley-cups.tsv"):
    elements = partition(filename=filename)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/tsv"


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_csv_from_file(filename="example-docs/stanley-cups.csv"):
    with open(filename, "rb") as f:
        elements = partition(file=f)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/csv"


def test_auto_partition_html_pre_from_file(filename="example-docs/fake-html-pre.htm"):
    elements = partition(filename=filename)

    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert clean_extra_whitespace(elements[0].text) == "[107th Congress Public Law 56]"
    assert isinstance(elements[0], Title)
    assert elements[0].metadata.filetype == "text/html"
    assert elements[0].metadata.filename == "fake-html-pre.htm"


def test_auto_partition_works_on_empty_filename(filename="example-docs/empty.txt"):
    assert partition(filename=filename) == []


def test_auto_partition_works_on_empty_file(filename="example-docs/empty.txt"):
    with open(filename, "rb") as f:
        assert partition(file=f) == []


def test_auto_partition_org_from_filename(filename="example-docs/README.org"):
    elements = partition(filename=filename)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_auto_partition_org_from_file(filename="example-docs/README.org"):
    with open(filename, "rb") as f:
        elements = partition(file=f, content_type="text/org")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_auto_partition_rst_from_filename(filename="example-docs/README.rst"):
    elements = partition(filename=filename)

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


def test_auto_partition_rst_from_file(filename="example-docs/README.rst"):
    with open(filename, "rb") as f:
        elements = partition(file=f, content_type="text/x-rst")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


def test_auto_partition_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        elements = partition(file=f, metadata_filename=filename)
    assert elements[0].metadata.filename == os.path.split(filename)[-1]


def test_auto_partition_warns_about_file_filename_deprecation(caplog):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        elements = partition(file=f, file_filename=filename)
    assert elements[0].metadata.filename == os.path.split(filename)[-1]
    assert "WARNING" in caplog.text
    assert "The file_filename kwarg will be deprecated" in caplog.text


def test_auto_partition_raises_with_file_and_metadata_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f, pytest.raises(ValueError):
        partition(file=f, file_filename=filename, metadata_filename=filename)


def test_get_partition_with_extras_prompts_for_install_if_missing():
    partition_with_extras_map = {}
    with pytest.raises(ImportError) as exception_info:
        _get_partition_with_extras("pdf", partition_with_extras_map)

    msg = str(exception_info.value)
    assert 'Install the pdf dependencies with pip install "unstructured[pdf]"' in msg
