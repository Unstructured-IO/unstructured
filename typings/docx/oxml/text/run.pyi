from docx.oxml.xmlchemy import BaseOxmlElement

class CT_Br(BaseOxmlElement):
    type: str | None
    clear: str | None
    @property
    def text(self) -> str: ...

class CT_Cr(BaseOxmlElement):
    @property
    def text(self) -> str: ...

class CT_NoBreakHyphen(BaseOxmlElement):
    @property
    def text(self) -> str: ...

class CT_PTab(BaseOxmlElement):
    @property
    def text(self) -> str: ...

class CT_R(BaseOxmlElement):
    text: str

class CT_Tab(BaseOxmlElement):
    @property
    def text(self) -> str: ...

class CT_Text(BaseOxmlElement):
    @property
    def text(self) -> str: ...
