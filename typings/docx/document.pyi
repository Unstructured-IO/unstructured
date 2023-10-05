# pyright: reportPrivateUsage=false

from typing import IO, Union

from docx.blkcntnr import BlockItemContainer
from docx.oxml.document import CT_Document
from docx.section import Sections
from docx.settings import Settings
from docx.styles.style import _ParagraphStyle
from docx.text.paragraph import Paragraph

class Document(BlockItemContainer):
    def add_paragraph(
        self, text: str = "", style: Union[_ParagraphStyle, str, None] = None,
    ) -> Paragraph: ...
    @property
    def element(self) -> CT_Document: ...
    def save(self, path_or_stream: Union[str, IO[bytes]]) -> None: ...
    @property
    def sections(self) -> Sections: ...
    @property
    def settings(self) -> Settings: ...
