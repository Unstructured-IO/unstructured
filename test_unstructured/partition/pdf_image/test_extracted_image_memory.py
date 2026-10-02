"""Extraction byte parity, bounded upload reads, and owned image lifetime regressions."""

import base64
import io

import pytest
from PIL import Image as PILImage

from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import ElementMetadata, Image
from unstructured.partition.pdf_image import pdf_image_utils


def _closed(image):
    try:
        image.getpixel((0, 0))
    except ValueError:
        return True
    return False


def _element():
    return Image(
        text="figure",
        coordinates=((-3, 2), (-3, 35), (45, 35), (45, 2)),
        coordinate_system=PixelSpace(width=50, height=40),
        metadata=ElementMetadata(page_number=7),
    )


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "L"])
@pytest.mark.parametrize("payload", [True, False])
def test_extraction_preserves_native_jpeg_bytes_and_metadata(tmp_path, mode, payload):
    source = tmp_path / "source.png"
    with PILImage.new(mode, (50, 40), 123) as image:
        image.save(source)
    with PILImage.open(source) as image:
        crop = image.crop((-3, 2, 45, 35))
        if mode == "RGBA":
            crop = crop.convert("RGB")
        with crop, io.BytesIO() as expected:
            crop.save(expected, format="JPEG")
            expected_bytes = expected.getvalue()
    element = _element()
    pdf_image_utils.save_elements(
        [element],
        7,
        "Image",
        200,
        filename=str(source),
        is_image=True,
        extract_image_block_to_payload=payload,
        output_dir_path=str(tmp_path),
    )
    assert element.text == "figure"
    assert element.metadata.page_number == 7
    if payload:
        assert element.metadata.image_base64 == base64.b64encode(expected_bytes).decode()
        assert element.metadata.image_mime_type == "image/jpeg"
        assert element.metadata.image_path is None
    else:
        path = tmp_path / "figure-7-1.jpg"
        assert path.read_bytes() == expected_bytes
        assert element.metadata.image_path == str(path)
        assert element.metadata.image_base64 is None


def test_image_upload_reads_are_bounded_and_leave_borrowed_stream_open(tmp_path):
    class BoundedStream(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024
            return super().read(size)

    with PILImage.new("RGB", (50, 40)) as image, io.BytesIO() as encoded:
        image.save(encoded, format="PNG")
        raw = encoded.getvalue()
    stream = BoundedStream(raw)
    stream.seek(3)
    element = _element()
    pdf_image_utils.save_elements(
        [element],
        7,
        "Image",
        200,
        file=stream,
        is_image=True,
        extract_image_block_to_payload=True,
    )
    assert not stream.closed
    assert stream.tell() == len(raw)
    stream.seek(0)
    assert stream.read(1024 * 1024) == raw


@pytest.mark.parametrize("fail_encode", [False, True])
def test_extraction_releases_page_before_encoding_and_crops_before_next_decode(
    tmp_path,
    monkeypatch,
    fail_encode,
):
    source = tmp_path / "source.png"
    with PILImage.new("RGBA", (50, 40)) as image:
        image.save(source)
    opened = []
    crops = []
    real_open = PILImage.open
    real_crop = PILImage.Image.crop
    real_save = PILImage.Image.save
    real_convert = PILImage.Image.convert

    def tracked_open(*args, **kwargs):
        assert all(_closed(image) for image in crops)
        image = real_open(*args, **kwargs)
        opened.append(image)
        return image

    def tracked_crop(image, *args, **kwargs):
        crop = real_crop(image, *args, **kwargs)
        crops.append(crop)
        return crop

    def tracked_convert(image, *args, **kwargs):
        converted = real_convert(image, *args, **kwargs)
        crops.append(converted)
        return converted

    def tracked_save(image, *args, **kwargs):
        assert all(_closed(page) for page in opened)
        assert _closed(crops[-2])  # RGBA crop is released after RGB conversion.
        if fail_encode:
            raise OSError("failed JPEG encoder")
        return real_save(image, *args, **kwargs)

    monkeypatch.setattr(PILImage, "open", tracked_open)
    monkeypatch.setattr(PILImage.Image, "crop", tracked_crop)
    monkeypatch.setattr(PILImage.Image, "convert", tracked_convert)
    monkeypatch.setattr(PILImage.Image, "save", tracked_save)
    pdf_image_utils.save_elements(
        [_element(), _element()],
        7,
        "Image",
        200,
        filename=str(source),
        is_image=True,
        extract_image_block_to_payload=True,
    )
    assert len(opened) == 2
    assert all(_closed(image) for image in opened + crops)
