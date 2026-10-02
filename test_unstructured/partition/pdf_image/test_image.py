from __future__ import annotations

import io
import os
import pathlib
import struct
import tempfile
import time
import zlib
from typing import Any, Callable
from unittest import mock

import pytest
from pi_heif import register_heif_opener
from PIL import Image, ImageFile, TiffImagePlugin
from pytest_mock import MockFixture
from unstructured_inference.inference import layout
from unstructured_pytesseract import TesseractError

from test_unstructured.partition.pdf_image.test_pdf import assert_element_extraction
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementType
from unstructured.errors import UnprocessableEntityError
from unstructured.partition import image, pdf
from unstructured.partition.pdf_image import ocr
from unstructured.partition.utils.constants import (
    UNSTRUCTURED_INCLUDE_DEBUG_METADATA,
    PartitionStrategy,
)
from unstructured.utils import only

DIRECTORY = pathlib.Path(__file__).parent.resolve()


class MockResponse:
    def __init__(self, status_code, response):
        self.status_code = status_code
        self.response = response

    def json(self):
        return self.response


def mock_healthy_get(url, **kwargs):
    return MockResponse(status_code=200, response={})


def mock_unhealthy_get(url, **kwargs):
    return MockResponse(status_code=500, response={})


def mock_unsuccessful_post(url, **kwargs):
    return MockResponse(status_code=500, response={})


def mock_successful_post(url, **kwargs):
    response = {
        "pages": [
            {
                "number": 0,
                "elements": [
                    {"type": "Title", "text": "Charlie Brown and the Great Pumpkin"},
                ],
            },
            {
                "number": 1,
                "elements": [{"type": "Title", "text": "A Charlie Brown Christmas"}],
            },
        ],
    }
    return MockResponse(status_code=200, response=response)


class MockPageLayout(layout.PageLayout):
    def __init__(self, number: int, image: Image):
        self.number = number
        self.image = image
        self.image_metadata = {"pdf_rotation": 0}
        self.elements = [
            layout.LayoutElement.from_coords(
                type="Title",
                x1=0,
                y1=0,
                x2=2,
                y2=2,
                text="Charlie Brown and the Great Pumpkin",
            ),
        ]
        self.elements_array = layout.LayoutElements.from_list(self.elements)


class MockDocumentLayout(layout.DocumentLayout):
    @property
    def pages(self):
        return [
            MockPageLayout(number=0, image=Image.new("1", (1, 1))),
        ]


@pytest.mark.parametrize(
    ("filename", "file"),
    [
        (example_doc_path("img/example.jpg"), None),
        (None, b"0000"),
    ],
)
def test_partition_image_local(monkeypatch, filename, file):
    monkeypatch.setattr(
        layout,
        "process_data_with_model",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        layout,
        "process_file_with_model",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        ocr,
        "process_data_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )
    monkeypatch.setattr(
        ocr,
        "process_data_with_ocr",
        lambda *args, **kwargs: MockDocumentLayout(),
    )

    partition_image_response = pdf._partition_pdf_or_image_local(
        filename,
        file,
        is_image=True,
    )
    assert partition_image_response[0].text == "Charlie Brown and the Great Pumpkin"


@pytest.mark.skip("Needs to be fixed upstream in unstructured-inference")
def test_partition_image_local_raises_with_no_filename():
    with pytest.raises(FileNotFoundError):
        pdf._partition_pdf_or_image_local(filename="", file=None, is_image=True)


def test_partition_image_with_auto_strategy():
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.AUTO)
    titles = [
        el for el in elements if el.category == ElementType.TITLE and len(el.text.split(" ")) > 10
    ]
    title = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    idx = 3
    assert titles[0].text == title
    assert elements[idx].metadata.detection_class_prob is not None
    assert isinstance(elements[idx].metadata.detection_class_prob, float)


def test_partition_image_with_table_extraction():
    filename = example_doc_path("img/layout-parser-paper-with-table.jpg")
    elements = image.partition_image(
        filename=filename,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]


def test_partition_image_with_multipage_tiff():
    filename = example_doc_path("img/layout-parser-paper-combined.tiff")
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.AUTO)
    assert elements[-1].metadata.page_number == 2


def test_partition_image_with_bmp(tmpdir):
    filename = example_doc_path("img/layout-parser-paper-with-table.jpg")
    bmp_filename = os.path.join(tmpdir.dirname, "example.bmp")
    img = Image.open(filename)
    img.save(bmp_filename)

    elements = image.partition_image(
        filename=bmp_filename,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]


def test_partition_image_with_language_passed():
    filename = example_doc_path("img/example.jpg")
    with mock.patch.object(
        ocr,
        "process_file_with_ocr",
        mock.MagicMock(),
    ) as mock_partition:
        image.partition_image(
            filename=filename,
            strategy=PartitionStrategy.HI_RES,
            ocr_languages="eng+swe",
        )

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


def test_partition_image_from_file_with_language_passed():
    filename = example_doc_path("img/example.jpg")
    with (
        mock.patch.object(
            ocr,
            "process_data_with_ocr",
            mock.MagicMock(),
        ) as mock_partition,
        open(filename, "rb") as f,
    ):
        image.partition_image(file=f, strategy=PartitionStrategy.HI_RES, ocr_languages="eng+swe")

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


# NOTE(crag): see https://github.com/Unstructured-IO/unstructured/issues/1086
@pytest.mark.skip(reason="Current catching too many tesseract errors")
def test_partition_image_raises_with_invalid_language():
    filename = example_doc_path("img/example.jpg")
    with pytest.raises(TesseractError):
        image.partition_image(
            filename=filename,
            strategy=PartitionStrategy.HI_RES,
            ocr_languages="fakeroo",
        )


@pytest.mark.parametrize(
    "strategy",
    [
        PartitionStrategy.HI_RES,
        PartitionStrategy.OCR_ONLY,
    ],
)
def test_partition_image_strategies_keep_languages_metadata(strategy):
    filename = example_doc_path("img/english-and-korean.png")
    elements = image.partition_image(
        filename=filename,
        languages=["eng", "kor"],
        strategy=strategy,
    )

    assert elements[0].metadata.languages == ["eng", "kor"]


def test_partition_image_with_ocr_detects_korean():
    filename = example_doc_path("img/english-and-korean.png")
    elements = image.partition_image(
        filename=filename,
        ocr_languages="eng+kor",
        strategy=PartitionStrategy.OCR_ONLY,
    )

    assert elements[0].text == "RULES AND INSTRUCTIONS"
    # FIXME (yao): revisit this lstrip after refactoring merging logics; right now on docker and
    # local testing yield different results and on docker there is a "," at the start of the Korean
    # text line
    assert elements[3].text.replace(" ", "").lstrip(",").startswith("안녕하세요")


def test_partition_image_with_ocr_detects_korean_from_file():
    filename = example_doc_path("img/english-and-korean.png")
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            ocr_languages="eng+kor",
            strategy=PartitionStrategy.OCR_ONLY,
        )

    assert elements[0].text == "RULES AND INSTRUCTIONS"
    assert elements[3].text.replace(" ", "").lstrip(",").startswith("안녕하세요")


def test_partition_image_raises_with_bad_strategy():
    filename = example_doc_path("img/english-and-korean.png")
    with pytest.raises(ValueError):
        image.partition_image(filename=filename, strategy="fakeroo")


def test_partition_image_default_strategy_hi_res():
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    with open(filename, "rb") as f:
        elements = image.partition_image(file=f)

    title = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    idx = 2
    assert elements[idx].text == title
    assert elements[idx].metadata.coordinates is not None
    assert elements[idx].metadata.detection_class_prob is not None
    assert isinstance(elements[idx].metadata.detection_class_prob, float)
    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        # A bug in partition_groups_from_regions in unstructured-inference losses some sources
        assert {element.metadata.detection_origin for element in elements} == {
            "yolox",
            "ocr_tesseract",
        }


# -- .metadata.last_modified ---------------------------------------------------------------------


def test_partition_image_from_file_path_gets_last_modified_from_filesystem(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = image.partition_image(example_doc_path("img/english-and-korean.png"))

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_image_from_file_path_with_hi_res_strategy_gets_last_modified_from_filesystem(
    mocker: MockFixture,
):
    filesystem_last_modified = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = image.partition_image(
        example_doc_path("img/english-and-korean.png"), strategy=PartitionStrategy.HI_RES
    )

    assert all(e.metadata.last_modified == filesystem_last_modified for e in elements)


def test_partition_image_from_file_path_prefers_metadata_last_modified(mocker: MockFixture):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2009-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = image.partition_image(
        example_doc_path("img/english-and-korean.png"),
        metadata_last_modified=metadata_last_modified,
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_image_from_file_path_with_hi_res_strategy_prefers_metadata_last_modified(
    mocker: MockFixture,
):
    filesystem_last_modified = "2029-07-05T09:24:28"
    metadata_last_modified = "2009-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=filesystem_last_modified,
    )

    elements = image.partition_image(
        example_doc_path("img/english-and-korean.png"),
        strategy=PartitionStrategy.HI_RES,
        metadata_last_modified=metadata_last_modified,
    )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_image_from_file_gets_last_modified_None():
    with open(example_doc_path("img/english-and-korean.png"), "rb") as f:
        elements = image.partition_image(file=f)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_image_from_file_with_hi_res_strategy_gets_last_modified_None(
    mocker: MockFixture,
):
    with open(example_doc_path("img/english-and-korean.png"), "rb") as f:
        elements = image.partition_image(file=f, strategy=PartitionStrategy.HI_RES)

    assert all(e.metadata.last_modified is None for e in elements)


def test_partition_image_from_file_prefers_metadata_last_modified():
    metadata_last_modified = "2009-07-05T09:24:28"

    with open(example_doc_path("img/english-and-korean.png"), "rb") as f:
        elements = image.partition_image(file=f, metadata_last_modified=metadata_last_modified)

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


def test_partition_image_from_file_with_hi_res_strategy_prefers_metadata_last_modified():
    metadata_last_modified = "2009-07-05T09:24:28"

    with open(example_doc_path("img/english-and-korean.png"), "rb") as f:
        elements = image.partition_image(
            file=f,
            metadata_last_modified=metadata_last_modified,
            strategy=PartitionStrategy.HI_RES,
        )

    assert all(e.metadata.last_modified == metadata_last_modified for e in elements)


# ------------------------------------------------------------------------------------------------


def test_partition_msg_with_json():
    elements = image.partition_image(
        example_doc_path("img/layout-parser-paper-fast.jpg"),
        strategy=PartitionStrategy.AUTO,
    )
    assert_round_trips_through_JSON(elements)


def test_partition_image_with_ocr_has_coordinates_from_filename():
    filename = example_doc_path("img/english-and-korean.png")
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.OCR_ONLY)
    int_coordinates = [(int(x), int(y)) for x, y in elements[0].metadata.coordinates.points]
    assert int_coordinates == [(14, 16), (14, 37), (381, 37), (381, 16)]


@pytest.mark.parametrize(
    "filename",
    [
        "img/layout-parser-paper-with-table.jpg",
        "img/english-and-korean.png",
        "img/layout-parser-paper-fast.jpg",
    ],
)
def test_partition_image_with_ocr_coordinates_are_not_nan_from_filename(
    filename,
):
    import math

    elements = image.partition_image(
        filename=example_doc_path(filename), strategy=PartitionStrategy.OCR_ONLY
    )
    for element in elements:
        # TODO (jennings) One or multiple elements is an empty string
        # without coordinates. This should be fixed in a new issue
        if element.text:
            box = element.metadata.coordinates.points
            for point in box:
                assert point[0] is not math.nan
                assert point[1] is not math.nan


def test_partition_image_formats_languages_for_tesseract():
    filename = example_doc_path("img/jpn-vert.jpeg")
    with mock.patch(
        "unstructured.partition.pdf_image.ocr.process_file_with_ocr",
    ) as mock_process_file_with_ocr:
        image.partition_image(
            filename=filename, strategy=PartitionStrategy.HI_RES, languages=["jpn_vert"]
        )
        _, kwargs = mock_process_file_with_ocr.call_args_list[0]
        assert "ocr_languages" in kwargs
        assert kwargs["ocr_languages"] == "jpn_vert"


def test_partition_image_warns_with_ocr_languages(caplog):
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    image.partition_image(filename=filename, strategy=PartitionStrategy.HI_RES, ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_add_chunking_strategy_on_partition_image():
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    elements = image.partition_image(filename=filename)
    chunk_elements = image.partition_image(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_image_hi_res():
    filename = example_doc_path("img/layout-parser-paper-with-table.jpg")
    elements = image.partition_image(
        filename=filename,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    chunk_elements = image.partition_image(
        filename,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
        chunking_strategy="by_title",
    )
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_image_uses_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        image.partition_image(
            example_doc_path("img/layout-parser-paper-fast.jpg"), model_name="test"
        )
        print(mockpartition.call_args)
        assert "model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["model_name"]


def test_partition_image_uses_hi_res_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        image.partition_image(
            example_doc_path("img/layout-parser-paper-fast.jpg"), hi_res_model_name="test"
        )
        print(mockpartition.call_args)
        assert "model_name" not in mockpartition.call_args.kwargs
        assert "hi_res_model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["hi_res_model_name"] == "test"


@pytest.mark.parametrize(
    ("ocr_mode", "idx_title_element"),
    [
        ("entire_page", 2),
        ("individual_blocks", 1),
    ],
)
def test_partition_image_hi_res_ocr_mode(ocr_mode, idx_title_element):
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    elements = image.partition_image(
        filename=filename, ocr_mode=ocr_mode, strategy=PartitionStrategy.HI_RES
    )
    # Note(yuming): idx_title_element is different based on xy-cut and ocr mode
    assert elements[idx_title_element].category == ElementType.TITLE


def test_partition_image_hi_res_invalid_ocr_mode():
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    with pytest.raises(ValueError):
        _ = image.partition_image(
            filename=filename, ocr_mode="invalid_ocr_mode", strategy=PartitionStrategy.HI_RES
        )


@pytest.mark.parametrize(
    "ocr_mode",
    [
        "entire_page",
        "individual_blocks",
    ],
)
def test_partition_image_hi_res_ocr_mode_with_table_extraction(ocr_mode):
    filename = example_doc_path("img/layout-parser-paper-with-table.jpg")
    elements = image.partition_image(
        filename=filename,
        ocr_mode=ocr_mode,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]
    assert "Layouts of history Japanese documents" in table[0]
    assert "Layouts of scanned modern magazines and scientific reports" in table[0]


def test_partition_image_raises_type_error_for_invalid_languages():
    filename = example_doc_path("img/layout-parser-paper-fast.jpg")
    with pytest.raises(TypeError):
        image.partition_image(filename=filename, strategy=PartitionStrategy.HI_RES, languages="eng")


@pytest.fixture()
def inference_results():
    page = layout.PageLayout(
        number=1,
        image=mock.MagicMock(format="JPEG"),
    )
    page.elements = [layout.LayoutElement.from_coords(0, 0, 600, 800, text="hello")]
    page.elements_array = layout.LayoutElements.from_list(page.elements)
    doc = layout.DocumentLayout(pages=[page])
    return doc


def test_partition_image_has_filename(inference_results):
    filename = "layout-parser-paper-fast.jpg"
    # Mock inference call with known return results
    with mock.patch(
        "unstructured_inference.inference.layout.process_file_with_model",
        return_value=inference_results,
    ) as mock_inference_func:
        elements = image.partition_image(
            filename=example_doc_path(f"img/{filename}"),
            strategy=PartitionStrategy.HI_RES,
        )
    # Make sure we actually went down the path we expect.
    mock_inference_func.assert_called_once()
    # Unpack element but also make sure there is only one
    element = only(elements)
    # This makes sure we are still getting the filetype metadata (should be translated from the
    # fixtures)
    assert element.metadata.filetype == "JPEG"
    # This should be kept from the filename we originally gave
    assert element.metadata.filename == filename


@pytest.mark.parametrize("file_mode", ["filename", "rb"])
@pytest.mark.parametrize("extract_image_block_to_payload", [False, True])
def test_partition_image_element_extraction(
    file_mode,
    extract_image_block_to_payload,
):
    filename = example_doc_path("img/embedded-images-tables.jpg")
    extract_image_block_types = ["Image", "Table"]

    with tempfile.TemporaryDirectory() as tmpdir:
        if file_mode == "filename":
            elements = image.partition_image(
                filename=filename,
                extract_image_block_types=extract_image_block_types,
                extract_image_block_to_payload=extract_image_block_to_payload,
                extract_image_block_output_dir=tmpdir,
            )
        else:
            with open(filename, "rb") as f:
                elements = image.partition_image(
                    file=f,
                    extract_image_block_types=extract_image_block_types,
                    extract_image_block_to_payload=extract_image_block_to_payload,
                    extract_image_block_output_dir=tmpdir,
                )

        assert_element_extraction(
            elements, extract_image_block_types, extract_image_block_to_payload, tmpdir
        )


def test_partition_image_works_on_heic_file():
    filename = example_doc_path("img/DA-1p.heic")
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.AUTO)
    titles = [el.text for el in elements if el.category == ElementType.TITLE]
    assert "CREATURES" in titles


@pytest.mark.parametrize(
    "strategy",
    [PartitionStrategy.HI_RES, PartitionStrategy.OCR_ONLY],
)
def test_deterministic_element_ids(strategy: str):
    elements_1 = image.partition_image(
        example_doc_path("img/layout-parser-paper-with-table.jpg"),
        strategy=strategy,
        starting_page_number=2,
    )
    elements_2 = image.partition_image(
        example_doc_path("img/layout-parser-paper-with-table.jpg"),
        strategy=strategy,
        starting_page_number=2,
    )
    ids_1 = [element.id for element in elements_1]
    ids_2 = [element.id for element in elements_2]

    assert ids_1 == ids_2


def test_multi_page_tiff_starts_on_starting_page_number():
    elements = image.partition_image(
        example_doc_path("img/layout-parser-paper-combined.tiff"),
        starting_page_number=2,
    )
    pages = {element.metadata.page_number for element in elements}

    assert pages == {2, 3}


# -- pixel limit ---------------------------------------------------------------------------------


def _write_multi_frame_tiff(tmp_path: pathlib.Path, n_frames: int, side: int) -> str:
    """Write a TIFF of `n_frames` blank `side x side` frames; blank frames compress to ~nothing."""
    frame = Image.new("1", (side, side), 1)
    file_path = str(tmp_path / "frames.tiff")
    frame.save(
        file_path, compression="group4", save_all=True, append_images=[frame] * (n_frames - 1)
    )
    return file_path


@pytest.mark.parametrize("source", ["filename", "file", "bytes"])
def test_check_image_max_pixels_exceeded_sums_pixels_across_frames(
    source: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    # -- 3 frames of 100 x 100 = 30,000 pixels --
    file_path = _write_multi_frame_tiff(tmp_path, n_frames=3, side=100)
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    def check():
        if source == "filename":
            pdf.check_image_max_pixels_exceeded(filename=file_path)
        elif source == "bytes":
            pdf.check_image_max_pixels_exceeded(file=file_bytes)
        else:
            file = io.BytesIO(file_bytes)
            file.seek(7)
            pdf.check_image_max_pixels_exceeded(file=file)
            # -- the caller's read position is restored --
            assert file.tell() == 7

    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "30000")
    check()

    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "29999")
    with pytest.raises(UnprocessableEntityError, match="first 3 frame"):
        check()


def test_check_image_max_pixels_exceeded_reports_a_decompression_bomb_frame_as_unprocessable(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    # -- PIL refuses to open a frame over twice `MAX_IMAGE_PIXELS` --
    file_path = _write_multi_frame_tiff(tmp_path, n_frames=1, side=100)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)

    with pytest.raises(UnprocessableEntityError, match="too many pixels"):
        pdf.check_image_max_pixels_exceeded(filename=file_path)


def _write_tiff(tmp_path: pathlib.Path, sizes: list[tuple[int, int]]) -> str:
    """Write a TIFF with one blank frame of each `(width, height)` in `sizes`."""
    first, *rest = (Image.new("1", size, 1) for size in sizes)
    file_path = str(tmp_path / "mixed.tiff")
    first.save(file_path, compression="group4", save_all=True, append_images=rest)
    return file_path


@pytest.fixture()
def pixel_allocations(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records each pixel-buffer allocation and frame load PIL makes from now on."""
    calls: list[str] = []
    core_new = Image.core.new
    load = ImageFile.ImageFile.load

    def recording_core_new(*args: Any, **kwargs: Any):
        calls.append("core.new")
        return core_new(*args, **kwargs)

    def recording_load(self: ImageFile.ImageFile, *args: Any, **kwargs: Any):
        calls.append("load")
        return load(self, *args, **kwargs)

    monkeypatch.setattr(Image.core, "new", recording_core_new)
    monkeypatch.setattr(ImageFile.ImageFile, "load", recording_load)
    return calls


def test_check_image_max_pixels_exceeded_reads_tiff_frame_sizes_without_allocating(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
):
    # -- mixed frame sizes: 100x100 + 300x200 + 50x50 = 72,500 pixels --
    file_path = _write_tiff(tmp_path, [(100, 100), (300, 200), (50, 50)])
    pixel_allocations = request.getfixturevalue("pixel_allocations")

    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "72500")
    pdf.check_image_max_pixels_exceeded(filename=file_path)
    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "72499")
    with pytest.raises(UnprocessableEntityError, match="first 3 frame"):
        pdf.check_image_max_pixels_exceeded(filename=file_path)

    assert pixel_allocations == []


def test_check_image_max_pixels_exceeded_stops_at_the_frame_that_exceeds_the_limit(
    tmp_path: pathlib.Path, mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    file_path = _write_tiff(tmp_path, [(10, 10), (100, 100), (1000, 1000)])
    seek_ = mocker.spy(TiffImagePlugin.TiffImageFile, "seek")
    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "5000")

    with pytest.raises(UnprocessableEntityError, match="first 2 frame.* 10,100 pixels"):
        pdf.check_image_max_pixels_exceeded(filename=file_path)

    # -- the third frame's header is never read --
    assert max(call.args[1] for call in seek_.call_args_list) == 1


def _save_frames(tmp_path: pathlib.Path, format: str, frames: list[Image.Image]) -> str:
    file_path = str(tmp_path / f"frames.{format.lower()}")
    frames[0].save(file_path, format=format, save_all=True, append_images=frames[1:])
    return file_path


def _distinct_frames(mode: str, size: tuple[int, int], n: int) -> list[Image.Image]:
    """`n` frames that differ, so an encoder does not merge them."""
    frames = []
    for i in range(n):
        frame = Image.new(mode, size, 0)
        frame.putpixel((i, 0), (255, 255, 255) if mode == "RGB" else i + 1)
        frames.append(frame)
    return frames


@pytest.mark.parametrize(
    ("make_file", "n_frames", "total_pixels"),
    [
        # -- frames composited onto the canvas, counted from metadata --
        (lambda p: _save_frames(p, "PNG", _distinct_frames("RGB", (40, 40), 3)), 3, 3 * 1600),
        (lambda p: _save_frames(p, "WEBP", _distinct_frames("RGB", (40, 40), 3)), 3, 3 * 1600),
        (lambda p: _save_frames(p, "GIF", _distinct_frames("P", (40, 30), 3)), 3, 3 * 1200),
        # -- frames of different sizes, read from each frame's header --
        (
            lambda p: _save_frames(
                p, "MPO", [Image.new("RGB", (40, 30)), Image.new("RGB", (400, 300))]
            ),
            2,
            40 * 30 + 400 * 300,
        ),
        # -- images of different sizes, read from the HEIF container --
        (
            lambda p: example_doc_path("img/multi-image-64x48-640x480.heic"),
            2,
            64 * 48 + 640 * 480,
        ),
    ],
    ids=["apng", "webp", "gif", "mpo", "heif"],
)
def test_check_image_max_pixels_exceeded_charges_every_frame_without_decoding_any(
    make_file: Callable[[pathlib.Path], str],
    n_frames: int,
    total_pixels: int,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
):
    register_heif_opener()
    file_path = make_file(tmp_path)
    pixel_allocations = request.getfixturevalue("pixel_allocations")

    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", str(total_pixels))
    pdf.check_image_max_pixels_exceeded(filename=file_path)
    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", str(total_pixels - 1))
    with pytest.raises(UnprocessableEntityError, match=f"first {n_frames} frame"):
        pdf.check_image_max_pixels_exceeded(filename=file_path)

    assert pixel_allocations == []


def _apng_declaring_frames(n_frames: int) -> bytes:
    """A valid two-frame 1x1 APNG whose `acTL` chunk declares `n_frames` frames instead."""
    buffer = io.BytesIO()
    frames = _distinct_frames("RGB", (2, 1), 2)
    frames[0].save(buffer, format="PNG", save_all=True, append_images=frames[1:])
    data = buffer.getvalue()
    i = data.index(b"acTL")
    # -- chunk: 4-byte length, type, data (num_frames, num_plays), CRC over type + data --
    body = b"acTL" + struct.pack(">II", n_frames, 0)
    return (
        data[: i - 4]
        + struct.pack(">I", 8)
        + body
        + struct.pack(">I", zlib.crc32(body))
        + (data[i + 4 + 8 + 4 :])
    )


def test_check_image_max_pixels_exceeded_does_not_iterate_a_declared_frame_count(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
):
    monkeypatch.delenv("IMAGE_MAX_TOTAL_PIXELS", raising=False)  # -- default limit of 5e8 --
    # -- a few hundred bytes declaring 2^31 - 1 frames of 2 x 1 pixels --
    file = io.BytesIO(_apng_declaring_frames(2**31 - 1))
    pixel_allocations = request.getfixturevalue("pixel_allocations")

    started = time.monotonic()
    with pytest.raises(
        UnprocessableEntityError, match="first 250,000,001 frame.* 500,000,002 pixels"
    ):
        pdf.check_image_max_pixels_exceeded(file=file)

    # -- constant work: a loop over the declared frames would take minutes --
    assert time.monotonic() - started < 2
    assert pixel_allocations == []


def test_check_image_max_pixels_exceeded_leaves_the_file_open_at_its_position_when_reading_fails(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    with open(_write_tiff(tmp_path, [(10, 10)] * 3), "rb") as f:
        file = io.BytesIO(f.read())
    file.seek(3)

    def failing_seek(self: TiffImagePlugin.TiffImageFile, frame: int) -> None:
        raise OSError("truncated frame header")

    monkeypatch.setattr(TiffImagePlugin.TiffImageFile, "seek", failing_seek)

    with pytest.raises(OSError, match="truncated frame header"):
        pdf.check_image_max_pixels_exceeded(file=file)

    assert not file.closed
    assert file.tell() == 3


def test_check_image_max_pixels_exceeded_charges_only_the_first_frame_unless_all_frames(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    file_path = _write_tiff(tmp_path, [(100, 100)] * 3)
    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "10000")

    pdf.check_image_max_pixels_exceeded(filename=file_path, all_frames=False)
    with pytest.raises(UnprocessableEntityError, match="first 2 frame"):
        pdf.check_image_max_pixels_exceeded(filename=file_path, all_frames=True)


def test_check_image_max_pixels_exceeded_leaves_a_rejected_file_open_at_its_position(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    with open(_write_tiff(tmp_path, [(100, 100)] * 3), "rb") as f:
        file = io.BytesIO(f.read())
    file.seek(5)
    monkeypatch.setenv("IMAGE_MAX_TOTAL_PIXELS", "100")

    with pytest.raises(UnprocessableEntityError):
        pdf.check_image_max_pixels_exceeded(file=file)

    assert not file.closed
    assert file.tell() == 5


@pytest.mark.parametrize(
    ("strategy", "missing_dependency", "partitioner_name", "expected_all_frames"),
    [
        (PartitionStrategy.HI_RES, None, "_partition_pdf_or_image_local", True),
        (PartitionStrategy.OCR_ONLY, None, "_partition_pdf_or_image_with_ocr", False),
        # -- auto resolves to hi_res for an image --
        (PartitionStrategy.AUTO, None, "_partition_pdf_or_image_local", True),
        # -- the limit follows the strategy a missing dependency falls back to --
        (
            PartitionStrategy.HI_RES,
            "unstructured_inference",
            "_partition_pdf_or_image_with_ocr",
            False,
        ),
        (
            PartitionStrategy.OCR_ONLY,
            "unstructured_pytesseract",
            "_partition_pdf_or_image_local",
            True,
        ),
    ],
)
def test_partition_image_measures_every_frame_only_for_hi_res(
    strategy: str,
    missing_dependency: str | None,
    partitioner_name: str,
    expected_all_frames: bool,
    mocker: MockFixture,
):
    check_ = mocker.patch.object(pdf, "check_image_max_pixels_exceeded")
    mocker.patch.object(pdf, partitioner_name, return_value=[])
    mocker.patch(
        "unstructured.partition.strategies.dependency_exists",
        side_effect=lambda name: name != missing_dependency,
    )
    file_path = example_doc_path("img/layout-parser-paper-fast.jpg")

    pdf.partition_pdf_or_image(file_path, is_image=True, strategy=strategy)

    check_.assert_called_once_with(filename=file_path, file=None, all_frames=expected_all_frames)


def test_partition_pdf_does_not_apply_the_image_pixel_limit(mocker: MockFixture):
    check_ = mocker.patch.object(pdf, "check_image_max_pixels_exceeded")

    pdf.partition_pdf_or_image(
        example_doc_path("pdf/layout-parser-paper-fast.pdf"), strategy=PartitionStrategy.FAST
    )

    check_.assert_not_called()


def test_check_image_max_pixels_exceeded_ignores_a_file_that_is_not_an_image():
    pdf.check_image_max_pixels_exceeded(file=b"not an image")


def test_partition_image_rejects_frames_over_the_pixel_limit_before_decoding(
    tmp_path: pathlib.Path, mocker: MockFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("IMAGE_MAX_TOTAL_PIXELS", raising=False)  # -- default limit of 5e8 --
    # -- 6 blank 10,000 x 10,000 frames: 6e8 pixels, ~1.8 GB as RGB, from a ~40 KB file --
    file_path = _write_multi_frame_tiff(tmp_path, n_frames=6, side=10_000)
    convert_ = mocker.spy(Image.Image, "convert")

    with pytest.raises(UnprocessableEntityError, match="first 6 frame"):
        image.partition_image(file_path, strategy=PartitionStrategy.HI_RES)

    convert_.assert_not_called()
