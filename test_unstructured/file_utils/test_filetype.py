import os
import pathlib
import zipfile

import magic
import pytest

from unstructured.file_utils import filetype
from unstructured.file_utils.filetype import (
    DOCX_MIME_TYPES,
    XLSX_MIME_TYPES,
    FileType,
    detect_filetype,
)

FILE_DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(FILE_DIRECTORY, "..", "..", "example-docs")


@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("fake-email.eml", FileType.EML),
        ("unsupported/factbook.xml", FileType.XML),
        ("example-10k.html", FileType.HTML),
        ("fake-html.html", FileType.HTML),
        ("unsupported/fake-excel.xlsx", FileType.XLSX),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
    ],
)
def test_detect_filetype_from_filename(file, expected):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    assert detect_filetype(filename) == expected


@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("fake-email.eml", FileType.EML),
        ("unsupported/factbook.xml", FileType.XML),
        ("example-10k.html", FileType.HTML),
        ("fake-html.html", FileType.HTML),
        ("unsupported/fake-excel.xlsx", FileType.XLSX),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
        ("fake-doc.rtf", FileType.RTF),
    ],
)
def test_detect_filetype_from_filename_with_extension(monkeypatch, file, expected):
    """Test that we detect the filetype from the filename extension when libmagic is not available
    or the file does not exist."""
    # Test when libmagic is not available
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", False)
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    assert detect_filetype(filename) == expected
    # Test when the file does not exist
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", True)
    extension = pathlib.Path(file).suffix
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "not-on-disk" + extension)
    assert detect_filetype(filename) == expected


@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("fake-email.eml", FileType.EML),
        ("unsupported/factbook.xml", FileType.XML),
        # NOTE(robinson) - For the document, some operating systems return
        # */xml and some return */html. Either could be acceptable depending on the OS
        ("example-10k.html", [FileType.HTML, FileType.XML]),
        ("fake-html.html", FileType.HTML),
        ("unsupported/fake-excel.xlsx", FileType.XLSX),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
    ],
)
def test_detect_filetype_from_file(file, expected):
    expected = expected if isinstance(expected, list) else [expected]
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    with open(filename, "rb") as f:
        assert detect_filetype(file=f) in expected


def test_detect_filetype_from_file_raises_without_libmagic(monkeypatch):
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", False)
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f, pytest.raises(ImportError):
        detect_filetype(file=f)


def test_detect_xml_application_xml(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/xml")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.xml")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.XML


def test_detect_xml_application_rtf(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/rtf")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.rtf")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.RTF


def test_detect_xml_text_xml(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/xml")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.xml")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.XML


def test_detect_html_application_xml(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/xml")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.html")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.HTML


def test_detect_html_text_xml(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/xml")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.html")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.HTML


def test_detect_docx_filetype_application_octet_stream(monkeypatch):
    monkeypatch.setattr(magic, "from_buffer", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.docx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.DOCX


def test_detect_docx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.docx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.DOCX


def test_detect_docx_filetype_application_zip(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/zip")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.docx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.DOCX


def test_detect_application_zip_files(monkeypatch, tmpdir):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/zip")
    filename = os.path.join(tmpdir, "test.zip")
    zf = zipfile.ZipFile(filename, "w")
    zf.close()
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.ZIP


def test_detect_doc_file_from_mime_type(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/msword")
    filetype = detect_filetype(filename="fake.doc")
    assert filetype == FileType.DOC


def test_detect_ppt_file_from_mime_type(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/vnd.ms-powerpoint")
    filetype = detect_filetype(filename="fake.ppt")
    assert filetype == FileType.PPT


def test_detect_xls_file_from_mime_type(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/vnd.ms-excel")
    filetype = detect_filetype(filename="fake.xls")
    assert filetype == FileType.XLS


def test_detect_xlsx_filetype_application_octet_stream(monkeypatch):
    monkeypatch.setattr(magic, "from_buffer", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "unsupported", "fake-excel.xlsx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.XLSX


def test_detect_xlsx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "unsupported", "fake-excel.xlsx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.XLSX


def test_detect_pptx_filetype_application_octet_stream(monkeypatch):
    monkeypatch.setattr(magic, "from_buffer", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.PPTX


def test_detect_pptx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.PPTX


def test_detect_application_octet_stream_returns_none_with_unknown(monkeypatch):
    monkeypatch.setattr(magic, "from_buffer", lambda *args, **kwargs: "application/octet-stream")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.UNK


def test_detect_application_zip_returns_zip_with_unknown(monkeypatch):
    monkeypatch.setattr(magic, "from_buffer", lambda *args, **kwargs: "application/zip")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.ZIP


def test_detect_docx_filetype_word_mime_type(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: DOCX_MIME_TYPES[0])
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.docx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.DOCX


def test_detect_xlsx_filetype_word_mime_type(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: XLSX_MIME_TYPES[0])
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "unsupported", "fake-excel.xlsx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.XLSX


def test_detect_filetype_returns_none_with_unknown(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/fake")
    assert detect_filetype(filename="made_up.fake") == FileType.UNK


def test_detect_filetype_detects_png(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "image/png")
    assert detect_filetype(filename="made_up.png") == FileType.PNG


def test_detect_filetype_detects_unknown_text_types_as_txt(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/new-type")
    monkeypatch.setattr(os.path, "isfile", lambda *args, **kwargs: True)
    assert detect_filetype(filename="made_up.png") == FileType.TXT


def test_detect_filetype_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-email.eml")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        detect_filetype(filename=filename, file=f)


def test_detect_filetype_raises_with_none_specified():
    with pytest.raises(ValueError):
        detect_filetype()


def test_filetype_order():
    assert FileType.HTML < FileType.XML
