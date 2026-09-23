from enum import Enum


class Source(Enum):
    YOLOX = "yolox"
    DETECTRON2_ONNX = "detectron2_onnx"
    DETECTRON2_LP = "detectron2_lp"


class IsExtracted(Enum):
    TRUE = "true"
    FALSE = "false"
    PARTIAL = "partial"


class ElementType:
    PARAGRAPH = "Paragraph"
    IMAGE = "Image"
    PARAGRAPH_IN_IMAGE = "ParagraphInImage"
    FIGURE = "Figure"
    PICTURE = "Picture"
    TABLE = "Table"
    PARAGRAPH_IN_TABLE = "ParagraphInTable"
    LIST = "List"
    FORM = "Form"
    PARAGRAPH_IN_FORM = "ParagraphInForm"
    CHECK_BOX_CHECKED = "CheckBoxChecked"
    CHECK_BOX_UNCHECKED = "CheckBoxUnchecked"
    RADIO_BUTTON_CHECKED = "RadioButtonChecked"
    RADIO_BUTTON_UNCHECKED = "RadioButtonUnchecked"
    LIST_ITEM = "List-item"
    FORMULA = "Formula"
    CAPTION = "Caption"
    PAGE_HEADER = "Page-header"
    SECTION_HEADER = "Section-header"
    PAGE_FOOTER = "Page-footer"
    FOOTNOTE = "Footnote"
    TITLE = "Title"
    TEXT = "Text"
    UNCATEGORIZED_TEXT = "UncategorizedText"
    PAGE_BREAK = "PageBreak"
    CODE_SNIPPET = "CodeSnippet"
    PAGE_NUMBER = "PageNumber"
    OTHER = "Other"


FULL_PAGE_REGION_THRESHOLD = 0.99

# this field is defined by pytesseract/unstructured.pytesseract
TESSERACT_TEXT_HEIGHT = "height"

PDF_POINTS_PER_INCH = 72
