"""Test-suite for `unstructured.partition.xml` module."""

from __future__ import annotations

from contextlib import ExitStack
from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile

import pytest
from pytest_mock import MockerFixture

from test_unstructured.unit_utils import example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import NarrativeText, Title
from unstructured.partition.json import partition_json
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA
from unstructured.partition.xml import partition_xml
from unstructured.staging.base import elements_to_json


@pytest.mark.parametrize("source", ["filename", "file", "bytesio", "spooled"])
@pytest.mark.parametrize("xml_path", [None, "//item"])
@pytest.mark.parametrize(
    ("encoding", "byte_encoding", "text"),
    [
        ("windows-1252", "windows-1252", "Café crème"),
        ("windows-1251", "windows-1251", "Привет"),
        ("utf-8-sig", "utf-8", "Café 中文"),
        ("utf-8-sig", "utf-8-sig", "Café 中文"),
        ("utf_8_sig", "utf-8", "Café 中文"),
        ("utf_8_sig", "utf-8-sig", "Café 中文"),
    ],
)
def test_partition_xml_honors_explicit_encoding(
    tmp_path: Path, source: str, xml_path: str | None, encoding: str, byte_encoding: str, text: str
):
    data = f"<root><item>{text}</item></root>".encode(byte_encoding)
    path = tmp_path / "encoded.xml"
    path.write_bytes(data)

    with ExitStack() as stack:
        if source == "filename":
            kwargs = {"filename": str(path)}
        elif source == "file":
            kwargs = {"file": stack.enter_context(path.open("rb"))}
        elif source == "bytesio":
            kwargs = {"file": BytesIO(data)}
        else:
            stream = stack.enter_context(SpooledTemporaryFile(max_size=1))
            stream.write(data)
            stream.seek(0)
            kwargs = {"file": stream}

        elements = partition_xml(**kwargs, encoding=encoding, xml_path=xml_path, languages=["eng"])

        if "file" in kwargs:
            assert not kwargs["file"].closed
            kwargs["file"].seek(0)
            assert kwargs["file"].read() == data

    assert [element.text for element in elements] == [text]


@pytest.mark.parametrize("xml_path", [None, "//item"])
@pytest.mark.parametrize(
    ("encoding", "byte_encoding", "declaration"),
    [
        ("windows-1252", "windows-1252", "UTF-8"),
        ("utf-8-sig", "utf-8", "windows-1252"),
        ("utf-8-sig", "utf-8-sig", "windows-1252"),
        ("utf_8_sig", "utf-8", "windows-1252"),
        ("utf_8_sig", "utf-8-sig", "windows-1252"),
    ],
)
def test_partition_xml_explicit_encoding_overrides_declaration(
    encoding: str, byte_encoding: str, declaration: str, xml_path: str | None
):
    data = (f'<?xml version="1.0" encoding="{declaration}"?><root><item>Café</item></root>').encode(
        byte_encoding
    )

    stream = BytesIO(data)
    elements = partition_xml(file=stream, encoding=encoding, xml_path=xml_path, languages=["eng"])

    assert [element.text for element in elements] == ["Café"]
    assert not stream.closed


@pytest.mark.parametrize("xml_path", [None, "//item"])
def test_partition_xml_preserves_libxml2_encoding_names(xml_path: str | None):
    data = "<root><item>Café</item></root>".encode("utf-32-be")

    elements = partition_xml(
        file=BytesIO(data), encoding="UCS-4", xml_path=xml_path, languages=["eng"]
    )

    assert [element.text for element in elements] == ["Café"]


@pytest.mark.parametrize("xml_path", [None, "//item"])
def test_partition_xml_rejects_unknown_encoding_without_closing_stream(xml_path: str | None):
    stream = BytesIO(b"<root><item>Example</item></root>")

    with pytest.raises(LookupError, match="unknown encoding"):
        partition_xml(file=stream, encoding="not-an-encoding", xml_path=xml_path)

    assert not stream.closed


def test_partition_xml_detects_declared_encoding():
    data = '<?xml version="1.0" encoding="windows-1252"?><root><item>Café</item></root>'.encode(
        "windows-1252"
    )

    elements = partition_xml(file=BytesIO(data), languages=["eng"])

    assert [element.text for element in elements] == ["Café"]


def test_partition_xml_does_not_apply_byte_encoding_to_text():
    elements = partition_xml(
        text="<root><item>Café 中文</item></root>", encoding="windows-1252", languages=["eng"]
    )

    assert [element.text for element in elements] == ["Café 中文"]


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_filename(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        assert {element.metadata.detection_origin for element in elements} == {"xml"}


def test_partition_xml_from_filename_with_metadata_filename():
    elements = partition_xml(
        example_doc_path("factbook.xml"), xml_keep_tags=False, metadata_filename="test"
    )

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_with_metadata_filename():
    with open(example_doc_path("factbook.xml"), "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename="test")

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == "test"


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_rb(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=False, metadata_filename=file_path)

    assert elements[0].text == "United States"
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_filename_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_text_with_tags():
    with open(example_doc_path("factbook.xml")) as f:
        text = f.read()
    elements = partition_xml(text=text, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text


def test_partition_xml_from_filename_with_tags_raises_encoding_error():
    with pytest.raises(UnicodeDecodeError):
        partition_xml(example_doc_path("factbook-utf-16.xml"), xml_keep_tags=True, encoding="utf-8")


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_from_file_rb_with_tags_default_encoding(filename: str):
    file_path = example_doc_path(filename)
    with open(file_path, "rb") as f:
        elements = partition_xml(file=f, xml_keep_tags=True, metadata_filename=file_path)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == filename


def test_partition_xml_from_file_rb_with_tags_raises_encoding_error():
    with pytest.raises(UnicodeDecodeError):
        with open(example_doc_path("factbook-utf-16.xml"), "rb") as f:
            partition_xml(
                file=f,
                xml_keep_tags=True,
                encoding="utf-8",
            )


# -- .metadata.filetype --------------------------------------------------------------------------


def test_partition_xml_gets_the_XML_mime_type_in_metadata_filetype():
    XML_MIME_TYPE = "application/xml"
    elements = partition_xml(example_doc_path("factbook.xml"))
    assert all(e.metadata.filetype == XML_MIME_TYPE for e in elements), (
        f"Expected all elements to have '{XML_MIME_TYPE}' as their filetype, but got:"
        f" {repr(elements[0].metadata.filetype)}"
    )


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_xml_from_file_path_gets_last_modified_from_filesystem(mocker: MockerFixture):
    mocked_last_modification_date = "2029-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )

    elements = partition_xml(filename="example-docs/factbook.xml")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_xml_from_file_gets_last_modified_None():
    with open("example-docs/factbook.xml", "rb") as f:
        elements = partition_xml(file=f)

    assert elements[0].metadata.last_modified is None


def test_partition_xml_from_file_path_prefers_metadata_last_modified(mocker: MockerFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2020-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.xml.get_last_modified_date", return_value=filesystem_last_modified
    )

    elements = partition_xml(
        filename="example-docs/factbook.xml",
        metadata_last_modified=metadata_last_modified,
    )

    assert elements[0].metadata.last_modified == metadata_last_modified


def test_partition_xml_from_file_prefers_metadata_last_modified():
    with open("example-docs/factbook.xml", "rb") as f:
        elements = partition_xml(file=f, metadata_last_modified="2029-07-05T09:24:28")

    assert elements[0].metadata.last_modified == "2029-07-05T09:24:28"


# ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["factbook.xml", "factbook-utf-16.xml"])
def test_partition_xml_with_json(filename: str):
    file_path = example_doc_path(filename)
    elements = partition_xml(filename=file_path, xml_keep_tags=False)
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    assert elements[0].metadata.filename == test_elements[0].metadata.filename

    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_partition_xml_with_narrative_line_breaks():
    xml_text = """<xml>
        <parrot>
            <name>Conure</name>
            <description>A conure is a very friendly bird.
            Conures are feathery and like to dance.
            </description>
        </parrot>
    </xml>"""

    elements = partition_xml(text=xml_text)
    assert elements[0] == Title("Conure")
    assert isinstance(elements[1], NarrativeText)
    assert str(elements[1]).startswith("A conure is a very friendly bird.")
    assert str(elements[1]).strip().endswith("Conures are feathery and like to dance.")


def test_add_chunking_strategy_on_partition_xml():
    file_path = example_doc_path("factbook.xml")
    elements = partition_xml(file_path)
    chunk_elements = partition_xml(file_path, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_xml_element_metadata_has_languages():
    file_path = example_doc_path("factbook.xml")
    elements = partition_xml(file_path)
    assert elements[0].metadata.languages == ["eng"]


def test_partition_xml_respects_detect_language_per_element():
    elements = partition_xml(
        example_doc_path("language-docs/eng_spa_mult.xml"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]
