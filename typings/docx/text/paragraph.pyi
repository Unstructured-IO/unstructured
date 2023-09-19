# pyright: reportPrivateUsage = false

from typing import Optional, Sequence

from docx.blkcntnr import BlockItemContainer
from docx.oxml.text.paragraph import CT_P
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.styles.style import _ParagraphStyle
from docx.text.run import Run

class Paragraph(BlockItemContainer):
    _p: CT_P
    def __init__(self, p: BaseOxmlElement, parent: BlockItemContainer) -> None: ...
    @property
    def runs(self) -> Sequence[Run]: ...
    @property
    def style(self) -> Optional[_ParagraphStyle]: ...
    @property
    def text(self) -> str: ...
