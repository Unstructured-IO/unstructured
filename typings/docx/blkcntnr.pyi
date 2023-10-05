from typing import Sequence

from docx.oxml.xmlchemy import BaseOxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph

class BlockItemContainer:
    _element: BaseOxmlElement
    @property
    def paragraphs(self) -> Sequence[Paragraph]: ...
    @property
    def tables(self) -> Sequence[Table]: ...
