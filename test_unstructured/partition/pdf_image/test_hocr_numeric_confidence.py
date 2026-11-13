import pytest
from lxml import etree

from unstructured.partition.utils.ocr_models.tesseract_ocr import OCRAgentTesseract


def _hocr(characters):
    namespace = "http://www.w3.org/1999/xhtml"
    root = etree.Element(f"{{{namespace}}}html")
    word = etree.SubElement(
        root, f"{{{namespace}}}span", attrib={"class": "ocrx_word", "title": "bbox 10 20 60 35"}
    )
    for character, confidence in characters:
        child = etree.SubElement(
            word,
            f"{{{namespace}}}span",
            attrib={"class": "ocrx_cinfo", "title": f"x_bboxes 10 20 20 35; x_conf {confidence}"},
        )
        child.text = character
    return root


@pytest.mark.parametrize(
    ("confidence", "threshold"),
    [
        ("0", 0),
        ("99", 0.99),
        ("100", 1),
        ("99.5", 0.995),
        ("9.8e1", 0.98),
        ("1e-07", 0),
        ("1.0E+2", 1),
    ],
)
def test_hocr_accepts_integer_decimal_and_exponent_confidence(confidence, threshold):
    word = _hocr([("A", confidence)])[0]

    assert OCRAgentTesseract().extract_word_from_hocr(word, threshold) == "A"


@pytest.mark.parametrize("confidence", ["unknown", "99oops", "99.5oops", "9.8e", ""])
def test_hocr_does_not_accept_a_numeric_prefix_of_invalid_confidence(confidence):
    word = _hocr([("A", confidence)])[0]

    assert OCRAgentTesseract().extract_word_from_hocr(word, 0) == ""


@pytest.mark.parametrize(
    ("threshold", "expected"), [(0, "ABCDE"), (0.98, "ABCD"), (0.99, "AB"), (1, "A")]
)
def test_hocr_dataframe_keeps_characters_above_their_numeric_threshold(threshold, expected):
    hocr = etree.tostring(
        _hocr([("A", "100"), ("B", "99"), ("C", "98.5"), ("D", "9.8e1"), ("E", "1e-07")])
    )

    result = OCRAgentTesseract().hocr_to_dataframe(hocr, character_confidence_threshold=threshold)

    assert result.to_dict("records") == [
        {"left": 10, "top": 20, "width": 50, "height": 15, "text": expected}
    ]
