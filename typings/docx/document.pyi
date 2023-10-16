from typing import IO

from docx.blkcntnr import BlockItemContainer
from docx.oxml.document import CT_Document
from docx.section import Sections
from docx.settings import Settings
from docx.styles.style import ParagraphStyle
from docx.text.paragraph import Paragraph

class Document(BlockItemContainer):
    def add_paragraph(
        self, text: str = "", style: ParagraphStyle | str | None = None
    ) -> Paragraph: ...
    @property
    def element(self) -> CT_Document: ...
    def save(self, path_or_stream: str | IO[bytes]) -> None: ...
    @property
    def sections(self) -> Sections: ...
    @property
    def settings(self) -> Settings: ...
