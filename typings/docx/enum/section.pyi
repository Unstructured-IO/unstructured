import enum

class WD_SECTION_START(enum.Enum):
    CONTINUOUS: enum.Enum
    EVEN_PAGE: enum.Enum
    NEW_COLUMN: enum.Enum
    NEW_PAGE: enum.Enum
    ODD_PAGE: enum.Enum

# -- alias --
WD_SECTION = WD_SECTION_START
