from __future__ import annotations

import contextlib
import math
import os
from functools import lru_cache
from pathlib import Path, PurePath
from threading import Lock
from typing import BinaryIO, Optional, Union

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTChar, LTContainer
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from unstructured_inference.config import inference_config
from unstructured_inference.constants import PDF_POINTS_PER_INCH

_pdfium_lock = Lock()


class PdfRenderTooLargeError(ValueError):
    pass


def _check_pdf_render_max_pixels(page, page_number: int, scale: float, maximum: int) -> None:
    if maximum <= 0:
        return

    rendered_width = math.ceil(page.get_width() * scale)
    rendered_height = math.ceil(page.get_height() * scale)
    rendered_pixels = rendered_width * rendered_height

    if rendered_pixels > maximum:
        raise PdfRenderTooLargeError(
            "PDF page would render to too many pixels for safe processing: "
            f"page={page_number}, pixels={rendered_pixels}, maximum={maximum}. "
            "Try splitting the PDF, reducing the page dimensions, or using a lower render DPI.",
        )


@lru_cache(maxsize=1)
def _get_pdfium_module():
    import pypdfium2 as pdfium

    return pdfium


def _iter_ltchars(obj):
    """Yield every ``LTChar`` reachable from a pdfminer layout object."""
    if isinstance(obj, LTChar):
        yield obj
    elif isinstance(obj, LTContainer):
        for child in obj:
            yield from _iter_ltchars(child)


def _dominant_text_rotation(page_layout, threshold: float) -> int:
    """Estimate the extra rotation (a multiple of 90 degrees) to apply to a rendered page
    so that its dominant text becomes horizontal.

    The angle is derived from pdfminer character matrices, which are expressed in the
    page's *display* frame (pdfminer already honors ``/Rotate``) — the same frame the
    rendered bitmap lives in. This is the only orientation signal that reliably matches
    the render: pdfium's character-angle APIs report in the unrotated page frame and do
    not map cleanly to the displayed image.

    Returns ``0`` (no correction) unless a single non-zero 90-degree orientation accounts
    for at least ``threshold`` of the characters, so pages without a clear dominant text
    direction are left in their display frame.
    """
    counts = {0: 0, 90: 0, 180: 0, 270: 0}
    total = 0
    for char in _iter_ltchars(page_layout):
        angle = math.degrees(math.atan2(char.matrix[1], char.matrix[0])) % 360
        bucket = min((0, 90, 180, 270, 360), key=lambda k: abs(k - angle)) % 360
        counts[bucket] += 1
        total += 1

    if total == 0:
        return 0

    dominant = max(counts, key=counts.get)
    if dominant == 0 or counts[dominant] / total < threshold:
        return 0
    # PIL's rotate() is counter-clockwise, so the rotation that brings text drawn at
    # ``dominant`` degrees back to horizontal is its complement.
    return (360 - dominant) % 360


def _as_pdfminer_source(filename, file):
    """Return a path or a rewound byte stream that pdfminer can read without disturbing
    the caller's ``file`` object."""
    import io

    if filename is not None:
        return filename
    if isinstance(file, (bytes, bytearray)):
        return io.BytesIO(bytes(file))
    # file-like: snapshot its bytes so we don't consume the caller's stream position
    position = file.tell()
    file.seek(0)
    data = file.read()
    file.seek(position)
    return io.BytesIO(data)


def _estimate_rotation_corrections(
    filename,
    file,
    rotated_page_indices: list,
    password: Optional[str],
    threshold: float,
) -> dict:
    """Map each rotated page index (0-based) to the extra rotation that makes its dominant
    text horizontal. Returns ``{}`` on any failure so rendering degrades gracefully to the
    page's native display frame (still consistent with pdfminer, just possibly sideways)."""
    if not rotated_page_indices:
        return {}
    try:
        wanted = sorted(rotated_page_indices)
        source = _as_pdfminer_source(filename, file)
        corrections = {}
        for idx, page_layout in zip(
            wanted,
            extract_pages(source, page_numbers=wanted, password=password or ""),
        ):
            corrections[idx] = _dominant_text_rotation(page_layout, threshold)
        return corrections
    except Exception:
        return {}


def convert_pdf_to_image(
    filename: Optional[str] = None,
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
    output_folder: Optional[Union[str, PurePath]] = None,
    path_only: bool = False,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    password: Optional[str] = None,
    pdf_render_max_pixels_per_page: Optional[int] = None,
) -> Union[list[Image.Image], list[str]]:
    """Render PDF pages to PIL images or saved PNGs using pypdfium2.

    This is the single source of truth for PDF→image rendering across unstructured
    and unstructured-inference. Callers should pass their own DPI value explicitly.
    """
    if path_only and not output_folder:
        raise ValueError("output_folder must be specified if path_only is true")
    if filename is None and file is None:
        raise ValueError("Either filename or file must be provided")
    if output_folder:
        assert Path(output_folder).exists()
        assert Path(output_folder).is_dir()

    scale = dpi / PDF_POINTS_PER_INCH
    if pdf_render_max_pixels_per_page is None:
        pdf_render_max_pixels_per_page = inference_config.PDF_RENDER_MAX_PIXELS_PER_PAGE
    pdfium = _get_pdfium_module()

    def _in_range(page_num: int) -> bool:
        return (first_page is None or page_num >= first_page) and (
            last_page is None or page_num <= last_page
        )

    with _pdfium_lock:
        pdf = pdfium.PdfDocument(filename or file, password=password)
        # Initialize the form-fill environment so AcroForm/XFA field values
        # (e.g. text typed into fillable fields) are painted into the rendered
        # image. Without this, pdfium silently drops widget annotation content
        # even though may_draw_forms defaults to True on page.render().
        # Fall back to page rendering without form appearances when form env init fails.
        with contextlib.suppress(pdfium.PdfiumError):
            pdf.init_forms()
        n_pages = len(pdf)

        # Pre-scan page rotations so the (heavier) text-orientation pass only runs on the
        # pages the author explicitly marked as rotated (Guard 1: /Rotate != 0).
        page_rotations: dict[int, int] = {}
        for i in range(n_pages):
            if not _in_range(i + 1):
                continue
            pg = pdf[i]
            try:
                page_rotations[i] = pg.get_rotation()
            finally:
                pg.close()

    rotated_page_indices = [i for i, rot in page_rotations.items() if rot]
    rotation_corrections = _estimate_rotation_corrections(
        filename,
        file,
        rotated_page_indices,
        password,
        inference_config.PDF_ROTATION_DOMINANT_ANGLE_THRESHOLD,
    )

    try:
        images: dict[int, Image.Image] = {}
        filenames: list[str] = []
        for i in range(n_pages):
            page_num = i + 1
            if first_page is not None and page_num < first_page:
                continue
            if last_page is not None and page_num > last_page:
                break

            with _pdfium_lock:
                page = pdf[i]
                try:
                    _check_pdf_render_max_pixels(
                        page=page,
                        page_number=page_num,
                        scale=scale,
                        maximum=pdf_render_max_pixels_per_page,
                    )
                    bitmap = page.render(
                        scale=scale,
                        no_smoothtext=False,
                        no_smoothimage=False,
                        no_smoothpath=False,
                        optimize_mode="print",
                    )
                    try:
                        pil_image = bitmap.to_pil()
                    finally:
                        bitmap.close()

                    # pypdfium2 already renders with /Rotate applied (the display frame),
                    # which matches pdfminer's coordinate frame. Only apply an *additional*
                    # text-orientation correction when one was estimated, and apply the
                    # same angle to the pdfminer coordinates downstream (via the stored
                    # metadata) so the two layers stay consistent.
                    rotation = page.get_rotation()
                    correction = rotation_corrections.get(i, 0)
                    if correction:
                        pil_image = pil_image.rotate(correction, expand=True)
                    pil_image.info["pdf_rotation"] = rotation
                    pil_image.info["pdf_rotation_correction"] = correction

                finally:
                    page.close()

            if output_folder:
                fn: str = os.path.join(str(output_folder), f"page_{page_num}.png")

                png_meta = PngInfo()
                png_meta.add_text("pdf_rotation", str(rotation))
                png_meta.add_text("pdf_rotation_correction", str(correction))
                pil_image.save(
                    fn,
                    format="PNG",
                    compress_level=1,
                    optimize=False,
                    pnginfo=png_meta,
                )
                filenames.append(fn)
                if not path_only:
                    images[page_num] = pil_image
            else:
                images[page_num] = pil_image
    finally:
        with _pdfium_lock:
            pdf.close()

    if path_only:
        return filenames
    return list(images.values())
