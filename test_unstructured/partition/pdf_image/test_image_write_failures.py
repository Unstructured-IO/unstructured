import re

import cv2
import numpy as np
import pytest
from PIL import Image

from unstructured.partition.pdf_image.pdf_image_utils import write_image


@pytest.mark.parametrize("image_type", ["numpy", "pil"])
@pytest.mark.parametrize("destination_kind", ["missing-parent", "parent-is-file", "is-directory"])
def test_failed_image_writes_raise_for_both_supported_image_types(
    tmp_path, image_type, destination_kind
):
    pixels = np.zeros((4, 5, 3), dtype=np.uint8)
    image = pixels if image_type == "numpy" else Image.fromarray(pixels)
    if destination_kind == "missing-parent":
        destination = tmp_path / "missing" / "image.png"
    elif destination_kind == "parent-is-file":
        parent = tmp_path / "parent"
        parent.write_text("existing data", encoding="utf-8")
        destination = parent / "image.png"
    else:
        destination = tmp_path / "image.png"
        destination.mkdir()

    try:
        with pytest.raises(OSError, match=re.escape(str(destination))):
            write_image(image, str(destination))
    finally:
        if isinstance(image, Image.Image):
            image.close()

    if destination_kind == "parent-is-file":
        assert parent.read_text(encoding="utf-8") == "existing data"
    elif destination_kind == "is-directory":
        assert destination.is_dir()
    else:
        assert not destination.exists()


@pytest.mark.parametrize(
    "pixels",
    [
        np.arange(60, dtype=np.uint8).reshape(4, 5, 3),
        np.arange(20, dtype=np.uint8).reshape(4, 5),
        (np.arange(20, dtype=np.uint16) * 1000).reshape(4, 5),
    ],
    ids=["color", "grayscale", "16bit-grayscale"],
)
def test_successful_numpy_image_writes_preserve_pixels_and_return_none(tmp_path, pixels):
    destination = tmp_path / "image.png"

    assert write_image(pixels, str(destination)) is None
    decoded = cv2.imread(str(destination), cv2.IMREAD_UNCHANGED)
    np.testing.assert_array_equal(decoded, pixels)
