"""Table-related docx proxy-objects."""

from __future__ import annotations

from typing import Sequence

from docx.blkcntnr import BlockItemContainer
from docx.oxml.table import CT_Row, CT_Tbl, CT_Tc
from docx.shared import Parented

class _Cell(BlockItemContainer):
    _tc: CT_Tc
    def __init__(self, tc: CT_Tc, parent: Parented) -> None: ...
    @property
    def text(self) -> str: ...

class _Row(Parented):
    _tr: CT_Row
    @property
    def cells(self) -> Sequence[_Cell]: ...

class _Rows(Sequence[_Row]): ...

class Table(Parented):
    def __init__(self, tbl: CT_Tbl, parent: BlockItemContainer) -> None: ...
    @property
    def rows(self) -> _Rows: ...
