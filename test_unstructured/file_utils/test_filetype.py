# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.file_utils.filetype`."""

from __future__ import annotations

import io
import os

import pytest

from test_unstructured.unit_utils import (
    FixtureRequest,
    LogCaptureFixture,
    Mock,
    example_doc_path,
    patch,
    property_mock,
)
from unstructured.file_utils.filetype import (
    _FileTypeDetectionContext,
    _OleFileDifferentiator,
    _TextFileDifferentiator,
    _ZipFileDifferentiator,
    detect_filetype,
    is_json_processable,
)
from unstructured.file_utils.model import FileType

is_in_docker = os.path.exists("/.dockerenv")

# ================================================================================================
# STRATEGY #1 - CONTENT-TYPE ASSERTED IN CALL
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name", "content_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.DOC, "simple.doc", "application/msword"),
        (
            FileType.DOCX,
            "simple.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.EPUB, "winter-sports.epub", "application/epub+zip"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.JSON, "spring-weather.html.json", "application/json"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.MSG, "fake-email.msg", "application/vnd.ms-outlook"),
        (FileType.ODT, "simple.odt", "application/vnd.oasis.opendocument.text"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.PPT, "fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            FileType.PPTX,
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.XLS, "tests-example.xls", "application/vnd.ms-excel"),
        (
            FileType.XLSX,
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.ZIP, "simple.zip", "application/zip"),
    ],
)
def test_it_detects_correct_file_type_from_file_path_with_correct_asserted_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable strategy #2, leaving only asserted content-type and extension --
    ctx_mime_type_.return_value = None

    file_type = detect_filetype(example_doc_path(file_name), content_type=content_type)

    # -- Strategy 1 should not need to refer to guessed MIME-type and detection should not
    # -- fall back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type == expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name", "content_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.DOC, "simple.doc", "application/msword"),
        (
            FileType.DOCX,
            "simple.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.EPUB, "winter-sports.epub", "application/epub+zip"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.JSON, "spring-weather.html.json", "application/json"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.MSG, "fake-email.msg", "application/vnd.ms-outlook"),
        (FileType.ODT, "simple.odt", "application/vnd.oasis.opendocument.text"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.PPT, "fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            FileType.PPTX,
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.XLS, "tests-example.xls", "application/vnd.ms-excel"),
        (
            FileType.XLSX,
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.ZIP, "simple.zip", "application/zip"),
    ],
)
def test_it_detects_correct_file_type_from_file_no_name_with_correct_asserted_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable strategy #2 (guessed mime-type) --
    ctx_mime_type_.return_value = None
    # -- disable strategy #3 (filename extension) by supplying no source of file name --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file, content_type=content_type)

    # -- Strategy 1 should not need to refer to guessed MIME-type and detection should not
    # -- fall-back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.DOCX, "simple.docx"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.XLSX, "stanley-cups.xlsx"),
    ],
)
@pytest.mark.parametrize(
    "content_type",
    [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
)
def test_it_detects_correct_file_type_from_file_no_name_with_swapped_ms_office_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable strategies 2 & 3, content-type strategy should get this on its own --
    ctx_mime_type_.return_value = None
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file, content_type=content_type)

    # -- Strategy 1 should not need to refer to guessed MIME-type and detection should not
    # -- fall-back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.DOC, "simple.doc"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.MSG, "fake-email-multiple-attachments.msg"),
    ],
)
@pytest.mark.parametrize(
    "content_type",
    [
        "application/msword",
        "application/vnd.ms-outlook",
        "application/vnd.ms-powerpoint",
        "application/vnd.ms-excel",
        "anything/else",
    ],
)
def test_it_detects_correct_file_type_from_OLE_file_no_name_with_wrong_asserted_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    """Fixes wrong XLS asserted as DOC, PPT, etc.

    Asserted content-type can be anything except `None` and differentiator will fix it if the file
    is DOC, PPT, XLS, or MSG type.
    """
    # -- disable strategies 2 & 3, content-type strategy should get this on its own --
    ctx_mime_type_.return_value = None
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file, content_type=content_type)

    # -- Strategy 1 should not need to refer to guessed MIME-type and detection should not
    # -- fall-back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type is expected_value


# ================================================================================================
# STRATEGY #2 - GUESS MIME-TYPE WITH LIBMAGIC
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name", "mime_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.CSV, "stanley-cups.csv", "application/csv"),
        (FileType.CSV, "stanley-cups.csv", "application/x-csv"),
        (FileType.DOC, "simple.doc", "application/msword"),
        (
            FileType.DOCX,
            "simple.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.EPUB, "winter-sports.epub", "application/epub"),
        (FileType.EPUB, "winter-sports.epub", "application/epub+zip"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.JSON, "spring-weather.html.json", "application/json"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.MD, "README.md", "text/x-markdown"),
        (FileType.MSG, "fake-email.msg", "application/vnd.ms-outlook"),
        (FileType.ODT, "simple.odt", "application/vnd.oasis.opendocument.text"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.PPT, "fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            FileType.PPTX,
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.RTF, "fake-doc.rtf", "application/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.TXT, "simple.yaml", "text/yaml"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.XLS, "tests-example.xls", "application/vnd.ms-excel"),
        (
            FileType.XLSX,
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.XML, "factbook.xml", "text/xml"),
        (FileType.ZIP, "simple.zip", "application/zip"),
    ],
)
def test_it_detects_correct_file_type_using_strategy_2_when_libmagic_guesses_recognized_mime_type(
    file_name: str, mime_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- libmagic guesses a MIME-type mapped to a `FileType` --
    ctx_mime_type_.return_value = mime_type
    # -- disable strategy #3 (filename extension) by not providing filename --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    # -- disable strategy #1 by not asserting a content_type in the call --
    file_type = detect_filetype(file=file)

    # -- ctx.mime_type may be referenced multiple times, but at least once --
    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.CSV, "stanley-cups.csv"),
        (FileType.DOC, "simple.doc"),
        (FileType.DOCX, "simple.docx"),
        (FileType.EML, "eml/fake-email.eml"),
        (FileType.EPUB, "winter-sports.epub"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.HTML, "ideas-page.html"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.JSON, "spring-weather.html.json"),
        (FileType.MSG, "fake-email.msg"),
        (FileType.ODT, "simple.odt"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.TXT, "norwich-city.txt"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.XLSX, "stanley-cups.xlsx"),
        (FileType.XML, "factbook.xml"),
        (FileType.ZIP, "simple.zip"),
    ],
)
def test_it_detects_most_file_types_using_strategy_2_when_libmagic_guesses_mime_type_for_itself(
    file_name: str, expected_value: FileType
):
    """Does not work for all types, in particular:

    TODOs:
    - TSV is identified as TXT, maybe need an `.is_tsv` predicate in `_TextFileDifferentiator`

    NOCANDOs: w/o an extension I think these are the best we can do.
    - MD is identified as TXT
    - ORG is identified as TXT
    - RST is identified as TXT
    """
    # -- disable strategy #1 by not asserting a content_type in the call --
    # -- disable strategy #3 (extension) by passing file-like object with no `.name` attribute --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    assert detect_filetype(file=file) is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.DOC, "simple.doc"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.MSG, "fake-email-multiple-attachments.msg"),
    ],
)
@pytest.mark.parametrize(
    "guessed_mime_type",
    [
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-outlook",
        "application/vnd.ms-powerpoint",
        "application/x-ole-storage",
        "anything/else",
    ],
)
def test_it_detects_correct_file_type_from_OLE_file_no_name_with_wrong_guessed_mime_type(
    file_name: str, guessed_mime_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    """Fixes XLS wrongly-guessed as DOC, PPT, "application/x-ole-storage" etc.

    It's better than that actually, the OLE differentiator will get the right file-type for any DOC,
    PPT, XLS, or MSG file, regardless of guessed MIME-type.
    """
    ctx_mime_type_.return_value = guessed_mime_type
    # -- disable strategy 3 by not providing a file-name source --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    # -- disable strategy 1 by not asserting a content-type --
    file_type = detect_filetype(file=file)

    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        # -- `filetype` lib recognizes all these binary file-types --
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.DOC, "simple.doc"),
        (FileType.DOCX, "simple.docx"),
        (FileType.EPUB, "winter-sports.epub"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.ODT, "simple.odt"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.XLSX, "stanley-cups.xlsx"),
        (FileType.ZIP, "simple.zip"),
        # -- but it doesn't recognize textual file-types at all --
        (FileType.UNK, "stanley-cups.csv"),
        (FileType.UNK, "eml/fake-email.eml"),
        (FileType.UNK, "example-10k-1p.html"),
        (FileType.UNK, "spring-weather.html.json"),
        (FileType.UNK, "README.md"),
        (FileType.UNK, "README.org"),
        (FileType.UNK, "README.rst"),
        (FileType.UNK, "stanley-cups.tsv"),
        (FileType.UNK, "norwich-city.txt"),
        (FileType.UNK, "factbook.xml"),
        # -- and it doesn't recognize MSG files --
        (FileType.UNK, "fake-email.msg"),
    ],
)
def test_strategy_2_can_detect_only_binary_file_types_when_libmagic_is_unavailable(
    file_name: str, expected_value: FileType, LIBMAGIC_AVAILABLE_False: bool
):
    """File-type is detected using `filetype` library when libmagic is not available.

    `filetype.guess_mime()` does a good job on binary file types (PDF, images, legacy MS-Office),
    but doesn't even try to guess textual file-types.
    """
    # -- disable strategy #3 (extension) by passing file-like object with no `.name` attribute --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())
    # -- simulate libmagic is not available --
    assert LIBMAGIC_AVAILABLE_False is False

    # -- disable strategy #1 by not asserting a content_type in the call --
    file_type = detect_filetype(file=file)

    assert file_type is expected_value


def test_detect_filetype_from_file_warns_when_libmagic_is_not_installed(
    caplog: LogCaptureFixture, LIBMAGIC_AVAILABLE_False: bool
):
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        detect_filetype(file=f)

    assert "WARNING" in caplog.text
    assert "libmagic is unavailable but assists in filetype detection. Please cons" in caplog.text


# ================================================================================================
# STRATEGY #3 - MAP FILENAME EXTENSION TO FILETYPE
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.CSV, "stanley-cups.csv"),
        (FileType.DOC, "simple.doc"),
        (FileType.DOCX, "simple.docx"),
        (FileType.EML, "eml/fake-email.eml"),
        (FileType.EPUB, "winter-sports.epub"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.HTML, "example-10k-1p.html"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.JSON, "spring-weather.html.json"),
        (FileType.MD, "README.md"),
        (FileType.MSG, "fake-email.msg"),
        (FileType.ODT, "simple.odt"),
        (FileType.ORG, "README.org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.RST, "README.rst"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.TSV, "stanley-cups.tsv"),
        (FileType.TXT, "norwich-city.txt"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.XLSX, "stanley-cups.xlsx"),
        (FileType.XML, "factbook.xml"),
        (FileType.ZIP, "simple.zip"),
    ],
)
def test_it_detects_correct_file_type_from_strategy_3_when_extension_maps_to_file_type(
    file_name: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable strategy #2 by making libmagic always guess `None` --
    ctx_mime_type_.return_value = None

    # -- disable strategy #1 by not asserting a content_type in the call --
    # -- enable strategy #3 by passing filename as source for extension --
    file_type = detect_filetype(example_doc_path(file_name))

    # -- ctx.mime_type may be referenced multiple times, but at least once --
    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name", "mime_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "application/zip"),
        (FileType.DOC, "simple.doc", None),
        (FileType.EPUB, "winter-sports.epub", "application/x-ole-storage"),
        (FileType.MSG, "fake-email.msg", "application/octet-stream"),
    ],
)
def test_it_falls_back_to_extension_strategy_when_prior_strategies_fail(
    file_name: str, mime_type: str | None, expected_value: FileType, ctx_mime_type_: Mock
):
    ctx_mime_type_.return_value = mime_type

    file_type = detect_filetype(example_doc_path(file_name))

    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


# ================================================================================================
# SPECIAL CASES
# ================================================================================================


@pytest.mark.parametrize("mime_type", ["application/xml", "text/xml"])
@pytest.mark.parametrize("extension", [".html", ".htm"])
def test_it_detects_HTML_from_guessed_mime_type_ending_with_xml_and_html_extension(
    mime_type: str, extension: str, ctx_mime_type_: Mock
):
    ctx_mime_type_.return_value = mime_type
    with open(example_doc_path("example-10k-1p.html"), "rb") as f:
        file = io.BytesIO(f.read())
        file.name = f"a/b/page{extension}"

    file_type = detect_filetype(file=file)

    ctx_mime_type_.assert_called_with()
    assert file_type is FileType.HTML


@pytest.mark.parametrize(
    "mime_type",
    [
        "application/octet-stream",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ],
)
@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.DOCX, "simple.docx"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.XLSX, "stanley-cups.xlsx"),
        (FileType.ZIP, "simple.zip"),
    ],
)
def test_it_differentiates_files_when_libmagic_guesses_octet_stream_zip_or_modern_ms_office(
    mime_type: str, file_name: str, expected_value: FileType, ctx_mime_type_: Mock
):
    ctx_mime_type_.return_value = mime_type
    # -- disable extension-based strategy #3 --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file)

    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("mime_type", "file_name"),
    [
        ("text/x-script.python", "logger.py"),
        ("text/x-go", "fake.go"),
        ("application/x-javascript", "fake-text.txt"),
    ],
)
def test_it_detects_TXT_for_source_code_files(mime_type: str, file_name: str, ctx_mime_type_: Mock):
    ctx_mime_type_.return_value = mime_type
    # -- disable extension-based strategy #3 --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file)

    ctx_mime_type_.assert_called_with()
    assert file_type is FileType.TXT


def test_detects_TXT_from_an_unknown_guessed_text_subtype(ctx_mime_type_: Mock):
    ctx_mime_type_.return_value = "text/new-type"
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)

    ctx_mime_type_.assert_called_with()
    assert filetype == FileType.TXT


def test_detect_filetype_raises_with_neither_path_or_file_like_object_specified():
    with pytest.raises(ValueError, match="either `file_path` or `file` argument must be provided"):
        detect_filetype()


def test_it_detects_EMPTY_from_file_path_to_empty_file():
    assert detect_filetype(example_doc_path("empty.txt")) == FileType.EMPTY


def test_it_detects_EMPTY_from_empty_file_like_object():
    with open(example_doc_path("empty.txt"), "rb") as f:
        assert detect_filetype(file=f) == FileType.EMPTY


def test_it_detect_CSV_from_path_and_file_when_content_contains_escaped_commas():
    file_path = example_doc_path("csv-with-escaped-commas.csv")

    assert detect_filetype(file_path) == FileType.CSV
    with open(file_path, "rb") as f:
        assert detect_filetype(file=f) == FileType.CSV


# ================================================================================================
# Describe `is_json_processable()`
# ================================================================================================


def it_affirms_JSON_is_array_of_objects_from_a_file_path():
    assert is_json_processable(example_doc_path("simple.json")) is True


def and_it_affirms_JSON_is_NOT_an_array_of_objects_from_a_file_path():
    assert is_json_processable(example_doc_path("not-unstructured-payload.json")) is False


def it_affirms_JSON_is_array_of_objects_from_a_file_like_object_open_for_reading_bytes():
    with open(example_doc_path("simple.json"), "rb") as f:
        assert is_json_processable(file=f) is True


def and_it_affirms_JSON_is_NOT_an_array_of_objects_from_a_file_like_object_open_for_reading_bytes():
    with open(example_doc_path("not-unstructured-payload.json"), "rb") as f:
        assert is_json_processable(file=f) is False


def it_affirms_JSON_is_array_of_objects_from_text():
    with open(example_doc_path("simple.json")) as f:
        text = f.read()
    assert is_json_processable(file_text=text) is True


def and_it_affirms_JSON_is_NOT_an_array_of_objects_from_text():
    with open(example_doc_path("not-unstructured-payload.json")) as f:
        text = f.read()
    assert is_json_processable(file_text=text) is False


# ================================================================================================
# MODULE-LEVEL FIXTURES
# ================================================================================================


@pytest.fixture()
def LIBMAGIC_AVAILABLE_False():
    with patch("unstructured.file_utils.filetype.LIBMAGIC_AVAILABLE", False) as m:
        yield m


@pytest.fixture()
def ctx_mime_type_(request: FixtureRequest):
    return property_mock(request, _FileTypeDetectionContext, "mime_type")


# ================================================================================================
# UNIT-TESTS
# ================================================================================================


class Describe_FileTypeDetectionContext:
    """Unit-test suite for `unstructured.file_utils.filetype._FileTypeDetectionContext`."""

    # -- .new() -------------------------------------------------

    def it_provides_a_validating_alternate_constructor(self):
        ctx = _FileTypeDetectionContext.new(
            file_path=example_doc_path("simple.docx"),
            file=None,
            encoding="utf-8",
            content_type="text/plain",
            metadata_file_path="a/b/foo.bar",
        )
        assert isinstance(ctx, _FileTypeDetectionContext)

    def and_the_validating_constructor_raises_on_an_invalid_context(self):
        with pytest.raises(ValueError, match="either `file_path` or `file` argument must be pro"):
            _FileTypeDetectionContext.new(
                file_path=None,
                file=None,
                encoding=None,
                content_type=None,
                metadata_file_path=None,
            )

    # -- .content_type ------------------------------------------

    def it_knows_the_content_type_asserted_by_the_caller(self):
        assert _FileTypeDetectionContext(content_type="TEXT/hTmL").content_type == "text/html"

    # -- .encoding ----------------------------------------------

    @pytest.mark.parametrize(
        ("encoding", "expected_value"),
        [
            ("utf-8", "utf-8"),
            ("UTF_8", "utf-8"),
            ("UTF_16LE", "utf-16le"),
            ("ISO_8859_6_I", "iso-8859-6"),
            # -- default value is utf-8 --
            (None, "utf-8"),
        ],
    )
    def it_knows_the_encoding_asserted_by_the_caller_and_normalizes_it(
        self, encoding: str | None, expected_value: str
    ):
        assert _FileTypeDetectionContext(encoding=encoding).encoding == expected_value

    # -- .extension ---------------------------------------------

    def it_derives_the_filename_extension_from_the_file_path_when_one_is_provided(self):
        ctx = _FileTypeDetectionContext(file_path=example_doc_path("simple.docx"))
        assert ctx.extension == ".docx"

    def and_it_derives_the_extension_from_a_file_opened_from_a_path(self):
        with open(example_doc_path("picture.pptx"), "rb") as f:
            assert _FileTypeDetectionContext(file=f).extension == ".pptx"

    @pytest.mark.parametrize(
        "file_name",
        [
            # -- case 1: file-like object has no `.name` attribute
            None,
            # -- case 2: file-like object has `.name` attribute but it's value is the empty string
            "",
        ],
    )
    def and_it_derives_the_extension_from_metadata_file_path_when_file_object_has_no_name(
        self, file_name: str | None
    ):
        with open(example_doc_path("ideas-page.html"), "rb") as f:
            file = io.BytesIO(f.read())
            if file_name is not None:
                file.name = file_name

        ctx = _FileTypeDetectionContext(file=file, metadata_file_path="a/b/c.html")

        assert ctx.extension == ".html"

    @pytest.mark.parametrize(
        "file_name",
        [
            # -- case 1: file-like object has no `.name` attribute
            None,
            # -- case 2: file-like object has `.name` attribute but it's value is the empty string
            "",
        ],
    )
    def and_it_returns_the_empty_string_as_the_extension_when_there_are_no_file_name_sources(
        self, file_name: str | None
    ):
        with open(example_doc_path("ideas-page.html"), "rb") as f:
            file = io.BytesIO(f.read())
            if file_name is not None:
                file.name = file_name

        assert _FileTypeDetectionContext(file=file).extension == ""

    # -- .file_head ---------------------------------------------

    def it_grabs_the_first_8k_bytes_of_the_file_for_use_by_magic(self):
        ctx = _FileTypeDetectionContext(file_path=example_doc_path("norwich-city.txt"))

        head = ctx.file_head

        assert isinstance(head, bytes)
        assert len(head) == 8192
        assert head.startswith(b"Iwan Roberts\nRoberts celebrating after")

    # -- .file_path ---------------------------------------------

    @pytest.mark.parametrize("file_path", [None, "a/b/c.pdf"])
    def it_knows_the_file_path_provided_by_the_caller(self, file_path: str | None):
        assert _FileTypeDetectionContext(file_path=file_path).file_path == file_path

    # -- .has_code_mime_type ------------------------------------

    @pytest.mark.parametrize(
        ("mime_type", "expected_value"),
        [
            ("text/plain", False),
            ("text/x-csharp", True),
            ("text/x-go", True),
            ("text/x-java", True),
            ("text/x-python", True),
            ("application/xml", False),
            (None, False),
        ],
    )
    def it_knows_whether_its_mime_type_indicates_programming_language_source_code(
        self, mime_type_prop_: Mock, mime_type: str | None, expected_value: bool
    ):
        mime_type_prop_.return_value = mime_type
        assert _FileTypeDetectionContext().has_code_mime_type is expected_value

    # -- .is_zipfile --------------------------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"),
        [
            ("README.md", False),
            ("emoji.xlsx", True),
            ("simple.doc", False),
            ("simple.docx", True),
            ("simple.odt", True),
            ("simple.zip", True),
            ("winter-sports.epub", True),
        ],
    )
    def it_knows_whether_it_is_a_zipfile(self, file_name: str, expected_value: bool):
        assert _FileTypeDetectionContext(example_doc_path(file_name)).is_zipfile is expected_value

    # -- .mime_type ---------------------------------------------

    def it_provides_the_MIME_type_detected_by_libmagic_from_a_file_path(self):
        ctx = _FileTypeDetectionContext(file_path=example_doc_path("norwich-city.txt"))
        assert ctx.mime_type == "text/plain"

    def and_it_provides_the_MIME_type_from_path_using_filetype_lib_when_magic_is_unavailable(self):
        with patch("unstructured.file_utils.filetype.LIBMAGIC_AVAILABLE", False):
            ctx = _FileTypeDetectionContext(file_path=example_doc_path("simple.doc"))
            assert ctx.mime_type == "application/msword"

    def but_it_warns_to_install_libmagic_when_the_filetype_lib_cannot_detect_the_MIME_type(
        self, caplog: LogCaptureFixture
    ):
        with patch("unstructured.file_utils.filetype.LIBMAGIC_AVAILABLE", False):
            ctx = _FileTypeDetectionContext(file_path=example_doc_path("norwich-city.txt"))
            assert ctx.mime_type is None
            assert "WARNING" in caplog.text
            assert "libmagic is unavailable" in caplog.text
            assert "consider installing libmagic" in caplog.text

    def it_provides_the_MIME_type_detected_by_libmagic_from_a_file_like_object(self):
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            ctx = _FileTypeDetectionContext(file=f)
            assert ctx.mime_type == "text/plain"

    def and_it_provides_the_MIME_type_from_file_using_filetype_lib_when_magic_is_unavailable(self):
        with patch("unstructured.file_utils.filetype.LIBMAGIC_AVAILABLE", False):
            file_path = example_doc_path("simple.doc")
            with open(file_path, "rb") as f:
                ctx = _FileTypeDetectionContext(file=f)
                assert ctx.mime_type == "application/msword"

    # -- .open() ------------------------------------------------

    def it_provides_transparent_access_to_the_source_file_when_it_is_a_file_like_object(self):
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            ctx = _FileTypeDetectionContext(file=f)
            with ctx.open() as file:
                assert file is f
                assert file.read(38) == b"Iwan Roberts\nRoberts celebrating after"

    def it_provides_transparent_access_to_the_source_file_when_it_is_a_file_path(self):
        ctx = _FileTypeDetectionContext(file_path=example_doc_path("norwich-city.txt"))
        with ctx.open() as file:
            assert file.read(38) == b"Iwan Roberts\nRoberts celebrating after"

    # -- .text_head ---------------------------------------------

    def it_grabs_the_first_4k_chars_from_file_path_for_textual_type_differentiation(self):
        ctx = _FileTypeDetectionContext(file_path=example_doc_path("norwich-city.txt"))

        text_head = ctx.text_head

        assert isinstance(text_head, str)
        assert len(text_head) == 4096
        assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def and_it_uses_character_detection_to_correct_a_wrong_encoding_arg_for_file_path(self):
        ctx = _FileTypeDetectionContext(
            file_path=example_doc_path("norwich-city.txt"), encoding="utf_32_be"
        )

        text_head = ctx.text_head

        assert isinstance(text_head, str)
        assert len(text_head) == 4096
        assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def but_not_to_correct_a_wrong_encoding_arg_for_a_file_like_object_open_in_binary_mode(self):
        """Fails silently in this case, returning empty string."""
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            file = io.BytesIO(f.read())
        ctx = _FileTypeDetectionContext(file=file, encoding="utf_32_be")

        text_head = ctx.text_head

        assert text_head == ""

    def and_it_grabs_the_first_4k_chars_from_binary_file_for_textual_type_differentiation(self):
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            ctx = _FileTypeDetectionContext(file=f)

            text_head = ctx.text_head

            assert isinstance(text_head, str)
            # -- some characters consume multiple bytes, so shorter than 4096 --
            assert len(text_head) == 4063
            assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def and_it_grabs_the_first_4k_chars_from_text_file_for_textual_type_differentiation(self):
        """Not a documented behavior to accept IO[str], but support is implemented."""
        with open(example_doc_path("norwich-city.txt")) as f:
            ctx = _FileTypeDetectionContext(file=f)  # pyright: ignore[reportArgumentType]

            text_head = ctx.text_head

            assert isinstance(text_head, str)
            assert len(text_head) == 4096
            assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def it_accommodates_a_utf_32_encoded_file_path(self):
        ctx = _FileTypeDetectionContext(example_doc_path("fake-text-utf-32.txt"))

        text_head = ctx.text_head

        assert isinstance(text_head, str)
        # -- test document is short --
        assert len(text_head) == 188
        assert text_head.startswith("This is a test document to use for unit tests.\n\n    Doyle")

    # TODO: this fails because `.text_head` ignores decoding errors on a file open for binary
    # reading. Probably better if it used chardet in that case as it does for a file-path.
    @pytest.mark.xfail(reason="WIP", raises=AssertionError, strict=True)
    def and_it_accommodates_a_utf_32_encoded_file_like_object(self):
        with open(example_doc_path("fake-text-utf-32.txt"), "rb") as f:
            file = io.BytesIO(f.read())
        ctx = _FileTypeDetectionContext(file=file)

        text_head = ctx.text_head

        assert isinstance(text_head, str)
        # -- test document is short --
        assert len(text_head) == 188
        assert text_head.startswith("This is a test document to use for unit tests.\n\n    Doyle")

    # -- .validate() --------------------------------------------

    def it_raises_when_no_file_exists_at_the_specified_file_path(self):
        with pytest.raises(FileNotFoundError, match="no such file a/b/c.foo"):
            _FileTypeDetectionContext(file_path="a/b/c.foo")._validate()

    def it_raises_when_neither_file_path_nor_file_is_provided(self):
        with pytest.raises(ValueError, match="either `file_path` or `file` argument must be pro"):
            _FileTypeDetectionContext()._validate()

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture
    def mime_type_prop_(self, request: FixtureRequest):
        return property_mock(request, _FileTypeDetectionContext, "mime_type")


class Describe_OleFileDifferentiator:
    """Unit-test suite for `unstructured.file_utils.filetype._OleFileDifferentiator`."""

    # -- .applies() ---------------------------------------------

    def it_provides_a_qualifying_alternate_constructor_which_constructs_when_applicable(self):
        """The constructor determines whether this differentiator is applicable.

        It returns an instance only when differentiating a CFBF file-type is required, which it
        judges by inspecting the initial bytes of the file for the CFBF magic-bytes.
        """
        ctx = _FileTypeDetectionContext(example_doc_path("simple.doc"))

        differentiator = _OleFileDifferentiator.applies(ctx, "foo/bar")

        assert differentiator is not None
        assert isinstance(differentiator, _OleFileDifferentiator)

    def and_it_returns_None_when_ole_differentiation_is_not_applicable_to_the_mime_type(self):
        ctx = _FileTypeDetectionContext(example_doc_path("winter-sports.epub"))
        assert _OleFileDifferentiator.applies(ctx, "application/epub") is None

    # -- .file_type ---------------------------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"),
        [
            ("simple.doc", FileType.DOC),
            ("fake-power-point.ppt", FileType.PPT),
            ("tests-example.xls", FileType.XLS),
            ("fake-email.msg", FileType.MSG),
            ("README.org", None),
        ],
    )
    def it_distinguishes_the_file_type_of_applicable_zip_files(
        self, file_name: str, expected_value: FileType | None
    ):
        # -- no file-name available, just to make sure we're not relying on an extension --
        with open(example_doc_path(file_name), "rb") as f:
            file = io.BytesIO(f.read())
        ctx = _FileTypeDetectionContext(file=file)
        differentiator = _OleFileDifferentiator(ctx)

        assert differentiator.file_type is expected_value


class Describe_TextFileDifferentiator:
    """Unit-test suite for `unstructured.file_utils.filetype._TextFileDifferentiator`."""

    # -- .applies() ---------------------------------------------

    def it_provides_a_qualifying_alternate_constructor_which_constructs_when_applicable(self):
        """The constructor determines whether this differentiator is applicable.

        It returns an instance only when differentiating a text file-type is required, which it can
        judge from the context (`ctx`).
        """
        ctx = _FileTypeDetectionContext(example_doc_path("norwich-city.txt"))

        differentiator = _TextFileDifferentiator.applies(ctx)

        assert isinstance(differentiator, _TextFileDifferentiator)

    def and_it_returns_None_when_text_differentiation_does_not_apply_to_the_detection_context(self):
        ctx = _FileTypeDetectionContext(example_doc_path("simple.docx"))
        assert _TextFileDifferentiator.applies(ctx) is None

    # -- ._is_csv -----------------------------------------------

    @pytest.mark.parametrize(
        ("content", "expected_value"),
        [
            # -- no commas, too few lines --
            (b"d\xe2\x80", False),
            (b'[{"key": "value"}]', False),
            # -- at least a header and one data row, at least two columns --
            (b"column1,column2,column3\nvalue1,value2,value3\n", True),
            # -- no content --
            (b"", False),
        ],
    )
    def it_distinguishes_a_CSV_file_from_other_text_files(
        self, content: bytes, expected_value: bool
    ):
        ctx = _FileTypeDetectionContext(file=io.BytesIO(content))
        differentiator = _TextFileDifferentiator(ctx)

        assert differentiator._is_csv is expected_value

    # -- ._is_eml -----------------------------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"), [("fake-email.eml", True), ("norwich-city.txt", False)]
    )
    def it_distinguishes_an_EML_file_from_other_text_files(
        self, file_name: str, expected_value: bool
    ):
        ctx = _FileTypeDetectionContext(example_doc_path(file_name))
        assert _TextFileDifferentiator(ctx)._is_eml is expected_value

    # -- ._is_json ----------------------------------------------

    @pytest.mark.parametrize(
        ("content", "expected_value"),
        [
            (b"d\xe2\x80", False),
            (b'[{"key": "value"}]', True),
            (b"", False),
            # -- valid JSON, but not for our purposes --
            (b'"This is not a JSON"', False),
        ],
    )
    def it_distinguishes_a_JSON_file_from_other_text_files(
        self, content: bytes, expected_value: bool
    ):
        ctx = _FileTypeDetectionContext(file=io.BytesIO(content))
        differentiator = _TextFileDifferentiator(ctx)

        assert differentiator._is_json is expected_value


class Describe_ZipFileDifferentiator:
    """Unit-test suite for `unstructured.file_utils.filetype._ZipFileDifferentiator`."""

    # -- .applies() ---------------------------------------------

    def it_provides_a_qualifying_alternate_constructor_which_constructs_when_applicable(self):
        """The constructor determines whether this differentiator is applicable.

        It returns an instance only when differentiating a zip file-type is required, which it can
        judge from the mime-type provided by the context (`ctx`).
        """
        ctx = _FileTypeDetectionContext(example_doc_path("simple.docx"))

        differentiator = _ZipFileDifferentiator.applies(ctx, "application/zip")

        assert isinstance(differentiator, _ZipFileDifferentiator)

    def and_it_returns_None_when_zip_differentiation_does_not_apply_to_the_detection_context(self):
        ctx = _FileTypeDetectionContext(example_doc_path("norwich-city.txt"))
        assert _ZipFileDifferentiator.applies(ctx, "application/epub") is None

    # -- .file_type ---------------------------------------------

    @pytest.mark.parametrize(
        ("file_name", "expected_value"),
        [
            ("simple.docx", FileType.DOCX),
            ("picture.pptx", FileType.PPTX),
            ("vodafone.xlsx", FileType.XLSX),
            ("simple.zip", FileType.ZIP),
            ("README.org", None),
        ],
    )
    def it_distinguishes_the_file_type_of_applicable_zip_files(
        self, file_name: str, expected_value: FileType | None
    ):
        ctx = _FileTypeDetectionContext(example_doc_path(file_name))
        differentiator = _ZipFileDifferentiator(ctx)

        assert differentiator.file_type is expected_value
