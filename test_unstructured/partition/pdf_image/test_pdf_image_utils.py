import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image as PILImg

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, ElementType, Image, Table
from unstructured.partition.pdf_image import pdf_image_utils


@pytest.mark.parametrize("image_type", ["pil", "numpy_array"])
def test_write_image(image_type):
    mock_pil_image = PILImg.new("RGB", (50, 50))
    mock_numpy_image = np.zeros((50, 50, 3), np.uint8)

    image_map = {
        "pil": mock_pil_image,
        "numpy_array": mock_numpy_image,
    }
    image = image_map[image_type]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_image_path = os.path.join(tmpdir, "test_image.jpg")
        pdf_image_utils.write_image(image, output_image_path)
        assert os.path.exists(output_image_path)

        # Additional check to see if the written image can be read
        read_image = PILImg.open(output_image_path)
        assert read_image is not None


@pytest.mark.parametrize("file_mode", ["filename", "rb"])
@pytest.mark.parametrize("path_only", [True, False])
def test_convert_pdf_to_image(
    file_mode, path_only, filename=example_doc_path("embedded-images.pdf")
):
    with tempfile.TemporaryDirectory() as tmpdir:
        if file_mode == "filename":
            images = pdf_image_utils.convert_pdf_to_image(
                filename=filename,
                file=None,
                output_folder=tmpdir,
                path_only=path_only,
            )
        else:
            with open(filename, "rb") as f:
                images = pdf_image_utils.convert_pdf_to_image(
                    filename="",
                    file=f,
                    output_folder=tmpdir,
                    path_only=path_only,
                )

        if path_only:
            assert isinstance(images[0], str)
        else:
            assert isinstance(images[0], PILImg.Image)


def test_convert_pdf_to_image_raises_error(filename=example_doc_path("embedded-images.pdf")):
    with pytest.raises(ValueError) as exc_info:
        pdf_image_utils.convert_pdf_to_image(filename=filename, path_only=True, output_folder=None)

    assert str(exc_info.value) == "output_folder must be specified if path_only is true"


@pytest.mark.parametrize(
    ("filename", "is_image"),
    [
        (example_doc_path("layout-parser-paper-fast.pdf"), False),
        (example_doc_path("layout-parser-paper-fast.jpg"), True),
    ],
)
@pytest.mark.parametrize("element_category_to_save", [ElementType.IMAGE, ElementType.TABLE])
@pytest.mark.parametrize("extract_image_block_to_payload", [False, True])
def test_save_elements(
    element_category_to_save,
    extract_image_block_to_payload,
    filename,
    is_image,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        elements = [
            Image(
                text="Image Text 1",
                coordinates=((78, 86), (78, 519), (512, 519), (512, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="Image Text 2",
                coordinates=((570, 86), (570, 519), (1003, 519), (1003, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="Table 1",
                coordinates=((1062, 86), (1062, 519), (1496, 519), (1496, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
        ]
        if not is_image:
            # add a page 2 element
            elements.append(
                Table(
                    text="Table 2",
                    coordinates=((1062, 86), (1062, 519), (1496, 519), (1496, 86)),
                    coordinate_system=PixelSpace(width=1575, height=1166),
                    metadata=ElementMetadata(page_number=2),
                ),
            )

        pdf_image_utils.save_elements(
            elements=elements,
            element_category_to_save=element_category_to_save,
            pdf_image_dpi=200,
            filename=filename,
            is_image=is_image,
            output_dir_path=str(tmpdir),
            extract_image_block_to_payload=extract_image_block_to_payload,
        )

        saved_elements = [el for el in elements if el.category == element_category_to_save]
        for i, el in enumerate(saved_elements):
            basename = "table" if el.category == ElementType.TABLE else "figure"
            expected_image_path = os.path.join(
                str(tmpdir), f"{basename}-{el.metadata.page_number}-{i + 1}.jpg"
            )
            if extract_image_block_to_payload:
                assert isinstance(el.metadata.image_base64, str)
                assert isinstance(el.metadata.image_mime_type, str)
                assert not el.metadata.image_path
                assert not os.path.isfile(expected_image_path)
            else:
                assert os.path.isfile(expected_image_path)
                assert el.metadata.image_path == expected_image_path
                assert not el.metadata.image_base64
                assert not el.metadata.image_mime_type


@pytest.mark.parametrize("storage_enabled", [False, True])
def test_save_elements_with_output_dir_path_none(monkeypatch, storage_enabled):
    monkeypatch.setenv("GLOBAL_WORKING_DIR_ENABLED", storage_enabled)
    with (
        patch("PIL.Image.open"),
        patch("unstructured.partition.pdf_image.pdf_image_utils.write_image"),
        patch("unstructured.partition.pdf_image.pdf_image_utils.convert_pdf_to_image"),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        pdf_image_utils.save_elements(
            elements=[],
            element_category_to_save="",
            pdf_image_dpi=200,
            filename="dummy.pdf",
            output_dir_path=None,
        )

        # Verify that the images are saved in the expected directory
        if storage_enabled:
            from unstructured.partition.utils.config import env_config

            expected_output_dir = os.path.join(env_config.GLOBAL_WORKING_PROCESS_DIR, "figures")
        else:
            expected_output_dir = os.path.join(tmpdir, "figures")
        assert os.path.exists(expected_output_dir)
        assert os.path.isdir(expected_output_dir)
        os.chdir(original_cwd)


def test_write_image_raises_error():
    with pytest.raises(ValueError):
        pdf_image_utils.write_image("invalid_type", "test_image.jpg")


@pytest.mark.parametrize(
    ("text", "outcome"), [("", False), ("foo", True), (None, False), ("(cid:10)boo", False)]
)
def test_valid_text(text, outcome):
    assert pdf_image_utils.valid_text(text) == outcome


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("base", 0.0),
        ("", 0.0),
        ("(cid:2)", 1.0),
        ("(cid:1)a", 0.5),
        ("c(cid:1)ab", 0.25),
    ],
)
def test_cid_ratio(text, expected):
    assert pdf_image_utils.cid_ratio(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("base", False),
        ("(cid:2)", True),
        ("(cid:1234567890)", True),
        ("jkl;(cid:12)asdf", True),
    ],
)
def test_is_cid_present(text, expected):
    assert pdf_image_utils.is_cid_present(text) == expected


def test_pad_bbox():
    bbox = (100, 100, 200, 200)
    padding = (10, 20)  # Horizontal padding 10, Vertical padding 20
    expected = (90, 80, 210, 220)

    result = pdf_image_utils.pad_bbox(bbox, padding)
    assert result == expected


@pytest.mark.parametrize(
    ("input_types", "expected"),
    [
        (None, []),
        (["table", "image"], ["Table", "Image"]),
        (["unknown"], ["Unknown"]),
        (["Table", "image", "UnknOwn"], ["Table", "Image", "Unknown"]),
    ],
)
def test_check_element_types_to_extract(input_types, expected):
    assert pdf_image_utils.check_element_types_to_extract(input_types) == expected


def test_check_element_types_to_extract_raises_error():
    with pytest.raises(TypeError) as exc_info:
        pdf_image_utils.check_element_types_to_extract("not a list")
    assert "must be a list" in str(exc_info.value)


class MockPageLayout:
    def annotate(self, colors):
        return "mock_image"


class MockDocumentLayout:
    pages = [MockPageLayout(), MockPageLayout]


def test_annotate_layout_elements_with_image():
    inferred_layout = MockPageLayout()
    extracted_layout = MockPageLayout()
    output_basename = "test_page"
    page_number = 1

    # Check if images for both layouts were saved
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        patch("unstructured.partition.pdf_image.pdf_image_utils.write_image") as mock_write_image,
    ):
        pdf_image_utils.annotate_layout_elements_with_image(
            inferred_page_layout=inferred_layout,
            extracted_page_layout=extracted_layout,
            output_dir_path=str(tmpdir),
            output_f_basename=output_basename,
            page_number=page_number,
        )

        expected_filenames = [
            f"{output_basename}_{page_number}_inferred.jpg",
            f"{output_basename}_{page_number}_extracted.jpg",
        ]
        actual_calls = [call.args[1] for call in mock_write_image.call_args_list]
        for expected_filename in expected_filenames:
            assert any(expected_filename in actual_call for actual_call in actual_calls)

    # Check if only the inferred layout image was saved if extracted layout is None
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        patch("unstructured.partition.pdf_image.pdf_image_utils.write_image") as mock_write_image,
    ):
        pdf_image_utils.annotate_layout_elements_with_image(
            inferred_page_layout=inferred_layout,
            extracted_page_layout=None,
            output_dir_path=str(tmpdir),
            output_f_basename=output_basename,
            page_number=page_number,
        )

        expected_filename = f"{output_basename}_{page_number}_inferred.jpg"
        actual_calls = [call.args[1] for call in mock_write_image.call_args_list]
        assert any(expected_filename in actual_call for actual_call in actual_calls)
        assert len(actual_calls) == 1  # Only one image should be saved


@pytest.mark.parametrize(
    ("filename", "is_image"),
    [
        (example_doc_path("layout-parser-paper-fast.pdf"), False),
        (example_doc_path("layout-parser-paper-fast.jpg"), True),
    ],
)
def test_annotate_layout_elements(filename, is_image):
    inferred_document_layout = MockDocumentLayout
    extracted_layout = [MagicMock(), MagicMock()]

    with (
        patch("PIL.Image.open"),
        patch(
            "unstructured.partition.pdf_image.pdf_image_utils.convert_pdf_to_image",
            return_value=["/path/to/image1.jpg", "/path/to/image2.jpg"],
        ) as mock_pdf2image,
        patch(
            "unstructured.partition.pdf_image.pdf_image_utils.annotate_layout_elements_with_image"
        ) as mock_annotate_layout_elements_with_image,
    ):
        pdf_image_utils.annotate_layout_elements(
            inferred_document_layout=inferred_document_layout,
            extracted_layout=extracted_layout,
            filename=filename,
            output_dir_path="/output",
            pdf_image_dpi=200,
            is_image=is_image,
        )
        if is_image:
            mock_annotate_layout_elements_with_image.assert_called_once()
        else:
            assert mock_annotate_layout_elements_with_image.call_count == len(
                mock_pdf2image.return_value
            )


def test_annotate_layout_elements_file_not_found_error():
    with pytest.raises(FileNotFoundError):
        pdf_image_utils.annotate_layout_elements(
            inferred_document_layout=MagicMock(),
            extracted_layout=[],
            filename="nonexistent.jpg",
            output_dir_path="/output",
            pdf_image_dpi=200,
            is_image=True,
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [("test\tco\x0cn\ftrol\ncharacter\rs\b", "test control characters"), ("\"'\\", "\"'\\")],
)
def test_remove_control_characters(text, expected):
    assert pdf_image_utils.remove_control_characters(text) == expected
