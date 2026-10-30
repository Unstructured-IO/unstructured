# pyright: reportPrivateUsage=false

"""Test suite for `unstructured.file_utils.filetype`."""

from __future__ import annotations

import codecs
import io
import json
import os
import shutil
import tempfile
import warnings
from pathlib import Path

import pytest

from test_unstructured.unit_utils import (
    FixtureRequest,
    LogCaptureFixture,
    Mock,
    example_doc_path,
    input_path,
    patch,
    property_mock,
)
from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils.encoding import EncodingDetectionWarning
from unstructured.file_utils.filetype import (
    _JSON_DISAMBIGUATION_MAX_CHARS,
    _decode_head_bytes,
    _decode_prefix,
    _FileTypeDetectionContext,
    _OleFileDetector,
    _TextFileDifferentiator,
    _ZipFileDetector,
    detect_filetype,
    is_json_processable,
    is_ndjson_processable,
)
from unstructured.file_utils.model import FileType, create_file_type

is_in_docker = os.path.exists("/.dockerenv")


# ================================================================================================
# STRATEGY #1 - DIRECT DETECTION OF CFB/ZIP-BASED BINARY FILE TYPES (8 TYPES)
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.DOC, "simple.doc"),
        (FileType.DOCX, "simple.docx"),
        (FileType.EPUB, "winter-sports.epub"),
        (FileType.ODT, "simple.odt"),
        (FileType.PPT, "fake-power-point.ppt"),
        (FileType.PPTX, "fake-power-point.pptx"),
        (FileType.XLS, "tests-example.xls"),
        (FileType.XLSX, "stanley-cups.xlsx"),
    ],
)
def test_it_detects_correct_file_type_for_CFB_and_ZIP_subtypes_detected_by_direct_inspection(
    file_name: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable other strategies; no content-type, guessed MIME-type or extension --
    ctx_mime_type_.return_value = None
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file)

    # -- Strategy 1 should not need to refer to guessed MIME-type and detection should not
    # -- fall back to MIME-type guessing for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type == expected_value


# ================================================================================================
# STRATEGY #2 - CONTENT-TYPE ASSERTED IN CALL
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name", "content_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.WEBP, "img/DA-1p.webp", "image/webp"),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.ZIP, "simple.zip", "application/zip"),
        (FileType.NDJSON, "spring-weather.html.ndjson", "application/x-ndjson"),
    ],
)
def test_it_detects_correct_file_type_from_file_path_with_correct_asserted_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable mime-guessing leaving only asserted content-type and extension --
    ctx_mime_type_.return_value = None

    file_type = detect_filetype(example_doc_path(file_name), content_type=content_type)

    # -- Content-type strategy should not need to refer to guessed MIME-type and detection should
    # not -- fall back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type == expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name", "content_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.WEBP, "img/DA-1p.webp", "image/webp"),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.ZIP, "simple.zip", "application/zip"),
    ],
)
def test_it_detects_correct_file_type_from_file_no_name_with_correct_asserted_content_type(
    file_name: str, content_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- disable mime-guessing --
    ctx_mime_type_.return_value = None
    # -- disable filename extension mapping by supplying no source of file name --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file, content_type=content_type)

    # -- Content-type strategy should not need to refer to guessed MIME-type and detection should
    # -- not fall-back to strategy 2 for any of these test cases.
    ctx_mime_type_.assert_not_called()
    assert file_type is expected_value


def test_it_identifies_NDJSON_for_file_like_object_with_no_name_but_NDJSON_content_type():
    with open(example_doc_path("simple.ndjson"), "rb") as f:
        file = io.BytesIO(f.read())
    assert detect_filetype(file=file, content_type=FileType.NDJSON.mime_type) == FileType.NDJSON


def test_it_identifies_NDJSON_for_file_with_ndjson_extension_but_JSON_content_type():
    file_path = example_doc_path("simple.ndjson")
    assert detect_filetype(file_path, content_type=FileType.JSON.mime_type) == FileType.NDJSON


@pytest.mark.parametrize(
    ("expected_value", "file_name", "mime_type", "metadata_file_path"),
    [
        # -- detected by MIME-type guessing --
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf", None),
        (FileType.HTML, "example-10k-1p.html", "text/html", None),
        # -- detected by filename extension --
        (FileType.MD, "README.md", None, "README.md"),
    ],
)
def test_it_ignores_asserted_octet_stream_content_type(
    file_name: str,
    mime_type: str | None,
    metadata_file_path: str | None,
    expected_value: FileType,
    ctx_mime_type_: Mock,
):
    # -- the generic "application/octet-stream" maps to `FileType.UNK` and must not end detection
    # -- before MIME-type guessing and the filename extension get a chance --
    ctx_mime_type_.return_value = mime_type
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(
        file=file, content_type="application/octet-stream", metadata_file_path=metadata_file_path
    )

    assert file_type is expected_value


# ================================================================================================
# STRATEGY #3 - GUESS MIME-TYPE WITH LIBMAGIC/FILETYPE LIBRARY
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name", "mime_type"),
    [
        (FileType.BMP, "img/bmp_24.bmp", "image/bmp"),
        (FileType.BMP, "img/bmp_24.bmp", "image/x-bmp"),
        (FileType.BMP, "img/bmp_24.bmp", "image/x-ms-bmp"),
        (FileType.CSV, "stanley-cups.csv", "text/csv"),
        (FileType.CSV, "stanley-cups.csv", "application/csv"),
        (FileType.CSV, "stanley-cups.csv", "application/x-csv"),
        (FileType.EML, "eml/fake-email.eml", "message/rfc822"),
        (FileType.HEIC, "img/DA-1p.heic", "image/heic"),
        (FileType.HEIC, "img/DA-1p.heic", "image/x-heic"),
        (FileType.HTML, "example-10k-1p.html", "text/html"),
        (FileType.JPG, "img/example.jpg", "image/jpeg"),
        (FileType.JSON, "spring-weather.html.json", "application/json"),
        (FileType.MD, "README.md", "text/markdown"),
        (FileType.MD, "README.md", "text/x-markdown"),
        (FileType.ORG, "README.org", "text/org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf", "application/pdf"),
        (FileType.PNG, "img/DA-1p.png", "image/png"),
        (FileType.RST, "README.rst", "text/x-rst"),
        (FileType.RTF, "fake-doc.rtf", "text/rtf"),
        (FileType.RTF, "fake-doc.rtf", "application/rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff", "image/tiff"),
        (FileType.TSV, "stanley-cups.tsv", "text/tsv"),
        (FileType.TXT, "norwich-city.txt", "text/plain"),
        (FileType.TXT, "simple.yaml", "text/yaml"),
        (FileType.WAV, "CantinaBand3.wav", "audio/wav"),
        (FileType.WEBP, "img/DA-1p.webp", "image/webp"),
        (FileType.XML, "factbook.xml", "application/xml"),
        (FileType.XML, "factbook.xml", "text/xml"),
    ],
)
def test_it_detects_correct_file_type_by_guessed_MIME_when_libmagic_guesses_recognized_mime_type(
    file_name: str, mime_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- libmagic guesses a MIME-type mapped to a `FileType` --
    ctx_mime_type_.return_value = mime_type
    # -- disable strategy #3 (filename extension) by not providing filename --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    # -- disable content-type strategy by not asserting a content_type in the call --
    file_type = detect_filetype(file=file)

    # -- ctx.mime_type may be referenced multiple times, but at least once --
    ctx_mime_type_.assert_called_with()
    assert file_type is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.CSV, "stanley-cups.csv"),
        (FileType.EML, "eml/fake-email.eml"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.HTML, "ideas-page.html"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.JSON, "spring-weather.html.json"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.TXT, "norwich-city.txt"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.WEBP, "img/DA-1p.webp"),
        (FileType.XML, "factbook.xml"),
        (FileType.ZIP, "simple.zip"),
    ],
)
def test_it_detects_most_file_types_using_mime_guessing_when_libmagic_guesses_mime_type_for_itself(
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
    # -- disable content-type strategy by not asserting a content_type in the call --
    # -- disable extension-mapping strategy by passing file-like object with no `.name` attribute --
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    assert detect_filetype(file=file) is expected_value


def test_it_detects_WEBP_from_its_content_when_its_extension_is_png(tmp_path):
    # -- the `.png` extension decides only when MIME-type guessing fails --
    file_path = str(tmp_path / "renamed.png")
    shutil.copyfile(example_doc_path("img/DA-1p.webp"), file_path)

    assert detect_filetype(file_path=file_path) is FileType.WEBP


@pytest.mark.parametrize(
    ("file_name", "fallback_mime_type", "expected_value"),
    [
        ("img/bmp_24.bmp", "image/bmp", FileType.BMP),
        ("img/DA-1p.heic", "image/heic", FileType.HEIC),
        ("CantinaBand3.wav", "audio/wav", FileType.WAV),
        ("img/DA-1p.webp", "image/webp", FileType.WEBP),
    ],
)
def test_it_falls_back_to_filetype_mime_guessing_when_libmagic_returns_unrecognized_mime_type(
    file_name: str, fallback_mime_type: str, expected_value: FileType, ctx_mime_type_: Mock
):
    # -- simulate libmagic returning an unhelpful MIME-type --
    ctx_mime_type_.return_value = "application/octet-stream"
    with patch("unstructured.file_utils.filetype.LIBMAGIC_AVAILABLE", True):
        with patch(
            "unstructured.file_utils.filetype.ft.guess_mime", return_value=fallback_mime_type
        ):
            with open(example_doc_path(file_name), "rb") as f:
                file = io.BytesIO(f.read())

            assert detect_filetype(file=file) is expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        # -- `filetype` lib recognizes all these binary file-types --
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.WEBP, "img/DA-1p.webp"),
        (FileType.ZIP, "simple.zip"),
        # -- but it doesn't recognize textual file-types at all --
        (FileType.UNK, "stanley-cups.csv"),
        (FileType.UNK, "eml/fake-email.eml"),
        (FileType.UNK, "example-10k-1p.html"),
        (FileType.UNK, "README.md"),
        (FileType.UNK, "README.org"),
        (FileType.UNK, "README.rst"),
        (FileType.UNK, "stanley-cups.tsv"),
        (FileType.UNK, "norwich-city.txt"),
        (FileType.UNK, "factbook.xml"),
    ],
)
def test_strategy_mime_guessing_can_detect_only_binary_file_types_when_libmagic_is_unavailable(
    file_name: str, expected_value: FileType, LIBMAGIC_AVAILABLE_False: bool
):
    """File-type is detected using `filetype` library when libmagic is not available.

    `filetype.guess_mime()` does a good job on binary file types (PDF, images, legacy MS-Office),
    but doesn't even try to guess textual file-types.
    """
    # -- disable detection by extension by passing file-like object with no `.name` attribute --
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
# STRATEGY #4 - MAP FILENAME EXTENSION TO FILETYPE
# ================================================================================================


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [
        (FileType.BMP, "img/bmp_24.bmp"),
        (FileType.CSV, "stanley-cups.csv"),
        (FileType.EML, "eml/fake-email.eml"),
        (FileType.HEIC, "img/DA-1p.heic"),
        (FileType.HTML, "example-10k-1p.html"),
        (FileType.JPG, "img/example.jpg"),
        (FileType.JSON, "spring-weather.html.json"),
        (FileType.MD, "README.md"),
        (FileType.ORG, "README.org"),
        (FileType.PDF, "pdf/layout-parser-paper-fast.pdf"),
        (FileType.PNG, "img/DA-1p.png"),
        (FileType.RST, "README.rst"),
        (FileType.RTF, "fake-doc.rtf"),
        (FileType.TIFF, "img/layout-parser-paper-fast.tiff"),
        (FileType.TSV, "stanley-cups.tsv"),
        (FileType.TXT, "norwich-city.txt"),
        (FileType.WAV, "CantinaBand3.wav"),
        (FileType.WEBP, "img/DA-1p.webp"),
        (FileType.XML, "factbook.xml"),
        (FileType.NDJSON, "simple.ndjson"),
    ],
)
def test_it_detects_correct_file_type_from_extension_when_that_maps_to_a_file_type(
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
        (FileType.BMP, "img/bmp_24.bmp", "application/octet-stream"),
        (FileType.HEIC, "img/DA-1p.heic", "application/octet-stream"),
        (FileType.WEBP, "img/DA-1p.webp", "application/octet-stream"),
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


@pytest.mark.parametrize("mime_type", [FileType.XLS.mime_type, FileType.XLSX.mime_type])
def test_it_ignores_asserted_XLS_content_type_when_file_is_CSV(mime_type: str):
    file_path = example_doc_path("stanley-cups.csv")
    assert detect_filetype(file_path, content_type=mime_type) == FileType.CSV


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
    ("expected_value", "file_name"),
    [(FileType.NDJSON, "simple.ndjson"), (FileType.JSON, "spring-weather.html.json")],
)
def test_it_detects_correct_json_type_without_extension(expected_value: FileType, file_name: str):
    with open(example_doc_path(file_name), "rb") as f:
        file = io.BytesIO(f.read())

    filetype = detect_filetype(file=file)
    assert filetype == expected_value


@pytest.mark.parametrize(
    ("expected_value", "file_name"),
    [(FileType.NDJSON, "simple.ndjson"), (FileType.JSON, "spring-weather.html.json")],
)
def test_it_detects_correct_json_type_with_extension(expected_value: FileType, file_name: str):
    filetype = detect_filetype(file_path=example_doc_path(file_name))
    assert filetype == expected_value


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


@pytest.mark.parametrize("max_size", [0, 1])
def test_it_detects_a_SpooledTemporaryFile_in_place_and_rewinds_it(max_size: int):
    with open(example_doc_path("simple.docx"), "rb") as f:
        content = f.read()

    with tempfile.SpooledTemporaryFile(max_size=max_size) as spooled_file:
        spooled_file.write(content)
        spooled_file.seek(0)

        with patch.object(
            _FileTypeDetectionContext, "new", wraps=_FileTypeDetectionContext.new
        ) as new_:
            file_type = detect_filetype(file=spooled_file)

        assert file_type == FileType.DOCX
        assert new_.call_args.kwargs["file"] is spooled_file
        assert spooled_file.tell() == 0


def test_it_uses_metadata_file_path_extension_for_a_rolled_over_SpooledTemporaryFile():
    with tempfile.SpooledTemporaryFile(max_size=1) as spooled_file:
        spooled_file.write(b"# Heading\n\nSome *markdown* text.\n")
        assert spooled_file._rolled

        assert detect_filetype(file=spooled_file, metadata_file_path="notes.md") == FileType.MD


def test_it_ignores_the_temporary_file_name_of_a_rolled_over_SpooledTemporaryFile():
    # -- on Windows a rolled-over spool is named by its temporary file, never the upload --
    with tempfile.SpooledTemporaryFile(max_size=1) as spooled_file:
        spooled_file.write(b"# Heading\n\nSome *markdown* text.\n")
        spooled_file.seek(0)
        named = tempfile.NamedTemporaryFile(suffix=".tmp")  # noqa: SIM115 - closed by the spool
        named.write(spooled_file.read())
        spooled_file._file.close()  # pyright: ignore[reportPrivateUsage]
        spooled_file._file = named  # pyright: ignore[reportPrivateUsage]
        assert spooled_file.name.endswith(".tmp")

        assert detect_filetype(file=spooled_file, metadata_file_path="notes.md") == FileType.MD


def test_it_preserves_a_path_like_stream_name_extension():
    file = io.BytesIO(b"# Heading\n\nSome *markdown* text.\n")
    file.name = Path("notes.md")

    assert detect_filetype(file=file) == FileType.MD


@pytest.mark.parametrize("mime_type", ["text/plain", None])
def test_it_detects_MD_from_a_dot_markdown_extension(
    mime_type: str | None, tmp_path: Path, ctx_mime_type_: Mock
):
    # -- libmagic usually guesses "text/plain" for Markdown, `None` is the no-libmagic case --
    ctx_mime_type_.return_value = mime_type
    file_path = tmp_path / "notes.markdown"
    file_path.write_text("# Release notes\n\nThis release fixes several bugs.\n")

    assert detect_filetype(file_path=str(file_path)) is FileType.MD


def test_it_detect_CSV_from_path_and_file_when_content_contains_escaped_commas():
    file_path = example_doc_path("csv-with-escaped-commas.csv")

    assert detect_filetype(file_path) == FileType.CSV
    with open(file_path, "rb") as f:
        assert detect_filetype(file=f) == FileType.CSV


def test_it_detects_correct_file_type_for_custom_types(tmp_path):
    file_type = create_file_type("FOO", canonical_mime_type="application/foo", extensions=[".foo"])
    dumb_file = tmp_path / "dumb.foo"
    dumb_file.write_bytes(b"38v8df889qw8sdfj")
    assert detect_filetype(file_path=str(dumb_file), content_type="application/foo") is file_type


# ================================================================================================
# Describe `is_json_processable()`
# ================================================================================================


def it_warns_that_is_json_processable_is_deprecated():
    with pytest.warns(DeprecationWarning, match="is_json_processable\\(\\) is deprecated"):
        is_json_processable(file_text='[{"a": 1}]')


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
# Describe `is_ndjson_processable()`
# ================================================================================================


def it_warns_that_is_ndjson_processable_is_deprecated():
    with pytest.warns(DeprecationWarning, match="is_ndjson_processable\\(\\) is deprecated"):
        is_ndjson_processable(file_text='{"a": 1}\n{"b": 2}\n')


def it_still_reports_a_long_single_line_object_as_ndjson_processable_for_legacy_callers():
    # -- `is_ndjson_processable()` is deprecated and frozen: it still affirms a single-line
    # -- object as 1-record NDJSON even though `detect_filetype()` classifies the same payload
    # -- as `FileType.JSON` (see
    # -- `it_classifies_json_and_ndjson_correctly_when_first_record_exceeds_text_head_prefix`).
    # -- Kept only for backward compatibility; do not "fix" this divergence. --
    big_value = "x" * 5000
    payload_one_record = json.dumps({"text": big_value, "type": "NarrativeText"}).encode()

    assert is_ndjson_processable(file=io.BytesIO(payload_one_record)) is True


def it_recognizes_real_ndjson_with_multiple_object_lines():
    assert is_ndjson_processable(file_text='{"a": 1}\n{"b": 2}\n') is True


def it_recognizes_single_line_ndjson_with_trailing_newline():
    assert is_ndjson_processable(file_text='{"a": 1}\n{"b": 2}') is True


def it_rejects_a_multiline_single_json_object():
    # The bug: was True; now must be False so partition_ndjson does not get this payload.
    text = '{\n  "id": "Sample-1",\n  "name": "Sample 1"\n}'
    assert is_ndjson_processable(file_text=text) is False


def it_accepts_a_single_line_json_object_as_one_record_ndjson():
    """A single-line JSON object is a valid 1-record NDJSON payload.

    `partition_ndjson` parses it via `splitlines()` and yields one record. Existing callers
    rely on this; only multi-line single objects are pathological.
    """
    assert is_ndjson_processable(file_text='{"a": 1}') is True


def it_rejects_a_json_array_of_objects():
    assert is_ndjson_processable(file_text='[{"a": 1}, {"b": 2}]') is False


def it_rejects_whitespace_only():
    assert is_ndjson_processable(file_text="   \n  ") is False


def it_rejects_garbage_text():
    assert is_ndjson_processable(file_text="not json at all") is False


def it_rejects_a_jupyter_notebook_payload():
    """Jupyter notebooks are a single multi-line JSON object -- must not route to NDJSON."""
    notebook_text = (
        "{\n"
        ' "cells": [],\n'
        ' "metadata": {"kernelspec": {"name": "python3"}},\n'
        ' "nbformat": 4,\n'
        ' "nbformat_minor": 5\n'
        "}\n"
    )
    assert is_ndjson_processable(file_text=notebook_text) is False


def it_rejects_ndjson_first_line_is_a_bare_value_not_an_object():
    # NDJSON of bare values is uncommon and partition_ndjson expects dicts. Be strict.
    assert is_ndjson_processable(file_text="1\n2\n3\n") is False


# ================================================================================================
# Describe JSON/NDJSON disambiguation in `detect_filetype()`
# ================================================================================================


def it_classifies_a_compact_single_line_object_as_JSON():
    # -- a single JSON value is JSON, not NDJSON, even though it is also valid 1-line NDJSON --
    assert detect_filetype(example_doc_path("single-line-object.json")) == FileType.JSON


def and_it_classifies_a_compact_single_line_object_as_JSON_without_an_extension():
    payload = b'{"sku": "GRD-8842", "name": "Garden Trowel", "price": 12.5}'
    assert detect_filetype(file=io.BytesIO(payload)) == FileType.JSON


def and_it_classifies_a_pretty_printed_multi_line_object_as_JSON():
    payload = b'{\n  "sku": "GRD-8842",\n  "name": "Garden Trowel"\n}'
    assert detect_filetype(file=io.BytesIO(payload)) == FileType.JSON


def and_it_classifies_a_single_line_array_as_JSON():
    payload = b'[{"sku": "GRD-8842"}, {"sku": "GRD-1290"}]'
    assert detect_filetype(file=io.BytesIO(payload)) == FileType.JSON


def and_it_falls_back_to_JSON_when_multiple_lines_are_not_all_JSON_values():
    # -- an asserted-JSON payload that neither whole-parses nor line-parses exercises the
    # -- per-line except fallback: not valid JSON, not valid NDJSON -> FileType.JSON --
    payload = b'not json at all\n{"sku": "GRD-8842"}\n'
    filetype = detect_filetype(file=io.BytesIO(payload), content_type="application/json")
    assert filetype == FileType.JSON


def it_classifies_multiple_json_object_lines_as_NDJSON():
    payload = b'{"sku": "GRD-8842"}\n{"sku": "GRD-1290"}\n{"sku": "GRD-3317"}\n'
    assert detect_filetype(file=io.BytesIO(payload)) == FileType.NDJSON


def and_it_classifies_an_arbitrary_ndjson_file_as_NDJSON():
    assert detect_filetype(example_doc_path("arbitrary-records.ndjson")) == FileType.NDJSON


def and_it_classifies_a_non_UTF8_ndjson_file_like_object_as_NDJSON():
    """Regression for #4434: a non-UTF-8 payload must not be decoded with `errors="ignore"`.

    Disambiguation decoded its read using the declared encoding with `errors="ignore"`, which
    silently stripped every byte UTF-8 could not decode. A UTF-16 payload -- such as NDJSON
    written by Windows tooling and uploaded to S3/GCS -- was mangled into text whose lines no
    longer parsed, so a multi-record payload classified as JSON instead of NDJSON.
    """
    records = [{"sku": "GRD-8842", "name": "café münchen"}, {"sku": "GRD-1290", "name": "büro"}]
    ndjson_text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    payload = ndjson_text.encode("utf-16")

    file_type = detect_filetype(file=io.BytesIO(payload), content_type=FileType.JSON.mime_type)

    assert file_type == FileType.NDJSON


def and_it_classifies_a_non_UTF8_json_file_as_NDJSON(tmp_path):
    # -- a file path is read as bytes for disambiguation just like a file-like object, so it
    # -- decodes through the same fallback and is no longer misclassified either --
    records = [{"sku": "GRD-8842"}, {"sku": "GRD-1290"}]
    payload = "\n".join(json.dumps(record) for record in records).encode("utf-16")
    json_file = tmp_path / "records.json"
    json_file.write_bytes(payload)

    file_type = detect_filetype(file_path=str(json_file), content_type=FileType.JSON.mime_type)

    assert file_type == FileType.NDJSON


def and_it_decodes_a_non_UTF8_head_without_stripping_its_characters():
    # -- characters of a non-UTF-8 payload survive the decode used for classification instead
    # -- of being dropped as undecodable --
    text = '{"name": "café münchen"}'

    assert _decode_head_bytes(text.encode("cp1252"), encoding="utf-8", eof_reached=True) == text


_ABOVE_BOUND_RECORD = '{"x":1}\n'

_BOM_BY_ENCODING = {"utf-16": codecs.BOM_UTF16_LE, "utf-32": codecs.BOM_UTF32_LE}


def _above_bound_bom_less_ndjson(encoding: str) -> bytes:
    """Native-endian NDJSON, no BOM, larger than the disambiguation read bound."""

    record_count = (_JSON_DISAMBIGUATION_MAX_CHARS // len(_ABOVE_BOUND_RECORD)) + 4096
    payload = (_ABOVE_BOUND_RECORD * record_count).encode(encoding)
    return payload[len(_BOM_BY_ENCODING[encoding]) :]


class _ShortReadStream(io.BytesIO):
    """A seekable stream whose `read(n)` returns at most `chunk_size` bytes.

    A raw stream or adapter may return fewer bytes than requested while more data remains, so
    a single short read does not establish EOF. Every read is recorded as
    `(position, requested size, returned length)`.
    """

    def __init__(self, payload: bytes, chunk_size: int):
        super().__init__(payload)
        self._chunk_size = chunk_size
        self.reads: list[tuple[int, int, int]] = []

    def read(self, size: int = -1) -> bytes:
        position = self.tell()
        chunk = super().read(size) if size < 0 else super().read(min(size, self._chunk_size))
        self.reads.append((position, size, len(chunk)))
        return chunk

    def prefix_reads(self) -> list[tuple[int, int, int]]:
        """The reads spent accumulating the disambiguation prefix, in order."""

        start = next(
            index
            for index, (_, size, _) in enumerate(self.reads)
            if size == _JSON_DISAMBIGUATION_MAX_CHARS + 1
        )
        return self.reads[start:]


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def and_it_decodes_a_BOM_less_prefix_cut_inside_a_code_unit(encoding):
    # -- `codecs.getincrementaldecoder()` re-runs BOM detection over the prefix and refuses
    # -- BOM-less native-endian UTF-16/32, so the decode of a prefix that crossed the read bound
    # -- inside a code unit used to fall through to character-set inference
    payload = _above_bound_bom_less_ndjson(encoding)
    cut_prefix = payload[: _JSON_DISAMBIGUATION_MAX_CHARS + 1]
    complete_prefix = cut_prefix[:_JSON_DISAMBIGUATION_MAX_CHARS]

    with patch("unstructured.file_utils.filetype.detect_file_encoding") as detect_mock:
        assert _decode_head_bytes(cut_prefix, encoding=encoding, eof_reached=False) == (
            complete_prefix.decode(encoding)
        )
    detect_mock.assert_not_called()


def and_it_still_fails_a_prefix_whose_tail_is_missing_at_EOF():
    # -- a character cut by the end of the document is a real defect, not a boundary split, so
    # -- withholding trailing bytes applies only while more content follows --
    payload = (_ABOVE_BOUND_RECORD * 100).encode("utf-16")

    whole_text = payload.decode("utf-16")

    with pytest.raises(UnprocessableEntityError):
        _decode_head_bytes(payload[:-1], encoding="utf-16", eof_reached=True)

    assert _decode_head_bytes(payload[:-1], encoding="utf-16", eof_reached=False) == whole_text[:-1]


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def and_it_classifies_above_bound_BOM_less_UTF16_and_UTF32_payloads_as_NDJSON(encoding, tmp_path):
    # -- the asserted encoding decides the byte order for a payload larger than the read bound,
    # -- whether it arrives as a file path or as a byte stream, so no inference warning fires --
    payload = _above_bound_bom_less_ndjson(encoding)
    json_file = tmp_path / "records.json"
    json_file.write_bytes(payload)

    with (
        patch("unstructured.file_utils.filetype.detect_file_encoding") as detect_mock,
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error", EncodingDetectionWarning)
        assert (
            detect_filetype(
                file=io.BytesIO(payload), encoding=encoding, content_type=FileType.JSON.mime_type
            )
            == FileType.NDJSON
        )
        assert (
            detect_filetype(
                file_path=str(json_file), encoding=encoding, content_type=FileType.JSON.mime_type
            )
            == FileType.NDJSON
        )
    detect_mock.assert_not_called()


def and_it_reads_past_a_short_read_until_the_budget_or_EOF():
    # -- a short read is not EOF: the prefix has to be accumulated until the budget is spent or
    # -- an empty read proves the end, or a character cut by the short read is taken for a
    # -- malformed document --
    payload = _ABOVE_BOUND_RECORD.encode() * ((_JSON_DISAMBIGUATION_MAX_CHARS // 8) + 4096)
    stream = _ShortReadStream(payload, 4095)

    assert detect_filetype(file=stream, content_type=FileType.JSON.mime_type) == FileType.NDJSON

    prefix_reads = stream.prefix_reads()
    returned_lengths = [returned for _, _, returned in prefix_reads]
    assert prefix_reads[0][0] == 0
    assert max(returned_lengths[:-1]) == 4095
    assert sum(returned_lengths[:-1]) == _JSON_DISAMBIGUATION_MAX_CHARS + 1
    assert prefix_reads[-1] == (_JSON_DISAMBIGUATION_MAX_CHARS + 1, 1, 1)
    assert all(size <= _JSON_DISAMBIGUATION_MAX_CHARS + 1 for _, size, _ in stream.reads)

    assert stream.tell() == 0
    assert not stream.closed
    assert stream.read(4) == payload[:4]

    short_payload = _ABOVE_BOUND_RECORD.encode() * 3
    short_stream = _ShortReadStream(short_payload, 4)

    assert (
        detect_filetype(file=short_stream, content_type=FileType.JSON.mime_type) == FileType.NDJSON
    )
    short_prefix_reads = short_stream.prefix_reads()
    assert sum(returned for _, _, returned in short_prefix_reads) == len(short_payload)


# -- a byte sequence the declared codec REJECTS and a character the read boundary CUT look the
# -- same to a decoder that only retries shorter prefixes: both decode once the tail is gone. The
# -- difference is what the tail means. `é` is a complete character followed by a delimiter, so
# -- dropping it deletes real content and the fallback never runs; `\xc3` on its own is an
# -- unfinished character whose completion is simply not in this read.


@pytest.mark.parametrize(
    ("content", "encoding", "expected_value"),
    [
        # -- an unfinished character: withhold it, keep everything that did decode --
        (b'{"a":1}\n{"a":2}\n' + b"\xc3", "utf-8", '{"a":1}\n{"a":2}\n'),
        (b"ab\xe2\x82", "utf-8", "ab"),
        (b"a\x00b", "utf-16-le", "a"),
        ("\u65e5\u672c".encode("shift_jis") + b"\x93", "shift_jis", "\u65e5\u672c"),
        # -- a complete character the codec rejects outright: not a boundary split --
        (b"a,b\n" + b"a" * 4089 + b"\xc3\xa9,", "ascii", None),
        (b"ab\xff", "ascii", None),
        # -- a wrong encoding rather than a split character, so nothing is withheld --
        (b"\xff" + b"ab" * 100, "ascii", None),
        # -- a whole read that is one unfinished character has nothing to classify --
        (b"\xc3", "utf-8", None),
    ],
)
def it_decodes_a_cut_character_without_dropping_a_rejected_one(content, encoding, expected_value):
    assert _decode_prefix(content, encoding) == expected_value


def and_it_keeps_a_complete_character_at_the_read_boundary_in_the_text_it_classifies(
    ctx_mime_type_: Mock,
):
    # -- an ASCII-asserted CSV whose 4096-byte read ends on a complete UTF-8 `é` and the comma
    # -- after it: withholding bytes until ASCII accepted the remainder deleted both, so the
    # -- second row lost its delimiter, `_is_csv` rejected it, and the file classified as TXT
    ctx_mime_type_.return_value = "text/plain"
    payload = b"a,b\n" + b"a" * 4089 + "é,".encode() + b"rest\n"
    head = payload[:4096]
    assert head.endswith("é,".encode())
    assert len(head) == 4096

    assert detect_filetype(file=io.BytesIO(payload), encoding="ascii") is FileType.CSV

    ctx = _FileTypeDetectionContext(file=io.BytesIO(payload), encoding="ascii")
    assert ctx.text_head.endswith("é,")


# -- a BOM-prefixed CSV whose 4,096-byte read ends inside `é`, one byte short of the second
# -- row's delimiter-adjacent multibyte character. `utf-8-sig` strips the three BOM bytes before
# -- reporting a decode offset, so applying that offset to the original buffer removed three
# -- valid bytes ahead of the cut: the row delimiter and the two characters before it. All
# -- complete characters and the delimiter have to survive for `_is_csv` to see two columns.
_BOM_PREFIXED_CSV_CUT_INSIDE_A_CHARACTER = (
    codecs.BOM_UTF8 + b"a,b\n" + b"a" * 4087 + b",\xc3\xa9rest\n"
)
_BOM_PREFIXED_CSV_HEAD_BYTES = 4096


def and_it_withholds_only_the_cut_character_when_UTF8_sig_carries_a_BOM():
    head = _BOM_PREFIXED_CSV_CUT_INSIDE_A_CHARACTER[:_BOM_PREFIXED_CSV_HEAD_BYTES]
    assert head.endswith(b",\xc3")

    text = _decode_prefix(head, "utf-8-sig")

    assert text == head[:-1].decode("utf-8-sig")
    assert text.endswith(",")


def and_it_keeps_a_multibyte_character_that_sits_ahead_of_the_cut_character():
    # -- the byte offset `utf-8-sig` reports is relative to the buffer after the BOM, so a cut
    # -- taken from it landed inside the complete `e-acute` before the unfinished character and
    # -- the retry raised UnicodeDecodeError on a valid read
    payload = codecs.BOM_UTF8 + b"a,b\n" + b"a" * 4084 + "\u00e9".encode() + b"aa" + b"\xc3"
    head = payload[:4096]
    assert head.endswith("\u00e9aa".encode() + b"\xc3")
    assert head[4091:4093] == "\u00e9".encode()

    assert _decode_prefix(head, "utf-8-sig") == head[:-1].decode("utf-8-sig")


def and_it_classifies_a_BOM_prefixed_UTF8_sig_CSV_cut_inside_a_character(
    ctx_mime_type_: Mock,
):
    # -- the reported regression, end to end on a byte stream: the cut character is withheld, the
    # -- delimiter before it survives, the CSV is still a CSV, and no inference runs --
    ctx_mime_type_.return_value = "text/plain"
    payload = _BOM_PREFIXED_CSV_CUT_INSIDE_A_CHARACTER

    with (
        patch("unstructured.file_utils.filetype.detect_file_encoding") as detect_mock,
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error", EncodingDetectionWarning)
        assert detect_filetype(file=io.BytesIO(payload), encoding="utf-8-sig") is FileType.CSV
    detect_mock.assert_not_called()

    ctx = _FileTypeDetectionContext(file=io.BytesIO(payload), encoding="utf-8-sig")
    assert ctx.text_head == payload[:_BOM_PREFIXED_CSV_HEAD_BYTES - 1].decode("utf-8-sig")
    assert "\xc3\xa9" not in ctx.text_head


def and_it_classifies_the_same_BOM_prefixed_UTF8_sig_CSV_from_a_path(
    ctx_mime_type_: Mock, tmp_path
):
    # -- the path branch reads text through the codec, so it never splits a character; the same
    # -- payload has to classify identically from disk --
    ctx_mime_type_.return_value = "text/plain"
    csv_file = tmp_path / "records"
    csv_file.write_bytes(_BOM_PREFIXED_CSV_CUT_INSIDE_A_CHARACTER)

    with (
        patch("unstructured.file_utils.filetype.detect_file_encoding") as detect_mock,
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error", EncodingDetectionWarning)
        assert (
            detect_filetype(file_path=str(csv_file), encoding="utf-8-sig") is FileType.CSV
        )
    detect_mock.assert_not_called()


def it_routes_not_unstructured_payload_json_away_from_ndjson_via_detect_filetype():
    file_type = detect_filetype(example_doc_path("not-unstructured-payload.json"))
    # A multi-line single-object JSON file used to get classified as NDJSON. It should now end up
    # as JSON (and partition_json now partitions it as arbitrary JSON).
    assert file_type == FileType.JSON


def it_classifies_json_and_ndjson_correctly_when_first_record_exceeds_text_head_prefix():
    """JSON/NDJSON whose first record is longer than the 4096-char text_head prefix.

    `_disambiguate_json_file_type` reads past `text_head` to find the first newline, so the
    heuristic must not rely on the first record fitting in the prefix. A single-record payload
    is one JSON value and classifies as `FileType.JSON`; only the multi-record payload is
    `FileType.NDJSON`.
    """
    big_value = "x" * 5000
    payload_one_record = json.dumps({"text": big_value, "type": "NarrativeText"}).encode()
    payload_many_records = (
        payload_one_record + b"\n" + json.dumps({"text": "tiny", "type": "Title"}).encode()
    )

    assert detect_filetype(file=io.BytesIO(payload_one_record)) == FileType.JSON
    assert detect_filetype(file=io.BytesIO(payload_many_records)) == FileType.NDJSON


def it_classifies_multiline_json_as_json_when_first_newline_exceeds_text_head_prefix():
    big_value = "x" * 5000
    payload = ('{"text": "' + big_value + '",\n "type": "NarrativeText"\n}').encode()

    assert detect_filetype(file=io.BytesIO(payload)) == FileType.JSON


def it_leaves_a_caller_owned_file_at_position_zero_after_json_disambiguation():
    # -- regression: disambiguation used to leave the file at EOF, so a detect-then-partition
    # -- sequence on the same handle read an empty payload --
    with open(example_doc_path("simple.json"), "rb") as f:
        file = io.BytesIO(f.read())

    file_type = detect_filetype(file=file)

    assert file_type == FileType.JSON
    assert file.tell() == 0


def it_detects_a_file_type_for_a_deeply_nested_payload_without_RecursionError():
    # -- the whole-payload parse raises RecursionError (not JSONDecodeError) on deep nesting;
    # -- classification must swallow it and fall back to JSON rather than letting it escape --
    file_type = detect_filetype(file=io.BytesIO(b"[" * 200000), content_type="application/json")

    assert file_type == FileType.JSON


def it_reads_only_a_bounded_prefix_and_classifies_oversized_ndjson_as_NDJSON(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    payload = b'{"sku": "GRD-8842", "qty": 3}\n' * 100

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.NDJSON


def and_it_classifies_ndjson_whose_second_record_spans_the_bound_as_NDJSON(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- a single complete line within the bound is enough to classify NDJSON, even when the
    # -- next record runs past the read bound --
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    payload = b'{"sku": "GRD-8842", "qty": 3}\n' + json.dumps({"description": "x" * 500}).encode()

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.NDJSON


@pytest.mark.parametrize("trailing_newline", [True, False])
def and_it_classifies_two_record_ndjson_of_exactly_the_bound_plus_one_as_NDJSON(
    monkeypatch: pytest.MonkeyPatch, trailing_newline: bool
):
    # -- a payload of exactly MAX+1 chars is fully in hand, not truncated, so it classifies on
    # -- its whole content rather than dropping the (complete) final line as a partial tail --
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    second_record = b'{"sku": "B-200"}' + (b"\n" if trailing_newline else b"")
    pad_len = 129 - len(second_record) - len(b'{"sku": ""}\n')
    payload = b'{"sku": "' + b"A" * pad_len + b'"}\n' + second_record
    assert len(payload) == 129

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.NDJSON


def and_it_classifies_a_single_record_of_exactly_the_bound_plus_one_ending_in_newline_as_JSON(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- pins the two-step truncation probe: a lone MAX+1-char record ending in a newline is
    # -- fully in hand, so the whole-payload parse wins and classifies JSON. A length-only probe
    # -- (`truncated = len(head) > MAX`) would falsely flag truncation, classify on the complete
    # -- first line, and flip this payload to NDJSON --
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    pad_len = 129 - len(b'{"note": ""}\n')
    payload = b'{"note": "' + b"A" * pad_len + b'"}\n'
    assert len(payload) == 129
    assert payload.endswith(b"\n")

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.JSON


def and_it_classifies_oversized_compact_single_line_json_as_JSON_from_its_bounded_prefix(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- no complete line fits within the bound, so classification falls back to JSON --
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    payload = json.dumps({"description": "x" * 500}).encode()

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.JSON


def and_it_classifies_oversized_pretty_printed_json_as_JSON_from_its_bounded_prefix(
    monkeypatch: pytest.MonkeyPatch,
):
    # -- complete lines fit within the bound but do not individually parse, so JSON --
    monkeypatch.setattr("unstructured.file_utils.filetype._JSON_DISAMBIGUATION_MAX_CHARS", 128)
    payload = json.dumps({f"key-{i}": i for i in range(100)}, indent=2).encode()

    file_type = detect_filetype(file=io.BytesIO(payload), content_type="application/json")

    assert file_type == FileType.JSON


def it_ties_a_one_record_ndjson_source_to_NDJSON_over_a_whole_json_parse():
    # -- a one-record ".ndjson" is also valid one-value JSON, but the explicit ".ndjson" signal
    # -- (here paired with an asserted "application/json" content-type) wins the tie-break --
    payload = b'{"type": "Title", "text": "hello"}\n'

    file_type = detect_filetype(
        file=io.BytesIO(payload),
        metadata_file_path="one-record.ndjson",
        content_type="application/json",
    )

    assert file_type == FileType.NDJSON


def and_a_multi_record_ndjson_source_stays_NDJSON():
    payload = b'{"type": "Title", "text": "a"}\n{"type": "Title", "text": "b"}\n'

    file_type = detect_filetype(
        file=io.BytesIO(payload),
        metadata_file_path="records.ndjson",
        content_type="application/json",
    )

    assert file_type == FileType.NDJSON


def but_a_compact_single_line_json_object_still_classifies_as_JSON():
    # -- the NDJSON tie-break must not touch ".json" or extension-less sources: the SAP
    # -- compact-object path stays JSON --
    payload = b'{"type": "Title", "text": "hello"}'

    assert (
        detect_filetype(file=io.BytesIO(payload), metadata_file_path="one-record.json")
        == FileType.JSON
    )


def it_classifies_a_scalar_json_source_as_JSON():
    # -- a bare scalar is valid JSON; a ".json" source must reach JSON, not fall through to TXT --
    file_type = detect_filetype(file=io.BytesIO(b"123"), metadata_file_path="scalar.json")

    assert file_type == FileType.JSON


def it_classifies_a_scalar_per_line_ndjson_source_as_NDJSON():
    file_type = detect_filetype(file=io.BytesIO(b'1\n2\n"x"\n'), metadata_file_path="scalar.ndjson")

    assert file_type == FileType.NDJSON


def but_a_genuinely_textual_txt_source_stays_TXT():
    # -- the scalar allowance is scoped to JSON/NDJSON sources; plain prose in a ".txt" is TXT --
    payload = b"just some prose\nwith another line\n"

    assert detect_filetype(file=io.BytesIO(payload), metadata_file_path="notes.txt") == FileType.TXT


def it_does_not_classify_a_json_source_containing_NaN_as_parseable_ndjson():
    # -- the detector uses the partitioners' strict parser, so `NaN` lines (which json.loads
    # -- accepts by default) are not treated as valid JSON values and do not flip to NDJSON --
    payload = b"NaN\nNaN\n"

    assert (
        detect_filetype(file=io.BytesIO(payload), content_type="application/json") == FileType.JSON
    )


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

    def and_it_ignores_a_file_name_that_is_not_a_string(self):
        with tempfile.SpooledTemporaryFile(max_size=1) as spooled_file:
            spooled_file.write(b"<html></html>")

            ctx = _FileTypeDetectionContext(file=spooled_file, metadata_file_path="a/b/c.html")

            assert ctx.extension == ".html"

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

    def and_it_uses_character_detection_to_correct_a_wrong_encoding_arg_for_a_file_like_object(
        self,
    ):
        """Fallback character detection corrects a wrong encoding arg, like the file-path case."""
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            file = io.BytesIO(f.read())
        ctx = _FileTypeDetectionContext(file=file, encoding="utf_32_be")

        text_head = ctx.text_head

        assert isinstance(text_head, str)
        assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def and_it_detects_a_non_utf8_file_like_object_instead_of_stripping_its_characters(self):
        """A non-UTF-8 file-like object is decoded via fallback detection, not errors="ignore".

        Regression for #4434: decoding with errors="ignore" silently stripped the
        undecodable characters, corrupting the text head for cloud-storage streams.
        """
        content = "café à la résumé".encode("iso_8859_1")
        ctx = _FileTypeDetectionContext(file=io.BytesIO(content))

        text_head = ctx.text_head

        assert "café" in text_head
        assert "résumé" in text_head

    def and_it_grabs_the_first_4k_chars_from_binary_file_for_textual_type_differentiation(self):
        with open(example_doc_path("norwich-city.txt"), "rb") as f:
            ctx = _FileTypeDetectionContext(file=f)

            text_head = ctx.text_head

            assert isinstance(text_head, str)
            # -- some characters consume multiple bytes, so shorter than 4096 --
            assert len(text_head) == 4063
            assert text_head.startswith("Iwan Roberts\nRoberts celebrating after")

    def and_it_runs_character_detection_for_a_truncated_utf8_tail(self):
        """A truncated stream must fall through to detection, not silently drop the tail."""
        content = b"caf\xc3"
        ctx = _FileTypeDetectionContext(file=io.BytesIO(content))

        # -- a silently-truncated decode would return exactly "caf" --
        assert ctx.text_head != "caf"

    def and_it_does_not_mistake_a_boundary_split_character_for_a_wrong_encoding(self):
        """A multi-byte character split by the 4096-byte read is not a decode error."""
        content = b"a" * 4095 + "é".encode()
        ctx = _FileTypeDetectionContext(file=io.BytesIO(content))

        text_head = ctx.text_head

        assert text_head == "a" * 4095

    @pytest.mark.parametrize(
        ("bom", "encoding"),
        [(codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be")],
    )
    def and_it_does_not_mistake_a_boundary_split_surrogate_pair_for_a_decode_error(
        self, bom: bytes, encoding: str
    ):
        """After a UTF-16 BOM, a surrogate pair split by the 4096-byte read is not an error."""
        # -- BOM + 2046 two-byte chars leaves the emoji's high surrogate as the last 2 bytes --
        file = io.BytesIO(bom + ("a" * 2046 + "\U0001f600\n").encode(encoding))
        ctx = _FileTypeDetectionContext(file=file)

        text_head = ctx.text_head

        assert text_head == "a" * 2046
        assert file.tell() == 0

    @pytest.mark.parametrize(
        ("bom", "encoding"),
        [(codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be")],
    )
    def but_it_rejects_a_utf16_stream_that_ends_inside_a_surrogate_pair(
        self, bom: bytes, encoding: str
    ):
        file = io.BytesIO(bom + ("a" * 10 + "\U0001f600").encode(encoding)[:-2])
        ctx = _FileTypeDetectionContext(file=file)

        with pytest.raises(UnprocessableEntityError, match="decode failed"):
            ctx.text_head

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


class Describe_OleFileDetector:
    """Unit-test suite for `unstructured.file_utils.filetype._OleFileDetector`."""

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
    def it_distinguishes_the_file_type_of_applicable_CFB_files(
        self, file_name: str, expected_value: FileType | None
    ):
        # -- no file-name available, just to make sure we're not relying on an extension --
        with open(example_doc_path(file_name), "rb") as f:
            file = io.BytesIO(f.read())
        ctx = _FileTypeDetectionContext(file=file)

        assert _OleFileDetector.file_type(ctx) is expected_value


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


class Describe_ZipFileDetector:
    """Unit-test suite for `unstructured.file_utils.filetype._ZipFileDetector`."""

    @pytest.mark.parametrize(
        ("file_name", "expected_value"),
        [
            ("simple.docx", FileType.DOCX),
            ("winter-sports.epub", FileType.EPUB),
            ("simple.odt", FileType.ODT),
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
        assert _ZipFileDetector.file_type(ctx) is expected_value


def test_mimetype_magic_detection_is_used_before_filename_when_filetype_is_detected_for_json():
    json_bytes = json.dumps([{"example": "data"}]).encode("utf-8")

    file_buffer = io.BytesIO(json_bytes)
    predicted_type = detect_filetype(file=file_buffer, metadata_file_path="filename.pdf")
    assert predicted_type == FileType.JSON

    file_buffer.name = "filename.pdf"
    predicted_type = detect_filetype(file=file_buffer)
    assert predicted_type == FileType.JSON


def test_mimetype_magic_detection_is_used_before_filename_when_filetype_is_detected_for_ndjson():
    data = [{"example": "data1"}, {"example": "data2"}, {"example": "data3"}]
    ndjson_string = "\n".join(json.dumps(item) for item in data) + "\n"
    ndjson_bytes = ndjson_string.encode("utf-8")

    file_buffer = io.BytesIO(ndjson_bytes)
    predicted_type = detect_filetype(file=file_buffer, metadata_file_path="filename.pdf")
    assert predicted_type == FileType.NDJSON

    file_buffer.name = "filename.pdf"
    predicted_type = detect_filetype(file=file_buffer)
    assert predicted_type == FileType.NDJSON


def test_json_content_type_is_disambiguated_for_ndjson():
    data = [{"example": "data1"}, {"example": "data2"}, {"example": "data3"}]
    ndjson_string = "\n".join(json.dumps(item) for item in data) + "\n"
    ndjson_bytes = ndjson_string.encode("utf-8")

    file_buffer = io.BytesIO(ndjson_bytes)
    predicted_type = detect_filetype(
        file=file_buffer, metadata_file_path="filename.pdf", content_type="application/json"
    )
    assert predicted_type == FileType.NDJSON

    file_buffer.name = "filename.pdf"
    predicted_type = detect_filetype(file=file_buffer, content_type="application/json")
    assert predicted_type == FileType.NDJSON


def test_office_files_when_document_archive_has_non_standard_prefix():
    predicted_type = detect_filetype(
        file_path=input_path("file_type/test_document_from_office365.docx")
    )
    assert predicted_type == FileType.DOCX


@pytest.mark.parametrize("name", ["temporary-upload", Path("temporary-upload"), 42, None])
def test_extensionless_stream_names_fall_back_to_metadata_file_path(name):
    file = io.BytesIO(b"# Heading\n\nSome *markdown* text.\n")
    file.name = name
    assert detect_filetype(file=file, metadata_file_path="notes.md") == FileType.MD
