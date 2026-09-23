from __future__ import annotations

import numpy as np
import pypdfium2 as pdfium

from unstructured_inference.inference import pdf_image

# sample-docs/form-field.pdf is a 1-page PDF with an empty content stream and a single
# filled text form field. The field value ("FORMVALUE777") is drawn only by the widget
# annotation's appearance stream, so it renders only when the form-fill environment is
# initialized (init_forms). Geometry below mirrors the fixture's widget rectangle.
FORM_PDF = "sample-docs/form-field.pdf"
PAGE_WIDTH, PAGE_HEIGHT = 612, 792
FIELD_RECT = (40, 700, 320, 724)  # x1, y1, x2, y2 in PDF user space (origin bottom-left)
RENDER_DPI = 200


def _field_region_dark_pixels(img) -> int:
    """Count dark pixels inside the form field's rectangle in the rendered image."""
    gray = img.convert("L")
    scale_x = gray.width / PAGE_WIDTH
    scale_y = gray.height / PAGE_HEIGHT
    x0, y0, x1, y1 = FIELD_RECT
    # PDF user space is bottom-up; image space is top-down.
    box = (
        int(x0 * scale_x),
        int((PAGE_HEIGHT - y1) * scale_y),
        int(x1 * scale_x),
        int((PAGE_HEIGHT - y0) * scale_y),
    )
    crop = np.array(gray.crop(box))
    return int(np.count_nonzero(crop < 128))


def test_convert_pdf_to_image_renders_acroform_field_value():
    """Filled form-field values are painted into the rendered page image."""
    img = pdf_image.convert_pdf_to_image(filename=FORM_PDF, dpi=RENDER_DPI)[0]

    assert _field_region_dark_pixels(img) > 100, "Expected the form field value to be rendered"


def test_convert_pdf_to_image_drops_form_field_without_init_forms(monkeypatch):
    """Control: without init_forms() the widget appearance is not painted.

    Patching init_forms() to a no-op reproduces the pre-fix behavior and proves the
    rendered field value in the test above comes specifically from initializing the
    form-fill environment, not from the page content stream (which is empty here).
    """
    monkeypatch.setattr(pdfium.PdfDocument, "init_forms", lambda self, *a, **k: None)
    img = pdf_image.convert_pdf_to_image(filename=FORM_PDF, dpi=RENDER_DPI)[0]

    assert _field_region_dark_pixels(img) == 0, "Field should be blank without form init"
