from layoutparser.ocr.tesseract_agent import is_pytesseract_available, TesseractAgent

from unstructured.logger import get_logger

ocr_agent: TesseractAgent = None

logger = get_logger()


def load_agent():
    """Loads the Tesseract OCR agent as a global variable to ensure that we only load it once."""
    global ocr_agent

    if not is_pytesseract_available():
        raise ImportError(
            "Failed to load Tesseract. Ensure that Tesseract is installed. Example command: \n"
            "    >>> sudo apt install -y tesseract-ocr"
        )

    if ocr_agent is None:
        logger.info("Loading the Tesseract OCR agent ...")
        ocr_agent = TesseractAgent(languages="eng")
