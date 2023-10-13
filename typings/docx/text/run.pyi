from docx.oxml.text.run import CT_R
from docx.shared import Parented
from docx.text.paragraph import Paragraph

class Run(Parented):
    _element: CT_R
    _r: CT_R
    def __init__(self, r: CT_R, parent: Paragraph) -> None: ...
    @property
    def bold(self) -> bool: ...
    @property
    def italic(self) -> bool: ...
    @property
    def text(self) -> str: ...
