"""Table-related XML element-types."""

from __future__ import annotations

from typing import List

from docx.oxml.xmlchemy import BaseOxmlElement

class CT_Row(BaseOxmlElement):
    tc_lst: List[CT_Tc]

class CT_Tc(BaseOxmlElement):
    @property
    def vMerge(self) -> str | None: ...

class CT_Tbl(BaseOxmlElement): ...
