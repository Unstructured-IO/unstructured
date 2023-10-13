from typing import Sequence

from docx.blkcntnr import BlockItemContainer
from docx.oxml.table import CT_Tbl, CT_Tc
from docx.shared import Parented
from docx.text.paragraph import Paragraph

class _Cell(BlockItemContainer):
    _tc: CT_Tc
    @property
    def paragraphs(self) -> Sequence[Paragraph]: ...

class _Row:
    @property
    def cells(self) -> Sequence[_Cell]: ...

class _Rows(Sequence[_Row]): ...

class Table(Parented):
    def __init__(self, tbl: CT_Tbl, parent: BlockItemContainer) -> None: ...
    @property
    def rows(self) -> _Rows: ...
