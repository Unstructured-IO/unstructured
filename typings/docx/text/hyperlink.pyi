from docx.oxml.text.hyperlink import CT_Hyperlink
from docx.shared import Parented
from docx.text.paragraph import Paragraph

class Hyperlink(Parented):
    _element: CT_Hyperlink
    _r: CT_Hyperlink
    text: str
    url: str
    def __init__(self, hyperlink: CT_Hyperlink, parent: Paragraph) -> None: ...
