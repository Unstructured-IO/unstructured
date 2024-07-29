# pyright: reportPrivateUsage=false

from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import tempfile
import warnings
from importlib import import_module
from typing import Iterator, cast
from unittest.mock import patch

import pytest
from PIL import Image

from test_unstructured.partition.pdf_image.test_pdf import assert_element_extraction
from test_unstructured.partition.test_constants import (
    EXPECTED_TABLE,
    EXPECTED_TABLE_XLSX,
    EXPECTED_TEXT,
    EXPECTED_XLS_TABLE,
)
from test_unstructured.unit_utils import (
    ANY,
    FixtureRequest,
    LogCaptureFixture,
    example_doc_path,
    function_mock,
    method_mock,
)
from unstructured.cleaners.core import clean_extra_whitespace
from unstructured.documents.elements import (
    Address,
    CompositeElement,
    Element,
    ElementMetadata,
    ListItem,
    NarrativeText,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.file_utils.model import FileType
from unstructured.partition.auto import _PartitionerLoader, partition
from unstructured.partition.utils.constants import PartitionStrategy
from unstructured.staging.base import elements_from_json, elements_to_dicts, elements_to_json

is_in_docker = os.path.exists("/.dockerenv")


# ================================================================================================
# CSV
# ================================================================================================


def test_auto_partition_csv_from_filename():
    elements = partition(example_doc_path("stanley-cups.csv"))

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/csv"


def test_auto_partition_csv_from_file():
    with open(example_doc_path("stanley-cups.csv"), "rb") as f:
        elements = partition(file=f)

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert isinstance(elements[0], Table)
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/csv"


# ================================================================================================
# DOC
# ================================================================================================


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/msword"), (True, "application/msword"), (True, None)],
)
def test_auto_partition_doc_from_filename(
    pass_metadata_filename: bool, content_type: str | None, expected_docx_elements: list[Element]
):
    file_path = example_doc_path("simple.doc")
    metadata_filename = file_path if pass_metadata_filename else None

    elements = partition(
        filename=file_path,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy=PartitionStrategy.HI_RES,
    )

    for e in elements:
        print(f"{type(e).__name__}({repr(e.text)})")

    assert elements == expected_docx_elements
    assert all(e.metadata.filename == "simple.doc" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


@pytest.mark.skipif(is_in_docker, reason="Passes in CI but not Docker. Remove skip on #3364 fix.")
@pytest.mark.xfail(sys.platform == "darwin", reason="#3364", raises=KeyError, strict=True)
def test_auto_partition_doc_from_file(expected_docx_elements: list[Element]):
    # -- NOTE(scanny): https://github.com/Unstructured-IO/unstructured/issues/3364
    # -- detect_filetype() identifies .doc as `application/x-ole-storage` which is true but not
    # -- specific enough. The `FileType.MSG` file-type is assigned (which is also an OLE file)
    # -- and `partition()` routes the document to `partition_msg` which is where the `KeyError`
    # -- comes from.
    # -- For some reason, this xfail problem only occurs locally, not in CI, possibly because we
    # -- use two different `libmagic` sourcs (`libmagic` on CI and `libmagic1` on Mac). Doesn't
    # -- matter much though because when we add disambiguation they'll both get it right.
    with open(example_doc_path("simple.doc"), "rb") as f:
        elements = partition(file=f)

    assert elements == expected_docx_elements


# ================================================================================================
# DOCX
# ================================================================================================


def test_auto_partition_docx_from_filename(expected_docx_elements: list[Element]):
    elements = partition(example_doc_path("simple.docx"), strategy=PartitionStrategy.HI_RES)

    assert elements == expected_docx_elements
    assert all(e.metadata.filename == "simple.docx" for e in elements)


def test_auto_partition_docx_from_file(expected_docx_elements: list[Element]):
    with open(example_doc_path("simple.docx"), "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)
    assert elements == expected_docx_elements


@pytest.mark.parametrize("file_name", ["simple.docx", "simple.doc", "simple.odt"])
@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.AUTO,
        PartitionStrategy.FAST,
        PartitionStrategy.HI_RES,
        PartitionStrategy.OCR_ONLY,
    ],
)
def test_partition_forwards_strategy_arg_to_partition_docx_and_its_brokers(
    request: FixtureRequest, file_name: str, strategy: str
):
    """The `strategy` arg value received by `partition()` is received by `partition_docx().

    To do this in the brokering-partitioner cases (DOC, ODT) it must make its way to
    `partition_doc()` or `partition_odt()` which must then forward it to `partition_docx()`. This
    test makes sure it made it all the way.

    Note this is 3 file-types X 4 strategies = 12 test-cases.
    """
    from unstructured.partition.docx import _DocxPartitioner

    def fake_iter_document_elements(self: _DocxPartitioner) -> Iterator[Element]:
        yield Text(f"strategy=={self._opts.strategy}")

    _iter_elements_ = method_mock(
        request,
        _DocxPartitioner,
        "_iter_document_elements",
        side_effect=fake_iter_document_elements,
    )

    (element,) = partition(example_doc_path(file_name), strategy=strategy)

    _iter_elements_.assert_called_once_with(ANY)
    assert element.text == f"strategy=={strategy}"


# ================================================================================================
# EML
# ================================================================================================

EXPECTED_EMAIL_OUTPUT = [
    NarrativeText(text="This is a test email to use for unit tests."),
    Title(text="Important points:"),
    ListItem(text="Roses are red"),
    ListItem(text="Violets are blue"),
]


def test_auto_partition_email_from_filename():
    file_path = example_doc_path("eml/fake-email.eml")

    elements = partition(file_path, strategy=PartitionStrategy.HI_RES)

    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT
    assert elements[0].metadata.filename == os.path.basename(file_path)
    assert elements[0].metadata.file_directory == os.path.split(file_path)[0]


def test_auto_partition_email_from_file():
    with open(example_doc_path("eml/fake-email.eml"), "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)

    assert len(elements) > 0
    assert elements == EXPECTED_EMAIL_OUTPUT


def test_auto_partition_eml_add_signature_to_metadata():
    elements = partition(example_doc_path("eml/signed-doc.p7s"))

    assert len(elements) == 1
    assert elements[0].text == "This is a test"
    assert elements[0].metadata.signature == "<SIGNATURE>\n"


# ================================================================================================
# EPUB
# ================================================================================================


def test_auto_partition_epub_from_filename():
    elements = partition(example_doc_path("winter-sports.epub"), strategy=PartitionStrategy.HI_RES)

    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


def test_auto_partition_epub_from_file():
    with open(example_doc_path("winter-sports.epub"), "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)

    assert len(elements) > 0
    assert elements[0].text.startswith("The Project Gutenberg eBook of Winter Sports")


# ================================================================================================
# HTML
# ================================================================================================


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_filename(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("example-10k-1p.html")
    metadata_filename = file_path if pass_metadata_filename else None

    elements = partition(
        filename=file_path,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy=PartitionStrategy.HI_RES,
    )

    assert elements
    expected_filename, expected_directory = os.path.basename(file_path), os.path.split(file_path)[0]
    assert all(e.metadata.filename == expected_filename for e in elements)
    assert all(e.metadata.file_directory == expected_directory for e in elements)


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "text/html"), (True, "text/html"), (True, None)],
)
def test_auto_partition_html_from_file(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("example-10k-1p.html")
    metadata_filename = file_path if pass_metadata_filename else None

    with open(file_path, "rb") as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
            content_type=content_type,
            strategy=PartitionStrategy.HI_RES,
        )

    assert len(elements) > 0


def test_auto_partition_html_pre_from_file():
    elements = partition(example_doc_path("fake-html-pre.htm"))

    assert len(elements) > 0
    assert "PageBreak" not in [elem.category for elem in elements]
    assert clean_extra_whitespace(elements[0].text).startswith("[107th Congress Public Law 56]")
    assert isinstance(elements[0], NarrativeText)
    assert all(e.metadata.filetype == "text/html" for e in elements)
    assert all(e.metadata.filename == "fake-html-pre.htm" for e in elements)


# ================================================================================================
# IMAGE
# ================================================================================================


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpeg_from_filename(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("img/layout-parser-paper-fast.jpg")
    metadata_filename = file_path if pass_metadata_filename else None

    elements = partition(
        filename=file_path,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy=PartitionStrategy.AUTO,
    )

    e = elements[2]
    assert e.text == (
        "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    )
    assert e.metadata.coordinates is not None


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "image/jpeg"), (True, "image/jpeg"), (True, None)],
)
def test_auto_partition_jpeg_from_file(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("img/layout-parser-paper-fast.jpg")
    metadata_filename = file_path if pass_metadata_filename else None

    with open(file_path, "rb") as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
            content_type=content_type,
            strategy=PartitionStrategy.AUTO,
        )

    e = elements[2]
    assert e.text == (
        "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    )
    assert e.metadata.coordinates is not None


def test_auto_partition_bmp_from_filename(tmp_path: pathlib.Path):
    bmp_filename = str(tmp_path / "example.bmp")
    with Image.open(example_doc_path("img/layout-parser-paper-with-table.jpg")) as img:
        img.save(bmp_filename)

    elements = partition(filename=bmp_filename, strategy=PartitionStrategy.HI_RES)

    table = [e.metadata.text_as_html for e in elements if e.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]


@pytest.mark.parametrize("extract_image_block_to_payload", [False, True])
def test_auto_partition_image_element_extraction(extract_image_block_to_payload: bool):
    extract_image_block_types = ["Image", "Table"]

    with tempfile.TemporaryDirectory() as tmpdir:
        elements = partition(
            filename=example_doc_path("img/embedded-images-tables.jpg"),
            extract_image_block_types=extract_image_block_types,
            extract_image_block_to_payload=extract_image_block_to_payload,
            extract_image_block_output_dir=tmpdir,
        )

        assert_element_extraction(
            elements, extract_image_block_types, extract_image_block_to_payload, tmpdir
        )


# ================================================================================================
# JSON
# ================================================================================================


# TODO(scanny): This test should go away when we fix #3365. This test glosses over several
# important JSON "rehydration" behaviors, in particular that the metadata should match exactly.
# The following test `test_auto_partition_json_from_file_preserves_original_elements` will be the
# replacement for this test.
def test_auto_partitioned_json_output_maintains_consistency_with_fixture_elements():
    """Test auto-processing an unstructured json output file by filename."""
    json_file_path = example_doc_path("spring-weather.html.json")
    original_file_name = "spring-weather.html"
    with open(json_file_path) as json_f:
        expected_result = json.load(json_f)

    partitioning_result = json.loads(
        cast(
            str,
            elements_to_json(
                partition(
                    filename=str(json_file_path),
                    # -- use the original file name to get the same element IDs (hashes) --
                    metadata_filename=original_file_name,
                    strategy=PartitionStrategy.HI_RES,
                )
            ),
        )
    )
    for elem in partitioning_result:
        elem.pop("metadata")
    for elem in expected_result:
        elem.pop("metadata")

    assert expected_result == partitioning_result


@pytest.mark.xfail(
    reason=(
        "https://github.com/Unstructured-IO/unstructured/issues/3365"
        " partition_json() does not preserve original element-id or metadata"
    ),
    raises=AssertionError,
    strict=True,
)
def test_auto_partition_json_from_file_preserves_original_elements():
    file_path = example_doc_path("simple.json")
    original_elements = elements_from_json(file_path)

    with open(file_path, "rb") as f:
        partitioned_elements = partition(file=f)

    assert elements_to_dicts(partitioned_elements) == elements_to_dicts(original_elements)


def test_auto_partition_json_raises_with_unprocessable_json(tmp_path: pathlib.Path):
    # NOTE(robinson) - This is unprocessable because it is not a list of dicts, per the
    # Unstructured JSON serialization format
    text = '{"hi": "there"}'

    file_path = str(tmp_path / "unprocessable.json")
    with open(file_path, "w") as f:
        f.write(text)

    with pytest.raises(ValueError, match="Detected a JSON file that does not conform to the Unst"):
        partition(filename=file_path)


# ================================================================================================
# MD
# ================================================================================================


def test_partition_md_from_url_works_with_embedded_html():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/README.md"
    elements = partition(url=url, content_type="text/markdown", strategy=PartitionStrategy.HI_RES)
    assert "unstructured" in elements[0].text


# ================================================================================================
# MSG
# ================================================================================================


def test_auto_partition_msg_from_filename():
    assert partition(example_doc_path("fake-email.msg"), strategy=PartitionStrategy.HI_RES) == [
        NarrativeText(text="This is a test email to use for unit tests."),
        Title(text="Important points:"),
        ListItem(text="Roses are red"),
        ListItem(text="Violets are blue"),
    ]


# ================================================================================================
# ODT
# ================================================================================================


def test_auto_partition_odt_from_filename(expected_docx_elements: list[Element]):
    elements = partition(example_doc_path("simple.odt"), strategy=PartitionStrategy.HI_RES)
    assert elements == expected_docx_elements


def test_auto_partition_odt_from_file(expected_docx_elements: list[Element]):
    with open(example_doc_path("simple.odt"), "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)

    assert elements == expected_docx_elements


# ================================================================================================
# ORG
# ================================================================================================


def test_auto_partition_org_from_filename():
    elements = partition(example_doc_path("README.org"))

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


def test_auto_partition_org_from_file():
    with open(example_doc_path("README.org"), "rb") as f:
        elements = partition(file=f, content_type="text/org")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/org"


# ================================================================================================
# PDF
# ================================================================================================


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_filename(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("pdf/layout-parser-paper-fast.pdf")
    metadata_filename = file_path if pass_metadata_filename else None

    elements = partition(
        filename=file_path,
        metadata_filename=metadata_filename,
        content_type=content_type,
        strategy=PartitionStrategy.HI_RES,
    )

    # NOTE(scanny): gave up trying to figure out why, but this file partitions differently locally
    # (on Mac) than it does in CI. Basically the first element when partitioning locally is split
    # in two when partitioning on CI. Other than that split the text is exactly the same.
    idx = 2 if sys.platform == "darwin" else 3

    e = elements[idx]
    assert isinstance(e, Title)
    assert e.text.startswith("LayoutParser")
    assert e.metadata.filename == os.path.basename(file_path)
    assert e.metadata.file_directory == os.path.split(file_path)[0]

    e = elements[idx + 1]
    assert isinstance(e, NarrativeText)
    assert e.text.startswith("Zejiang Shen")


@pytest.mark.parametrize(
    ("pass_metadata_filename", "content_type"),
    [(False, None), (False, "application/pdf"), (True, "application/pdf"), (True, None)],
)
def test_auto_partition_pdf_from_file(pass_metadata_filename: bool, content_type: str | None):
    file_path = example_doc_path("pdf/layout-parser-paper-fast.pdf")
    metadata_filename = file_path if pass_metadata_filename else None

    with open(file_path, "rb") as f:
        elements = partition(
            file=f,
            metadata_filename=metadata_filename,
            content_type=content_type,
            strategy=PartitionStrategy.HI_RES,
        )

    # NOTE(scanny): see "from_filename" version of this test above for more on this oddness
    idx = 2 if sys.platform == "darwin" else 3

    e = elements[idx]
    assert isinstance(e, Title)
    assert e.text.startswith("LayoutParser")

    e = elements[idx + 1]
    assert isinstance(e, NarrativeText)
    assert e.text.startswith("Zejiang Shen")


def test_auto_partition_pdf_with_fast_strategy(request: FixtureRequest):
    partition_pdf_ = function_mock(
        request,
        "unstructured.partition.pdf.partition_pdf",
        return_value=[NarrativeText("Hello there!")],
    )
    partitioner_loader_get_ = method_mock(
        request, _PartitionerLoader, "get", return_value=partition_pdf_
    )
    file_path = example_doc_path("pdf/layout-parser-paper-fast.pdf")

    partition(file_path, strategy=PartitionStrategy.FAST)

    partitioner_loader_get_.assert_called_once_with(ANY, FileType.PDF)
    partition_pdf_.assert_called_once_with(
        filename=file_path,
        file=None,
        url=None,
        strategy=PartitionStrategy.FAST,
        languages=None,
        metadata_filename=None,
        include_page_breaks=False,
        infer_table_structure=False,
        extract_images_in_pdf=False,
        extract_image_block_types=None,
        extract_image_block_output_dir=None,
        extract_image_block_to_payload=False,
        hi_res_model_name=None,
        date_from_file_object=False,
        starting_page_number=1,
    )


def test_auto_partition_pdf_uses_pdf_infer_table_structure_argument():
    with patch(
        "unstructured.partition.pdf_image.ocr.process_file_with_ocr",
    ) as mock_process_file_with_model:
        partition(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"),
            pdf_infer_table_structure=True,
            strategy=PartitionStrategy.HI_RES,
        )
        assert mock_process_file_with_model.call_args[1]["infer_table_structure"]


@pytest.mark.parametrize("extract_image_block_to_payload", [False, True])
def test_auto_partition_pdf_element_extraction(extract_image_block_to_payload: bool):
    extract_image_block_types = ["Image", "Table"]

    with tempfile.TemporaryDirectory() as tmpdir:
        elements = partition(
            example_doc_path("pdf/embedded-images-tables.pdf"),
            extract_image_block_types=extract_image_block_types,
            extract_image_block_to_payload=extract_image_block_to_payload,
            extract_image_block_output_dir=tmpdir,
        )

        assert_element_extraction(
            elements, extract_image_block_types, extract_image_block_to_payload, tmpdir
        )


def test_partition_pdf_does_not_raise_warning():
    # NOTE(robinson): This is the recommended way to check that no warning is emitted,
    # per the pytest docs.
    # ref: https://docs.pytest.org/en/7.0.x/how-to/capture-warnings.html
    #      #additional-use-cases-of-warnings-in-tests
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        partition(
            example_doc_path("pdf/layout-parser-paper-fast.pdf"), strategy=PartitionStrategy.HI_RES
        )


# ================================================================================================
# PPT
# ================================================================================================


def test_auto_partition_ppt_from_filename():
    file_path = example_doc_path("fake-power-point.ppt")

    elements = partition(file_path, strategy=PartitionStrategy.HI_RES)

    assert elements == [
        Title(text="Adding a Bullet Slide"),
        ListItem(text="Find the bullet slide layout"),
        ListItem(text="Use _TextFrame.text for first bullet"),
        ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
        NarrativeText(text="Here is a lot of text!"),
        NarrativeText(text="Here is some text in a text box!"),
    ]
    assert all(e.metadata.filename == "fake-power-point.ppt" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


# ================================================================================================
# PPTX
# ================================================================================================


def test_auto_partition_pptx_from_filename():
    file_path = example_doc_path("fake-power-point.pptx")

    elements = partition(file_path, strategy=PartitionStrategy.HI_RES)

    assert elements == [
        Title(text="Adding a Bullet Slide"),
        ListItem(text="Find the bullet slide layout"),
        ListItem(text="Use _TextFrame.text for first bullet"),
        ListItem(text="Use _TextFrame.add_paragraph() for subsequent bullets"),
        NarrativeText(text="Here is a lot of text!"),
        NarrativeText(text="Here is some text in a text box!"),
    ]
    assert all(e.metadata.filename == "fake-power-point.pptx" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


@pytest.mark.parametrize("file_name", ["simple.pptx", "fake-power-point.ppt"])
@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.AUTO,
        PartitionStrategy.FAST,
        PartitionStrategy.HI_RES,
        PartitionStrategy.OCR_ONLY,
    ],
)
def test_partition_forwards_strategy_arg_to_partition_pptx_and_its_brokers(
    request: FixtureRequest, file_name: str, strategy: str
):
    """The `strategy` arg value received by `partition()` is received by `partition_pptx().

    To do this in the brokering-partitioner case (PPT) the strategy argument must make its way to
    `partition_ppt()` which must then forward it to `partition_pptx()`. This test makes sure it
    made it all the way.

    Note this is 2 file-types X 4 strategies = 8 test-cases.
    """
    from unstructured.partition.pptx import _PptxPartitioner

    def fake_iter_presentation_elements(self: _PptxPartitioner) -> Iterator[Element]:
        yield Text(f"strategy=={self._opts.strategy}")

    _iter_elements_ = method_mock(
        request,
        _PptxPartitioner,
        "_iter_presentation_elements",
        side_effect=fake_iter_presentation_elements,
    )

    (element,) = partition(example_doc_path(file_name), strategy=strategy)

    _iter_elements_.assert_called_once_with(ANY)
    assert element.text == f"strategy=={strategy}"


# ================================================================================================
# RST
# ================================================================================================


def test_auto_partition_rst_from_filename():
    elements = partition(example_doc_path("README.rst"))

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


def test_auto_partition_rst_from_file():
    with open(example_doc_path("README.rst"), "rb") as f:
        elements = partition(file=f, content_type="text/x-rst")

    assert elements[0] == Title("Example Docs")
    assert elements[0].metadata.filetype == "text/x-rst"


# ================================================================================================
# RTF
# ================================================================================================


def test_auto_partition_rtf_from_filename():
    elements = partition(example_doc_path("fake-doc.rtf"), strategy=PartitionStrategy.HI_RES)
    assert elements[0] == Title("My First Heading")


# ================================================================================================
# TSV
# ================================================================================================


def test_auto_partition_tsv_from_filename():
    elements = partition(example_doc_path("stanley-cups.tsv"))

    assert clean_extra_whitespace(elements[0].text) == EXPECTED_TEXT
    assert elements[0].metadata.text_as_html == EXPECTED_TABLE
    assert elements[0].metadata.filetype == "text/tsv"


# ================================================================================================
# TXT
# ================================================================================================


def test_auto_partition_text_from_filename():
    file_path = example_doc_path("fake-text.txt")

    elements = partition(filename=file_path, strategy=PartitionStrategy.HI_RES)

    assert elements == [
        NarrativeText(text="This is a test document to use for unit tests."),
        Address(text="Doylestown, PA 18901"),
        Title(text="Important points:"),
        ListItem(text="Hamburgers are delicious"),
        ListItem(text="Dogs are the best"),
        ListItem(text="I love fuzzy blankets"),
    ]
    assert all(e.metadata.filename == "fake-text.txt" for e in elements)
    assert all(e.metadata.file_directory == example_doc_path("") for e in elements)


def test_auto_partition_text_from_file():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition(file=f, strategy=PartitionStrategy.HI_RES)

    assert len(elements) > 0
    assert elements == [
        NarrativeText(text="This is a test document to use for unit tests."),
        Address(text="Doylestown, PA 18901"),
        Title(text="Important points:"),
        ListItem(text="Hamburgers are delicious"),
        ListItem(text="Dogs are the best"),
        ListItem(text="I love fuzzy blankets"),
    ]


# ================================================================================================
# XLS
# ================================================================================================


def test_auto_partition_xls_from_filename():
    elements = partition(
        example_doc_path("tests-example.xls"), include_header=False, skip_infer_table_types=[]
    )

    assert sum(isinstance(element, Table) for element in elements) == 2
    assert len(elements) == 14

    assert clean_extra_whitespace(elements[0].text)[:45] == (
        "MC What is 2+2? 4 correct 3 incorrect MA What"
    )
    # NOTE(crag): if the beautifulsoup4 package is installed, some (but not all) additional
    # whitespace is removed, so the expected text length is less than is the case when
    # beautifulsoup4 is *not* installed. E.g.
    #      "\n\n\nMA\nWhat C datatypes are 8 bits"
    #  vs. '\n  \n    \n      MA\n      What C datatypes are 8 bits?... "
    assert len(elements[0].text) == 550
    assert elements[0].metadata.text_as_html == EXPECTED_XLS_TABLE


# ================================================================================================
# XLSX
# ================================================================================================


def test_auto_partition_xlsx_from_filename():
    elements = partition(
        example_doc_path("stanley-cups.xlsx"), include_header=False, skip_infer_table_types=[]
    )

    assert len(elements) == 4
    assert sum(isinstance(e, Table) for e in elements) == 2
    assert sum(isinstance(e, Title) for e in elements) == 2
    assert clean_extra_whitespace(elements[0].text) == "Stanley Cups"
    assert clean_extra_whitespace(elements[1].text) == (
        "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
    )
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert all(e.metadata.page_number == 1 for e in elements[:2])
    assert all(e.metadata.page_number == 2 for e in elements[2:])
    assert all(
        e.metadata.filetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        for e in elements
    )


def test_auto_partition_xlsx_from_file():
    with open(example_doc_path("stanley-cups.xlsx"), "rb") as f:
        elements = partition(file=f, include_header=False, skip_infer_table_types=[])

    assert len(elements) == 4
    assert sum(isinstance(element, Table) for element in elements) == 2
    assert sum(isinstance(element, Title) for element in elements) == 2
    assert clean_extra_whitespace(elements[0].text) == "Stanley Cups"
    assert clean_extra_whitespace(elements[1].text) == (
        "Team Location Stanley Cups Blues STL 1 Flyers PHI 2 Maple Leafs TOR 13"
    )
    assert elements[1].metadata.text_as_html == EXPECTED_TABLE_XLSX
    assert all(e.metadata.page_number == 1 for e in elements[:2])
    assert all(e.metadata.page_number == 2 for e in elements[2:])
    assert all(
        e.metadata.filetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        for e in elements
    )


def test_auto_partition_xlsx_respects_starting_page_number_argument():
    elements = partition(example_doc_path("stanley-cups.xlsx"), starting_page_number=3)
    assert all(e.metadata.page_number == 3 for e in elements[:2])
    assert all(e.metadata.page_number == 4 for e in elements[2:])


# ================================================================================================
# XML
# ================================================================================================


def test_auto_partition_xml_from_filename():
    elements = partition(example_doc_path("factbook.xml"), xml_keep_tags=False)

    assert elements[0].text == "United States"
    assert all(e.metadata.filename == "factbook.xml" for e in elements)


def test_auto_partition_xml_from_file():
    with open(example_doc_path("factbook.xml"), "rb") as f:
        elements = partition(file=f, xml_keep_tags=False)

    assert elements[0].text == "United States"


def test_auto_partition_xml_from_filename_with_tags():
    elements = partition(example_doc_path("factbook.xml"), xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text
    assert elements[0].metadata.filename == "factbook.xml"


def test_auto_partition_xml_from_file_with_tags():
    with open(example_doc_path("factbook.xml"), "rb") as f:
        elements = partition(file=f, xml_keep_tags=True)

    assert "<leader>Joe Biden</leader>" in elements[0].text


# ================================================================================================
# FILE_TYPE NOT RECOGNIZED OR NOT SUPPORTED
# ================================================================================================


def test_auto_partition_raises_with_bad_type(request: FixtureRequest):
    detect_filetype_ = function_mock(
        request, "unstructured.partition.auto.detect_filetype", return_value=FileType.UNK
    )

    with pytest.raises(ValueError, match="Invalid file made-up.fake. The FileType.UNK file type "):
        partition(filename="made-up.fake", strategy=PartitionStrategy.HI_RES)

    detect_filetype_.assert_called_once_with(
        file_path="made-up.fake",
        file=None,
        encoding=None,
        content_type=None,
        metadata_file_path=None,
    )


# ================================================================================================
# LOAD FROM URL
# ================================================================================================


def test_auto_partition_from_url():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"

    elements = partition(url=url, content_type="text/plain", strategy=PartitionStrategy.HI_RES)

    assert elements[0] == Title("Apache License")
    assert all(e.metadata.url == url for e in elements)


def test_auto_partition_from_url_with_rfc9110_content_type():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"

    elements = partition(
        url=url, content_type="text/plain; charset=utf-8", strategy=PartitionStrategy.HI_RES
    )

    assert elements[0] == Title("Apache License")
    assert all(e.metadata.url == url for e in elements)


def test_auto_partition_from_url_without_providing_content_type():
    url = "https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/LICENSE.md"

    elements = partition(url=url, strategy=PartitionStrategy.HI_RES)

    assert elements[0] == Title("Apache License")
    assert all(e.metadata.url == url for e in elements)


def test_auto_partition_warns_if_header_set_and_not_url(caplog: LogCaptureFixture):
    partition(
        example_doc_path("eml/fake-email.eml"),
        headers={"Accept": "application/pdf"},
        strategy=PartitionStrategy.HI_RES,
    )

    assert caplog.records[0].levelname == "WARNING"
    assert "headers kwarg is set but the url kwarg is not. The headers kwarg will b" in caplog.text


def test_auto_partition_from_url_routes_timeout_to_HTTP_request(request: FixtureRequest):
    file_and_type_from_url_ = function_mock(
        request,
        "unstructured.partition.auto.file_and_type_from_url",
        side_effect=ConnectionError("Trouble on the wire ..."),
    )

    with pytest.raises(ConnectionError, match="Trouble on the wire ..."):
        partition(url="http://eie.io", request_timeout=326)

    file_and_type_from_url_.assert_called_once_with(
        url="http://eie.io", content_type=None, headers={}, ssl_verify=True, request_timeout=326
    )


# ================================================================================================
# OTHER ARGS
# ================================================================================================

# -- chunking_strategy ----------------------------------------------------


def test_auto_partition_forwards_chunking_strategy_via_kwargs():
    chunks = partition(example_doc_path("example-10k-1p.html"), chunking_strategy="by_title")
    assert all(isinstance(chunk, (CompositeElement, Table, TableChunk)) for chunk in chunks)


def test_auto_partition_forwards_max_characters_via_kwargs():
    chunks = partition(
        example_doc_path("example-10k-1p.html"),
        chunking_strategy="by_title",
        max_characters=250,
    )
    assert all(len(chunk.text) <= 250 for chunk in chunks)


# -- detect_language_per_element ------------------------------------------


def test_auto_partition_respects_detect_language_per_element_arg():
    elements = partition(
        example_doc_path("language-docs/eng_spa_mult.txt"), detect_language_per_element=True
    )
    langs = [element.metadata.languages for element in elements]
    assert langs == [["eng"], ["spa", "eng"], ["eng"], ["eng"], ["spa"]]


# -- languages ------------------------------------------------------------


@pytest.mark.parametrize(
    "file_extension", "doc docx eml epub html md odt org ppt pptx rst rtf txt xml".split()
)
def test_auto_partition_respects_language_arg(file_extension: str):
    elements = partition(
        example_doc_path(f"language-docs/eng_spa_mult.{file_extension}"), languages=["deu"]
    )
    assert all(element.metadata.languages == ["deu"] for element in elements)


# -- include_page_breaks --------------------------------------------------


def test_auto_partition_forwards_include_page_breaks_to_partition_pdf():
    elements = partition(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"),
        include_page_breaks=True,
        strategy=PartitionStrategy.HI_RES,
    )
    assert "PageBreak" in [elem.category for elem in elements]


# -- metadata_filename ----------------------------------------------------


def test_auto_partition_forwards_metadata_filename_via_kwargs():
    with open(example_doc_path("fake-text.txt"), "rb") as f:
        elements = partition(file=f, metadata_filename="much-more-interesting-name.txt")

    assert all(e.metadata.filename == "much-more-interesting-name.txt" for e in elements)


def test_auto_partition_warns_about_file_filename_deprecation(caplog: LogCaptureFixture):
    file_path = example_doc_path("fake-text.txt")

    with open(file_path, "rb") as f:
        elements = partition(file=f, file_filename=file_path)

    assert all(e.metadata.filename == "fake-text.txt" for e in elements)
    assert caplog.records[0].levelname == "WARNING"
    assert "The file_filename kwarg will be deprecated" in caplog.text


def test_auto_partition_raises_when_both_file_filename_and_metadata_filename_args_are_used():
    file_path = example_doc_path("fake-text.txt")
    with open(file_path, "rb") as f:
        file = io.BytesIO(f.read())

    with pytest.raises(ValueError, match="Only one of metadata_filename and file_filename is spe"):
        partition(file=file, file_filename=file_path, metadata_filename=file_path)


# -- ocr_languages --------------------------------------------------------


def test_auto_partition_image_formats_languages_for_tesseract(request: FixtureRequest):
    process_file_with_ocr_ = function_mock(
        request, "unstructured.partition.pdf_image.ocr.process_file_with_ocr"
    )

    partition(
        example_doc_path("img/chi_sim_image.jpeg"),
        strategy=PartitionStrategy.HI_RES,
        languages=["zh"],
    )

    call_kwargs = process_file_with_ocr_.call_args_list[0][1]
    assert call_kwargs["ocr_languages"] == "chi_sim+chi_sim_vert+chi_tra+chi_tra_vert"


@pytest.mark.parametrize(("languages", "ocr_languages"), [(["auto"], ""), (["eng"], "")])
def test_auto_partition_ignores_empty_string_for_ocr_languages(
    languages: list[str], ocr_languages: str
):
    elements = partition(
        example_doc_path("book-war-and-peace-1p.txt"),
        strategy=PartitionStrategy.OCR_ONLY,
        ocr_languages=ocr_languages,
        languages=languages,
    )
    assert all(e.metadata.languages == ["eng"] for e in elements)


def test_auto_partition_warns_with_ocr_languages(caplog: LogCaptureFixture):
    partition(
        example_doc_path("pdf/chevron-page.pdf"),
        strategy=PartitionStrategy.HI_RES,
        ocr_languages="eng",
    )

    assert caplog.records[0].levelname == "WARNING"
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


# -- skip_infer_table_types -----------------------------------------------


@pytest.mark.parametrize(
    ("skip_infer_table_types", "filename", "has_text_as_html"),
    [
        (["xlsx"], "stanley-cups.xlsx", False),
        ([], "stanley-cups.xlsx", True),
        (["odt"], "fake.odt", False),
        ([], "fake.odt", True),
    ],
)
def test_auto_partition_respects_skip_infer_table_types(
    skip_infer_table_types: list[str], filename: str, has_text_as_html: bool
):
    with open(example_doc_path(filename), "rb") as f:
        elements = partition(file=f, skip_infer_table_types=skip_infer_table_types)

    table_elements = [e for e in elements if isinstance(e, Table)]
    assert table_elements
    for e in table_elements:
        assert (e.metadata.text_as_html is not None) == has_text_as_html


# ================================================================================================
# METADATA BEHAVIORS
# ================================================================================================

# -- .filetype ------------------------------------------------------------


@pytest.mark.parametrize(
    ("content_type", "shortname", "expected_value"),
    [
        ("text/csv", "csv", "text/csv"),
        ("text/html", "html", "text/html"),
        ("jdsfjdfsjkds", "pdf", None),
    ],
)
def test_auto_partition_adds_filetype_to_metadata(
    request: FixtureRequest,
    content_type: str,
    shortname: str,
    expected_value: str | None,
):
    partition_fn_ = function_mock(
        request,
        f"unstructured.partition.{shortname}.partition_{shortname}",
        return_value=[Text("text 1"), Text("text 2")],
    )
    partitioner_loader_get_ = method_mock(
        request, _PartitionerLoader, "get", return_value=partition_fn_
    )

    elements = partition(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"), content_type=content_type
    )

    partitioner_loader_get_.assert_called_once()
    assert len(elements) == 2
    assert all(e.metadata.filetype == expected_value for e in elements)


@pytest.mark.parametrize(
    "content_type",
    [
        # -- content-type provided as argument --
        "application/pdf",
        # -- auto-detected content-type --
        None,
    ],
)
def test_auto_partition_overwrites_any_filetype_applied_by_file_specific_partitioner(
    request: FixtureRequest, content_type: str | None
):
    metadata = ElementMetadata(filetype="imapdf")
    partition_pdf_ = function_mock(
        request,
        "unstructured.partition.pdf.partition_pdf",
        return_value=[Text("text 1", metadata=metadata), Text("text 2", metadata=metadata)],
    )
    partitioner_loader_get_ = method_mock(
        request, _PartitionerLoader, "get", return_value=partition_pdf_
    )

    elements = partition(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"), content_type=content_type
    )

    partitioner_loader_get_.assert_called_once_with(ANY, FileType.PDF)
    assert len(elements) == 2
    assert all(e.metadata.filetype == "application/pdf" for e in elements)


@pytest.mark.parametrize(
    "file_type",
    [
        t
        for t in FileType
        if t
        not in (
            FileType.EMPTY,
            FileType.JSON,
            FileType.UNK,
            FileType.WAV,
            FileType.XLS,
            FileType.ZIP,
        )
        and t.partitioner_shortname != "image"
    ],
)
def test_auto_partition_applies_the_correct_filetype_for_all_filetypes(file_type: FileType):
    partition_fn_name = file_type.partitioner_function_name
    module = import_module(file_type.partitioner_module_qname)
    partition_fn = getattr(module, partition_fn_name)

    # -- partition the first example-doc with the extension for this filetype --
    elements: list[Element] = []
    doc_path = example_doc_path("pdf") if file_type == FileType.PDF else example_doc_path("")
    extensions = file_type._extensions
    for file in pathlib.Path(doc_path).iterdir():
        if file.is_file() and file.suffix in extensions:
            elements = partition_fn(str(file))
            break

    assert elements
    assert all(
        e.metadata.filetype == file_type.mime_type
        for e in elements
        if e.metadata.filetype is not None
    )


# -- .languages -----------------------------------------------------------


def test_auto_partition_passes_user_provided_languages_arg_to_PDF():
    elements = partition(
        example_doc_path("pdf/chevron-page.pdf"),
        strategy=PartitionStrategy.OCR_ONLY,
        languages=["eng"],
    )
    assert all(e.metadata.languages == ["eng"] for e in elements)


def test_auto_partition_languages_argument_default_to_None_when_omitted():
    elements = partition(example_doc_path("handbook-1p.docx"), detect_language_per_element=True)
    # -- PageBreak and any other element with no text is assigned `None` --
    assert all(e.text == "" for e in elements if e.metadata.languages is None)


def test_auto_partition_default_does_not_overwrite_other_defaults():
    """`partition()` ["eng"] default does not overwrite ["auto"] default in other partitioners."""
    # the default for `languages` is ["auto"] in partiton_text
    from unstructured.partition.text import partition_text

    # Use a document that is primarily in a language other than English
    file_path = example_doc_path("language-docs/UDHR_first_article_all.txt")
    text_elements = partition_text(file_path)
    assert text_elements[0].metadata.languages != ["eng"]

    auto_elements = partition(file_path)
    assert auto_elements[0].metadata.languages != ["eng"]
    assert auto_elements[0].metadata.languages == text_elements[0].metadata.languages


# ================================================================================================
# MISCELLANEOUS BEHAVIORS
# ================================================================================================


def test_auto_partition_from_filename_works_on_empty_file():
    assert partition(example_doc_path("empty.txt")) == []


def test_auto_partition_from_file_works_on_empty_file():
    with open(example_doc_path("empty.txt"), "rb") as f:
        assert partition(file=f) == []


def test_auto_partition_that_requires_extras_raises_when_dependencies_are_not_installed(
    request: FixtureRequest,
):
    _PartitionerLoader._partitioners.pop(FileType.PDF, None)
    dependency_exists_ = function_mock(
        request, "unstructured.partition.auto.dependency_exists", return_value=False
    )
    match = r"partition_pdf\(\) is not available because one or more dependencies are not installed"
    with pytest.raises(ImportError, match=match):
        partition(example_doc_path("pdf/layout-parser-paper-fast.pdf"))

    dependency_exists_.assert_called_once_with("pdf2image")


# ================================================================================================
# MODULE-LEVEL FIXTURES
# ================================================================================================


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
        Address("DOYLESTOWN, PA 18901"),
    ]
