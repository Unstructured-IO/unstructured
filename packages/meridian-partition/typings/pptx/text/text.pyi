from typing import Optional, Sequence

from pptx.oxml.text import CT_TextParagraph
from pptx.shapes import Subshape

class TextFrame(Subshape):
    text: str
    def add_paragraph(self) -> _Paragraph: ...
    @property
    def paragraphs(self) -> Sequence[_Paragraph]: ...

class _Paragraph(Subshape):
    _p: CT_TextParagraph
    text: str
    level: Optional[int]
