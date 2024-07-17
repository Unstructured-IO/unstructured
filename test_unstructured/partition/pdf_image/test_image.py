from __future__ import annotations

import os
import pathlib
import tempfile
from unittest import mock

import pytest
from PIL import Image
from pytesseract import TesseractError
from unstructured_inference.inference import layout

from test_unstructured.partition.pdf_image.test_pdf import assert_element_extraction
from test_unstructured.unit_utils import assert_round_trips_through_JSON, example_doc_path
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementType
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


def test_partition_image_with_auto_strategy(
    filename=example_doc_path("img/layout-parser-paper-fast.jpg"),
):
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.AUTO)
    titles = [
        el for el in elements if el.category == ElementType.TITLE and len(el.text.split(" ")) > 10
    ]
    title = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    idx = 3
    assert titles[0].text == title
    assert elements[idx].metadata.detection_class_prob is not None
    assert isinstance(elements[idx].metadata.detection_class_prob, float)


def test_partition_image_with_table_extraction(
    filename=example_doc_path("img/layout-parser-paper-with-table.jpg"),
):
    elements = image.partition_image(
        filename=filename,
        strategy=PartitionStrategy.HI_RES,
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><tr>" in table[0]
    assert "</thead><tbody><tr>" in table[0]


def test_partition_image_with_multipage_tiff(
    filename=example_doc_path("img/layout-parser-paper-combined.tiff"),
):
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.AUTO)
    assert elements[-1].metadata.page_number == 2


def test_partition_image_with_bmp(
    tmpdir,
    filename=example_doc_path("img/layout-parser-paper-with-table.jpg"),
):
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


def test_partition_image_with_language_passed(filename=example_doc_path("img/example.jpg")):
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


def test_partition_image_from_file_with_language_passed(
    filename=example_doc_path("img/example.jpg"),
):
    with mock.patch.object(
        ocr,
        "process_data_with_ocr",
        mock.MagicMock(),
    ) as mock_partition, open(filename, "rb") as f:
        image.partition_image(file=f, strategy=PartitionStrategy.HI_RES, ocr_languages="eng+swe")

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


# NOTE(crag): see https://github.com/Unstructured-IO/unstructured/issues/1086
@pytest.mark.skip(reason="Current catching too many tesseract errors")
def test_partition_image_raises_with_invalid_language(
    filename=example_doc_path("img/example.jpg"),
):
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
    assert elements[3].text.replace(" ", "").startswith("안녕하세요")


def test_partition_image_with_ocr_detects_korean_from_file():
    filename = example_doc_path("img/english-and-korean.png")
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            ocr_languages="eng+kor",
            strategy=PartitionStrategy.OCR_ONLY,
        )

    assert elements[0].text == "RULES AND INSTRUCTIONS"
    assert elements[3].text.replace(" ", "").startswith("안녕하세요")


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


def test_partition_image_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(filename=filename)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_with_hi_res_strategy_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(filename=filename, strategy=PartitionStrategy.HI_RES)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_metadata_date_custom_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_with_hi_res_strategy_metadata_date_custom_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(
        filename=filename,
        strategy=PartitionStrategy.HI_RES,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_from_file_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(file=f)

    assert elements[0].metadata.last_modified is None


def test_partition_image_from_file_explicit_get_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(file=f, date_from_file_object=True)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_from_file_with_hi_res_strategy_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = image.partition_image(file=f, strategy=PartitionStrategy.HI_RES)

    assert elements[0].metadata.last_modified is None


def test_partition_image_from_file_with_hi_res_strategy_explicit_get_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f, strategy=PartitionStrategy.HI_RES, date_from_file_object=True
        )

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_from_file_metadata_date_custom_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            metadata_last_modified=expected_last_modification_date,
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_from_file_with_hi_res_strategy_metadata_date_custom_metadata_date(
    mocker,
    filename=example_doc_path("img/english-and-korean.png"),
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf_image.pdf_image_utils.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            metadata_last_modified=expected_last_modification_date,
            strategy=PartitionStrategy.HI_RES,
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_from_file_without_metadata_date(
    filename=example_doc_path("img/english-and-korean.png"),
):
    """Test partition_image() with file that are not possible to get last modified date"""
    with open(filename, "rb") as f:
        sf = tempfile.SpooledTemporaryFile()
        sf.write(f.read())
        sf.seek(0)
        elements = image.partition_image(file=sf, date_from_file_object=True)

    assert elements[0].metadata.last_modified is None


def test_partition_msg_with_json():
    elements = image.partition_image(
        example_doc_path("img/layout-parser-paper-fast.jpg"),
        strategy=PartitionStrategy.AUTO,
    )
    assert_round_trips_through_JSON(elements)


def test_partition_image_with_ocr_has_coordinates_from_filename(
    filename=example_doc_path("img/english-and-korean.png"),
):
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


def test_add_chunking_strategy_on_partition_image(
    filename=example_doc_path("img/layout-parser-paper-fast.jpg"),
):
    elements = image.partition_image(filename=filename)
    chunk_elements = image.partition_image(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_on_partition_image_hi_res(
    filename=example_doc_path("img/layout-parser-paper-with-table.jpg"),
):
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
    filename=example_doc_path("img/embedded-images-tables.jpg"),
):
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


def test_partition_image_works_on_heic_file(
    filename=example_doc_path("img/DA-1p.heic"),
):
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
