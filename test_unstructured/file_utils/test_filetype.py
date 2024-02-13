import os
import pathlib
import zipfile

import magic
import pytest
import yaml
from PIL import Image

from unstructured.file_utils import filetype
from unstructured.file_utils.filetype import (
    FileType,
    _detect_filetype_from_octet_stream,
    _is_code_mime_type,
    _is_text_file_a_csv,
    _is_text_file_a_json,
    detect_filetype,
)

FILE_DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(FILE_DIRECTORY, "..", "..", "example-docs")

is_in_docker = os.path.exists("/.dockerenv")

DOCX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

XLSX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]


@pytest.mark.parametrize(
    ("file", "expected"),
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
        # NOTE(robinson) - currently failing in the docker tests because the detected
        # MIME type is text/csv
        # ("stanley-cups.csv", FileType.CSV),
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
        ("eml/fake-email.eml", FileType.EML),
        ("factbook.xml", FileType.XML),
        # NOTE(robinson) - For the document, some operating systems return
        # */xml and some return */html. Either could be acceptable depending on the OS
        ("example-10k.html", [FileType.HTML, FileType.XML]),
        ("fake-html.html", FileType.HTML),
        ("stanley-cups.xlsx", FileType.XLSX),
        # NOTE(robinson) - currently failing in the docker tests because the detected
        # MIME type is text/csv
        # ("stanley-cups.csv", FileType.CSV),
        ("stanley-cups.tsv", FileType.TSV),
        ("fake-power-point.pptx", FileType.PPTX),
        ("winter-sports.epub", FileType.EPUB),
        ("fake-incomplete-json.txt", FileType.TXT),
    ],
)
def test_detect_filetype_from_file(file, expected):
    expected = expected if isinstance(expected, list) else [expected]
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    with open(filename, "rb") as f:
        assert detect_filetype(file=f) in expected


def test_detect_filetype_from_file_warning_without_libmagic(monkeypatch, caplog):
    monkeypatch.setattr(filetype, "LIBMAGIC_AVAILABLE", False)
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-text.txt")
    with open(filename, "rb") as f:
        detect_filetype(file=f)
        assert "WARNING" in caplog.text


def test_detect_xml_application_xml(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/xml")
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.xml")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.XML


def test_detect_text_csv(monkeypatch, filename="example-docs/stanley-cup.csv"):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/csv")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.CSV


def test_detect_text_python_from_filename(monkeypatch, filename="unstructured/logger.py"):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/x-script.python")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.TXT


def test_detect_text_python_from_file(monkeypatch, filename="unstructured/logger.py"):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/x-script.python")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.TXT


def test_detects_go_mime_type():
    assert _is_code_mime_type("text/x-go") is True


def test_detect_xml_application_go(monkeypatch, tmpdir):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/x-go")

    filename = os.path.join(tmpdir, "fake.go")
    with open(filename, "w") as f:
        f.write("")

    with open(filename, "rb") as f:
        assert detect_filetype(filename=filename) == FileType.TXT


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
    monkeypatch.setattr(
        magic,
        "from_buffer",
        lambda *args, **kwargs: "application/octet-stream",
    )
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake.docx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.DOCX


def test_detect_docx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/octet-stream",
    )
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
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/msword",
    )
    filetype = detect_filetype(filename="fake.doc")
    assert filetype == FileType.DOC


def test_detect_ppt_file_from_mime_type(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/vnd.ms-powerpoint",
    )
    filetype = detect_filetype(filename="fake.ppt")
    assert filetype == FileType.PPT


def test_detect_xls_file_from_mime_type(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/vnd.ms-excel",
    )
    filetype = detect_filetype(filename="fake.xls")
    assert filetype == FileType.XLS


def test_detect_xlsx_filetype_application_octet_stream(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_buffer",
        lambda *args, **kwargs: "application/octet-stream",
    )
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "stanley-cups.xlsx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.XLSX


def test_detect_xlsx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/octet-stream",
    )
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "stanley-cups.xlsx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.XLSX


def test_detect_pptx_filetype_application_octet_stream(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_buffer",
        lambda *args, **kwargs: "application/octet-stream",
    )
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.PPTX


def test_detect_pptx_filetype_application_octet_stream_with_filename(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_file",
        lambda *args, **kwargs: "application/octet-stream",
    )
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "fake-power-point.pptx")
    filetype = detect_filetype(filename=filename)
    assert filetype == FileType.PPTX


def test_detect_application_octet_stream_returns_none_with_unknown(monkeypatch):
    monkeypatch.setattr(
        magic,
        "from_buffer",
        lambda *args, **kwargs: "application/octet-stream",
    )
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
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "stanley-cups.xlsx")
    with open(filename, "rb") as f:
        filetype = detect_filetype(file=f)
    assert filetype == FileType.XLSX


def test_detect_filetype_returns_none_with_unknown(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "application/fake")
    assert detect_filetype(filename="made_up.fake") == FileType.UNK


def test_detect_filetype_detects_png(monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "image/png")
    assert detect_filetype(filename="made_up.png") == FileType.PNG


def test_detect_filetype_detects_unknown_text_types_as_txt(monkeypatch, tmpdir):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/new-type")
    monkeypatch.setattr(os.path, "isfile", lambda *args, **kwargs: True)

    filename = os.path.join(tmpdir.dirname, "made_up.png")
    with open(filename, "w") as f:
        f.write("here is a fake file!")

    assert detect_filetype(filename=filename) == FileType.TXT


def test_detect_filetype_detects_bmp_from_filename(
    tmpdir,
    filename="example-docs/layout-parser-paper-with-table.jpg",
):
    bmp_filename = os.path.join(tmpdir.dirname, "example.bmp")
    img = Image.open(filename)
    img.save(bmp_filename)

    detect_filetype(filename=bmp_filename) == FileType.BMP


@pytest.mark.skipif(is_in_docker, reason="Skipping this test in Docker container")
def test_detect_filetype_detects_bmp_from_file(
    tmpdir,
    filename="example-docs/layout-parser-paper-with-table.jpg",
):
    bmp_filename = os.path.join(tmpdir.dirname, "example.bmp")
    img = Image.open(filename)
    img.save(bmp_filename)

    with open(bmp_filename, "rb") as f:
        assert detect_filetype(file=f) == FileType.BMP


def test_detect_filetype_raises_with_both_specified():
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, "eml/fake-email.eml")
    with open(filename, "rb") as f, pytest.raises(ValueError):
        detect_filetype(filename=filename, file=f)


def test_detect_filetype_raises_with_none_specified():
    with pytest.raises(ValueError):
        detect_filetype()


def test_filetype_order():
    assert FileType.HTML < FileType.XML


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"d\xe2\x80", False),  # Invalid JSON
        (b'[{"key": "value"}]', True),  # Valid JSON
        (b"", False),  # Empty content
        (b'"This is not a JSON"', False),  # Serializable as JSON, but we want to treat it as txt
    ],
)
def test_is_text_file_a_json(content, expected):
    from io import BytesIO

    with BytesIO(content) as f:
        assert _is_text_file_a_json(file=f) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"d\xe2\x80", False),  # Invalid CSV
        (b'[{"key": "value"}]', False),  # Invalid CSV
        (b"column1,column2,column3\nvalue1,value2,value3\n", True),  # Valid CSV
        (b"", False),  # Empty content
    ],
)
def test_is_text_file_a_csv(content, expected):
    from io import BytesIO

    with BytesIO(content) as f:
        assert _is_text_file_a_csv(file=f) == expected


def test_csv_json_check_with_filename_and_utf_32(filename="example-docs/fake-text-utf-32.txt"):
    assert _is_text_file_a_csv(filename=filename) is False
    assert _is_text_file_a_json(filename=filename) is False


def test_csv_json_check_with_file_and_utf_32(filename="example-docs/fake-text-utf-32.txt"):
    with open(filename, "rb") as f:
        assert _is_text_file_a_csv(file=f) is False

    with open(filename, "rb") as f:
        assert _is_text_file_a_json(file=f) is False


def test_detect_filetype_detects_empty_filename(filename="example-docs/empty.txt"):
    assert detect_filetype(filename=filename) == FileType.EMPTY


def test_detect_filetype_detects_empty_file(filename="example-docs/empty.txt"):
    with open(filename, "rb") as f:
        assert detect_filetype(file=f) == FileType.EMPTY


def test_detect_filetype_skips_escape_commas_for_csv(tmpdir):
    text = 'A,A,A,A,A\nA,A,A,"A,A",A\nA,A,A,"A,A",A'
    filename = os.path.join(tmpdir.dirname, "csv-with-escaped-commas.csv")
    with open(filename, "w") as f:
        f.write(text)

    assert detect_filetype(filename=filename) == FileType.CSV

    with open(filename, "rb") as f:
        assert detect_filetype(file=f) == FileType.CSV


def test_detect_filetype_from_octet_stream(filename="example-docs/emoji.xlsx"):
    with open(filename, "rb") as f:
        assert _detect_filetype_from_octet_stream(file=f) == FileType.XLSX


def test_detect_wav_from_filename(filename="example-docs/CantinaBand3.wav"):
    assert detect_filetype(filename=filename) == FileType.WAV


def test_detect_wav_from_file(filename="example-docs/CantinaBand3.wav"):
    with open(filename, "rb") as f:
        assert detect_filetype(file=f) == FileType.WAV


def test_detect_yaml_as_text_from_filename(tmpdir):
    data = {"hi": "there", "this is": "yaml"}
    filename = os.path.join(tmpdir.dirname, "test.yaml")
    with open(filename, "w") as f:
        yaml.dump(data, f)

    assert detect_filetype(filename=filename) == FileType.TXT


def test_detect_yaml_as_text_from_file(tmpdir, monkeypatch):
    monkeypatch.setattr(magic, "from_file", lambda *args, **kwargs: "text/yaml")
    data = {"hi": "there", "this is": "yaml"}
    filename = os.path.join(tmpdir.dirname, "test.yaml")
    with open(filename, "w") as f:
        yaml.dump(data, f)

    with open(filename, "rb") as f:
        assert detect_filetype(file=f) == FileType.TXT
