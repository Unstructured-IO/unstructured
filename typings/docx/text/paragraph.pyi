from typing import Iterator, List, Sequence

from docx.blkcntnr import BlockItemContainer
from docx.oxml.text.paragraph import CT_P
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.styles.style import ParagraphStyle
from docx.text.hyperlink import Hyperlink
from docx.text.pagebreak import RenderedPageBreak
from docx.text.run import Run

class Paragraph(BlockItemContainer):
    _p: CT_P
    _parent: BlockItemContainer
    text: str
    def __init__(self, p: BaseOxmlElement, parent: BlockItemContainer) -> None: ...
    @property
    def contains_page_break(self) -> bool: ...
    @property
    def hyperlinks(self) -> List[Hyperlink]: ...
    def iter_inner_content(self) -> Iterator[Run | Hyperlink]: ...
    @property
    def rendered_page_breaks(self) -> List[RenderedPageBreak]: ...
    @property
    def runs(self) -> Sequence[Run]: ...
    @property
    def style(self) -> ParagraphStyle | None: ...
