import json
import os
import pathlib
import warnings
from unittest.mock import patch

import docx
import pypandoc
import pytest

from unstructured.documents.elements import (
    Address,
    ListItem,
    NarrativeText,
    PageBreak,
    Text,
    Title,
)
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


def test_auto_partition_email_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    elements = partition(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
    assert elements[0].metadata.filename == filename


def test_auto_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename) as f:
        elements = partition(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_email_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename, "rb") as f:
        elements = partition(file=f)
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

    elements = partition(filename=filename)
    assert elements == expected_docx_elements
    assert elements[0].metadata.filename == filename


def test_auto_partition_docx_with_file(mock_docx_document, expected_docx_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_docx_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition(file=f)
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
    )
    assert elements == expected_docx_elements
    assert elements[0].metadata.filename == doc_filename


# NOTE(robinson) - the application/x-ole-storage mime type is not specific enough to
# determine that the file is an .doc document
@pytest.mark.xfail()
def test_auto_partition_doc_with_file(mock_docx_document, expected_docx_elements, tmpdir):
    docx_filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    doc_filename = os.path.join(tmpdir.dirname, "mock_document.doc")
    mock_docx_document.save(docx_filename)
    convert_office_doc(docx_filename, tmpdir.dirname, "doc")

    with open(doc_filename, "rb") as f:
        elements = partition(file=f)
    assert elements == expected_docx_elements


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_filename(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "example-10k.html")
    file_filename = filename if pass_file_filename else None
    elements = partition(filename=filename, file_filename=file_filename, content_type=content_type)
    assert len(elements) > 0
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_file(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    file_filename = filename if pass_file_filename else None
    with open(filename) as f:
        elements = partition(file=f, file_filename=file_filename, content_type=content_type)
    assert len(elements) > 0


def test_auto_partition_html_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    with open(filename, "rb") as f:
        elements = partition(file=f)
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
    json_elems = json.loads(elements_to_json(partition(filename=filename)))
    for elem in json_elems:
        # coordinates are always in the element data structures, even if None
        elem.pop("coordinates")
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
        json_elems = json.loads(elements_to_json(partition(file=partition_f)))
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
    elements = partition(filename=filename)
    assert len(elements) > 0
    assert elements == EXPECTED_TEXT_OUTPUT
    assert elements[0].metadata.filename == filename


def test_auto_partition_text_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        elements = partition(file=f)
    assert len(elements) > 0
    assert elements == EXPECTED_TEXT_OUTPUT


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_filename(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    file_filename = filename if pass_file_filename else None

    elements = partition(filename=filename, file_filename=file_filename, content_type=content_type)

    assert isinstance(elements[0], Title)
    assert elements[0].text.startswith("LayoutParser")

    assert isinstance(elements[1], NarrativeText)
    assert elements[1].text.startswith("Zejiang Shen")

    assert elements[0].metadata.filename == filename


def test_auto_partition_pdf_uses_table_extraction():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    with patch(
        "unstructured_inference.inference.layout.process_file_with_model",
    ) as mock_process_file_with_model:
        partition(filename, pdf_infer_table_structure=True)
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
        elements = partition(file=f, file_filename=file_filename, content_type=content_type)

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
        partition(filename=filename)


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "example.jpg")
    file_filename = filename if pass_file_filename else None
    elements = partition(filename=filename, file_filename=file_filename, content_type=content_type)
    assert len(elements) > 0


@pytest.mark.parametrize(
    ("pass_file_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpg_from_file(pass_file_filename, content_type):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "example.jpg")
    file_filename = filename if pass_file_filename else None
    with open(filename, "rb") as f:
        elements = partition(file=f, file_filename=file_filename, content_type=content_type)
    assert len(elements) > 0


def test_auto_partition_raises_with_bad_type(monkeypatch):
    monkeypatch.setattr(auto, "detect_filetype", lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        partition(filename="made-up.fake")


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
    elements = partition(filename=filename)
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == filename


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_ppt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition(filename=filename)
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == filename


def test_auto_with_page_breaks():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    elements = partition(filename=filename, include_page_breaks=True)
    assert PageBreak() in elements


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition(filename=filename)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition(file=f)
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
    elements = partition(filename=filename)
    assert elements == EXPECTED_MSG_OUTPUT


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
@pytest.mark.skipif(rtf_not_supported, reason="RTF not supported in this version of pypandoc.")
def test_auto_partition_rtf_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-doc.rtf")
    elements = partition(filename=filename)
    assert elements[0] == Title("My First Heading")


def test_auto_partition_from_url():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"
    elements = partition(url=url, content_type="text/plain")
    assert elements[0] == Title("Apache License")
    assert elements[0].metadata.url == url


def test_partition_md_works_with_embedded_html():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/README.md"
    elements = partition(url=url, content_type="text/markdown")
    elements[0].text
    unstructured_found = False
    for element in elements:
        if "unstructured" in elements[0].text:
            unstructured_found = True
            break
    assert unstructured_found is True


def test_auto_partition_warns_if_header_set_and_not_url(caplog):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    partition(filename=filename, headers={"Accept": "application/pdf"})
    assert caplog.records[0].levelname == "WARNING"
