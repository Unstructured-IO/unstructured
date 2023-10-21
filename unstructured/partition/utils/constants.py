import os
from enum import Enum


class OCRMode(Enum):
    INDIVIDUAL_BLOCKS = "individual_blocks"
    FULL_PAGE = "entire_page"


SORT_MODE_XY_CUT = "xy-cut"
SORT_MODE_BASIC = "basic"
SORT_MODE_DONT = "dont"

SUBREGION_THRESHOLD_FOR_OCR = 0.5
UNSTRUCTURED_INCLUDE_DEBUG_METADATA = os.getenv("UNSTRUCTURED_INCLUDE_DEBUG_METADATA", False)


# this field is defined by pytesseract/unstructured.pytesseract
TESSERACT_TEXT_HEIGHT = "height"
