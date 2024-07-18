# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.file_utils.filetype`."""

from __future__ import annotations

import io
import os
import pathlib

import magic
import pytest

from test_unstructured.unit_utils import (
    FixtureRequest,
    LogCaptureFixture,
    Mock,
    MonkeyPatch,
    call,
    example_doc_path,
    method_mock,
)
from unstructured.file_utils import filetype
from unstructured.file_utils.filetype import (
    _detect_filetype_from_octet_stream,
    _is_code_mime_type,
    _is_text_file_a_csv,
    _is_text_file_a_json,
    detect_filetype,
)
from unstructured.file_utils.model import FileType

is_in_docker = os.path.exists("/.dockerenv")


@pytest.mark.parametrize(
    ("file_name", "expected_value"),
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("eml/fake-email.eml", FileType.EML),
        ("factbook.xml", FileType.XML),
        ("example-10k.html", FileType.HTML),
        ("fake-html.html", FileType.HTML),
        ("stanley-cups.xlsx", FileType.XLSX),
        ("stanley-cups.csv", FileType.CSV),
        ("stanley-cups.tsv", FileType.TSV),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
        ("spring-weather.html.json", FileType.JSON),
        ("README.org", FileType.ORG),
        ("README.rst", FileType.RST),
        ("README.md", FileType.MD),
        ("fake.odt", FileType.ODT),
        ("fake-incomplete-json.txt", FileType.TXT),
    ],
)
def test_detect_filetype_from_filename(file_name: str, expected_value: FileType):
    assert detect_filetype(example_doc_path(file_name)) == expected_value


@pytest.mark.parametrize(
    ("file_name", "expected_value"),
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("eml/fake-email.eml", FileType.EML),
        ("factbook.xml", FileType.XML),
        ("example-10k.html", FileType.HTML),
        ("fake-html.html", FileType.HTML),
        ("stanley-cups.xlsx", FileType.XLSX),
        ("stanley-cups.csv", FileType.CSV),
        ("stanley-cups.tsv", FileType.TSV),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
        ("fake-doc.rtf", FileType.RTF),
        ("spring-weather.html.json", FileType.JSON),
        ("fake.odt", FileType.ODT),
        ("fake-incomplete-json.txt", FileType.TXT),
    ],
)
def test_detect_filetype_from_filename_with_extension(
    file_name: str, expected_value: FileType, monkeypatch: MonkeyPatch
):
    """File-type is detected from extension when libmagic not available or file does not exist."""
    # -- when libmagic is not available --
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", False)
    assert detect_filetype(example_doc_path(file_name)) == expected_value
    # -- when file does not exist --
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", True)
    extension = pathlib.Path(file_name).suffix
    assert detect_filetype(example_doc_path("not-on-disk" + extension)) == expected_value


@pytest.mark.parametrize(
    ("file_name", "expected_value"),
    [
        ("pdf/layout-parser-paper-fast.pdf", [FileType.PDF]),
        ("fake.docx", [FileType.DOCX]),
        ("img/example.jpg", [FileType.JPG]),
        ("fake-text.txt", [FileType.TXT]),
        ("eml/fake-email.eml", [FileType.EML]),
        ("factbook.xml", [FileType.XML]),
        # NOTE(robinson]) - For the document, some operating systems return
        # */xml and some return */html. Either could be acceptable depending on the OS
        ("example-10k.html", [FileType.HTML, FileType.XML]),
        ("fake-html.html", [FileType.HTML]),
        ("stanley-cups.xlsx", [FileType.XLSX]),
        ("stanley-cups.csv", [FileType.CSV]),
        ("stanley-cups.tsv", [FileType.TSV]),
        ("fake-power-point.pptx", [FileType.PPTX]),
        ("winter-sports.epub", [FileType.EPUB]),
        ("fake-incomplete-json.txt", [FileType.TXT]),
    ],
)
def test_detect_filetype_from_file(file_name: str, expected_value: list[FileType]):
    with open(example_doc_path(file_name), "rb") as f:
        assert detect_filetype(file=f) in expected_value


def test_detect_filetype_from_file_warns_when_libmagic_is_not_installed(
    monkeypatch: MonkeyPatch, caplog: LogCaptureFixture
):
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", False)
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        detect_filetype(file=f)

    assert "WARNING" in caplog.text


def test_detect_XML_from_application_xml_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/xml"
    file_path = example_doc_path("factbook.xml")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.XML


def test_detect_CSV_from_text_csv_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "text/csv"
    file_path = example_doc_path("stanley-cups.csv")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.CSV


def test_detect_TXT_from_text_x_script_python_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "text/x-script.python"
    file_path = example_doc_path("logger.py")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.TXT


def test_detect_TXT_from_text_x_script_python_file(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "text/x-script.python"
    file_path = example_doc_path("logger.py")

    with open(file_path, "rb") as f:
        head = f.read(4096)
        f.seek(0)
        filetype = detect_filetype(file=f)

    magic_from_buffer_.assert_called_once_with(head, mime=True)
    assert filetype == FileType.TXT


def test_is_code_mime_type_for_Go():
    assert _is_code_mime_type("text/x-go") is True


def test_detect_TXT_from_text_go_file(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "text/x-go"
    file_path = example_doc_path("fake.go")

    with open(file_path, "rb") as f:
        head = f.read(4096)
        f.seek(0)
        filetype = detect_filetype(file=f)

    magic_from_buffer_.assert_called_once_with(head, mime=True)
    assert filetype == FileType.TXT


def test_detect_RTF_from_application_rtf_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/rtf"
    file_path = example_doc_path("fake-doc.rtf")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.RTF


def test_detect_XML_from_text_xml_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "text/xml"
    file_path = example_doc_path("factbook.xml")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.XML


def test_detect_HTML_from_application_xml_file_path_with_html_extension(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/xml"
    file_path = example_doc_path("fake-html.html")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.HTML


def test_detect_HTML_from_text_xml_file_path_with_html_extension(magic_from_file_: Mock):
    magic_from_file_.return_value = "text/xml"
    file_path = example_doc_path("fake-html.html")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.HTML


def test_detect_DOCX_from_application_octet_stream_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "application/octet-stream"
    with open(example_doc_path("simple.docx"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.DOCX


def test_detect_DOCX_from_application_octet_stream_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/octet-stream"
    file_path = example_doc_path("simple.docx")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.DOCX


def test_detect_DOCX_from_application_zip_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/zip"
    file_path = example_doc_path("simple.docx")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.DOCX


def test_detect_ZIP_from_application_zip_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/zip"
    file_path = example_doc_path("simple.zip")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.ZIP


def test_detect_DOC_from_application_msword_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/msword"
    file_path = example_doc_path("fake.doc")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.DOC


def test_detect_PPT_from_application_vnd_ms_powerpoint_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/vnd.ms-powerpoint"
    file_path = example_doc_path("fake-power-point.ppt")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.PPT


def test_detect_XLS_from_application_vnd_ms_excel_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/vnd.ms-excel"
    file_path = example_doc_path("tests-example.xls")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.XLS


def test_detect_XLSX_from_application_octet_stream_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "application/octet-stream"
    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.XLSX


def test_detect_XLSX_from_application_octet_stream_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/octet-stream"
    file_path = example_doc_path("stanley-cups.xlsx")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.XLSX


def test_detect_PPTX_from_application_octet_stream_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "application/octet-stream"
    with open(example_doc_path("fake-power-point.pptx"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.PPTX


def test_detect_PPTX_from_application_octet_stream_file_path(magic_from_file_: Mock):
    magic_from_file_.return_value = "application/octet-stream"
    file_path = example_doc_path("fake-power-point.pptx")

    filetype = detect_filetype(file_path)

    magic_from_file_.assert_called_once_with(file_path, mime=True)
    assert filetype == FileType.PPTX


def test_detect_UNK_from_application_octet_stream_text_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "application/octet-stream"
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    assert magic_from_buffer_.call_args_list == [
        call(file.getvalue()[:4096], mime=True),
        call(b"", mime=True),
    ]
    assert filetype == FileType.UNK


def test_detect_ZIP_from_application_zip_not_a_zip_file(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "application/zip"

    with open(example_doc_path("fake-text.txt"), "rb") as f:
        head = f.read(4096)
        f.seek(0)
        filetype = detect_filetype(file=f)

    assert magic_from_buffer_.call_args_list == [
        call(head, mime=True),
        call(b"", mime=True),
    ]
    assert filetype == FileType.ZIP


def test_detect_DOCX_from_docx_mime_type_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    with open(example_doc_path("simple.docx"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.DOCX


def test_detect_XLSX_from_xlsx_mime_type_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.XLSX


def test_detect_UNK_from_extension_of_non_existent_file_path():
    assert detect_filetype(example_doc_path("made_up.fake")) == FileType.UNK


def test_detect_PNG_from_extension_of_non_existent_file_path():
    assert detect_filetype(example_doc_path("made_up.png")) == FileType.PNG


def test_detect_TXT_from_unknown_text_subtype_file_no_extension(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "text/new-type"
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    magic_from_buffer_.assert_called_once_with(file.getvalue()[:4096], mime=True)
    assert filetype == FileType.TXT


def test_detect_BMP_from_file_path():
    assert detect_filetype(example_doc_path("bmp_24.bmp")) == FileType.BMP


def test_detect_BMP_from_file_no_extension():
    with open(example_doc_path("img/bmp_24.bmp"), "rb") as f:
        file = io.BytesIO(f.read())
    assert detect_filetype(file=file) == FileType.BMP


def test_detect_filetype_raises_when_both_path_and_file_like_object_are_specified():
    file_path = example_doc_path("fake-email.eml")
    with open(example_doc_path(file_path), "rb") as f:
        file = io.BytesIO(f.read())

    with pytest.raises(ValueError, match="Exactly one of filename and file must be specified."):
        detect_filetype(filename=file_path, file=file)


def test_detect_filetype_raises_with_neither_path_or_file_like_object_specified():
    with pytest.raises(ValueError, match="Exactly one of filename and file must be specified."):
        detect_filetype()


def test_FileType_is_ordererd_by_name():
    """FileType is a total order on name, e.g. FileType.A < FileType.B."""
    assert FileType.EML < FileType.HTML < FileType.XML


@pytest.mark.parametrize(
    ("content", "expected_value"),
    [
        (b"d\xe2\x80", False),  # Invalid JSON
        (b'[{"key": "value"}]', True),  # Valid JSON
        (b"", False),  # Empty content
        (b'"This is not a JSON"', False),  # Serializable as JSON, but we want to treat it as txt
    ],
)
def test_is_text_file_a_json_distinguishes_JSON_from_text(content: bytes, expected_value: bool):
    with io.BytesIO(content) as f:
        assert _is_text_file_a_json(file=f) == expected_value


@pytest.mark.parametrize(
    ("content", "expected_value"),
    [
        (b"d\xe2\x80", False),  # Invalid CSV
        (b'[{"key": "value"}]', False),  # Invalid CSV
        (b"column1,column2,column3\nvalue1,value2,value3\n", True),  # Valid CSV
        (b"", False),  # Empty content
    ],
)
def test_is_text_file_a_csv_distinguishes_CSV_from_text(content: bytes, expected_value: bool):
    with io.BytesIO(content) as f:
        assert _is_text_file_a_csv(file=f) == expected_value


def test_csv_and_json_checks_with_filename_accommodate_utf_32_encoded_file():
    file_path = example_doc_path("fake-text-utf-32.txt")
    assert _is_text_file_a_csv(filename=file_path) is False
    assert _is_text_file_a_json(filename=file_path) is False


def test_csv_and_json_checks_with_file_accommodate_utf_32_encoded_content():
    with open(example_doc_path("fake-text-utf-32.txt"), "rb") as f:
        file = io.BytesIO(f.read())

    assert _is_text_file_a_csv(file=file) is False
    file.seek(0)
    assert _is_text_file_a_json(file=file) is False


def test_detect_EMPTY_from_file_path_to_empty_file():
    assert detect_filetype(example_doc_path("empty.txt")) == FileType.EMPTY


def test_detect_EMPTY_from_file_that_is_empty():
    with open(example_doc_path("empty.txt"), "rb") as f:
        assert detect_filetype(file=f) == FileType.EMPTY


def test_detect_CSV_from_path_and_file_when_content_contains_escaped_commas():
    file_path = example_doc_path("csv-with-escaped-commas.csv")

    assert detect_filetype(filename=file_path) == FileType.CSV
    with open(file_path, "rb") as f:
        assert detect_filetype(file=f) == FileType.CSV


def test_detect_filetype_from_octet_stream():
    with open(example_doc_path("emoji.xlsx"), "rb") as f:
        assert _detect_filetype_from_octet_stream(file=f) == FileType.XLSX


def test_detect_WAV_from_filename():
    assert detect_filetype(example_doc_path("CantinaBand3.wav")) == FileType.WAV


def test_detect_wav_from_file():
    with open(example_doc_path("CantinaBand3.wav"), "rb") as f:
        assert detect_filetype(file=f) == FileType.WAV


def test_detect_TXT_from_file_path_to_yaml():
    assert detect_filetype(example_doc_path("simple.yaml")) == FileType.TXT


def test_detect_TXT_from_yaml_file(magic_from_buffer_: Mock):
    magic_from_buffer_.return_value = "text/yaml"

    with open(example_doc_path("simple.yaml"), "rb") as f:
        head = f.read(4096)
        f.seek(0)
        file_type = detect_filetype(file=f)

    magic_from_buffer_.assert_called_once_with(head, mime=True)
    assert file_type == FileType.TXT


# ================================================================================================
# MODULE-LEVEL FIXTURES
# ================================================================================================


# -- `from_buffer()` and `from_file()` are not "methods" on `magic` per-se (`magic` is a module)
# -- but they behave like methods for mocking purposes.
@pytest.fixture()
def magic_from_buffer_(request: FixtureRequest):
    return method_mock(request, magic, "from_buffer")


@pytest.fixture()
def magic_from_file_(request: FixtureRequest):
    return method_mock(request, magic, "from_file")
