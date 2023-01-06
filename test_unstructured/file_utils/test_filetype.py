import os
import pathlib
import pytest


from unstructured.file_utils.filetype import detect_filetype, FileType

FILE_DIRECTORY = pathlib.Path(__file__).parent.resolve()
EXAMPLE_DOCS_DIRECTORY = os.path.join(FILE_DIRECTORY, "..", "..", "example-docs")


@pytest.mark.parametrize(
    "file, expected",
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("fake-email.eml", FileType.EML),
        ("factbook.xml", FileType.XML),
        ("example-10k.html", FileType.HTML),
        ("fake-html.html", FileType.HTML),
        ("fake-excel.xlsx", FileType.XLSX),
    ],
)
def test_detect_filetype_from_filename(file, expected):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    assert detect_filetype(filename) == expected


@pytest.mark.parametrize(
    "file, expected",
    [
        ("layout-parser-paper-fast.pdf", FileType.PDF),
        ("fake.docx", FileType.DOCX),
        ("example.jpg", FileType.JPG),
        ("fake-text.txt", FileType.TXT),
        ("fake-email.eml", FileType.TXT),
        ("factbook.xml", FileType.XML),
        ("example-10k.html", FileType.XML),
        ("fake-html.html", FileType.HTML),
        ("fake-excel.xlsx", FileType.XLSX),
    ],
)
def test_detect_filetype_from_file(file, expected):
    filename = os.path.join(EXAMPLE_DOCS_DIRECTORY, file)
    with open(filename, "rb") as f:
        assert detect_filetype(file=f) == expected
