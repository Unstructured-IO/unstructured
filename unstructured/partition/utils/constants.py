from enum import Enum


class OCRMode(Enum):
    INDIVIDUAL_BLOCKS = "individual_blocks"
    FULL_PAGE = "entire_page"


SORT_MODE_XY_CUT = "xy-cut"
SORT_MODE_BASIC = "basic"

SUBREGION_THRESHOLD_FOR_OCR = 0.5
