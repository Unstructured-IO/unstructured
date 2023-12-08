from typing import Iterator, Sequence

from docx.oxml.xmlchemy import BaseOxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph

class BlockItemContainer:
    _element: BaseOxmlElement
    def iter_inner_content(self) -> Iterator[Paragraph | Table]: ...
    @property
    def paragraphs(self) -> Sequence[Paragraph]: ...
    @property
    def tables(self) -> Sequence[Table]: ...
