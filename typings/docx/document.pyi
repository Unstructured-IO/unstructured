from typing import IO, Iterator, List

from docx.oxml.document import CT_Document
from docx.section import Sections
from docx.settings import Settings
from docx.shared import ElementProxy
from docx.styles.style import ParagraphStyle
from docx.table import Table
from docx.text.paragraph import Paragraph

class Document(ElementProxy):
    def add_paragraph(
        self,
        text: str = "",
        style: ParagraphStyle | str | None = None,
    ) -> Paragraph: ...
    @property
    def element(self) -> CT_Document: ...
    def iter_inner_content(self) -> Iterator[Paragraph | Table]: ...
    @property
    def paragraphs(self) -> List[Paragraph]: ...
    @property
    def tables(self) -> List[Table]: ...
    def save(self, path_or_stream: str | IO[bytes]) -> None: ...
    @property
    def sections(self) -> Sections: ...
    @property
    def settings(self) -> Settings: ...
