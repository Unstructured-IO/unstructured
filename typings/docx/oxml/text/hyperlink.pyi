from typing import List

from docx.oxml.text.run import CT_R
from docx.oxml.xmlchemy import BaseOxmlElement

class CT_Hyperlink(BaseOxmlElement):
    address: str
    @property
    def r_lst(self) -> List[CT_R]: ...
