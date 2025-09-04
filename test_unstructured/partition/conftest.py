import pytest

from unstructured.partition.utils.constants import OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT


@pytest.fixture
def mock_ocr_get_instance(mocker):
    """Fixture that mocks OCRAgent.get_instance to prevent real OCR agent instantiation."""

    def mock_get_instance(ocr_agent_module, language):
        if ocr_agent_module in (OCR_AGENT_TESSERACT, OCR_AGENT_PADDLE):
            return mocker.MagicMock()
        else:
            raise ValueError(f"Unknown OCR agent: {ocr_agent_module}")

    from unstructured.partition.pdf_image.ocr import OCRAgent

    return mocker.patch.object(OCRAgent, "get_instance", side_effect=mock_get_instance)
