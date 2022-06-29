import pytest
from unittest.mock import patch

import unstructured.models.ocr.tesseract as tesseract


class MockTesseractAgent:
    def __init__(self, languages):
        pass


def test_load_agent(monkeypatch):
    monkeypatch.setattr(tesseract, "TesseractAgent", MockTesseractAgent)

    with patch.object(tesseract, "is_pytesseract_available", return_value=True):
        tesseract.load_agent()

    assert isinstance(tesseract.ocr_agent, MockTesseractAgent)


def test_load_agent_raises_when_not_available():
    with patch.object(tesseract, "is_pytesseract_available", return_value=False):
        with pytest.raises(ImportError):
            tesseract.load_agent()
