from typing import Optional

from docx.oxml.xmlchemy import BaseOxmlElement

class CT_Br(BaseOxmlElement):
    type: Optional[str]
    clear: Optional[str]

class CT_R(BaseOxmlElement): ...
