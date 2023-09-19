import os
import pathlib
from unittest import mock

import pytest
from PIL import Image
from pytesseract import TesseractError
from unstructured_inference.inference import layout

from unstructured.chunking.title import chunk_by_title
from unstructured.partition import image, pdf
from unstructured.partition.json import partition_json
from unstructured.staging.base import elements_to_json

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

    @property
    def elements(self):
        return [
            layout.LayoutElement(
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
    [("example-docs/example.jpg", None), (None, b"0000")],
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
    filename="example-docs/layout-parser-paper-fast.jpg",
):
    elements = image.partition_image(filename=filename, strategy="auto")
    titles = [el for el in elements if el.category == "Title" and len(el.text.split(" ")) > 10]
    title = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    assert titles[0].text == title
    assert elements[0].metadata.detection_class_prob is not None
    assert isinstance(elements[0].metadata.detection_class_prob, float)


def test_partition_image_with_table_extraction(
    filename="example-docs/layout-parser-paper-with-table.jpg",
):
    elements = image.partition_image(
        filename=filename,
        strategy="hi_res",
        infer_table_structure=True,
    )
    table = [el.metadata.text_as_html for el in elements if el.metadata.text_as_html]
    assert len(table) == 1
    assert "<table><thead><th>" in table[0]


def test_partition_image_with_multipage_tiff(
    filename="example-docs/layout-parser-paper-combined.tiff",
):
    elements = image.partition_image(filename=filename, strategy="auto")
    assert elements[-1].metadata.page_number == 2


def test_partition_image_with_language_passed(filename="example-docs/example.jpg"):
    with mock.patch.object(
        layout,
        "process_file_with_model",
        mock.MagicMock(),
    ) as mock_partition:
        image.partition_image(
            filename=filename,
            strategy="hi_res",
            ocr_languages="eng+swe",
        )

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


def test_partition_image_from_file_with_language_passed(
    filename="example-docs/example.jpg",
):
    with mock.patch.object(
        layout,
        "process_data_with_model",
        mock.MagicMock(),
    ) as mock_partition, open(filename, "rb") as f:
        image.partition_image(file=f, strategy="hi_res", ocr_languages="eng+swe")

    assert mock_partition.call_args.kwargs.get("ocr_languages") == "eng+swe"


# NOTE(crag): see https://github.com/Unstructured-IO/unstructured/issues/1086
@pytest.mark.skip(reason="Current catching too many tesseract errors")
def test_partition_image_raises_with_invalid_language(
    filename="example-docs/example.jpg",
):
    with pytest.raises(TesseractError):
        image.partition_image(
            filename=filename,
            strategy="hi_res",
            ocr_languages="fakeroo",
        )


def test_partition_image_with_ocr_detects_korean():
    filename = os.path.join(
        DIRECTORY,
        "..",
        "..",
        "..",
        "example-docs",
        "english-and-korean.png",
    )
    elements = image.partition_image(
        filename=filename,
        ocr_languages="eng+kor",
        strategy="ocr_only",
    )

    assert elements[0].text == "RULES AND INSTRUCTIONS"
    assert elements[3].text.replace(" ", "").startswith("안녕하세요")


def test_partition_image_with_ocr_detects_korean_from_file():
    filename = os.path.join(DIRECTORY, "..", "..", "..", "example-docs", "english-and-korean.png")
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            ocr_languages="eng+kor",
            strategy="ocr_only",
        )

    assert elements[0].text == "RULES AND INSTRUCTIONS"
    assert elements[3].text.replace(" ", "").startswith("안녕하세요")


def test_partition_image_raises_with_bad_strategy():
    filename = os.path.join(
        DIRECTORY,
        "..",
        "..",
        "..",
        "example-docs",
        "english-and-korean.png",
    )
    with pytest.raises(ValueError):
        image.partition_image(filename=filename, strategy="fakeroo")


def test_partition_image_default_strategy_hi_res():
    filename = os.path.join(
        DIRECTORY,
        "..",
        "..",
        "..",
        "example-docs",
        "layout-parser-paper-fast.jpg",
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(file=f)

    first_line = "LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis"
    assert elements[0].text == first_line
    assert elements[0].metadata.coordinates is not None
    assert elements[0].metadata.detection_class_prob is not None
    assert isinstance(elements[0].metadata.detection_class_prob, float)


def test_partition_image_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(filename=filename)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_with_hi_res_strategy_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(filename=filename, stratefy="hi_res")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_metadata_date_custom_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(
        filename=filename,
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_with_hi_res_strategy_metadata_date_custom_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date",
        return_value=mocked_last_modification_date,
    )
    elements = image.partition_image(
        filename=filename,
        stratefy="hi_res",
        metadata_last_modified=expected_last_modification_date,
    )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_image_from_file_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(file=f)

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_from_file_with_hi_res_strategy_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )

    with open(filename, "rb") as f:
        elements = image.partition_image(file=f, stratefy="hi_res")

    assert elements[0].metadata.last_modified == mocked_last_modification_date


def test_partition_image_from_file_metadata_date_custom_metadata_date(
    mocker,
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
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
    filename="example-docs/english-and-korean.png",
):
    mocked_last_modification_date = "2029-07-05T09:24:28"
    expected_last_modification_date = "2009-07-05T09:24:28"

    mocker.patch(
        "unstructured.partition.pdf.get_last_modified_date_from_file",
        return_value=mocked_last_modification_date,
    )
    with open(filename, "rb") as f:
        elements = image.partition_image(
            file=f,
            metadata_last_modified=expected_last_modification_date,
            stratefy="hi_res",
        )

    assert elements[0].metadata.last_modified == expected_last_modification_date


def test_partition_msg_with_json(
    filename="example-docs/layout-parser-paper-fast.jpg",
):
    elements = image.partition_image(filename=filename, strategy="auto")
    test_elements = partition_json(text=elements_to_json(elements))

    assert len(elements) == len(test_elements)
    assert elements[0].metadata.page_number == test_elements[0].metadata.page_number
    for i in range(len(elements)):
        assert elements[i] == test_elements[i]


def test_partition_image_with_ocr_has_coordinates_from_filename(
    filename="example-docs/english-and-korean.png",
):
    elements = image.partition_image(filename=filename, strategy="ocr_only")
    int_coordinates = [(int(x), int(y)) for x, y in elements[0].metadata.coordinates.points]
    assert int_coordinates == [(14, 36), (14, 16), (381, 16), (381, 36)]


@pytest.mark.parametrize(
    ("filename"),
    [
        ("example-docs/layout-parser-paper-with-table.jpg"),
        ("example-docs/english-and-korean.png"),
        ("example-docs/layout-parser-paper-fast.jpg"),
    ],
)
def test_partition_image_with_ocr_coordinates_are_not_nan_from_filename(
    filename,
):
    import math

    elements = image.partition_image(filename=filename, strategy="ocr_only")
    for element in elements:
        # TODO (jennings) One or multiple elements is an empty string
        # without coordinates. This should be fixed in a new issue
        if element.text:
            box = element.metadata.coordinates.points
            for point in box:
                assert point[0] is not math.nan
                assert point[1] is not math.nan


def test_partition_image_formats_languages_for_tesseract():
    filename = "example-docs/jpn-vert.jpeg"
    with mock.patch.object(layout, "process_file_with_model", mock.MagicMock()) as mock_process:
        image.partition_image(filename=filename, strategy="hi_res", languages=["jpn_vert"])
        mock_process.assert_called_once_with(
            filename,
            is_image=True,
            ocr_languages="jpn_vert",
            ocr_mode="entire_page",
            extract_tables=False,
            model_name=None,
        )


def test_partition_image_warns_with_ocr_languages(caplog):
    filename = "example-docs/layout-parser-paper-fast.jpg"
    image.partition_image(filename=filename, strategy="hi_res", ocr_languages="eng")
    assert "The ocr_languages kwarg will be deprecated" in caplog.text


def test_add_chunking_strategy_on_partition_image(
    filename="example-docs/layout-parser-paper-fast.jpg",
):
    elements = image.partition_image(filename=filename)
    chunk_elements = image.partition_image(filename, chunking_strategy="by_title")
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_partition_image_uses_model_name():
    with mock.patch.object(
        pdf,
        "_partition_pdf_or_image_local",
    ) as mockpartition:
        image.partition_image("example-docs/layout-parser-paper-fast.jpg", model_name="test")
        print(mockpartition.call_args)
        assert "model_name" in mockpartition.call_args.kwargs
        assert mockpartition.call_args.kwargs["model_name"]
