import os
import tempfile

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


@pytest.mark.parametrize("element_category_to_save", [ElementType.IMAGE, ElementType.TABLE])
@pytest.mark.parametrize("extract_to_payload", [False, True])
def test_save_elements(
    element_category_to_save,
    extract_to_payload,
    filename=example_doc_path("layout-parser-paper-fast.pdf"),
):
    with tempfile.TemporaryDirectory() as tmpdir:
        elements = [
            Image(
                text="3",
                coordinates=((78, 86), (78, 519), (512, 519), (512, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="4",
                coordinates=((570, 86), (570, 519), (1003, 519), (1003, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="5",
                coordinates=((1062, 86), (1062, 519), (1496, 519), (1496, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Table(
                text="Sample Table",
                coordinates=((1062, 86), (1062, 519), (1496, 519), (1496, 86)),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=2),
            ),
        ]

        pdf_image_utils.save_elements(
            elements=elements,
            element_category_to_save=element_category_to_save,
            pdf_image_dpi=200,
            filename=filename,
            output_dir_path=str(tmpdir),
            extract_to_payload=extract_to_payload,
        )

        saved_elements = [el for el in elements if el.category == element_category_to_save]
        for i, el in enumerate(saved_elements):
            basename = "table" if el.category == ElementType.TABLE else "figure"
            expected_image_path = os.path.join(
                str(tmpdir), f"{basename}-{el.metadata.page_number}-{i + 1}.jpg"
            )
            if extract_to_payload:
                assert isinstance(el.metadata.image_base64, str)
                assert isinstance(el.metadata.image_mime_type, str)
                assert not el.metadata.image_path
                assert not os.path.isfile(expected_image_path)
            else:
                assert os.path.isfile(expected_image_path)
                assert el.metadata.image_path == expected_image_path
                assert not el.metadata.image_base64
                assert not el.metadata.image_mime_type


def test_write_image_raises_error():
    with pytest.raises(ValueError):
        pdf_image_utils.write_image("invalid_type", "test_image.jpg")


@pytest.mark.parametrize(
    ("text", "outcome"), [("", False), ("foo", True), (None, False), ("(cid:10)boo", False)]
)
def test_valid_text(text, outcome):
    assert pdf_image_utils.valid_text(text) == outcome
