from pptx.util import Length

class BaseShape:
    left: Length
    top: Length
    @property
    def has_table(self) -> bool: ...
    @property
    def has_text_frame(self) -> bool: ...
