import os
import os.path
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pytest
from PIL import Image

import unstructured_inference.models.base as models
from unstructured_inference.constants import IsExtracted
from unstructured_inference.inference import elements, layout, layoutelement, pdf_image
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    ImageTextRegion,
)
from unstructured_inference.models.unstructuredmodel import (
    UnstructuredElementExtractionModel,
    UnstructuredObjectDetectionModel,
)

skip_outside_ci = os.getenv("CI", "").lower() in {"", "false", "f", "0"}


@pytest.fixture
def mock_image():
    return Image.new("1", (1, 1))


@pytest.fixture
def mock_initial_layout():
    text_block = EmbeddedTextRegion.from_coords(
        2,
        4,
        6,
        8,
        text="A very repetitive narrative. " * 10,
        is_extracted=IsExtracted.TRUE,
    )

    title_block = EmbeddedTextRegion.from_coords(
        1,
        2,
        3,
        4,
        text="A Catchy Title",
        is_extracted=IsExtracted.TRUE,
    )

    return [text_block, title_block]


@pytest.fixture
def mock_final_layout():
    text_block = layoutelement.LayoutElement.from_coords(
        2,
        4,
        6,
        8,
        source="Mock",
        text="A very repetitive narrative. " * 10,
        type="NarrativeText",
    )

    title_block = layoutelement.LayoutElement.from_coords(
        1,
        2,
        3,
        4,
        source="Mock",
        text="A Catchy Title",
        type="Title",
    )

    return layoutelement.LayoutElements.from_list([text_block, title_block])


def test_pdf_page_converts_images_to_array(mock_image):
    def verify_image_array():
        assert page.image_array is None
        image_array = page._get_image_array()
        assert isinstance(image_array, np.ndarray)
        assert page.image_array.all() == image_array.all()

    # Scenario 1: where self.image exists
    page = layout.PageLayout(number=0, image=mock_image)
    verify_image_array()

    # Scenario 2: where self.image is None, but self.image_path exists
    page.image_array = None
    page.image = None
    page.image_path = "mock_path_to_image"
    with patch.object(Image, "open", return_value=mock_image):
        verify_image_array()


class MockLayoutModel:
    def __init__(self, layout):
        self.layout_return = layout

    def __call__(self, *args):
        return self.layout_return

    def initialize(self, *args, **kwargs):
        pass

    def deduplicate_detected_elements(self, elements, *args, **kwargs):
        return elements


def test_get_page_elements(monkeypatch, mock_final_layout):
    image = Image.fromarray(
        np.random.randint(12, 14, size=(40, 10, 3)).astype(np.uint8), mode="RGB"
    )
    page = layout.PageLayout(
        number=0,
        image=image,
        detection_model=MockLayoutModel(mock_final_layout),
    )
    elements = page.get_elements_with_detection_model(inplace=False)
    page.get_elements_with_detection_model(inplace=True)
    assert elements == page.elements_array


class MockPool:
    def map(self, f, xs):
        return [f(x) for x in xs]

    def close(self):
        pass

    def join(self):
        pass


@pytest.mark.parametrize("model_name", [None, "checkbox", "fake"])
def test_process_data_with_model(monkeypatch, mock_final_layout, model_name):
    monkeypatch.setattr(layout, "get_model", lambda x: MockLayoutModel(mock_final_layout))
    monkeypatch.setattr(
        layout.DocumentLayout,
        "from_file",
        lambda *args, **kwargs: layout.DocumentLayout.from_pages([]),
    )

    def new_isinstance(obj, cls):
        if type(obj) is MockLayoutModel:
            return True
        else:
            return isinstance(obj, cls)

    with (
        patch("builtins.open", mock_open(read_data=b"000000")),
        patch(
            "unstructured_inference.inference.layout.UnstructuredObjectDetectionModel",
            MockLayoutModel,
        ),
        open("") as fp,
    ):
        assert layout.process_data_with_model(fp, model_name=model_name)


def test_process_data_with_model_raises_on_invalid_model_name():
    with (
        patch("builtins.open", mock_open(read_data=b"000000")),
        pytest.raises(
            models.UnknownModelException,
        ),
        open("") as fp,
    ):
        layout.process_data_with_model(fp, model_name="fake")


@pytest.mark.parametrize("model_name", [None, "yolox"])
def test_process_file_with_model(monkeypatch, mock_final_layout, model_name):
    def mock_initialize(self, *args, **kwargs):
        self.model = MockLayoutModel(mock_final_layout)

    monkeypatch.setattr(
        layout.DocumentLayout,
        "from_file",
        lambda *args, **kwargs: layout.DocumentLayout.from_pages([]),
    )
    monkeypatch.setattr(models.UnstructuredDetectronONNXModel, "initialize", mock_initialize)
    filename = ""
    assert layout.process_file_with_model(filename, model_name=model_name)


def test_process_file_no_warnings(monkeypatch, mock_final_layout, recwarn):
    def mock_initialize(self, *args, **kwargs):
        self.model = MockLayoutModel(mock_final_layout)

    monkeypatch.setattr(
        layout.DocumentLayout,
        "from_file",
        lambda *args, **kwargs: layout.DocumentLayout.from_pages([]),
    )
    monkeypatch.setattr(models.UnstructuredDetectronONNXModel, "initialize", mock_initialize)
    filename = ""
    layout.process_file_with_model(filename, model_name=None)
    # There should be no UserWarning, but if there is one it should not have the following message
    with pytest.raises(AssertionError, match="not found in warning list"):
        user_warning = recwarn.pop(UserWarning)
        assert "not in available provider names" not in str(user_warning.message)


def test_process_file_with_model_raises_on_invalid_model_name():
    with pytest.raises(models.UnknownModelException):
        layout.process_file_with_model("", model_name="fake")


class MockPoints:
    def tolist(self):
        return [1, 2, 3, 4]


class MockEmbeddedTextRegion(EmbeddedTextRegion):
    def __init__(self, type=None, text=None):
        self.type = type
        self.text = text

    @property
    def points(self):
        return MockPoints()


class MockPageLayout(layout.PageLayout):
    def __init__(
        self,
        number=1,
        image=None,
        model=None,
        detection_model=None,
    ):
        self.image = image
        self.layout = layout
        self.model = model
        self.number = number
        self.detection_model = detection_model


class MockLayout:
    def __init__(self, *elements):
        self.elements = elements

    def __len__(self):
        return len(self.elements)

    def sort(self, key, inplace):
        return self.elements

    def __iter__(self):
        return iter(self.elements)

    def get_texts(self):
        return [el.text for el in self.elements]

    def filter_by(self, *args, **kwargs):
        return MockLayout()


@pytest.mark.parametrize("element_extraction_model", [None, "foo"])
@pytest.mark.parametrize("filetype", ["png", "jpg", "tiff"])
def test_from_image_file(monkeypatch, mock_final_layout, filetype, element_extraction_model):
    def mock_get_elements(self, *args, **kwargs):
        self.elements = [mock_final_layout]

    monkeypatch.setattr(layout.PageLayout, "get_elements_with_detection_model", mock_get_elements)
    monkeypatch.setattr(layout.PageLayout, "get_elements_using_image_extraction", mock_get_elements)
    filename = f"sample-docs/loremipsum.{filetype}"
    image = Image.open(filename)
    image_metadata = {
        "format": image.format,
        "width": image.width,
        "height": image.height,
        "pdf_rotation": 0,
        "pdf_rotation_correction": 0,
    }

    doc = layout.DocumentLayout.from_image_file(
        filename,
        element_extraction_model=element_extraction_model,
    )
    page = doc.pages[0]
    assert page.elements[0] == mock_final_layout
    assert page.image is None
    assert page.image_path == os.path.abspath(filename)
    assert page.image_metadata == image_metadata


def test_from_file(monkeypatch, mock_final_layout):
    def mock_get_elements(self, *args, **kwargs):
        self.elements = [mock_final_layout]

    monkeypatch.setattr(layout.PageLayout, "get_elements_with_detection_model", mock_get_elements)

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "loremipsum.ppm")
        image = Image.open("sample-docs/loremipsum.jpg")
        image.save(image_path)
        image_metadata = {
            "format": "PPM",
            "width": image.width,
            "height": image.height,
            "pdf_rotation": 0,
            "pdf_rotation_correction": 0,
        }

        with patch.object(
            layout,
            "convert_pdf_to_image",
            lambda *args, **kwargs: ([image_path]),
        ):
            doc = layout.DocumentLayout.from_file("fake-file.pdf")
            page = doc.pages[0]
            assert page.elements[0] == mock_final_layout
            assert page.image_metadata == image_metadata
            assert page.image is None


def test_from_file_rotated_pdf_stores_rotation_in_metadata(monkeypatch, mock_final_layout):
    """image_metadata includes pdf_rotation for rotated PDF pages."""

    def mock_get_elements(self, *args, **kwargs):
        self.elements = [mock_final_layout]

    monkeypatch.setattr(layout.PageLayout, "get_elements_with_detection_model", mock_get_elements)

    doc = layout.DocumentLayout.from_file("sample-docs/rotated-page-90.pdf")
    page = doc.pages[0]
    assert page.image_metadata["pdf_rotation"] == 90
    assert page.image is None


@pytest.mark.slow
def test_from_file_with_password(monkeypatch, mock_final_layout):

    doc = layout.DocumentLayout.from_file("sample-docs/password.pdf", password="password")
    assert doc

    monkeypatch.setattr(layout, "get_model", lambda x: MockLayoutModel(mock_final_layout))
    with (
        patch(
            "unstructured_inference.inference.layout.UnstructuredObjectDetectionModel",
            MockLayoutModel,
        ),
        open("sample-docs/password.pdf", mode="rb") as fp,
    ):
        doc = layout.process_data_with_model(fp, model_name="fake", password="password")
        assert doc


def test_from_image_file_raises_with_empty_fn():
    with pytest.raises(FileNotFoundError):
        layout.DocumentLayout.from_image_file("")


def test_from_image_file_raises_isadirectoryerror_with_dir():
    with tempfile.TemporaryDirectory() as tempdir, pytest.raises(IsADirectoryError):
        layout.DocumentLayout.from_image_file(tempdir)


def test_page_numbers_in_page_objects():
    with patch(
        "unstructured_inference.inference.layout.PageLayout.get_elements_with_detection_model",
    ) as mock_get_elements:
        doc = layout.DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf")
        mock_get_elements.assert_called()
        assert [page.number for page in doc.pages] == list(range(1, len(doc.pages) + 1))


no_text_region = EmbeddedTextRegion.from_coords(0, 0, 100, 100)
text_region = EmbeddedTextRegion.from_coords(0, 0, 100, 100, text="test")
overlapping_rect = ImageTextRegion.from_coords(50, 50, 150, 150)
nonoverlapping_rect = ImageTextRegion.from_coords(150, 150, 200, 200)
populated_text_region = EmbeddedTextRegion.from_coords(50, 50, 60, 60, text="test")
unpopulated_text_region = EmbeddedTextRegion.from_coords(50, 50, 60, 60, text=None)


@pytest.mark.parametrize(
    ("colors", "add_details", "threshold"),
    [("red", False, 0.992), (None, False, 0.992), ("red", True, 0.8)],
)
def test_annotate(colors, add_details, threshold):
    def check_annotated_image():
        annotated_array = np.array(annotated_image)
        for coords in [coords1, coords2]:
            x1, y1, x2, y2 = coords
            # Make sure the pixels on the edge of the box are red
            for i, expected in zip(range(3), [255, 0, 0]):
                assert all(annotated_array[y1, x1:x2, i] == expected)
                assert all(annotated_array[y2, x1:x2, i] == expected)
                assert all(annotated_array[y1:y2, x1, i] == expected)
                assert all(annotated_array[y1:y2, x2, i] == expected)
            # Make sure almost all the pixels are not changed
            assert ((annotated_array[:, :, 0] == 1).mean()) > threshold
            assert ((annotated_array[:, :, 1] == 1).mean()) > threshold
            assert ((annotated_array[:, :, 2] == 1).mean()) > threshold

    test_image_arr = np.ones((100, 100, 3), dtype="uint8")
    image = Image.fromarray(test_image_arr)
    page = layout.PageLayout(number=1, image=image)
    coords1 = (21, 30, 37, 41)
    rect1 = elements.TextRegion.from_coords(*coords1)
    coords2 = (1, 10, 7, 11)
    rect2 = elements.TextRegion.from_coords(*coords2)
    page.elements = [rect1, rect2]

    annotated_image = page.annotate(colors=colors, add_details=add_details, sources=None)
    check_annotated_image()

    # Scenario 1: where self.image exists
    annotated_image = page.annotate(colors=colors, add_details=add_details)
    check_annotated_image()

    # Scenario 2: where self.image is None, but self.image_path exists
    with patch.object(Image, "open", return_value=image):
        page.image = None
        page.image_path = "mock_path_to_image"
        annotated_image = page.annotate(colors=colors, add_details=add_details)
        check_annotated_image()


class MockDetectionModel(layout.UnstructuredObjectDetectionModel):
    def initialize(self, *args, **kwargs):
        pass

    def predict(self, x):
        return layoutelement.LayoutElements.from_list(
            [
                layout.LayoutElement.from_coords(x1=447.0, y1=315.0, x2=1275.7, y2=413.0, text="0"),
                layout.LayoutElement.from_coords(x1=380.6, y1=473.4, x2=1334.8, y2=533.9, text="1"),
                layout.LayoutElement.from_coords(x1=578.6, y1=556.8, x2=1109.0, y2=874.4, text="2"),
                layout.LayoutElement.from_coords(
                    x1=444.5,
                    y1=942.3,
                    x2=1261.1,
                    y2=1584.1,
                    text="3",
                ),
                layout.LayoutElement.from_coords(
                    x1=444.8,
                    y1=1609.4,
                    x2=1257.2,
                    y2=1665.2,
                    text="4",
                ),
                layout.LayoutElement.from_coords(
                    x1=414.0,
                    y1=1718.8,
                    x2=635.0,
                    y2=1755.2,
                    text="5",
                ),
                layout.LayoutElement.from_coords(
                    x1=372.6,
                    y1=1786.9,
                    x2=1333.6,
                    y2=1848.7,
                    text="6",
                ),
            ],
        )


def test_layout_order(mock_image):
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_image_path = os.path.join(tmpdir, "mock.jpg")
        mock_image.save(mock_image_path)
        with (
            patch.object(layout, "get_model", lambda: MockDetectionModel()),
            patch.object(
                layout,
                "convert_pdf_to_image",
                lambda *args, **kwargs: ([mock_image_path]),
            ),
        ):
            doc = layout.DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf")
            page = doc.pages[0]
    for n, element in enumerate(page.elements):
        assert element.text == str(n)


def test_page_layout_raises_when_multiple_models_passed(mock_image, mock_initial_layout):
    with pytest.raises(ValueError):
        layout.PageLayout(
            0,
            mock_image,
            mock_initial_layout,
            detection_model="something",
            element_extraction_model="something else",
        )


class MockElementExtractionModel:
    def __call__(self, x):
        return [1, 2, 3]


@pytest.mark.parametrize(("inplace", "expected"), [(True, None), (False, [1, 2, 3])])
def test_get_elements_using_image_extraction(mock_image, inplace, expected):
    page = layout.PageLayout(
        1,
        mock_image,
        None,
        element_extraction_model=MockElementExtractionModel(),
    )
    assert page.get_elements_using_image_extraction(inplace=inplace) == expected


def test_get_elements_using_image_extraction_raises_with_no_extraction_model(
    mock_image,
):
    page = layout.PageLayout(1, mock_image, None, element_extraction_model=None)
    with pytest.raises(ValueError):
        page.get_elements_using_image_extraction()


def test_get_elements_with_detection_model_raises_with_wrong_default_model(monkeypatch):
    monkeypatch.setattr(layout, "get_model", lambda *x: MockLayoutModel(mock_final_layout))
    page = layout.PageLayout(1, mock_image, None)
    with pytest.raises(NotImplementedError):
        page.get_elements_with_detection_model()


@pytest.mark.parametrize(
    (
        "detection_model",
        "element_extraction_model",
        "detection_model_called",
        "element_extraction_model_called",
    ),
    [(None, "asdf", False, True), ("asdf", None, True, False)],
)
def test_from_image(
    mock_image,
    detection_model,
    element_extraction_model,
    detection_model_called,
    element_extraction_model_called,
):
    with (
        patch.object(
            layout.PageLayout,
            "get_elements_using_image_extraction",
        ) as mock_image_extraction,
        patch.object(
            layout.PageLayout,
            "get_elements_with_detection_model",
        ) as mock_detection,
    ):
        layout.PageLayout.from_image(
            mock_image,
            image_path=None,
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
        )
        assert mock_image_extraction.called == element_extraction_model_called
        assert mock_detection.called == detection_model_called


class MockUnstructuredElementExtractionModel(UnstructuredElementExtractionModel):
    def initialize(self, *args, **kwargs):
        return super().initialize(*args, **kwargs)

    def predict(self, x: Image):
        return super().predict(x)


class MockUnstructuredDetectionModel(UnstructuredObjectDetectionModel):
    def initialize(self, *args, **kwargs):
        return super().initialize(*args, **kwargs)

    def predict(self, x: Image):
        return super().predict(x)


@pytest.mark.parametrize(
    ("model_type", "is_detection_model"),
    [
        (MockUnstructuredElementExtractionModel, False),
        (MockUnstructuredDetectionModel, True),
    ],
)
def test_process_file_with_model_routing(monkeypatch, model_type, is_detection_model):
    model = model_type()
    monkeypatch.setattr(layout, "get_model", lambda *x: model)
    with patch.object(layout.DocumentLayout, "from_file") as mock_from_file:
        layout.process_file_with_model("asdf", model_name="fake", is_image=False)
        if is_detection_model:
            detection_model = model
            element_extraction_model = None
        else:
            detection_model = None
            element_extraction_model = model
        mock_from_file.assert_called_once_with(
            "asdf",
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
            fixed_layouts=None,
            password=None,
            pdf_image_dpi=200,
            pdf_render_max_pixels_per_page=None,
        )


@pytest.mark.parametrize(("pdf_image_dpi", "expected"), [(200, 2200), (100, 1100)])
def test_exposed_pdf_image_dpi(pdf_image_dpi, expected, monkeypatch):
    with patch.object(layout.PageLayout, "from_image") as mock_from_image:
        layout.DocumentLayout.from_file("sample-docs/loremipsum.pdf", pdf_image_dpi=pdf_image_dpi)
        assert mock_from_image.call_args[0][0].height == expected


def test_convert_pdf_to_image_no_output_folder():
    result = layout.convert_pdf_to_image(filename="sample-docs/loremipsum.pdf", dpi=72)
    assert len(result) == 1
    assert isinstance(result[0], Image.Image)


def _install_mock_pdfium(monkeypatch, *, width=720, height=720):
    page = MagicMock()
    page.get_width.return_value = width
    page.get_height.return_value = height
    page.get_rotation.return_value = 0
    page.render.return_value.to_pil.return_value = Image.new("RGB", (1, 1))
    pdf = MagicMock()
    pdf.__len__.return_value = 1
    pdf.__getitem__.return_value = page
    pdfium = MagicMock()
    pdfium.PdfDocument.return_value = pdf
    monkeypatch.setattr(pdf_image, "_get_pdfium_module", lambda: pdfium)
    return page


def test_convert_pdf_to_image_rejects_oversized_page_before_render(monkeypatch):
    page = _install_mock_pdfium(monkeypatch)

    with pytest.raises(pdf_image.PdfRenderTooLargeError, match="too many pixels"):
        pdf_image.convert_pdf_to_image(
            filename="mock.pdf",
            dpi=100,
            pdf_render_max_pixels_per_page=999_999,
        )

    page.render.assert_not_called()


def test_convert_pdf_to_image_allows_render_guard_to_be_disabled(monkeypatch):
    page = _install_mock_pdfium(monkeypatch)

    result = pdf_image.convert_pdf_to_image(
        filename="mock.pdf",
        dpi=100,
        pdf_render_max_pixels_per_page=0,
    )

    page.render.assert_called_once()
    assert len(result) == 1
    assert isinstance(result[0], Image.Image)


def test_page_hotload_preserves_render_max_pixels_per_page(monkeypatch, tmp_path):
    image_path = tmp_path / "page_1.png"
    Image.new("RGB", (1, 1)).save(image_path)
    calls = []

    def fake_convert_pdf_to_image(**kwargs):
        calls.append(kwargs)
        return [str(image_path)]

    monkeypatch.setattr(layout, "convert_pdf_to_image", fake_convert_pdf_to_image)
    page = layout.PageLayout(
        number=1,
        image=Image.new("RGB", (1, 1)),
        document_filename="mock.pdf",
        pdf_render_max_pixels_per_page=None,
    )

    image = page._get_image("mock.pdf", 1, pdf_image_dpi=123)

    assert image.size == (1, 1)
    assert calls[0]["dpi"] == 123
    assert calls[0]["pdf_render_max_pixels_per_page"] is None


def test_convert_pdf_to_image_output_folder_returns_images(tmp_path):
    result = layout.convert_pdf_to_image(
        filename="sample-docs/loremipsum.pdf",
        dpi=72,
        output_folder=tmp_path,
        path_only=False,
    )
    assert len(result) == 1
    assert isinstance(result[0], Image.Image)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) == 1


def test_convert_pdf_to_image_path_only(tmp_path):
    result = layout.convert_pdf_to_image(
        filename="sample-docs/loremipsum.pdf",
        dpi=72,
        output_folder=tmp_path,
        path_only=True,
    )
    assert len(result) == 1
    assert all(isinstance(p, str) for p in result)
    for p in result:
        assert os.path.exists(p)
        assert p.endswith(".png")
    saved = sorted(tmp_path.glob("*.png"))
    assert [str(s) for s in saved] == sorted(result)


def test_convert_pdf_to_image_applies_rotation_path_only(tmp_path):
    """Rotation is also applied when saving to disk (path_only mode)."""
    result = layout.convert_pdf_to_image(
        filename="sample-docs/rotated-page-90.pdf",
        dpi=72,
        output_folder=tmp_path,
        path_only=True,
    )
    assert len(result) == 1
    saved = Image.open(result[0])
    assert saved.height > saved.width, f"Expected portrait after rotation, got {saved.size}"


def test_convert_pdf_to_image_no_rotation_on_normal_pdf():
    """Non-rotated PDFs are unchanged."""
    result = layout.convert_pdf_to_image(filename="sample-docs/loremipsum.pdf", dpi=72)
    assert len(result) == 1
    img = result[0]
    # loremipsum.pdf is a standard portrait page - should stay portrait
    assert img.height > img.width, f"Expected portrait, got {img.size}"


def test_convert_pdf_to_image_save_not_under_pdfium_lock(tmp_path):
    """Verify that PIL save (disk I/O) is NOT performed while holding _pdfium_lock."""
    original_save = Image.Image.save
    lock_held_during_save = []

    def spy_save(self, *args, **kwargs):
        lock_held_during_save.append(layout._pdfium_lock.locked())
        return original_save(self, *args, **kwargs)

    with patch.object(Image.Image, "save", spy_save):
        layout.convert_pdf_to_image(
            filename="sample-docs/loremipsum.pdf",
            dpi=72,
            output_folder=tmp_path,
            path_only=True,
        )
    assert lock_held_during_save, "save was never called"
    assert not any(lock_held_during_save), "pil_image.save() was called while _pdfium_lock was held"


def test_convert_pdf_to_image_concurrent_saves_not_serialized(tmp_path):
    """Two concurrent callers must be able to overlap their disk writes.

    Uses a threading.Barrier to verify both threads are inside save()
    simultaneously. If saves are serialized under _pdfium_lock, the second
    thread can never reach save() while the first is there, so the barrier
    times out and the test fails.
    """
    import threading

    original_save = Image.Image.save
    barrier = threading.Barrier(2, timeout=5)
    overlap_detected = threading.Event()

    def barrier_save(self, *args, **kwargs):
        try:
            barrier.wait()
            overlap_detected.set()
        except threading.BrokenBarrierError:
            pass
        return original_save(self, *args, **kwargs)

    errors: list[str] = []

    def run(folder):
        try:
            layout.convert_pdf_to_image(
                filename="sample-docs/loremipsum.pdf",
                dpi=72,
                output_folder=folder,
                path_only=True,
            )
        except Exception as exc:
            errors.append(str(exc))

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    with patch.object(Image.Image, "save", barrier_save):
        t1 = threading.Thread(target=run, args=(dir_a,))
        t2 = threading.Thread(target=run, args=(dir_b,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

    assert not errors, f"threads raised: {errors}"
    assert overlap_detected.is_set(), (
        "saves were serialized under _pdfium_lock — threads could not overlap"
    )
    assert list(dir_a.glob("*.png")), "thread A produced no output"
    assert list(dir_b.glob("*.png")), "thread B produced no output"


def test_render_can_proceed_while_other_thread_saves(tmp_path):
    """Thread B can acquire _pdfium_lock and render while thread A is in save().

    Blocks thread A inside save() (outside the lock), then starts thread B.
    If B completes entirely while A is still blocked, the lock was not held
    during save — rendering and saving can overlap across callers.
    """
    import threading

    original_save = Image.Image.save
    a_in_save = threading.Event()
    b_done = threading.Event()

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    def gated_save(self, *args, **kwargs):
        fp = str(args[0]) if args else ""
        if str(dir_a) in fp:
            a_in_save.set()
            b_done.wait(timeout=5)
        return original_save(self, *args, **kwargs)

    errors: list[str] = []

    def run(folder, done_event=None):
        try:
            layout.convert_pdf_to_image(
                filename="sample-docs/loremipsum.pdf",
                dpi=72,
                output_folder=folder,
                path_only=True,
            )
        except Exception as exc:
            errors.append(str(exc))
        finally:
            if done_event:
                done_event.set()

    with patch.object(Image.Image, "save", gated_save):
        t_a = threading.Thread(target=run, args=(dir_a,))
        t_b = threading.Thread(target=run, args=(dir_b, b_done))
        t_a.start()
        a_in_save.wait(timeout=5)
        # A is now blocked in save (outside lock). B should render + save freely.
        t_b.start()
        t_b.join(timeout=10)
        t_a.join(timeout=10)

    assert not errors, f"threads raised: {errors}"
    assert b_done.is_set(), "Thread B could not complete while A was saving"
    assert list(dir_a.glob("*.png")), "thread A produced no output"
    assert list(dir_b.glob("*.png")), "thread B produced no output"


def test_multi_page_concurrent_output_complete(tmp_path):
    """Two threads processing a multi-page PDF both produce correct, complete output."""
    import threading

    errors: list[str] = []

    def run(folder):
        try:
            layout.convert_pdf_to_image(
                filename="sample-docs/loremipsum_multipage.pdf",
                dpi=72,
                output_folder=folder,
                path_only=True,
            )
        except Exception as exc:
            errors.append(str(exc))

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    t1 = threading.Thread(target=run, args=(dir_a,))
    t2 = threading.Thread(target=run, args=(dir_b,))
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)

    assert not errors, f"threads raised: {errors}"
    a_files = sorted(dir_a.glob("*.png"))
    b_files = sorted(dir_b.glob("*.png"))
    assert len(a_files) == 10, f"thread A produced {len(a_files)} files, expected 10"
    assert len(b_files) == 10, f"thread B produced {len(b_files)} files, expected 10"
    for i in range(1, 11):
        assert (dir_a / f"page_{i}.png").exists(), f"thread A missing page_{i}.png"
        assert (dir_b / f"page_{i}.png").exists(), f"thread B missing page_{i}.png"


def test_error_in_one_thread_does_not_block_other(tmp_path):
    """If one thread fails mid-processing, the other still completes."""
    import threading

    original_save = Image.Image.save

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    def failing_save(self, *args, **kwargs):
        fp = str(args[0]) if args else ""
        if str(dir_a) in fp:
            raise OSError("simulated disk failure")
        return original_save(self, *args, **kwargs)

    a_error: list[Exception] = []
    b_result: list[str] = []
    b_error: list[Exception] = []

    def run_a():
        try:
            layout.convert_pdf_to_image(
                filename="sample-docs/loremipsum.pdf",
                dpi=72,
                output_folder=dir_a,
                path_only=True,
            )
        except Exception as exc:
            a_error.append(exc)

    def run_b():
        try:
            result = layout.convert_pdf_to_image(
                filename="sample-docs/loremipsum.pdf",
                dpi=72,
                output_folder=dir_b,
                path_only=True,
            )
            b_result.extend(result)
        except Exception as exc:
            b_error.append(exc)

    with patch.object(Image.Image, "save", failing_save):
        t_a = threading.Thread(target=run_a)
        t_b = threading.Thread(target=run_b)
        t_a.start()
        t_b.start()
        t_a.join(timeout=10)
        t_b.join(timeout=10)

    assert a_error, "Thread A should have failed"
    assert not b_error, f"Thread B should have succeeded: {b_error}"
    assert b_result, "Thread B produced no result"
    assert list(dir_b.glob("*.png")), "Thread B produced no output files"


@pytest.mark.parametrize(
    ("filename", "img_num", "should_complete"),
    [
        ("sample-docs/empty-document.pdf", 0, True),
        ("sample-docs/empty-document.pdf", 10, False),
    ],
)
def test_get_image(filename, img_num, should_complete):
    doc = layout.DocumentLayout.from_file(filename)
    page = doc.pages[0]
    try:
        img = page._get_image(filename, img_num)
        # transform img to numpy array
        img = np.array(img)
        # is a blank image with all pixels white
        assert img.mean() == 255.0
    except ValueError:
        assert not should_complete
