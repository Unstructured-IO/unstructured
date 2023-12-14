import os
import tempfile

import numpy as np
import pytest
from PIL import Image as PILImg

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, ElementType, Image
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


def test_save_elements(filename=example_doc_path("embedded-images.pdf")):
    with tempfile.TemporaryDirectory() as tmpdir:
        elements = [
            Image(
                text="3",
                coordinates=(
                    (78.7401411111111, 86.61545694444455),
                    (78.7401411111111, 519.9487805555556),
                    (512.0734647222223, 519.9487805555556),
                    (512.0734647222223, 86.61545694444455),
                ),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="4",
                coordinates=(
                    (570.8661397222222, 86.6154566666667),
                    (570.8661397222222, 519.6862825000001),
                    (1003.9369655555556, 519.6862825000001),
                    (1003.9369655555556, 86.6154566666667),
                ),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
            Image(
                text="5",
                coordinates=(
                    (1062.9921808333331, 86.61545694444455),
                    (1062.9921808333331, 519.9487805555556),
                    (1496.3255044444445, 519.9487805555556),
                    (1496.3255044444445, 86.61545694444455),
                ),
                coordinate_system=PixelSpace(width=1575, height=1166),
                metadata=ElementMetadata(page_number=1),
            ),
        ]

        pdf_image_utils.save_elements(
            elements=elements,
            element_category_to_save=ElementType.IMAGE,
            pdf_image_dpi=200,
            filename=filename,
            output_dir_path=str(tmpdir),
        )

        for i, el in enumerate(elements):
            expected_image_path = os.path.join(
                str(tmpdir), f"figure-{el.metadata.page_number}-{i + 1}.jpg"
            )
            assert os.path.isfile(el.metadata.image_path)
            assert el.metadata.image_path == expected_image_path


def test_write_image_raises_error():
    with pytest.raises(ValueError):
        pdf_image_utils.write_image("invalid_type", "test_image.jpg")


@pytest.mark.parametrize(
    ("text", "outcome"), [("", False), ("foo", True), (None, False), ("(cid:10)boo", False)]
)
def test_valid_text(text, outcome):
    assert pdf_image_utils.valid_text(text) == outcome
