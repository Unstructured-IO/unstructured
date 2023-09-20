from typing import Iterator

from docx.oxml.xmlchemy import BaseOxmlElement

class CT_Body(BaseOxmlElement):
    def __iter__(self) -> Iterator[BaseOxmlElement]: ...

class CT_Document(BaseOxmlElement):
    @property
    def body(self) -> CT_Body: ...
