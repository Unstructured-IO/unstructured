from typing import Optional

from docx.oxml.xmlchemy import BaseOxmlElement

class CT_SectPr(BaseOxmlElement):
    @property
    def preceding_sectPr(self) -> Optional[CT_SectPr]: ...
