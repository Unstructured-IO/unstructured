from docx.shared import ElementProxy

class Settings(ElementProxy):
    @property
    def odd_and_even_pages_header_footer(self) -> bool: ...
