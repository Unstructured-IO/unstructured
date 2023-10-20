import os
from enum import Enum


class Source(Enum):
    OCR_TESSERACT = "ocr_tesseract"
    OCR_PADDLE = "ocr_paddle"


class OCRMode(Enum):
    INDIVIDUAL_BLOCKS = "individual_blocks"
    FULL_PAGE = "entire_page"


class OCROutputType(Enum):
    STRING = "string"
    TEXT_REGIONS = "text_regions"


SORT_MODE_XY_CUT = "xy-cut"
SORT_MODE_BASIC = "basic"
SORT_MODE_DONT = "dont"

SUBREGION_THRESHOLD_FOR_OCR = 0.5
UNSTRUCTURED_INCLUDE_DEBUG_METADATA = os.getenv("UNSTRUCTURED_INCLUDE_DEBUG_METADATA", False)
