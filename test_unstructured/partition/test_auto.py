import json
import os
import pathlib
import warnings
from importlib import import_module
from unittest.mock import ANY, Mock, patch

import docx
import pytest

from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT,
    EXPECTED_TEXT_XLSX,
    EXPECTED_TITLE,
)
from unstructured.chunking.title import chunk_by_title
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    Address,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.file_utils.filetype import FILETYPE_TO_MIMETYPE, FileType
from unstructured.partition import auto
from unstructured.partition.auto import _get_partition_with_extras, partition
from unstructured.partition.common import convert_office_doc
from unstructured.partition.utils.constants import PartitionStrategy
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
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_email_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
    with open(filename) as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_email_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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

    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements == expected_docx_elements
    assert elements[0].metadata.filename == os.path.basename(filename)


def test_auto_partition_docx_with_file(mock_docx_document, expected_docx_elements, tmpdir):
    filename = os.path.join(tmpdir.dirname, "mock_document.docx")
    mock_docx_document.save(filename)

    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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
        strategy=PartitionStrategy.HI_RES,
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
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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
        strategy=PartitionStrategy.HI_RES,
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
            strategy=PartitionStrategy.HI_RES,
        )
    assert len(elements) > 0


def test_auto_partition_html_from_file_rb():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-html.html")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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
    json_elems = json.loads(
        elements_to_json(partition(filename=filename, strategy=PartitionStrategy.HI_RES))
    )
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
        json_elems = json.loads(
            elements_to_json(partition(file=partition_f, strategy=PartitionStrategy.HI_RES))
        )
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
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert len(elements) > 0
    assert elements == EXPECTED_TEXT_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_partition_text_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename) as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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
        strategy=PartitionStrategy.HI_RES,
    )

    idx = 3
    assert isinstance(elements[idx], Title)
    assert elements[idx].text.startswith("LayoutParser")

    assert elements[idx].metadata.filename == os.path.basename(filename)
    assert elements[idx].metadata.file_directory == os.path.split(filename)[0]

    # NOTE(alan): Xfail since new model skips the word Zejiang
    request.applymarker(pytest.mark.xfail)

    idx += 1
    assert isinstance(elements[idx], NarrativeText)
    assert elements[idx].text.startswith("Zejiang Shen")


def test_auto_partition_pdf_uses_table_extraction():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    with patch(
        "unstructured.partition.ocr.process_file_with_ocr",
    ) as mock_process_file_with_model:
        partition(filename, pdf_infer_table_structure=True, strategy=PartitionStrategy.HI_RES)
        assert mock_process_file_with_model.call_args[1]["infer_table_structure"]


def test_auto_partition_pdf_with_fast_strategy(monkeypatch):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")

    mock_return = [NarrativeText("Hello there!")]
    with patch.object(auto, "partition_pdf", return_value=mock_return) as mock_partition:
        mock_partition_with_extras_map = {"pdf": mock_partition}
        monkeypatch.setattr(auto, "PARTITION_WITH_EXTRAS_MAP", mock_partition_with_extras_map)
        partition(filename=filename, strategy=PartitionStrategy.FAST)

    mock_partition.assert_called_once_with(
        filename=filename,
        metadata_filename=None,
        file=None,
        url=None,
        include_page_breaks=False,
        infer_table_structure=False,
        extract_images_in_pdf=ANY,
        image_output_dir_path=ANY,
        strategy=PartitionStrategy.FAST,
        languages=None,
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
            strategy=PartitionStrategy.HI_RES,
        )

    idx = 3
    assert isinstance(elements[idx], Title)
    assert elements[idx].text.startswith("LayoutParser")

    # NOTE(alan): Xfail since new model misses the first word Zejiang
    request.applymarker(pytest.mark.xfail)

    idx += 1
    assert isinstance(elements[idx], NarrativeText)
    assert elements[idx].text.startswith("Zejiang Shen")


def test_auto_partition_formats_languages_for_tesseract():
    filename = "example-docs/chi_sim_image.jpeg"
    with patch(
        "unstructured.partition.ocr.process_file_with_ocr",
    ) as mock_process_file_with_ocr:
        partition(filename, strategy=PartitionStrategy.HI_RES, languages=["zh"])
        _, kwargs = mock_process_file_with_ocr.call_args_list[0]
        assert "ocr_languages" in kwargs
        assert kwargs["ocr_languages"] == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"


def test_auto_partition_element_metadata_user_provided_languages():
    filename = "example-docs/chevron-page.pdf"
    elements = partition(filename=filename, strategy=PartitionStrategy.OCR_ONLY, languages=["eng"])
    assert elements[0].metadata.languages == ["eng"]


@pytest.mark.parametrize(
    ("languages", "ocr_languages"),
    [(["auto"], ""), (["eng"], "")],
)
def test_auto_partition_ignores_empty_string_for_ocr_languages(languages, ocr_languages):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "book-war-and-peace-1p.txt")
    elements = partition(
        filename=filename,
        strategy=PartitionStrategy.OCR_ONLY,
        ocr_languages=ocr_languages,
        languages=languages,
    )
    assert elements[0].metadata.languages == ["eng"]


def test_auto_partition_warns_with_ocr_languages(caplog):
    filename = "example-docs/chevron-page.pdf"
    partition(filename=filename, strategy=PartitionStrategy.HI_RES, ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_partition_pdf_doesnt_raise_warning():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    # NOTE(robinson): This is the recommended way to check that no warning is emitted,
    # per the pytest docs.
    # ref: https://docs.pytest.org/en/7.0.x/how-to/capture-warnings.html
    #      #additional-use-cases-of-warnings-in-tests
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        partition(filename=filename, strategy=PartitionStrategy.HI_RES)


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
        strategy=PartitionStrategy.AUTO,
    )

    # should be same result as test_partition_image_default_strategy_hi_res() in test_image.py
    title = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    idx = 3
    assert elements[idx].text == title
    assert elements[idx].metadata.coordinates is not None


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
        strategy=PartitionStrategy.AUTO,
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
            strategy=PartitionStrategy.AUTO,
        )
    assert len(elements) > 0


def test_auto_partition_raises_with_bad_type(monkeypatch):
    monkeypatch.setattr(auto, "detect_filetype", lambda *args, **kwargs: None)
    with pytest.raises(ValueError):
        partition(filename="made-up.fake", strategy=PartitionStrategy.HI_RES)


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
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_auto_partition_ppt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.ppt")
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements == EXPECTED_PPTX_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(filename)
    assert elements[0].metadata.file_directory == os.path.split(filename)[0]


def test_auto_with_page_breaks():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "layout-parser-paper-fast.pdf")
    elements = partition(
        filename=filename, include_page_breaks=True, strategy=PartitionStrategy.HI_RES
    )
    assert "PageBreak" in [elem.category for elem in elements]


def test_auto_partition_epub_from_filename():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


def test_auto_partition_epub_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "example-docs", "winter-sports.epub")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
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
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements == EXPECTED_MSG_OUTPUT


def test_auto_partition_rtf_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-doc.rtf")
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements[0] == Title("My First Heading")


def test_auto_partition_from_url():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"
    elements = partition(url=url, content_type="text/plain", strategy=PartitionStrategy.HI_RES)
    assert elements[0] == Title("Apache License")
    assert elements[0].metadata.url == url


def test_partition_md_works_with_embedded_html():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/README.md"
    elements = partition(url=url, content_type="text/markdown", strategy=PartitionStrategy.HI_RES)
    elements[0].text
    unstructured_found = False
    for element in elements:
        if "unstructured" in elements[0].text:
            unstructured_found = True
            break
    assert unstructured_found is True


def test_auto_partition_warns_if_header_set_and_not_url(caplog):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, EML_TEST_FILE)
    partition(
        filename=filename, headers={"Accept": "application/pdf"}, strategy=PartitionStrategy.HI_RES
    )
    assert caplog.records[0].levelname == "WARNING"


def test_auto_partition_works_with_unstructured_jsons():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "spring-weather.html.json")
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements[0].text == "News Around NOAA"


def test_auto_partition_works_with_unstructured_jsons_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "spring-weather.html.json")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
    assert elements[0].text == "News Around NOAA"


def test_auto_partition_odt_from_filename():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    elements = partition(filename=filename, strategy=PartitionStrategy.HI_RES)
    assert elements[0] == Title("Lorem ipsum dolor sit amet.")


def test_auto_partition_odt_from_file():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.odt")
    with open(filename, "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)

    assert elements[0] == Title("Lorem ipsum dolor sit amet.")


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
    elements = partition(filename=filename, xml_keep_tags=False, metadata_filename=filename)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition(file=f, xml_keep_tags=False)

    assert elements[0].text == "United States"


def test_auto_partition_xml_from_filename_with_tags(filename="example-docs/factbook.xml"):
    elements = partition(filename=filename, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file_with_tags(filename="example-docs/factbook.xml"):
    with open(filename, "rb") as f:
        elements = partition(file=f, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text


EXPECTED_XLSX_FILETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_auto_partition_xlsx_from_filename(filename="example-docs/stanley-cups.xlsx"):
    elements = partition(filename=filename, include_header=False, skip_infer_table_types=[])

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_XLSX_FILETYPE


@pytest.mark.parametrize(
    ("skip_infer_table_types", "filename", "has_text_as_html_field"),
    [
        (["xlsx"], "stanley-cups.xlsx", False),
        ([], "stanley-cups.xlsx", True),
        (["odt"], "fake.odt", False),
        ([], "fake.odt", True),
    ],
)
def test_auto_partition_respects_skip_infer_table_types(
    skip_infer_table_types,
    filename,
    has_text_as_html_field,
):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, filename)
    with open(filename, "rb") as f:
        table_elements = [
            e
            for e in partition(file=f, skip_infer_table_types=skip_infer_table_types)
            if isinstance(e, Table)
        ]
        for table_element in table_elements:
            table_element_has_text_as_html_field = (
                hasattr(table_element.metadata, "text_as_html")
                and table_element.metadata.text_as_html is not None
            )
        assert table_element_has_text_as_html_field == has_text_as_html_field


def test_auto_partition_xlsx_from_file(filename="example-docs/stanley-cups.xlsx"):
    with open(filename, "rb") as f:
        elements = partition(file=f, include_header=False, skip_infer_table_types=[])

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert len(elements) == 4

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TITLE
    assert clean_extra_whitespace(elements[1].text) == EXPECTED_TEXT_XLSX
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert elements[1].metadata.page_number == 1
    assert elements[1].metadata.filetype == EXPECTED_XLSX_FILETYPE


EXPECTED_XLS_TEXT_LEN = 550


EXPECTED_XLS_INITIAL_45_CLEAN_TEXT = "MC What is 2+2? 4 correct 3 incorrect MA What"

EXPECTED_XLS_TABLE = (
    """<table border="1" class="dataframe">
  <tbody>
    <tr>
      <td>MC</td>
      <td>What is 2+2?</td>
      <td>4</td>
      <td>correct</td>
      <td>3</td>
      <td>incorrect</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
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
    elements = partition(filename=filename, include_header=False, skip_infer_table_types=[])

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 18

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
    assert clean_extra_whitespace(elements[0].text).startswith("[107th Congress Public Law 56]")
    assert isinstance(elements[0], NarrativeText)
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


def test_add_chunking_strategy_on_partition_auto():
    filename = "example-docs/example-10k-1p.html"
    elements = partition(filename)
    chunk_elements = partition(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_title_on_partition_auto_respects_multipage():
    filename = "example-docs/example-10k-1p.html"
    partitioned_elements_multipage_false_combine_chars_0 = partition(
        filename,
        chunking_strategy="by_title",
        multipage_sections=False,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    partitioned_elements_multipage_true_combine_chars_0 = partition(
        filename,
        chunking_strategy="by_title",
        multipage_sections=True,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    elements = partition(filename)
    cleaned_elements_multipage_false_combine_chars_0 = chunk_by_title(
        elements,
        multipage_sections=False,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    cleaned_elements_multipage_true_combine_chars_0 = chunk_by_title(
        elements,
        multipage_sections=True,
        combine_text_under_n_chars=0,
        new_after_n_chars=300,
        max_characters=400,
    )
    assert (
        partitioned_elements_multipage_false_combine_chars_0
        == cleaned_elements_multipage_false_combine_chars_0
    )
    assert (
        partitioned_elements_multipage_true_combine_chars_0
        == cleaned_elements_multipage_true_combine_chars_0
    )
    assert len(partitioned_elements_multipage_true_combine_chars_0) != len(
        partitioned_elements_multipage_false_combine_chars_0,
    )


def test_add_chunking_strategy_on_partition_auto_respects_max_chars():
    filename = "example-docs/example-10k-1p.html"

    # default chunk size in chars is 200
    partitioned_table_elements_200_chars = [
        e
        for e in partition(
            filename,
            chunking_strategy="by_title",
            max_characters=200,
            combine_text_under_n_chars=5,
        )
        if isinstance(e, (Table, TableChunk))
    ]

    partitioned_table_elements_5_chars = [
        e
        for e in partition(
            filename,
            chunking_strategy="by_title",
            max_characters=5,
            combine_text_under_n_chars=5,
        )
        if isinstance(e, (Table, TableChunk))
    ]

    elements = partition(filename)

    table_elements = [e for e in elements if isinstance(e, Table)]

    assert len(partitioned_table_elements_5_chars) != len(table_elements)
    assert len(partitioned_table_elements_200_chars) != len(table_elements)

    assert len(partitioned_table_elements_5_chars[0].text) == 5
    assert len(partitioned_table_elements_5_chars[0].metadata.text_as_html) == 5

    # the first table element is under 200 chars so doesn't get chunked!
    assert table_elements[0] == partitioned_table_elements_200_chars[0]
    assert len(partitioned_table_elements_200_chars[0].text) < 200
    assert len(partitioned_table_elements_200_chars[1].text) == 200
    assert len(partitioned_table_elements_200_chars[1].metadata.text_as_html) == 200


def test_add_chunking_strategy_chars_on_partition_auto_adds_is_continuation():
    filename = "example-docs/example-10k-1p.html"

    table_elements = [e for e in partition(filename) if isinstance(e, Table)]
    chunked_table_elements = [
        e
        for e in partition(
            filename,
            chunking_strategy="by_title",
        )
        if isinstance(e, Table)
    ]

    assert table_elements != chunked_table_elements

    i = 0
    for table in chunked_table_elements:
        # have to reset the counter to 0 here when we encounter a Table element
        if isinstance(table, Table):
            i = 0
        if i > 0 and isinstance(table, TableChunk):
            assert table.metadata.is_continuation is True
            i += 1


EXAMPLE_LANG_DOCS = "example-docs/language-docs/eng_spa_mult."


@pytest.mark.parametrize(
    "file_extension",
    [
        "doc",
        "docx",
        "eml",
        "epub",
        "html",
        "md",
        "odt",
        "org",
        "ppt",
        "pptx",
        "rst",
        "rtf",
        "txt",
        "xml",
    ],
)
def test_partition_respects_language_arg(file_extension):
    filename = EXAMPLE_LANG_DOCS + file_extension
    elements = partition(filename=filename, languages=["deu"])
    assert all(element.metadata.languages == ["deu"] for element in elements)


def test_partition_respects_detect_language_per_element_arg():
    filename = "example-docs/language-docs/eng_spa_mult.txt"
    elements = partition(filename=filename, detect_language_per_element=True)
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


# check that the ["eng"] default in `partition` does not overwrite the ["auto"]
# default in other `partition_` functions.
def test_partition_default_does_not_overwrite_other_defaults():
    # the default for `languages` is ["auto"] in partiton_text
    from unstructured.partition.text import partition_text

    # Use a document that is primarily in a language other than English
    filename = "example-docs/language-docs/UDHR_first_article_all.txt"
    text_elements = partition_text(filename)
    assert text_elements[0].metadata.languages != ["eng"]

    auto_elements = partition(filename)
    assert auto_elements[0].metadata.languages != ["eng"]
    assert auto_elements[0].metadata.languages == text_elements[0].metadata.languages


def test_partition_languages_default_to_None():
    filename = "example-docs/handbook-1p.docx"
    elements = partition(filename=filename, detect_language_per_element=True)
    # PageBreak and other elements with no text will have `None` for `languages`
    none_langs = [element for element in elements if element.metadata.languages is None]
    assert none_langs[0].text == ""


def test_partition_languages_incorrectly_defaults_to_English(tmpdir):
    # We don't totally rely on langdetect for short text, so text like the following that is
    # in German will be labeled as English.
    german = "Ein kurzer Satz."
    filepath = os.path.join(tmpdir, "short-german.txt")
    with open(filepath, "w") as f:
        f.write(german)
    elements = partition(filepath)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_timeout_gets_routed():
    class CallException(Exception):
        pass

    mock_ocr_func = Mock(side_effect=CallException("Function called!"))
    with patch("unstructured.partition.auto.file_and_type_from_url", mock_ocr_func), pytest.raises(
        CallException
    ):
        auto.partition(url="fake_url", request_timeout=326)
    kwargs = mock_ocr_func.call_args.kwargs
    assert "request_timeout" in kwargs
    assert kwargs["request_timeout"] == 326
