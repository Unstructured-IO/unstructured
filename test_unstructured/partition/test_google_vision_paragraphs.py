import pytest
from google.cloud.vision import Paragraph, TextAnnotation

from unstructured.partition.utils.ocr_models.google_vision_ocr import OCRAgentGoogleVision


@pytest.mark.parametrize(
    ("symbols", "expected"),
    [
        ([("final", "UNKNOWN", False)], "final"),
        ([("first", "SPACE", False), ("last", "UNKNOWN", False)], "first last"),
        ([("first", "SURE_SPACE", False), ("last", "UNKNOWN", False)], "first last"),
        ([("first", "EOL_SURE_SPACE", False), ("last", "UNKNOWN", False)], "first last"),
        ([("first", "LINE_BREAK", False), ("last", "UNKNOWN", False)], "first\nlast"),
        ([("hyphen", "HYPHEN", False), ("ated", "UNKNOWN", False)], "hyphen-\nated"),
        ([("first", "UNKNOWN", False), ("last", "SPACE", True)], "first last"),
        ([("whole", "LINE_BREAK", False)], "whole"),
        ([], ""),
    ],
)
def test_paragraph_keeps_all_symbols_and_detected_breaks(symbols, expected):
    breaks = TextAnnotation.DetectedBreak.BreakType
    words = []
    for text, break_, prefix in symbols:
        characters = [{"text": char} for char in text]
        characters[0 if prefix else -1]["property"] = {
            "detected_break": {"type_": getattr(breaks, break_), "is_prefix": prefix}
        }
        words.append({"symbols": characters})
    paragraph = Paragraph(words=words)
    agent = object.__new__(OCRAgentGoogleVision)

    assert agent._get_text_from_paragraph(paragraph) == expected
