from unittest import mock

import numpy as np
import pytest
from PIL import Image
from unstructured_inference.inference.elements import Rectangle
from unstructured_inference.inference.layout import DocumentLayout, PageLayout
from unstructured_inference.inference.layoutelement import LayoutElement

from unstructured.partition.pdf_image.analysis.bbox_visualisation import (
    AnalysisDrawer,
    TextAlignment,
    get_bbox_text_size,
    get_bbox_thickness,
    get_label_rect_and_coords,
    get_rgb_color,
    get_text_color,
)
from unstructured.partition.pdf_image.analysis.layout_dump import ObjectDetectionLayoutDumper


@pytest.mark.parametrize("color", ["red", "green", "blue", "yellow", "black", "white"])
def test_get_rgb_color(color: str):
    color_tuple = get_rgb_color(color)

    assert isinstance(color_tuple, tuple)
    assert len(color_tuple) == 3
    assert all(isinstance(c, int) for c in color_tuple)
    assert all(0 <= c <= 255 for c in color_tuple)


@pytest.mark.parametrize(
    ("bbox", "expected_text_size"),
    [
        ((0, 0, 90, 90), 17),
        ((0, 0, 500, 200), 21),
        ((0, 0, 10000, 10000), 32),
    ],
)
def test_get_bbox_text_size(bbox: tuple[int, int, int, int], expected_text_size):
    page_size = (1700, 2200)  # standard size of a page
    text_size = get_bbox_text_size(bbox, page_size)

    assert text_size == expected_text_size


@pytest.mark.parametrize(
    ("bbox", "expected_box_thickness"),
    [
        ((0, 0, 90, 90), 1),
        ((0, 0, 450, 250), 2),
        ((0, 0, 600, 1000), 3),
    ],
)
def test_get_bbox_thickness(bbox: tuple[int, int, int, int], expected_box_thickness):
    page_size = (1700, 2200)  # standard size of a page
    box_thickness = get_bbox_thickness(bbox, page_size)

    assert box_thickness == expected_box_thickness


@pytest.mark.parametrize(
    ("color", "expected_text_color"),
    [
        ("navy", "white"),
        ("crimson", "white"),
        ("maroon", "white"),
        ("dimgray", "white"),
        ("darkgreen", "white"),
        ("darkcyan", "white"),
        ("fuchsia", "white"),
        ("violet", "black"),
        ("gold", "black"),
        ("aqua", "black"),
        ("greenyellow", "black"),
    ],
)
def test_best_text_color(color, expected_text_color):
    color_tuple = get_rgb_color(color)
    expected_text_color_tuple = get_rgb_color(expected_text_color)

    _, text_color_tuple = get_text_color(color_tuple)
    assert text_color_tuple == expected_text_color_tuple


@pytest.mark.parametrize(
    ("alignment", "expected_text_bbox"),
    [
        (TextAlignment.CENTER, ((145, 145), (155, 155))),
        (TextAlignment.TOP_LEFT, ((100, 90), (120, 100))),
        (TextAlignment.TOP_RIGHT, ((180, 100), (200, 110))),
        (TextAlignment.BOTTOM_LEFT, ((100, 190), (120, 200))),
        (TextAlignment.BOTTOM_RIGHT, ((180, 190), (200, 200))),
    ],
)
def test_get_text_bbox(alignment, expected_text_bbox):
    text_bbox, text_xy = get_label_rect_and_coords(
        alignment=alignment, bbox_points=(100, 100, 200, 200), text_width=10, text_height=10
    )
    # adding high atol to account for the text-based extending of the bbox
    assert np.allclose(text_bbox, expected_text_bbox, atol=10)


def test_od_document_layout_dump():
    page1 = PageLayout(
        number=1,
        image=Image.new("1", (1, 1)),
        image_metadata={"width": 100, "height": 100},
    )
    page1.elements = [
        LayoutElement(type="Title", bbox=Rectangle(x1=0, y1=0, x2=10, y2=10), prob=0.7),
        LayoutElement(type="Paragraph", bbox=Rectangle(x1=0, y1=100, x2=10, y2=110), prob=0.8),
    ]
    page2 = PageLayout(
        number=2,
        image=Image.new("1", (1, 1)),
        image_metadata={"width": 100, "height": 100},
    )
    page2.elements = [
        LayoutElement(type="Table", bbox=Rectangle(x1=0, y1=0, x2=10, y2=10), prob=0.9),
        LayoutElement(type="Image", bbox=Rectangle(x1=0, y1=100, x2=10, y2=110), prob=1.0),
    ]
    od_document_layout = DocumentLayout(pages=[page1, page2])

    expected_dump = {
        "pages": [
            {
                "number": 1,
                "size": {
                    "width": 100,
                    "height": 100,
                },
                "elements": [
                    {"bbox": [0, 0, 10, 10], "type": "Title", "prob": 0.7},
                    {"bbox": [0, 100, 10, 110], "type": "Paragraph", "prob": 0.8},
                ],
            },
            {
                "number": 2,
                "size": {
                    "width": 100,
                    "height": 100,
                },
                "elements": [
                    {"bbox": [0, 0, 10, 10], "type": "Table", "prob": 0.9},
                    {"bbox": [0, 100, 10, 110], "type": "Image", "prob": 1.0},
                ],
            },
        ]
    }
    od_layout_dump = ObjectDetectionLayoutDumper(od_document_layout).dump()

    assert expected_dump == {"pages": od_layout_dump.get("pages")}

    # check OD model classes are attached but do not depend on a specific model instance
    assert "object_detection_classes" in od_layout_dump
    assert len(od_layout_dump["object_detection_classes"]) > 0


class TestAnalysisDrawerDpi:
    """Tests for pdf_image_dpi passthrough in AnalysisDrawer (issue #3985)."""

    def test_analysis_drawer_stores_pdf_image_dpi(self):
        drawer = AnalysisDrawer(
            filename="test.pdf",
            is_image=False,
            save_dir="/tmp",
            pdf_image_dpi=72,
        )
        assert drawer.pdf_image_dpi == 72

    def test_analysis_drawer_defaults_pdf_image_dpi_to_none(self):
        drawer = AnalysisDrawer(
            filename="test.pdf",
            is_image=False,
            save_dir="/tmp",
        )
        assert drawer.pdf_image_dpi is None

    @pytest.mark.parametrize("dpi", [72, 150, 300])
    def test_analysis_drawer_passes_dpi_to_convert_pdf_to_image(self, dpi):
        drawer = AnalysisDrawer(
            filename="test.pdf",
            is_image=False,
            save_dir="/tmp",
            pdf_image_dpi=dpi,
        )
        with mock.patch(
            "unstructured.partition.pdf_image.analysis.bbox_visualisation.convert_pdf_to_image",
            return_value=[],
        ) as mock_convert:
            list(drawer.load_source_image())
            mock_convert.assert_called_once()
            assert mock_convert.call_args[1]["dpi"] == dpi

    def test_analysis_drawer_passes_none_dpi_when_not_set(self):
        drawer = AnalysisDrawer(
            filename="test.pdf",
            is_image=False,
            save_dir="/tmp",
        )
        with mock.patch(
            "unstructured.partition.pdf_image.analysis.bbox_visualisation.convert_pdf_to_image",
            return_value=[],
        ) as mock_convert:
            list(drawer.load_source_image())
            mock_convert.assert_called_once()
            assert mock_convert.call_args[1]["dpi"] is None


class TestSaveAnalysisArtifactsDpi:
    """Tests for pdf_image_dpi passthrough in save_analysis_artifiacts."""

    @pytest.mark.parametrize("dpi", [72, 150, None])
    def test_save_analysis_artifiacts_passes_dpi_to_drawer(self, dpi):
        from unstructured.partition.pdf_image.analysis import tools

        with mock.patch.object(tools, "AnalysisDrawer") as mock_drawer_cls:
            mock_drawer_cls.return_value.process = mock.MagicMock()
            tools.save_analysis_artifiacts(
                is_image=False,
                analyzed_image_output_dir_path="/tmp/test_analysis",
                filename="test.pdf",
                pdf_image_dpi=dpi,
            )
            mock_drawer_cls.assert_called_once()
            assert mock_drawer_cls.call_args[1]["pdf_image_dpi"] == dpi


class TestRenderBboxesForFileDpi:
    """Tests for pdf_image_dpi passthrough in render_bboxes_for_file."""

    @pytest.mark.parametrize("dpi", [72, 300, None])
    def test_render_bboxes_passes_dpi_to_drawer(self, tmp_path, dpi):
        import json

        from unstructured.partition.pdf_image.analysis import tools

        # Create the directory structure expected by render_bboxes_for_file
        filename = "test.pdf"
        dump_dir = tmp_path / "analysis" / "test" / "layout_dump"
        dump_dir.mkdir(parents=True)
        dump_file = dump_dir / "final.json"
        dump_file.write_text(json.dumps({"pages": []}))

        with mock.patch.object(tools, "AnalysisDrawer") as mock_drawer_cls:
            mock_drawer_cls.return_value.process = mock.MagicMock()
            tools.render_bboxes_for_file(
                filename=filename,
                analyzed_image_output_dir_path=str(tmp_path),
                pdf_image_dpi=dpi,
            )
            mock_drawer_cls.assert_called_once()
            assert mock_drawer_cls.call_args[1]["pdf_image_dpi"] == dpi
