import numpy as np
import pandas as pd
import pytest
from PIL import Image

from unstructured.partition.utils.ocr_models.tesseract_ocr import OCRAgentTesseract, zoom_image


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "P", "L", "LA", "1"])
@pytest.mark.parametrize("zoom", [0.5, 1, 2, 0])
def test_ocr_zoom_preserves_rgb_colors_and_resolves_image_modes(mode, zoom):
    with Image.new("RGB", (40, 20), (210, 20, 40)) as original:
        converted = (
            original.quantize(colors=1)
            if mode == "P"
            else original.convert(mode, dither=Image.Dither.NONE)
        )
        with converted as source:
            before = source.tobytes()
            with source.convert("RGB") as rgb_source:
                expected_pixel = rgb_source.getpixel((10, 10))

            with zoom_image(source, zoom) as result:
                effective_zoom = zoom if zoom > 0 else 1
                assert result.size == (int(40 * effective_zoom), int(20 * effective_zoom))
                assert result.mode == "RGB"
                assert result.getpixel((result.width // 2, result.height // 2)) == expected_pixel

            assert source.mode == mode
            assert source.tobytes() == before


def test_tesseract_rescaling_pass_receives_rgb_pixels(mocker, monkeypatch):
    monkeypatch.setenv("TESSERACT_MIN_TEXT_HEIGHT", "12")
    monkeypatch.setenv("TESSERACT_OPTIMUM_TEXT_HEIGHT", "20")
    first = pd.DataFrame([{"left": 2, "top": 2, "width": 10, "height": 4, "text": "word"}])
    second = pd.DataFrame([{"left": 10, "top": 10, "width": 50, "height": 20, "text": "word"}])
    agent = OCRAgentTesseract()
    recognize = mocker.patch.object(
        agent, "image_to_data_with_character_confidence_filter", side_effect=[first, second]
    )

    with Image.new("RGB", (40, 20), (210, 20, 40)) as source:
        result = agent.get_layout_from_image(source)

    assert recognize.call_count == 2
    resized_pixels = recognize.call_args_list[1].args[0]
    assert resized_pixels.shape == (100, 200, 3)
    np.testing.assert_array_equal(resized_pixels[50, 100], [210, 20, 40])
    assert result.texts.tolist() == ["word"]
    np.testing.assert_array_equal(result.element_coords, [[2, 2, 12, 6]])
