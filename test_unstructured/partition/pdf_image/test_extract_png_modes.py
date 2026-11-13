import base64
from io import BytesIO

import pytest
from PIL import Image as PILImage

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, ElementType, Image
from unstructured.partition.pdf_image.pdf_image_utils import save_elements


@pytest.mark.parametrize("mode", ["P", "LA", "RGBA", "RGB", "L"])
@pytest.mark.parametrize("to_payload", [False, True])
def test_extract_png_modes_preserves_the_crop_and_color(tmp_path, mode, to_payload):
    source_path = tmp_path / "source.png"
    with PILImage.new("RGB", (40, 30), (210, 20, 40)) as original:
        converted = original.quantize(colors=1) if mode == "P" else original.convert(mode)
        with converted as source:
            source.save(source_path)
            with source.convert("RGB") as rgb_source:
                expected_pixel = rgb_source.getpixel((10, 10))

    element = Image(
        text="figure",
        coordinates=((5, 5), (5, 25), (35, 25), (35, 5)),
        coordinate_system=PixelSpace(40, 30),
        metadata=ElementMetadata(page_number=1),
    )

    save_elements(
        [element],
        starting_page_number=1,
        element_category_to_save=ElementType.IMAGE,
        pdf_image_dpi=200,
        filename=str(source_path),
        is_image=True,
        extract_image_block_to_payload=to_payload,
        output_dir_path=str(tmp_path / "figures"),
    )

    if to_payload:
        assert element.metadata.image_base64
        assert element.metadata.image_mime_type == "image/jpeg"
        image_source = BytesIO(base64.b64decode(element.metadata.image_base64))
        assert element.metadata.image_path is None
    else:
        assert element.metadata.image_path
        image_source = element.metadata.image_path
        assert element.metadata.image_base64 is None

    with PILImage.open(image_source) as extracted:
        assert extracted.format == "JPEG"
        assert extracted.size == (30, 20)
        with extracted.convert("RGB") as rgb_extracted:
            assert rgb_extracted.getpixel((10, 10)) == pytest.approx(expected_pixel, abs=3)
    with PILImage.open(source_path) as unchanged_source:
        assert unchanged_source.mode == mode
        assert unchanged_source.size == (40, 30)
