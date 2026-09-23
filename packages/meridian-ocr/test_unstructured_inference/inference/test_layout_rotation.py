from __future__ import annotations

import numpy as np

from unstructured_inference.inference import pdf_image


def test_convert_pdf_to_image_applies_rotation():
    """Pages with /Rotate metadata are rendered upright."""
    result = pdf_image.convert_pdf_to_image(filename="sample-docs/rotated-page-90.pdf", dpi=72)
    assert len(result) == 1
    img = result[0]
    # pypdfium2 renders this /Rotate=90 page in its display frame (landscape, text sideways);
    # the text-orientation correction then rotates it back upright (portrait), and records the
    # angle so the pdfminer coordinates can be rotated to match downstream.
    assert img.height > img.width, f"Expected portrait after rotation, got {img.size}"
    assert img.info.get("pdf_rotation") == 90
    assert img.info.get("pdf_rotation_correction") == 90

    # Fixture contract: rotated-page-90.pdf has visible dark text in the upper half when upright.
    # Use relative dark-pixel counts to reduce sensitivity to minor renderer differences.
    gray = np.array(img.convert("L"))
    split = gray.shape[0] // 2
    top_dark_pixels = int(np.count_nonzero(gray[:split] < 245))
    bottom_dark_pixels = int(np.count_nonzero(gray[split:] < 245))

    assert top_dark_pixels > 0, "Expected text pixels in upper half of upright page"
    assert top_dark_pixels > max(bottom_dark_pixels * 10, 50), (
        "Expected substantially more dark pixels in upper half for upright orientation; "
        f"got top={top_dark_pixels}, bottom={bottom_dark_pixels}"
    )


def test_convert_pdf_to_image_no_correction_for_unrotated_page():
    """Pages without /Rotate are rendered as-is with a zero correction."""
    result = pdf_image.convert_pdf_to_image(filename="sample-docs/loremipsum.pdf", dpi=72)
    img = result[0]
    assert img.info.get("pdf_rotation") == 0
    assert img.info.get("pdf_rotation_correction") == 0


def test_convert_pdf_to_image_skips_correction_below_threshold(monkeypatch):
    """A high dominant-angle threshold leaves the page in its native display frame.

    This guards against re-orienting pages without a clear dominant text direction: with an
    unreachable threshold no correction is applied even though /Rotate is non-zero.
    """
    monkeypatch.setenv("PDF_ROTATION_DOMINANT_ANGLE_THRESHOLD", "1.1")
    img = pdf_image.convert_pdf_to_image(filename="sample-docs/rotated-page-90.pdf", dpi=72)[0]
    assert img.info.get("pdf_rotation") == 90
    assert img.info.get("pdf_rotation_correction") == 0
    # native display frame for this page is landscape (sideways), i.e. no correction applied
    assert img.width > img.height, f"Expected uncorrected landscape frame, got {img.size}"
