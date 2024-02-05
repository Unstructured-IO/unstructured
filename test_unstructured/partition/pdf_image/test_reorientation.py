import io
from typing import List

import pypdf
import pytest
from PIL import Image as PILImage
from rapidfuzz.distance import Levenshtein

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import Element, Text
from unstructured.partition import pdf
from unstructured.partition.pdf_image import orientation_and_rotation
from unstructured.partition.pdf_image.orientation_and_rotation import Orientation
from unstructured.partition.utils.constants import PartitionStrategy, ReorientationStrategy


def test_do_not_reorient_when_strategy_none(
    filename=example_doc_path("layout-parser-paper-fast.pdf"),
):
    pdf_doc = pypdf.PdfReader(filename)
    for page in pdf_doc.pages:
        assert orientation_and_rotation._find_orientation(page, ReorientationStrategy.NONE) == 0


@pytest.mark.parametrize(
    "strategy",
    [
        ReorientationStrategy.NONE,
        ReorientationStrategy.CNN,
        ReorientationStrategy.TESSEROCR,
        ReorientationStrategy.PYTESSERACT,
    ],
)
def test_do_not_reorient_when_not_scan(
    strategy: str,
    filename=example_doc_path("embedded-images.pdf"),
):
    pdf_doc = pypdf.PdfReader(filename)
    for page in pdf_doc.pages:
        assert orientation_and_rotation._find_orientation(page.rotate(90), strategy) == 0


def test_same_ocr_result(
    monkeypatch,
    strategy: str = ReorientationStrategy.PYTESSERACT,
    filename=example_doc_path("loremipsum-flat.pdf"),
):
    test_done = False
    monkeypatch.setattr(orientation_and_rotation, "_find_orientation", lambda *args, **kwargs: 180)

    pdf_doc = pypdf.PdfReader(filename)
    for page in pdf_doc.pages:
        if len(page.images) == 1:
            image = PILImage.open(io.BytesIO(page.images[0].data))
            new_image = image.rotate(180)
            new_pdf_orig = io.BytesIO()
            new_pdf_rotated = io.BytesIO()

            image.save(new_pdf_orig, "pdf")
            new_image.save(new_pdf_rotated, "pdf")
            original_result = pdf.partition_pdf(
                file=new_pdf_orig,
                strategy=PartitionStrategy.HI_RES,
                hi_res_reorientation_strategy="",
            )
            rotated_no_reorientation_result = pdf.partition_pdf(
                file=new_pdf_rotated,
                strategy=PartitionStrategy.HI_RES,
                hi_res_reorientation_strategy="",
            )
            rotated_reoriented_result = pdf.partition_pdf(
                file=new_pdf_rotated,
                strategy=PartitionStrategy.HI_RES,
                hi_res_reorientation_strategy=strategy,
            )

            def get_text(results: List[Element]) -> str:
                return "".join([result.text for result in results if isinstance(result, Text)])

            def similar(text1: str, text2: str) -> bool:
                return Levenshtein.normalized_similarity(text1, text2) > 0.99

            original_text = get_text(original_result)
            rotated_no_reorientation_text = get_text(rotated_no_reorientation_result)
            rotated_reoriented_text = get_text(rotated_reoriented_result)

            assert similar(original_text, rotated_reoriented_text)
            assert not similar(original_text, rotated_no_reorientation_text)
            test_done = True

    assert test_done
