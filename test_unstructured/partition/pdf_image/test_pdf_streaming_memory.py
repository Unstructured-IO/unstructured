"""Preserve upload ownership and native render output while bounding working memory."""

import io
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from unstructured.partition.pdf_image import ocr, pdf_image_utils


class BoundedBytesIO(io.BytesIO):
    def read(self, size=-1):
        assert 0 < size <= 1024 * 1024
        return super().read(size)


@pytest.mark.parametrize("kind", ["bytes", "bytesio", "spool-memory", "spool-disk", "buffered"])
def test_uploaded_pdf_is_copied_in_bounded_reads_with_original_cursor_semantics(kind, tmp_path):
    stack = ExitStack()
    payload = b"document" * 300000
    path = tmp_path / "source.pdf"
    path.write_bytes(payload)
    if kind == "bytes":
        source = payload
    elif kind == "bytesio":
        source = BoundedBytesIO(payload)
    elif kind == "buffered":
        source = stack.enter_context(path.open("rb"))
    else:
        source = stack.enter_context(
            tempfile.SpooledTemporaryFile(  # noqa: SIM115 - owned by ExitStack
                max_size=1 if kind == "spool-disk" else len(payload) + 1
            )
        )
        source.write(payload)
    if kind != "bytes":
        source.seek(3)
    with pdf_image_utils._pdf_source_path("", source) as copied_path:
        assert Path(copied_path).read_bytes() == payload
        assert kind == "bytes" or not source.closed
    assert not os.path.exists(copied_path)
    if kind != "bytes":
        assert source.tell() == (0 if kind.startswith("spool") else 3)
        stack.close()


def test_render_generator_does_not_materialize_a_decoded_page_batch(monkeypatch):
    monkeypatch.setattr(
        pdf_image_utils.pdf2image, "pdfinfo_from_path", lambda *a, **k: {"Pages": 10}
    )
    calls = []

    def render(**kwargs):
        calls.append((kwargs["first_page"], kwargs["last_page"]))
        assert kwargs["first_page"] == kwargs["last_page"]
        return [Image.new("RGB", (2, 2), (kwargs["first_page"], 0, 0))]

    monkeypatch.setattr(pdf_image_utils, "render_pdf_to_image", render)
    pages = pdf_image_utils.convert_pdf_to_images(filename="input.pdf")
    first = next(pages)
    assert calls == [(1, 1)]
    rest = list(pages)
    assert calls == [(page, page) for page in range(1, 11)]
    assert first.getpixel((0, 0)) == (1, 0, 0)
    assert rest[-1].getpixel((0, 0)) == (10, 0, 0)
    for image in [first, *rest]:
        image.close()


def test_generator_close_removes_owned_upload_without_closing_borrowed_stream(monkeypatch):
    paths = []

    def info(path, **kwargs):
        paths.append(path)
        return {"Pages": 2}

    monkeypatch.setattr(pdf_image_utils.pdf2image, "pdfinfo_from_path", info)
    monkeypatch.setattr(
        pdf_image_utils, "render_pdf_to_image", lambda **k: [Image.new("RGB", (1, 1))]
    )
    source = BoundedBytesIO(b"pdf bytes")
    pages = pdf_image_utils.convert_pdf_to_images(file=source)
    image = next(pages)
    assert os.path.exists(paths[0])
    pages.close()
    assert not os.path.exists(paths[0])
    assert not source.closed
    assert image.getpixel((0, 0)) == (0, 0, 0)
    image.close()


def test_process_data_with_ocr_copies_only_remaining_stream_without_retaining_a_full_read(
    monkeypatch,
):
    source = BoundedBytesIO(b"prefix" + b"document" * 300000)
    source.seek(6)
    paths = []
    result = object()

    def process(filename, **kwargs):
        paths.append(filename)
        assert Path(filename).read_bytes() == b"document" * 300000
        return result

    monkeypatch.setattr(ocr, "process_file_with_ocr", process)
    assert ocr.process_data_with_ocr(source, Mock(), []) is result
    assert not source.closed
    assert source.tell() == len(source.getvalue())
    assert not os.path.exists(paths[0])


@pytest.mark.parametrize("fail", [False, True])
def test_ocr_only_closes_owned_render_images_on_success_and_failure(monkeypatch, fail):
    from unstructured.partition import pdf

    image = Image.new("RGB", (2, 2))
    monkeypatch.setattr(pdf_image_utils, "convert_pdf_to_images", lambda *a, **k: iter([image]))

    def partition(**kwargs):
        assert kwargs["image"].getpixel((0, 0)) == (0, 0, 0)
        if fail:
            raise RuntimeError("OCR failed")
        return []

    monkeypatch.setattr(pdf, "_partition_pdf_or_image_with_ocr_from_image", partition)
    if fail:
        with pytest.raises(RuntimeError, match="OCR failed"):
            pdf._partition_pdf_or_image_with_ocr(filename="input.pdf")
    else:
        assert pdf._partition_pdf_or_image_with_ocr(filename="input.pdf") == []
    with pytest.raises(ValueError, match="closed image"):
        image.getpixel((0, 0))


@pytest.mark.parametrize(
    "fixture",
    ["rotated-page-90.pdf", "pdf/layout-parser-paper-fast.pdf", "pdf/embedded-images.pdf"],
)
def test_single_page_render_matches_native_batch_pixels_and_metadata(fixture):
    from test_unstructured.unit_utils import example_doc_path

    path = str(example_doc_path(fixture))
    expected = pdf_image_utils.render_pdf_to_image(
        filename=path,
        dpi=pdf_image_utils.env_config.PDF_RENDER_DPI,
        pdf_render_max_pixels_per_page=pdf_image_utils.env_config.PDF_RENDER_MAX_PIXELS_PER_PAGE,
    )
    actual = list(pdf_image_utils.convert_pdf_to_images(filename=path))
    assert len(actual) == len(expected)
    for baseline, candidate in zip(expected, actual):
        assert (candidate.size, candidate.mode, candidate.format, candidate.info) == (
            baseline.size,
            baseline.mode,
            baseline.format,
            baseline.info,
        )
        assert candidate.tobytes() == baseline.tobytes()
        baseline.close()
        candidate.close()


class ReadSeekStream(io.RawIOBase):
    """A readable, seekable stream that is not a `BytesIO`, spool or buffered file."""

    def __init__(self, payload: bytes):
        self._buffer = io.BytesIO(payload)

    def readable(self):
        return True

    def seekable(self):
        return True

    def readinto(self, buffer):
        return self._buffer.readinto(buffer)

    def seek(self, offset, whence=io.SEEK_SET):
        return self._buffer.seek(offset, whence)

    def tell(self):
        return self._buffer.tell()


def test_ocr_only_accepts_any_readable_seekable_stream():
    from test_unstructured.unit_utils import example_doc_path
    from unstructured.partition import pdf

    path = example_doc_path("pdf/layout-parser-paper-fast.pdf")
    expected = pdf._partition_pdf_or_image_with_ocr(filename=path)
    source = ReadSeekStream(Path(path).read_bytes())
    source.seek(5)
    actual = pdf._partition_pdf_or_image_with_ocr(file=source)
    assert [element.text for element in actual] == [element.text for element in expected]
    assert not source.closed
    assert source.tell() == 0
