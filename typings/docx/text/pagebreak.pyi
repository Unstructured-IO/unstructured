from typing import Any

from docx.oxml.text.pagebreak import CT_LastRenderedPageBreak
from docx.shared import Parented
from docx.text.paragraph import Paragraph

class RenderedPageBreak(Parented):
    def __init__(self, lastRenderedPageBreak: CT_LastRenderedPageBreak, parent: Any) -> None: ...
    @property
    def preceding_paragraph_fragment(self) -> Paragraph | None: ...
    @property
    def following_paragraph_fragment(self) -> Paragraph | None: ...
